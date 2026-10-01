# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import json
import os
import subprocess
import unittest
from unittest.mock import patch
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from augmentor_linux import gnome_shortcuts as gnome
from augmentor_linux import shortcuts


class GnomeShortcutTests(unittest.TestCase):
    def test_qt_keys_preserve_super_shift_and_literal_plus_without_text_parsing(self):
        examples=[('Ctrl+Meta+F9',{'symbol':'F9'},['Control','Super']),
                  ('Ctrl+Shift+A',{'character':'a'},['Shift','Control']),
                  ('Ctrl++',{'character':'+'},['Control']),
                  ('Meta+Space',{'character':' '},['Super']),
                  ('Meta+Hangul',{'symbol':'Hangul'},['Super'])]
        for text,key,modifiers in examples:
            with self.subTest(text=text):self.assertEqual(gnome.encode(QKeySequence(text)),{'key':key,'modifiers':modifiers})

    def test_machine_binding_decodes_actual_modifiers_and_key_identity(self):
        for text,symbol,character,modifiers in [('Ctrl+Meta+F9','F9',None,['Control','Super']),
                                               ('Ctrl+Shift+A','a','a',['Shift','Control']),
                                               ('Ctrl++','plus','+',['Control']),
                                               ('Meta+Hangul','Hangul',None,['Super'])]:
            with self.subTest(text=text):
                actual=gnome.decode({'symbol':symbol,'character':character,'modifiers':modifiers})
                self.assertEqual(actual,QKeySequence(text)[0].toCombined())

    def test_unsupported_capture_and_modifier_cannot_be_reported_saved(self):
        for text in ('A','Ctrl+Num+1',''):
            with self.subTest(text=text),self.assertRaises(ValueError):gnome.encode(QKeySequence(text))
        with self.assertRaisesRegex(ValueError,'unsupported modifier'):
            gnome.decode({'symbol':'a','character':'a','modifiers':['Hyper']})

    def test_gnome_routing_keeps_two_rows_and_does_not_register_kde(self):
        with patch.dict(os.environ,{'XDG_CURRENT_DESKTOP':'ubuntu:GNOME'}),\
             patch('augmentor_linux.shortcuts.sys.platform','linux'),\
             patch.object(gnome,'current_keys',return_value=[123]) as read,\
             patch.object(gnome,'save_shortcut',return_value=456) as save,patch.object(shortcuts,'call') as kde:
            self.assertEqual(shortcuts.current_keys('secondary'),[123]);read.assert_called_once_with('secondary')
            sequence=QKeySequence('Ctrl+J');self.assertEqual(shortcuts.save_shortcut(sequence,'main'),456)
            save.assert_called_once_with(sequence,'main');kde.assert_not_called()

    def test_macos_adapter_takes_priority_over_inherited_desktop_environment(self):
        with patch.dict(os.environ,{'XDG_CURRENT_DESKTOP':'GNOME'}),\
             patch('augmentor_linux.shortcuts.sys.platform','darwin'),\
             patch('augmentor_linux.macos_shortcuts.current_keys',return_value=['Fn+Space']) as read,\
             patch.object(gnome,'request') as request:
            self.assertEqual(shortcuts.current_keys('secondary'),['Fn+Space'])
            read.assert_called_once_with('secondary');request.assert_not_called()

    def test_worker_is_bounded_and_never_claims_delivery(self):
        reply={'schema':1,'configured':False,'key':None,'functionalTested':False}
        with patch.object(gnome.subprocess,'run',return_value=subprocess.CompletedProcess([],0,json.dumps(reply),'')) as run:
            self.assertEqual(gnome.current_keys('main'),[])
            self.assertEqual(run.call_args.kwargs['timeout'],5)
            self.assertEqual(json.loads(run.call_args.kwargs['input'])['instance'],'main')
        reply['functionalTested']=True
        with patch.object(gnome.subprocess,'run',return_value=subprocess.CompletedProcess([],0,json.dumps(reply),'')),\
             self.assertRaisesRegex(RuntimeError,'invalid binding status'):
            gnome.current_keys('main')

    def test_conflict_and_malformed_worker_replies_are_explicit(self):
        error={'schema':1,'kind':'invalid','error':'already assigned'}
        with patch.object(gnome.subprocess,'run',return_value=subprocess.CompletedProcess([],1,json.dumps(error),'')),\
             self.assertRaisesRegex(ValueError,'already assigned'):
            gnome.save_shortcut(QKeySequence('Ctrl+J'),'secondary')
        for text in ('null','broken JSON','x'*4097):
            with self.subTest(text=text[:20]),\
                 patch.object(gnome.subprocess,'run',return_value=subprocess.CompletedProcess([],0,text,'')),\
                 self.assertRaisesRegex(RuntimeError,'invalid response'):
                gnome.current_keys('main')
