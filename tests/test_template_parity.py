# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import json,unittest
from pathlib import Path
from augmentor_linux.templates import expand_template
class TemplateParity(unittest.TestCase):
    def test_common_fixtures(self):
        for row in json.loads((Path(__file__).parent/'parity/clipboard.json').read_text()):
            with self.subTest(row=row):
                if row.get('error'):
                    with self.assertRaises(ValueError):expand_template(row['template'],row['snapshot'])
                else:self.assertEqual(expand_template(row['template'],row['snapshot']),row['expected'])
