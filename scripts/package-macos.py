#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Build a self-contained development app on macOS, with no system Python/Node dependency.

The app preserves a Python interpreter because the shared services execute Python
scripts independently of the UI. Public signing, notarization and release review
are separate gates; this builder labels its artifact as development-only.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import shutil
import subprocess
import sys
import sysconfig
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
HEADER = '# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0\n'


def build_launcher(destination, component, minimum_macos):
    """Embed the pinned Python without changing the native desktop process identity."""
    if component not in ('desktop', 'browser', 'runtime'):
        raise ValueError('Unknown bundled component')
    library = Path(sys.base_prefix)/'lib'/sysconfig.get_config_var('LDLIBRARY')
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['xcrun', 'clang', '-O2', '-Wall', '-Wextra', '-Werror',
        '-target', 'arm64-apple-macos'+minimum_macos,
        '-I'+sysconfig.get_path('include'), '-DAUGMENTOR_COMPONENT="'+component+'"',
        str(ROOT/'services/platform/macos-launcher.c'), str(library),
        '-Wl,-headerpad_max_install_names',
        '-Wl,-rpath,@executable_path/../Resources/app/python/lib',
        '-o', str(destination)], check=True)
    # Standalone distributions may use the builder's absolute dylib install ID.
    # Rewrite that reference before signing; never depend on the build machine.
    install_id = subprocess.check_output(['otool', '-D', str(library)], text=True).splitlines()[1].strip()
    subprocess.run(['install_name_tool', '-change', install_id,
        '@rpath/'+library.name, str(destination)], check=True)


def disk_image(app, destination):
    """Read-only drag-install image; development status is explicit in its name."""
    with tempfile.TemporaryDirectory(prefix='augmentor-dmg-', dir=destination.parent) as temporary:
        stage = Path(temporary)
        subprocess.run(['ditto', str(app), str(stage/app.name)], check=True)
        (stage/'Applications').symlink_to('/Applications', target_is_directory=True)
        subprocess.run(['hdiutil', 'create', '-quiet', '-volname', 'Augmentor Agent Preview',
            '-srcfolder', str(stage), '-format', 'UDZO', str(destination)], check=True)
    subprocess.run(['hdiutil', 'verify', '-quiet', str(destination)], check=True)
    return {'artifact':destination.name, 'sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),
        'bytes':destination.stat().st_size, 'signedForDistribution':False, 'notarized':False}


def copy(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, destination, dirs_exist_ok=True, symlinks=True,
            ignore=shutil.ignore_patterns('__pycache__','*.pyc','.git','node_modules','test','tests'))
    else:shutil.copy2(source, destination)


