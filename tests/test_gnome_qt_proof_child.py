# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Qt proof children receive verified source paths without weakening entry guards."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

ROOT=Path(__file__).resolve().parents[1]


def load(path):
    spec=importlib.util.spec_from_file_location(path.stem.replace('-','_'),path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


proof=load(ROOT/'release/noble-gnome-shortcut-session.py')
runtime=load(ROOT/'scripts/linux-python-runtime.py')
source_qt=load(ROOT/'scripts/linux-source-qt.py')


class QtProofChild(unittest.TestCase):
    def helper(self,folder):
        helper=folder/'owned-helper.py'
        helper.write_text('''import ctypes,os
def qt_save():
    return {'value':ctypes.CDLL('libaugmentor_gnome_fixture.so').fixture(),
            'python':os.environ['AUGMENTOR_PYTHON'],'root':str(ROOT)}
def app_settings_save():
    return {'operation':'actual-settings','root':str(ROOT),
            'loader':os.environ.get('LD_LIBRARY_PATH')}
''')
        return helper

    @unittest.skipUnless(sys.platform.startswith('linux') and shutil.which('cc'),'ELF compiler/loader required')
    def test_verified_preexec_paths_reach_real_loader_without_mutating_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);app=folder/'app';app.mkdir()
            native=folder/'runtime';library=native/'qt/lib/libaugmentor_gnome_fixture.so';library.parent.mkdir(parents=True)
            subprocess.run([shutil.which('cc'),'-shared','-fPIC','-x','c','-','-o',str(library)],
                           input='int fixture(void) { return 91; }',text=True,check=True,capture_output=True)
            helper=self.helper(folder);python=sys.executable
            provider=SimpleNamespace(environment=lambda root,chosen,env:source_qt.environment(native,{**env,'AUGMENTOR_PYTHON':chosen}))
            spec=SimpleNamespace(loader=SimpleNamespace(exec_module=Mock()))
            base={'PATH':os.defpath,'HOME':directory,'QT_QPA_PLATFORM':'offscreen','QT_QPA_PLATFORMTHEME':'foreign'}
            with patch.dict(os.environ,base,clear=True),patch.object(proof,'__file__',str(helper)):
                with self.assertRaises(RuntimeError):proof.qt_operation(app,python,'qt-save')
                (app/'linux-python-runtime.json').write_text('{}')
                with patch.object(proof.importlib.util,'spec_from_file_location',return_value=spec),patch.object(proof.importlib.util,'module_from_spec',return_value=provider):
                    result=proof.qt_operation(app,python,'qt-save')
                self.assertEqual(result,{'value':91,'python':python,'root':str(app)})
                self.assertEqual(dict(os.environ),base)

    def test_native_child_retains_default_environment_and_bounded_operation(self):
        with tempfile.TemporaryDirectory() as directory:
            app=Path(directory);helper=self.helper(app)
            with patch.object(proof,'__file__',str(helper)),patch.dict(os.environ,{'PATH':os.defpath},clear=True),patch.object(proof.importlib.util,'spec_from_file_location') as loader:
                result=proof.qt_operation(app,sys.executable,'app-settings-save')
                self.assertEqual(result,{'operation':'actual-settings','root':str(app),'loader':None})
                loader.assert_not_called()

    def test_runtime_refusal_precedes_child_and_preserves_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            app=Path(directory);(app/'linux-python-runtime.json').write_text('{}')
            provider=SimpleNamespace(environment=Mock(side_effect=ValueError('selected inventory changed')))
            spec=SimpleNamespace(loader=SimpleNamespace(exec_module=Mock()));before=dict(os.environ)
            with patch.object(proof.importlib.util,'spec_from_file_location',return_value=spec),patch.object(proof.importlib.util,'module_from_spec',return_value=provider),patch.object(proof.subprocess,'run') as child:
                with self.assertRaisesRegex(ValueError,'inventory changed'):proof.qt_operation(app,sys.executable,'qt-save')
                child.assert_not_called();self.assertEqual(dict(os.environ),before)

    def test_dangling_policy_refuses_without_legacy_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            app=Path(directory);(app/'scripts').mkdir()
            shutil.copy2(ROOT/'scripts/linux-python-runtime.py',app/'scripts/linux-python-runtime.py')
            (app/'linux-python-runtime.json').symlink_to(app/'missing.json')
            with patch.object(proof.subprocess,'run') as child:
                with self.assertRaisesRegex(ValueError,'regular artifact file'):proof.qt_operation(app,sys.executable,'qt-save')
                child.assert_not_called()

    def test_unsupported_operation_refuses_before_child(self):
        with patch.object(proof.subprocess,'run') as child:
            with self.assertRaisesRegex(ValueError,'bounded Qt'):proof.qt_operation(ROOT,sys.executable,'arbitrary')
            child.assert_not_called()

    def test_failed_and_uncertain_children_are_never_retried(self):
        with tempfile.TemporaryDirectory() as directory:
            app=Path(directory)
            for failure in (subprocess.CompletedProcess([],1,'','worker refused'),subprocess.TimeoutExpired([],120)):
                with self.subTest(failure=type(failure).__name__),patch.object(proof.subprocess,'run',return_value=failure if not isinstance(failure,Exception) else None,side_effect=failure if isinstance(failure,Exception) else None) as child:
                    with self.assertRaises((RuntimeError,subprocess.TimeoutExpired)):proof.qt_operation(app,sys.executable,'app-settings-save')
                    child.assert_called_once()
                    self.assertEqual(child.call_args.kwargs['timeout'],120)


if __name__=='__main__':unittest.main()
