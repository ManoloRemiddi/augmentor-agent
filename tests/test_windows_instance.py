# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest


@unittest.skipUnless(sys.platform == 'win32', 'requires Windows pipes and Qt dispatch')
class WindowsInstanceTests(unittest.TestCase):
    def test_authenticated_pipe_dispatches_on_qt_thread_and_replies(self):
        from PySide6.QtCore import QCoreApplication
        from augmentor_linux.windows_instance import Client, Server, Lock
        from augmentor_linux.platform_runtime import LocalSocket, private_directory
        app = QCoreApplication.instance() or QCoreApplication([])
        with tempfile.TemporaryDirectory() as temporary:
            root = private_directory(Path(temporary)/'private')
            address = str(root/'instance.sock')
            first, second = Lock(root/'instance.lock'), Lock(root/'instance.lock')
            self.assertTrue(first.tryLock(200)); self.assertFalse(second.tryLock(200))
            server = Server(); received = []; results = []
            main_thread = threading.get_ident()
            def activate():
                connection = server.nextPendingConnection()
                if not connection: return
                received.append((threading.get_ident(), bytes(connection.readAll()).decode()))
                connection.write(b'{"accepted":true}\n'); connection.disconnectFromServer()
            server.newConnection.connect(activate)
            server.listen(address)
            def client():
                try:
                    with LocalSocket() as peer:
                        peer.settimeout(3); peer.connect(address)
                        peer.sendall('onboarding:café 🪟\n'.encode())
                        with peer.makefile('rb') as stream: results.append(json.loads(stream.readline()))
                except BaseException as error: results.append(error)
            worker = threading.Thread(target=client); worker.start()
            try:
                deadline = time.monotonic()+5
                while worker.is_alive() and time.monotonic()<deadline:
                    app.processEvents(); time.sleep(.005)
                worker.join(timeout=1)
                self.assertFalse(worker.is_alive())
                self.assertEqual(received, [(main_thread, 'onboarding:café 🪟')])
                self.assertEqual(results, [{'accepted': True}])
                launcher = Client(); launcher.connectToServer(address)
                self.assertTrue(launcher.waitForConnected(500))
                launcher.write(b'show'); launcher.close()
                deadline = time.monotonic()+3
                while len(received)<2 and time.monotonic()<deadline:
                    app.processEvents(); time.sleep(.005)
                self.assertEqual(received[-1], (main_thread, 'show'))
            finally:
                server.close(); first.close(); second.close()
            self.assertTrue(second.tryLock(200)); second.close()


if __name__ == '__main__': unittest.main()
