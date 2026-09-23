#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real service process and Carbon ownership, using isolated user settings."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
if sys.platform != 'darwin':raise SystemExit('Run this proof on macOS.')
HELPER = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(ROOT/'apps/native'))
from PySide6.QtGui import QKeySequence
from augmentor_linux.macos_shortcut_service import request
from augmentor_linux.macos_shortcuts import ShortcutManager, RemoteShortcutManager, select_manager


def start():
    child = subprocess.Popen([sys.executable, '-B', '-m', 'augmentor_linux.macos_shortcut_service'],
                             stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if child.poll() is not None:
            raise RuntimeError(child.stderr.read().decode())
        try:
            status = request({'operation':'status'})
            if status['pid'] == child.pid:return child
        except OSError:pass
        time.sleep(0.05)
    child.terminate();child.wait(timeout=20);child.stderr.close()
    raise RuntimeError('Service readiness timed out.')


def stop(child):
    child.terminate()
    assert child.wait(timeout=20) == 0
    errors = child.stderr.read().decode()
    child.stderr.close()
    assert not errors, errors


with tempfile.TemporaryDirectory(prefix='ash-', dir='/tmp') as directory:
    os.environ.update(XDG_RUNTIME_DIR=directory+'/run', XDG_CONFIG_HOME=directory+'/config',
                      AUGMENTOR_MACOS_HOTKEY=str(HELPER), PYTHONPATH=str(ROOT/'apps/native'))
    child = start()
    competitor = ShortcutManager()
    sequence = QKeySequence('Ctrl+Meta+Alt+Shift+F19')
    try:
        client = select_manager()
        assert isinstance(client, RemoteShortcutManager)
        client.save(sequence)
        assert request({'operation':'status'})['active']
        client.close()
        try:
            competitor.save(sequence, persist=False)
            raise AssertionError('The service lost exclusive Carbon ownership.')
        except ValueError:pass
        stop(child);child = None
        competitor.save(sequence, persist=False)
        competitor.close()
        child = start()
        status = request({'operation':'status'})
        assert status['active'] and status['key'] == sequence[0].toCombined(), status
        stop(child);child = None
        result = {'serviceProcess':True, 'nativeCarbonRegistration':True,
                  'clientClosePreservesOwnership':True, 'terminationReleasesKey':True,
                  'restartRestoresKey':True, 'physicalKeyDeliveryTested':False,
                  'loginLaunchTested':False, 'installedCandidateTested':False}
        output = ROOT/'outputs/cross-platform/mac-shortcut-service-proof.json'
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(result))
    finally:
        if child is not None:stop(child)
        competitor.close()
