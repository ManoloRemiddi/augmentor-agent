#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Disposable W1 installer app. Never included in an Augmentor customer package."""
import json
import os
from pathlib import Path
import shutil
import sys
import time

import velopack

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ['AUGMENTOR_INSTALLER_PROOF_DIR'])
CONFIG = json.loads((ROOT/'fixture.json').read_text())
DATA.mkdir(parents=True, exist_ok=True)


def hook(name, *args):
    import winreg
    key = 'Software\\Google\\Chrome\\NativeMessagingHosts\\' + CONFIG['hostName']
    manifest = DATA/'host.json'
    if name == 'uninstall':
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as entry:
                owned = winreg.QueryValue(entry, None) == str(manifest)
            if owned:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key)
        except FileNotFoundError:
            pass
    else:
        manifest.write_text(json.dumps({'name': CONFIG['hostName'], 'description': 'Disposable installer fixture',
            'path': str(ROOT/'AugmentorFixture.exe'), 'type': 'stdio', 'allowed_origins': []}))
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key) as entry:
            winreg.SetValueEx(entry, '', 0, winreg.REG_SZ, str(manifest))
    with (DATA/'hooks.jsonl').open('a', encoding='utf-8') as stream:
        stream.write(json.dumps({'hook': name, 'version': CONFIG['version']})+'\n')


def main():
    # The public SDK cleans old packages on startup even with auto-apply off.
    # Preserve the preceding package outside its cleanup tree before that call.
    packages = ROOT.parent/'packages'
    recovery = DATA/'recovery'
    recovery.mkdir(exist_ok=True)
    for package in packages.glob('*-full.nupkg'):
        target = recovery/package.name
        if not target.exists():
            shutil.copy2(package, target)
    (velopack.App().set_auto_apply_on_startup(False)
        .on_after_install_fast_callback(lambda *args: hook('install', *args))
        .on_after_update_fast_callback(lambda *args: hook('update', *args))
        .on_before_uninstall_fast_callback(lambda *args: hook('uninstall', *args)).run())
    args = sys.argv[1:]
    if not args:
        return
    action, report_file, *rest = args
    report = {'version': CONFIG['version'], 'python': sys.version, 'executable': sys.executable,
              'argv': args, 'installedRoot': str(ROOT)}
    if action == '--hold':
        busy = DATA/'busy'
        busy.write_text(str(os.getpid()))
        Path(report_file).write_text(json.dumps(report))
        try:
            deadline = time.monotonic()+90
            while busy.exists() and time.monotonic() < deadline:
                time.sleep(.1)
        finally:
            busy.unlink(missing_ok=True)
        return
    if action in ('--download', '--apply'):
        manager = velopack.UpdateManager(rest[0])
        update = manager.check_for_updates()
        assert update is not None, 'Expected a second fixture version'
        if action == '--download':
            manager.download_updates(update)
            report['pending'] = manager.get_update_pending_restart().Version
        else:
            if (DATA/'busy').exists():
                report['refusedBusy'] = True
                Path(report_file).write_text(json.dumps(report))
                return 2
            # Only call the framework after the fixture's active work exits.
            # The full product must acquire its maintenance gate in W8.
            manager.apply_updates_and_restart_with_args(update, ['--inspect', report_file])
            raise AssertionError('Apply should have exited the process')
    elif action != '--inspect':
        raise ValueError('Unknown fixture action')
    Path(report_file).write_text(json.dumps(report))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
