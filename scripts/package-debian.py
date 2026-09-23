#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Build separate Debian runtime/companion and desktop packages from tested code.

Build-time network fetches are pinned. Installing the resulting packages does not
require npm or fetch JavaScript dependencies. System Qt remains replaceable.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
HEADER = '# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0\n'


def write(path, text, executable=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(0o755 if executable else 0o644)


def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, target, dirs_exist_ok=True, ignore=shutil.ignore_patterns(
            '__pycache__', '*.pyc', 'node_modules', '.git', '.github', 'test', 'tests', 'trace'))
    else:
        shutil.copy2(source, target)


def node_runtime(app, configuration, cache):
    item = configuration['node']; archive = cache / Path(item['url']).name
    if not archive.exists():
        temporary = archive.with_suffix('.download')
        with urllib.request.urlopen(item['url'], timeout=60) as response, temporary.open('wb') as out:
            shutil.copyfileobj(response, out)
        temporary.replace(archive)
    with archive.open('rb') as stream: archive_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
    if archive_hash != item['sha256']:
        raise ValueError('Node archive checksum differs from the reviewed release configuration')
    prefix = f'node-v{item["version"]}-linux-x64/'
    with tarfile.open(archive) as bundle:
        # Only the Node executable and its complete upstream notices are shipped.
        # npm, headers and development tools are not required at runtime.
        for member, dest in [('bin/node', 'node/bin/node'), ('LICENSE', 'licenses/node.txt')]:
            source = bundle.extractfile(prefix + member)
            if source is None:
                raise ValueError('Node release is missing ' + member)
            target = app / dest; target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('wb') as out: shutil.copyfileobj(source, out)
            target.chmod(0o755 if member == 'bin/node' else 0o644)


def native_notices(app, configuration):
    expected = {'node/bin/node': 'node', 'node_modules/@esbuild/linux-x64/bin/esbuild': 'esbuild',
                'node_modules/@earendil-works/pi-coding-agent/node_modules/@esbuild/linux-x64/bin/esbuild': 'esbuild',
                'node_modules/@earendil-works/pi-coding-agent/node_modules/@silvia-odwyer/photon-node/photon_rs_bg.wasm': 'photon'}
    components = []
    for path in sorted(app.rglob('*')):
        if not path.is_file() or path.is_symlink(): continue
        with path.open('rb') as stream: magic = stream.read(4)
        if magic not in (b'\x7fELF', b'\x00asm', b'\xcf\xfa\xed\xfe', b'\xfe\xed\xfa\xcf') and not magic.startswith(b'MZ'):
            continue
        relative = path.relative_to(app).as_posix()
        if relative not in expected:
            raise ValueError('Unreviewed native executable in distribution: ' + relative)
        component = expected[relative]
        content = path.read_bytes()
        if component == 'esbuild':
            versions = set(re.findall(rb'\bgo1\.\d+(?:\.\d+)?\b', content))
            if versions != {b'go1.26.4'}:
                raise ValueError('esbuild Go toolchain changed; review its source/license record')
            version = subprocess.check_output([str(path), '--version'], text=True).strip()
            if version != '0.28.1': raise ValueError('Unexpected esbuild version')
            notices = ['upstream/esbuild.txt', 'upstream/go.txt', 'upstream/esbuild-xxhash.txt']
        elif component == 'photon':
            record = json.loads((app / 'licenses/photon/BUILD.json').read_text())
            if hashlib.sha256(content).hexdigest() != record['files']['photon_rs_bg.wasm']:
                raise ValueError('Photon binary differs from its reviewed source build')
            version = record['npmVersion']
            notices = ['photon/components.json', 'photon/rust-standard-library.html', 'photon/roboto-license.txt', 'photon/roboto-copyright.txt']
        else:
            version = subprocess.check_output([str(path), '--version'], text=True).strip().removeprefix('v')
            if version != configuration['node']['version']: raise ValueError('Unexpected Node version')
            notices = ['node.txt']
        components.append({'component': component, 'version': version, 'path': relative,
                           'sha256': hashlib.sha256(content).hexdigest(), 'notices': notices})
    if {item['path'] for item in components} != set(expected):
        raise ValueError('Expected packaged native executables are missing')
    write(app / 'licenses/native-components.json', json.dumps(components, indent=2) + '\n')


