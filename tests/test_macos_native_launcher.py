# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real native embedding tests; run on an ARM64 Mac with the pinned Python.

This fixture isolates the launcher contract, not distribution signing or TCC.
"""
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('native_launcher_builder', ROOT/'scripts/package-macos.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


@unittest.skipUnless(sys.platform == 'darwin' and platform.machine() == 'arm64', 'requires ARM64 macOS')
class NativeLauncherTests(unittest.TestCase):
    def test_native_identity_relocation_isolation_arguments_and_exit(self):
        with tempfile.TemporaryDirectory(prefix='augmentor-launcher-') as temporary:
            root = Path(temporary)
            app = root/'Build.app'
            project = app/'Contents/Resources/app'
            (project/'scripts').mkdir(parents=True)
            (project/'python').symlink_to(sys.base_prefix, target_is_directory=True)
            (project/'scripts/launch-component.py').write_text('''
import ctypes, json, os, subprocess, sys
lib = ctypes.CDLL('/usr/lib/libproc.dylib')
buf = ctypes.create_string_buffer(4096)
assert lib.proc_pidpath(os.getpid(), buf, len(buf)) > 0
child = subprocess.check_output([sys.executable, '-I', '-c', 'print("child-ok")'], text=True).strip()
print(json.dumps({'argv':sys.argv[1:], 'nativeExecutable':buf.value.decode(),
    'isolated':sys.flags.isolated, 'bytecode':sys.dont_write_bytecode,
    'child':child, 'path':sys.path, 'prefix':sys.prefix}))
raise SystemExit(23)
''')
            launcher = app/'Contents/MacOS/Augmentor'
            builder.build_launcher(launcher, 'desktop', '14.0')
            linked = subprocess.check_output(['otool', '-L', str(launcher)], text=True)
            self.assertNotIn(str(Path(sys.base_prefix)/'lib'), linked)
            self.assertIn('@rpath/libpython', linked)
            relocated = root/'Moved folder ü'/'Augmentor Agent.app'
            relocated.parent.mkdir()
            app.rename(relocated)
            launcher = relocated/'Contents/MacOS/Augmentor'
            malicious = root/'injected'
            malicious.mkdir()
            (malicious/'sitecustomize.py').write_text('raise RuntimeError("environment injection")')
            args = ['a b', 'quote"', 'dollar$()', '日本語', '-c', 'raise SystemExit(99)']
            result = subprocess.run([str(launcher), *args], cwd='/', text=True, capture_output=True,
                env={**os.environ, 'PYTHONHOME':'/does-not-exist', 'PYTHONPATH':str(malicious)}, timeout=30)
            self.assertEqual(result.returncode, 23, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report['argv'], ['desktop', *args])
            self.assertEqual(Path(report['nativeExecutable']).resolve(), launcher.resolve())
            self.assertEqual(report['isolated'], 1)
            self.assertTrue(report['bytecode'])
            self.assertEqual(report['child'], 'child-ok')
            self.assertNotIn(str(malicious), report['path'])
            self.assertFalse(list(relocated.rglob('*.pyc')))


if __name__ == '__main__':
    unittest.main()
