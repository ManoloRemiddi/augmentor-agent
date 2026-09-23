# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from augmentor_linux.instances import scoped_path, ipc_basename, validate_name
from augmentor_linux.controller import Controller
from augmentor_linux.preferences import Preferences


class InstanceTests(unittest.TestCase):
    def test_primary_paths_and_invalid_names(self):
        with patch.dict(os.environ, {'AUGMENTOR_WINDOW_ID':'main'}):
            self.assertEqual(scoped_path(Path('/tmp/session.json')), Path('/tmp/session.json'))
            self.assertEqual(ipc_basename(), 'augmentor-linux-pi')
        for name in ['../other', '', 'a/b', 'UPPER', 'x'*33]:
            with self.assertRaises(ValueError):validate_name(name)

    def test_named_controller_inherits_model_but_not_conversation_and_restores_own_chat(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'AUGMENTOR_PI_STATE':directory,'AUGMENTOR_WINDOW_ID':'main'}):
            first=Controller();first.session='primary-chat';first.selection={'provider':'local','model':'selected'};first.save_session()
            original=first.state_file.read_bytes()
            with patch.dict(os.environ, {'AUGMENTOR_WINDOW_ID':'secondary'}):
                second=Controller()
                self.assertIsNone(second.session);self.assertEqual(second.selection,first.selection)
                self.assertNotEqual(first.state_file,second.state_file)
                second.session='second-chat';second.save_session()
                restored=Controller();self.assertEqual(restored.session,'second-chat')
                self.assertEqual(ipc_basename(),'augmentor-linux-pi-secondary')
                self.assertEqual(second.state_file.stat().st_mode&0o777,0o600)
            self.assertEqual(first.state_file.read_bytes(),original)
            for controller in [first,second,restored]:controller.queue_executor.shutdown(wait=False)

    def test_named_appearance_clones_once_and_restores_own_settings(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'AUGMENTOR_PI_CONFIG':directory,'AUGMENTOR_WINDOW_ID':'main'}):
            primary=Preferences();primary.values.update(hue=123,voice_mode='hands-free',placement={'x':200});primary.save()
            original=primary.path.read_bytes()
            with patch.dict(os.environ, {'AUGMENTOR_WINDOW_ID':'secondary'}):
                secondary=Preferences();self.assertEqual(secondary.values['hue'],123)
                self.assertEqual(secondary.values['voice_mode'],'hands-free');self.assertEqual(secondary.values['placement'],{})
                self.assertTrue(secondary.path.exists(),'First clone must persist immediately')
                primary.values['hue']=17;primary.save()
                self.assertEqual(Preferences().values['hue'],123,'Later primary edits must not change the clone')
                primary.path.write_bytes(original)
                secondary.values.update(hue=42,accent_hue=312,skin_name='My second skin',voice_mode='manual',voice_pause_ms=1200);secondary.save()
                restored=Preferences()
                for key in ('hue','accent_hue','skin_name','voice_mode','voice_pause_ms'):self.assertEqual(restored.values[key],secondary.values[key])
            self.assertEqual(primary.path.read_bytes(),original)

if __name__=='__main__':unittest.main()
