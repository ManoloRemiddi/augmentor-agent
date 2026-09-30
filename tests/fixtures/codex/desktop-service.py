#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual desktop socket handler, isolated fake OS boundary; no screen or input access."""
import base64
import importlib.util
import json
import os
from pathlib import Path
import sys
import threading
import time
import types
from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QImage, QColor

ROOT = Path(__file__).resolve().parents[3]
# The OS implementation is deliberately never instantiated by this fixture.
if sys.platform != 'darwin':
    repository = types.ModuleType('gi.repository'); repository.GLib = None
    sys.modules['gi'] = types.ModuleType('gi'); sys.modules['gi.repository'] = repository
    portal = types.ModuleType('portal'); portal.Portal = None; sys.modules['portal'] = portal
sys.path.insert(0, str(ROOT / 'services/desktop'))
spec = importlib.util.spec_from_file_location('desktop_service_fixture', ROOT / 'services/desktop/service.py')
service = importlib.util.module_from_spec(spec); spec.loader.exec_module(service)
service.schedule = lambda work: threading.Thread(target=work, daemon=True).start()


class Boundary:
    def __init__(self, root):
        self.owner = None; self.cancel = threading.Event(); self.busy = threading.Lock(); self.generation = 0
        self.sequence = 0; self.token = None; self.root = root; self.log_lock = threading.Lock()
        pixels = QImage(16, 16, QImage.Format.Format_RGB32); pixels.fill(QColor('green'))
        output = QBuffer(); output.open(QIODevice.OpenModeFlag.WriteOnly); assert pixels.save(output, 'JPEG')
        self.image = {'mimeType': 'image/jpeg', 'data': base64.b64encode(bytes(output.data())).decode(), 'width': 16, 'height': 16}
    def log(self, method, **fields):
        with self.log_lock:
            with (self.root / 'desktop-events.jsonl').open('a') as output: output.write(json.dumps({'method': method, **fields}) + '\n')
    def status(self): return {'active': bool(self.owner), 'sharing': bool(self.owner), 'owner': self.owner, 'busy': self.busy.locked()}
    def connect(self, owner):
        if self.owner and self.owner != owner: raise RuntimeError('Another chat owns desktop control.')
        self.log('connect', owner=owner)
        if (self.root / 'decline').exists(): raise RuntimeError('Fixture consent declined.')
        self.owner = owner; return self.status()
    def capture(self, owner):
        if self.owner != owner or self.cancel.is_set(): raise RuntimeError('Connect desktop control first.')
        self.sequence += 1; self.token = 'fixture-observation-' + str(self.sequence)
        self.log('capture', owner=owner)
        return {'token': self.token, 'image': self.image, 'imageSize': {'width': 16, 'height': 16}, 'window': {'id': 1, 'pid': 42}, 'expiresInSeconds': 30}
    def action(self, owner, params):
        if self.owner != owner or self.cancel.is_set(): raise RuntimeError('Wrong desktop owner.')
        if not self.token or params.get('token') != self.token: raise RuntimeError('Observation already consumed.')
        self.token = None; self.log('action', owner=owner, params=params)
        if params.get('text') == 'hold-until-stop':
            if not self.cancel.wait(15): raise RuntimeError('Fixture cancellation timed out.')
            raise RuntimeError('Desktop action interrupted after dispatch.')
        return {'dispatched': True, 'verified': False}
    def stop(self):
        self.log('stop', owner=self.owner); self.cancel.set(); self.owner = None; self.token = None
        return {'stopped': True}


if __name__ == '__main__':
    os.umask(0o077); root = Path(sys.argv[1]); path = root / 'augmentor-desktop.sock'
    server = service.Server(str(path), service.Handler); server.backend = Boundary(root)
    print(json.dumps({'ready': True, 'socket': str(path)}), flush=True)
    try: server.serve_forever()
    finally: server.server_close(); path.unlink(missing_ok=True)
