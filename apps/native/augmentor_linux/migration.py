# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Explicit, repeatable import of reusable legacy preferences and prompts."""
import json
import os
from pathlib import Path
import re
import tempfile


def atomic_json(path,value):
    path=Path(path);path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w',dir=path.parent,delete=False) as file:
        json.dump(value,file,indent=2);temporary=file.name
    os.replace(temporary,path)


def migrate(config,appearance=None,settings=None,prompts=None):
    config=Path(config);report={'appearance':False,'pins':0,'prompts':0,'skipped':[]}
    if appearance and Path(appearance).exists():
        from .preferences import DEFAULTS
        old=json.loads(Path(appearance).read_text());destination=config/'appearance.json'
        if not isinstance(old,dict):raise ValueError('Appearance must be a JSON object')
        if not destination.exists():atomic_json(destination,{k:v for k,v in old.items() if k in DEFAULTS and type(v) is type(DEFAULTS[k])});report['appearance']=True
        else:report['skipped'].append('Existing Pi appearance')
    source={}
    if settings:
        import yaml
        source=yaml.safe_load(Path(settings).read_text()) or {}
        current_path=config/'settings.json'
        current=json.loads(current_path.read_text()) if current_path.exists() else {'revision':0,'defaultPreset':'workspace-write','pinned':[],'hidden':[],'defaultModel':None}
        pins=source.get('model-picker-augmented',{}).get('pinned',[])
        valid=[p for p in pins if isinstance(p,str) and '/' in p]
        current['pinned']=list(dict.fromkeys(current.get('pinned',[])+valid));report['pins']=len(valid)
        current['revision']=current.get('revision',0)+1;atomic_json(current_path,current)
    rows=source.get('prompt-library',{}).get('prompts',[])
    if prompts:
        data=json.loads(Path(prompts).read_text());rows=data if isinstance(data,list) else data.get('prompts',[])
    folder=config/'agent/prompts';folder.mkdir(mode=0o700,parents=True,exist_ok=True)
    for row in rows:
        name=row.get('name','');content=row.get('content','')
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,128}',name) or not isinstance(content,str) or not content.strip():report['skipped'].append('Invalid prompt');continue
        target=folder/(name+'.md')
        if target.exists():report['skipped'].append('Existing prompt /'+name);continue
        with target.open('x') as file:file.write(content)
        target.chmod(0o600);report['prompts']+=1
    return report
