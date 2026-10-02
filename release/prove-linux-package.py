#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Qualify actual packages inside a disposable container, never the host.

Container evidence covers installation, ordinary-user rendering and maintenance.
It does not establish desktop-session, physical audio or SELinux acceptance.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PROOF_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
sys.path.insert(0, str(ROOT/'scripts'))
from linux_distribution import host_target, package_files


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def run(command, **kwargs):
    return subprocess.run(command, check=True, text=True, **kwargs)


def wmctrl_version(user):
    # wmctrl opens X before parsing even -V. Give this read-only binary check
    # its own local display; neither an owner display nor a window manager is
    # needed. Xvfb is a qualification dependency, not a product dependency.
    read_fd, write_fd = os.pipe()
    server = None
    try:
        with tempfile.TemporaryFile() as log:
            server = subprocess.Popen(['Xvfb', '-displayfd', str(write_fd),
                '-nolisten', 'tcp', '-screen', '0', '640x480x24'],
                pass_fds=(write_fd,), stdout=log, stderr=log)
            os.close(write_fd)
            write_fd = None
            if not select.select([read_fd], [], [], 15)[0]:
                raise RuntimeError('Private package-check display did not become ready.')
            number = os.read(read_fd, 32).decode().strip()
            if not number.isdigit() or server.poll() is not None:
                raise RuntimeError('Private package-check display failed.')
            return subprocess.check_output(['runuser', '-u', user, '--', 'env',
                'DISPLAY=:' + number, 'wmctrl', '-V'], text=True, timeout=10).strip()
    finally:
        os.close(read_fd)
        if write_fd is not None:
            os.close(write_fd)
        if server is not None and server.poll() is None:
            server.terminate()
            server.wait(timeout=10)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--artifacts', type=Path, required=True)
    p.add_argument('--image-digest', required=True)
    p.add_argument('--out', type=Path, default=Path('/tmp/linux-package-proof.json'))
    a = p.parse_args()
    if os.geteuid() != 0 or not any(Path(marker).exists() for marker in ('/.dockerenv', '/run/.containerenv')):
        raise SystemExit('Run only as root inside a disposable Docker/Podman container.')
    target = host_target()
    artifacts = a.artifacts.resolve()
    manifest = json.loads((artifacts/'artifacts.json').read_text())
    hashes = {item['file']: item['sha256'] for item in manifest['artifacts']}
    names = package_files({'version': manifest['version'], 'sha256': hashes}, target)
    if target.startswith('fedora') and manifest.get('target') != target:
        raise ValueError('The RPM target differs from this container.')
    for name in names:
        if digest(artifacts/name) != hashes[name]:
            raise ValueError('Package checksum mismatch: ' + name)
    rpm = target.startswith('fedora')
    packages = ['augmentor-agent'] if rpm else ['augmentor-desktop', 'augmentor-runtime']

    def install():
        run((['dnf', '-y', 'install'] if rpm else ['apt-get', '-y', 'install', '--no-install-recommends']) + [str(artifacts/name) for name in names])

    def reinstall(check=True):
        command = (['dnf', '-y', 'reinstall'] if rpm else ['apt-get', '-y', 'install', '--reinstall', '--no-install-recommends']) + [str(artifacts/name) for name in names]
        return subprocess.run(command, check=check, text=True, capture_output=True)

    def remove(check=True):
        command = (['dnf', '-y', 'remove', '--setopt=clean_requirements_on_remove=False'] if rpm else ['apt-get', '-y', 'remove']) + packages
        return subprocess.run(command, check=check, text=True, capture_output=True)

    if not rpm:
        run(['apt-get', 'update', '-qq'])
        run(['apt-get', '-y', 'install', '--no-install-recommends', 'passwd', 'util-linux', 'xvfb'])
    else:
        run(['dnf', '-y', 'install', 'shadow-utils', 'util-linux', 'xorg-x11-server-Xvfb'])
    app = Path('/usr/lib/augmentor')
    fresh = not (app/'release.json').exists()
    install()
    release = json.loads((app/'release.json').read_text())
    assert release['version'] == manifest['version']
    assert release['source'] == manifest['source']
    if rpm:
        run(['rpm', '-V', 'augmentor-agent'])
    else:
        run(['dpkg', '--audit'])
    user = 'augmentor-proof'
    home = Path('/home')/user
    run(['useradd', '-m', '-s', '/bin/sh', user])
    gtk = subprocess.check_output(['runuser', '-u', user, '--', '/usr/bin/python3', '-c',
        'import gi; gi.require_version("Gtk", "4.0"); from gi.repository import Gtk; '
        'assert callable(Gtk.accelerator_parse_with_keycode); '
        'print(str(Gtk.get_major_version())+"."+str(Gtk.get_minor_version())+"."+str(Gtk.get_micro_version()))'],text=True).strip()
    wmctrl = wmctrl_version(user)
    run(['runuser', '-u', user, '--', '/usr/bin/python3', str(app/'scripts/run-component.py'), 'runtime', str(app/'node/bin/node'), '--version'])
    run(['runuser', '-u', user, '--', 'env', 'QT_QPA_PLATFORM=offscreen', 'augmentor-agent', '--preview', '--screenshot', str(home/'window.png')])
    assert (home/'window.png').stat().st_size > 1000
    sentinel = home/'.local/share/augmentor-proof/keep-my-data'
    run(['runuser', '-u', user, '--', 'sh', '-c', 'mkdir -p "$HOME/.local/share/augmentor-proof"; printf preserved > "$HOME/.local/share/augmentor-proof/keep-my-data"'])
    before = digest(app/'release.json')
    # Exercise both component locks, including desktop-only activity.
    for component in ('runtime', 'desktop'):
        with tempfile.TemporaryFile(mode='w+t') as holder_log:
            holder = subprocess.Popen(['runuser', '-u', user, '--', '/usr/bin/python3', str(app/'scripts/run-component.py'), component, '/usr/bin/python3', '-u', '-c', 'import os,time; print(os.getpid(),flush=True); time.sleep(120)'], stdout=subprocess.PIPE, stderr=holder_log, text=True)
            child_pid = None
            try:
                ready = holder.stdout.readline().strip()
                holder_log.seek(0)
                assert ready.isdigit(), 'Lease holder failed to start: ' + holder_log.read()
                child_pid = int(ready)
                for operation in (reinstall, remove):
                    result = operation(check=False)
                    assert 'Augmentor is still open' in result.stdout + result.stderr, result.stdout + result.stderr
                    assert digest(app/'release.json') == before, 'Active payload was replaced or removed'
                    if component == 'desktop':
                        assert (Path('/usr/share/augmentor')/'desktop-version').read_text().strip() == manifest['version']
                    if rpm:
                        run(['rpm', '-V', 'augmentor-agent'])
            finally:
                # Kill the holder child as well as runuser; avoid orphaned leases.
                if holder.poll() is None:
                    if child_pid:
                        os.kill(child_pid, signal.SIGTERM)
                    else:
                        holder.terminate()
                holder.wait(timeout=10)
        # A refused multi-package operation can leave a maintenance marker from
        # its earlier component. Retry while idle before starting the next one.
        reinstall()
        assert not list(Path('/run/augmentor').glob('*.pending'))
    remove()
    assert sentinel.read_text() == 'preserved'
    assert not (app/'release.json').exists()
    install()
    assert sentinel.read_text() == 'preserved'
    if rpm:
        run(['rpm', '-V', 'augmentor-agent'])
    versions = json.loads(subprocess.check_output(['/usr/bin/python3', '-c', 'import json,platform,PySide6;from PySide6.QtCore import qVersion;print(json.dumps({"python":platform.python_version(),"pyside":PySide6.__version__,"qt":qVersion()}))'], text=True))
    versions['node'] = subprocess.check_output([str(app/'node/bin/node'), '--version'], text=True).strip()
    report = {'target': target, 'imageDigest': a.image_digest, 'source': manifest['source'], 'artifacts': hashes,
              'proofScriptSha256': PROOF_SHA256,
              'versions': versions, 'gtk4Version': gtk, 'gtk4ShortcutApiImportTested': True,
              'wmctrlVersion': wmctrl, 'wmctrlBinaryTested': True,
              'freshInstall': fresh, 'nonRootRuntimeLease': True, 'nonRootQtRender': True,
              'activeRuntimeAndDesktopReinstallBlocked': True, 'activeComponentRemovalBlocked': True,
              'idleReinstall': True, 'removePreservesPrivateFiles': True, 'reinstallAfterRemove': True,
              'realDesktopSessionTested': False, 'physicalAudioTested': False, 'selinuxEnforcingTested': False,
              'dshModelTurnTested': False}
    a.out.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
