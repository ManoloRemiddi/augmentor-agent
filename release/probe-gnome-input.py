# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Owned Fedora GNOME candidate input probe; production selection stays unchanged.

Native consent and foreground activation are manual observed operations. Each
private trigger.input.json explicitly requests capture/action/inspect/finish.
No input is inferred from readiness, dispatched automatically or replayed.
"""
import argparse
import base64
import binascii
from collections import deque
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import stat
import sys
import threading
import time
import uuid


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


def candidate_controller(candidate,installed):
    """Resolve candidate modules and verified installed dependencies, after admission."""
    sys.path.insert(0,str(candidate))
    # portal imports KWin even though GnomeControl never constructs it. The
    # reviewed eleven-file fixture owns changed modules; its other dependencies
    # come from the already verified selected artifact, without extra overlays.
    sys.path.append(str(installed/'services/desktop'))
    from worker import Worker
    from gnome_control import GnomeControl
    return Worker,GnomeControl


def retain_capture_image(candidate,image,expected_size):
    """Opt-in proof artifact only: validate and retain the original JPEG bytes."""
    if not isinstance(image,dict) or image.get('mimeType')!='image/jpeg':
        raise RuntimeError('The actual capture must contain a JPEG image.')
    width,height=image.get('width'),image.get('height')
    if (type(width) is not int or type(height) is not int or not 1<=width<=1600 or not 1<=height<=1200
            or not isinstance(expected_size,dict) or any(type(expected_size.get(key)) is not int for key in ('width','height'))
            or expected_size!={'width':width,'height':height}):
        raise RuntimeError('The capture image dimensions differ from its bounded API receipt.')
    encoded=image.get('data');maximum=900000
    if not isinstance(encoded,str) or not encoded or len(encoded)>4*((maximum+2)//3):
        raise RuntimeError('The encoded capture image exceeds the bounded JPEG contract.')
    try:raw=base64.b64decode(encoded,validate=True)
    except (ValueError,binascii.Error):raise RuntimeError('The capture image requires strict base64.') from None
    if (not raw or len(raw)>maximum or base64.b64encode(raw).decode()!=encoded
            or not raw.startswith(b'\xff\xd8\xff') or not raw.endswith(b'\xff\xd9')):
        raise RuntimeError('The capture bytes are not a bounded canonical JPEG.')
    # Use the already admitted native Qt decoder, without conversion/re-encoding.
    # Both header dimensions and a complete decode must agree with the API.
    from PySide6.QtCore import QByteArray,QBuffer,QIODevice
    from PySide6.QtGui import QImageReader
    buffer=QBuffer();buffer.setData(QByteArray(raw));buffer.open(QIODevice.OpenModeFlag.ReadOnly)
    reader=QImageReader(buffer);size=reader.size()
    if bytes(reader.format())!=b'jpeg' or (size.width(),size.height())!=(width,height):
        raise RuntimeError('The actual JPEG format or decoded dimensions differ from capture.')
    decoded=reader.read()
    if decoded.isNull() or (decoded.width(),decoded.height())!=(width,height):
        raise RuntimeError('The actual JPEG could not be decoded completely.')
    candidate=Path(candidate)
    if not candidate.is_absolute() or candidate.resolve()!=candidate or candidate.is_symlink():
        raise RuntimeError('Retain capture only inside the fresh private candidate directory.')
    directory=os.open(candidate,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        st=os.fstat(directory)
        if not stat.S_ISDIR(st.st_mode) or st.st_uid!=os.getuid() or st.st_mode&0o077:
            raise RuntimeError('Retain capture only inside the fresh private candidate directory.')
        filename='capture-'+uuid.uuid4().hex+'.jpg'
        try:fd=os.open(filename,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=directory)
        except FileExistsError:raise RuntimeError('The unique capture path already exists; no overwrite or replay.') from None
        with os.fdopen(fd,'wb') as destination:
            os.fchmod(destination.fileno(),0o600);destination.write(raw);destination.flush();os.fsync(destination.fileno())
        if candidate.is_symlink() or candidate.resolve()!=candidate or candidate.stat().st_ino!=st.st_ino or candidate.stat().st_dev!=st.st_dev:
            raise RuntimeError('The private candidate directory changed during retention; no replay.')
    finally:os.close(directory)
    return {'path':str(candidate/filename),'mimeType':'image/jpeg','bytes':len(raw),
        'sha256':hashlib.sha256(raw).hexdigest(),'width':width,'height':height,'mode':'0600'}


class IdleWatchTrace:
    """Bounded private RPC history; first error survives rollover and cleanup."""
    def __init__(self,limit=128):
        self.limit=limit;self.calls=deque(maxlen=limit);self.total=0
        self.first_error=None;self.recording_failures=0;self.mutex=threading.Lock()

    def record(self,value):
        with self.mutex:
            self.total+=1;value={**value,'sequence':self.total};self.calls.append(value)
            if value['outcome']=='error' and self.first_error is None:self.first_error=value

    def lost(self):
        with self.mutex:self.recording_failures+=1

    def snapshot(self):
        with self.mutex:
            return deepcopy({'limit':self.limit,'totalCalls':self.total,'droppedCalls':self.total-len(self.calls),
                'recordingFailures':self.recording_failures,'calls':list(self.calls),'firstError':self.first_error})


class IdleWatchBus:
    """Delegate unchanged RPCs; record only existing owner checks and Read."""
    def __init__(self,bus,stage,trace):self.bus=bus;self.stage=stage;self.trace=trace

    def __getattr__(self,name):return getattr(self.bus,name)

    def call_sync(self,name,path,interface,method,parameters,reply_type,flags,timeout_msec,cancellable):
        traced=(interface=='org.freedesktop.DBus' and method=='GetNameOwner'
            or interface=='com.augmentor.GnomeObserver' and method=='Read')
        lookup_name=None
        if traced and interface=='org.freedesktop.DBus':
            # Read only the public alias before GIO can consume a floating
            # parameters Variant. Forward that original object unchanged.
            try:
                lookup=parameters.unpack()
                if lookup in (('org.freedesktop.portal.Desktop',),('org.freedesktop.impl.portal.desktop.gnome',),('org.gnome.Shell',)):
                    lookup_name=lookup[0]
            except Exception:pass
        started=time.monotonic() if traced else None;error=None
        try:return self.bus.call_sync(name,path,interface,method,parameters,reply_type,flags,timeout_msec,cancellable)
        except BaseException as failure:error=failure;raise
        finally:
            if traced:
                try:
                    elapsed=time.monotonic()-started
                    value={'stage':self.stage,'destination':name,'path':path,'interface':interface,'method':method,
                        'timeoutMs':timeout_msec,'elapsedSeconds':elapsed,'outcome':'error' if error is not None else 'reply'}
                    if lookup_name is not None:value['lookupName']=lookup_name
                    if error is not None:
                        value['error']={'kind':type(error).__name__,'message':str(error)[:512]}
                        domain=getattr(error,'domain',None);code=getattr(error,'code',None)
                        if isinstance(domain,str):value['error']['domain']=domain
                        if type(code) is int:value['error']['code']=code
                    self.trace.record(value)
                except Exception:
                    # A diagnostic sink failure must not mask native outcome,
                    # skip cancellation, or introduce another RPC/retry.
                    try:self.trace.lost()
                    except Exception:pass


def traced_controller(base,trace):
    class TracedControl(base):
        def watch_session(self,*args):
            consent=self.consent;native=getattr(self.kwin,'native',None)
            if consent is None or native is None:return super().watch_session(*args)
            consent_bus,native_bus=consent.bus,native.bus
            consent.bus=IdleWatchBus(consent_bus,'verify',trace)
            native.bus=IdleWatchBus(native_bus,'read',trace)
            try:return super().watch_session(*args)
            finally:
                # Stop may detach/dispose these objects. Restore the captured
                # objects without reattaching them or reopening any connection.
                consent.bus=consent_bus;native.bus=native_bus
    return TracedControl


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',required=True);parser.add_argument('--source',required=True)
    parser.add_argument('--selected-artifact',required=True);parser.add_argument('--native-source',required=True)
    parser.add_argument('--target-pid',type=int,required=True)
    parser.add_argument('--trace-idle-watch',action='store_true',help='Record bounded private method/bound/elapsed diagnostics; guards stay unchanged.')
    parser.add_argument('--retain-capture-image',action='store_true',help='Retain original validated JPEG bytes privately after an explicit capture; never capture automatically.')
    args=parser.parse_args()
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
    os.environ['QT_QPA_PLATFORM']='xcb';os.umask(0o077)
    Worker,GnomeControl=candidate_controller(candidate,installed)
    spec=importlib.util.spec_from_file_location('owned_installed_banner',installed/'services/desktop/service.py')
    service=importlib.util.module_from_spec(spec);spec.loader.exec_module(service)
    from PySide6.QtCore import QObject,Signal,QTimer
    from PySide6.QtWidgets import QApplication
    app=QApplication([]);app.setQuitOnLastWindowClosed(False);banner=service.Banner()
    class Delivery(QObject):notice=Signal(bool,str);result=Signal(str,object);closed=Signal();request=Signal(str)
    delivery=Delivery();delivery.notice.connect(banner.update.emit)
    trace=IdleWatchTrace() if args.trace_idle_watch else None
    Control=traced_controller(GnomeControl,trace) if trace is not None else GnomeControl
    worker=Worker(lambda context:Control(context,delivery.notice.emit,request_timeout=180,on_request=delivery.request.emit))
    controller=worker.backend;owner='codex:owned-gnome-input-fixture'
    report={'format':'augmentor-owned-gnome-input-probe/1','selectedSource':args.source,'targetPid':args.target_pid,
        'selectedArtifactAdmission':admission,
        'targetStartTime':start,'qtPlatform':app.platformName(),'inputQualified':False,'productionInputEnabled':False,
        'probeConsentTimeoutSeconds':180,'guiTimerTicks':0,'records':[],'closed':False,'stopClicked':False,
        'sourceSha256':{name:hashlib.sha256((candidate/name).read_bytes()).hexdigest() for name in sources},
        'initialTarget':target_receipt(),'helperPids':[],'selectedApplicationChanged':False,'idleWatchTraceEnabled':trace is not None,
        'captureImageRetentionEnabled':args.retain_capture_image}
    def save():
        if selection.read_bytes()!=original:raise RuntimeError('Selected application bytes changed during the candidate proof.')
        if trace is not None:report['idleWatchRpcTrace']=trace.snapshot()
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
        if args.retain_capture_image:value['privateImageReceipt']=retain_capture_image(candidate,image,value['imageSize'])
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
