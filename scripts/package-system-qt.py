#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Prepare complete Arch/Leap application payloads and native build recipes.

The input Debian packages supply checked application/Node/Handy bytes, never
their dependency metadata or maintainer hooks. No package is installed here.
Native makepkg/rpmbuild execution and installed acceptance are separate steps.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
HEADER = '# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0\n'
TARGETS = {
    'arch20261001-x86_64': ('pacman', 'arch20261001-python-voice.json', 'arch20261002-inventory.json', '/usr/bin/python3'),
    'opensuse-leap16.0-x86_64': ('rpm', 'opensuse-leap16.0-python-voice.json', 'leap20261002-inventory.json', '/usr/bin/python3.13'),
}


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), ROOT/'scripts'/f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, text, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(mode)


def inventory(app):
    files = {}
    for path in sorted(app.rglob('*')):
        relative = path.relative_to(app).as_posix()
        if '__pycache__' in Path(relative).parts or path.suffix == '.pyc' or relative == 'linux-package.json':
            continue
        if path.is_symlink():
            if not path.resolve().is_relative_to(app.resolve()):
                raise ValueError('External application payload link: '+relative)
            files[relative] = 'link:'+path.readlink().as_posix()
        elif path.is_file():
            files[relative] = digest(path)
    return files


def wrappers(payload, python):
    app = '/usr/lib/augmentor'
    prefix = '#!/bin/sh\n'+HEADER+'set -eu\nexport AUGMENTOR_PI_NODE='+app+'/node/bin/node\nexport PI_TELEMETRY=0 PI_SKIP_VERSION_CHECK=1\n'
    lease = 'exec '+python+' '+app+'/scripts/run-component.py runtime "$AUGMENTOR_PI_NODE" '
    for name, command in [('augmentor-runtime', '/dist/runtime/src/main.js'),
                          ('augmentor-browser-host', '/apps/browser/native-host.mjs')]:
        write(payload/'usr/bin'/name, prefix+lease+app+command+' "$@"\n', 0o755)
    write(payload/'usr/bin/augmentor-maintenance', '#!/bin/sh\n'+HEADER+'exec '+python+' '+app+'/scripts/maintenance.py "$@"\n', 0o755)
    desktop = prefix+'export PYTHONPATH='+app+'/apps/native\n'
    desktop += 'augmentor_python="$('+python+' '+app+'/scripts/linux-python-runtime.py resolve --app-root '+app+')"\n'
    desktop += 'export AUGMENTOR_PYTHON="$augmentor_python"\n'
    desktop += 'if [ -z "${QT_QPA_PLATFORM:-}" ] && [ "${XDG_SESSION_TYPE:-}" = wayland ] && [ -n "${DISPLAY:-}" ]; then\n  export QT_QPA_PLATFORM=xcb\nfi\n'
    desktop += 'exec '+python+' '+app+'/scripts/run-component.py desktop "$augmentor_python" -m augmentor_linux "$@"\n'
    write(payload/'usr/bin/augmentor-agent', desktop, 0o755)


def leap_scriptlets(package):
    # Independent public source must survive final removal. RPM expands % even
    # inside Python scriptlets, including the guard's rpm query format strings.
    body = (ROOT/'release/linux-package-guard.py').read_text().rsplit("\nif __name__=='__main__':", 1)[0]
    phases = {
        'pre': body+'\nprint(json.dumps(begin('+repr('opensuse-leap16.0-x86_64')+", 'upgrade', "+repr(package)+')))\n',
        'posttrans': body+'\nprint(json.dumps(complete('+repr('opensuse-leap16.0-x86_64')+')))\n',
        'preun': 'import sys\n'+body+"\nif sys.argv[1]=='0': print(json.dumps(begin('opensuse-leap16.0-x86_64', 'remove')))\n",
        'postuntrans': 'import sys\n'+body+"\nif sys.argv[1]=='0': print(json.dumps(complete('opensuse-leap16.0-x86_64')))\n",
    }
    return {name: text.replace('%', '%%') for name, text in phases.items()}


