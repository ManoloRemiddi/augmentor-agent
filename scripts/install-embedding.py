#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Install product-owned embedding startup; --plan performs no mutations."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys

ROOT = Path(__file__).absolute().parents[1]
LABEL = 'org.augmentor.embed'


def startup_plan(runtime, *, platform=None, home=None, startup=None, uid=None):
    platform = platform or sys.platform
    home = Path.home() if home is None else Path(home)
    root = Path(runtime['root'])
    environment = runtime.get('environment', {})
    command = [runtime['python'], '-I', '-B', str(root/'scripts/app-sdk-launch.py'), 'embed']
    if platform == 'linux':
        data = Path(os.environ.get('XDG_DATA_HOME', home/'.local/share'))/'augmentor'
        launcher = data/'embed-launch.py'
        target = Path(os.environ.get('XDG_CONFIG_HOME', home/'.config'))/'systemd/user/augmentor-embed.service'
        service = runtime.get('dshService') or ''
        quote = lambda value: '"'+str(value).replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%')+'"'
        body = ('# Augmentor SDK embedding service\n[Unit]\nDescription=Augmentor Browser embedding service\n'
                'After=network.target '+service+'\nWants='+service+'\nStartLimitIntervalSec=0\n\n[Service]\n'
                'Type=simple\nExecStart='+quote(runtime['python'])+' '+quote(launcher)+'\nRestart=always\nRestartSec=3\n'
                'TimeoutStopSec=10\nUMask=0077\nNoNewPrivileges=true\n\n[Install]\nWantedBy=default.target\n')
        return {'target': target, 'bytes': body.encode(), 'launcher': launcher,
                'start': [['systemctl', '--user', 'daemon-reload'], ['systemctl', '--user', 'enable', '--now', 'augmentor-embed.service']]}
    if platform == 'darwin':
        target = home/'Library/LaunchAgents'/f'{LABEL}.plist'
        body = plistlib.dumps({'Label': LABEL, 'ProgramArguments': command, 'EnvironmentVariables': environment,
                              'RunAtLoad': True, 'KeepAlive': True, 'ProcessType': 'Interactive', 'ThrottleInterval': 3})
        if uid is None:uid = os.getuid() if hasattr(os,'getuid') else 0
        return {'target': target, 'bytes': body, 'start': [['launchctl', 'bootstrap', f'gui/{uid}', str(target)]]}
    if platform == 'win32':
        if startup is None:
            if sys.platform != 'win32':
                raise ValueError('Windows startup needs a verified Windows known folder.')
            from win32com.shell import shell, shellcon
            startup = shell.SHGetFolderPath(0, shellcon.CSIDL_STARTUP, None, 0)
        target = Path(startup)/'Augmentor embedding.vbs'
        commandline = subprocess.list2cmdline(command).replace('"', '""')
        body = "' Augmentor SDK embedding service\r\nCreateObject(\"WScript.Shell\").Run \""+commandline+'\", 0, False\r\n'
        return {'target': target, 'bytes': body.encode('utf-16'), 'start': [['wscript.exe', str(target)]]}
    raise ValueError('No embedding startup adapter for this platform.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', action='store_true', help='Inspect startup without installing or starting it')
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('app_sdk_runtime', ROOT/'scripts/app-sdk-runtime.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    runtime = module.describe()
    plan = startup_plan(runtime)
    if args.plan:
        print(json.dumps({'platform': sys.platform, 'startup': str(plan['target']), 'serviceStarted': False,
                          'installed': False, 'startupCommands': plan['start']}))
        return
    target = plan['target']
    if target.exists():
        text = target.read_bytes()
        marker = LABEL.encode() if sys.platform == 'darwin' else 'Augmentor SDK embedding service'.encode('utf-16-le' if sys.platform == 'win32' else 'utf-8')
        legacy = b'Description=Augmentor Browser embedding service'
        if marker not in text and not (sys.platform == 'linux' and legacy in text):
            raise SystemExit('The startup path is occupied by another file and was preserved.')
        if text == plan['bytes']:
            print('Embedding startup is already registered; no services were restarted.')
            return
        raise SystemExit('Embedding startup differs. Stop dependent app work and remove its owned startup entry before reinstalling.')
    target.parent.mkdir(parents=True, exist_ok=True)
    if 'launcher' in plan:
        plan['launcher'].parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT/'scripts/embed-launch.py', plan['launcher'])
    with target.open('xb') as stream:
        stream.write(plan['bytes'])
    for command in plan['start']:
        subprocess.run(command, check=True)
    print('Registered product-owned Augmentor embedding startup.')


if __name__ == '__main__':
    main()
