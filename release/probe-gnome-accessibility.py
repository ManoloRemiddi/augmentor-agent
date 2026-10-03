# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Owned Fedora read-only accessibility proof; no input/actions/text queries.

Separate private helper candidate and disposable GTK target are required.
Create owner-only trigger.json with operation focus/status/cancel/deadline/exit.
cancel/deadline temporarily SIGSTOP only this probe's exact child to test its
parent hard deadline, then dispose it permanently. Never runs on an owner host.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--candidate',required=True);parser.add_argument('--target-candidate',required=True)
parser.add_argument('--target-pid',type=int,required=True);parser.add_argument('--source',required=True);args=parser.parse_args()
assert os.getuid()==1000 and os.environ.get('USER')=='augmentor-proof'
assert Path('/etc/augmentor-test-vm').read_text()=='Isolated Augmentor Fedora GNOME qualification VM\n'
assert subprocess.check_output(['systemd-detect-virt'],text=True).strip()=='qemu'
assert subprocess.check_output(['getenforce'],text=True).strip()=='Enforcing'
for name in (args.candidate,args.target_candidate):assert name.startswith('gnome-execution-probe-') and '/' not in name and '..' not in name
root=Path.home()/args.candidate;target_root=Path.home()/args.target_candidate
for directory in (root,target_root):assert directory.is_dir() and not directory.is_symlink() and directory.stat().st_uid==os.getuid() and not directory.stat().st_mode&0o077
proc=Path('/proc')/str(args.target_pid)
assert proc.stat().st_uid==os.getuid() and str(target_root/'probe-gnome-target.py').encode() in (proc/'cmdline').read_bytes().split(b'\0')
selection=Path.home()/'.local/share/augmentor/desktop.json';original=selection.read_bytes()
assert json.loads(original)['sourceRef']==args.source
env=dict(row.split('=',1) for row in subprocess.check_output(['systemctl','--user','show-environment'],text=True).splitlines() if '=' in row)
assert env['XDG_CURRENT_DESKTOP']=='GNOME' and env['XDG_SESSION_TYPE']=='wayland'
os.environ.update({key:value for key,value in env.items() if key in ('DISPLAY','WAYLAND_DISPLAY','XAUTHORITY','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','XDG_CURRENT_DESKTOP','XDG_SESSION_TYPE')})
os.umask(0o077);sys.path.insert(0,str(root))
from a11y_helper import AccessibilityHelper,process_start
helper=AccessibilityHelper(args.target_pid)
report={'format':'augmentor-owned-gnome-accessibility/1','parentPid':os.getpid(),'helperPid':helper.process.pid,
    'selectedSource':args.source,'targetPid':args.target_pid,'closed':False,'inputQualified':False,'inputSent':False,
    'sourceSha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [root/'a11y_helper.py',root/'a11y_service.py',Path(__file__),target_root/'probe-gnome-target.py']},
    'records':[{'operation':'initial-status','reply':helper.request('status')}], 'parentAtspiImported':False}
def save():
    assert selection.read_bytes()==original
    temporary=root/'a11y-result.json.tmp';temporary.write_text(json.dumps(report,indent=2)+'\n');temporary.replace(root/'a11y-result.json')
save()
try:
    while True:
        trigger=root/'trigger.json'
        if not trigger.exists():time.sleep(.05);continue
        assert not trigger.is_symlink() and trigger.stat().st_uid==os.getuid() and not trigger.stat().st_mode&0o077 and trigger.stat().st_size<8192
        value=json.loads(trigger.read_text());trigger.unlink();operation=value['operation']
        assert operation in ('focus','status','cancel','deadline','exit')
        if operation=='exit':break
        row={'operation':operation};started=time.monotonic()
        if operation in ('cancel','deadline'):
            assert helper.process.poll() is None and process_start(helper.process.pid)==helper.helper_start
            os.kill(helper.process.pid,signal.SIGSTOP)
        cancel=None;timer=None
        if operation=='cancel':cancel=threading.Event();timer=threading.Timer(.05,cancel.set);timer.start()
        if operation=='deadline':helper.timeout=.3
        try:row['reply']=helper.request('focus' if operation in ('cancel','deadline') else operation,generation=len(report['records']),cancel=cancel)
        except Exception as error:row['error']={'kind':type(error).__name__,'message':str(error)}
        finally:
            if timer:timer.cancel()
        row['durationSeconds']=time.monotonic()-started;row['helperClosed']=helper.closed
        report['records'].append(row);save()
        if helper.closed:break
finally:
    helper.close();report['closed']=helper.closed and helper.process.poll() is not None
    report['parentAtspiImported']='gi.repository.Atspi' in sys.modules
    report['selectedApplicationChanged']=selection.read_bytes()!=original;save()
