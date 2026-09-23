# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Allowlisted support data: no history, environment dump, paths or credentials."""
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import socket

ROOT=Path(__file__).resolve().parents[2]

def report():
    product=json.loads((ROOT/'release/product.json').read_text())
    release={k:product[k] for k in ('version','channel','protocols','dataSchema')}
    distro={}
    try:
        for line in Path('/etc/os-release').read_text().splitlines():
            key,_,value=line.partition('=');value=value.strip('"')
            if key in ('ID','VERSION_ID') and re.fullmatch(r'[A-Za-z0-9._-]{1,40}',value):distro[key]=value
    except OSError:pass
    desktop={'reachable':False}
    path=Path(os.environ.get('XDG_RUNTIME_DIR',f'/run/user/{os.getuid()}'))/'augmentor-desktop.sock'
    try:
        with socket.socket(socket.AF_UNIX) as client:
            client.settimeout(1);client.connect(str(path));client.sendall(b'{"protocol":"augmentor-desktop/1","method":"status"}\n')
            with client.makefile('rb') as reader:response=json.loads(reader.readline(8193))
            if response.get('ok'):
                desktop={'reachable':True,**{key:response['result'].get(key) is True for key in ('active','sharing','busy')}}
    except (OSError,ValueError):pass
    return {'schema':'augmentor-support/1','release':release,'os':{'distribution':distro,'architecture':platform.machine(),'session':os.environ.get('XDG_SESSION_TYPE') if os.environ.get('XDG_SESSION_TYPE') in ('wayland','x11') else 'unknown'},
        'components':{'pi':(ROOT/'node_modules/@earendil-works/pi-coding-agent/package.json').is_file(),'desktopUi':importlib.util.find_spec('PySide6') is not None,'accessibility':importlib.util.find_spec('gi') is not None,'dshCommand':shutil.which('dsh') is not None},
        'desktop':desktop,'privacy':'Contains version and component status only. No chats, prompts, screenshots, clipboard, memory, credentials, endpoints or personal file paths are included.'}
