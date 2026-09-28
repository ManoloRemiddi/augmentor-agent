#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real compiled native-host binary/protocol proof, separate from browser UI acceptance."""
import importlib.util
import json
import os
from pathlib import Path
import queue
import struct
import subprocess
import threading
import time


def prove(root, work, session):
    import windows_supervisor as owner
    spec = importlib.util.spec_from_file_location('browser_entrypoint', root/'scripts/launch-windows-browser.py')
    entrypoint = importlib.util.module_from_spec(spec); spec.loader.exec_module(entrypoint)
    argv = [str(root/'AugmentorBrowserHost.exe'), '--qualification-root', str(work), entrypoint.origin(root), '--parent-window=0']
    process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW, cwd=root, env={**os.environ})
    frames = queue.Queue()
    def read():
        def exact(size):
            result = bytearray()
            while len(result) < size:
                chunk = process.stdout.read(size-len(result))
                if not chunk: raise EOFError('The native browser host disconnected.')
                result.extend(chunk)
            return bytes(result)
        try:
            while True:
                size, = struct.unpack('<I', exact(4))
                if not 0 < size <= 1024*1024: raise ValueError('Invalid native messaging frame size.')
                frames.put(json.loads(exact(size)))
        except Exception as error: frames.put(error)
    reader = threading.Thread(target=read, daemon=True); reader.start()
    serial = 0
    def request(method, params=None, *, error=False):
        nonlocal serial
        serial += 1; identity = str(serial)
        raw = json.dumps({'id': identity, 'method': method, 'params': params or {}}, ensure_ascii=False).encode()
        process.stdin.write(struct.pack('<I', len(raw))+raw); process.stdin.flush()
        deadline = time.monotonic()+30
        while True:
            result = frames.get(timeout=max(.1, deadline-time.monotonic()))
            if isinstance(result, Exception): raise result
            if result.get('id') != identity:
                if time.monotonic()>deadline: raise TimeoutError('The native host reply was not received; no replay.')
                continue  # Actual DSH event notifications can precede a reply.
            if error:
                assert 'error' in result, result
                return result
            if 'error' in result: raise AssertionError(result)
            return result['result']
    try:
        version = json.loads((root/'release.json').read_text(encoding='utf-8'))['version']
        request('augmentor/prompts', {'action': 'list'}, error=True)
        request('augmentor/handshake', {'protocol': 'augmentor/1', 'version': '0.0.0'}, error=True)
        request('augmentor/prompts', {'action': 'list'}, error=True)
        assert request('augmentor/handshake', {'protocol': 'augmentor/1', 'version': version})['version'] == version
        text = 'Keep café 日本語 😀 and\na second line.'
        saved = request('augmentor/prompts', {'action': 'save', 'name': 'windows-browser-proof', 'content': text})
        assert saved['ok'], saved
        assert next(row for row in saved['library']['prompts'] if row['name'] == 'windows-browser-proof')['content'] == text
        assert request('augmentor/prompts', {'action': 'list'})['library'] == saved['library']
        selected = request('harness.select', {'harness': 'dsh'})
        assert selected['harness'] == 'dsh', selected
        initialized = request('initialize'); assert initialized, initialized
        history = request('session.history', {'sessionId': session})
        assert 'Windows managed setup verified.' in json.dumps(history), history
        request('augmentor/update-plugin', {'version': '9.9.9'}, error=True)
        before = owner.request('status', root=root)
        assert before['dsh']['running'], before
        process.stdin.close(); process.stdin = None
        assert process.wait(timeout=15) == 0, 'The native host did not exit on browser disconnect.'
        reader.join(timeout=5)
        assert not reader.is_alive(), 'The native protocol output handle leaked.'
        after = owner.request('status', root=root)
        assert after['dsh']['running'], after
        assert before['companions']['prompts']['running'], before
        assert after['companions']['prompts'] == before['companions']['prompts'], after
        return {'passed': True, 'version': version, 'unicodeBinaryFrames': True,
            'handshakeRequired': True, 'versionMismatchBlocked': True, 'sharedPrompts': True,
            'realDshHistory': True, 'legacyUpdateBlocked': True, 'disconnectPreservesBackground': True,
            'scope': 'Actual AugmentorBrowserHost.exe with fixture-provided browser stdio; no real-browser registry/UI claim.'}
    finally:
        if process.poll() is None: process.kill()
        process.communicate(timeout=10)
        reader.join(timeout=5)
