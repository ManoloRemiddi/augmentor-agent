# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual Windows relay framing and lease; no SDK or provider can mask the pipe."""
import base64
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'services'))
VERSION = 'augmentor-pipe-server/1'


@unittest.skipUnless(sys.platform == 'win32', 'requires native Windows named pipes')
class WindowsPipeServerRelayTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.endpoint = str(Path(self.temporary.name) / 'owned-relay.sock')
        # A stalled helper reports thread locations, never application payloads.
        probe = 'import faulthandler,runpy,sys;faulthandler.dump_traceback_later(3);sys.argv=sys.argv[1:];runpy.run_path(sys.argv[0],run_name="__main__")'
        self.child = subprocess.Popen(
            [sys.executable, '-I', '-Xutf8', '-B', '-c', probe, str(ROOT / 'services/platform_adapters/pipe_server_relay.py'), self.endpoint],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.frames, self.errors, self.clients = queue.Queue(), [], []

        def read_frames():
            try:
                for raw in self.child.stdout:
                    self.frames.put(json.loads(raw))
            except Exception as error:
                self.frames.put(error)
            finally:
                self.frames.put(None)

        self.reader = threading.Thread(target=read_frames)
        self.reader.start()
        self.diagnostics = threading.Thread(target=lambda: self.errors.append(self.child.stderr.read()))
        self.diagnostics.start()
        self.addCleanup(self.close)
        self.assertEqual(self.next(), {'version': VERSION, 'type': 'ready'})

    def close(self):
        forced = False
        for client in self.clients:
            client.close()
        if self.child.poll() is None:
            self.child.stdin.close()
            try:
                self.child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Only this test's exact owned child, never an adopted PID.
                self.child.kill()
                self.child.wait(timeout=5)
                forced = True
        if not self.child.stdin.closed:
            self.child.stdin.close()
        self.reader.join(timeout=5)
        self.diagnostics.join(timeout=5)
        self.assertFalse(self.reader.is_alive())
        self.assertFalse(self.diagnostics.is_alive())
        self.child.stdout.close()
        self.child.stderr.close()
        self.assertFalse(forced, b''.join(self.errors).decode(errors='replace'))

    def next(self):
        frame = self.frames.get(timeout=5)
        self.assertIsInstance(frame, dict, b''.join(self.errors).decode(errors='replace'))
        self.assertEqual(frame['version'], VERSION)
        return frame

    def connect(self):
        from platform_adapters.windows_pipe import PipeSocket
        client = PipeSocket()
        client.settimeout(3)
        client.connect(self.endpoint)
        self.clients.append(client)
        self.assertEqual(client.verify_peer(), self.child.pid)
        frame = self.next()
        self.assertEqual(frame['type'], 'connect')
        return client, frame['id']

    def send(self, **value):
        self.child.stdin.write((json.dumps({'version': VERSION, **value}) + '\n').encode('ascii'))
        self.child.stdin.flush()

    def test_bidirectional_binary_frames_preserve_client_identity_and_control_is_only_data(self):
        first, first_id = self.connect()
        second, second_id = self.connect()
        self.assertNotEqual(first_id, second_id)
        data = b'\x00\xff' + 'café 日本語 😀'.encode() * 4000 + b'\n{"version":"augmentor-pipe-server/1","type":"shutdown"}\n'
        first.sendall(data)
        received = bytearray()
        while len(received) < len(data):
            frame = self.next()
            self.assertEqual((frame['type'], frame['id']), ('data', first_id))
            part = base64.b64decode(frame['data'], validate=True)
            self.assertLessEqual(len(part), 65536)
            received.extend(part)
        self.assertEqual(received, data)
        reply = b'\x00\xfe' + 'Independent reply café'.encode() * 1000
        self.send(type='data', id=second_id, data=base64.b64encode(reply).decode())
        received = bytearray()
        while len(received) < len(reply):
            received.extend(second.recv(65536))
        self.assertEqual(received, reply)
        self.send(type='close', id=first_id)
        self.assertEqual(first.recv(16), b'')
        self.assertEqual(self.child.poll(), None)

    def test_parent_eof_closes_the_owned_listener_and_connected_client(self):
        client, _identity = self.connect()
        self.child.stdin.close()
        self.assertEqual(self.child.wait(timeout=5), 0)
        self.assertEqual(client.recv(16), b'')
        self.diagnostics.join(timeout=5)
        self.assertNotIn(b'Private Windows listener was refused', b''.join(self.errors))

    def test_invalid_control_fails_closed_without_treating_it_as_client_bytes(self):
        client, identity = self.connect()
        self.send(type='data', id=identity, data='%%%')
        self.assertEqual(self.child.wait(timeout=5), 1)
        self.assertEqual(client.recv(16), b'')
        self.diagnostics.join(timeout=5)
        self.assertIn(b'Private Windows listener was refused', b''.join(self.errors))


@unittest.skipUnless(sys.platform == 'win32', 'requires Windows handles and Node pipe ownership')
class WindowsNodeRelayLeaseTests(unittest.TestCase):
    def test_node_owner_exit_releases_its_relay_without_using_the_cleanup_job(self):
        import win32api, win32con, win32event
        from platform_adapters.processes import OwnedProcess
        node = Path(os.environ.get('AUGMENTOR_PI_NODE', ROOT / 'outputs/runtime/node/node.exe'))
        self.assertTrue(node.is_file(), 'The prepared product Node runtime is required.')
        code = '''const {spawn}=require('node:child_process');
const child=spawn(process.argv[1],['-I','-Xutf8','-B',process.argv[2],process.argv[3]],{stdio:'pipe',windowsHide:true});
child.stderr.pipe(process.stderr);
let buffer='';child.stdout.on('data',bytes=>{buffer+=bytes;let end;
 while((end=buffer.indexOf('\\n'))>=0){const frame=JSON.parse(buffer.slice(0,end));buffer=buffer.slice(end+1);
  if(frame.type==='ready')console.log(JSON.stringify({ready:true,owner:process.pid,relay:child.pid}));
  else if(frame.type==='connect'||frame.type==='close')console.log(JSON.stringify({observed:frame.type}));}});
process.stdin.once('data',()=>process.exit(0));
'''
        with tempfile.TemporaryDirectory() as temporary:
            endpoint = str(Path(temporary) / 'node-owned-relay.sock')
            owned = OwnedProcess([str(node), '-e', code, sys.executable,
                str(ROOT / 'services/platform_adapters/pipe_server_relay.py'), endpoint],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            frames, errors, handles = queue.Queue(), [], []
            def read_frames():
                for line in owned.process.stdout:
                    frames.put(line)
            reader = threading.Thread(target=read_frames)
            diagnostics = threading.Thread(target=lambda: errors.append(owned.process.stderr.read()))
            reader.start(); diagnostics.start()
            try:
                identity = json.loads(frames.get(timeout=5))
                self.assertTrue(identity['ready'])
                for pid in (identity['owner'], identity['relay']):
                    handles.append(win32api.OpenProcess(win32con.SYNCHRONIZE, False, pid))
                from platform_adapters.windows_pipe import PipeSocket
                with PipeSocket() as peer:
                    peer.settimeout(3); peer.connect(endpoint)
                    self.assertEqual(peer.verify_peer(), identity['relay'])
                    self.assertEqual(json.loads(frames.get(timeout=5)), {'observed': 'connect'})
                self.assertEqual(json.loads(frames.get(timeout=5)), {'observed': 'close'})
                owned.process.stdin.write(b'exit\n'); owned.process.stdin.flush()
                self.assertEqual(win32event.WaitForSingleObject(handles[0], 5000), win32event.WAIT_OBJECT_0)
                # The enclosing cleanup Job remains open and is not terminated
                # until after this assertion, so it cannot mask a broken lease.
                self.assertEqual(win32event.WaitForSingleObject(handles[1], 5000), win32event.WAIT_OBJECT_0,
                    'The relay outlived its original Node owner.')
                self.assertEqual(owned.wait_graceful(timeout=5), 0)
            finally:
                owned.terminate(); owned.wait(timeout=5)
                for handle in handles:
                    handle.Close()
                owned.process.stdin.close()
                reader.join(timeout=5); diagnostics.join(timeout=5)
                self.assertFalse(reader.is_alive()); self.assertFalse(diagnostics.is_alive())
                owned.process.stdout.close(); owned.process.stderr.close()


if __name__ == '__main__':
    unittest.main()
