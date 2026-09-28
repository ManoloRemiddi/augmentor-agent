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
    from lifecycle.windows_components import discover_browsers
    from platform_adapters.paths import runtime_directory
    spec = importlib.util.spec_from_file_location('browser_entrypoint', root/'scripts/launch-windows-browser.py')
    entrypoint = importlib.util.module_from_spec(spec); spec.loader.exec_module(entrypoint)
    argv = [str(root/'AugmentorBrowserHost.exe'), '--qualification-root', str(work), entrypoint.origin(root), '--parent-window=0']
    process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW, cwd=root, env={**os.environ})
    frames = queue.Queue();write_lock=threading.Lock();observations=[]
    browser_phase='ready';browser_busy=False
    def send_frame(value):
        raw=json.dumps(value,ensure_ascii=False).encode()
        with write_lock:
            process.stdin.write(struct.pack('<I',len(raw))+raw);process.stdin.flush()
    def read():
        nonlocal browser_phase
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
                value=json.loads(exact(size))
                if value.get('method')=='augmentor/maintenance':
                    # Renderer semantics are qualified in real Chromium by a
                    # separate proof. Here the fixture answers binary frames to
                    # exercise the actual compiled owner/relay/host transport.
                    action=value['params']['method'].removeprefix('host.maintenance.')
                    if browser_busy and action=='prepare':send_frame({'id':value['id'],'error':{'message':'Fixture browser has a draft.'}});continue
                    if action=='prepare':browser_phase='prepared'
                    elif action=='cancel':browser_phase='ready'
                    elif action=='commit':browser_phase='closing'
                    send_frame({'id':value['id'],'result':{'protocol':'augmentor-component-maintenance/1',
                        'phase':browser_phase,'active':0,'expiresInSeconds':30 if browser_phase in ('prepared','closing') else None}})
                else:frames.put(value)
        except Exception as error: frames.put(error)
    reader = threading.Thread(target=read, daemon=True); reader.start()
    serial = 0
    def request(method, params=None, *, error=False):
        nonlocal serial
        serial += 1; identity = str(serial)
        send_frame({'id': identity, 'method': method, 'params': params or {}})
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
        observations=discover_browsers(root,runtime_directory())
        assert [p.pid for p in observations]==[process.pid], 'Discovery must retain this exact native host.'
        participant=observations[0]
        assert participant.initial['connected'], participant.initial
        from lifecycle.windows_startup import Startup
        with Startup(runtime_directory(),maintenance=True): pass
        token='a'*32
        browser_busy=True
        try:participant.control('prepare',token)
        except ValueError:pass
        else:raise AssertionError('A browser draft must refuse preparation.')
        browser_busy=False
        assert participant.control('prepare',token)['phase']=='prepared'
        assert 'not started' in request('augmentor/prompts',{'action':'list'},error=True)['error']['message']
        assert participant.control('renew',token)['phase']=='prepared'
        assert participant.control('cancel',token)['phase']=='ready'
        assert request('augmentor/prompts',{'action':'list'})['ok']
        before = owner.request('status', root=root)
        assert before['dsh']['running'], before
        with Startup(runtime_directory(),maintenance=True):
            assert participant.control('prepare',token)['phase']=='prepared'
            assert participant.control('commit',token)['phase']=='closing'
            assert process.wait(timeout=15) == 0, 'The committed native host did not drain naturally.'
            assert participant.exited(), 'The retained kernel observation must see this exact host exit.'
        process.stdin.close(); process.stdin = None
        reader.join(timeout=5)
        assert not reader.is_alive(), 'The native protocol output handle leaked.'
        after = owner.request('status', root=root)
        assert after['dsh']['running'], after
        assert before['companions']['prompts']['running'], before
        assert after['companions']['prompts'] == before['companions']['prompts'], after
        return {'passed': True, 'version': version, 'unicodeBinaryFrames': True,
            'handshakeRequired': True, 'versionMismatchBlocked': True, 'sharedPrompts': True,
            'realDshHistory': True, 'legacyUpdateBlocked': True, 'disconnectPreservesBackground': True,
            'privateBrowserDiscovery':True,'nativeReservationWithRendererFixture':True,'nativeActionRefusal':True,
            'committedNaturalDrainWithStartupExclusion':True,'commitReplyBeforeObservedExit':True,
            'scope': 'Actual AugmentorBrowserHost.exe with fixture-provided browser stdio; no real-browser registry/UI claim.'}
    finally:
        for participant in observations:participant.close()
        if process.poll() is None: process.kill()
        process.communicate(timeout=10)
        reader.join(timeout=5)
