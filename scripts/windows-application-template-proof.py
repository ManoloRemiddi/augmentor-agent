#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Execute the exact application Inno script with a small inert fixture payload.

This proves installer event integration quickly; it never launches an application
or claims complete-runtime, actual-browser or installed update qualification.
The separate full-payload proof remains required.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import winreg

ROOT = Path(__file__).resolve().parents[1]


def prove(out, arch, compiler, fixture_executable):
    from platform_adapters.processes import OwnedProcess
    from platform_adapters.private_files import atomic_json, descriptor
    from platform_adapters.windows_identity import private_directory
    from platform_adapters.windows_browsers import command_executable
    import os
    out = Path(out)
    payload = out/'application-template-payload'
    payload.mkdir()
    # The installer only copies these markers. Runtime intake/launch is proved
    # elsewhere against the actual assembled product, never against this tree.
    for name in ('python/python.exe', 'node/node.exe', 'powershell/pwsh.exe',
                 'updater/WinSparkle.dll', 'dsh/payload.json', 'scripts/launch-windows.py'):
        target = payload/name; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b'Inert installer template fixture; never execute.\n')
    for name in ('Augmentor.exe', 'AugmentorBrowserHost.exe'):
        shutil.copy2(fixture_executable, payload/name)
    release = {'version':'0.0.1', 'sourceCommit':subprocess.check_output(
        ['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip(), 'target':'windows-'+arch,
        'customerDistribution':False, 'qualificationStatus':'development-candidate'}
    (payload/'release.json').write_text(json.dumps(release), encoding='utf-8')
    spec = importlib.util.spec_from_file_location('template_package', ROOT/'scripts/package-windows.py')
    package = importlib.util.module_from_spec(spec); spec.loader.exec_module(package)
    report = package.build(payload, arch, out/'application-template-package',
        qualification=out/'application-template-private', compiler_path=compiler)
    install = Path(report['installationDirectory'])
    flags = ['/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-']
    stages = []; removal = None
    def run(executable, label, success=True):
        child = OwnedProcess([str(executable), *flags,
            '/LOG='+str(out/('application-template-'+label+'.log'))], stdin=subprocess.DEVNULL)
        try:
            # Inno's first uninstall process exits before the copied remover
            # finishes. Observe natural exit of the whole disposable range.
            code = child.wait_graceful(timeout=60)
        finally:
            if child.job is not None:
                child.kill(); child.wait(timeout=10)  # Failed fixture cleanup only.
        assert (code == 0) == success, (label,code)
    try:
        run(report['installer'], 'initial')
        key_path = r'Software\Microsoft\Windows\CurrentVersion\Uninstall'+'\\'+report['applicationId']+'_is1'
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ|winreg.KEY_WOW64_64KEY) as key:
            removal = command_executable(winreg.QueryValueEx(key, 'UninstallString')[0])
        assert removal.is_relative_to(install)
        run(report['installer'], 'repair')
        run(removal, 'without-browser')
        assert not (install/'current/Augmentor.exe').exists()
        stages.append('actual-template-repair-and-removal-without-browser')
        run(report['installer'], 'reinstall')
        manifest = Path(report['browserManifest'])
        private_directory(manifest.parent)
        atomic_json(manifest, {'name':'com.augmentor.agent', 'description':'Inert template fixture',
            'type':'stdio', 'path':str(install/'current/AugmentorBrowserHost.exe'),
            'allowed_origins':['chrome-extension://'+'a'*32+'/']})
        original = manifest.read_bytes()
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, report['installationKey'], 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, 'BrowserManifestSHA256', 0, winreg.REG_SZ, hashlib.sha256(original).hexdigest())
            winreg.FlushKey(key)
        for key_path in report['browserKeys']:
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, '', 0, winreg.REG_SZ, str(manifest)); winreg.FlushKey(key)
        def write(content):
            with os.fdopen(descriptor(manifest, writable=True), 'wb') as stream:
                stream.write(content); stream.truncate(); stream.flush(); os.fsync(stream.fileno())
        write(original+b' ')
        run(removal, 'edited-browser-refusal', success=False)
        assert (install/'current/Augmentor.exe').is_file() and manifest.read_bytes() == original+b' '
        write(original)
        run(removal, 'owned-browser-removal')
        assert not (install/'current/Augmentor.exe').exists() and manifest.read_bytes() == original
        for key_path in [report['installationKey'], report['startupKey'], *report['browserKeys']]:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                assert winreg.QueryInfoKey(key)[:2] == (0,0), key_path
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
        stages.append('actual-template-edited-browser-refusal-and-owned-removal')
        return {'passed':True, 'stages':stages, 'scope':'Exact application Inno script with inert payload; no app/browser launch.'}
    finally:
        (out/'application-template-result.json').write_text(json.dumps({
            'stages':stages, 'scope':'Exact application Inno script with inert payload; no app/browser launch.'}, indent=2)+'\n', encoding='utf-8')
