# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Resolve the installed Harness; never start an empty legacy Pi profile."""
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import shlex
import stat
import subprocess
import sys


def private_record(path, *, raw=False):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077 or info.st_nlink != 1 or info.st_size > 2*1024*1024):
            raise ValueError('Harness connection records must be private, owned regular files.')
        data = os.read(fd, 2*1024*1024+1)
        return data if raw else json.loads(data)
    finally:
        os.close(fd)


def absolute(value):
    if not isinstance(value, str) or not value or any(ord(c) < 32 for c in value):
        raise ValueError('Harness connection paths must be explicit absolute paths.')
    path = Path(value)
    if not path.is_absolute() or str(path) != value or path.resolve() != path:
        raise ValueError('Harness connection paths cannot contain aliases or symbolic links.')
    return path


def macos_launch_environment(home, agent):
    """Read either supported installer format without evaluating shell code."""
    if agent.get('Label') != 'com.augmentor.Harness':
        raise ValueError('The installed Harness LaunchAgent has an unexpected identity.')
    if isinstance(agent.get('EnvironmentVariables'), dict):
        return agent['EnvironmentVariables']
    base=home/'Library/Application Support/Augmentor Harness'
    wrapper=base/'bin/start-harness'
    if agent.get('ProgramArguments') != [str(wrapper)]:
        raise ValueError('The installed Harness launcher format is unsupported.')
    private_record(wrapper,raw=True)
    text=private_record(base/'bin/environment.sh',raw=True).decode('utf-8')
    wanted={'AUGMENTOR_HARNESS_HOME','XDG_RUNTIME_DIR','AUGMENTOR_PI_CONFIG','AUGMENTOR_PI_STATE',
            'AUGMENTOR_PI_SOCKET','AUGMENTOR_PI_WORKSPACE','AUGMENTOR_SHARED_STATE','AUGMENTOR_SHARED_DATA'}
    values={'HOME':str(home),'UID':str(os.getuid())};seen=set()
    for line in text.splitlines():
        match=re.fullmatch(r'export ([A-Z_]+)=(.*)',line.strip())
        if not match or match[1] not in wanted:continue
        key=match[1]
        if key in seen:raise ValueError('Duplicate Harness environment path declaration.')
        words=shlex.split(match[2])
        if len(words)!=1:raise ValueError('Unsupported Harness environment path declaration.')
        # The installer uses this literal user-id expression. Replace it with
        # the known uid; never run a shell, substitution, or arbitrary command.
        value=words[0].replace('$(id -u)',str(os.getuid()))
        def expand(m):
            name=m[1] or m[2]
            if name not in values:raise ValueError('Unknown Harness environment path variable.')
            return values[name]
        value=re.sub(r'\$(?:\{([A-Z_]+)\}|([A-Z_]+))',expand,value)
        if '$' in value or '`' in value or any(ord(c)<32 for c in value):
            raise ValueError('Dynamic Harness environment paths are unsupported.')
        values[key]=value;seen.add(key)
    if wanted-seen:raise ValueError('The installed Harness environment lacks required connection paths.')
    if values['AUGMENTOR_HARNESS_HOME']!=str(base):
        raise ValueError('The installed Harness environment belongs to another installation.')
    return values


