# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real Unix peers and exit observations; inert helpers, no application work."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'services'))
from platform_adapters.peer_process import PeerProcess
from platform_adapters.transport import LocalSocket


@unittest.skipUnless(sys.platform in ('linux','darwin'),'requires native Unix socket/process APIs')
class PeerProcessTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='ap-');self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name).resolve();self.endpoint=self.root/'peer.sock'
        source="""import socket,sys,time
from pathlib import Path
root=Path(sys.argv[1])
with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as server:
 server.bind(str(root/'peer.sock'));server.listen(8)
 (root/'ready').write_bytes(b'Inert server is listening.')
 deadline=time.monotonic()+15
 while not (root/'exit').exists():
  if time.monotonic()>deadline:raise TimeoutError('The inert fixture was not closed.')
  time.sleep(.02)
"""
        self.child=subprocess.Popen([sys.executable,'-I','-B','-c',source,str(self.root)],
            stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        def close():
            (self.root/'exit').write_bytes(b'Exit only the inert child.')
            self.child.communicate(timeout=20)
        self.addCleanup(close)
        deadline=time.monotonic()+10
        while not (self.root/'ready').exists():
            if self.child.poll() is not None:self.fail(self.child.stderr.read().decode(errors='replace'))
            if time.monotonic()>deadline:self.fail('The inert peer did not become ready.')
            time.sleep(.02)

    def connect(self):
        peer=LocalSocket();self.addCleanup(peer.close);peer.settimeout(5);peer.connect(self.endpoint)
        return peer

    def test_actual_socket_peer_exit_is_observed_and_new_connection_verified(self):
        with PeerProcess(self.connect(),Path(sys.executable).resolve()) as observed:
            self.assertEqual(observed.pid,self.child.pid);self.assertFalse(observed.exited())
            confirmation=self.connect()
            observed.verify(confirmation)
            (self.root/'exit').write_bytes(b'Exit inert original peer.')
            self.assertTrue(observed.exited(timeout=10));self.assertEqual(self.child.wait(timeout=10),0)
            with self.assertRaises(ValueError):observed.verify(confirmation)

    def test_closing_observation_preserves_the_running_peer(self):
        observed=PeerProcess(self.connect(),Path(sys.executable).resolve());observed.close()
        self.assertIsNone(self.child.poll())
        with self.assertRaises(ValueError):observed.exited()

    def test_unrelated_executable_refuses_without_stopping_peer(self):
        with self.assertRaises(ValueError):PeerProcess(self.connect(),self.root/'unrelated-executable')
        self.assertIsNone(self.child.poll())


if __name__=='__main__':unittest.main()
