# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Durable update progress; a record never authorizes execution or replay.

The caller supplies already verified current/recovery and proposed artifacts.
Hashes here bind the record to that decision; they do not establish publisher
trust. A new coordinator may inspect an interrupted record but cannot resume
its commands using saved PIDs. It must rediscover live processes and selection.
"""
from copy import deepcopy
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import secrets

from platform_adapters import locks
from platform_adapters.private_files import atomic_json, descriptor, read_json, require_directory, replace_file

SCHEMA = 'augmentor-update/1'
PHASES = ('verified', 'preparing', 'prepared', 'draining', 'drained',
          'installer-ready', 'apply-intent', 'apply-acknowledged', 'installed', 'healthy', 'complete')
STEP_PHASES = ('commit-intent', 'commit-acknowledged', 'commit-unknown', 'exited')


def artifact(value):
    fields = {'version', 'sourceCommit', 'target', 'channel', 'sha256', 'dataSchema', 'readableDataSchemas'}
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError('An exact release and retained recovery identity are required.')
    for name, pattern in (
        ('version', r'\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?'), ('sourceCommit', r'[a-f0-9]{40}'),
        ('sha256', r'[a-f0-9]{64}'), ('target', r'(?:windows|linux|macos)-(?:x64|arm64)'),
        ('channel', r'[a-z][a-z0-9-]{0,31}')):
        if not isinstance(value[name], str) or not re.fullmatch(pattern, value[name]):
            raise ValueError('Invalid release identity field: '+name)
    readable = value['readableDataSchemas']
    if (type(value['dataSchema']) is not int or value['dataSchema'] < 1 or
            not isinstance(readable, list) or not 1 <= len(readable) <= 16 or
            any(type(item) is not int or item < 1 for item in readable) or
            len(set(readable)) != len(readable) or value['dataSchema'] not in readable):
        raise ValueError('Invalid release data compatibility.')
    return deepcopy(value)


def validate(record):
    if (not isinstance(record, dict) or set(record) != {
            'schema', 'id', 'source', 'target', 'phase', 'revision', 'updatedAt', 'steps'} or
            record['schema'] != SCHEMA or not isinstance(record['id'], str) or
            not re.fullmatch('[a-f0-9]{48}', record['id']) or record['phase'] not in PHASES or
            type(record['revision']) is not int or not 0 <= record['revision'] <= 256 or
            not isinstance(record['updatedAt'], str) or len(record['updatedAt']) > 40):
        raise ValueError('The update record is invalid. Preserve it for recovery.')
    before, after = artifact(record['source']), artifact(record['target'])
    if (before['target'] != after['target'] or before['channel'] != after['channel'] or
            before['dataSchema'] not in after['readableDataSchemas'] or
            after['dataSchema'] not in before['readableDataSchemas']):
        raise ValueError('This update needs an explicit platform, channel or data migration plan.')
    steps = record['steps']
    if not isinstance(steps, list) or len(steps) > 192:
        raise ValueError('The update shutdown record is invalid.')
    states = {}
    for step in steps:
        if (not isinstance(step, dict) or set(step) != {'participant', 'pid', 'kind', 'phase'} or
                type(step['participant']) is not int or not 0 <= step['participant'] < 64 or
                type(step['pid']) is not int or not 0 < step['pid'] <= 0xffffffff or
                not isinstance(step['kind'], str) or not re.fullmatch('[A-Za-z][A-Za-z0-9_]{0,63}', step['kind']) or
                step['phase'] not in STEP_PHASES):
            raise ValueError('The update component record is invalid.')
        key = step['participant']; old = states.get(key)
        if old is None:
            if step['phase'] != 'commit-intent' or (states and next(reversed(states.values()))['phase'] != 'exited'):
                raise ValueError('The update shutdown order is invalid.')
        elif ((old['pid'], old['kind']) != (step['pid'], step['kind']) or
              (old['phase'], step['phase']) not in (
                  ('commit-intent', 'commit-acknowledged'), ('commit-intent', 'commit-unknown'),
                  ('commit-acknowledged', 'exited'), ('commit-unknown', 'exited'))):
            raise ValueError('An update shutdown attempt cannot be replayed.')
        states[key] = step
    if steps and PHASES.index(record['phase']) < PHASES.index('draining'):
        raise ValueError('The update phase precedes its shutdown record.')
    if PHASES.index(record['phase']) >= PHASES.index('drained') and any(row['phase'] != 'exited' for row in states.values()):
        raise ValueError('The update contains an unobserved process exit.')
    return record


def recovery_action(record):
    """Read-only classification, never a process command or permission to apply."""
    phase = validate(record)['phase']
    if phase == 'complete': return 'complete'
    if phase in ('installed', 'healthy'): return 'verify-local-health'
    if PHASES.index(phase) >= PHASES.index('apply-intent'): return 'inspect-installation'
    if phase in ('draining', 'drained', 'installer-ready'): return 'inspect-stopped-components'
    return 'release-reservations'


class UpdateJournal:
    """One writer, one attempt; close never erases or completes an update.

    The record directory must be outside the replaceable application. Existing
    records are refused, including completed ones: retention/recovery owns their
    archival and the decision to start a later transaction.
    """
    def __init__(self, directory, source, target):
        self.directory = require_directory(Path(directory))
        self.path = self.directory/'active.json'
        self.fd = None; self.record = None; self.uncertain = False; self.participants = []
        try:
            self.fd = descriptor(self.directory/'writer.lock', writable=True, create=True)
            locks.flock(self.fd, locks.LOCK_EX | locks.LOCK_NB)
            if self.path.exists() or self.path.is_symlink():
                validate(read_json(self.path))
                raise ValueError('An earlier update record requires recovery or archival. It was preserved.')
            self._write({'schema': SCHEMA, 'id': secrets.token_hex(24),
                'source': artifact(source), 'target': artifact(target), 'phase': 'verified',
                'revision': 0, 'updatedAt': '', 'steps': []})
        except BaseException:
            self.close(); raise

    def _write(self, record):
        if self.fd is None or self.uncertain:
            raise ValueError('The update writer is closed or has an unknown write outcome. Inspect the durable record.')
        record = deepcopy(record)
        record['updatedAt'] = datetime.now(timezone.utc).isoformat()
        validate(record)
        try: atomic_json(self.path, record)
        except BaseException:
            # A namespace flush can fail after replacement. No in-memory state
            # can decide which revision survived; do not retry this writer.
            self.uncertain = True
            raise
        self.record = record

    def advance(self, phase):
        current = self.record['phase']
        allowed = {
            'verified': ('preparing',), 'preparing': ('prepared',),
            'prepared': ('drained',), 'draining': ('drained',),
            'drained': ('installer-ready',), 'installer-ready': ('apply-intent',),
            'apply-intent': ('apply-acknowledged', 'installed'),
            'apply-acknowledged': ('installed',), 'installed': ('healthy',), 'healthy': ('complete',),
        }
        if phase not in allowed.get(current, ()):
            raise ValueError('The update phase cannot be skipped or repeated.')
        record = deepcopy(self.record); record['phase'] = phase; record['revision'] += 1
        self._write(record)

    def checkpoint(self, phase, participant):
        if self.record['phase'] not in ('prepared', 'draining'):
            raise ValueError('Shutdown checkpoints require a prepared update.')
        index = next((index for index, item in enumerate(self.participants) if item is participant), None)
        if index is None:
            if phase != 'commit-intent' or len(self.participants) >= 64:
                raise ValueError('An unobserved component cannot complete shutdown.')
            index = len(self.participants)
        record = deepcopy(self.record); record['phase'] = 'draining'; record['revision'] += 1
        record['steps'].append({'participant': index, 'pid': participant.pid,
                               'kind': type(participant).__name__, 'phase': phase})
        self._write(record)
        if index == len(self.participants): self.participants.append(participant)

    def close(self):
        if self.fd is not None: os.close(self.fd); self.fd = None

    @classmethod
    def complete_verified(cls, directory, source, target, verify_health):
        """Finalize an independently observed installation; never resume commands.

        The caller revalidates the retained artifacts and actual installed
        selection, and observes the real installer exit before calling. The
        bounded local-health callback must verify that selected build without
        provider/network availability being a prerequisite. This method does
        not infer those facts from recorded PIDs, versions or an installer log.
        It cannot drain, launch an installer, roll back or recover unknown apply.
        """
        if not callable(verify_health): raise ValueError('Independent local health verification is required.')
        journal = cls.__new__(cls)
        journal.directory = require_directory(Path(directory))
        journal.path = journal.directory/'active.json'
        journal.fd = None; journal.record = None; journal.uncertain = False; journal.participants = []
        try:
            journal.fd = descriptor(journal.directory/'writer.lock', writable=True, create=True)
            locks.flock(journal.fd, locks.LOCK_EX | locks.LOCK_NB)
            journal.record = validate(read_json(journal.path))
            if journal.record['source'] != artifact(source) or journal.record['target'] != artifact(target):
                raise ValueError('The independently verified release pair differs from this update. Its record was preserved.')
            if journal.record['phase'] not in ('apply-intent', 'apply-acknowledged', 'installed', 'healthy', 'complete'):
                raise ValueError('This transaction did not authorize installation. Its record was preserved.')
            # Give observers a copy; no callback may edit this durable history.
            if verify_health(deepcopy(journal.record)) is not True:
                raise ValueError('Installed local health was not verified. The update remains unresolved.')
            if journal.record['phase'] in ('apply-intent', 'apply-acknowledged'): journal.advance('installed')
            if journal.record['phase'] == 'installed': journal.advance('healthy')
            if journal.record['phase'] == 'healthy': journal.advance('complete')
            archive = journal.directory/('completed-'+journal.record['id']+'.json')
            if archive.exists() or archive.is_symlink():
                raise ValueError('An update archive already exists. Both records were preserved.')
            # Same-directory durable rename retains the finished record and
            # frees active.json only after completion. Failure is never retried
            # here: the next observer must inspect which name actually exists.
            replace_file(journal.path, archive)
            return archive
        finally: journal.close()

    def __enter__(self): return self
    def __exit__(self, *_): self.close()
