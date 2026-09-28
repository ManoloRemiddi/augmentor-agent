#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Qualify candidate installer refusal and native signed-update checks in isolation."""
import argparse
import base64
import functools
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import threading
import time
from urllib.request import urlopen
import uuid
import winreg
from xml.sax.saxutils import quoteattr
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def run(command, *, expected=0, **options):
    result = subprocess.run(list(map(str, command)), timeout=120, **options)
    if expected is not None: assert result.returncode == expected, (command[0], result.returncode)
    return result


def wait_for(path):
    end = time.monotonic()+30
    while not path.is_file() and time.monotonic() < end: time.sleep(.05)
    return json.loads(path.read_text(encoding='utf-8'))


def download(spec, target):
    with urlopen(spec['url'], timeout=60) as source: content = source.read()
    assert hashlib.sha256(content).hexdigest() == spec['sha256'], 'Candidate tool integrity mismatch'
    target.write_bytes(content)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--arch', choices=('x64', 'arm64'), required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    assert sys.platform == 'win32'
    out, runtime = args.out.resolve(), args.runtime.resolve()
    if out.exists() and any(out.iterdir()): parser.error('Choose an empty proof directory.')
    out.mkdir(parents=True, exist_ok=True)
    pins = json.loads((ROOT/'release/windows/installer-candidates.json').read_text())
    # Inno hashes/truncates long AppIds when naming their uninstall key.
    # Keep this unique disposable identity below that threshold.
    identity = 'AugmentorQ.'+uuid.uuid4().hex
    registry = r'Software\Microsoft\Windows\CurrentVersion\Uninstall'+'\\'+identity+'_is1'
    data, payload, install = out/'persistent', out/'payload', out/'installed café with spaces'
    data.mkdir(); payload.mkdir()
    sys.path.insert(0,str(ROOT/'services'))
    from platform_adapters.windows_identity import private_directory
    handoff_state=private_directory(data/'handoff')
    gate = data/'admission.lock'; gate.touch()
    sentinel = data/'settings.json'; sentinel.write_text('{"model":"retain this selection"}')
    sentinel_bytes = sentinel.read_bytes()
    compiler_setup = out/'inno-setup.exe'
    download(pins['inno'], compiler_setup)
    compiler = out/'compiler'
    run([compiler_setup, '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/CURRENTUSER', '/NOICONS', '/DIR='+str(compiler)])
    archive = out/'sparkle.zip'; download(pins['winsparkle'], archive)
    signer = out/'winsparkle-tool.exe'
    with zipfile.ZipFile(archive) as z:
        prefix = 'WinSparkle-'+pins['winsparkle']['version']+'/'
        signer.write_bytes(z.read(prefix+'bin/winsparkle-tool.exe'))
        (payload/'WinSparkle.dll').write_bytes(z.read(prefix+('ARM64' if args.arch == 'arm64' else 'x64')+'/Release/WinSparkle.dll'))
        for name in ('COPYING', 'COPYING.expat', 'AUTHORS'):
            (out/('WinSparkle-'+name)).write_bytes(z.read(prefix+name))
    binary = (payload/'WinSparkle.dll').read_bytes()
    offset = struct.unpack_from('<I', binary, 0x3c)[0]
    assert binary[offset:offset+4] == b'PE\0\0'
    assert struct.unpack_from('<H', binary, offset+4)[0] == {'x64':0x8664,'arm64':0xaa64}[args.arch]
    shutil.copytree(runtime/'python', payload/'python', ignore=shutil.ignore_patterns('site-packages', '__pycache__', '*.pyc'))
    (payload/'python/Lib/site-packages').mkdir(parents=True, exist_ok=True)
    (payload/'scripts').mkdir()
    shutil.copy2(ROOT/'scripts/windows-inno-fixture.py', payload/'scripts/launch-windows.py')
    spec = importlib.util.spec_from_file_location('builder', ROOT/'scripts/build-windows-launcher.py')
    builder = importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)
    builder.build_launcher(payload, args.arch, name='AugmentorFixture.exe')
    handoff_helper=builder.build_installer_helper(out/'handoff-helper',development=True)
    registration_key=r'Software\AugmentorQualification'+'\\'+identity+'\\OwnedValues'
    registration_base=private_directory(out/'registration-private')
    from platform_adapters.private_files import atomic_json
    registration_manifest=private_directory(registration_base/'browser')/'host.json'
    atomic_json(registration_manifest,{'fixture':'private manifest retention'})
    long_tree=registration_base/'long-payload'
    nested=long_tree.joinpath(*['nested-'+str(index)+'-'+'x'*55 for index in range(6)])
    extended=Path('\\\\?\\'+str(nested));extended.mkdir(parents=True)
    (extended/'ordinary.txt').write_text('fixture ordinary payload beyond MAX_PATH')
    definitions={'FixtureId':identity+'.reg','QualificationBase':registration_base,
        'OutputDirectory':out/'registration-installer','HandoffHelper':handoff_helper,'RegistryKey':registration_key,
        'ManifestPath':registration_manifest,'ManifestDigest':hashlib.sha256(registration_manifest.read_bytes()).hexdigest(),
        'LongTree':long_tree}
    with (out/'registration-compile.log').open('w',encoding='utf-8') as log:
        run([compiler/'ISCC.exe',*['/D'+key+'='+str(value) for key,value in definitions.items()],
            ROOT/'scripts/windows-registration-fixture.iss'],stdout=log,stderr=subprocess.STDOUT)
    run([out/'registration-installer/registration-fixture.exe','/VERYSILENT','/SUPPRESSMSGBOXES',
         '/NORESTART','/SP-','/LOG='+str(out/'registration.log')])
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,registration_key) as registered:
        assert winreg.QueryInfoKey(registered)[:2]==(0,1)
        assert winreg.QueryValueEx(registered,'Unrelated')==('preserve',winreg.REG_SZ)
    winreg.DeleteKey(winreg.HKEY_CURRENT_USER,registration_key)
    template_spec=importlib.util.spec_from_file_location('application_template_proof', ROOT/'scripts/windows-application-template-proof.py')
    template=importlib.util.module_from_spec(template_spec);template_spec.loader.exec_module(template)
    application_template=template.prove(out,args.arch,compiler/'ISCC.exe',payload/'AugmentorFixture.exe',runtime)
    installers = []
    for version in ('0.0.1', '0.0.2'):
        (payload/'fixture.json').write_text(json.dumps({'version':version, 'gate':str(gate)}))
        definitions = {'FixtureId':identity, 'FixtureVersion':version, 'InstallDirectory':install,
                       'PayloadDirectory':payload, 'OutputDirectory':out/'installers', 'GateFile':gate,
                       'HandoffReady':handoff_state/'ready.json', 'HandoffContinue':handoff_state/'continue',
                       'HandoffHelper':handoff_helper,'HandoffRuntime':handoff_state,
                       'AllowedArchitecture':'arm64' if args.arch == 'arm64' else 'x64os'}
        with (out/('compile-'+version+'.log')).open('w', encoding='utf-8') as log:
            run([compiler/'ISCC.exe', *['/D'+key+'='+str(value) for key,value in definitions.items()],
                 ROOT/'scripts/windows-inno-fixture.iss'], stdout=log, stderr=subprocess.STDOUT)
        installers.append(out/'installers'/('fixture-'+version+'.exe'))
    flags = ['/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-']
    def setup(index, label, *extra, expected=0):
        return run([installers[index], *flags, '/LOG='+str(out/(label+'.log')), *extra], expected=expected)
    app = install/'AugmentorFixture.exe'
    def inspect(name):
        report = out/(name+'.json'); run([app,'--inspect',report]); return wait_for(report)
    holders = []
    try:
        setup(0, 'initial')
        assert inspect('initial')['version'] == '0.0.1'
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry, 0, winreg.KEY_READ|winreg.KEY_WOW64_64KEY) as key:
            removal = winreg.QueryValueEx(key, 'UninstallString')[0]
        # Parse the registry-provided executable using actual Windows quoting.
        sys.path.insert(0, str(ROOT/'services'))
        from platform_adapters.windows_browsers import command_executable
        uninstaller = command_executable(removal)
        assert uninstaller.is_relative_to(install)
        for number in range(2):
            report = out/('active-'+str(number)+'.json'); stop = out/('stop-'+str(number))
            holder = subprocess.Popen([str(app),'--hold',str(report),str(stop)])
            holders.append((holder,stop)); assert wait_for(report)['pid'] == holder.pid
        assert setup(0, 'busy-repair', expected=None).returncode != 0
        assert setup(1, 'busy-update', expected=None).returncode != 0
        assert run([uninstaller,*flags,'/LOG='+str(out/'busy-uninstall.log')],expected=None).returncode != 0
        assert all(process.poll() is None for process,_stop in holders)
        assert inspect('after-refusal')['version'] == '0.0.1'
        for process,stop in holders: stop.touch(); assert process.wait(timeout=15) == 0
        # A failure after admission acquisition must release it for the next launch.
        assert setup(1, 'cancelled-after-gate', '/failaftergate=1', expected=None).returncode != 0
        report = out/'after-cancel.json'; stop = out/'stop-after-cancel'
        holder = subprocess.Popen([str(app),'--hold',str(report),str(stop)])
        holders.append((holder,stop)); wait_for(report); stop.touch(); assert holder.wait(timeout=15)==0
        setup(0, 'idle-repair'); assert inspect('repair')['version'] == '0.0.1'
        assert setup(1,'invalid-handoff','/startupowner='+str(os.getpid()),'/startuphandle=0',expected=None).returncode!=0
        assert inspect('after-invalid-handoff')['version']=='0.0.1'
        setup(1, 'idle-update'); assert inspect('updated')['version'] == '0.0.2'
        handoff=prove_handoff(installers[1],handoff_state,out)
        assert inspect('after-handoff')['version']=='0.0.2'
        assert sentinel.read_bytes() == sentinel_bytes
        run([uninstaller,*flags,'/LOG='+str(out/'idle-uninstall.log')])
        assert not app.exists() and sentinel.read_bytes() == sentinel_bytes
        try:
            winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry, 0, winreg.KEY_READ|winreg.KEY_WOW64_64KEY)
            raise AssertionError('Fixture registration survived removal.')
        except FileNotFoundError: pass
        native_update = prove_updater(payload, out, signer, installers[1], identity, args.arch)
        signed_bundle = prove_signed_bundle(runtime, payload, out, signer, installers[1], identity, args.arch)
        report = {'schema':'augmentor-windows-alternative-installer-proof/1', 'arch':args.arch,
                  'sourceCommit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                  'tools':pins, 'twoSimultaneousHolders':True, 'busyRepairUpdateUninstallRefused':True,
                  'failedMaintenanceReleasesAdmission':True, 'idleRepairUpdateUninstall':True,
                  'persistentDataPreserved':True, 'nativeUpdater':native_update, 'signedBundle':signed_bundle,
                  'nativeTypedOwnedRegistry':True, 'nativeBrowserManifestPinned':True, 'nativeLongPayloadPaths':True,
                  'applicationTemplate':application_template,
                  'independentSetupHandoff':handoff,
                  'productionInstallerQualified':False,
                  'limits':['Disposable unsigned fixture; no full Augmentor shutdown/migration/rollback or ordinary-user client acceptance.',
                            'Updater inspects signed downloads in a callback; actual installer lifecycle is exercised separately.',
                            'Installer/compiler run as x64, emulated on ARM; application, Python and updater DLL are native to target.']}
        (out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(report))
    finally:
        for process,stop in holders:
            stop.touch()
            if process.poll() is None: process.wait(timeout=15)
        if (install/'unins000.exe').is_file(): run([install/'unins000.exe',*flags],expected=None)
        if (compiler/'unins000.exe').is_file(): run([compiler/'unins000.exe',*flags],expected=None)


