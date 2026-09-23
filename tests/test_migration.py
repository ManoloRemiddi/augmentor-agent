# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import json
import tempfile
from pathlib import Path
import unittest
from augmentor_linux.migration import migrate

class MigrationTests(unittest.TestCase):
    def test_import_preserves_source_and_existing_prompts_and_omits_credentials(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);config=root/'pi';source=root/'legacy.yaml';appearance=root/'appearance.json'
            raw='model-picker-augmented:\n  pinned: [mx-qwen/model]\nprompt-library:\n  prompts:\n    - name: summary\n      content: Summarise the task.\ncredentials:\n  secret: do-not-copy\n'
            source.write_text(raw);appearance.write_text('{"theme":"light","hue":40}')
            first=migrate(config,appearance,source);self.assertEqual(first['prompts'],1)
            (config/'agent/prompts/summary.md').write_text('Edited in Pi')
            second=migrate(config,appearance,source);self.assertEqual(second['prompts'],0)
            self.assertEqual((config/'agent/prompts/summary.md').read_text(),'Edited in Pi')
            self.assertEqual(source.read_text(),raw)
            self.assertNotIn('do-not-copy',(config/'settings.json').read_text())
            self.assertEqual(json.loads((config/'settings.json').read_text())['pinned'],['mx-qwen/model'])
            self.assertEqual((config/'appearance.json').stat().st_mode&0o777,0o600)
