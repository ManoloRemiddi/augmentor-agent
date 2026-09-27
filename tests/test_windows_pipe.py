# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real Windows pipe transport; no API mocks stand in for kernel behavior."""
import json
from pathlib import Path
import socketserver
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'services'))


@unittest.skipUnless(sys.platform == 'win32', 'requires native Windows named pipes')
class WindowsPipeTests(unittest.TestCase):
    def test_framing_large_unicode_response_and_repeated_connections(self):
        from platform_adapters.windows_pipe import PipeSocket, ThreadingPipeServer
        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                self.connection.settimeout(3)
                self.connection.verify_peer()
                line = self.rfile.readline(1024*1024)
                if not line:
                    return
                request = json.loads(line)
                self.wfile.write((json.dumps({'id': request['id'], 'result': 'café 日本語 '*20000})+'\n').encode())
        with tempfile.TemporaryDirectory() as temporary:
            endpoint = Path(temporary)/'companion.sock'
            with ThreadingPipeServer(endpoint, Handler) as server:
                worker = threading.Thread(target=server.serve_forever)
                worker.start()
                try:
                    for _ in range(5):
                        with PipeSocket() as probe:
                            probe.settimeout(1); probe.connect(endpoint)
                    for index in range(3):
                        with PipeSocket() as connection:
                            connection.settimeout(5); connection.connect(endpoint)
                            connection.sendall(json.dumps({'id': index}).encode()+b'\n')
                            with connection.makefile('rb') as reader:
                                result = json.loads(reader.readline(1024*1024))
                            self.assertEqual(result, {'id': index, 'result': 'café 日本語 '*20000})
                finally:
                    server.shutdown(); worker.join(timeout=5)
                    self.assertFalse(worker.is_alive())

    def test_existing_pipe_name_is_not_taken_over(self):
        from platform_adapters.windows_pipe import PipeListener
        import pywintypes
        with tempfile.TemporaryDirectory() as temporary:
            endpoint = Path(temporary)/'companion.sock'
            owner = PipeListener(endpoint)
            try:
                with self.assertRaises(pywintypes.error):
                    PipeListener(endpoint)
            finally:
                owner.close()
            replacement = PipeListener(endpoint)
            replacement.close()

    def test_read_timeout_cancels_io_and_server_can_continue(self):
        from platform_adapters.windows_pipe import PipeSocket, PipeListener
        with tempfile.TemporaryDirectory() as temporary:
            endpoint = Path(temporary)/'companion.sock'
            listener = PipeListener(endpoint)
            with PipeSocket() as client:
                try:
                    client.settimeout(.05); client.connect(endpoint)
                    server, _ = listener.accept(1)
                    try:
                        with self.assertRaises(TimeoutError):
                            client.recv(100)
                        server.sendall(b'after-timeout\n')
                        self.assertEqual(client.recv(100), b'after-timeout\n')
                    finally:
                        server.close()
                finally:
                    listener.close()


if __name__ == '__main__':
    unittest.main()
