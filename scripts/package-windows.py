#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Build a development candidate or explicitly opted-in unsigned public preview.

Stable customer delivery still requires publisher and update qualification.
Qualification locations are compiled into the candidate, never installer switches.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'services'))
from lifecycle.payload_integrity import verify_payload


def digest(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def candidate(root, arch, *, public_preview=False):
    root = Path(root)
    release = json.loads((root/'release.json').read_text(encoding='utf-8'))
    if public_preview:
        profile = json.loads((ROOT/'release/windows/public-preview.json').read_text(encoding='utf-8'))
        if any(release.get(key) != value for key, value in profile.items()):
            raise ValueError('Public preview must retain its exact published limitations.')
    if (release.get('customerDistribution') is not public_preview or
            release.get('qualificationStatus') != ('public-preview' if public_preview else 'development-candidate') or
            release.get('target') != 'windows-'+arch or
            not re.fullmatch(r'\d+\.\d+\.\d+', release.get('version', '')) or
            not re.fullmatch('[a-f0-9]{40}', release.get('sourceCommit', ''))):
        raise ValueError('Use the matching explicitly staged native distribution profile.')
    for name in ('Augmentor.exe', 'AugmentorBrowserHost.exe', 'python/python.exe',
                 'node/node.exe', 'powershell/pwsh.exe', 'updater/WinSparkle.dll',
                 'dsh/payload.json', 'scripts/launch-windows.py', 'scripts/windows-local-health.py',
                 'scripts/windows-inspect-payload.py', 'scripts/windows-recover-source.py',
                 'scripts/verify-windows-publisher.ps1', 'release/windows/signing.json',
                 'release/update-components.json',
                 'services/updates/windows_signing.py',
                 'services/lifecycle/source_restoration.py', 'services/lifecycle/payload_integrity.py',
                 'services/lifecycle/recovery_source.py', 'services/lifecycle/health_report.py',
                 'services/lifecycle/update_journal.py',
                 'components/handy/runtime/bin/handy.exe',
                 'components/handy/runtime/BUILD.json',
                 'licenses/Windows-installation-terms.txt',
                 'services/platform_adapters/private_files.py', 'services/platform_adapters/locks.py'):
        if not (root/name).is_file(): raise ValueError('Incomplete shared application payload: '+name)
    # Includes aliases/redirects and stale build output. Never reseal here: a
    # mutated staged runtime must fail intake rather than become a new baseline.
    from updates.components import installed as installed_components
    installed_components(root)
    verify_payload(root,(root/'release.json').read_bytes())
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


def build(root, arch, out, *, qualification=None, compiler_path=None, public_preview=False):
    if sys.platform != 'win32': raise ValueError('Build the package on its native Windows target.')
    root, out = Path(root).resolve(), Path(out).resolve()
    if public_preview and qualification:
        raise ValueError('Public preview cannot use disposable qualification locations.')
    release = candidate(root, arch, public_preview=public_preview)
    if out.exists() and any(out.iterdir()): raise ValueError('Use an empty package output directory.')
    out.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location('windows_builder', ROOT/'scripts/build-windows-launcher.py')
    builder = importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)
    helper = builder.build_installer_helper(out/'helper', development=bool(qualification))
    definitions = {'ApplicationId':'com.augmentor.Agent', 'ShortcutName':'Augmentor Agent',
        'ProductVersion':release['version'], 'TargetArchitecture':arch,
        'PackageSuffix':'preview' if public_preview else 'candidate',
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
        result = subprocess.run([str(tool), *['/D'+key+'='+value for key,value in definitions.items()],
            str(ROOT/'scripts/windows-application.iss')], timeout=900, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        detail = (out/'compile.log').read_text(encoding='utf-8', errors='replace')[-8192:]
        raise RuntimeError('Inno compilation failed:\n'+detail)
    suffix = 'preview' if public_preview else 'candidate'
    installer = out/f'Augmentor-{release["version"]}-windows-{arch}-{suffix}.exe'
    report = {'installer':str(installer), 'sha256':digest(installer), 'release':release,
        'installerBytes':installer.stat().st_size,
        'customerDistribution':public_preview, 'signed':False, 'applicationId':definitions['ApplicationId'],
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
    parser.add_argument('--public-preview', action='store_true')
    args = parser.parse_args()
    print(json.dumps(build(args.root, args.arch, args.out,
        qualification=args.qualification_root, compiler_path=args.compiler, public_preview=args.public_preview)))
