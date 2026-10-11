# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual Windows relay framing and lease; no SDK or provider can mask the pipe."""
import base64
import json
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
        self.assertEqual(b''.join(self.errors), b'')

    def test_invalid_control_fails_closed_without_treating_it_as_client_bytes(self):
        client, identity = self.connect()
        self.send(type='data', id=identity, data='%%%')
        self.assertEqual(self.child.wait(timeout=5), 1)
        self.assertEqual(client.recv(16), b'')
        self.diagnostics.join(timeout=5)
        self.assertIn(b'Private Windows listener was refused', b''.join(self.errors))


if __name__ == '__main__':
    unittest.main()
