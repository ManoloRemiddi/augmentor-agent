# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Permission identity and resource lookups survive the Mac helper's relocation."""
import importlib.util
import json
from pathlib import Path
import plistlib
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('package_macos',ROOT/'scripts/package-macos.py')
packager=importlib.util.module_from_spec(spec);spec.loader.exec_module(packager)


class DictationBundleTests(unittest.TestCase):
    def test_hidden_permission_identity_retains_native_relative_resources_and_notices(self):
        with tempfile.TemporaryDirectory(prefix='augmentor-mac-helper-') as temporary:
            project=Path(temporary);runtime=project/'components/handy/runtime'
            values={'bin/handy':b'owned executable fixture','bin/libtranscribe.dylib':b'transcription fixture',
                    'Resources/resources/models/silero.onnx':b'vad fixture','lib/Handy/libonnxruntime.dylib':b'ort fixture',
                    'notices/Handy-MIT.txt':b'original notice fixture'}
            for name,data in values.items():
                path=runtime/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
            (runtime/'bin/handy').chmod(0o755)
            receipt={'upstream':{'version':'0.9.7'},'files':list(values)}
            (runtime/'BUILD.json').write_text(json.dumps(receipt))
            bundle=packager.bundle_dictation(project,'13.0');contents=bundle/'Contents'
            identity=plistlib.loads((contents/'Info.plist').read_bytes())
            self.assertEqual(identity['CFBundleIdentifier'],'com.augmentor.agent.dictation')
            self.assertTrue(identity['LSUIElement']);self.assertTrue(identity['NSMicrophoneUsageDescription'])
            executable=contents/'MacOS'/identity['CFBundleExecutable']
            self.assertEqual(executable.read_bytes(),values['bin/handy'])
            self.assertTrue(executable.stat().st_mode&0o111)
            self.assertEqual((executable.parent/'../Resources/resources/models/silero.onnx').read_bytes(),values['Resources/resources/models/silero.onnx'])
            self.assertEqual((executable.parent/'../lib/Handy/libonnxruntime.dylib').read_bytes(),values['lib/Handy/libonnxruntime.dylib'])
            self.assertEqual((executable.parent/'libtranscribe.dylib').read_bytes(),values['bin/libtranscribe.dylib'])
            self.assertEqual((runtime/'notices/Handy-MIT.txt').read_bytes(),values['notices/Handy-MIT.txt'])
            self.assertEqual(json.loads((runtime/'BUILD.json').read_text()),receipt)
            self.assertIn('exec ',(runtime/'bin/handy').read_text())


if __name__=='__main__':unittest.main()
