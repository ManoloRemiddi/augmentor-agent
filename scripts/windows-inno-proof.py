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
    installers = []
    for version in ('0.0.1', '0.0.2'):
        (payload/'fixture.json').write_text(json.dumps({'version':version, 'gate':str(gate)}))
        definitions = {'FixtureId':identity, 'FixtureVersion':version, 'InstallDirectory':install,
                       'PayloadDirectory':payload, 'OutputDirectory':out/'installers', 'GateFile':gate,
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
        setup(1, 'idle-update'); assert inspect('updated')['version'] == '0.0.2'
        assert sentinel.read_bytes() == sentinel_bytes
        run([uninstaller,*flags,'/LOG='+str(out/'idle-uninstall.log')])
        assert not app.exists() and sentinel.read_bytes() == sentinel_bytes
        try:
            winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry, 0, winreg.KEY_READ|winreg.KEY_WOW64_64KEY)
            raise AssertionError('Fixture registration survived removal.')
        except FileNotFoundError: pass
        native_update = prove_updater(payload, out, signer, installers[1], identity, args.arch)
        report = {'schema':'augmentor-windows-alternative-installer-proof/1', 'arch':args.arch,
                  'sourceCommit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                  'tools':pins, 'twoSimultaneousHolders':True, 'busyRepairUpdateUninstallRefused':True,
                  'failedMaintenanceReleasesAdmission':True, 'idleRepairUpdateUninstall':True,
                  'persistentDataPreserved':True, 'nativeUpdater':native_update,
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


if __name__ == '__main__': main()