def arch_recipe(version, release, payload_hash):
    dependencies = [
        'augmentor-package-guard>=0.2.13-2', 'python>=3.14', 'pyside6', 'shiboken6',
        'qt6-base', 'qt6-declarative', 'qt6-svg', 'qt6-wayland', 'python-pip',
        'python-yaml', 'python-websocket-client', 'python-pygments>=2.18',
        'python-keyring>=25.6', 'python-secretstorage', 'python-jeepney',
        'python-cffi', 'python-numpy>=1.24', 'python-flatbuffers', 'python-packaging',
        'python-typing_extensions', 'python-gobject', 'gtk4', 'at-spi2-core',
        'gst-python', 'gstreamer', 'gst-plugins-base', 'gst-plugin-pipewire',
        'portaudio', 'alsa-lib', 'alsa-plugins', 'libpulse', 'gnome-keyring',
        'libsecret', 'wmctrl', 'ttf-dejavu', 'noto-fonts', 'noto-fonts-cjk', 'glibc>=2.39', 'libstdc++',
        'gtk3', 'webkit2gtk-4.1', 'gtk-layer-shell', 'libayatana-appindicator',
        'openblas', 'vulkan-icd-loader', 'which', 'xdotool', 'wl-clipboard',
        'xorg-xwayland', 'systemd', 'kmod',
    ]
    return HEADER+f'''# Install the guard in a separate completed transaction first.
pkgname=augmentor-agent
pkgver={version}
pkgrel={release}
pkgdesc='Augmentor Agent Desktop and Browser companion (Arch snapshot candidate)'
arch=('x86_64')
url='https://github.com/ManoloRemiddi/augmentor-agent'
license=('custom:Augmentor-MIT-Resale-1.0')
depends=({' '.join(shlex.quote(name) for name in dependencies)})
conflicts=('augmentor-runtime' 'augmentor-desktop')
options=('!strip' '!debug')
source=('payload.tar')
sha256sums=('{payload_hash}')
package() {{
  cp -a "$srcdir/payload/." "$pkgdir/"
}}
'''


def leap_recipe(version, release, payload_hash):
    qt = load('linux-system-qt').PROFILES[load('linux-system-qt').LEAP][3]
    dependencies = list(qt)+[
        'python313-pip', 'python313-PyYAML', 'python313-websocket-client',
        'python313-Pygments >= 2.18', 'python313-SecretStorage', 'python313-jeepney',
        'python313-jaraco.classes', 'python313-jaraco.functools', 'python313-jaraco.context',
        'python313-cffi', 'python313-numpy >= 1.24', 'python313-flatbuffers', 'python313-packaging',
        'python313-typing_extensions', 'python313-gobject', 'python313-gobject-Gdk',
        'python313-gst', 'typelib-1_0-Gtk-4_0', 'typelib-1_0-Atspi-2_0',
        'typelib-1_0-Gst-1_0', 'typelib-1_0-GstApp-1_0', 'typelib-1_0-GstAudio-1_0',
        'gstreamer', 'gstreamer-plugins-base', 'gstreamer-plugin-pipewire',
        'libportaudio2', 'libasound2', 'alsa-plugins-pulse', 'libpulse0', 'pulseaudio-utils',
        'gnome-keyring', 'libsecret-1-0', 'wmctrl', 'dejavu-fonts',
        'google-noto-sans-symbols2-fonts', 'google-noto-sans-jp-fonts', 'glibc >= 2.39',
        'libstdc++.so.6(GLIBCXX_3.4.32)(64bit)', 'libgtk-3-0', 'libwebkit2gtk-4_1-0',
        'libgtk-layer-shell0', 'libappindicator3-1', 'libopenblas_serial0', 'libvulkan1',
        'which', 'xdotool', 'wl-clipboard', 'xwayland', 'systemd', 'udev', 'kmod',
    ]
    package = {'name': 'augmentor-agent', 'versionRelease': version+'-'+str(release)+'.leap16', 'architecture': 'x86_64'}
    hooks = leap_scriptlets(package)
    spec = HEADER+f'''%global debug_package %{{nil}}
%global __os_install_post %{{nil}}
%global _build_id_links none
Name: augmentor-agent
Version: {version}
Release: {release}.leap16
Summary: Augmentor Agent Desktop and Browser companion (Leap16 candidate)
License: LicenseRef-Augmentor-MIT-Resale-1.0 AND MIT AND BSD-3-Clause AND Apache-2.0
URL: https://github.com/ManoloRemiddi/augmentor-agent
BuildArch: x86_64
AutoReqProv: no
Source0: payload.tar
BuildRequires: coreutils, tar
'''
    spec += ''.join('Requires: '+name+'\n' for name in dependencies)
    spec += ''.join('Requires('+name+'): /usr/bin/python3.13\n' for name in hooks)
    spec += '''Conflicts: augmentor-runtime, augmentor-desktop
%description
Complete native application/Node/Handy candidate with an exact system Qt profile
and offline Python wheels. DSH, model setup and extension activation are separate.
%prep
echo "'''+payload_hash+'''  %{SOURCE0}" | sha256sum -c -
tar -xf %{SOURCE0}
%build
%install
mkdir -p %{buildroot}
cp -a payload/. %{buildroot}/
'''
    for name, body in hooks.items():
        spec += '%'+name+' -p "/usr/bin/python3.13 -I"\n'+body+'\n'
    spec += '''%files
/usr/lib/augmentor
/usr/lib/tmpfiles.d/augmentor.conf
/usr/lib/udev/rules.d/70-augmentor-dictation.rules
/usr/lib/modules-load.d/augmentor-dictation.conf
/usr/lib64/chromium/native-messaging-hosts/com.augmentor.agent.json
/usr/bin/augmentor-agent
/usr/bin/augmentor-runtime
/usr/bin/augmentor-browser-host
/usr/bin/augmentor-maintenance
/usr/share/augmentor
/usr/share/applications/com.augmentor.Agent.desktop
/usr/share/icons/hicolor/scalable/apps/com.augmentor.Agent.svg
/usr/share/doc/augmentor-runtime
/usr/share/doc/augmentor-desktop
/etc/chromium/native-messaging-hosts/com.augmentor.agent.json
/etc/opt/chrome/native-messaging-hosts/com.augmentor.agent.json
'''
    return spec


