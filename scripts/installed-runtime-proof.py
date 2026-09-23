#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Exercise the installed Debian runtime as an ordinary user with a local model fixture.

No source-checkout imports, developer model, provider credentials or system Node.
This proves installed backend behavior, not user onboarding or a full desktop VM.
"""
import http.server
import importlib.util
import json
import os
from pathlib import Path
import select
import shutil
import struct
import subprocess
import sys
import threading
import time
import zlib

APP = Path('/usr/lib/augmentor')
assert os.getuid() != 0, 'Run this proof as an ordinary user'
assert shutil.which('node') is None, 'A system Node installation would mask a packaging failure'
assert importlib.util.find_spec('PySide6') is None, 'Run companion proof before installing the desktop'
sys.path.insert(0, str(APP / 'apps/native'))
from augmentor_linux.pi_client import PiClient

work = Path.home() / 'augmentor-install-proof'; work.mkdir(exist_ok=True)
target = work / 'completed.txt'; target.unlink(missing_ok=True)
config = work / 'config'; state = work / 'state'
os.environ.update(AUGMENTOR_PI_CONFIG=str(config), AUGMENTOR_PI_STATE=str(state),
                  AUGMENTOR_SHARED_DATA=str(work / 'shared-data'), AUGMENTOR_SHARED_STATE=str(work / 'shared-state'),
                  AUGMENTOR_PI_NO_AUTOSTART='1', PI_OFFLINE='1')
(config / 'agent').mkdir(parents=True, exist_ok=True)
requests = []; slow = threading.Event(); images_received = []
image_path = work / 'large-image.png'
def png_chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
image_path.write_bytes(b'\x89PNG\r\n\x1a\n' + png_chunk(b'IHDR', struct.pack('>IIBBBBB', 3200, 2000, 8, 2, 0, 0, 0)) +
                      png_chunk(b'IDAT', zlib.compress((b'\x00' + bytes([17, 34, 51]) * 3200) * 2000)) + png_chunk(b'IEND', b''))


class Model(http.server.BaseHTTPRequestHandler):
    def log_message(self, *_): pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        requests.append(body)
        messages = body['messages']
        image_parts = [part['image_url']['url'] for message in messages if isinstance(message.get('content'), list)
                       for part in message['content'] if part.get('type') == 'image_url']
        images_received.extend(image_parts)
        self.send_response(200); self.send_header('Content-Type', 'text/event-stream'); self.end_headers()
        def chunk(delta, finish=None):
            value = {'id': 'fixture', 'object': 'chat.completion.chunk', 'created': 1, 'model': 'fixture',
                     'choices': [{'index': 0, 'delta': delta, 'finish_reason': finish}]}
            self.wfile.write(('data: ' + json.dumps(value) + '\n\n').encode()); self.wfile.flush()
        try:
            if 'SLOW' in json.dumps(messages):
                slow.set()
                for _ in range(200): chunk({'content': 'working '}); time.sleep(.05)
            elif 'READ_IMAGE' in json.dumps(messages) and not image_parts:
                chunk({'role': 'assistant', 'tool_calls': [{'index': 0, 'id': 'read-image', 'type': 'function',
                       'function': {'name': 'read', 'arguments': json.dumps({'path': str(image_path)})}}]})
                chunk({}, 'tool_calls')
            elif messages[-1]['role'] != 'tool' and not image_parts:
                chunk({'role': 'assistant', 'tool_calls': [{'index': 0, 'id': 'write-proof', 'type': 'function',
                       'function': {'name': 'write', 'arguments': json.dumps({'path': str(target), 'content': 'Installed Augmentor: Café π\n'})}}]})
                chunk({}, 'tool_calls')
            else:
                chunk({'role': 'assistant', 'content': 'The fixture file was written.'}); chunk({}, 'stop')
            self.wfile.write(b'data: [DONE]\n\n')
        except (BrokenPipeError, ConnectionResetError): pass


server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Model)
threading.Thread(target=server.serve_forever, daemon=True).start()
models = {'providers': {'fixture': {'baseUrl': f'http://127.0.0.1:{server.server_port}/v1',
           'api': 'openai-completions', 'apiKey': 'fixture-not-a-credential', 'models': [
               {'id': 'fixture', 'name': 'Installation fixture', 'reasoning': False, 'input': ['text', 'image'],
                'contextWindow': 32000, 'maxTokens': 2048}]}}}
(config / 'agent/models.json').write_text(json.dumps(models))
client = PiClient(); child = None
log = (work / 'runtime.log').open('ab')


def until(check, timeout=20):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if check(): return
        time.sleep(.05)
    raise AssertionError('Installed runtime check timed out')


def start():
    global child
    child = subprocess.Popen(['/usr/bin/augmentor-runtime'], stdin=subprocess.DEVNULL, stdout=log, stderr=log)
    def ready():
        assert child.poll() is None, (work / 'runtime.log').read_text()
        try: return client.call('host.describe')['pid'] == child.pid
        except Exception: return False
    until(ready)
    assert Path(f'/proc/{child.pid}/exe').resolve() == APP / 'node/bin/node'


def idle(sid):
    until(lambda: not next(row for row in client.call('session.list')['items'] if row['sessionId'] == sid)['running'])


def native_request(frame):
    process = subprocess.Popen(['/usr/bin/augmentor-browser-host'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log)
    try:
        def read(size):
            value = b''; end = time.monotonic() + 20
            while len(value) < size:
                assert select.select([process.stdout], [], [], max(0, end-time.monotonic()))[0], 'Native host timed out'
                chunk = os.read(process.stdout.fileno(), size-len(value))
                assert chunk, 'Native host exited without its response'
                value += chunk
            return value
        for request in [{'id':'compatibility','method':'augmentor/handshake','params':{'protocol':'augmentor/1','version':json.loads((APP/'release.json').read_text())['version']}},frame]:
            raw=json.dumps(request).encode();process.stdin.write(struct.pack('<I',len(raw))+raw);process.stdin.flush()
            size,=struct.unpack('<I',read(4));assert size<=1024*1024
            result=json.loads(read(size));assert 'error' not in result,result
        return result
    finally:
        process.stdin.close()
        try: process.wait(timeout=10)
        except subprocess.TimeoutExpired: process.kill(); process.wait()


try:
    start()
    assert client.call('models.validate', {'provider': 'fixture', 'model': 'fixture'})
    permission = client.call('settings.describe')['namespaces'][0]
    client.call('settings.mutate', {'ns': 'permission', 'expectedRevision': permission['revision'],
                'ops': [{'op': 'set', 'path': ['defaultPreset'], 'value': 'danger-full-access'}]})
    client.call('session.create', {'sessionId': 'install-proof', 'cwd': str(work), 'selection': {'provider': 'fixture', 'model': 'fixture'}})
    client.call('session.prompt', {'sessionId': 'install-proof', 'content': [{'type': 'text', 'text': 'Write the installation fixture file.'}]})
    idle('install-proof')
    assert target.read_text() == 'Installed Augmentor: Café π\n'
    history = client.call('session.history', {'sessionId': 'install-proof'})
    assert any(row['event']['type'] == 'tool/result' and not row['event']['data']['isError'] for row in history['events'])
    client.call('prompts.save', {'name': 'installation', 'content': 'Rewrite [clipboard]'})
    prompts = native_request({'id': 'prompts', 'method': 'augmentor/prompts', 'params': {'action': 'list'}})
    assert prompts['result']['ok'], prompts
    assert any(row['name'] == 'installation' for row in prompts['result']['library']['prompts'])
    client.call('host.shutdown'); child.wait(timeout=15)
    before = len(requests); start()
    assert client.call('session.history', {'sessionId': 'install-proof'}) == history
    assert len(requests) == before, 'Restart replayed a model request'
    client.call('session.prompt', {'sessionId': 'install-proof', 'content': [{'type': 'text', 'text': 'READ_IMAGE'}]})
    idle('install-proof')
    assert images_received, 'The SDK omitted the image'
    decoder = '''const fs=require('node:fs');const p=require('/usr/lib/augmentor/node_modules/@earendil-works/pi-coding-agent/node_modules/@silvia-odwyer/photon-node');
const url=fs.readFileSync(0,'utf8');const im=p.PhotonImage.new_from_byteslice(Buffer.from(url.split(',')[1],'base64'));
console.log(JSON.stringify({width:im.get_width(),height:im.get_height()}));im.free();'''
    dimensions = json.loads(subprocess.check_output([str(APP / 'node/bin/node'), '-e', decoder], input=images_received[0], text=True))
    assert 0 < dimensions['width'] < 3200 and 0 < dimensions['height'] < 2000, dimensions
    client.call('session.prompt', {'sessionId': 'install-proof', 'content': [{'type': 'text', 'text': 'SLOW'}]})
    assert slow.wait(15)
    assert client.call('session.cancel', {'sessionId': 'install-proof'})['accepted']
    idle('install-proof')
    stopped = client.call('session.history', {'sessionId': 'install-proof'})
    assert stopped['events'][-1]['event']['data']['reason']['kind'] == 'aborted'
    assert (state / 'runtime.sock').stat().st_mode & 0o777 == 0o600
    result = {'packagedNode': True, 'systemNodeAbsent': True, 'qtAbsent': True, 'fileToolVerified': True,
              'sharedPromptsViaNativeHost': True, 'restartPreservedHistoryWithoutReplay': True, 'stopVerified': True,
              'sdkImageReadAndResize': dimensions}
    maintenance=APP/'scripts/maintenance.py'
    if maintenance.exists():
        prepared=json.loads(subprocess.check_output(['python3',str(maintenance),'prepare'],text=True))
        child.wait(timeout=20)
        assert prepared['prepared'] and prepared['dataPreserved']
        snapshot=Path(prepared['backup'])
        assert (snapshot/'config/pi/agent/models.json').read_bytes()==(config/'agent/models.json').read_bytes()
        assert (snapshot/'data/shared/prompts.sqlite3').is_file()
        assert not (state/'runtime.sock').exists()
        assert not (work/'shared-state/prompts.sock').exists()
        assert not (work/'shared-state/dual-memory.sock').exists()
        assert (snapshot/'data/shared/dual-memory.sqlite3').is_file()
        result['idleMaintenanceClosedServicesAndBackedUpData']=True
    (work / 'result.json').write_text(json.dumps(result, indent=2)); print(json.dumps(result))
finally:
    if child and child.poll() is None:
        child.terminate()
        try: child.wait(timeout=10)
        except subprocess.TimeoutExpired: child.kill(); child.wait()
    server.shutdown(); server.server_close(); log.close()