def prove_handoff(installer,state,out):
    """Actual Inno loader + Setup process, not just a Python recipient."""
    import win32api,win32con,win32event,win32process
    from lifecycle.windows_startup import Startup
    from lifecycle.windows_installer_process import InstallerProcess
    from platform_adapters.windows_identity import private_file_descriptor,private_lock_descriptor
    from platform_adapters import locks
    from platform_adapters.paths import private_directory
    from platform_adapters.private_files import read_json
    from lifecycle.update_journal import recovery_action
    # The fixture supplies the digest. Production must obtain it from the
    # signed release-verification boundary; hashing a download is not trust.
    staged=state/'installer.exe'
    content=installer.read_bytes();digest=hashlib.sha256(content).hexdigest()
    with os.fdopen(private_file_descriptor(staged,writable=True,exclusive=True),'wb') as stream:stream.write(content)
    try:
        with InstallerProcess(staged,'0'*64,[]):pass
    except ValueError as error:assert 'bytes changed' in str(error)
    else:raise AssertionError('An installer with a mismatched digest was launched.')
    outer_jobs=[]
    # Preserve the earlier transfer mechanism case and exercise its replacement
    # over authenticated IPC with a distinct explicit apply decision.
    for authenticated,crash,blocked,observer_job in ((False,False,False,False),(False,True,False,False),
            (True,False,False,False),(True,True,False,False),(True,False,True,False),
            (True,False,False,True),(True,True,False,True)):
        journal=private_directory(state/('journal-'+str(authenticated)+'-'+str(crash)+'-'+str(blocked)+'-'+str(observer_job))) if authenticated else None
        for name in ('ready.json','coordinator.json','continue','parent-release'):
            (state/name).unlink(missing_ok=True)
        parent=subprocess.Popen([sys.executable,'-I','-Xutf8','-B',str(ROOT/'scripts/windows-inno-handoff-proof.py'),
            '--installer',str(staged),'--sha256',digest,'--state',str(state),'--log',
            str(out/('handoff-'+('observer-' if observer_job else '')+('authenticated-' if authenticated else '')+('blocked' if blocked else 'crash' if crash else 'exit')+'.log')),
            *(['--authenticated','--journal',str(journal)] if authenticated else []),
            *(['--observer-job'] if observer_job else []),
            *(['--blocked-final-lease'] if blocked else [])],
            stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        setup_process=None;loader=None;blocker=None;contained=None
        try:
            deadline=time.monotonic()+30
            while not (state/'coordinator.json').is_file():
                if parent.poll() is not None:
                    _output,error=parent.communicate(timeout=5)
                    raise AssertionError('The disposable installer coordinator exited before readiness: '+error.decode('utf-8',errors='replace')[-4000:])
                if time.monotonic()>=deadline:raise TimeoutError('The disposable installer coordinator did not become ready.')
                time.sleep(.05)
            info=wait_for(state/'coordinator.json');ready=wait_for(state/'ready.json')
            outer_jobs.append(info['outerRunnerJobObserved'])
            assert info['actualSetupInInstallerJob'] and info['unrelatedPidRefused'] and info['setupPid']==ready['pid']
            assert info['coordinatorLifetimeLease']
            assert info['observerBreakawayVerified']==observer_job
            if observer_job:
                contained=win32api.OpenProcess(win32con.SYNCHRONIZE,False,info['containedProbePid'])
                assert win32event.WaitForSingleObject(contained,0)==win32event.WAIT_TIMEOUT
            lifetime=private_lock_descriptor(state/'installation.lock')
            try:
                try:locks.flock(lifetime,locks.LOCK_EX|locks.LOCK_NB)
                except BlockingIOError:pass
                else:raise AssertionError('The coordinator did not retain its lifetime lease.')
            finally:os.close(lifetime)
            try:
                writable=private_file_descriptor(staged,writable=True)
            except OSError as error:assert error.winerror==32,error
            else:
                os.close(writable)
                raise AssertionError('Verified installer bytes remained writable during launch.')
            loader=win32api.OpenProcess(win32con.SYNCHRONIZE|win32con.PROCESS_QUERY_LIMITED_INFORMATION,False,info['installerPid'])
            setup_process=win32api.OpenProcess(win32con.SYNCHRONIZE|win32con.PROCESS_QUERY_INFORMATION|
                win32con.PROCESS_VM_READ,False,ready['pid'])
            assert Path(win32process.GetModuleFileNameEx(setup_process,0)).name.lower().endswith('.tmp'), 'The actual extracted Setup process must adopt the handle.'
            assert ready['pid']!=parent.pid and ready['pid']!=info['installerPid']
            if blocked:
                blocker=private_lock_descriptor(state/'installation.lock')
                locks.flock(blocker,locks.LOCK_SH|locks.LOCK_NB)
            if crash:parent.kill()  # Deliberate disposable coordinator crash.
            else:(state/'parent-release').write_text('release',encoding='utf-8')
            _out,errors=parent.communicate(timeout=10)
            if not crash:assert parent.returncode==0,errors.decode('utf-8',errors='replace')
            if contained is not None:
                assert win32event.WaitForSingleObject(contained,10000)==win32event.WAIT_OBJECT_0
            if journal:
                recorded=read_json(journal/'active.json')
                assert recorded['phase']=='apply-acknowledged' and recorded['target']['sha256']==digest
                assert recovery_action(recorded)=='inspect-installation'
            assert win32event.WaitForSingleObject(setup_process,0)==win32event.WAIT_TIMEOUT
            for maintenance in (False,True):
                try:
                    with Startup(state,maintenance=maintenance):pass
                except OSError as error:assert error.winerror==32,error
                else:raise AssertionError('Inno did not retain startup exclusion after the coordinator exited.')
            (state/'continue').write_text('continue',encoding='utf-8')
            assert win32event.WaitForSingleObject(setup_process,30000)==win32event.WAIT_OBJECT_0
            exit_code=win32process.GetExitCodeProcess(setup_process)
            assert (exit_code!=0 if blocked else exit_code==0),exit_code
            assert win32event.WaitForSingleObject(loader,10000)==win32event.WAIT_OBJECT_0
            with Startup(state):pass
        finally:
            (state/'continue').write_text('continue',encoding='utf-8')
            if parent.poll() is None:parent.kill()
            parent.communicate(timeout=10)
            for process in (setup_process,loader,contained):
                if process is not None:win32event.WaitForSingleObject(process,30000);process.Close()
            if blocker is not None:os.close(blocker)
    for name in ('ready.json','coordinator.json','continue','parent-release'):(state/name).unlink(missing_ok=True)
    cancelled_journal=private_directory(state/'journal-cancel')
    run([sys.executable,'-I','-Xutf8','-B',ROOT/'scripts/windows-inno-handoff-proof.py',
        '--installer',staged,'--sha256',digest,'--state',state,'--log',out/'handoff-abort.log',
        '--authenticated','--cancel-before-apply','--journal',cancelled_journal])
    assert read_json(cancelled_journal/'active.json')['phase']=='installer-ready'
    assert not (state/'ready.json').exists(),'Setup progressed after cancellation without APPLY.'
    with Startup(state):pass
    run([sys.executable,'-I','-Xutf8','-B',ROOT/'scripts/windows-inno-handoff-proof.py',
        '--installer',staged,'--sha256',digest,'--state',state,'--log',out/'handoff-wrong-coordinator.log',
        '--authenticated','--wrong-coordinator'])
    assert not (state/'ready.json').exists(),'Setup progressed with the wrong coordinator identity.'
    with Startup(state):pass
    interrupted_journal=private_directory(state/'journal-before-apply-crash')
    parent=subprocess.Popen([sys.executable,'-I','-Xutf8','-B',str(ROOT/'scripts/windows-inno-handoff-proof.py'),
        '--installer',str(staged),'--sha256',digest,'--state',str(state),'--log',str(out/'handoff-before-apply-crash.log'),
        '--authenticated','--crash-before-apply','--journal',str(interrupted_journal)],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    aborted=None
    try:
        pid=wait_for(state/'prepared.json')['pid']
        aborted=win32api.OpenProcess(win32con.SYNCHRONIZE,False,pid)
        (state/'crash-now').write_text('crash disposable coordinator',encoding='utf-8')
        _output,errors=parent.communicate(timeout=10)
        assert parent.returncode==79,errors.decode('utf-8',errors='replace')
        recorded=read_json(interrupted_journal/'active.json')
        assert recorded['phase']=='installer-ready' and recovery_action(recorded)=='inspect-stopped-components'
        assert win32event.WaitForSingleObject(aborted,10000)==win32event.WAIT_OBJECT_0
    finally:
        if parent.poll() is None:parent.kill()
        parent.communicate(timeout=10)
        if aborted is not None:aborted.Close()
    assert not (state/'ready.json').exists(),'Setup progressed after coordinator loss before APPLY.'
    with Startup(state):pass
    return {'actualExtractedSetupOwnsGate':True,'parentNormalExit':True,'parentCrash':True,
        'newStartupAndSecondWriterRefused':True,'completedRepairReleasesGate':True,
        'invalidTransferRefusedBeforeVersionChange':True,
        'verifiedDigestBoundBeforeLaunch':True,'artifactWriteExcludedWhileObserved':True,
        'actualSetupJobObserved':True,'unrelatedPidRefused':True,'normalCloseDoesNotTerminateInstaller':True,
        'authenticatedPipeTransfer':True,'abortBeforeApply':True,'coordinatorCrashBeforeApplyRefused':True,
        'unrelatedPipeClientRefused':True,'wrongCoordinatorPidRefused':True,
        'durableJournalBeforeAndAfterApply':True,'noAutomaticReplayFromSavedJournal':True,
        'coordinatorLifetimeLeaseObserved':True,'actualSetupAcquiresFinalInstallationLease':True,
        'additionalLifetimeLeaseRefusesFileApplication':True,
        'qualificationRetainsOuterRunnerJob':True,
        'explicitObserverJobBreakaway':True,'observerExitAndCrashPreserveSetup':True,
        'ordinaryObserverChildTerminatesOnExitAndCrash':True,
        'outerRunnerJobObservations':outer_jobs,
        'productionInstallerQualified':False}


def prove_updater(payload, out, signer, installer, identity, arch):
    feed = out/'feed'; feed.mkdir()
    shutil.copy2(installer, feed/'update.exe')
    key = out/'ephemeral-signing.key'
    generated = run([signer,'generate-key','--file',key],capture_output=True,text=True).stdout
    public = re.search(r'Public key:\s*([A-Za-z0-9+/=]+)', generated).group(1)
    try: signature = run([signer,'sign','-f',key,installer],capture_output=True,text=True).stdout.strip()
    finally: key.unlink(missing_ok=True)
    assert len(base64.b64decode(signature,validate=True)) == 64
    digest = hashlib.sha256(installer.read_bytes()).hexdigest()
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self,*args): pass
    server = ThreadingHTTPServer(('127.0.0.1',0),functools.partial(QuietHandler,directory=str(feed)))
    thread = threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    results = {}
    try:
        for name in ('good','bad-signature','busy','wrong-architecture'):
            sig = signature if name != 'bad-signature' else ('A' if signature[0]!='A' else 'B')+signature[1:]
            target = arch if name != 'wrong-architecture' else ('arm64' if arch=='x64' else 'x64')
            url = f'http://127.0.0.1:{server.server_port}'
            (feed/(name+'.xml')).write_text('<?xml version="1.0" encoding="UTF-8"?><rss version="2.0" '
                'xmlns:sparkle="http://www.andymatuschak.org/xml-namespaces/sparkle"><channel><title>Isolated test</title>'
                '<item><title>0.0.2</title><sparkle:version>0.0.2</sparkle:version><enclosure '
                f'url={quoteattr(url+"/update.exe")} length={quoteattr(str(installer.stat().st_size))} '
                f'type="application/octet-stream" sparkle:os="windows-{target}" sparkle:edSignature={quoteattr(sig)} />'
                '</item></channel></rss>',encoding='utf-8')
            settings = {'id':identity, 'registry':r'Software\AugmentorQualification'+'\\'+identity+'\\'+name,
                        'url':url+'/'+name+'.xml', 'key':public, 'busy':name=='busy',
                        'progress':str(out/(name+'-progress.json'))}
            config = out/(name+'-settings.json'); config.write_text(json.dumps(settings))
            path = out/(name+'-updater.json')
            run([payload/'AugmentorFixture.exe','--sparkle',path,config])
            result = wait_for(path)
            if name == 'good': assert result['downloadHandled'] and result['downloadSha256']==digest, result
            elif name == 'busy': assert result['canShutdown'] is False and not result['downloadHandled'], result
            elif name == 'bad-signature': assert 'error' in result['events'] and not result['downloadHandled'], result
            else: assert 'no-update' in result['events'] and not result['downloadHandled'], result
            results[name] = result
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER,settings['registry'])
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)
    return results