def prepare(debian, wheelhouse, out, target, release=1):
    if target not in TARGETS or type(release) is not int or not 0 < release < 100000:
        raise ValueError('Use an exact candidate target and positive package release.')
    if out.exists() or out.is_symlink():
        raise ValueError('Choose a new output directory; existing results are preserved.')
    manager, policy_name, stack_name, python = TARGETS[target]
    manifest = json.loads((debian/'artifacts.json').read_text())
    source = manifest.get('source')
    if (not isinstance(source, dict) or source.get('dirty') is not False
            or not re.fullmatch('[0-9a-f]{40}', source.get('commit', ''))
            or manifest.get('pythonRuntime') is not None or manifest.get('target') != 'debian13-amd64'):
        raise ValueError('Use clean generic Debian application bytes; no Noble/source Qt conversion.')
    version = manifest['version']
    if not re.fullmatch(r'[0-9]+(?:\.[0-9]+){2}', version):
        raise ValueError('Invalid application version.')
    expected = {f'augmentor-{kind}_{version}_amd64.deb' for kind in ('runtime', 'desktop')}
    rows = manifest['artifacts']
    if len(rows) != 2 or {row['file'] for row in rows} != expected:
        raise ValueError('Require exactly matching runtime and Desktop packages.')
    for row in rows:
        path = debian/row['file']
        if path.is_symlink() or path.stat().st_size != row['bytes'] or digest(path) != row['sha256']:
            raise ValueError('Input package checksum/size differs.')
        if subprocess.check_output(['dpkg-deb', '-f', str(path), 'Architecture'], text=True).strip() != 'amd64':
            raise ValueError('Use an x86_64 payload.')
    wheel_tool = load('linux-wheel-inventory')
    policy_path = ROOT/'release'/policy_name
    value = wheel_tool.runtime.policy(policy_path)
    contract = wheel_tool.runtime.contract(value, digest(policy_path))
    wheel_report, notices = wheel_tool.inventory(value, wheelhouse)
    stack = ROOT/'release/system-qt'/stack_name
    system = value['systemQtStack']
    if digest(stack) != system['sha256'] or stack.stat().st_size != system['bytes']:
        raise ValueError('The reviewed system Qt inventory differs from its policy.')
    with tempfile.TemporaryDirectory(prefix='augmentor-system-qt-', dir=out.parent) as temp:
        stage = Path(temp)
        payload = stage/'payload'
        payload.mkdir()
        for row in rows:
            subprocess.run(['dpkg-deb', '-x', str(debian/row['file']), str(payload)], check=True)
        app = payload/'usr/lib/augmentor'
        product = json.loads((app/'release.json').read_text())
        if (product.get('source') != source or product.get('version') != version
                or product.get('pythonRuntime') is not None or (app/'linux-python-runtime.json').exists()
                or (app/'linux-python-runtime.json').is_symlink()):
            raise ValueError('Input payload identity differs or already declares a Python runtime.')
        if (payload/'usr/share/augmentor/desktop-version').read_text().strip() != version:
            raise ValueError('Desktop/runtime package versions differ.')
        for file in ('scripts/linux-python-runtime.py', 'scripts/linux-system-qt.py', 'scripts/run-component.py', 'services/lifecycle/lease.py'):
            if digest(app/file) != digest(ROOT/file):
                raise ValueError('Rebuild the payload with the current runtime/lifecycle adapter: '+file)
        product.update(target=target, pythonRuntime=contract, candidateOnly=True)
        write(app/'release.json', json.dumps(product, indent=2)+'\n')
        config = json.loads((app/'release/runtime.json').read_text())
        config['target'] = target
        write(app/'release/runtime.json', json.dumps(config, indent=2)+'\n')
        shutil.copy2(policy_path, app/'linux-python-runtime.json')
        wheels = app/'python-wheels'
        wheels.mkdir()
        for row in value['wheels']:
            shutil.copy2(wheelhouse/row['file'], wheels/row['file'])
        shutil.copy2(stack, wheels/system['file'])
        for name, content in notices.items():
            path = app/'licenses/linux-wheels'/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        write(app/'licenses/linux-wheel-inventory.json', json.dumps(wheel_report, indent=2)+'\n')
        wrappers(payload, python)
        if manager == 'rpm':
            host = payload/'usr/lib64/chromium/native-messaging-hosts'
            host.mkdir(parents=True)
            shutil.copy2(payload/'etc/chromium/native-messaging-hosts/com.augmentor.agent.json', host)
        package = {'name': 'augmentor-agent', 'versionRelease': version+'-'+str(release)+('.leap16' if manager == 'rpm' else ''), 'architecture': 'x86_64'}
        receipt = {'format': 'augmentor-linux-package-receipt/1', 'target': target,
                   'manager': manager, 'version': version, 'source': source, 'package': package,
                   'completeInventory': True, 'files': inventory(app)}
        write(app/'linux-package.json', json.dumps(receipt, indent=2)+'\n')
        with tarfile.open(stage/'payload.tar', 'w') as archive:
            archive.add(payload, arcname='payload')
        payload_hash = digest(stage/'payload.tar')
        name = 'PKGBUILD' if manager == 'pacman' else 'augmentor-agent.spec'
        recipe = arch_recipe(version, release, payload_hash) if manager == 'pacman' else leap_recipe(version, release, payload_hash)
        write(stage/name, recipe)
        report = {'format': 'augmentor-system-qt-package-preparation/1', 'target': target,
                  'version': version, 'source': source, 'package': package, 'pythonRuntime': contract,
                  'inputDebs': {row['file']: row['sha256'] for row in rows},
                  'packagingRecipeSha256': digest(Path(__file__)),
                  'guardSourceSha256': digest(ROOT/'release/linux-package-guard.py'),
                  'payloadArchive': {'file': 'payload.tar', 'sha256': payload_hash, 'bytes': (stage/'payload.tar').stat().st_size},
                  'nativeRecipe': {'file': name, 'sha256': digest(stage/name)},
                  'candidateOnly': True, 'nativePackageBuilt': False, 'installedAcceptance': False,
                  'legalAcceptance': False, 'publicRelease': False}
        write(stage/'preparation.json', json.dumps(report, indent=2)+'\n')
        # Expose complete inputs only after every check succeeds.
        shutil.rmtree(payload)
        stage.rename(out)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--debian', type=Path, required=True)
    parser.add_argument('--wheelhouse', type=Path, required=True)
    parser.add_argument('--target', choices=tuple(TARGETS), required=True)
    parser.add_argument('--package-release', type=int, default=1)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    report = prepare(args.debian.resolve(), args.wheelhouse.resolve(), args.out.resolve(), args.target, args.package_release)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
