# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]

def load(path):
    spec=importlib.util.spec_from_file_location('deployment_test_module',ROOT/path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory(prefix='desktop release ')
        self.addCleanup(self.folder.cleanup)
        self.home=Path(self.folder.name)
        self.tool=load('scripts/desktop-deployment.py')
        self.tool.DATA=self.home/'data/augmentor';self.tool.DATA.mkdir(parents=True)
        self.source=self.home/'candidate'
        (self.source/'apps/native/augmentor_linux').mkdir(parents=True)
        (self.source/'apps/native/augmentor_linux/window.py').write_text('--ensure-running')
        (self.source/'release').mkdir();(self.source/'release/product.json').write_text('{"version":"test"}')
        self.selected={'root':str(self.source),'python':'/venv/bin/python','node':'/usr/bin/node','dshService':'dsh-web.service'}
        self.tool.atomic(self.tool.DATA/'desktop.json',self.selected)
        self.check=patch.object(self.tool,'check');self.mock_check=self.check.start();self.addCleanup(self.check.stop)

    def stage(self):return self.tool.stage(self.source,'tested-fixture')

    def test_staging_is_separate_and_preserves_selection(self):
        (self.source/'apps/browser/plugin/dist').mkdir(parents=True)
        (self.source/'apps/browser/plugin/dist/index.js').write_text('browser integration')
        (self.source/'release/dsh').mkdir()
        (self.source/'release/dsh/desktop-capabilities.json').write_text('[]')
        release=self.stage()
        (self.source/'apps/native/augmentor_linux/window.py').write_text('next development edit')
        self.assertEqual(self.tool.verify(release)['deployment']['sourceRef'],'tested-fixture')
        self.assertEqual(self.tool.read(self.tool.DATA/'desktop.json'),self.selected)
        self.assertEqual((release/'apps/native/augmentor_linux/window.py').read_text(),'--ensure-running')
        self.assertTrue((release/'apps/browser/plugin/dist/index.js').is_file())
        self.assertTrue((release/'release/dsh/desktop-capabilities.json').is_file())

    def test_activation_and_rollback_retain_both_selections(self):
        release=self.stage();updated=self.tool.activate(release)
        self.assertEqual(self.tool.read(self.tool.DATA/'desktop.json'),updated)
        self.assertEqual(self.tool.read(self.tool.DATA/'desktop.previous.json'),self.selected)
        self.assertEqual(self.tool.rollback(),self.selected)
        self.assertEqual(self.tool.read(self.tool.DATA/'desktop.previous.json'),updated)
        self.assertTrue(release.exists())

    def test_changed_release_cannot_replace_working_selection(self):
        release=self.stage();(release/'apps/native/augmentor_linux/window.py').write_text('broken')
        with self.assertRaisesRegex(ValueError,'changed after staging'):self.tool.activate(release)
        self.assertEqual(self.tool.read(self.tool.DATA/'desktop.json'),self.selected)

    def test_incompatible_runtime_leaves_previous_selection_untouched(self):
        release=self.stage();self.mock_check.side_effect=RuntimeError('integration mismatch')
        with self.assertRaisesRegex(RuntimeError,'integration mismatch'):self.tool.activate(release)
        self.assertEqual(self.tool.read(self.tool.DATA/'desktop.json'),self.selected)
        self.assertFalse((self.tool.DATA/'desktop.previous.json').exists())

    def test_interrupted_promotion_retains_selected_build(self):
        release=self.stage();replace=self.tool.os.replace
        def interrupted(source,target):
            if Path(target)==self.tool.DATA/'desktop.json':raise OSError('simulated interruption')
            return replace(source,target)
        with patch.object(self.tool.os,'replace',side_effect=interrupted):
            with self.assertRaises(OSError):self.tool.activate(release)
        self.assertEqual(self.tool.read(self.tool.DATA/'desktop.json'),self.selected)
        self.assertEqual(self.tool.read(self.tool.DATA/'desktop.previous.json'),self.selected)

    def test_external_dependency_symlink_is_refused(self):
        (self.source/'services').mkdir();(self.source/'services/mutable').symlink_to(self.home/'external')
        with self.assertRaisesRegex(ValueError,'external symlink'):self.stage()
        self.assertEqual(list((self.tool.DATA/'releases').iterdir()),[])

    def test_internal_links_and_venv_identity_are_preserved(self):
        (self.source/'services').mkdir();(self.source/'services/file').write_text('module')
        (self.source/'services/link').symlink_to('file')
        release=self.stage()
        self.assertEqual(self.tool.verify(release)['deployment']['python'],'/venv/bin/python')
        self.assertEqual((release/'services/link').read_text(),'module')

    def test_failed_import_discards_staging_only(self):
        self.mock_check.side_effect=RuntimeError('missing PySide6')
        with self.assertRaises(RuntimeError):self.stage()
        self.assertEqual(list((self.tool.DATA/'releases').iterdir()),[])
        self.assertEqual(self.tool.read(self.tool.DATA/'desktop.json'),self.selected)

    def test_mobile_follows_registry_and_reports_missing_release(self):
        mobile=load('apps/mobile/start.py')
        with patch.dict(os.environ,{'XDG_DATA_HOME':str(self.home/'data')}):
            self.assertEqual(mobile.desktop_config(),self.selected)
            self.assertEqual(mobile.desktop_config(ROOT)['root'],str(ROOT))
            self.tool.atomic(self.tool.DATA/'desktop.json',dict(self.selected,root=str(self.home/'missing')))
            with self.assertRaisesRegex(RuntimeError,'selected desktop release is missing'):mobile.desktop_config()

    def test_commit_record_cannot_move_without_restaging(self):
        release=self.stage();moved=release.with_name('moved');release.rename(moved)
        with self.assertRaisesRegex(ValueError,'moved after staging'):self.tool.activate(moved)
