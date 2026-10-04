# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real Windows sharing/handle inheritance, not an installer or shutdown proof."""
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
from lifecycle.windows_startup import Startup


def handoff_parent(runtime):
    import msvcrt
    import win32api
    import win32con
    # Only a duplicate is made inheritable. The normal ownership handle never
    # leaks to other subprocesses; the child receives an explicit handle list.
    with Startup(runtime, maintenance=True) as gate:
        current = win32api.GetCurrentProcess()
        duplicate = win32api.DuplicateHandle(current, msvcrt.get_osfhandle(gate.fd),
            current, 0, True, win32con.DUPLICATE_SAME_ACCESS)
        try:
            startup = subprocess.STARTUPINFO()
            startup.lpAttributeList = {'handle_list': [int(duplicate)]}
            child = subprocess.Popen([sys.executable, '-I', '-Xutf8', '-B', __file__,
                '--handoff-child', str(runtime), str(int(duplicate))], close_fds=True,
                startupinfo=startup, stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        finally: duplicate.Close()
        (runtime/'child.json').write_text(json.dumps({'pid':child.pid}), encoding='utf-8')
        while not (runtime/'parent-release').exists(): time.sleep(.02)


def handoff_child(runtime, value):
    import win32api
    import win32file
    try:
        win32file.GetFileInformationByHandle(value)  # Real inherited open file.
        (runtime/'child-ready').write_text('ready', encoding='utf-8')
        while not (runtime/'child-release').exists(): time.sleep(.02)
    finally: win32api.CloseHandle(value)


@unittest.skipUnless(sys.platform == 'win32', 'requires actual Windows file sharing')
class WindowsStartupFenceTests(unittest.TestCase):
    def setUp(self):
        from platform_adapters.windows_identity import private_directory
        self.temp = tempfile.TemporaryDirectory(prefix='augmentor-startup-fence-')
        self.runtime = private_directory(Path(self.temp.name)/'private')

    def tearDown(self): self.temp.cleanup()

    def blocked(self, *, maintenance=False):
        with self.assertRaises(OSError) as result:
            with Startup(self.runtime, maintenance=maintenance): pass
        self.assertEqual(result.exception.winerror, 32)

    def wait_path(self, name):
        deadline = time.monotonic()+10
        while not (self.runtime/name).exists():
            if time.monotonic() >= deadline: self.fail('The disposable startup process did not become ready.')
            time.sleep(.02)

    def test_readers_exclude_writer_and_writer_excludes_every_new_startup(self):
        with Startup(self.runtime), Startup(self.runtime):
            self.blocked(maintenance=True)
        with Startup(self.runtime, maintenance=True):
            self.blocked(); self.blocked(maintenance=True)
        with Startup(self.runtime, maintenance=True) as gate:
            with self.assertRaises(RuntimeError): gate.ready()
        with Startup(self.runtime): pass
        self.assertEqual((self.runtime/'startup.lock').read_bytes(), b'')
        self.assertFalse((self.runtime/'maintenance.json').exists())

    def test_inherited_gate_survives_parent_exit_and_crash_without_a_launch_gap(self):
        import win32api
        import win32con
        import win32event
        import win32file
        from platform_adapters.windows_identity import private_file_descriptor
        for crash in (False, True):
            with self.subTest(crash=crash):
                for name in ('child.json','child-ready','child-release','parent-release'):
                    (self.runtime/name).unlink(missing_ok=True)
                parent = subprocess.Popen([sys.executable,'-I','-Xutf8','-B',__file__,
                    '--handoff-parent',str(self.runtime)], stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                child = None
                try:
                    self.wait_path('child.json'); self.wait_path('child-ready')
                    pid = json.loads((self.runtime/'child.json').read_text(encoding='utf-8'))['pid']
                    child = win32api.OpenProcess(win32con.SYNCHRONIZE, False, pid)
                    self.blocked(); self.blocked(maintenance=True)
                    if crash: parent.kill()  # Deliberate failure of disposable coordinator.
                    else: (self.runtime/'parent-release').write_text('release', encoding='utf-8')
                    _out, errors = parent.communicate(timeout=10)
                    if not crash: self.assertEqual(parent.returncode, 0, errors.decode('utf-8', errors='replace'))
                    self.assertEqual(win32event.WaitForSingleObject(child, 0), win32event.WAIT_TIMEOUT)
                    self.blocked(); self.blocked(maintenance=True)
                    # The retained startup gate does not prevent the final
                    # installer gate once every application lifetime lease ends.
                    path = self.runtime/'installation.lock'
                    os.close(private_file_descriptor(path, writable=True, create=True))
                    final = win32file.CreateFile(str(path), win32con.GENERIC_READ|win32con.GENERIC_WRITE,
                        0, None, win32con.OPEN_EXISTING, 0, None)
                    try: self.blocked()
                    finally: final.Close()
                    (self.runtime/'child-release').write_text('release', encoding='utf-8')
                    self.assertEqual(win32event.WaitForSingleObject(child, 10000), win32event.WAIT_OBJECT_0)
                    with Startup(self.runtime), Startup(self.runtime): pass
                finally:
                    (self.runtime/'child-release').write_text('release', encoding='utf-8')
                    if parent.poll() is None: parent.kill()
                    parent.communicate(timeout=10)
                    if child is not None:
                        win32event.WaitForSingleObject(child, 10000); child.Close()


if __name__ == '__main__':
    if sys.argv[1:2] == ['--handoff-parent']: handoff_parent(Path(sys.argv[2]))
    elif sys.argv[1:2] == ['--handoff-child']: handoff_child(Path(sys.argv[2]), int(sys.argv[3]))
    else: unittest.main()
