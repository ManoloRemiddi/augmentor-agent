# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import importlib.util
import json
import os
from pathlib import Path
import shutil
import runpy
import sys
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT/path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


recipient = load('recipient_tests','scripts/linux-recipient-runtime.py')
qt = load('recipient_qt','scripts/linux-source-qt.py')
official = load('recipient_python','scripts/linux-python-runtime.py')
component = load('recipient_component','scripts/run-component.py')
desktop = load('recipient_desktop','scripts/desktop-launch.py')


class RecipientTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(); self.addCleanup(folder.cleanup)
        self.home = Path(folder.name); self.app = self.home/'app'; self.app.mkdir()
        self.value = {'profile':'noble-cp312-x86_64-source-qt-voice','pythonAbi':[3,12],
                      'python':sys.executable,'sourceQt':{'qtVersion':'6.8.2'}}
        for name, value in [('release.json',{'source':'synthetic','version':'0.2.13'}),
                            ('linux-python-runtime.json',self.value)]:
            (self.app/name).write_text(json.dumps(value)); (self.app/name).chmod(0o644)
        self.base = self.home/'official'; self.base.mkdir(mode=0o700)
        for name, raw in [('pyvenv.cfg',b'official config'),('wheel-lock.txt',b'official wheels'),
                          ('qt/lib/libQt6Core.so.6.8.2',b'official core'),('qt/stage-inventory.json',b'official manifest'),
                          ('lib/python3.12/site-packages/PySide6/QtCore.abi3.so',b'official binding'),
                          ('lib/python3.12/site-packages/keyring/__init__.py',b'unchanged nonQt')]:
            path = self.base/name; path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(raw); path.chmod(0o644)
        (self.base/'bin').mkdir(); (self.base/'bin/python3').symlink_to(sys.executable)
        for path in self.base.rglob('*'):
            if path.is_dir(): path.chmod(0o755)
        files = recipient.inventory(self.base)
        (self.base/'augmentor-python-runtime.json').write_text(json.dumps({'files':files}))
        (self.base/'augmentor-python-runtime.json').chmod(0o600)
        self.root = self.home/'modified'; shutil.copytree(self.base,self.root,symlinks=True); self.root.chmod(0o700)
        (self.root/'qt/lib/libQt6Core.so.6.8.2').write_bytes(b'explicit modified core')
        self.runtime = SimpleNamespace(SOURCE_PROFILES={self.value['profile']}, RECEIPT='augmentor-python-runtime.json',
            POLICY_FILE='linux-python-runtime.json', policy=lambda p:self.value, identity=lambda v:'official-identity',
            resolve_official=lambda app,python:str(self.base/'bin/python3'),source_qt=lambda:qt)
        self.abi = {'pythonAbi':[3,12],'qtVersion':'6.8.2','pysideVersion':'6.8.2.1','shibokenVersion':'6.8.2.1'}
        self.env = {'HOME':str(self.home),'XDG_DATA_HOME':str(self.home/'data'),'DISPLAY':':fixture'}
        self.addCleanup(patch.stopall)
        patch.object(recipient,'load_runtime',return_value=self.runtime).start()
        self.probe = patch.object(recipient,'abi_probe',return_value=self.abi).start()

    def choose(self):
        return recipient.select(self.app,str(self.base/'bin/python3'),self.root,self.env)

    def test_explicit_fresh_selection_returns_executable_and_environment_without_changing_official_receipt(self):
        before = (self.base/'augmentor-python-runtime.json').read_bytes()
        self.choose()
        chosen, env = recipient.launch(self.app,str(self.base/'bin/python3'),self.env,self.runtime)
        self.assertEqual(chosen,str(self.root/'bin/python3'))
        self.assertEqual(env['AUGMENTOR_PYTHON'],chosen)
        self.assertEqual(env['LD_LIBRARY_PATH'],str(self.root/'qt/lib'))
        self.assertEqual(env['DISPLAY'],':fixture')
        self.assertEqual((self.base/'augmentor-python-runtime.json').read_bytes(),before)
        self.assertNotEqual(recipient.read_json(self.root/recipient.RECEIPT)[0]['files'],
                            json.loads(before)['files'])

    def test_wrong_abi_never_selects_runtime(self):
        self.probe.return_value = {**self.abi,'pythonAbi':[3,13]}
        with self.assertRaisesRegex(ValueError,'ABI'): self.choose()
        self.assertFalse(recipient.selection_path(self.app,self.env).exists())
        self.assertFalse((self.root/recipient.RECEIPT).exists())

    def test_nonQt_change_refuses_before_recipient_execution(self):
        (self.root/'lib/python3.12/site-packages/keyring/__init__.py').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'non-Qt'): self.choose()
        self.probe.assert_not_called()

    def test_added_files_and_changed_interpreter_links_refuse_before_execution(self):
        (self.root/'extra.so').write_bytes(b'extra')
        (self.root/'extra.so').chmod(0o644)
        with self.assertRaisesRegex(ValueError,'file/link set'): self.choose()
        (self.root/'extra.so').unlink()
        (self.root/'bin/python3').unlink(); (self.root/'bin/python3').symlink_to('/foreign/python')
        with self.assertRaisesRegex(ValueError,'non-Qt/binding file or link'): self.choose()
        self.probe.assert_not_called()

    def test_modified_selected_bytes_refuse_before_probe(self):
        self.choose(); self.probe.reset_mock()
        (self.root/'qt/lib/libQt6Core.so.6.8.2').write_bytes(b'changed after select')
        with self.assertRaisesRegex(ValueError,'stale or its runtime changed'):
            recipient.launch(self.app,None,self.env,self.runtime)
        self.probe.assert_not_called()

    def test_changed_receipt_and_malformed_receipt_refuse_before_probe(self):
        self.choose(); self.probe.reset_mock()
        path = self.root/recipient.RECEIPT; path.write_text('{}')
        with self.assertRaisesRegex(ValueError,'receipt changed'): recipient.launch(self.app,None,self.env,self.runtime)
        selection_path = recipient.selection_path(self.app,self.env)
        value,_ = recipient.read_json(selection_path); value['receiptSha256'] = recipient.sha(path.read_bytes())
        selection_path.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'stale or its runtime changed'): recipient.launch(self.app,None,self.env,self.runtime)
        self.probe.assert_not_called()

    def test_official_receipt_and_app_identity_changes_cannot_be_silently_adopted(self):
        self.choose(); self.probe.reset_mock()
        path = self.base/'augmentor-python-runtime.json'
        original = path.read_bytes(); path.write_bytes(original+b'\n')
        with self.assertRaisesRegex(ValueError,'stale or its runtime changed'): recipient.launch(self.app,None,self.env,self.runtime)
        path.write_bytes(original)
        (self.app/'release.json').write_text('{"source":"new app"}')
        with self.assertRaisesRegex(ValueError,'stale or different application'): recipient.launch(self.app,None,self.env,self.runtime)
        self.probe.assert_not_called()

    def test_removed_policy_cannot_silently_fall_back_from_an_explicit_choice(self):
        self.choose();self.probe.reset_mock()
        (self.app/'linux-python-runtime.json').unlink()
        with self.assertRaises(FileNotFoundError): recipient.launch(self.app,None,self.env,self.runtime)
        self.probe.assert_not_called()

    def test_selection_replacement_during_probe_is_terminal(self):
        self.choose()
        def change(*args):
            path = recipient.selection_path(self.app,self.env); path.write_bytes(path.read_bytes()+b'\n')
            return self.abi
        self.probe.side_effect = change
        with self.assertRaisesRegex(ValueError,'changed during validation'): recipient.launch(self.app,None,self.env,self.runtime)

    def test_symlink_receipt_or_nonprivate_selection_parent_refuses(self):
        self.choose()
        path = self.root/recipient.RECEIPT; raw = path.read_bytes(); path.unlink()
        other = self.home/'other'; other.write_bytes(raw); path.symlink_to(other)
        with self.assertRaises(OSError): recipient.launch(self.app,None,self.env,self.runtime)
        recipient.selection_path(self.app,self.env).parent.chmod(0o755)
        with self.assertRaisesRegex(ValueError,'private'): recipient.launch(self.app,None,self.env,self.runtime)

    def test_existing_selection_refuses_before_probe_or_rewrite(self):
        self.choose(); self.probe.reset_mock()
        path = recipient.selection_path(self.app,self.env); before = path.read_bytes()
        with self.assertRaisesRegex(ValueError,'Clear'): self.choose()
        self.assertEqual(path.read_bytes(),before); self.probe.assert_not_called()

    def test_loader_override_refuses_before_recipient_probe(self):
        self.choose(); self.probe.reset_mock()
        with self.assertRaisesRegex(ValueError,'preload/audit'):
            recipient.launch(self.app,None,{**self.env,'LD_PRELOAD':'/foreign.so'},self.runtime)
        self.probe.assert_not_called()

    def test_unbound_executable_bytecode_is_not_ignored(self):
        path=self.root/'lib/python3.12/site-packages/keyring/__pycache__';path.mkdir()
        (path/'unbound.pyc').write_bytes(b'unbound executable cache')
        with self.assertRaisesRegex(ValueError,'bytecode caches'): self.choose()
        self.probe.assert_not_called()

    def test_default_official_resolve_stays_strict_and_no_selection_has_no_recipient_import(self):
        with (patch.object(official,'resolve_official',return_value='/official/python') as resolve,
                patch.dict(os.environ,self.env,clear=True)):
            self.assertEqual(official.resolve(self.app),'/official/python')
        resolve.assert_called_once()

    def test_component_replaces_verified_official_python_argument_with_recipient(self):
        env={'AUGMENTOR_OFFICIAL_PYTHON':'/official/python','AUGMENTOR_PYTHON':'/recipient/python'}
        with patch.object(component,'hold'),patch.object(component,'component_environment',return_value=env),patch.object(component.os,'execvpe') as execute:
            component.main(['desktop','/official/python','-m','augmentor_linux'])
        execute.assert_called_once_with('/recipient/python',['/recipient/python','-m','augmentor_linux'],env)

    def test_real_shell_uses_combined_preexec_and_does_not_publish_fallback_system_python(self):
        scripts=self.app/'scripts';scripts.mkdir()
        shutil.copy2(ROOT/'scripts/augmentor-linux',scripts/'augmentor-linux')
        (scripts/'linux-python-runtime.py').write_text('import json,os,sys\nprint(json.dumps({"args":sys.argv[1:],"python":os.environ.get("AUGMENTOR_PYTHON")}))\n')
        result=subprocess.run(['/bin/bash',str(scripts/'augmentor-linux'),'--instance=second'],env={**self.env,'PATH':'/usr/bin:/bin'},text=True,capture_output=True,check=True,timeout=10)
        observed=json.loads(result.stdout)
        self.assertIsNone(observed['python'])
        self.assertEqual(observed['args'],['exec','--app-root',str(self.app),'--exec-args','-m','augmentor_linux','--instance=second'])

    def test_preexec_cli_executes_exact_pair_returned_by_launch(self):
        class Executed(Exception): pass
        with (patch.object(sys,'argv',['linux-python-runtime.py','exec','--app-root',str(self.app),'--exec-args','-m','augmentor_linux']),
                patch.object(official,'launch',return_value=('/recipient/python',{'QT_PLUGIN_PATH':'/recipient/plugins'})),
                patch.object(official.os,'execve',side_effect=Executed) as execute):
            with self.assertRaises(Executed): official.main()
        execute.assert_called_once_with('/recipient/python',['/recipient/python','-m','augmentor_linux'],{'QT_PLUGIN_PATH':'/recipient/plugins'})

    def test_desktop_executes_returned_python_not_saved_base(self):
        window = self.app/'apps/native/augmentor_linux/window.py'; window.parent.mkdir(parents=True); window.touch()
        module = SimpleNamespace(launch=lambda *args:('/recipient/python',{'AUGMENTOR_PYTHON':'/recipient/python'}))
        config={'root':str(self.app),'python':'/official/python','node':'/node'}
        with patch.object(desktop,'configuration',return_value=config),patch.object(desktop.importlib.util,'module_from_spec',return_value=module),patch.object(desktop.importlib.util,'spec_from_file_location',return_value=SimpleNamespace(loader=SimpleNamespace(exec_module=lambda m:None))),patch.object(desktop.os,'execve') as execute:
            desktop.main(['--instance=second'])
        self.assertEqual(execute.call_args.args[:2],('/recipient/python',['/recipient/python','-m','augmentor_linux','--instance=second']))

    def test_embedded_browser_validates_and_passes_recipient_environment_before_node(self):
        entry=self.app/'apps/browser/embed/server.mjs';entry.parent.mkdir(parents=True);entry.touch()
        data=self.home/'data/augmentor';data.mkdir(parents=True)
        (data/'desktop.json').write_text(json.dumps({'root':str(self.app),'python':'/official/python','node':'/node'}))
        env={'AUGMENTOR_PYTHON':'/recipient/python','LD_LIBRARY_PATH':'/recipient/qt/lib'}
        launch=SimpleNamespace(launch=lambda *args:('/recipient/python',env))
        with (patch.dict(os.environ,self.env,clear=True),
                patch.object(importlib.util,'module_from_spec',return_value=launch),
                patch.object(importlib.util,'spec_from_file_location',return_value=SimpleNamespace(loader=SimpleNamespace(exec_module=lambda m:None))),
                patch.object(os,'execve') as execute):
            runpy.run_path(str(ROOT/'scripts/embed-launch.py'),run_name='__main__')
        execute.assert_called_once_with('/node',['/node',str(entry)],env)


if __name__ == '__main__': unittest.main()