def control(root, name, version, depends, description):
    for hook in ('preinst','prerm','postinst','postrm'):
        script=(ROOT/'release/debian-maintainer.py').read_text().replace('@COMPONENT@',name.removeprefix('augmentor-')).replace('@HOOK@',hook).replace('@VERSION@',version)
        write(root/'DEBIAN'/hook,script,True)
    write(root / 'DEBIAN/control', f'''Package: {name}
Version: {version}
Architecture: amd64
Maintainer: Manolo Remiddi <38885969+ManoloRemiddi@users.noreply.github.com>
Depends: {depends}
{('Pre-Depends: augmentor-runtime (= '+version+')'+chr(10)) if name=='augmentor-desktop' else ''}Section: utils
Priority: optional
Homepage: https://github.com/ManoloRemiddi/augmentor-agent
Description: {description}
 Augmentor Agent Desktop with shared prompts and DSH and Pi adapters.
''')
    write(root / f'usr/share/doc/{name}/copyright',
          'Augmentor-authored code: Copyright © 2026 Manolo Remiddi, MIT with Augmentor Resale Restriction.\n'
          'Redistributed dependencies retain their own licenses.\n'
          'Complete component notices: /usr/lib/augmentor/licenses/\n\n' + (ROOT / 'LICENSE').read_text())