def selection():
    """Return non-secret IPC/profile metadata from the existing installation."""
    if sys.platform == 'win32':
        raise ValueError('Augmentor Harness installation discovery on Windows is not available yet.')
    if os.environ.get('AUGMENTOR_AH_CONNECTION'):
        record = private_record(absolute(os.environ['AUGMENTOR_AH_CONNECTION']))
        if record.get('schema') != 'augmentor-ah-connection/1':
            raise ValueError('Unsupported Augmentor Harness connection record.')
        profile = record['profile']; root = record['root']; version = record['version']
        start = None  # Explicit profiles must already be managed by their installer.
    elif sys.platform == 'linux':
        data = Path(os.environ.get('XDG_DATA_HOME', Path.home()/'.local/share'))
        current = private_record(data/'augmentor-harness/startup/current.json')
        if current.get('schema') != 'augmentor-harness-startup/1' or not re.fullmatch(r'[a-z][a-z0-9-]{0,31}', current.get('review', '')):
            raise ValueError('The installed Harness startup selection is invalid.')
        registry = absolute(current['registry']); opener = absolute(current['opener'])
        records = private_record(registry/'reviews.json')
        if records.get('schema') != 'augmentor-harness-reviews/1':
            raise ValueError('The Harness installation registry is invalid.')
        if records.get('ownedFiles', {}).get(str(opener)) != hashlib.sha256(private_record(opener, raw=True)).hexdigest():
            raise ValueError('The registered Harness launcher changed; reinstall it before connecting.')
        entry = records['entries'][current['review']]
        profile = entry['profile']; root = entry['deployment']['root']; version = entry['deployment']['version']
        start = [sys.executable, str(opener), '--registry', str(registry), 'open', current['review'], '--print-url']
    elif sys.platform == 'darwin':
        # Read the installer's real service environment instead of guessing a socket.
        path = Path.home()/'Library/LaunchAgents/com.augmentor.Harness.plist'
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o022:
            raise ValueError('The installed Harness LaunchAgent is unsafe.')
        agent = plistlib.loads(path.read_bytes()); env = macos_launch_environment(Path.home(),agent)
        root = str((Path.home()/'Library/Application Support/Augmentor Harness/current').resolve(strict=True))
        version = json.loads((Path(root)/'package.json').read_text())['version']
        profile = dict(config=env['AUGMENTOR_PI_CONFIG'], state=env['AUGMENTOR_PI_STATE'], socket=env['AUGMENTOR_PI_SOCKET'],
                       workspace=env['AUGMENTOR_PI_WORKSPACE'], sharedState=env['AUGMENTOR_SHARED_STATE'], sharedData=env['AUGMENTOR_SHARED_DATA'])
        # /tmp and /var are system aliases on macOS. Canonicalize the socket
        # from the owned LaunchAgent, while keeping the reported profile paths.
        profile['socket'] = str(Path(profile['socket']).resolve())
        profile['sharedState'] = str(Path(profile['sharedState']).resolve())
        start = ['launchctl', 'kickstart', 'gui/'+str(os.getuid())+'/com.augmentor.Harness']
    else:
        raise ValueError('Connect an installed Harness using AUGMENTOR_AH_CONNECTION on this platform.')
    root = str(absolute(root))
    for key in ('config', 'state', 'workspace', 'sharedState', 'sharedData'):
        path = absolute(profile[key]); info = path.stat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
            raise ValueError('The registered Harness profile is unavailable.')
        if key != 'workspace' and info.st_mode & 0o077:
            raise ValueError('Harness state and configuration must be private.')
    endpoint = absolute(profile['socket']); parent = endpoint.parent.stat()
    if parent.st_uid != os.getuid() or parent.st_mode & 0o077:
        raise ValueError('The Harness socket directory must be private and owned.')
    identity = hashlib.sha256(json.dumps([profile['config'], profile['state'], str(endpoint)]).encode()).hexdigest()
    return dict(schema='augmentor-ah-connection/1', profile={k:profile[k] for k in ('config','state','socket','workspace','sharedState','sharedData')},
                root=root, version=version, binding=identity, start=start)


def ensure_running(expected):
    current = selection()
    if current != expected:
        raise ValueError('The selected Harness changed. Reconnect before continuing; no action was replayed.')
    if not current['start']:
        raise ValueError('Start the registered Augmentor Harness application, then reconnect.')
    # The Linux opener owns seal, maintenance and duplicate-owner checks. Its
    # private URL is captured and discarded, never sent to clients or logs.
    result = subprocess.run(current['start'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=95)
    if result.returncode:
        raise ValueError('Augmentor Harness could not start. Open its normal launcher to check the installation.')


def check_description(value, description):
    profile = value['profile']
    if (description.get('protocol') != 'augmentor-pi/1' or description.get('stateDir') != profile['state']
            or description.get('configDir') != profile['config'] or description.get('version') != value['version']):
        raise ValueError('The connected runtime does not match the selected Augmentor Harness. No action was sent.')


def shared_environment(value):
    p = value['profile']
    return {**os.environ, 'AUGMENTOR_SHARED_STATE':p['sharedState'], 'AUGMENTOR_SHARED_DATA':p['sharedData'],
            'AUGMENTOR_PI_CONFIG':p['config'], 'AUGMENTOR_PI_STATE':p['state'], 'AUGMENTOR_PI_SOCKET':p['socket'],
            'PYTHONDONTWRITEBYTECODE':'1'}
