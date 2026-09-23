# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Fail-closed memory inference admission, independent of transcript capture.

Leases are process-local: restarting the companion grants no activity. Charges
are durable and reserved before a model call, so a crash cannot replenish them.
Only harness lifecycle signals can renew a lease; recall and append cannot.
"""
import threading
import time
import uuid
from pathlib import Path


LEASE_SECONDS = 6
WINDOW_SECONDS = 120
JOB_SECONDS = 120
JOB_TOKENS = 65536
CALL_SECONDS = 45
CALL_OUTPUT_TOKENS = 4096


class BudgetDenied(ValueError):
    pass


class InferenceBudget:
    def __init__(self, connect, clock=time.monotonic):
        self.connect = connect
        self.clock = clock
        self.lock = threading.RLock()
        self.leases = {}
        self.window_ends = {}
        self.active = None
        self.paused = False
        # Monotonic deadlines survive a companion restart, but not a reboot.
        # A reboot must invalidate old owners rather than extend their window.
        try:
            self.boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        except OSError:
            # Platforms without a boot ID invalidate owners on every restart.
            self.boot = uuid.uuid4().hex
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS memory_processing (id INTEGER PRIMARY KEY CHECK(id=1), paused INTEGER NOT NULL)')
            db.execute('INSERT OR IGNORE INTO memory_processing VALUES (1,0)')
            self.paused = bool(db.execute('SELECT paused FROM memory_processing').fetchone()[0])
            db.execute('''CREATE TABLE IF NOT EXISTS memory_windows (
                owner TEXT PRIMARY KEY, session TEXT NOT NULL, deadline REAL NOT NULL, closed INTEGER NOT NULL DEFAULT 0)''')
            if 'boot' not in {r['name'] for r in db.execute('PRAGMA table_info(memory_windows)')}:
                db.execute("ALTER TABLE memory_windows ADD COLUMN boot TEXT NOT NULL DEFAULT ''")
            db.execute('''CREATE TABLE IF NOT EXISTS memory_budgets (
                id TEXT PRIMARY KEY, seconds REAL NOT NULL, tokens INTEGER NOT NULL,
                calls INTEGER NOT NULL DEFAULT 0, failures INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'pending')''')

    def activity(self, session, owner, phase):
        if phase not in ('foreground', 'tools', 'stop'):
            raise ValueError('Invalid memory activity phase')
        with self.lock:
            key = (session, owner)
            if self.active and (phase == 'foreground' or phase == 'stop' and self.active['session'] == session):
                self.active['cancelled'] = True
            if phase == 'stop':
                self.leases.pop(key, None)
                self.window_ends.pop(key, None)
                with self.connect() as db:
                    db.execute('UPDATE memory_windows SET closed=1 WHERE owner=? AND session=?', (owner, session))
            else:
                with self.connect() as db:
                    db.execute('INSERT OR IGNORE INTO memory_windows(owner,session,deadline,boot) VALUES (?,?,?,?)',
                               (owner, session, self.clock() + WINDOW_SECONDS, self.boot))
                    row = db.execute('SELECT * FROM memory_windows WHERE owner=?', (owner,)).fetchone()
                if row['session'] != session or row['closed'] or row['boot'] != self.boot:
                    raise ValueError('Activity owner ended or belongs to another session')
                # Renewing a short liveness lease cannot extend the absolute
                # user-turn window, including after a companion restart.
                self.leases[key] = (self.clock() + LEASE_SECONDS, phase)
                self.window_ends[key] = row['deadline']
            return {'leaseSeconds': LEASE_SECONDS}

    def live(self, session):
        with self.lock:
            return any(s == session and expires > self.clock() for (s, _), (expires, _) in self.leases.items())

    def pause(self, paused):
        if type(paused) is not bool:
            raise ValueError('Invalid processing pause setting')
        with self.lock, self.connect() as db:
            self.paused = paused
            if paused and self.active:
                self.active['cancelled'] = True
            db.execute('UPDATE memory_processing SET paused=?', (int(paused),))
        return self.status()

    def allowed(self, session):
        with self.lock:
            now = self.clock()
            self.leases = {key: value for key, value in self.leases.items() if value[0] > now}
            return (not self.paused and
                    not any(phase == 'foreground' for _, phase in self.leases.values()) and
                    any(s == session and phase == 'tools' and self.window_ends[(s, owner)] > now
                        for (s, owner), (_, phase) in self.leases.items()))

    def open(self, job, session):
        with self.lock:
            if self.active or not self.allowed(session):
                raise BudgetDenied('Memory waits for an active tool window; foreground work has priority.')
            with self.connect() as db:
                db.execute('INSERT OR IGNORE INTO memory_budgets(id,seconds,tokens) VALUES (?,?,?)',
                           (job, JOB_SECONDS, JOB_TOKENS))
                row = db.execute('SELECT * FROM memory_budgets WHERE id=?', (job,)).fetchone()
                if row['seconds'] <= 0 or row['tokens'] <= 0 or row['failures'] >= 2 or row['status'] == 'stopped':
                    raise BudgetDenied('Memory job stopped: its budget or failure limit is exhausted.')
            token = uuid.uuid4().hex
            self.active = {'job': job, 'session': session, 'token': token}
            return token

    def close(self, token):
        with self.lock:
            if self.active and self.active['token'] == token:
                self.active = None

    def valid(self, token):
        with self.lock:
            return bool(self.active and not self.active.get('cancelled') and self.active['token'] == token and self.allowed(self.active['session']))

    def reserve(self, input_bytes, requested_output=None):
        """Charge a conservative token upper bound, including prompt processing.

        UTF-8 bytes upper-bound text tokens for the pinned local tokenizer. The
        gateway separately bounds the entire JSON body and rejects nontext input.
        Unknown outcomes keep the full reservation; successful usage can refund
        unused capacity. Retries necessarily pass admission again.
        """
        with self.lock:
            if not self.active or not self.valid(self.active['token']):
                raise BudgetDenied('No active memory processing window.')
            with self.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                row = db.execute('SELECT * FROM memory_budgets WHERE id=?', (self.active['job'],)).fetchone()
                output = min(CALL_OUTPUT_TOKENS, requested_output or CALL_OUTPUT_TOKENS,
                             row['tokens'] - input_bytes)
                seconds = min(CALL_SECONDS, row['seconds'])
                if output < 64 or seconds <= 0 or row['failures'] >= 2 or row['status'] == 'stopped':
                    raise BudgetDenied('Memory processing budget exhausted; previous memory is preserved.')
                tokens = input_bytes + output
                db.execute('UPDATE memory_budgets SET seconds=seconds-?,tokens=tokens-?,calls=calls+1 WHERE id=?',
                           (seconds, tokens, self.active['job']))
            return {**self.active, 'seconds': seconds, 'tokens': tokens, 'output': output,
                    'started': self.clock(), 'deadline': self.clock() + seconds}

    def settle(self, reservation, usage=None, failed=False):
        # A missing/invalid usage record is never grounds for a token refund.
        refund = reservation['tokens'] - usage if type(usage) is int and usage >= 0 else 0
        elapsed = max(0, self.clock() - reservation['started'])
        with self.lock, self.connect() as db:
            db.execute('UPDATE memory_budgets SET seconds=seconds+?,tokens=tokens+?,failures=failures+? WHERE id=?',
                       (reservation['seconds'] - elapsed, refund, int(failed), reservation['job']))
            db.execute("UPDATE memory_budgets SET status='stopped' WHERE id=? AND (failures>=2 OR seconds<=0 OR tokens<=0)",
                       (reservation['job'],))

    def status(self):
        with self.lock, self.connect() as db:
            return {'paused': self.paused, 'active': bool(self.active),
                    'stopped': db.execute("SELECT count(*) FROM memory_budgets WHERE status='stopped'").fetchone()[0]}
