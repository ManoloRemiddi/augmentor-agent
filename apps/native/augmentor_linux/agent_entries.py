# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Desktop references to harness agents; definitions and conversations stay in DSH."""
from contextlib import contextmanager, nullcontext
from copy import deepcopy
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
import uuid
from .instances import validate_name, current_name


def registry_path():
    return Path(os.environ.get('AUGMENTOR_AGENT_ENTRIES', Path(os.environ.get('XDG_CONFIG_HOME', Path.home()/'.config'))/'augmentor/agents.json'))


def defaults():
    return {'version': 1, 'revision': 0, 'entries': [
        {'id': 'main', 'name': 'First agent', 'preset': None, 'cwd': None, 'model': None, 'stateKey': None},
        {'id': 'secondary', 'name': 'Second agent', 'preset': None, 'cwd': None, 'model': None, 'stateKey': None}],
        'retained': [], 'removed': []}


def validate(entry):
    validate_name(entry['id'])
    name=entry.get('name')
    if not isinstance(name,str) or not name.strip() or len(name)>80 or any(ord(c)<32 for c in name):
        raise ValueError('Enter an agent name of 1–80 characters.')
    preset=entry.get('preset')
    if preset is not None and (not isinstance(preset,str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}',preset)):
        raise ValueError('Select a valid DSH agent.')
    cwd=entry.get('cwd')
    if cwd is not None and (not isinstance(cwd,str) or not Path(cwd).is_absolute()):
        raise ValueError('Choose an absolute working folder.')
    if preset and not cwd:raise ValueError('Choose a working folder for this DSH agent.')
    model=entry.get('model')
    if model is not None and (not isinstance(model,dict) or any(not isinstance(model.get(k),str) or not model[k] or len(model[k])>256 for k in ('provider','model'))):
        raise ValueError('Choose a model from DSH.')
    key=entry.get('stateKey')
    if key is not None and (not isinstance(key,str) or not re.fullmatch(r'[a-f0-9]{32}',key)):raise ValueError('Invalid conversation binding.')
    return {k:deepcopy(entry.get(k)) for k in ('id','name','preset','cwd','model','stateKey')}


def read():
    try:value=json.loads(registry_path().read_text())
    except FileNotFoundError:return defaults()
    if value.get('version')!=1 or type(value.get('revision')) is not int or not isinstance(value.get('entries'),list) or not isinstance(value.get('retained'),list) or not isinstance(value.get('removed'),list):
        raise ValueError('The desktop Agents registry is invalid; restore its backup.')
    value['entries']=[validate(e) for e in value['entries']]
    if len({e['id'] for e in value['entries']})!=len(value['entries']):raise ValueError('Duplicate desktop agent IDs.')
    for name in value['removed']:validate_name(name)
    for entry in value['retained']:validate(entry)
    return value


def entries():return read()['entries']


def get(name=None):
    name=name or current_name();value=read()
    if name in value['removed']:raise ValueError('This desktop agent was removed. Add an entry in Settings → Agents.')
    return next((e for e in value['entries'] if e['id']==name),None)


@contextmanager
def locked():
    path=registry_path();path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    db=sqlite3.connect(str(path)+'.lock.sqlite',timeout=5)
    try:
        with db:
            db.execute('BEGIN IMMEDIATE');yield path
    finally:db.close()


def atomic(path,value):
    fd,temporary=tempfile.mkstemp(prefix='.'+path.name,dir=path.parent)
    try:
        with os.fdopen(fd,'w') as stream:
            json.dump(value,stream,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:
        if os.path.exists(temporary):os.unlink(temporary)


def save(entry,expected_revision,shortcut_transaction=None):
    entry=validate(entry)
    with locked() as path:
        value=read()
        if value['revision']!=expected_revision:raise ValueError('Agents changed in another window. Reload before saving.')
        old=next((e for e in value['entries'] if e['id']==entry['id']),None)
        if old is None and entry['id'] in value['removed']:raise ValueError('This ID belongs to retained history. Add a new entry.')
        if old and all(old.get(k)==entry.get(k) for k in ('preset','cwd')):entry['stateKey']=old['stateKey']
        else:
            entry['stateKey']=uuid.uuid4().hex
            if old:value['retained'].append(old)
        value['entries']=[entry if e['id']==entry['id'] else e for e in value['entries']]
        if old is None:value['entries'].append(entry)
        value['revision']+=1
        with shortcut_transaction() if shortcut_transaction else nullcontext():atomic(path,value)
        return value


def remove(name,expected_revision,clear_shortcut,shortcut_transaction=None):
    if name=='main':raise ValueError('The primary desktop entry is required by startup. You can rename or edit it.')
    with locked() as path:
        value=read()
        if value['revision']!=expected_revision:raise ValueError('Agents changed in another window. Reload before removing.')
        entry=next((e for e in value['entries'] if e['id']==name),None)
        if entry is None:raise ValueError('This entry was already removed.')
        value['retained'].append(entry);value['entries']=[e for e in value['entries'] if e['id']!=name]
        value['removed'].append(name);value['revision']+=1
        with shortcut_transaction() if shortcut_transaction else nullcontext():
            if not shortcut_transaction:clear_shortcut(name)
            atomic(path,value)
        return value


def new_id():return 'agent-'+uuid.uuid4().hex[:20]


def binding(entry):return tuple(entry.get(k) for k in ('id','preset','cwd','stateKey')) if entry else None


def launch(name):
    import subprocess
    import sys
    entry=get(name)
    if entry is None:raise ValueError('This desktop agent is not configured.')
    if sys.platform=='darwin':
        from .shortcut_activation import DesktopActivation
        DesktopActivation(instance=name).activate()
    elif sys.platform=='win32':
        from .shortcut_activation import DesktopActivation
        DesktopActivation(instance=name).activate()
    else:
        launcher=Path.home()/'.local/bin/augmentor-agent'
        if not launcher.is_file():raise ValueError('Install the managed desktop launcher before opening another window.')
        subprocess.Popen([str(launcher),'--instance',name],start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
