# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('native_notices',Path(__file__).resolve().parents[1]/'scripts/collect-native-notices.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class NativeNoticesTest(unittest.TestCase):
    def test_multiple_references_id_fallback_and_missing_file_are_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'source';source.mkdir()
            (source/'LICENSES').mkdir();(source/'LICENSES/MIT.txt').write_text('fixture license')
            (source/'LICENSES/Apache-2.0.txt').write_text('second fixture license')
            (source/'COPYRIGHT').write_text('fixture copyright')
            rows=[{'Id':'one','LicenseFiles':['LICENSES/MIT.txt'],'CopyrightFile':'COPYRIGHT'},
                  {'Id':'two','LicenseId':'MIT'},
                  {'Id':'three','LicenseFile':'missing.txt'},
                  {'Id':'four','LicenseId':'Apache-2.0 AND MIT'}]
            (source/'qt_attribution.json').write_text(json.dumps(rows))
            def git(*args):return subprocess.check_output(['git','-C',str(source),*args],text=True).strip()
            git('init','-q');git('add','.')
            git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','Fixture')
            commit=git('rev-parse','HEAD')
            module.collect(source,commit,root/'out')
            report=json.loads((root/'out/collection.json').read_text())
            self.assertEqual(len(report['records']),4)
            self.assertEqual([x['licenseId'] for x in report['licenseIdResolutions'] if x['record']=='four'],['Apache-2.0','MIT'])
            self.assertEqual(report['unresolved'][0]['record'],'three')
            self.assertEqual(len(report['unresolved']),1)
            self.assertEqual(report['licenseIdResolutions'][0]['record'],'two')
            self.assertTrue((root/'out/COPYRIGHT').is_file())
            self.assertFalse(report['binaryCoverageVerified'])
            (source/'COPYRIGHT').write_text('changed')
            with self.assertRaises(ValueError):module.collect(source,commit,root/'dirty-output')
            self.assertFalse((root/'dirty-output').exists())


if __name__=='__main__':unittest.main()
