#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Discover an explicitly supplied local OpenAI-compatible endpoint for Pi."""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import sys
import urllib.request
from urllib.parse import urlsplit
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'apps/native'))
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--endpoint',default='http://127.0.0.1:8080/v1')
parser.add_argument('--model',default=None)
args=parser.parse_args()
url=urlsplit(args.endpoint)
if url.scheme!='http' or not ipaddress.ip_address(url.hostname).is_loopback or url.username or url.password or url.query or url.fragment:parser.error('A numeric loopback HTTP endpoint is required.')
config=Path(os.environ.get('AUGMENTOR_PI_CONFIG',Path(os.environ.get('XDG_CONFIG_HOME',Path.home()/'.config'))/'augmentor-pi'))
agent=config/'agent';agent.mkdir(mode=0o700,parents=True,exist_ok=True)
if (agent/'models.json').exists():
    print('Existing Pi model configuration preserved:',agent/'models.json');sys.exit(0)
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*_):raise ValueError('Endpoint redirects are disabled')
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
with opener.open(args.endpoint.rstrip('/')+'/models',timeout=5) as response:
    data=json.loads(response.read(1024*1024))
models=[row['id'] for row in data.get('data',[])]
model=args.model or (models[0] if len(models)==1 else None)
if model not in models:parser.error('Select one of the advertised models with --model: '+', '.join(models))
value={'providers':{'mx-qwen':{'baseUrl':args.endpoint,'api':'openai-completions','apiKey':'local-no-key','compat':{'supportsDeveloperRole':False,'supportsReasoningEffort':False},'models':[{'id':model,'name':model.split('-UD-')[0]+' (local)','reasoning':False,'input':['text'],'contextWindow':131072,'maxTokens':4096,'cost':{'input':0,'output':0,'cacheRead':0,'cacheWrite':0}}]}}}
# This setup uses the verified MX llama.cpp target. Custom endpoints may need
# their own context/token limits in Models & providers.
from augmentor_linux.migration import atomic_json
atomic_json(agent/'models.json',value)
settings=config/'settings.json'
if not settings.exists():atomic_json(settings,{'revision':0,'defaultPreset':'workspace-write','pinned':['mx-qwen/'+model],'hidden':[],'defaultModel':{'provider':'mx-qwen','model':model}})
print('Configured Pi directly against',args.endpoint,'with model',model)
