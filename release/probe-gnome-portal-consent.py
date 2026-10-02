#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Visible, input-free consent probe in the existing owned Fedora GNOME guest.

Reuses the selected artifact's unchanged Stop banner. Never stages/selects an
application, sends portal input or changes lock settings. Acceptance and Stop
must be exercised through the actual graphical desktop, outside this process.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True)
    parser.add_argument('--candidate',default='gnome-control-probe')
    parser.add_argument('--qt-platform',choices=('wayland','xcb'),required=True)
    args=parser.parse_args()
    assert os.geteuid()==1000 and os.environ.get('USER')=='augmentor-proof'
    assert Path('/etc/augmentor-test-vm').read_text()=='Isolated Augmentor Fedora GNOME qualification VM\n'
    assert subprocess.check_output(['systemd-detect-virt'],text=True).strip()=='qemu'
    assert subprocess.check_output(['getenforce'],text=True).strip()=='Enforcing'
    selection_path=Path.home()/'.local/share/augmentor/desktop.json';selection_bytes=selection_path.read_bytes()
    selected=json.loads(selection_bytes);root=Path(selected['root'])
    assert root.is_relative_to(Path.home()/'.local/share/augmentor/releases') and selected['sourceRef']==args.source
    assert json.loads((root/'release.json').read_text())['source']=={'commit':args.source,'dirty':False}
    env=dict(row.split('=',1) for row in subprocess.check_output(['systemctl','--user','show-environment'],text=True).splitlines() if '=' in row)
    assert env['XDG_CURRENT_DESKTOP']=='GNOME' and env['XDG_SESSION_TYPE']=='wayland'
    os.environ.update({key:value for key,value in env.items() if key in ('DISPLAY','WAYLAND_DISPLAY','XAUTHORITY','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','XDG_CURRENT_DESKTOP','XDG_SESSION_TYPE')})
    assert args.candidate.startswith('gnome-control-probe') and '/' not in args.candidate and '..' not in args.candidate
    candidate=Path.home()/args.candidate
    assert candidate.is_dir() and not candidate.is_symlink() and candidate.stat().st_uid==os.getuid()
    assert candidate.stat().st_mode&0o077==0
    # Import peer modules from the separate candidate directory, then reuse only
    # the approved installed banner class; no installed source is edited.
    sys.path.insert(0,str(candidate))
    from worker import Worker
    from portal_session import ConsentSession
    sys.path.insert(0,str(root/'services/desktop'))
    spec=importlib.util.spec_from_file_location('installed_banner_source',root/'services/desktop/service.py')
    service=importlib.util.module_from_spec(spec);spec.loader.exec_module(service)
    from PySide6.QtCore import QObject,Signal,QTimer
    from PySide6.QtWidgets import QApplication
    os.environ['QT_QPA_PLATFORM']=args.qt_platform
    os.umask(0o077);app=QApplication([]);app.setQuitOnLastWindowClosed(False)
    banner=service.Banner();worker=Worker(lambda context:ConsentSession(context,request_timeout=180));session=worker.backend
    report={'format':'augmentor-gnome-native-consent-probe/1','target':'fedora44-x86_64','selectedSource':args.source,
        'bannerSha256':hashlib.sha256((root/'services/desktop/service.py').read_bytes()).hexdigest(),
        'sourceSha256':{name:hashlib.sha256((candidate/name).read_bytes()).hexdigest()
            for name in ('worker.py','portal_session.py','probe-gnome-portal-consent.py')},
        'inputSent':False,'inputQualified':False,'ownerStateChanged':False,'productSelectionChanged':False,
        'result':None,'closed':False,'stopClicked':False,'guiTimerTicks':0,'qtPlatform':app.platformName(),
        'probeConsentTimeoutSeconds':180}
    class Delivery(QObject):ready=Signal(object);closed=Signal();revoked=Signal();request=Signal(str)
    delivery=Delivery();attempt=session.generation
    def save():
        assert selection_path.read_bytes()==selection_bytes
        (candidate/'consent-result.json').write_text(json.dumps(report,indent=2)+'\n')
    def started(result):
        report['result']=result
        if session.cancel.is_set() or session.generation!=attempt:
            report['lateResultDiscarded']=True;save();stop(False);return
        if result.get('error'):
            banner.update.emit(False,'Desktop sharing refused');save();stop(False)
        else:
            banner.update.emit(True,'Desktop sharing qualification — no input sent');save()
    def closed():
        report['closed']=session.session is None and session.fd is None and session.request_path is None
        banner.update.emit(False,'Desktop sharing stopped');save();app.quit()
    delivery.ready.connect(started);delivery.closed.connect(closed)
    def connect():
        try:result=session.connect()
        except Exception as error:result={'error':str(error)}
        delivery.ready.emit(result)
    def cleanup():
        try:session.dispose()
        finally:delivery.closed.emit()
    stopping=False
    def stop(clicked=True):
        nonlocal stopping
        if stopping:return
        stopping=True;report['stopClicked']=clicked;report['stopAtGuiTick']=report['guiTimerTicks']
        session.request_stop();worker.submit(cleanup)
    delivery.revoked.connect(lambda:stop(False));session.on_stopped=delivery.revoked.emit
    def request_phase(method):report.setdefault('requests',[]).append(method);save()
    delivery.request.connect(request_phase);session.on_request=delivery.request.emit
    banner.stop.clicked.connect(lambda:stop(True))
    banner.update.emit(True,'Waiting for GNOME desktop sharing consent')
    timer=QTimer();timer.setInterval(50)
    def tick():
        report['guiTimerTicks']+=1
        if report['guiTimerTicks']%100==0:save()
    timer.timeout.connect(tick);timer.start()
    QTimer.singleShot(0,lambda:worker.submit(connect))
    save()
    try:app.exec()
    finally:
        session.request_stop();worker.close();save()


if __name__=='__main__':main()