def prove_signed_bundle(runtime, payload, out, signer, installer, identity, arch):
    """Actual signed WinSparkle ZIP delivery into the shared release verifier."""
    from platform_adapters.windows_identity import private_directory
    feed=out/'bundle-feed';feed.mkdir()
    cache=private_directory(out/'bundle-cache')
    key=out/'ephemeral-bundle-download.key'
    generated=run([signer,'generate-key','--file',key],capture_output=True,text=True).stdout
    download_public=re.search(r'Public key:\s*([A-Za-z0-9+/=]+)',generated).group(1)
    current={'version':'0.0.1','sourceCommit':'a'*40,'target':'windows-'+arch,
        'channel':'qualification','sha256':'c'*64,'dataSchema':1,'readableDataSchemas':[1]}
    digest=hashlib.sha256(installer.read_bytes()).hexdigest()
    now=int(time.time())
    manifest={'schema':'augmentor-release-bundle/1','release':{**current,'version':'0.0.2',
        'sourceCommit':'b'*40,'sha256':digest},'installerBytes':installer.stat().st_size,
        'minimumOSBuild':26200,'protocols':{'product':'augmentor/1'},'issuedAt':now-60,'expiresAt':now+3600}
    sign_metadata="""
      const c=require('node:crypto'), chunks=[];
      process.stdin.on('data',b=>chunks.push(b));process.stdin.on('end',()=>{
        const pair=c.generateKeyPairSync('ed25519');
        const raw=Buffer.concat(chunks), public=pair.publicKey.export({format:'jwk'});
        console.log(JSON.stringify({key:Buffer.from(public.x,'base64url').toString('base64'),
          signature:c.sign(null,Buffer.concat([Buffer.from('augmentor-release-manifest/1\\0'),raw]),pair.privateKey).toString('base64')}));
      });
    """
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self,*args): pass
    server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(QuietHandler,directory=str(feed)))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    results={}
    try:
        for name in ('good','wrong-metadata-architecture','bad-metadata-signature','replaced-installer'):
            value=json.loads(json.dumps(manifest))
            if name=='wrong-metadata-architecture': value['release']['target']='windows-'+('x64' if arch=='arm64' else 'arm64')
            raw=json.dumps(value).encode('utf-8')
            signed=json.loads(run([runtime/'node/node.exe','-e',sign_metadata],input=raw,capture_output=True).stdout)
            metadata_signature=base64.b64decode(signed['signature'])
            if name=='bad-metadata-signature':metadata_signature=b'X'*64
            bundle=feed/(name+'.zip')
            with zipfile.ZipFile(bundle,'w',compression=zipfile.ZIP_STORED) as archive:
                archive.writestr('manifest.json',raw);archive.writestr('manifest.sig',metadata_signature)
                if name=='replaced-installer':archive.writestr('installer.exe',b'X'*installer.stat().st_size)
                else:archive.write(installer,'installer.exe')
            signature=run([signer,'sign','-f',key,bundle],capture_output=True,text=True).stdout.strip()
            url=f'http://127.0.0.1:{server.server_port}'
            (feed/(name+'.xml')).write_text('<?xml version="1.0" encoding="UTF-8"?><rss version="2.0" '
                'xmlns:sparkle="http://www.andymatuschak.org/xml-namespaces/sparkle"><channel><title>Isolated bundle test</title>'
                '<item><title>0.0.2</title><sparkle:version>0.0.2</sparkle:version><enclosure '
                f'url={quoteattr(url+"/"+name+".zip")} length={quoteattr(str(bundle.stat().st_size))} '
                f'type="application/octet-stream" sparkle:os="windows-{arch}" sparkle:edSignature={quoteattr(signature)} />'
                '</item></channel></rss>',encoding='utf-8')
            settings={'id':identity,'registry':r'Software\AugmentorQualification'+'\\'+identity+'\\bundle-'+name,
                'url':url+'/'+name+'.xml','key':download_public,'busy':False,
                'progress':str(out/('bundle-'+name+'-progress.json')),'dllPath':str(payload/'WinSparkle.dll'),
                'cache':str(cache),'bundlePolicy':{'public_key':signed['key'],'node':str(runtime/'node/node.exe'),
                    'current':current,'protocols':manifest['protocols'],'os_build':26200}}
            config=out/('bundle-'+name+'-settings.json');config.write_text(json.dumps(settings),encoding='utf-8')
            destination=out/('bundle-'+name+'-result.json')
            before=set(cache.iterdir())
            run([runtime/'python/python.exe','-I','-Xutf8','-B',ROOT/'scripts/windows-inno-fixture.py',
                 '--signed-bundle',destination,config])
            result=wait_for(destination)
            if name=='good':
                assert result['downloadHandled'] and result['verifiedRelease']==manifest['release'],result
                assert result['retainedInstallerSha256']==digest,result
                assert len(set(cache.iterdir())-before)==1
            else:
                assert not result['downloadHandled'] and result.get('callbackFailed'),result
                assert set(cache.iterdir())==before
            results[name]=result
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER,settings['registry'])
    finally:
        key.unlink(missing_ok=True)
        server.shutdown();server.server_close();thread.join(timeout=5)
    return {'cases':results,'scope':'Native WinSparkle signed ZIP callback and real private staging; ephemeral keys, synthetic release/OS policy, no installer execution.'}


if __name__ == '__main__': main()
