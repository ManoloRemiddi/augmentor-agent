#!/usr/bin/python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Opt-in installed Linux failure drills. Requires idle DSH, voice and desktops."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request


def systemctl(*args):
    return subprocess.run(['systemctl','--user',*args], capture_output=True, text=True, check=True, timeout=30).stdout.strip()


def status(name=''):
    runtime = Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}'))
    with socket.socket(socket.AF_UNIX) as sock:
        sock.settimeout(3)
        try: sock.connect(str(runtime/('augmentor-linux-pi'+name+'.sock')))
        except (FileNotFoundError,ConnectionRefusedError): return None
        try:
            sock.sendall(b'maintenance.status')
            with sock.makefile('rb') as stream:
                raw=stream.readline(16384)
                return json.loads(raw) if raw else None
        except (ConnectionResetError,BrokenPipeError): return None


def wait_ready(config, old_pid=None):
    start = time.monotonic()
    while time.monotonic()-start < 90:
        value = status()
        if value and value['pid'] != old_pid and value.get('online') and not value.get('sessionRestoreError'):
            assert value['buildRoot'] == config['root'] and value['voiceAvailable'] and value['modelReady'], value
            return round(time.monotonic()-start, 2), value
        time.sleep(.25)
    raise RuntimeError('Installed desktop failed to reconnect within 90 seconds.')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--live',action='store_true');args=parser.parse_args()
    if not args.live: parser.error('--live is required; this proof restarts idle installed services')
    data=Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local/share'))
    config=json.loads((data/'augmentor/desktop.json').read_text())
    sys.path.insert(0,config['root']+'/apps/native')
    from augmentor_linux.adapters.dsh import DshAdapter
    client=DshAdapter()
    def idle():
        assert not any(r.get('running') for r in client.session_rows()), 'DSH has active work'
        with urllib.request.urlopen('http://127.0.0.1:8877/health',timeout=3) as reply:
            assert not json.load(reply).get('active'), 'Voice is active'
        for name in ('','-mobile','-secondary'):
            current=status(name)
            assert not current or current.get('accepted'), 'A desktop has work or an open dialog'
    idle()
    service=config['dshService'];assert service
    mobile=systemctl('show','augmentor-mobile.service','-p','ActiveState','--value') == 'active'
    pointer=client.state_path();before=hashlib.sha256(pointer.read_bytes()).hexdigest()
    result={}
    try:
        if mobile:systemctl('stop','augmentor-mobile.service')
        old=status()['pid']
        systemctl('stop','augmentor-desktop.service',service)
        # Only the desktop starts: its cold connection check must start DSH.
        systemctl('start','augmentor-desktop.service')
        seconds,current=wait_ready(config,old);result['coldStartupSeconds']=seconds
        print('PASS: desktop cold start brought its managed DSH service online, with voice controls.',flush=True)
        idle();pid=systemctl('show',service,'-p','MainPID','--value')
        systemctl('stop',service)
        deadline=time.monotonic()+90
        while time.monotonic()<deadline:
            new=systemctl('show',service,'-p','MainPID','--value')
            if new not in ('0',pid):break
            time.sleep(.25)
        else:raise RuntimeError('Desktop did not restart the stopped DSH service')
        seconds,current=wait_ready(config);result['runtimeReconnectionSeconds']=seconds
        print('PASS: stopped DSH was restarted and the saved chat reconnected.',flush=True)
        idle();old=current['pid']
        systemctl('kill','--signal=SIGKILL','--kill-whom=main','augmentor-desktop.service')
        seconds,current=wait_ready(config,old);result['desktopCrashRecoverySeconds']=seconds
        print('PASS: supervised desktop process recovered after SIGKILL.',flush=True)
        pid=current['pid']
        subprocess.run([str(Path.home()/'.local/bin/augmentor-agent'),'--autostart'],check=True,timeout=20)
        assert status()['pid']==pid
        subprocess.run([str(Path.home()/'.local/bin/augmentor-recover')],check=True,timeout=120)
        assert hashlib.sha256(pointer.read_bytes()).hexdigest()==before, 'Saved chat/model pointer changed'
        result.update(autostartIdempotent=True, manualRecovery=True, savedChatAndModelPreserved=True, voiceControls=True, modelRequests=0)
        output=Path(os.environ.get('XDG_STATE_HOME',Path.home()/'.local/state'))/'augmentor-recovery/startup-proof.json'
        output.write_text(json.dumps(result,indent=2)+'\n');output.chmod(0o600)
        print(json.dumps(result),flush=True)
    finally:
        systemctl('start',service,'augmentor-desktop.service')
        if mobile:systemctl('start','augmentor-mobile.service')


if __name__=='__main__':main()
