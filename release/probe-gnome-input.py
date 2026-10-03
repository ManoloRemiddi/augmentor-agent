# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Owned Fedora GNOME candidate input probe; production selection stays unchanged.

Native consent and foreground activation are manual observed operations. Each
private trigger.input.json explicitly requests capture/action/inspect/finish.
No input is inferred from readiness, dispatched automatically or replayed.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


def private_json(path,limit=8192):
    if path.is_symlink() or not path.is_file() or path.stat().st_uid!=os.getuid() or path.stat().st_mode&0o077 or path.stat().st_size>limit:
        raise RuntimeError('A private bounded owned JSON file is required.')
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('Duplicate input proof field.')
            result[key]=value
        return result
    def invalid(_):raise ValueError('Nonfinite input proof value.')
    value=json.loads(path.read_text(),object_pairs_hook=pairs,parse_constant=invalid)
    if not isinstance(value,dict):raise RuntimeError('An input proof object is required.')
    return value


def selected_artifact(source,artifact_sha256,native_source):
    """Read-only admission before loading candidate, Qt or installed banner code.

    The selected managed artifact and native RPM may have different reviewed
    sources. Both are explicit identities; neither is inferred from the other.
    """
    if (not isinstance(source,str) or not re.fullmatch('[a-f0-9]{40}',source)
            or not isinstance(native_source,str) or not re.fullmatch('[a-f0-9]{40}',native_source)
            or not isinstance(artifact_sha256,str) or not re.fullmatch('[a-f0-9]{64}',artifact_sha256)):
        raise RuntimeError('Supply exact selected/native source and selected artifact identities.')
    overrides=('LD_PRELOAD','LD_AUDIT','LD_LIBRARY_PATH','QT_PLUGIN_PATH','QT_QPA_PLATFORM_PLUGIN_PATH',
        'QML_IMPORT_PATH','QML2_IMPORT_PATH','PYTHONHOME','PYTHONPATH','VIRTUAL_ENV')
    if any(os.environ.get(name) for name in overrides):raise RuntimeError('Input qualification refuses inherited loader or Python runtime overrides.')
    if sys.executable!='/usr/bin/python3' or sys.prefix!=sys.base_prefix:
        raise RuntimeError('Use the approved native /usr/bin/python3 interpreter.')
    if os.environ.get('AUGMENTOR_PYTHON') not in (None,'','/usr/bin/python3'):
        raise RuntimeError('The requested interpreter differs from the native contract.')
    data=Path.home()/'.local/share/augmentor';selection_path=data/'desktop.json'
    original=selection_path.read_bytes();selection=private_json(selection_path)
    root=Path(selection.get('root',''));store=data/'releases'
    if (not root.is_absolute() or root.resolve()!=root or root.parent!=store or root.is_symlink()
            or not root.is_dir() or root.stat().st_uid!=os.getuid() or root.stat().st_mode&0o077):
        raise RuntimeError('An owned private canonical managed release is required.')
    if selection.get('sourceRef')!=source or selection.get('artifactSha256')!=artifact_sha256:
        raise RuntimeError('The selected source or artifact hash differs from this proof.')
    if selection.get('python')!='/usr/bin/python3':raise RuntimeError('The selected interpreter differs from the native Fedora contract.')
    native=Path('/usr/lib/augmentor')
    for directory in (root,native):
        policy=directory/'linux-python-runtime.json'
        if policy.exists() or policy.is_symlink():raise RuntimeError('The native Fedora input fixture refuses managed or source Qt Python runtime policies.')
    release=json.loads((root/'release.json').read_text());native_release=json.loads((native/'release.json').read_text())
    for metadata,expected in ((release,source),(native_release,native_source)):
        if metadata.get('source')!={'commit':expected,'dirty':False} or metadata.get('target')!='fedora44-x86_64':
            raise RuntimeError('The selected or native clean release source/target differs from this proof.')
    if (not isinstance(selection.get('version'),str) or selection['version']!=release.get('version')
            or selection['version']!=native_release.get('version')):
        raise RuntimeError('The selected and native product versions differ.')
    audit=subprocess.run(['rpm','-V','augmentor-agent'],capture_output=True,text=True,timeout=30)
    if audit.returncode!=0 or audit.stdout.strip() or audit.stderr.strip():raise RuntimeError('The native Augmentor RPM audit is not clean.')
    verifier=data/'desktop-deployment.py'
    if verifier.is_symlink() or not verifier.is_file() or verifier.stat().st_uid!=os.getuid() or verifier.stat().st_mode&0o022:
        raise RuntimeError('The normal owned deployment verifier is unavailable or writable by another user.')
    spec=importlib.util.spec_from_file_location('owned_input_deployment_verifier',verifier)
    deployment=importlib.util.module_from_spec(spec);spec.loader.exec_module(deployment)
    receipt=deployment.verify(root)
    if receipt.get('deployment')!=selection or receipt.get('artifactSha256')!=artifact_sha256:
        raise RuntimeError('The complete verified deployment receipt differs from the exact selection.')
    if selection_path.read_bytes()!=original:raise RuntimeError('Selection changed during candidate admission.')
    return {'root':str(root),'python':'/usr/bin/python3','selection':selection,'selectedArtifactSha256':artifact_sha256,
        'selectedSource':source,'nativeSource':native_source,'target':'fedora44-x86_64',
        'managedInventoryVerified':True,'deploymentReceiptMatchesSelection':True,'nativeRpmAuditClean':True,
        'deploymentVerifierSha256':hashlib.sha256(verifier.read_bytes()).hexdigest()}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',required=True);parser.add_argument('--source',required=True)
    parser.add_argument('--selected-artifact',required=True);parser.add_argument('--native-source',required=True)
    parser.add_argument('--target-pid',type=int,required=True);args=parser.parse_args()
    if (os.getuid()!=1000 or os.environ.get('USER')!='augmentor-proof'
            or Path('/etc/augmentor-test-vm').read_text()!='Isolated Augmentor Fedora GNOME qualification VM\n'
            or subprocess.check_output(['systemd-detect-virt'],text=True).strip()!='qemu'
            or subprocess.check_output(['getenforce'],text=True).strip()!='Enforcing'):
        raise RuntimeError('This input probe requires the dedicated ordinary-user Fedora GNOME QEMU fixture.')
    if not re.fullmatch(r'gnome-execution-probe-input-[A-Za-z0-9_-]{1,64}',args.candidate):raise RuntimeError('Invalid owned input candidate.')
    candidate=Path.home()/args.candidate
    if not candidate.is_dir() or candidate.is_symlink() or candidate.stat().st_uid!=os.getuid() or candidate.stat().st_mode&0o077:
        raise RuntimeError('The candidate directory must be private and owned.')
    if Path(__file__).resolve()!=candidate/'probe-gnome-input.py':raise RuntimeError('Stage the exact probe with its candidate modules.')
    report_path=candidate/'input-result.json'
    if report_path.exists() or report_path.is_symlink():raise RuntimeError('Use a fresh input proof directory.')
    admission=selected_artifact(args.source,args.selected_artifact,args.native_source)
    selection=Path.home()/'.local/share/augmentor/desktop.json';original=selection.read_bytes()
    installed=Path(admission['root'])
    proc=Path('/proc')/str(args.target_pid)
    def target_start():
        if proc.stat().st_uid!=os.getuid() or str(candidate/'probe-gnome-input-target.py').encode() not in (proc/'cmdline').read_bytes().split(b'\0'):
            raise RuntimeError('The selected target is not this owned fixture.')
        return (proc/'stat').read_text().rsplit(')',1)[1].split()[19]
    start=target_start()
    def target_receipt():
        if target_start()!=start:raise RuntimeError('The owned target process changed.')
        state=private_json(candidate/'input-target-state.json')
        if state.get('format')!='augmentor-owned-gnome-input-target/1' or state.get('pid')!=args.target_pid or state.get('startTime')!=start or state.get('presented') is not True:
            raise RuntimeError('The actual target receipt does not match its process.')
        saved=candidate/'input-target-saved.json';result={'state':state}
        if saved.exists() or saved.is_symlink():
            value=private_json(saved)
            if value.get('format')!='augmentor-owned-gnome-input-saved/1' or value.get('pid')!=args.target_pid or value.get('startTime')!=start:
                raise RuntimeError('The saved file does not match the owned target.')
            result.update(saved=value,savedSha256=hashlib.sha256(saved.read_bytes()).hexdigest())
        return result
    target_receipt()
    env=dict(row.split('=',1) for row in subprocess.check_output(['systemctl','--user','show-environment'],text=True).splitlines() if '=' in row)
    if env.get('XDG_CURRENT_DESKTOP')!='GNOME' or env.get('XDG_SESSION_TYPE')!='wayland':raise RuntimeError('A normal GNOME Wayland session is required.')
    os.environ.update({key:value for key,value in env.items() if key in ('DISPLAY','WAYLAND_DISPLAY','XAUTHORITY','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','XDG_CURRENT_DESKTOP','XDG_SESSION_TYPE')})
    sources=('probe-gnome-input.py','probe-gnome-input-target.py','worker.py','gnome_control.py','gnome.py',
        'portal.py','portal_session.py','capture_stream.py','scene.py','a11y_helper.py','a11y_service.py')
    if any((candidate/name).is_symlink() or not (candidate/name).is_file() or (candidate/name).stat().st_uid!=os.getuid() for name in sources):
        raise RuntimeError('Stage ordinary-user owned regular candidate modules.')
    os.environ['QT_QPA_PLATFORM']='xcb';os.umask(0o077);sys.path.insert(0,str(candidate))
    from worker import Worker
    from gnome_control import GnomeControl
    spec=importlib.util.spec_from_file_location('owned_installed_banner',installed/'services/desktop/service.py')
    service=importlib.util.module_from_spec(spec);sys.path.append(str(installed/'services/desktop'));spec.loader.exec_module(service)
    from PySide6.QtCore import QObject,Signal,QTimer
    from PySide6.QtWidgets import QApplication
    app=QApplication([]);app.setQuitOnLastWindowClosed(False);banner=service.Banner()
    class Delivery(QObject):notice=Signal(bool,str);result=Signal(str,object);closed=Signal();request=Signal(str)
    delivery=Delivery();delivery.notice.connect(banner.update.emit)
    worker=Worker(lambda context:GnomeControl(context,delivery.notice.emit,request_timeout=180,on_request=delivery.request.emit))
    controller=worker.backend;owner='codex:owned-gnome-input-fixture'
    report={'format':'augmentor-owned-gnome-input-probe/1','selectedSource':args.source,'targetPid':args.target_pid,
        'selectedArtifactAdmission':admission,
        'targetStartTime':start,'qtPlatform':app.platformName(),'inputQualified':False,'productionInputEnabled':False,
        'probeConsentTimeoutSeconds':180,'guiTimerTicks':0,'records':[],'closed':False,'stopClicked':False,
        'sourceSha256':{name:hashlib.sha256((candidate/name).read_bytes()).hexdigest() for name in sources},
        'initialTarget':target_receipt(),'helperPids':[],'selectedApplicationChanged':False}
    def save():
        if selection.read_bytes()!=original:raise RuntimeError('Selected application bytes changed during the candidate proof.')
        temporary=report_path.with_suffix('.json.tmp');temporary.write_text(json.dumps(report,indent=2)+'\n');temporary.replace(report_path)
    pending=False;stopping=False
    def execute(operation,function):
        started=time.monotonic()
        try:value={'result':function()}
        except Exception as error:value={'error':{'kind':type(error).__name__,'message':str(error)}}
        value['durationSeconds']=time.monotonic()-started
        if controller.a11y is not None:
            helper=controller.a11y
            value['helperIdentity']={'pid':helper.process.pid,'startTime':helper.helper_start}
        delivery.result.emit(operation,value)
    def foreground():
        target_receipt();current=controller.kwin.read(controller.cancel)
        if (current.get('window') or {}).get('pid')!=args.target_pid:raise RuntimeError('Activate the observed owned target before capture/input; the probe never forces focus.')
    def captured():
        foreground();value=controller.capture(owner)
        if value['window']['pid']!=args.target_pid:raise RuntimeError('The captured target changed.')
        image=value.pop('image');value['encodedImageSha256']=hashlib.sha256(image['data'].encode()).hexdigest()
        value['targetReceipt']=target_receipt();return value
    def action(params):
        foreground();result=controller.action(owner,params)
        return {'dispatch':result,'targetReceipt':target_receipt()}
    def cleanup():
        try:controller.stop()
        finally:delivery.closed.emit()
    def stop(clicked=True):
        nonlocal stopping
        if stopping:return
        stopping=True;report['stopClicked']=clicked;report['stopAtGuiTick']=report['guiTimerTicks'];report['stopMonotonic']=time.monotonic()
        controller.request_stop();worker.submit(cleanup)
    def result(operation,value):
        nonlocal pending
        pending=False
        if operation=='connect' and controller.cancel.is_set():
            report['lateResultDiscarded']=True
            if 'error' not in value:value={'error':{'kind':'RuntimeError','message':'Late consent discarded after cancellation.'}}
        identity=value.get('helperIdentity')
        if identity is not None and identity not in report['helperPids']:report['helperPids'].append(identity)
        report['records'].append({'operation':operation,**value});save()
        if controller.cancel.is_set() or operation=='connect' and 'error' in value:stop(False)
    delivery.result.connect(result)
    def notice(active,_text):
        if not active and any(row['operation']=='connect' and row.get('result',{}).get('sharing') for row in report['records']):stop(False)
    delivery.notice.connect(notice)
    delivery.request.connect(lambda method:(report.setdefault('requests',[]).append(method),save()))
    def closed():
        report['closed']=all(getattr(controller,name) is None for name in ('consent','fd','session','snapshot','a11y'))
        report['failure']=controller.last_failure;report['stopReason']=controller.last_stop_reason
        report['cleanupAfterStopSeconds']=time.monotonic()-report['stopMonotonic']
        # This covers recorded surviving helper identities; the external owned
        # VM driver must also check for an unrecorded helper after a failed read.
        report['recordedHelperProcessesAbsent']=all(not (Path('/proc')/str(identity['pid'])).exists() for identity in report['helperPids'])
        save();app.quit()
    delivery.closed.connect(closed);banner.stop.clicked.connect(lambda:stop(True))
    timer=QTimer();timer.setInterval(50)
    def tick():
        nonlocal pending
        report['guiTimerTicks']+=1;trigger=candidate/'trigger.input.json'
        if (trigger.exists() or trigger.is_symlink()) and not stopping and not pending:
            try:
                value=private_json(trigger);operation=value.get('operation')
                if operation not in ('capture','action','inspect','finish'):raise RuntimeError('Unsupported explicit input proof operation.')
                if set(value)!=({'operation','params'} if operation=='action' else {'operation'}):raise RuntimeError('Unexpected input proof fields.')
                if operation=='action' and not isinstance(value['params'],dict):raise RuntimeError('Explicit action params must be an object.')
                trigger.unlink()
                if operation=='finish':stop(False);return
                pending=True
                function={'capture':captured,'action':lambda:action(value['params']),'inspect':target_receipt}[operation]
                worker.submit(lambda:execute(operation,function))
            except Exception as error:
                report['records'].append({'operation':'trigger-refusal','error':{'kind':type(error).__name__,'message':str(error)}});save();stop(False)
        if report['guiTimerTicks']%100==0:save()
    timer.timeout.connect(tick);timer.start();save();pending=True
    QTimer.singleShot(0,lambda:worker.submit(lambda:execute('connect',lambda:controller.connect(owner))))
    try:app.exec()
    finally:
        controller.request_stop();worker.close()
        report['selectedApplicationChanged']=selection.read_bytes()!=original;save()


if __name__=='__main__':main()
