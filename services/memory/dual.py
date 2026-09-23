# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Local automatic relationship/work memory. Raw events and versioned projections.

Only trusted harness adapters bind sessions and submit transcript events. Models
can produce bounded projections, never choose the person/project or run tools.
"""
from contextlib import contextmanager
import hashlib
import json
import os
import re
from pathlib import Path
import sqlite3
import time
import uuid

PROTOCOL = 'augmentor-dual-memory/1'
KINDS = ('relationship', 'work')


def identifier(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 1024:
        raise ValueError('Invalid memory identity')
    return value


class DualMemory:
    def __init__(self, path, clock=time.time):
        self.path = Path(path)
        self.clock = clock
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY CHECK(id=1), enabled INTEGER NOT NULL, person TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, person TEXT NOT NULL, project TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS skipped (session TEXT NOT NULL, event_id TEXT NOT NULL, PRIMARY KEY(session,event_id));
                CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY AUTOINCREMENT, session TEXT NOT NULL, event_id TEXT NOT NULL, role TEXT NOT NULL, mode TEXT NOT NULL, content TEXT NOT NULL, status TEXT NOT NULL, created REAL NOT NULL, digest TEXT NOT NULL, UNIQUE(session,event_id));
                CREATE TABLE IF NOT EXISTS event_scopes (seq INTEGER NOT NULL, kind TEXT NOT NULL, scope TEXT NOT NULL, PRIMARY KEY(seq,kind));
                CREATE INDEX IF NOT EXISTS scope_events ON event_scopes(kind,scope,seq);
                CREATE TABLE IF NOT EXISTS projections (kind TEXT NOT NULL, scope TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 0, cursor INTEGER NOT NULL DEFAULT 0, value TEXT NOT NULL DEFAULT '{"summary":"","items":[]}', token TEXT, lease REAL NOT NULL DEFAULT 0, until_seq INTEGER NOT NULL DEFAULT 0, failures INTEGER NOT NULL DEFAULT 0, retry REAL NOT NULL DEFAULT 0, PRIMARY KEY(kind,scope));
                CREATE TABLE IF NOT EXISTS revisions (kind TEXT NOT NULL, scope TEXT NOT NULL, revision INTEGER NOT NULL, cursor INTEGER NOT NULL, value TEXT NOT NULL, created REAL NOT NULL, PRIMARY KEY(kind,scope,revision));
            ''')
            db.execute('INSERT OR IGNORE INTO settings VALUES (1,1,?)', ('person:' + uuid.uuid4().hex,))
        os.chmod(self.path, 0o600)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA synchronous=FULL')
        db.execute('PRAGMA secure_delete=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def session(self, db, session):
        row = db.execute('SELECT * FROM sessions WHERE id=?', (identifier(session),)).fetchone()
        if not row:
            raise ValueError('Memory session is not bound')
        return row

    def scopes(self, session):
        # Project projections are person-partitioned even if two profiles share a workspace.
        project = hashlib.sha256(json.dumps([session['person'], session['project']]).encode()).hexdigest()
        return [('relationship', session['person']), ('work', project)]

    def call(self, method, p):
        action = method.removeprefix('memory.dual.')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            config = dict(db.execute('SELECT enabled,person FROM settings').fetchone())
            if action == 'describe':
                return {'protocol': PROTOCOL, 'pid': os.getpid(), **config, 'events': db.execute('SELECT count(*) FROM events').fetchone()[0],
                        'pending': db.execute('SELECT count(*) FROM projections p WHERE EXISTS (SELECT 1 FROM event_scopes e WHERE e.kind=p.kind AND e.scope=p.scope AND e.seq>p.cursor)').fetchone()[0],
                        'failures': db.execute('SELECT coalesce(sum(failures),0) FROM projections').fetchone()[0]}
            if action == 'configure':
                enabled = p.get('enabled', bool(config['enabled']))
                if type(enabled) is not bool:
                    raise ValueError('Invalid memory setting')
                person = identifier(p.get('person', config['person']))
                db.execute('UPDATE settings SET enabled=?,person=?', (int(enabled), person))
                if not enabled:
                    db.execute('UPDATE projections SET token=NULL,lease=0')
                return {'enabled': enabled, 'person': person}
            if action == 'bind':
                sid = identifier(p.get('session'))
                existing = db.execute('SELECT * FROM sessions WHERE id=?', (sid,)).fetchone()
                if existing:
                    return dict(existing)
                # Stable OS profile is the default; never infer identity from a voice/name.
                person = identifier(p.get('person', config['person']))
                project = identifier(p.get('project') or str(Path(p.get('cwd') or Path.home()).expanduser().resolve()))
                db.execute('INSERT INTO sessions VALUES (?,?,?)', (sid, person, project))
                row = {'id': sid, 'person': person, 'project': project}
                for kind, scope in self.scopes(row):
                    db.execute('INSERT OR IGNORE INTO projections(kind,scope) VALUES (?,?)', (kind, scope))
                return row
            session = self.session(db, p.get('session'))
            scopes = self.scopes(session)
            if action == 'export':
                after = p.get('after', 0)
                if type(after) is not int or after < 0:
                    raise ValueError('Invalid export cursor')
                rows = [dict(r) for r in db.execute('SELECT e.* FROM events e JOIN event_scopes s ON s.seq=e.seq WHERE s.kind=? AND s.scope=? AND e.seq>? ORDER BY e.seq LIMIT 100', (*scopes[0], after))]
                return {'events': rows, 'next': rows[-1]['seq'] if rows else None}
            if action == 'append':
                rows = p.get('events')
                if not isinstance(rows, list) or len(rows) > 100:
                    raise ValueError('Invalid transcript batch')
                for row in rows:
                    eid = identifier(row.get('id'))
                    role, mode, content = row.get('role'), row.get('mode'), row.get('content')
                    status = row.get('status', 'complete')
                    if role not in ('user', 'assistant') or mode not in ('voice', 'text') or status not in ('complete', 'interrupted', 'error'):
                        raise ValueError('Invalid transcript provenance')
                    if not isinstance(content, str) or not content.strip() or len(content) > 200000:
                        raise ValueError('Invalid transcript content')
                    if not config['enabled']:
                        db.execute('INSERT OR IGNORE INTO skipped VALUES (?,?)', (session['id'], eid))
                        continue
                    if db.execute('SELECT 1 FROM skipped WHERE session=? AND event_id=?', (session['id'], eid)).fetchone():
                        continue
                    digest = hashlib.sha256(json.dumps([role, mode, content, status]).encode()).hexdigest()
                    old = db.execute('SELECT digest FROM events WHERE session=? AND event_id=?', (session['id'], eid)).fetchone()
                    if old:
                        if old['digest'] != digest:
                            raise ValueError('Transcript event ID reused with different content')
                        continue
                    seq = db.execute('INSERT INTO events(session,event_id,role,mode,content,status,created,digest) VALUES (?,?,?,?,?,?,?,?)',
                                     (session['id'], eid, role, mode, content, status, self.clock(), digest)).lastrowid
                    for kind, scope in scopes:
                        db.execute('INSERT INTO event_scopes VALUES (?,?,?)', (seq, kind, scope))
                return {'enabled': bool(config['enabled'])}
            if not config['enabled']:
                return {'enabled': False}
            if action == 'recall':
                result = {'enabled': True, 'person': session['person'], 'project': session['project']}
                for kind, scope in scopes:
                    row = db.execute('SELECT * FROM projections WHERE kind=? AND scope=?', (kind, scope)).fetchone()
                    result[kind] = {**json.loads(row['value']), 'revision': row['revision'], 'through': row['cursor']}
                # Recent unprocessed turns are a bounded fallback in this project only.
                rows = db.execute('SELECT e.* FROM events e JOIN event_scopes s ON s.seq=e.seq WHERE s.kind=? AND s.scope=? AND e.seq>? ORDER BY e.seq DESC LIMIT 6', (*scopes[1], result['work']['through'])).fetchall()
                result['recent'] = [{'seq': r['seq'], 'role': r['role'], 'mode': r['mode'], 'status': r['status'], 'content': r['content'][:700]} for r in reversed(rows)]
                return result
            if action == 'search':
                query = p.get('query')
                if not isinstance(query, str) or not query.strip() or len(query) > 4096:
                    raise ValueError('Invalid memory query')
                terms = list(dict.fromkeys(re.findall(r"[\w-]{3,}", query.lower())))[:20]
                result = {'enabled': True, 'relationship': [], 'work': []}
                if not terms:
                    return result
                clause = ' OR '.join('lower(value) LIKE ?' for _ in terms)
                for kind, scope in scopes:
                    rows = db.execute('SELECT value,revision FROM revisions WHERE kind=? AND scope=? AND (' + clause + ') ORDER BY revision DESC LIMIT 100', (kind, scope, *['%' + t + '%' for t in terms]))
                    seen = set()
                    candidates = []
                    for row in rows:
                        for item in json.loads(row['value'])['items']:
                            key = item['text'].lower()
                            if key in seen:
                                continue
                            seen.add(key)
                            score = sum(term in key for term in terms)
                            if score:
                                candidates.append((score, row['revision'], item))
                    result[kind] = [{**item, 'revision': revision, 'historical': True} for _, revision, item in sorted(candidates, key=lambda x: (x[0], x[1]), reverse=True)[:6]]
                return result
            if action == 'claim':
                now = self.clock()
                for kind, scope in scopes:
                    row = db.execute('SELECT * FROM projections WHERE kind=? AND scope=?', (kind, scope)).fetchone()
                    if row['lease'] > now or row['retry'] > now:
                        continue
                    events = []
                    size = 0
                    for event in db.execute('SELECT e.* FROM events e JOIN event_scopes s ON s.seq=e.seq WHERE s.kind=? AND s.scope=? AND e.seq>? ORDER BY e.seq LIMIT 20', (kind, scope, row['cursor'])):
                        # Preserve raw content in SQLite; oversized events are split into
                        # bounded pieces in the client before submission (see adapter).
                        item = {k: event[k] for k in ('seq', 'role', 'mode', 'content', 'status', 'created')}
                        if size + len(item['content']) > 24000 and events:
                            break
                        events.append(item)
                        size += len(item['content'])
                    if not events:
                        continue
                    token = uuid.uuid4().hex
                    db.execute('UPDATE projections SET token=?,lease=?,until_seq=? WHERE kind=? AND scope=?', (token, now + 120, events[-1]['seq'], kind, scope))
                    return {'job': {'token': token, 'kind': kind, 'revision': row['revision'], 'previous': json.loads(row['value']), 'events': events}}
                return {'job': None}
            if action in ('commit', 'fail'):
                token = identifier(p.get('token'))
                row = db.execute('SELECT * FROM projections WHERE token=?', (token,)).fetchone()
                if not row or (row['kind'], row['scope']) not in scopes or row['lease'] < self.clock():
                    raise ValueError('Memory job expired or superseded')
                if action == 'fail':
                    delay = min(300, 5 * 2 ** min(row['failures'], 6))
                    db.execute('UPDATE projections SET token=NULL,lease=0,failures=failures+1,retry=? WHERE token=?', (self.clock() + delay, token))
                    return {'retryAfter': delay}
                value = self.validate_projection(db, row, p.get('value'))
                raw = json.dumps(value, ensure_ascii=False)
                revision = row['revision'] + 1
                db.execute('INSERT INTO revisions VALUES (?,?,?,?,?,?)', (row['kind'], row['scope'], revision, row['until_seq'], raw, self.clock()))
                db.execute('UPDATE projections SET revision=?,cursor=until_seq,value=?,token=NULL,lease=0,failures=0,retry=0 WHERE token=?', (revision, raw, token))
                return {'revision': revision}
            raise ValueError('Unsupported dual memory operation')

    def validate_projection(self, db, row, value):
        if not isinstance(value, dict) or set(value) != {'summary', 'items'}:
            raise ValueError('Memory projection must contain summary and items')
        if not isinstance(value['summary'], str) or len(value['summary']) > 4000:
            raise ValueError('Memory summary is too long')
        items = value['items']
        if not isinstance(items, list) or len(items) > 24:
            raise ValueError('Memory projection has too many items')
        if value['summary'].strip() and not items:
            raise ValueError('A memory summary needs supporting items')
        for item in items:
            if not isinstance(item, dict) or set(item) != {'text', 'sources', 'state'}:
                raise ValueError('Invalid memory item')
            if not isinstance(item['text'], str) or not item['text'].strip() or len(item['text']) > 500 or item['state'] not in ('current', 'open', 'resolved', 'uncertain'):
                raise ValueError('Invalid memory assertion')
            sources = item['sources']
            if not isinstance(sources, list) or not 1 <= len(sources) <= 8 or any(type(s) is not int for s in sources):
                raise ValueError('Every memory assertion needs transcript sources')
            for source in sources:
                if source > row['until_seq'] or not db.execute('SELECT 1 FROM event_scopes WHERE seq=? AND kind=? AND scope=?', (source, row['kind'], row['scope'])).fetchone():
                    raise ValueError('Memory source is outside this scope')
        if len(json.dumps(value)) > 16000:
            raise ValueError('Memory projection exceeds context budget')
        return value
