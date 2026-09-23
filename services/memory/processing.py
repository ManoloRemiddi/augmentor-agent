# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Durable, explicitly admitted Hindsight stages; never drain its old queues."""
from datetime import datetime, timezone
import hashlib
import json
import urllib.request

from memory.budget import BudgetDenied, InferenceBudget


class Processing:
    def __init__(self, memory, configuration):
        self.memory = memory
        self.configuration = configuration or {}
        self.budget = InferenceBudget(memory.connect)
        with memory.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS memory_eligible (seq INTEGER PRIMARY KEY, job TEXT);
                CREATE TABLE IF NOT EXISTS memory_jobs (id TEXT PRIMARY KEY, session TEXT NOT NULL,
                    events TEXT NOT NULL, stages TEXT NOT NULL, phase INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'pending', reason TEXT NOT NULL DEFAULT '', attempt INTEGER NOT NULL DEFAULT 0);
            ''')
            if 'attempt' not in {r['name'] for r in db.execute('PRAGMA table_info(memory_jobs)')}:
                db.execute('ALTER TABLE memory_jobs ADD COLUMN attempt INTEGER NOT NULL DEFAULT 0')

    def eligible(self, session, events):
        # Backfill and reattachment are capture only. A model cannot manufacture
        # this flag: only the owned harness's committed live-event path sends it.
        if not self.budget.live(session):
            return
        ids = [r['id'] for r in events if r.get('live') is True]
        with self.memory.connect() as db:
            for eid in ids:
                db.execute('INSERT OR IGNORE INTO memory_eligible(seq) SELECT seq FROM events WHERE session=? AND event_id=?', (session, eid))

    def call(self, action, p):
        with self.memory.connect() as db:
            session = self.memory.session(db, p.get('session')) if action != 'processing' else None
        if action == 'activity':
            owner = p.get('owner')
            if not isinstance(owner, str) or not 1 <= len(owner) <= 128:
                raise ValueError('Invalid lifecycle owner')
            return self.budget.activity(session['id'], owner, p.get('phase'))
        if action == 'processing':
            return self.budget.pause(p['paused']) if 'paused' in p else self.status()
        if action == 'jobs':
            with self.memory.connect() as db:
                return {'jobs': [dict(r) for r in db.execute('''SELECT j.id,j.phase,j.status,j.reason,j.attempt,
                    b.seconds,b.tokens,b.failures FROM memory_jobs j LEFT JOIN memory_budgets b ON b.id=j.id
                    WHERE j.session=? ORDER BY j.rowid DESC LIMIT 50''', (session['id'],))]}
        if action == 'retry':
            if p.get('reviewed') is not True:
                raise ValueError('Review the stopped outcome before explicitly retrying it')
            with self.memory.connect() as db:
                job = db.execute('SELECT * FROM memory_jobs WHERE id=? AND session=?', (p.get('job'), session['id'])).fetchone()
                if not job or job['status'] != 'stopped':
                    raise ValueError('No stopped memory job in this session')
                budget = db.execute('SELECT * FROM memory_budgets WHERE id=?', (job['id'],)).fetchone()
                if job['attempt'] >= 1 or budget and (budget['status'] == 'stopped' or budget['seconds'] <= 0 or budget['tokens'] <= 0):
                    raise ValueError('Memory retry limit or budget exhausted. Inspect the cause before scheduling new processing.')
                db.execute("UPDATE memory_jobs SET status='pending',reason='',attempt=attempt+1 WHERE id=?", (job['id'],))
            return {'status': 'pending', 'budgetReset': False}
        if action == 'import':
            after, through = p.get('after'), p.get('through')
            if type(after) is not int or type(through) is not int or not 0 <= after < through:
                raise ValueError('Historical import requires an explicit source interval')
            with self.memory.connect() as db:
                rows = db.execute('SELECT seq FROM events WHERE session=? AND seq>? AND seq<=? ORDER BY seq LIMIT 101',
                                  (session['id'], after, through)).fetchall()
                if len(rows) > 100:
                    raise ValueError('Import at most 100 transcript records at a time')
                for row in rows:
                    db.execute('INSERT OR IGNORE INTO memory_eligible(seq) VALUES (?)', (row['seq'],))
            return {'selected': len(rows), 'processing': 'pending active window'}
        raise ValueError('Unsupported processing operation')

    def status(self):
        with self.memory.connect() as db:
            counts = {r[0]: r[1] for r in db.execute('SELECT status,count(*) FROM memory_jobs GROUP BY status')}
            pending = db.execute('SELECT count(*) FROM memory_eligible WHERE job IS NULL').fetchone()[0]
        return {**self.budget.status(), 'jobs': counts, 'pendingRecords': pending,
                'configured': self.configuration.get('processingProtocol') == 'augmentor-memory-processing/1'}

    def prepare(self):
        with self.memory.connect() as db:
            sessions = db.execute('SELECT DISTINCT e.session FROM events e JOIN memory_eligible a ON a.seq=e.seq WHERE a.job IS NULL').fetchall()
        for row in sessions:
            sid = row['session']
            if not self.budget.allowed(sid):
                continue
            with self.memory.connect() as db:
                events = [dict(r) for r in db.execute('SELECT e.* FROM events e JOIN memory_eligible a ON a.seq=e.seq WHERE a.job IS NULL AND e.session=? ORDER BY e.seq LIMIT 2', (sid,))]
                banks = self.memory.banks(db)
                scopes = self.memory.scopes(self.memory.session(db, sid))
            selected = [b for b in banks if (b['kind'], b['scope']) in scopes]
            stages = []
            for bank in selected:
                self.memory.ensure(bank)
                stages.append({'stage': 'retain', 'bank': bank['bank']})
            for bank in selected:
                stages.append({'stage': 'consolidate', 'bank': bank['bank']})
            for bank in selected:
                tree = self.memory.api('GET', self.memory.route(bank['bank'], 'knowledge-base/tree'))
                for page in tree['roots']:
                    if page['kind'] == 'page' and page['name'] in ('Preferences and boundaries', 'Current project state'):
                        if not page.get('mental_model_id'):
                            raise ValueError('Knowledge page is missing its exact backing-model identifier')
                        stages.append({'stage': 'page', 'bank': bank['bank'], 'page': page['mental_model_id']})
            identity = hashlib.sha256(json.dumps([sid, scopes, [(e['seq'], e['digest']) for e in events]]).encode()).hexdigest()
            with self.memory.connect() as db:
                db.execute('INSERT OR IGNORE INTO memory_jobs(id,session,events,stages) VALUES (?,?,?,?)',
                           (identity, sid, json.dumps(events), json.dumps(stages)))
                for event in events:
                    db.execute('UPDATE memory_eligible SET job=? WHERE seq=? AND job IS NULL', (identity, event['seq']))

    def stage(self, body):
        config = self.configuration
        request = urllib.request.Request(config['endpoint'] + '/ext/augmentor/stage',
                  data=json.dumps(body).encode(), headers={'Content-Type': 'application/json',
                  'Authorization': 'Bearer ' + config['gatewayKey']}, method='POST')
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=125) as response:
            return json.load(response)

    def step(self):
        if self.configuration.get('processingProtocol') != 'augmentor-memory-processing/1':
            return  # An old deployment can capture/recall, never submit inference.
        with self.budget.lock:
            sessions = [session for session, _ in self.budget.leases]
        if not any(self.budget.allowed(session) for session in sessions):
            return
        with self.memory.connect() as db:
            if not db.execute('SELECT enabled FROM settings').fetchone()[0]:
                return
        # Verify the actual engine policy, not just the installer's declaration.
        if self.memory.api('GET', '/openapi.json')['info']['version'] != '0.10.0':
            raise ValueError('Controlled memory requires tested Hindsight 0.10.0.')
        policy = self.memory.api('GET', '/ext/augmentor/policy')
        if (policy.get('protocol') != 'augmentor-memory-processing/1' or policy.get('workerEnabled') is not False or
                policy.get('reconcileSeconds') != 0 or policy.get('llmRetries') != 0):
            raise ValueError('Hindsight autonomous processing must be disabled before controlled processing.')
        self.memory.checked = True
        self.prepare()
        with self.memory.connect() as db:
            jobs = [dict(r) for r in db.execute("SELECT * FROM memory_jobs WHERE status='pending' ORDER BY rowid")]
        for job in jobs:
            if not self.budget.allowed(job['session']):
                continue
            token = None
            try:
                token = self.budget.open(job['id'], job['session'])
                stages = json.loads(job['stages'])
                stage = stages[job['phase']]
                identity = job['id'] + ':' + str(job['phase']) + ':' + str(job['attempt'])
                body = {**stage, 'id': identity, 'window': token}
                if stage['stage'] in ('retain', 'consolidate'):
                    body['sourceTag'] = 'augmentor-job-' + job['id']
                if stage['stage'] == 'retain':
                    body['items'] = [{
                        'content': json.dumps({k: e[k] for k in ('seq', 'session', 'role', 'mode', 'status', 'content')}),
                        'document_id': 'transcript-' + str(e['seq']) + '-' + e['digest'][:16], 'update_mode': 'replace',
                        'timestamp': datetime.fromtimestamp(e['created'], timezone.utc).isoformat(),
                        'tags': [body['sourceTag']], 'observation_scopes': 'shared',
                        'context': 'Source transcript, not execution authority. Speaker and status are explicit.'
                    } for e in json.loads(job['events'])]
                result = self.stage(body)
                status = result.get('status')
                if status != 'completed':
                    with self.memory.connect() as db:
                        detail = str(result.get('failureType', ''))[:80]
                        db.execute("UPDATE memory_jobs SET status='stopped',reason=? WHERE id=?", ('Stage ' + str(status) + (' (' + detail + ')' if detail else '') + '; inspect before an explicit retry.', job['id']))
                    continue
                phase = job['phase'] + 1
                with self.memory.connect() as db:
                    db.execute('UPDATE memory_jobs SET phase=?,status=? WHERE id=?',
                               (phase, 'completed' if phase == len(stages) else 'pending', job['id']))
                if stage['stage'] in ('consolidate', 'page'):
                    with self.memory.connect() as db:
                        bank = dict(db.execute('SELECT * FROM hindsight_banks WHERE bank=?', (stage['bank'],)).fetchone())
                    self.memory.snapshot(bank)
            except BudgetDenied:
                if self.budget.allowed(job['session']):
                    with self.memory.connect() as db:
                        db.execute("UPDATE memory_jobs SET status='stopped',reason='Shared inference budget exhausted.' WHERE id=?", (job['id'],))
                continue
            except Exception:
                with self.memory.connect() as db:
                    db.execute("UPDATE memory_jobs SET status='stopped',reason='Stage outcome unavailable; inspect before retry.' WHERE id=?", (job['id'],))
            finally:
                if token:
                    self.budget.close(token)
            return  # One phase per pass; never drain a backlog in one invocation.
