#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Build a private unsigned installation candidate from the real staged payload.

This entrypoint refuses customer artifacts until publisher/recovery gates exist.
Qualification locations are compiled into the candidate, never installer switches.
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
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def candidate(root, arch):
    root = Path(root)
    release = json.loads((root/'release.json').read_text(encoding='utf-8'))
    if (release.get('customerDistribution') is not False or
            release.get('qualificationStatus') != 'development-candidate' or
            release.get('target') != 'windows-'+arch or
            not re.fullmatch(r'\d+\.\d+\.\d+', release.get('version', '')) or
            not re.fullmatch('[a-f0-9]{40}', release.get('sourceCommit', ''))):
        raise ValueError('Use a staged native development candidate. Public delivery is not enabled.')
    for name in ('Augmentor.exe', 'AugmentorBrowserHost.exe', 'python/python.exe',
                 'node/node.exe', 'powershell/pwsh.exe', 'updater/WinSparkle.dll',
                 'dsh/payload.json', 'scripts/launch-windows.py'):
        if not (root/name).is_file(): raise ValueError('Incomplete shared application payload: '+name)
    # Inno follows source links when collecting payload. Reject them before
    # compilation rather than distributing files from outside the staged tree.
    for directory, names, files in os.walk(root, followlinks=False):
        for name in [*names, *files]:
            path = Path(directory)/name
            if path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction()):
                raise ValueError('Installer payload contains a reparse/link entry: '+str(path.relative_to(root)))
    return release


def compiler(out):
    pins = json.loads((ROOT/'release/windows/installer-candidates.json').read_text(encoding='utf-8'))['inno']
    setup = out/'inno-setup.exe'
    with urlopen(pins['url'], timeout=60) as source, setup.open('wb') as target:
        while data := source.read(1024*1024): target.write(data)
    if digest(setup) != pins['sha256']: raise ValueError('Pinned Inno compiler integrity mismatch.')
    location = out/'compiler'
    subprocess.run([str(setup), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
                    '/CURRENTUSER', '/NOICONS', '/DIR='+str(location)], check=True, timeout=120)
    return location/'ISCC.exe'


def build(root, arch, out, *, qualification=None, compiler_path=None):
    if sys.platform != 'win32': raise ValueError('Build the package on its native Windows target.')
    root, out = Path(root).resolve(), Path(out).resolve()
    release = candidate(root, arch)
    if out.exists() and any(out.iterdir()): raise ValueError('Use an empty package output directory.')
    out.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location('windows_builder', ROOT/'scripts/build-windows-launcher.py')
    builder = importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)
    helper = builder.build_installer_helper(out/'helper', development=bool(qualification))
    definitions = {'ApplicationId':'com.augmentor.Agent', 'ShortcutName':'Augmentor Agent',
        'ProductVersion':release['version'], 'TargetArchitecture':arch,
        'AllowedArchitecture':'arm64' if arch == 'arm64' else 'x64os',
        'InstallDirectory':r'{localappdata}\Programs\Augmentor Agent',
        'OutputDirectory':str(out), 'HandoffHelper':str(helper), 'PayloadDirectory':str(root),
        'ReleaseDigest':digest(root/'release.json'), 'HelperDigest':digest(helper), 'QualificationBase':'',
        'RecoveryDirectory':r'{localappdata}\Augmentor\recovery',
        'HandoffRuntime':'', 'MinimumVersion':'10.0.26200',
        'InstallationKey':r'Software\Augmentor\Installation',
        'StartupKey':r'Software\Microsoft\Windows\CurrentVersion\Run',
        'BrowserManifestPath':r'{localappdata}\Augmentor\data\browser-native-host\com.augmentor.agent.json',
        'BrowserChromeKey':r'Software\Google\Chrome\NativeMessagingHosts\com.augmentor.agent',
        'BrowserChromiumKey':r'Software\Chromium\NativeMessagingHosts\com.augmentor.agent',
        'BrowserEdgeKey':r'Software\Microsoft\Edge\NativeMessagingHosts\com.augmentor.agent'}
    if qualification:
        # Build-only locations must already be explicit and private. Never
        # modify a personal installation from a qualification command switch.
        sys.path.insert(0, str(ROOT/'services'))
        from platform_adapters.windows_identity import private_directory
        base = private_directory(Path(qualification).resolve())
        data = private_directory(base/'user data café')
        private_directory(data/'run')
        identity = 'AugmentorQ.'+hashlib.sha256(str(base).encode()).hexdigest()[:24]
        definitions.update(ApplicationId=identity, ShortcutName=identity,
            InstallDirectory=str(base/'installed café'), QualificationBase=str(data),
            RecoveryDirectory=str(data/'recovery'),
            HandoffRuntime=str(data/'run'),
            InstallationKey='Software\\AugmentorQualification\\'+identity+'\\Installation',
            StartupKey='Software\\AugmentorQualification\\'+identity+'\\Run',
            BrowserManifestPath=str(data/'data/browser-native-host/com.augmentor.agent.json'),
            BrowserChromeKey='Software\\AugmentorQualification\\'+identity+'\\ChromeNativeHost',
            BrowserChromiumKey='Software\\AugmentorQualification\\'+identity+'\\ChromiumNativeHost',
            BrowserEdgeKey='Software\\AugmentorQualification\\'+identity+'\\EdgeNativeHost',
            MinimumVersion='10.0.26100')  # Hosted Server runner only; not an advertised OS target.
    # Compile-time strings are not code. Refuse Inno preprocessor/constants
    # injection in physical paths; only the fixed Known Folder expression above
    # is intentionally interpreted as a constant.
    for key, value in definitions.items():
        if any(char in value for char in '\r\n') or '"' in value:
            raise ValueError('Unsupported installer definition: '+key)
        if key in ('OutputDirectory','HandoffHelper','PayloadDirectory','QualificationBase','HandoffRuntime') or (qualification and key in ('InstallDirectory','RecoveryDirectory')):
            if any(char in value for char in '{};"'): raise ValueError('Unsupported installer path: '+key)
    tool = Path(compiler_path) if compiler_path else compiler(out)
    with (out/'compile.log').open('w', encoding='utf-8') as log:
        subprocess.run([str(tool), *['/D'+key+'='+value for key,value in definitions.items()],
            str(ROOT/'scripts/windows-application.iss')], check=True, timeout=900, stdout=log, stderr=subprocess.STDOUT)
    installer = out/f'Augmentor-{release["version"]}-windows-{arch}-candidate.exe'
    report = {'installer':str(installer), 'sha256':digest(installer), 'release':release,
        'installerBytes':installer.stat().st_size,
        'customerDistribution':False, 'signed':False, 'applicationId':definitions['ApplicationId'],
        'installationDirectory':definitions['InstallDirectory'], 'qualificationBase':definitions['QualificationBase'],
        'installationKey':definitions['InstallationKey'], 'startupKey':definitions['StartupKey'],
        'browserKeys':[definitions[name] for name in ('BrowserChromeKey','BrowserChromiumKey','BrowserEdgeKey')],
        'browserManifest':definitions['BrowserManifestPath']}
    (out/'package.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--arch', choices=('x64','arm64'), required=True)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--qualification-root', type=Path)
    parser.add_argument('--compiler', type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.root, args.arch, args.out,
        qualification=args.qualification_root, compiler_path=args.compiler)))
