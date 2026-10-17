# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Offline SQLite merge inside the Node owner's unpublished transaction stage.

No service objects, HTTP clients, engine stages or model work are constructed.
The exact original databases remain in the checked source archive.
"""
import hashlib
from collections import defaultdict
from bisect import bisect_right
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import time
import uuid
sys.path.insert(0, str(Path(__file__).resolve().parent))
from memory.dual import DualMemory

PROMPT = {
 'improvement': 'singleton content revision', 'library': 'singleton revision',
 'prompts': 'id name content revision updatedAt', 'imports': 'source sourceId digest promptId',
 'requests': 'id digest result', 'retired_prompt_requests': 'id digest'}
DUAL = {
 'settings': 'id enabled person', 'sessions': 'id person project', 'skipped': 'session event_id',
 'events': 'seq session event_id role mode content status created digest', 'event_scopes': 'seq kind scope',
 'projections': 'kind scope revision cursor value token lease until_seq failures retry',
 'revisions': 'kind scope revision cursor value created', 'hindsight_destination': 'id endpoint',
 'hindsight_banks': 'kind scope bank ready cursor snapshot updated',
 'hindsight_outbox': 'id bank through_seq body status attempts retry',
 'memory_processing': 'id paused', 'memory_windows': 'owner session deadline closed boot',
 'memory_budgets': 'id seconds tokens calls failures status', 'memory_eligible': 'seq job',
 'memory_jobs': 'id session events stages phase status reason attempt'}
MANUAL = {'configuration': 'singleton revision value', 'operations': 'id request_id digest endpoint bank scope document content provenance status created'}


def database(path, schema, writable=False):
    path = Path(path)
    if any(Path(str(path) + tail).exists() for tail in ('-wal', '-shm', '-journal')):
        raise ValueError('Recover and cleanly stop SQLite journals before consolidation.')
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 2 * 1024**3:
        raise ValueError('A bounded regular companion database is required.')
    db = sqlite3.connect(path if writable else path.as_uri() + '?mode=ro&immutable=1', uri=not writable)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA trusted_schema=OFF')
    deadline = time.monotonic() + 30
    db.set_progress_handler(lambda: int(time.monotonic() > deadline), 10000)
    try:
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Companion database integrity could not be verified.')
        objects = list(db.execute("SELECT type,name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"))
        tables = {r['name'] for r in objects if r['type'] == 'table'}
        expected = set(schema)
        if schema is PROMPT:
            expected.discard('retired_prompt_requests')
        if not expected <= tables or tables - set(schema) or any(r['type'] in ('view', 'trigger') for r in objects):
            raise ValueError('Companion database schema needs an explicit migration adapter.')
        for table in tables:
            if [r['name'] for r in db.execute('PRAGMA table_info("' + table + '")')] != schema[table].split():
                raise ValueError('Companion database columns need an explicit migration adapter.')
            if db.execute('SELECT count(*) FROM "' + table + '"').fetchone()[0] > 100000:
                raise ValueError('Companion table exceeds 100,000 rows.')
        if writable:
            db.execute('PRAGMA synchronous=FULL')
        return db
    except BaseException:
        db.close()
        raise


def rows(db, table):
    return [dict(r) for r in db.execute('SELECT * FROM "' + table + '"')]


def put(db, table, row, keys):
    old = db.execute('SELECT * FROM "' + table + '" WHERE ' + ' AND '.join('"'+k+'"=?' for k in keys), [row[k] for k in keys]).fetchone()
    if old:
        if dict(old) != row:
            raise ValueError('Conflicting companion record in ' + table + '; originals were preserved.')
        return False
    db.execute('INSERT INTO "' + table + '" (' + ','.join('"'+k+'"' for k in row) + ') VALUES (' + ','.join('?' for _ in row) + ')', list(row.values()))
    return True


def prompts(source, target, cut):
    a, b = database(source/'prompts.sqlite3', PROMPT), database(target/'prompts.sqlite3', PROMPT, True)
    aliases, imported = {}, 0
    try:
        with b:
            b.execute('CREATE TABLE IF NOT EXISTS retired_prompt_requests (id TEXT PRIMARY KEY, digest TEXT NOT NULL)')
            revision = b.execute('SELECT revision FROM library WHERE singleton=1').fetchone()[0]
            for row in rows(a, 'prompts'):
                if not re.fullmatch('[a-zA-Z0-9_-]{1,128}', row['name']) or not isinstance(row['content'], str) or not row['content'].strip() or len(row['content']) > 32000:
                    raise ValueError('Invalid source prompt.')
                same = b.execute('SELECT id FROM prompts WHERE name=? AND content=?', (row['name'], row['content'])).fetchone()
                if same:
                    aliases[row['id']] = same['id']; continue
                original = row['id']
                if b.execute('SELECT 1 FROM prompts WHERE id=?', (original,)).fetchone():
                    row['id'] = str(uuid.uuid5(uuid.NAMESPACE_URL, cut + ':' + original))
                base, number = row['name'], 1
                while b.execute('SELECT 1 FROM prompts WHERE name=?', (row['name'],)).fetchone():
                    number += 1; row['name'] = base[:105] + '-imported-' + str(number)
                revision += 1; row['revision'] = revision
                put(b, 'prompts', row, ['id']); aliases[original] = row['id']; imported += 1
            if b.execute('SELECT count(*) FROM prompts').fetchone()[0] > 1000 or b.execute('SELECT coalesce(sum(length(cast(content AS BLOB))),0) FROM prompts').fetchone()[0] > 500000:
                raise ValueError('Combined prompt library exceeds its existing bounds.')
            b.execute('UPDATE library SET revision=? WHERE singleton=1', (revision,))
            for row in rows(a, 'imports'):
                row['promptId'] = aliases.get(row['promptId'], row['promptId']); put(b, 'imports', row, ['source', 'sourceId', 'digest'])
            requests = rows(a, 'requests')
            if a.execute("SELECT 1 FROM sqlite_master WHERE name='retired_prompt_requests'").fetchone():
                requests += rows(a, 'retired_prompt_requests')
            for row in requests:
                old = b.execute('SELECT digest FROM requests WHERE id=?', (row['id'],)).fetchone()
                if old:
                    if old['digest'] != row['digest']:
                        raise ValueError('A source prompt request ID conflicts with the target.')
                else:
                    put(b, 'retired_prompt_requests', {k: row[k] for k in ('id','digest')}, ['id'])
            improvement_differs = a.execute('SELECT content FROM improvement').fetchone()[0] != b.execute('SELECT content FROM improvement').fetchone()[0]
            return {'imported': imported, 'aliases': aliases, 'sourceImprovementArchived': improvement_differs, 'targetImprovementPreserved': True, 'sourceCommittedRequestsRetired': len(requests)}
    finally:
        a.close(); b.close()


def engine(data):
    path = data/'hindsight.json'
    if not path.exists(): return None
    value = json.loads(path.read_text())
    return (value.get('endpoint'), value.get('apiKey', ''))


def memory(source, target, map_default):
    a, b = database(source/'dual-memory.sqlite3', DUAL), database(target/'dual-memory.sqlite3', DUAL, True)
    sequences, imported = {}, 0
    try:
        source_person = a.execute('SELECT person FROM settings WHERE id=1').fetchone()[0]
        target_person = b.execute('SELECT person FROM settings WHERE id=1').fetchone()[0]
        person = lambda p: target_person if map_default and p == source_person else p
        scopes = {}
        for row in rows(a, 'sessions'):
            old = DualMemory.scopes(None, row); new = DualMemory.scopes(None, {**row, 'person': person(row['person'])})
            for before, after in zip(old, new): scopes[before] = after
        def scope(kind, value): return scopes.get((kind,value), (kind,value))
        source_events = {r['seq']:r for r in rows(a, 'events')}
        source_membership = {(r['seq'],r['kind'],r['scope']) for r in rows(a,'event_scopes')}
        membership_by_seq=defaultdict(set);scope_events=defaultdict(list)
        for seq,kind,value in source_membership:
            membership_by_seq[seq].add((seq,kind,value));scope_events[(kind,value)].append(seq)
        sessions = {r['id']:r for r in rows(a, 'sessions')}
        for seq, row in source_events.items():
            expected = hashlib.sha256(json.dumps([row[k] for k in ('role','mode','content','status')]).encode()).hexdigest()
            if row['session'] not in sessions or expected != row['digest'] or row['role'] not in ('user','assistant') or row['mode'] not in ('text','voice') or row['status'] not in ('complete','interrupted','error'):
                raise ValueError('Invalid source memory transcript identity or digest.')
            if {(seq,*s) for s in DualMemory.scopes(None, sessions[row['session']])} != membership_by_seq[seq]:
                raise ValueError('Source memory transcript scopes do not match their immutable binding.')
        if any(r[0] not in source_events for r in source_membership): raise ValueError('Orphan memory source scope.')
        bank_rows = rows(a, 'hindsight_banks')
        if map_default and source_person != target_person and (a.execute('SELECT 1 FROM memory_jobs LIMIT 1').fetchone() or a.execute('SELECT 1 FROM hindsight_outbox LIMIT 1').fetchone()):
            raise ValueError('Processing receipts require a bank migration before person mapping.')
        destination=lambda db: [r['endpoint'] for r in db.execute('SELECT endpoint FROM hindsight_destination')]
        if any(r['ready'] or r['cursor'] or json.loads(r['snapshot']) for r in bank_rows) and (engine(source) != engine(target) or destination(a) != destination(b)):
            raise ValueError('Processed Hindsight banks require the same engine destination or an explicit bank migration.')
        for row in bank_rows:
            if scope(row['kind'],row['scope']) != (row['kind'],row['scope']) and (row['ready'] or row['cursor'] or json.loads(row['snapshot'])):
                raise ValueError('Processed memory identities need a bank migration before person mapping.')
        with b:
            for row in sessions.values(): put(b,'sessions',{**row,'person':person(row['person'])},['id'])
            for _, row in sorted(source_events.items()):
                if b.execute('SELECT 1 FROM skipped WHERE session=? AND event_id=?',(row['session'],row['event_id'])).fetchone(): raise ValueError('Source memory conflicts with a target capture-off tombstone.')
                old = b.execute('SELECT * FROM events WHERE session=? AND event_id=?',(row['session'],row['event_id'])).fetchone()
                if old:
                    if any(old[k] != row[k] for k in ('role','mode','content','status','digest')): raise ValueError('Conflicting memory event identity.')
                    sequences[row['seq']] = old['seq']
                else:
                    value = {k:v for k,v in row.items() if k != 'seq'}
                    b.execute('INSERT INTO events ('+','.join(value)+') VALUES ('+','.join('?' for _ in value)+')',list(value.values()))
                    sequences[row['seq']] = b.execute('SELECT last_insert_rowid()').fetchone()[0]; imported += 1
                for kind, value in DualMemory.scopes(None, sessions[row['session']]):
                    kind, value = scope(kind,value); put(b,'event_scopes',{'seq':sequences[row['seq']],'kind':kind,'scope':value},['seq','kind'])
            for row in rows(a,'skipped'):
                if b.execute('SELECT 1 FROM events WHERE session=? AND event_id=?',(row['session'],row['event_id'])).fetchone(): raise ValueError('Source capture-off tombstone conflicts with a retained target event.')
                put(b,'skipped',row,['session','event_id'])
            cursor_indexes={}
            def cursor(old, kind, value):
                key=(kind,value)
                if key not in cursor_indexes:
                    originals=sorted(scope_events[key]);prefix=[0];suffix=[float('inf')]*(len(originals)+1)
                    for seq in originals:prefix.append(max(prefix[-1],sequences[seq]))
                    for i in range(len(originals)-1,-1,-1):suffix[i]=min(suffix[i+1],sequences[originals[i]])
                    cursor_indexes[key]=(originals,prefix,suffix)
                originals,prefix,suffix=cursor_indexes[key];i=bisect_right(originals,old);through=prefix[i]
                if suffix[i]<=through:raise ValueError('Nonmonotonic shared memory cursor requires an explicit adapter.')
                return through
            def projection(row):
                kind, old_scope = row['kind'],row['scope'];value=json.loads(row['value'])
                for item in value.get('items',[]):
                    refs=item.get('sources',[])
                    if any((seq,kind,old_scope) not in source_membership for seq in refs): raise ValueError('Memory projection has a foreign source.')
                    if refs:item['sources']=[sequences[seq] for seq in refs]
                return {**row,'kind':scope(kind,old_scope)[0],'scope':scope(kind,old_scope)[1],'cursor':cursor(row['cursor'],kind,old_scope),'value':json.dumps(value,ensure_ascii=False)}
            for row in rows(a,'projections'):
                value=projection(row);value.update(token=None,lease=0,until_seq=0)
                old=b.execute('SELECT * FROM projections WHERE kind=? AND scope=?',(value['kind'],value['scope'])).fetchone()
                if old and not row['revision'] and not row['cursor'] and not json.loads(row['value']).get('items') and not json.loads(row['value']).get('summary'): continue
                if old and not old['revision'] and not old['cursor'] and not json.loads(old['value']).get('items') and not json.loads(old['value']).get('summary'):
                    b.execute('DELETE FROM projections WHERE kind=? AND scope=?',(value['kind'],value['scope']))
                put(b,'projections',value,['kind','scope'])
            for row in rows(a,'revisions'): put(b,'revisions',projection(row),['kind','scope','revision'])
            for row in bank_rows:
                if scope(row['kind'],row['scope']) != (row['kind'],row['scope']): continue  # Only never-created empty banks may remap.
                value={**row,'cursor':cursor(row['cursor'],row['kind'],row['scope'])};put(b,'hindsight_banks',value,['kind','scope'])
            for row in rows(a,'hindsight_outbox'):
                # Preserve engine-facing body/IDs; it is an historical receipt,
                # not an instruction to drain an old pending outbox.
                value={**row,'status':row['status'] if row['status'] in ('completed','failed','stopped') else 'stopped'};put(b,'hindsight_outbox',value,['id'])
            source_jobs=rows(a,'memory_jobs')
            for row in source_jobs:
                if row['session'] not in sessions:raise ValueError('Foreign memory processing job.')
                for event in json.loads(row['events']):
                    old=source_events.get(event.get('seq'))
                    if not old or old['session']!=row['session'] or any(event.get(k)!=old[k] for k in ('digest','content','role','mode','status')):raise ValueError('Processing job has an invalid original transcript reference.')
                # Keep original engine document/idempotency IDs, phases, payloads
                # and charges. New journal sequence numbers live in the receipt.
                value={**row}
                if value['status'] not in ('completed','stopped'):
                    value.update(status='stopped',reason='Imported processing receipt; inspect the original outcome before an explicit retry.')
                put(b,'memory_jobs',value,['id'])
            jobs={r['id'] for r in source_jobs}
            for row in rows(a,'memory_budgets'):
                if row['id'] not in jobs:raise ValueError('Memory budget has no source job.')
                put(b,'memory_budgets',row,['id'])
            for row in rows(a,'memory_eligible'):
                if row['seq'] not in sequences:raise ValueError('Processing eligibility has no source transcript.')
                if row['job'] is not None:
                    if row['job'] not in jobs:raise ValueError('Processing eligibility has no source job.')
                    put(b,'memory_eligible',{**row,'seq':sequences[row['seq']]},['seq'])
            # Neither activity windows nor unassigned eligibility is imported.
            # Historical processing remains the existing explicit interval action.
        return {'importedEvents':imported,'sequences':sequences,'personMapping':{'source':source_person,'target':person(source_person)},'activityWindowsArchived':a.execute('SELECT count(*) FROM memory_windows').fetchone()[0],'unassignedEligibilityArchived':a.execute('SELECT count(*) FROM memory_eligible WHERE job IS NULL').fetchone()[0],'processingJobs':len(source_jobs),'targetCaptureAndProcessingSettingsPreserved':True}
    finally:
        a.close(); b.close()


def manual(source,target):
    a,b=database(source/'memory.sqlite3',MANUAL),database(target/'memory.sqlite3',MANUAL,True)
    try:
        incoming=a.execute('SELECT value FROM configuration').fetchone()[0];current=b.execute('SELECT value FROM configuration').fetchone()[0]
        if json.loads(incoming).get('enabled') and json.loads(incoming)!=json.loads(current):raise ValueError('Configured manual memory needs an explicit destination mapping.')
        with b:
            for row in rows(a,'operations'):put(b,'operations',row,['id'])
        return {'sourceOperations':a.execute('SELECT count(*) FROM operations').fetchone()[0],'targetConfigurationPreserved':True}
    finally:a.close();b.close()


def merge(source,target,cut,map_default):
    source,target=Path(source),Path(target)
    result={'schema':'augmentor-shared-profile-merge/1','prompts':prompts(source,target,cut),'memory':memory(source,target,map_default),'manualMemory':manual(source,target)}
    for name,schema in [('prompts.sqlite3',PROMPT),('dual-memory.sqlite3',DUAL),('memory.sqlite3',MANUAL)]:
        check=database(target/name,schema);check.close()
    maps=target/'shared-imports'/cut/'memory-sequences.json'
    maps.write_text(json.dumps({'schema':'augmentor-memory-sequence-map/1','sourceStateSha256':cut,'sequences':result['memory'].pop('sequences')},sort_keys=True)+'\n');os.chmod(maps,0o600)
    return result


def validate(data):
    """Read-only schema/integrity qualification, without constructing services."""
    data=Path(data)
    for name,schema in [('prompts.sqlite3',PROMPT),('dual-memory.sqlite3',DUAL),('memory.sqlite3',MANUAL)]:
        check=database(data/name,schema)
        check.close()
    for name in ['hindsight.json','hindsight-installation.json']:
        if (data/name).exists() and not isinstance(json.loads((data/name).read_text()),dict):
            raise ValueError('Engine configuration must be a JSON object.')
    return {'schema':'augmentor-shared-databases-validation/1','databases':3,'readOnly':True}


if __name__=='__main__':
    value=json.load(sys.stdin)
    if value.get('action')=='validate':
        print(json.dumps(validate(value['data'])))
    else:
        print(json.dumps(merge(value['source'],value['target'],value['sha256'],value['mapDefaultPerson'])))
