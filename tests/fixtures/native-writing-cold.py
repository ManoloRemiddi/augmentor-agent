# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Keep the real cold-starting PromptClient alive for owned-helper inspection."""
import json
import os
from pathlib import Path
import sys
root=Path(sys.argv[1]).resolve();sys.path.insert(0,str(root))
from augmentor_linux.prompt_client import PromptClient
import augmentor_linux.prompt_client as module
assert Path(module.__file__).resolve()==root/'augmentor_linux/prompt_client.py'
client=PromptClient();assert Path(client.base)==Path(os.environ['AUGMENTOR_SHARED_STATE'])/'prompts.sock'
result=client.call('host.describe');print(json.dumps({'pid':result['pid'],'requestedClient':True}),flush=True)
sys.stdin.readline()