def build(output):
    subprocess.run([sys.executable,str(ROOT/'scripts/sync-version.py'),'--check'],check=True)
    version = json.loads((ROOT / 'package.json').read_text())['version']
    product = json.loads((ROOT / 'release/product.json').read_text())
    source = {'commit':subprocess.check_output(['git','-c',f'safe.directory={ROOT}','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              'dirty':bool(subprocess.check_output(['git','-c',f'safe.directory={ROOT}','status','--porcelain'],cwd=ROOT,text=True).strip())}
    configuration = json.loads((ROOT / 'release/runtime.json').read_text())
    if not (ROOT / 'dist/runtime/src/main.js').exists():
        raise ValueError('Run npm run build before packaging')
    output.mkdir(parents=True, exist_ok=True)
    cache = output / 'cache'; cache.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='augmentor-deb-') as temporary:
        workspace = Path(temporary); runtime = workspace / 'runtime'; desktop = workspace / 'desktop'
        app = runtime / 'usr/lib/augmentor'
        subprocess.run([sys.executable, str(ROOT / 'scripts/stage-production.py'), '--out', str(app)], check=True)
        for name in ('dist', 'apps/native', 'apps/browser', 'scripts', 'services', 'adapters', 'config', 'docs', 'licenses', 'LICENSE', 'README.md', 'release/runtime.json', 'release/product.json'):
            copy(ROOT / name, app / name)
        for name in ('desktop-capabilities.json', 'desktop-capabilities.LICENSE'):
            copy(ROOT / 'release/dsh' / name, app / 'release/dsh' / name)
        node_runtime(app, configuration, cache)
        native_notices(app, configuration)
        write(app / 'release.json', json.dumps({**product,'source':source,'target': configuration['target'],
                                               'node': configuration['node'], 'pi': configuration['pi']}, indent=2) + '\n')
        launcher = '#!/bin/sh\n' + HEADER + 'export AUGMENTOR_PI_NODE=/usr/lib/augmentor/node/bin/node\nexport PI_TELEMETRY=0 PI_SKIP_VERSION_CHECK=1\n'
        lease='exec /usr/bin/python3 /usr/lib/augmentor/scripts/run-component.py runtime "$AUGMENTOR_PI_NODE" '
        write(runtime / 'usr/bin/augmentor-browser-host', launcher + lease + '/usr/lib/augmentor/apps/browser/native-host.mjs "$@"\n', True)
        write(runtime / 'usr/bin/augmentor-runtime', launcher + lease + '/usr/lib/augmentor/dist/runtime/src/main.js "$@"\n', True)
        write(runtime / 'usr/bin/augmentor-maintenance', '#!/bin/sh\n'+HEADER+'exec /usr/bin/python3 /usr/lib/augmentor/scripts/maintenance.py "$@"\n',True)
        write(runtime/'usr/lib/tmpfiles.d/augmentor.conf',HEADER+'d /run/augmentor 0755 root root -\nf /run/augmentor/augmentor-runtime.lock 0644 root root -\nf /run/augmentor/augmentor-desktop.lock 0644 root root -\n')
        key = json.loads((app / 'apps/browser/extension/manifest.json').read_text())['key']
        identity = ''.join(chr(ord('a') + int(n, 16)) for n in hashlib.sha256(base64.b64decode(key)).hexdigest()[:32])
        manifest = {'name': 'com.augmentor.agent', 'description': 'Augmentor Agent', 'path': '/usr/bin/augmentor-browser-host',
                    'type': 'stdio', 'allowed_origins': ['chrome-extension://' + identity + '/']}
        for directory in ('etc/chromium/native-messaging-hosts', 'etc/opt/chrome/native-messaging-hosts'):
            write(runtime / directory / 'com.augmentor.agent.json', json.dumps(manifest, indent=2) + '\n')
        control(runtime, 'augmentor-runtime', version, 'python3 (>= 3.11), python3-yaml, python3-websocket, libc6 (>= 2.36), libstdc++6', 'Augmentor runtime and Chromium companion')
        write(desktop / 'usr/bin/augmentor-agent', launcher + 'exec /usr/lib/augmentor/scripts/augmentor-linux "$@"\n', True)
        write(desktop / 'usr/share/augmentor/desktop-version',version+'\n')
        control(desktop, 'augmentor-desktop', version, f'augmentor-runtime (= {version}), python3-pyside6.qtcore (>= 6.8.2.1), python3-pyside6.qtgui, python3-pyside6.qtwidgets, python3-pyside6.qtnetwork, python3-pyside6.qtdbus, libqt6svg6, qt6-svg-plugins, python3-gi, gir1.2-atspi-2.0, at-spi2-core, gir1.2-gstreamer-1.0, gstreamer1.0-pipewire, gstreamer1.0-plugins-base, python3-yaml, python3-websocket, python3-pygments (>= 2.18), python3-numpy (>= 1.24), fonts-dejavu-core, libglib2.0-bin', 'Augmentor Agent Desktop application')
        write(desktop / 'usr/share/applications/com.augmentor.Agent.desktop', HEADER + '''[Desktop Entry]
Type=Application
Name=Augmentor Agent
Comment=Work with your Linux desktop using Augmentor
Exec=augmentor-agent
Icon=com.augmentor.Agent
Terminal=false
Categories=Utility;
StartupWMClass=Augmentor Agent
''')
        copy(ROOT / 'apps/native/augmentor_linux/assets/augmentor.svg', desktop / 'usr/share/icons/hicolor/scalable/apps/com.augmentor.Agent.svg')
        # Container checkouts can have a different UID. Trust only this explicit
        # build root for this read, without changing the user's global Git policy.
        epoch = int(subprocess.check_output(['git', '-c', f'safe.directory={ROOT}', 'log', '-1', '--format=%ct'], cwd=ROOT, text=True).strip())
        results = []
        for name, directory in [('augmentor-runtime', runtime), ('augmentor-desktop', desktop)]:
            for path in directory.rglob('*'):
                os.utime(path, (epoch, epoch), follow_symlinks=False)
            artifact = output / f'{name}_{version}_amd64.deb'
            subprocess.run(['dpkg-deb', '--threads-max=2', '--root-owner-group', '--build', str(directory), str(artifact)],
                           env={**os.environ, 'SOURCE_DATE_EPOCH': str(epoch)}, check=True)
            with artifact.open('rb') as stream: sha = hashlib.file_digest(stream, 'sha256').hexdigest()
            results.append({'file': artifact.name, 'sha256': sha, 'bytes': artifact.stat().st_size})
        write(output / 'artifacts.json', json.dumps({'version': version, 'source':source,'target': configuration['target'], 'artifacts': results}, indent=2) + '\n')
        print(json.dumps(results))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'outputs/debian')
    args = parser.parse_args()
    build(args.out.resolve())
