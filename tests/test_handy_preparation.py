# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Supplier archive preparation must not discover the application's parent Git."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('prepare_handy',ROOT/'scripts/prepare-handy.py')
prepare=importlib.util.module_from_spec(spec);spec.loader.exec_module(prepare)


class HandyPreparationTests(unittest.TestCase):
    def test_windows_checkout_preserves_pinned_notice_bytes(self):
        with tempfile.TemporaryDirectory(prefix='augmentor-notice-fixture-') as temporary:
            base=Path(temporary);source=base/'source';source.mkdir()
            subprocess.run(['git','init','--quiet',str(source)],check=True)
            (source/'.gitattributes').write_bytes((ROOT/'.gitattributes').read_bytes())
            notice=Path('components/handy/licenses/Silero-v4.txt')
            (source/notice).parent.mkdir(parents=True)
            (source/notice).write_bytes((ROOT/notice).read_bytes())
            subprocess.run(['git','add','.'],cwd=source,check=True)
            subprocess.run(['git','-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','--quiet','-m','Fixture'],cwd=source,check=True)
            checkout=base/'windows-checkout'
            subprocess.run(['git','-c','core.autocrlf=true','clone','--quiet',str(source),str(checkout)],check=True)
            expected=json.loads((ROOT/'components/handy/silero.json').read_text())['licenseSha256']
            self.assertEqual(hashlib.sha256((checkout/notice).read_bytes()).hexdigest(),expected)

    def test_patch_applies_inside_an_existing_application_checkout(self):
        with tempfile.TemporaryDirectory(prefix='augmentor-supplier-fixture-') as temporary:
            base=Path(temporary);component=base/'components/handy';component.mkdir(parents=True)
            subprocess.run(['git','init','--quiet',str(base)],check=True)
            payload=io.BytesIO()
            with tarfile.open(fileobj=payload,mode='w:gz') as archive:
                for name,content in {'src-tauri/src/lib.rs':'original — fixture\n'.encode('utf-8'),'src/overlay/placeholder':b'fixture\n'}.items():
                    entry=tarfile.TarInfo('Handy-fixture/'+name);entry.size=len(content);archive.addfile(entry,io.BytesIO(content))
            data=payload.getvalue()
            (component/'upstream.json').write_text(json.dumps({'url':'https://supplier.invalid/fixture','commit':'fixture','sha256':hashlib.sha256(data).hexdigest()}))
            (component/'augmentor.patch').write_bytes('diff --git a/src-tauri/src/lib.rs b/src-tauri/src/lib.rs\n--- a/src-tauri/src/lib.rs\n+++ b/src-tauri/src/lib.rs\n@@ -1 +1 @@\n-original — fixture\n+embedded\n'.replace('\n','\r\n').encode('utf-8'))
            (component/'embedding.rs').write_text('owned embedding fixture\n')
            (component/'AugmentorOverlay.tsx').write_text('owned overlay fixture\n')
            target=base/'build/handy'
            configuration=base/'global.gitconfig';configuration.write_text('[core]\n autocrlf = true\n')
            with patch.dict(os.environ,{'GIT_CONFIG_GLOBAL':str(configuration)}),patch.object(prepare,'ROOT',base),patch.object(prepare.urllib.request,'urlopen',return_value=io.BytesIO(data)):
                prepare.prepare(target)
            self.assertEqual((target/'src-tauri/src/lib.rs').read_text(),'embedded\n')
            self.assertEqual((target/'src-tauri/src/embedding.rs').read_text(),'owned embedding fixture\n')
            self.assertEqual((target/'src/overlay/AugmentorOverlay.tsx').read_text(),'owned overlay fixture\n')
            self.assertEqual(Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],cwd=target,text=True).strip()),target)


if __name__=='__main__':unittest.main()
