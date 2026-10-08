# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch,Mock
from contextlib import contextmanager
from PySide6.QtWidgets import QApplication,QWidget
from PySide6.QtGui import QColor,QKeySequence
from augmentor_linux import agent_entries as store
from augmentor_linux.adapters.dsh import DshAdapter
from augmentor_linux.adapters.dsh_wire import DshClient
from augmentor_linux.agents_settings import AgentsSettings

class EntriesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.env=patch.dict(os.environ,{'AUGMENTOR_AGENT_ENTRIES':self.tmp.name+'/agents.json','AUGMENTOR_WINDOW_ID':'main'});self.env.start()
    def tearDown(self):self.env.stop();self.tmp.cleanup()
    def create(self,identity='research'):
        entry={'id':identity,'name':'Research','preset':'synthetic-research','cwd':self.tmp.name,'model':{'provider':'local','model':'fixture'}}
        return store.save(entry,store.read()['revision'])
    def test_migration_preserves_existing_files_and_default_bindings(self):
        original=Path(self.tmp.name)/'session.secondary.json';original.write_text('original')
        self.assertEqual([e['id'] for e in store.entries()],['main','secondary']);self.assertIsNone(store.get()['stateKey']);self.create()
        self.assertEqual(original.read_text(),'original');self.assertIsNone(store.get('secondary')['stateKey'])
    def test_rename_model_and_agent_changes_have_distinct_state_semantics(self):
        value=self.create();entry=store.get('research');key=entry['stateKey']
        value=store.save({**entry,'name':'New name','model':{'provider':'remote','model':'other'}},value['revision']);self.assertEqual(store.get('research')['stateKey'],key)
        value=store.save({**store.get('research'),'preset':'another-agent'},value['revision']);self.assertNotEqual(store.get('research')['stateKey'],key);self.assertEqual(value['retained'][0]['preset'],'synthetic-research')
        with self.assertRaisesRegex(ValueError,'another window'):store.save(entry,0)
    def test_removal_retains_binding_and_failed_shortcut_removal_preserves_entry(self):
        self.create();before=store.read()
        with self.assertRaises(RuntimeError):store.remove('research',before['revision'],Mock(side_effect=RuntimeError('OS failure')))
        self.assertEqual(store.read(),before)
        clear=Mock();value=store.remove('research',before['revision'],clear);clear.assert_called_once_with('research')
        self.assertEqual(value['retained'][-1]['preset'],'synthetic-research')
        with self.assertRaisesRegex(ValueError,'removed'):store.get('research')
    def test_custom_adapter_never_owns_another_folder_or_role(self):
        self.create()
        with patch.dict(os.environ,{'AUGMENTOR_WINDOW_ID':'research'}):
            adapter=DshAdapter(base='http://127.0.0.1:3080',home=self.tmp.name)
            self.assertEqual(adapter.preset,'synthetic-research');self.assertFalse(adapter.supports_voice)
            self.assertTrue(adapter.owns_session({'agentPreset':adapter.preset,'cwd':self.tmp.name}))
            self.assertFalse(adapter.owns_session({'agentPreset':adapter.preset,'cwd':'/elsewhere'}));self.assertFalse(adapter.owns_preset('augmentor-linux-product'))
            self.assertIn(store.get()['stateKey'],str(adapter.state_path()))
            for catalog in [[],[{'id':adapter.preset,'broken':'Missing service'}]]:
                with patch.object(DshClient,'call',return_value={'presets':catalog}):
                    with self.assertRaisesRegex(Exception,'unavailable'):adapter.check_preset()
            store.save({**store.get(),'preset':'changed'},store.read()['revision'])
            with self.assertRaisesRegex(Exception,'changed'):adapter.check_entry()
    def test_form_discovers_agents_and_shortcut_conflict_does_not_save_entry(self):
        class Owner(QWidget):
            accent=QColor('#50c8a0')
            def call_in_background(self,work,callback):callback(work())
            def open_appearance(self):pass
        with patch('augmentor_linux.agents_settings.current_keys',return_value=[]),patch.object(DshClient,'call',return_value={'presets':[{'id':'independent','name':'Independent','broken':False}]}),patch.object(DshClient,'model_catalog',return_value={'groups':[]}):
            owner=Owner();widget=AgentsSettings(owner);widget.add_entry();widget.name.setText('Independent');widget.agent.setCurrentIndex(widget.agent.findData('independent'));widget.shortcut.setKeySequence(QKeySequence('Ctrl+Alt+O'))
            before=store.read()
            with patch('augmentor_linux.agents_settings.shortcut_transaction',side_effect=ValueError('Already assigned')):widget.save_entry()
            self.assertEqual(store.read(),before);self.assertIn('Already assigned',widget.note.text());owner.close()
    def test_stale_revision_never_mutates_shortcut_and_failed_commit_rolls_back(self):
        value=self.create();entry=store.get('research');transaction=Mock()
        with self.assertRaisesRegex(ValueError,'another window'):store.save(entry,0,transaction)
        transaction.assert_not_called()
        actions=[]
        @contextmanager
        def change():
            actions.append('apply')
            try:yield
            except Exception:actions.append('restore');raise
        with patch.object(store,'atomic',side_effect=OSError('Disk failure')):
            with self.assertRaises(OSError):store.save({**entry,'name':'Renamed'},value['revision'],change)
        self.assertEqual(actions,['apply','restore']);self.assertEqual(store.read(),value)
    def test_linux_open_uses_the_registered_managed_launcher(self):
        self.create()
        launcher=Path(self.tmp.name)/'.local/bin/augmentor-agent';launcher.parent.mkdir(parents=True);launcher.touch()
        with patch('augmentor_linux.agent_entries.Path.home',return_value=Path(self.tmp.name)),patch('sys.platform','linux'),patch('subprocess.Popen') as launch:
            store.launch('research')
            self.assertEqual(launch.call_args.args[0],[str(launcher),'--instance','research'])
        # The startup installer and this action must agree on the public entrypoint.
        script=(Path(__file__).resolve().parents[1]/'scripts/install-desktop-startup.py').read_text()
        self.assertIn("binary/'augmentor-agent'",script)
