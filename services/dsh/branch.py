# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""One DSH Branch/Edit implementation, used by the desktop and browser adapters.

Only closed turn boundaries are supported by DSH's public fork API. The journal
is written before mutation: an acknowledgement lost in transit is never retried.
"""
import fcntl
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import urllib.request
from urllib.parse import urlsplit
import uuid


class BranchError(RuntimeError):
    pass


def history(call, session):
    events = {}; before = None; size = 0
    for _ in range(1000):
        params = {'sessionId': session, 'maxMessages': 50}
        if before is not None: params['beforeSeq'] = before
        page = call('session.history', params)
        rows = [r['event'] for r in page['events']]
        size += len(json.dumps(rows).encode())
        if size > 32*1024*1024: raise BranchError('This history exceeds the supported branch size.')
        for event in rows: events[event['seq']] = event
        if not page.get('hasMore'): return sorted(events.values(), key=lambda e: e['seq'])
        cursor = min((e['seq'] for e in rows), default=before)
        if cursor is None or (before is not None and cursor >= before):
            raise BranchError('DSH did not return a complete history. No new chat was created.')
        before = cursor
    raise BranchError('This history exceeds the supported branch size.')


def boundary(events, seq, mode):
    def human(event):
        return event['type']=='user/message' and event.get('data',{}).get('source',{}).get('kind','user')=='user'
    target = next((e for e in events if e['seq'] == seq), None)
    expected = 'user/message' if mode == 'edit' else 'assistant/message'
    if mode not in ('edit', 'reply') or target is None or target['type'] != expected:
        raise BranchError('Choose a message from this conversation.')
    if mode=='edit' and not human(target): raise BranchError('Choose a user input from this conversation.')
    starts = [e for e in events if e['type'] == 'turn/start' and e['seq'] <= seq]
    if not starts: raise BranchError('This message has no supported DSH turn boundary.')
    start = starts[-1]['seq']
    if mode == 'edit':
        users = [e for e in events if human(e)]
        if users[-1]['seq'] != seq: raise BranchError('Only the latest user input can be edited. Reload the chat.')
        # Steered inputs share a turn. Forking before such an input would also
        # erase the earlier user input; reject rather than silently changing it.
        if any(human(e) and start < e['seq'] < seq for e in events):
            raise BranchError('DSH cannot edit a steered input independently. Start a new chat with the revised request.')
        prior = [e for e in events if e['type'] == 'turn/end' and e['seq'] < start]
        return prior[-1]['seq'] if prior else None
    end = next((e for e in events if e['type'] == 'turn/end' and e['seq'] >= seq), None)
    if end is None: raise BranchError('Stop the current task before branching.')
    if any(p.get('type')=='toolCall' for p in target.get('data',{}).get('message',{}).get('content',[])):
        raise BranchError('Choose the final reply after its tools have finished.')
    next_start = next((e['seq'] for e in events if e['type'] == 'turn/start' and e['seq'] > end['seq']), float('inf'))
    if any(e['type'] in ('assistant/message', 'user/message', 'tool/call', 'tool/result') and seq < e['seq'] < next_start for e in events):
        raise BranchError('DSH branches after a complete turn. Choose the final reply after its tools have finished.')
    return end['seq']


def atomic(path, value):
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as file:
        json.dump(value, file); file.flush(); os.fsync(file.fileno()); name = file.name
    os.chmod(name, 0o600); os.replace(name, path)
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(descriptor)
    finally: os.close(descriptor)


def product_exact_fork(base, home):
    if __package__:
        from .setup import http
    else:
        from setup import http
    token=(Path(home)/'augmentor-product-token').read_text().strip()
    descriptor=http(base,'/api/augmentor-product')
    if descriptor.get('exactFork')!=1 or descriptor.get('homeId')!=hashlib.sha256(token.encode()).hexdigest():return None
    def create(params):
        result=http(base,'/api/augmentor-product',{'action':'exactFork',**params},{'x-augmentor-product-token':token})
        if not result.get('ok'):raise BranchError('DSH exact-prefix creation was not confirmed.')
        return result
    return create


def branch(call, params, *, surface, endpoint, state=None, exact_fork=None):
    source, target, seq, mode = (params.get(k) for k in ('sessionId', 'newSessionId', 'messageSeq', 'mode'))
    if not all(isinstance(s, str) and re.fullmatch(r'[A-Za-z0-9_.-]{1,160}', s) for s in (source, target)) or type(seq) is not int or seq < 0:
        raise BranchError('Invalid branch request.')
    if source == target: raise BranchError('The new chat must have a different identity.')
    directory = Path(state or os.environ.get('AUGMENTOR_SHARED_STATE', Path(os.environ.get('XDG_STATE_HOME', Path.home()/'.local/state'))/'augmentor'))/'dsh-branches'
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (directory/'lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        request = {'endpoint':endpoint, 'surface':surface, **{k:params[k] for k in ('sessionId','newSessionId','messageSeq','mode')}}
        path = directory/(hashlib.sha256((endpoint+'\0'+target).encode()).hexdigest()+'.json')
        record = json.loads(path.read_text()) if path.exists() else None
        if record:
            if record['request'] != request: raise BranchError('That branch identity already belongs to a different request.')
            if record.get('result'): return record['result']
            if not record.get('child'):
                raise BranchError('The earlier branch outcome is unknown. Check DSH chats before starting another branch; no request was replayed.')
        else:
            row = next((r for r in call('session.list', {})['items'] if r['sessionId'] == source), None)
            allowed = ('augmentor-linux','augmentor-linux-product') if surface == 'linux' else ('augmentor','augmentor-browser-product')
            if row is None or row.get('agentPreset') not in allowed:
                raise BranchError('This chat belongs to another Augmentor role.')
            preset=row['agentPreset']
            if row.get('running'): raise BranchError('Stop the current task before branching or editing.')
            events = history(call, source)
            at_seq = boundary(events, seq, mode)
            # DSH 0.1.5's fork includes records after the selected turn/end
            # until the next turn/start. A queued human input may live in that
            # interval. Refuse before creating a child rather than retaining
            # an input that Edit promises to replace.
            if at_seq is not None and exact_fork is None:
                for event in events:
                    if event['seq'] <= at_seq: continue
                    if event['type'] == 'turn/start': break
                    if event['type'] in ('user/message','agent/inbox/spliced'):
                        raise BranchError('DSH 0.1.5 cannot isolate this message: its fork would retain the next input. Start a new chat with the revised input. No child was created.')
            # A second snapshot detects changes made by another UI while paging.
            if history(call, source) != events:
                raise BranchError('The source chat changed. Reload it before branching.')
            selection = call('session.models', {'sessionId':source}).get('current')
            if not selection: raise BranchError('The source chat has no selected DSH model.')
            intent = hashlib.sha256(json.dumps([endpoint, source, seq, mode, events[-1]['seq']],sort_keys=True).encode()).hexdigest()
            for old in directory.glob('*.json'):
                previous = json.loads(old.read_text())
                if previous.get('intent') == intent and not previous.get('child'):
                    raise BranchError('An earlier branch of this message has an unknown outcome. Check DSH chats; it will not be replayed.')
            record = {'request':request, 'intent':intent, 'cwd':row['cwd'], 'agentPreset':preset, 'selection':selection}
            atomic(path, record)
            try:
                if at_seq is None:
                    created=call('session.create', {'sessionId':target, 'cwd':row['cwd'], 'agentPreset':preset})
                elif exact_fork is not None:
                    created=exact_fork({'surface':surface,'sessionId':source,'atSeq':at_seq,'expectedCursor':events[-1]['seq']})
                else:
                    created=call('session.fork', {'sessionId':source, 'atSeq':at_seq})
            except Exception as exc:
                raise BranchError('DSH did not confirm the new chat. The operation was recorded and will not be replayed. Check DSH chats.') from exc
            record['child'] = created['sessionId']; atomic(path, record)
        # A known child may safely finish setup after a lost setup response.
        call('session.selectModel', {'sessionId':record['child'], **record['selection']})
        result = {'sessionId':record['child'], 'cwd':record['cwd'], 'agentPreset':record['agentPreset'],
                  'selection':record['selection'], 'title':'Edited chat' if mode=='edit' else 'Branched chat'}
        record['result'] = result; atomic(path, record)
        return result


def main():
    os.umask(0o077)
    from setup import current
    base = (os.environ.get('DSH_AUGMENTOR_URL') or current().get('endpoint','http://127.0.0.1:3080')).rstrip('/')
    url = urlsplit(base)
    if url.scheme != 'http' or not ipaddress.ip_address(url.hostname or '').is_loopback or url.username or url.password or url.query or url.fragment:
        raise BranchError('DSH requires a numeric loopback HTTP endpoint.')
    from remote import client
    call=client(base,current().get('home')).call
    exact=product_exact_fork(base,current().get('home'))
    print(json.dumps(branch(call, json.loads(sys.stdin.read(65536)), surface='browser', endpoint=base,exact_fork=exact)))


if __name__ == '__main__':
    try: main()
    except Exception as exc:
        print(json.dumps({'error':str(exc)})); sys.exit(1)
