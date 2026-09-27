#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Build/install two disposable Velopack versions, update and remove them."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]


def wait_for(path, timeout=60):
    deadline = time.monotonic()+timeout
    while time.monotonic() < deadline:
        if path.is_file():
            return json.loads(path.read_text())
        time.sleep(.2)
    raise TimeoutError('No fixture response: '+str(path))


def build_launcher(payload, arch):
    vswhere = Path(os.environ.get('ProgramFiles(x86)', 'C:/Program Files (x86)'))/'Microsoft Visual Studio/Installer/vswhere.exe'
    install = subprocess.check_output([str(vswhere), '-latest', '-products', '*', '-property', 'installationPath'], text=True).strip()
    if not install:
        raise RuntimeError('Windows build tools are missing')
    vcvars = Path(install)/'VC/Auxiliary/Build/vcvarsall.bat'
    # Build paths originate in this controlled checkout. Do not accept shell
    # metacharacters: vcvarsall is the vendor's batch environment initializer.
    values = (str(vcvars), str(payload), str(ROOT))
    if any(any(c in value for c in '&|<>^%!\r\n') for value in values):
        raise ValueError('Unsupported shell character in the build path')
    include = payload/'python/include'
    if not (include/'Python.h').is_file():
        raise RuntimeError('Standalone Python must include its matching C headers')
    command = (f'call "{vcvars}" {"amd64_arm64" if arch == "arm64" else "amd64"} && '
        f'cl /nologo /O2 /W4 /MT /I"{include}" "{ROOT / "services/platform/windows-launcher.c"}" '
        f'/Fe:"{payload / "AugmentorFixture.exe"}" /Fo:"{payload / "launcher.obj"}" '
        '/link /SUBSYSTEM:WINDOWS user32.lib shell32.lib')
    subprocess.run(['cmd.exe', '/d', '/s', '/c', command], check=True)
    (payload/'launcher.obj').unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--arch', choices=('x64', 'arm64'), required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--vpk', type=Path, required=True)
    args = parser.parse_args()
    assert sys.platform == 'win32'
    out, runtime = args.out.resolve(), args.runtime.resolve()
    if out.exists() and any(out.iterdir()):
        parser.error('Choose a new empty proof directory')
    out.mkdir(parents=True, exist_ok=True)
    package_id = 'Augmentor.Qualification.'+uuid.uuid4().hex
    host_name = 'com.augmentor.fixture.'+uuid.uuid4().hex
    payload, installed, data = out/'payload', out/'installed café with spaces', out/'persistent'
    payload.mkdir(); data.mkdir()
    # W1 tests the actual interpreter and installer library. Full desktop/DSH
    # packaging is a separate gate; keeping this fixture small speeds iteration.
    shutil.copytree(runtime/'python', payload/'python',
                    ignore=shutil.ignore_patterns('site-packages', '__pycache__', '*.pyc'))
    site = payload/'python/Lib/site-packages'
    site.mkdir(parents=True, exist_ok=True)
    for entry in (runtime/'python/Lib/site-packages').glob('velopack*'):
        if entry.is_dir(): shutil.copytree(entry, site/entry.name)
        else: shutil.copy2(entry, site/entry.name)
    (payload/'scripts').mkdir()
    shutil.copy2(ROOT/'scripts/windows-installer-fixture.py', payload/'scripts/launch-windows.py')
    build_launcher(payload, args.arch)
    env = {**os.environ, 'AUGMENTOR_INSTALLER_PROOF_DIR': str(data)}
    sentinel = data/'settings.json'
    sentinel.write_text('{"model":"fixture-selected","draft":"preserve me"}')
    sentinel_bytes = sentinel.read_bytes()
    feeds = []
    for version in ('0.0.1', '0.0.2'):
        (payload/'fixture.json').write_text(json.dumps({'version': version, 'hostName': host_name}))
        feed = out/('feed-'+version); feeds.append(feed)
        subprocess.run([str(args.vpk.resolve()), 'pack', '--packId', package_id,
            '--packVersion', version, '--packDir', str(payload), '--mainExe', 'AugmentorFixture.exe',
            '--packTitle', package_id, '--runtime', 'win-'+args.arch,
            '--outputDir', str(feed)], check=True, env=env, timeout=300)
    setup = next(feeds[0].glob('*Setup.exe'))
    subprocess.run([str(setup), '--silent', '--installto', str(installed)], check=True, env=env, timeout=120)
    app = installed/'current/AugmentorFixture.exe'
    assert app.is_file()
    def invoke(action, name, *extra, expected=0):
        report = out/(name+'.json')
        result = subprocess.run([str(app), action, str(report), *map(str, extra)], env=env, timeout=60)
        assert result.returncode == expected, (action, result.returncode)
        return wait_for(report)
    holder = None
    try:
        assert invoke('--inspect', 'installed')['version'] == '0.0.1'
        assert invoke('--download', 'download', feeds[1])['pending'] == '0.0.2'
        # Restarting after download must not apply an update without consent.
        assert invoke('--inspect', 'reopened-with-pending-update')['version'] == '0.0.1'
        holder = subprocess.Popen([str(app), '--hold', str(out/'active.json')], env=env)
        wait_for(out/'active.json')
        refusal = invoke('--apply', 'busy-refusal', feeds[1], expected=2)
        assert refusal['refusedBusy'] and holder.poll() is None
        (data/'busy').unlink(); assert holder.wait(timeout=15) == 0
        assert invoke('--apply', 'updated', feeds[1])['version'] == '0.0.2'
        assert invoke('--inspect', 'reopened')['version'] == '0.0.2'
        assert sentinel.read_bytes() == sentinel_bytes
        assert any('0.0.1' in path.name for path in (data/'recovery').glob('*-full.nupkg'))
    finally:
        (data/'busy').unlink(missing_ok=True)
        if holder is not None and holder.poll() is None:
            holder.wait(timeout=15)
        updater = installed/'Update.exe'
        if updater.is_file():
            subprocess.run([str(updater), 'uninstall', '--silent'], check=True, env=env, timeout=120)
    assert sentinel.read_bytes() == sentinel_bytes
    assert not app.exists()
    hooks = [json.loads(line) for line in (data/'hooks.jsonl').read_text().splitlines()]
    assert {'install', 'update', 'uninstall'} <= {item['hook'] for item in hooks}
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Software\\Google\\Chrome\\NativeMessagingHosts\\'+host_name):
            raise AssertionError('Fixture native-host key survived uninstall')
    except FileNotFoundError:
        pass
    report = {'schema': 'augmentor-windows-installer-proof/1', 'arch': args.arch,
        'installUpdateReopenRemove': True, 'settingsPreserved': True, 'autoApplyDisabled': True,
        'busyFixtureRefused': True, 'previousPackageRetained': True, 'hooks': hooks,
        'limits': ['Unsigned disposable fixture only; full-app coordination, authenticated rollback, standard-user and customer-package qualification remain pending.']}
    (out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
