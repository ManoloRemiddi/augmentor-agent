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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'services'))


@unittest.skipUnless(sys.platform == 'win32', 'requires Windows Job objects')
class WindowsProcessTests(unittest.TestCase):
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
