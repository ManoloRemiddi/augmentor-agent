# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import importlib.util,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from augmentor_linux.preferences import Preferences
spec=importlib.util.spec_from_file_location('surface',Path(__file__).resolve().parents[1]/'services/surface/browser.py');surface=importlib.util.module_from_spec(spec);spec.loader.exec_module(surface)
class SurfacePreferences(unittest.TestCase):
    def test_shared_colours_preserve_model_voice_and_placement(self):
        with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,{'AUGMENTOR_PI_CONFIG':temp,'AUGMENTOR_WINDOW_ID':'main'}):
            prefs=Preferences();prefs.values.update(harness='pi',voice_pause_ms=1100,placement={'sentinel':True});prefs.save()
            before=surface.appearance();values={**before['values'],'theme':'light','accentHue':32,'neutBright':-3}
            after=surface.appearance(values);self.assertEqual(after['values']['accentHue'],32);self.assertEqual(after['tokens']['--text'],'#152b2c')
            loaded=Preferences().values;self.assertEqual(loaded['harness'],'pi');self.assertEqual(loaded['voice_pause_ms'],1100);self.assertEqual(loaded['placement'],{'sentinel':True})
            with self.assertRaises(ValueError):surface.appearance({**values,'neutBright':999})
            self.assertEqual(Preferences().values,loaded)
    def test_improvement_uses_native_adapter_and_shared_template_without_submission(self):
        with patch('augmentor_linux.adapters.dsh.DshAdapter') as adapter,patch('augmentor_linux.prompt_client.PromptClient') as prompts:
            prompts.return_value.call.return_value={'improvement':{'content':'Shared template'}}
            adapter.return_value.improve_prompt.return_value={'kind':'rewrite','text':'Better'}
            self.assertEqual(surface.request({'action':'improve','text':'Draft','selection':{'provider':'fixture','model':'model'}})['text'],'Better')
            adapter.return_value.improve_prompt.assert_called_once_with('Draft','Shared template',{'provider':'fixture','model':'model'})
            adapter.return_value.call.assert_not_called()
