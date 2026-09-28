# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real private transport; fake bridge semantics are explicitly separate."""
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'services'))
from lifecycle.browser_control import BrowserControlServer, Records, PROTOCOL
from platform_adapters.transport import LocalSocket
from platform_adapters.paths import private_directory
from platform_adapters import locks
from platform_adapters.private_files import descriptor


@unittest.skipUnless(sys.platform in ('linux','win32'),'Native Windows and portable Linux transport qualification')
class BrowserControlTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='augmentor-browser-control-')
        self.root=private_directory(Path(self.temp.name)/'private')
        self.observed=[];self.connections=[]
        self.ready=[]
        def verify(pid): self.observed.append(pid)
        self.server=BrowserControlServer(ROOT,self.root,verify_bridge=verify,timeout=.2,
            on_ready=lambda:self.ready.append(self.server.bridge is not None))
        self.server.__enter__()

    def tearDown(self):
        self.server.close()
        for connection in self.connections: connection.close()
        self.temp.cleanup()

    def connect(self):
        peer=LocalSocket();peer.settimeout(3);peer.connect(str(self.server.endpoint));self.connections.append(peer)
        return Records(peer)

    def request(self, kind, **fields):
        peer=self.connect();peer.write({'protocol':PROTOCOL,'kind':kind,**fields})
        return peer.read(time.monotonic()+3)

    def register(self):
        peer=self.connect();peer.write({'protocol':PROTOCOL,'kind':'bridge','nonce':self.server.nonce})
        self.assertTrue(peer.read(time.monotonic()+3)['ok'])
        # The wire acknowledgment can arrive before the handler publishes its
        # link; wait only on a read-only observation, never replay a mutation.
        end=time.monotonic()+3
        while self.server.bridge is None or not self.ready:
            if time.monotonic()>end:self.fail('Bridge not published')
            time.sleep(.001)
        return peer

    def test_identity_held_lock_and_registration_are_private_and_bounded(self):
        identity=self.request('describe')
        self.assertEqual(identity['pid'],os.getpid());self.assertEqual(identity['buildRoot'],str(ROOT))
        self.assertFalse(identity['connected']);self.assertNotIn('nonce',identity)
        lease=descriptor(self.server.lock_path,writable=True)
        try:
            with self.assertRaises(BlockingIOError):locks.flock(lease,locks.LOCK_EX|locks.LOCK_NB)
        finally:os.close(lease)
        self.assertFalse(self.request('bridge',nonce='wrong')['ok']);self.assertEqual(self.observed,[])
        self.assertEqual(self.ready,[])
        self.register();self.assertEqual(self.observed,[os.getpid()])
        self.assertEqual(self.ready,[True])
        self.assertTrue(self.request('describe')['connected'])
        self.assertFalse(self.request('bridge',nonce=self.server.nonce)['ok'])
        self.assertEqual(self.ready,[True])
        self.assertTrue(self.request('describe')['connected'])

    def test_failed_readiness_does_not_leave_a_discoverable_live_bridge(self):
        def fail(): raise RuntimeError('Disposable startup callback failed.')
        self.server.on_ready=fail
        peer=self.connect();peer.write({'protocol':PROTOCOL,'kind':'bridge','nonce':self.server.nonce})
        self.assertTrue(peer.read(time.monotonic()+3)['ok'])
        self.assertFalse(peer.read(time.monotonic()+3)['ok'])
        end=time.monotonic()+3
        while self.request('describe')['connected']:
            if time.monotonic()>end:self.fail('Failed readiness left a live bridge.')
            time.sleep(.001)

    def test_control_round_trip_and_timeout_never_replay(self):
        bridge=self.register();seen=[]
        def responder():
            row=bridge.read(time.monotonic()+3);seen.append(row)
            bridge.write({'protocol':PROTOCOL,'id':row['id'],'result':{'protocol':'augmentor-component-maintenance/1','phase':'prepared','active':0}})
        worker=threading.Thread(target=responder);worker.start()
        response=self.request('maintenance',method='host.maintenance.prepare',params={'token':'a'*32})
        worker.join(timeout=3);self.assertFalse(worker.is_alive())
        self.assertEqual(response['result']['phase'],'prepared');self.assertEqual(len(seen),1)
        response=self.request('maintenance',method='host.maintenance.renew',params={'token':'a'*32})
        self.assertFalse(response['ok']);self.assertIn('no request was replayed',response['error'])
        late=bridge.read(time.monotonic()+3)
        bridge.write({'protocol':PROTOCOL,'id':late['id'],'result':{'late':True}})
        self.assertTrue(self.request('describe')['connected'])
        self.assertFalse(self.request('maintenance',method='host.shutdown',params={})['ok'])

    def test_lost_bridge_releases_waiter_and_does_not_adopt_a_new_connection(self):
        bridge=self.register();result=[]
        call=threading.Thread(target=lambda:result.append(self.request('maintenance',method='host.maintenance.status',params={})))
        call.start();bridge.read(time.monotonic()+3);bridge.connection.close();call.join(timeout=3)
        self.assertFalse(call.is_alive());self.assertFalse(result[0]['ok'])
        end=time.monotonic()+3
        while self.server.bridge is not None:
            if time.monotonic()>end:self.fail('Disconnected bridge not released')
            time.sleep(.001)
        self.register();self.assertTrue(self.request('describe')['connected'])
        self.assertEqual(len(result),1)

    def test_oversized_and_malformed_records_do_not_close_the_bridge(self):
        self.register()
        malformed=self.connect();malformed.connection.sendall(b'{bad json}\n')
        self.assertFalse(malformed.read(time.monotonic()+3)['ok'])
        oversized=self.connect();oversized.connection.sendall(b'x'*65537+b'\n')
        self.assertFalse(oversized.read(time.monotonic()+3)['ok'])
        self.assertTrue(self.request('describe')['connected'])


if __name__=='__main__':unittest.main()
