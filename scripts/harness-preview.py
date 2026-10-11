#!/usr/bin/python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Open the separately staged Linux Harness preview through its stable selection."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from urllib.parse import urlparse


def private_directory(path):
    path.mkdir(parents=True,mode=0o700,exist_ok=True)
    info=path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077:
        raise ValueError('The Harness preview needs its own private directory.')
    return path


def configuration():
    home=Path.home()
    data=Path(os.environ.get('XDG_DATA_HOME',home/'.local/share'))/'augmentor-harness-preview'
    config=Path(os.environ.get('XDG_CONFIG_HOME',home/'.config'))/'augmentor-harness-preview'
    state=Path(os.environ.get('XDG_STATE_HOME',home/'.local/state'))/'augmentor-harness-preview'
    runtime=Path(os.environ.get('XDG_RUNTIME_DIR',f'/run/user/{os.getuid()}'))/'augmentor-harness-preview'
    for directory in (data,config,state,runtime):private_directory(directory)
    descriptor=data/'augmentor/desktop.json'
    info=descriptor.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077 or info.st_nlink!=1:
        raise ValueError('Invalid private preview selection.')
    selected=json.loads(descriptor.read_text())
    root=Path(selected['root'])
    if not root.is_absolute() or not root.resolve().is_relative_to((data/'augmentor/releases').resolve()) or root.is_symlink():
        raise ValueError('The preview selection must name its separate staged release.')
    manifest=json.loads((root/'desktop-release.json').read_text())
    if manifest['deployment']!=selected or manifest['artifactSha256']!=selected['artifactSha256']:
        raise ValueError('The selected preview does not match its staged identity.')
    # Verify every staged file before executing any candidate code.
    actual={}
    for path in sorted(root.rglob('*')):
        relative=path.relative_to(root)
        if '__pycache__' in relative.parts or path.suffix=='.pyc' or str(relative)=='desktop-release.json':continue
        if path.is_symlink():
            if not path.resolve().is_relative_to(root.resolve()):raise ValueError('The preview contains an external symlink.')
            actual[str(relative)]='link:'+os.readlink(path)
        elif path.is_file():actual[str(relative)]=hashlib.sha256(path.read_bytes()).hexdigest()
    if actual!=manifest['files'] or hashlib.sha256(json.dumps(actual,sort_keys=True).encode()).hexdigest()!=selected['artifactSha256']:
        raise ValueError('Preview files changed after staging; stage a new candidate.')
    node=Path(selected['node'])
    if not node.resolve().is_relative_to(root.resolve()):raise ValueError('The preview must use its staged Node runtime.')
    env={key:value for key,value in os.environ.items() if not key.startswith(('AUGMENTOR_','DSH_'))}
    env.update({'XDG_DATA_HOME':str(data),'XDG_CONFIG_HOME':str(config),'XDG_STATE_HOME':str(state),'XDG_RUNTIME_DIR':str(runtime),
         'AUGMENTOR_PI_CONFIG':str(config/'augmentor-pi'),'AUGMENTOR_PI_STATE':str(state/'augmentor-pi'),
         'AUGMENTOR_PI_SOCKET':str(runtime/'pi.sock'),'AUGMENTOR_SHARED_DATA':str(data/'shared'),
         'AUGMENTOR_SHARED_STATE':str(runtime/'shared'),'AUGMENTOR_PYTHON':selected['python'],'AUGMENTOR_PI_NODE':str(node),
         'PI_CODING_AGENT_DIR':str(config/'augmentor-pi/agent'),'PI_TELEMETRY':'0','PI_SKIP_VERSION_CHECK':'1',
         'AUGMENTOR_HARNESS':'1','PYTHONDONTWRITEBYTECODE':'1'})
    env['PYTHONPATH']=str(root/'apps/native')
    env['AUGMENTOR_PI_LLAMA_CPP_PROVIDERS']='mx-qwen'
    return selected,env


def main():
    if sys.platform!='linux':raise ValueError('The first Harness preview targets Linux; other platforms are deferred.')
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--native',action='store_true',help='Open the shared native desktop with Pi in this preview profile.')
    group.add_argument('--status',action='store_true',help='Print the selected preview identity without starting an owner or model.')
    args=parser.parse_args()
    selected,env=configuration();root=Path(selected['root'])
    if args.status:
        print(json.dumps({key:selected[key] for key in ('releaseId','version','sourceRef','artifactSha256','root')},indent=2));return
    if args.native:
        if not env.get('QT_QPA_PLATFORM') and env.get('XDG_SESSION_TYPE')=='wayland' and env.get('DISPLAY'):env['QT_QPA_PLATFORM']='xcb'
        os.execve(selected['python'],[selected['python'],'-B','-m','augmentor_linux','--harness','pi','--instance','harness-preview'],env)
    subprocess.run([selected['python'],'-B',str(root/'scripts/ensure-runtime.py'),'--harness','pi'],env=env,check=True,timeout=70)
    opened=subprocess.run([selected['node'],str(root/'scripts/open-harness.mjs'),'--print-url'],env=env,check=True,capture_output=True,text=True,timeout=15)
    link=opened.stdout.strip();url=urlparse(link)
    if url.scheme!='http' or url.hostname!='127.0.0.1' or not url.fragment.startswith('token='):
        raise ValueError('The preview owner did not return a private local Harness link.')
    # The regular browser keeps its own profile; the private bearer is never logged.
    subprocess.run(['xdg-open',link],env=os.environ,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15)


if __name__=='__main__':
    try:main()
    except Exception as error:
        # Avoid echoing subprocess arguments, which may include the private link.
        message='Preview startup failed; inspect its private runtime.log.' if isinstance(error,subprocess.SubprocessError) else str(error)
        print('Augmentor Harness Preview: '+message,file=sys.stderr);raise SystemExit(1)
