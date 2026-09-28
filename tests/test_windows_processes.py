# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Kernel proof that an owned process range cannot leave detached descendants."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'services'))


@unittest.skipUnless(sys.platform == 'win32', 'requires Windows Job objects')
class WindowsProcessTests(unittest.TestCase):
    def test_graceful_wait_preserves_surviving_descendant_until_its_own_exit(self):
        import win32api,win32con,win32event
        from platform_adapters.processes import OwnedProcess
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);record=root/'child.pid';release=root/'release'
            descendant=root/'descendant.py'
            descendant.write_text('import sys,time\nfrom pathlib import Path\nwhile not Path(sys.argv[1]).exists():time.sleep(.02)\n',encoding='utf-8')
            target=root/'parent.py'
            target.write_text('''import subprocess,sys
from pathlib import Path
child=subprocess.Popen([sys.executable,sys.argv[1],sys.argv[2]],creationflags=subprocess.DETACHED_PROCESS,
 stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
Path(sys.argv[3]).write_text(str(child.pid))
''',encoding='utf-8')
            child=OwnedProcess([sys.executable,str(target),str(descendant),str(release),str(record)],
                stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            handle=None
            try:
                self.assertEqual(child.process.wait(timeout=10),0)
                handle=win32api.OpenProcess(win32con.SYNCHRONIZE,False,int(record.read_text()))
                self.assertFalse(child.drained())
                with self.assertRaises(subprocess.TimeoutExpired):child.wait_graceful(timeout=.1)
                self.assertEqual(win32event.WaitForSingleObject(handle,0),win32event.WAIT_TIMEOUT)
                release.write_text('fixture complete')
                self.assertEqual(child.wait_graceful(timeout=5),0)
                self.assertEqual(win32event.WaitForSingleObject(handle,0),win32event.WAIT_OBJECT_0)
            finally:
                child.terminate();child.wait(timeout=5)
                if handle:handle.Close()

    def test_failed_job_configuration_closes_the_kernel_handle(self):
        import ctypes
        from ctypes import wintypes
        import win32api
        import win32job
        from platform_adapters.processes import OwnedProcess
        count = ctypes.WinDLL('kernel32', use_last_error=True).GetProcessHandleCount
        count.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        count.restype = wintypes.BOOL
        def handles():
            value = wintypes.DWORD()
            self.assertTrue(count(int(win32api.GetCurrentProcess()), ctypes.byref(value)))
            return value.value
        before = handles()
        with patch.object(win32job, 'QueryInformationJobObject', side_effect=RuntimeError('fixture job configuration failure')):
            for _ in range(5):
                with self.assertRaisesRegex(RuntimeError, 'fixture job'):
                    OwnedProcess([sys.executable, '-c', 'raise AssertionError("must not launch")'])
        self.assertEqual(handles(), before)

    def test_binary_stdio_and_unicode_environment_reach_contained_workload(self):
        from platform_adapters.processes import OwnedProcess
        code = '''import os,sys
value=sys.stdin.buffer.read()
sys.stdout.buffer.write(value+os.environ['AUGMENTOR_STDIO_FIXTURE'].encode('utf-8'))
sys.stdout.buffer.flush()
sys.stderr.buffer.write(b'fixture-stderr')
sys.stderr.buffer.flush()
'''
        child = OwnedProcess([sys.executable, '-Xutf8', '-c', code], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env={**os.environ, 'AUGMENTOR_STDIO_FIXTURE': 'café 秘密'})
        try:
            output, errors = child.process.communicate(b'\x00binary\xff', timeout=10)
            self.assertEqual(child.wait(timeout=5), 0)
            self.assertEqual(output, b'\x00binary\xff'+'café 秘密'.encode('utf-8'))
            self.assertEqual(errors, b'fixture-stderr')
        finally:
            child.terminate(); child.wait(timeout=5)

    def test_owner_crash_stops_parent_and_detached_grandchild(self):
        import win32api
        import win32con
        import win32event
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            grandchild = root/'grandchild.py'
            grandchild.write_text('import time\ntime.sleep(300)\n', encoding='utf-8')
            target = root/'target.py'
            target.write_text('''import json,os,subprocess,sys,time
from pathlib import Path
child=subprocess.Popen([sys.executable,sys.argv[1]],creationflags=subprocess.DETACHED_PROCESS)
Path(sys.argv[2]).write_text(json.dumps([os.getpid(),child.pid]))
time.sleep(300)
''', encoding='utf-8')
            owner = root/'owner.py'
            owner.write_text('''import sys,time
sys.path.insert(0,sys.argv[1])
from platform_adapters.processes import OwnedProcess
child=OwnedProcess([sys.executable,sys.argv[2],sys.argv[3],sys.argv[4]],stdout=sys.stdout,stderr=sys.stderr)
while child.poll() is None:time.sleep(.05)
sys.exit(child.wait())
''', encoding='utf-8')
            record = root/'pids.json'
            process = subprocess.Popen([sys.executable, '-Xutf8', '-B', str(owner), str(ROOT/'services'),
                str(target), str(grandchild), str(record)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW)
            handles = []
            try:
                deadline = time.monotonic()+10
                while not record.exists() and process.poll() is None and time.monotonic()<deadline:
                    time.sleep(.05)
                if not record.exists():
                    if process.poll() is None:process.kill()
                    _output, errors = process.communicate(timeout=5)
                    self.fail('Job helper did not launch its contained workload: '+errors.decode('utf-8', errors='replace'))
                for pid in json.loads(record.read_text()):
                    handles.append(win32api.OpenProcess(win32con.SYNCHRONIZE | win32con.PROCESS_TERMINATE, False, pid))
                process.kill(); process.communicate(timeout=5)
                for handle in handles:
                    self.assertEqual(win32event.WaitForSingleObject(handle, 5000), win32event.WAIT_OBJECT_0)
            finally:
                if process.poll() is None:
                    process.kill()
                process.communicate(timeout=5)
                for handle in handles:
                    if win32event.WaitForSingleObject(handle, 0) != win32event.WAIT_OBJECT_0:
                        win32api.TerminateProcess(handle, 1)
                    handle.Close()


if __name__ == '__main__':
    unittest.main()
