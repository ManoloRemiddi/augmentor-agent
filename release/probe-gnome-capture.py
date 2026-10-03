# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Owned Fedora capture/cancellation candidate. No portal input is ever requested.

Stage peer modules separately, launch the disposable GTK target, consent visibly,
activate that target and create private trigger.capture once. Visible Stop closes
the candidate. --stall-frame uses a synthetic empty pipeline with real consent
solely to exercise cancellation during acquisition, not real PipeWire capture.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--candidate',required=True)
parser.add_argument('--source',required=True);parser.add_argument('--target-pid',required=True,type=int)
parser.add_argument('--stall-frame',action='store_true');args=parser.parse_args()
assert os.getuid()==1000 and os.environ.get('USER')=='augmentor-proof'
assert Path('/etc/augmentor-test-vm').read_text()=='Isolated Augmentor Fedora GNOME qualification VM\n'
assert subprocess.check_output(['systemd-detect-virt'],text=True).strip()=='qemu'
assert subprocess.check_output(['getenforce'],text=True).strip()=='Enforcing'
assert args.candidate.startswith('gnome-execution-probe-') and '/' not in args.candidate and '..' not in args.candidate
candidate=Path.home()/args.candidate
assert candidate.is_dir() and not candidate.is_symlink() and candidate.stat().st_uid==os.getuid() and not candidate.stat().st_mode&0o077
target=Path('/proc')/str(args.target_pid)
assert target.stat().st_uid==os.getuid() and str(candidate/'probe-gnome-target.py').encode() in (target/'cmdline').read_bytes().split(b'\0')
target_start=(target/'stat').read_text().rsplit(')',1)[1].split()[19]
selection=Path.home()/'.local/share/augmentor/desktop.json';original=selection.read_bytes();selected=json.loads(original);installed=Path(selected['root'])
assert installed.is_relative_to(Path.home()/'.local/share/augmentor/releases') and selected['sourceRef']==args.source
assert json.loads((installed/'release.json').read_text())['source']=={'commit':args.source,'dirty':False}
env=dict(row.split('=',1) for row in subprocess.check_output(['systemctl','--user','show-environment'],text=True).splitlines() if '=' in row)
assert env['XDG_CURRENT_DESKTOP']=='GNOME' and env['XDG_SESSION_TYPE']=='wayland'
os.environ.update({key:value for key,value in env.items() if key in ('DISPLAY','WAYLAND_DISPLAY','XAUTHORITY','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','XDG_CURRENT_DESKTOP','XDG_SESSION_TYPE')})
os.environ['QT_QPA_PLATFORM']='xcb';os.umask(0o077);sys.path.insert(0,str(candidate))
from worker import Worker
from gnome_control import GnomeControl
from gi.repository import Gst
spec=importlib.util.spec_from_file_location('installed_banner',installed/'services/desktop/service.py')
service=importlib.util.module_from_spec(spec);sys.path.append(str(installed/'services/desktop'));spec.loader.exec_module(service)
from PySide6.QtCore import QObject,Signal,QTimer
from PySide6.QtWidgets import QApplication
app=QApplication([]);app.setQuitOnLastWindowClosed(False);banner=service.Banner()
class Delivery(QObject):notice=Signal(bool,str);result=Signal(str,object);closed=Signal();request=Signal(str)
delivery=Delivery();delivery.notice.connect(banner.update.emit)
worker=Worker(lambda context:GnomeControl(context,delivery.notice.emit,request_timeout=180,on_request=delivery.request.emit));controller=worker.backend
owner='codex:owned-gnome-capture-fixture'
report={'format':'augmentor-gnome-capture-probe/1','selectedSource':args.source,'qtPlatform':app.platformName(),
    'targetPid':args.target_pid,'targetStartTime':target_start,'inputSent':False,'inputQualified':False,
    'selectedApplicationChanged':False,'ownerStateChanged':False,'guiTimerTicks':0,'closed':False,'stopClicked':False,
    'syntheticStalledPipeline':args.stall_frame,'probeConsentTimeoutSeconds':180,'sourceSha256':{path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in candidate.glob('*.py')}}
def save():
    assert selection.read_bytes()==original
    (candidate/'capture-result.json').write_text(json.dumps(report,indent=2)+'\n')
def work(operation,function):
    try:value=function()
    except Exception as error:value={'error':str(error)}
    delivery.result.emit(operation,value)
def captured():
    assert target.stat().st_uid==os.getuid() and (target/'stat').read_text().rsplit(')',1)[1].split()[19]==target_start
    before=controller.kwin.read(controller.cancel)
    if before.get('window',{}).get('pid')!=args.target_pid:raise RuntimeError('Activate the owned GTK target before capture.')
    if args.stall_frame:
        from capture_stream import receive_frame
        pipeline=Gst.parse_launch('appsrc is-live=true ! appsink name=capture')
        try:receive_frame(pipeline,controller.cancel,timeout=30,context=controller.context,checkpoint=controller.checkpoint)
        finally:pipeline.set_state(Gst.State.NULL)
        raise RuntimeError('Synthetic stalled frame unexpectedly arrived.')
    result=controller.capture(owner)
    assert result['window']['pid']==args.target_pid
    data=result.pop('image')['data']
    return {'imageSize':result['imageSize'],'screen':result['screen'],'targetPid':result['window']['pid'],
        'encodedImageSha256':hashlib.sha256(data.encode()).hexdigest(),'freshTokenCreated':bool(result['token'])}
stopping=False
def cleanup():
    try:controller.stop()
    finally:delivery.closed.emit()
def stop(clicked=True):
    global stopping
    if stopping:return
    stopping=True;report['stopClicked']=clicked;report['stopAtGuiTick']=report['guiTimerTicks'];report['stopMonotonic']=time.monotonic()
    controller.request_stop();worker.submit(cleanup)
def result(operation,value):
    if operation=='connect' and controller.cancel.is_set():
        report['lateResultDiscarded']=True
        if not value.get('error'):value={'error':'Late consent discarded after cancellation.'}
    report[operation]=value;save()
    if value.get('error'):stop(False)
delivery.result.connect(result)
def notice(active,text):
    if not active and report.get('connect',{}).get('sharing'):stop(False)
delivery.notice.connect(notice)
def request(method):report.setdefault('requests',[]).append(method);save()
delivery.request.connect(request)
def closed():
    report['closed']=controller.consent is None and controller.fd is None and controller.session is None and controller.snapshot is None
    report['failure']=controller.last_failure;report['stopReason']=controller.last_stop_reason
    report['cleanupAfterStopSeconds']=time.monotonic()-report['stopMonotonic']
    save();app.quit()
delivery.closed.connect(closed);banner.stop.clicked.connect(lambda:stop(True))
timer=QTimer();timer.setInterval(50)
def tick():
    report['guiTimerTicks']+=1
    trigger=candidate/'trigger.capture'
    if trigger.exists() and not stopping:
        assert not trigger.is_symlink() and trigger.stat().st_uid==os.getuid() and not trigger.stat().st_mode&0o077
        trigger.unlink();report['captureStartedAtGuiTick']=report['guiTimerTicks'];save();worker.submit(lambda:work('capture',captured))
    if report['guiTimerTicks']%100==0:save()
timer.timeout.connect(tick);timer.start();save()
QTimer.singleShot(0,lambda:worker.submit(lambda:work('connect',lambda:controller.connect(owner))))
try:app.exec()
finally:controller.request_stop();worker.close();save()
