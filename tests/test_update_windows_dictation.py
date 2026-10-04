# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Native private Windows broker/lease/reopen proofs, no microphone or model."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'services'),str(ROOT/'apps/native')]
from augmentor_linux import dictation
from lifecycle.windows_dictation import discover_dictation
from lifecycle.windows_startup import Startup
from lifecycle.reservations import Reservations
from updates.windows_dictation_reopen import reopen


@unittest.skipUnless(sys.platform=='win32','Actual Windows pipe/process/session/file-sharing proof.')
class WindowsBrokerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from platform_adapters.windows_identity import private_directory
        cls.copy=tempfile.TemporaryDirectory(prefix='ag-windows-broker-code-')
        cls.addClassCleanup(cls.copy.cleanup)
        cls.project=private_directory(Path(cls.copy.name)/'project')
        for path in (ROOT/'services').rglob('*.py'):
            target=cls.project/path.relative_to(ROOT)
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
        target=cls.project/'apps/native/augmentor_linux/dictation.py'
        target.parent.mkdir(parents=True);shutil.copy2(ROOT/'apps/native/augmentor_linux/dictation.py',target)
        # A complete standalone interpreter, including its DLLs and libraries.
        shutil.copytree(Path(sys.executable).parent,cls.project/'python')
        (cls.project/'release.json').write_text(json.dumps({'target':'windows-'+('arm64' if 'arm' in os.environ.get('PROCESSOR_ARCHITECTURE','').lower() else 'x64'),
            'automaticInstallQualified':False,'customerDistribution':False,'qualificationStatus':'development-candidate'}))
        cls.python=cls.project/'python/python.exe'
        cls.script=cls.project/'services/dictation/server.py'
        cls.digest=hashlib.sha256(cls.python.read_bytes()).hexdigest()
        cls.original=cls.snapshot()

    @classmethod
    def snapshot(cls):
        return {path.relative_to(cls.project).as_posix():hashlib.sha256(path.read_bytes()).hexdigest()
            for path in cls.project.rglob('*') if path.is_file()}

    def setUp(self):
        from platform_adapters.windows_identity import private_directory
        self.temporary=tempfile.TemporaryDirectory(prefix='ag-windows-broker-state-')
        self.base=private_directory(Path(self.temporary.name)/'private')
        self.runtime=private_directory(self.base/'run');self.state=private_directory(self.base/'dictation')
        self.preference=b'{"enabled":false,"fixture":"preserved"}\n'
        (self.state/'preferences.json').write_bytes(self.preference)
        self.environment=patch.dict(os.environ,{'AUGMENTOR_DICTATION_STATE':str(self.state),
            'XDG_RUNTIME_DIR':str(self.runtime),'XDG_STATE_HOME':str(self.base/'state')})
        self.environment.start();self.children=[]

    def tearDown(self):
        try:
            # Only this private fixture's authenticated broker is addressed.
            try:dictation.request('conversation.release',{'token':'b'*32},start=False)
            except (RuntimeError,OSError,TimeoutError):pass
            peers=discover_dictation(self.project,self.runtime)
            try:
                for peer in peers:
                    with Reservations(keepalive=False) as group:
                        group.prepare(peer);group.commit(peer,checkpoint=lambda *_:None)
            finally:
                for peer in peers:peer.close()
        finally:
            for child in self.children:
                if child.poll() is None:child.terminate()  # Failed disposable fixture cleanup only.
                child.communicate(timeout=10)
            self.environment.stop()
            self.temporary.cleanup()

    def start(self,*,environment=None):
        child=subprocess.Popen([str(self.python),'-I','-Xutf8','-B',str(self.script)],
            env=environment,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        self.children.append(child);return child

    def observe(self,child=None):
        deadline=time.monotonic()+15
        while True:
            if child is not None and child.poll() is not None:self.fail(child.stderr.read().decode('utf-8','replace'))
            try:peers=discover_dictation(self.project,self.runtime)
            except FileNotFoundError:peers=[]
            if peers and all(peer.initial['ready'] for peer in peers):return peers
            for peer in peers:peer.close()
            if time.monotonic()>=deadline:self.fail('The disposable broker did not become discoverable.')
            time.sleep(.05)

    def immutable(self):self.assertEqual(self.snapshot(),self.original)

    def test_capture_refusal_cancel_startup_lifetime_normal_exit_and_one_shot_reopen(self):
        from platform_adapters import locks
        from platform_adapters.windows_identity import private_lock_descriptor,dictation_session_key
        child=self.start();peers=self.observe(child);self.assertEqual(len(peers),1);peer=peers[0]
        try:
            self.assertEqual(peer.pid,child.pid)
            self.assertEqual(peer.initial['session'],dictation_session_key(child.pid))
            self.assertFalse(dictation.request('status',start=False)['enabled'])
            descriptor=private_lock_descriptor(self.runtime/'installation.lock')
            try:
                with self.assertRaises(BlockingIOError):locks.flock(descriptor,locks.LOCK_EX|locks.LOCK_NB)
            finally:os.close(descriptor)
            dictation.request('conversation.acquire',{'token':'b'*32,'pid':os.getpid()},start=False)
            with self.assertRaises(ValueError):peer.control('prepare','a'*48)
            self.assertIsNone(child.poll())
            with self.assertRaisesRegex(RuntimeError,'busy'):
                dictation.request('conversation.acquire',{'token':'c'*32,'pid':os.getpid()},start=False)
            dictation.request('conversation.release',{'token':'b'*32},start=False)
            # Real pipe/process, synthetic alternate kernel session. Refuse
            # before prepare, even when ordinary replies omit login identity.
            with patch('platform_adapters.windows_identity.process_session_id',
                    side_effect=lambda pid=None:100 if pid is None else 101):
                with self.assertRaisesRegex(ValueError,'another Windows login session'):
                    peer.control('prepare','a'*48)
            self.assertEqual(peer.control('status')['phase'],'ready')
            with Reservations(keepalive=False) as group:
                group.prepare(peer)
                with self.assertRaises(RuntimeError):dictation.request('enable',{'enabled':True},start=False)
            self.assertEqual(peer.control('status')['phase'],'ready')
            with patch.dict(os.environ,{'AUGMENTOR_DICTATION_STATE':str(self.base/'other-state')}):
                with self.assertRaisesRegex(ValueError,'another session/state'):discover_dictation(self.project,self.runtime)
            from lifecycle.dictation_control import scope
            wrong={**scope(),'session':'f'*12}
            with patch('lifecycle.windows_dictation.scope',return_value=wrong):
                with self.assertRaisesRegex(ValueError,'another session/state'):discover_dictation(self.project,self.runtime)
            self.assertIsNone(child.poll())
            with Startup(self.runtime,maintenance=True):
                blocked=self.start(environment={**os.environ,'AUGMENTOR_DICTATION_STATE':str(self.base/'blocked-state')})
                _out,error=blocked.communicate(timeout=10)
                self.assertNotEqual(blocked.returncode,0);self.assertIn(b'WinError 32',error)
                with Reservations(keepalive=False) as group:
                    group.prepare(peer);group.commit(peer,checkpoint=lambda *_:None)
            self.assertEqual(child.wait(timeout=10),0)
        finally:peer.close()
        self.immutable()
        class Witness:dictation_reopening_started=False
        witness=Witness();captured={'instances':[],'hadBrowser':False,'hadDictation':True}
        self.assertTrue(reopen(witness,captured,self.project,self.runtime,self.digest,self.immutable,qualification=True))
        self.assertTrue(witness.dictation_reopened)
        with self.assertRaisesRegex(ValueError,'replayed'):
            reopen(witness,captured,self.project,self.runtime,self.digest,self.immutable,qualification=True)
        peers=self.observe()
        try:self.assertNotEqual(peers[0].pid,child.pid)
        finally:
            for peer in peers:peer.close()
        self.assertFalse(dictation.request('status',start=False)['enabled'])
        self.assertEqual((self.state/'preferences.json').read_bytes(),self.preference)
        self.immutable()

    def test_pending_record_refuses_start_without_replaying_or_removing_it(self):
        from platform_adapters.windows_identity import private_directory
        pending=private_directory(self.base/'updates')/'active.json';pending.write_bytes(b'')
        child=self.start();_out,error=child.communicate(timeout=10)
        self.assertNotEqual(child.returncode,0);self.assertIn(b'unfinished Augmentor update',error)
        self.assertEqual(pending.read_bytes(),b'');self.assertFalse(discover_dictation(self.project,self.runtime))
        # Read-only health retains startup exclusion while inspecting pending
        # bytes. Normal installed admission separately checks its lifetime lease.
        from lifecycle.windows_pending import require_clear
        with Startup(self.runtime):
            with self.assertRaisesRegex(RuntimeError,'unfinished'):require_clear(self.runtime)
        with Startup(self.runtime,maintenance=True):pass  # Recovery can observe while work remains fenced.
        self.immutable()

    def test_installed_gui_client_uses_fixed_python_and_private_session_authentication(self):
        from platform_adapters.windows_identity import private_file_descriptor,dictation_session_key
        driver="""import sys,json
from pathlib import Path
root=Path(sys.argv[1]);sys.path[:0]=[str(root/'services'),str(root/'apps/native')]
from augmentor_linux import dictation
sys.executable=str(root/'Augmentor.exe')
print(json.dumps(dictation.request('status')))
"""
        result=subprocess.run([str(self.python),'-I','-Xutf8','-B','-c',driver,str(self.project)],
            capture_output=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr.decode('utf-8','replace'))
        self.assertFalse(json.loads(result.stdout)['enabled'])
        peers=self.observe()
        try:self.assertEqual(peers[0].initial['session'],dictation_session_key(peers[0].pid))
        finally:
            for peer in peers:peer.close()
        _base,address,key=dictation.location();self.assertEqual(len(key),32)
        self.assertTrue(address.endswith(dictation_session_key()))
        with os.fdopen(private_file_descriptor(self.state/'auth.key'),'rb') as source:self.assertEqual(source.read(),key)
        import _winapi
        from lifecycle.dictation_control import scope
        link=self.base/'redirected-state';_winapi.CreateJunction(str(self.state),str(link))
        try:
            with self.assertRaises(PermissionError):dictation.windows_location(link)
            with patch.dict(os.environ,{'AUGMENTOR_DICTATION_STATE':str(link)}):
                with self.assertRaises(PermissionError):scope()
            self.assertEqual((self.state/'auth.key').read_bytes(),key)
        finally:os.rmdir(link)
        foreign=self.base/'inherited-key';foreign.mkdir()
        (foreign/'auth.key').write_bytes(b'x'*32)
        with self.assertRaises(PermissionError):dictation.windows_location(foreign)
        self.assertEqual((foreign/'auth.key').read_bytes(),b'x'*32)
        self.immutable()


if __name__=='__main__':unittest.main()
