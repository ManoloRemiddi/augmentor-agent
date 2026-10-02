# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from PySide6.QtGui import QKeySequence
from augmentor_linux import cinnamon_shortcuts as cinnamon,gnome_shortcuts as gnome,shortcuts

HELPER=Path(__file__).resolve().parents[1]/'services/desktop/cinnamon_shortcuts.py'
spec=importlib.util.spec_from_file_location('cinnamon_shortcut_helper',HELPER)
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)


class CinnamonShortcutTests(unittest.TestCase):
    def test_cinnamon_precedes_inherited_gnome_and_never_falls_through_on_refusal(self):
        with patch.dict(os.environ,{'XDG_CURRENT_DESKTOP':'GNOME:X-Cinnamon'}),patch('sys.platform','linux'),\
                patch.object(cinnamon,'current_keys',return_value=[123]) as read,\
                patch.object(cinnamon,'save_shortcut',side_effect=RuntimeError('locked')) as save,\
                patch.object(gnome,'request') as gnome_request,patch.object(shortcuts,'call') as kde:
            self.assertEqual(shortcuts.current_keys('secondary'),[123]);read.assert_called_once_with('secondary')
            sequence=QKeySequence('Ctrl+Meta+F9')
            with self.assertRaisesRegex(RuntimeError,'locked'):shortcuts.save_shortcut(sequence,'main')
            save.assert_called_once_with(sequence,'main');gnome_request.assert_not_called();kde.assert_not_called()

    def test_mac_priority_over_inherited_cinnamon_environment(self):
        with patch.dict(os.environ,{'XDG_CURRENT_DESKTOP':'X-Cinnamon:GNOME'}),patch('sys.platform','darwin'),\
                patch('augmentor_linux.macos_shortcuts.current_keys',return_value=['Fn+Space']) as read,\
                patch.object(cinnamon,'request') as request:
            self.assertEqual(shortcuts.current_keys('secondary'),['Fn+Space'])
            read.assert_called_once_with('secondary');request.assert_not_called()

    def test_actual_gtk_primary_spelling_decodes_shared_qt_identity(self):
        value={'symbol':'F9','character':None,'modifiers':['Control','Super'],'binding':'<Primary><Super>F9'}
        self.assertEqual(cinnamon.decode(value),QKeySequence('Ctrl+Meta+F9')[0].toCombined())
        for text in ('Ctrl++','Ctrl+Shift+A','Meta+Space','Meta+Hangul'):
            self.assertEqual(cinnamon.encode(QKeySequence(text)),gnome.encode(QKeySequence(text)))

    def test_typed_bounded_worker_cannot_claim_delivery_or_accept_bool_schema(self):
        for reply in ({'schema':True},{'schema':1,'error':{}},
                {'schema':1,'configured':True,'functionalTested':True},None):
            with self.subTest(reply=reply),patch.object(cinnamon.subprocess,'run',return_value=subprocess.CompletedProcess([],0,json.dumps(reply),'')),self.assertRaises(RuntimeError):
                cinnamon.current_keys('main')
        reply={'schema':1,'configured':False,'key':None,'functionalTested':False}
        with patch.object(cinnamon.subprocess,'run',return_value=subprocess.CompletedProcess([],0,json.dumps(reply),'')) as run:
            self.assertEqual(cinnamon.current_keys('secondary'),[])
            self.assertEqual(run.call_args.kwargs['timeout'],25)
            self.assertEqual(Path(run.call_args.args[0][-1]),HELPER)
        for value in ({'symbol':[],'character':'a','modifiers':[]},
                {'symbol':'a','character':'a','modifiers':['Control','Control']},
                {'symbol':'a','character':'a','modifiers':[{}]}):
            with self.subTest(value=value),self.assertRaises(RuntimeError):cinnamon.decode(value)


class OwnershipTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name);self.backend=helper.NativeShortcuts.__new__(helper.NativeShortcuts)
        self.backend.state=self.root/'state/cinnamon.json'
        self.value={'schema':1,'instances':{'main':{'id':'custom0','name':'Synthetic proof','command':'/test','binding':['<Control>F9']}}}

    def test_private_file_symlink_duplicate_ids_and_bool_schema_refuse(self):
        self.backend.persist(self.value);self.assertEqual(self.backend.mapping(),self.value)
        self.backend.state.chmod(0o644)
        with self.assertRaisesRegex(RuntimeError,'privately'):self.backend.mapping()
        self.backend.state.chmod(0o600);target=self.backend.state.with_name('saved.json');self.backend.state.rename(target);self.backend.state.symlink_to(target)
        with self.assertRaises(OSError):self.backend.mapping()
        self.backend.state.unlink();self.backend.state.write_text(json.dumps({'schema':True,'instances':{}}));self.backend.state.chmod(0o600)
        with self.assertRaisesRegex(RuntimeError,'invalid'):self.backend.mapping()
        self.value['instances']['secondary']=self.value['instances']['main'].copy();self.backend.persist(self.value)
        with self.assertRaisesRegex(RuntimeError,'duplicate'):self.backend.mapping()

    def test_precommit_sync_failure_preserves_previous_ownership(self):
        self.backend.persist(self.value);original=self.backend.state.read_bytes()
        with patch.object(helper.os,'fsync',side_effect=OSError('synthetic sync refusal')),self.assertRaises(OSError):
            self.backend.persist({'schema':1,'instances':{}})
        self.assertEqual(self.backend.state.read_bytes(),original)
        self.assertEqual(list(self.backend.state.parent.glob('.cinnamon-*')),[])

    def test_postreplace_sync_failure_keeps_committed_mapping_with_distinct_error(self):
        self.backend.persist(self.value)
        with patch.object(helper.os,'fsync',side_effect=[None,OSError('synthetic directory sync refusal')]),self.assertRaises(helper.OwnershipCommittedError):
            self.backend.persist({'schema':1,'instances':{}})
        self.assertEqual(self.backend.mapping(),{'schema':1,'instances':{}})
        self.assertEqual(self.backend.state.stat().st_mode&0o777,0o600)

    def intent(self):
        after=json.loads(json.dumps(self.value));after['instances']['main']['binding']=['<Control>F12']
        return {'schema':1,'instance':'main','beforeMapping':self.value,'afterMapping':after,
            'beforeUser':{'name':'Synthetic proof','command':'/test','binding':['<Control>F9']},
            'beforeEffective':{'name':'Synthetic proof','command':'/test','binding':['<Control>F9']},'added':False}

    def test_pending_read_refuses_before_any_native_binding_can_be_reported(self):
        intent=self.intent();self.backend.persist(intent,self.backend.pending_path)
        self.assertEqual(self.backend.pending(),intent)
        with self.assertRaisesRegex(RuntimeError,'interrupted'):self.backend.read('main')
        self.backend.pending_path.chmod(0o644)
        with self.assertRaisesRegex(RuntimeError,'privately'):self.backend.pending()

    def test_recovery_intent_cannot_change_unrelated_rows_or_accept_untyped_fields(self):
        intent=self.intent();intent['afterMapping']['instances']['secondary']={**self.value['instances']['main'],'id':'custom1'}
        self.backend.persist(intent,self.backend.pending_path)
        with self.assertRaisesRegex(RuntimeError,'unrelated'):self.backend.pending()
        intent=self.intent();intent['added']=1;self.backend.persist(intent,self.backend.pending_path)
        with self.assertRaisesRegex(RuntimeError,'invalid'):self.backend.pending()
        intent=self.intent();intent['beforeUser']['binding']='invalid';self.backend.persist(intent,self.backend.pending_path)
        with self.assertRaisesRegex(RuntimeError,'fields'):self.backend.pending()


if __name__=='__main__':unittest.main()