def application_inventory(project):
    """Identify shipped application files, separately from third-party runtimes."""
    files={}
    for name in ('apps','dist','services','adapters','scripts','config','docs','release',
                 'LICENSE','README.md','package.json','package-lock.json'):
        entry=project/name
        paths=entry.rglob('*') if entry.is_dir() else [entry]
        for path in paths:
            relative=path.relative_to(project).as_posix()
            if path.is_symlink():
                files[relative]={'symlink':os.readlink(path)}
            elif path.is_file():
                files[relative]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size}
    return {'schema':'augmentor-application-inventory/1','files':dict(sorted(files.items())),
            'scope':'Shipped application code and documents; excludes bundled runtimes, native binaries and third-party notices. Not clean-commit or upstream-source provenance.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True, help='New, empty output directory')
    parser.add_argument('--component', choices=('desktop','companion'), default='desktop')
    parser.add_argument('--dmg', action='store_true', help='Also create a development drag-install disk image')
    args = parser.parse_args()
    desktop = args.component == 'desktop'
    if sys.platform!='darwin' or platform.machine()!='arm64':
        parser.error('Build this target on an ARM64 Mac.')
    config = json.loads((ROOT/'release/macos.json').read_text())
    if platform.python_version()!=config['python']:
        parser.error('Use the pinned standalone Python '+config['python'])
    import PySide6
    if PySide6.__version__!=config['pythonBindings']:
        parser.error('Use the pinned PySide6 '+config['pythonBindings'])
    from importlib.metadata import distributions
    normalize=lambda name:name.lower().replace('_','-').replace('.','-')
    expected={normalize(name):version for name,version in config['pythonPackages'].items()}
    base_site=Path(sys.base_prefix)/'lib'/f'python{sys.version_info.major}.{sys.version_info.minor}'/'site-packages'
    actual={normalize(d.metadata['Name']):d.version for d in distributions(path=[str(base_site)])}
    actual.update({normalize(d.metadata['Name']):d.version for d in distributions()})
    if actual!=expected:
        parser.error('Build environment differs from the tested Python package set: '+json.dumps({'expected':expected,'actual':actual},sort_keys=True))
    out = args.out.resolve()
    if out.exists() and any(out.iterdir()):parser.error('Choose a new, empty output directory.')
    out.mkdir(parents=True, exist_ok=True)
    app_name = 'Augmentor Agent Desktop' if desktop else 'Augmentor Agent Browser Companion'
    app = out/(app_name+'.app')
    contents = app/'Contents'
    resources = contents/'Resources'
    resources.mkdir(parents=True)
    # Stage production JS with platform-specific dependencies and notices.
    subprocess.run([sys.executable,str(ROOT/'scripts/stage-production.py'),'--out',str(resources/'app')],check=True)
    project = resources/'app'
    for name in ('dist','apps/native','apps/browser','scripts','services','adapters','config','docs','licenses','LICENSE','README.md','release/product.json','release/macos.json','release/macos-requirements.txt','release/dsh'):
        copy(ROOT/name, project/name)
    # python-build-standalone (used by uv) supplies a relocatable interpreter.
    # Copy its stdlib as well as this build environment's locked GUI dependencies.
    python = project/'python'
    copy(Path(sys.base_prefix), python)
    site = python/'lib'/f'python{sys.version_info.major}.{sys.version_info.minor}'/'site-packages'
    # Do not merge a standalone interpreter's old pip metadata with the locked
    # environment. Every shipped third-party package comes from this environment.
    if site.exists():shutil.rmtree(site)
    copy(Path(sysconfig.get_path('purelib')), site)
    if desktop:
        subprocess.run([sys.executable,str(ROOT/'scripts/stage-macos-qt.py'),str(site/'PySide6'),
            '--policy',str(ROOT/'release/macos-qt-unloadable-plugins.json'),
            '--out',str(project/'licenses/qt-plugin-staging.json')],check=True)
    else:
        # Keep the standalone interpreter/stdlib, but rebuild its third-party
        # site directory from the runtime allowlist instead of shipping Qt.
        shutil.rmtree(site)
        site.mkdir(parents=True)
        from importlib.metadata import distribution
        for name in ('PyYAML','websocket-client'):
            package=distribution(name)
            for entry in package.files or ():
                relative=Path(str(entry))
                if relative.is_absolute() or '..' in relative.parts:continue
                source=Path(package.locate_file(entry))
                if source.is_file():copy(source,site/relative)
        shutil.rmtree(project/'apps/native')
        # Pure socket clients also serve CLI integrations and acceptance tools;
        # retain them without any Qt presentation modules or desktop entrypoint.
        for name in ('__init__.py','pi_client.py','prompt_client.py','runtime_start.py','preferences.py'):
            relative=Path('apps/native/augmentor_linux')/name
            copy(ROOT/relative,project/relative)
        shutil.rmtree(project/'services/desktop')
    for path in python.rglob('*'):
        if path.is_symlink() and os.path.isabs(os.readlink(path)):
            raise RuntimeError('The Python distribution contains a non-relocatable symlink: '+str(path.relative_to(python)))
    subprocess.run([str(python/'bin/python3'),'-I','-c',
        ('import sys,PySide6,numpy,websocket,yaml,sounddevice,onnxruntime; from PySide6.QtWidgets import QApplication; print(sys.prefix)' if desktop else
         'import sys,websocket,yaml,importlib.util; assert importlib.util.find_spec("PySide6") is None; print(sys.prefix)')],check=True)
    subprocess.run([str(python/'bin/python3'),'-I','-B',str(ROOT/'scripts/python-license-inventory.py'),
        '--out',str(project/'licenses/python-inventory.json')],check=True)
    item = config['node']
    archive = out/'node-download.tar.gz'
    with urllib.request.urlopen(item['url'],timeout=60) as response, archive.open('wb') as stream:
        shutil.copyfileobj(response, stream)
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=item['sha256']:
        raise RuntimeError('Node archive checksum differs from the pinned release configuration.')
    with tarfile.open(archive) as bundle:
        prefix = f'node-v{item["version"]}-darwin-arm64/'
        for member, dest in [('bin/node','node/bin/node'),('LICENSE','licenses/node.txt')]:
            source = bundle.extractfile(prefix+member)
            if source is None:raise RuntimeError('Missing Node release member '+member)
            target = project/dest;target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('wb') as stream:shutil.copyfileobj(source,stream)
            target.chmod(0o755 if member=='bin/node' else 0o644)
    archive.unlink()
    subprocess.run([str(project/'node/bin/node'),'--version'],check=True)
    subprocess.run([sys.executable, str(ROOT/'scripts/stage-dsh.py'),
        '--out', str(project/'dsh'), '--node', str(project/'node/bin/node')], check=True)
    product = json.loads((ROOT/'release/product.json').read_text())
    packaged_config=dict(config)
    dsh_payload = json.loads((project/'dsh/payload.json').read_text())
    packaged_config['dsh'] = {
        'version':json.loads((ROOT/'release/dsh/package.json').read_text())['dependencies']['@deepseek-ai/dsh'],
        'lockSha256':dsh_payload['lockSha256'], 'packages':len(dsh_payload['packages']),
        'licenseReviewComplete':dsh_payload['licenseReviewComplete']}
    if not desktop:
        packaged_config.pop('qt',None);packaged_config.pop('pythonBindings',None)
        packaged_config['pythonPackages']={name:config['pythonPackages'][name] for name in ('PyYAML','websocket-client')}
    (project/'release.json').write_text(json.dumps({**product,**packaged_config,'channel':'development','component':args.component,'signedForDistribution':False},indent=2)+'\n')
    if desktop:
        native=project/'native';native.mkdir(exist_ok=True)
        helper_info=native/'helper-info.plist'
        helper_info.write_bytes(plistlib.dumps({'CFBundleIdentifier':'com.augmentor.Agent.DesktopControl',
            'CFBundleName':'Augmentor Desktop Control','CFBundleDisplayName':'Augmentor Desktop Control',
            'CFBundleVersion':product['version'],
            'NSScreenCaptureUsageDescription':'Observe the screen for your requested Augmentor desktop task.'}))
        subprocess.run(['xcrun','swiftc','-parse-as-library','-O','-target','arm64-apple-macos'+config['minimumMacOS'],
            str(project/'services/desktop/macos-helper.swift'),'-o',str(native/'augmentor-desktop-control'),
            '-Xlinker','-sectcreate','-Xlinker','__TEXT','-Xlinker','__info_plist','-Xlinker',str(helper_info)],check=True)
        subprocess.run(['xcrun','swiftc','-parse-as-library','-O','-target','arm64-apple-macos'+config['minimumMacOS'],
            str(project/'services/desktop/macos-hotkey.swift'),'-o',str(native/'augmentor-hotkey')],check=True)
    (contents/'MacOS').mkdir()
    launchers=[('augmentor-browser-host','browser'),('augmentor-runtime','runtime')]
    if desktop:launchers.insert(0,(app_name,'desktop'))
    for name, component in launchers:
        launcher = contents/'MacOS'/name
        build_launcher(launcher, component, config['minimumMacOS'])
    info = {
        'CFBundleName':'Augmentor Agent' if desktop else app_name,'CFBundleDisplayName':'Augmentor Agent' if desktop else app_name,
        'CFBundleIdentifier':'com.augmentor.Agent' if desktop else 'com.augmentor.Agent.Companion',
        'CFBundleExecutable':app_name if desktop else 'augmentor-runtime',
        'CFBundlePackageType':'APPL','CFBundleShortVersionString':product['version'],
        'CFBundleVersion':product['version'],'LSMinimumSystemVersion':config['minimumMacOS'],
        'NSHighResolutionCapable':True,
        'NSMicrophoneUsageDescription':'Augmentor uses the microphone when you enable voice input.',
        'NSScreenCaptureUsageDescription':'Augmentor observes the desktop when you request computer control.',
        'NSAppleEventsUsageDescription':'Augmentor interacts with applications when you request computer control.'}
    (contents/'Info.plist').write_bytes(plistlib.dumps(info))
    inventory=json.dumps(application_inventory(project),sort_keys=True,indent=2)+'\n'
    (project/'application-inventory.json').write_text(inventory)
    inventory_hash=hashlib.sha256(inventory.encode()).hexdigest()
    # Development signature only. A Developer ID signature and notarization are
    # required before this target can be marked ready for public distribution.
    subprocess.run(['codesign','--force','--deep','--sign','-',str(app)],check=True)
    subprocess.run(['codesign','--verify','--deep','--strict',str(app)],check=True)
    # Keep binary hashes outside the sealed bundle: code signing changes Mach-O bytes.
    if desktop:
        subprocess.run([str(python/'bin/python3'),'-I','-B',str(ROOT/'scripts/qt-library-inventory.py'),
            '--qt-version',config['qt'],'--out',str(out/'qt-library-inventory.json')],check=True)
    artifact = out/f'augmentor-{args.component}-{product["version"]}-macos-arm64-development.zip'
    subprocess.run(['ditto','-c','-k','--sequesterRsrc','--keepParent',str(app),str(artifact)],check=True)
    report = {'component':args.component,'version':product['version'],'target':config['target'],'channel':'development',
        'artifact':artifact.name,'sha256':hashlib.sha256(artifact.read_bytes()).hexdigest(),
        'bytes':artifact.stat().st_size,'signature':'ad-hoc','notarized':False,
        'publicReleaseReady':False,'applicationInventorySha256':inventory_hash,'python':config['python'],'node':item['version'],
        'dsh':packaged_config['dsh'],
        'openGates':['guided managed setup','required plugin provisioning','store migration',
            'coordinated auto-update','installed acceptance','DSH feature qualification',
            *(['desktop control','permission attribution'] if desktop else []),
            'license review','Developer ID signing and notarization']}
    if args.dmg:
        report['diskImage'] = disk_image(app, artifact.with_suffix('.dmg'))
    (out/'artifacts.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':main()
