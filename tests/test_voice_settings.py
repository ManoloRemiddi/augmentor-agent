# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication,QPushButton
from augmentor_linux.window import Window
from augmentor_linux.voice_settings import VoiceSettingsDialog


class VoiceSettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_voice_selection_speed_and_volume_are_saved_together(self):
        calls=[]
        data={'voices':[{'id':f'resonant-{i}','name':f'Voice {i}','description':'Natural female voice'} for i in range(10)],'values':{'voiceId':'resonant-0','speed':1,'volume':1}}
        def request(path,values=None,raw=False):
            calls.append((path,values))
            if values:data['values']=values['values']
            return data
        with patch('augmentor_linux.voice_settings.voice_request',request),patch.object(VoiceSettingsDialog,'work',lambda self,work,callback:callback((work(),None))):
            window=Window(preview=True);dialog=VoiceSettingsDialog(window)
            self.assertEqual(dialog.voice.count(),10)
            dialog.voice.setCurrentIndex(3);dialog.speed.setValue(120);dialog.volume.setValue(65);dialog.save()
            self.assertEqual(calls[-1],('preferences',{'values':{'voiceId':'resonant-3','speed':1.2,'volume':.65}}))
            self.assertTrue(all(not b.icon().isNull() for b in dialog.findChildren(QPushButton)))
            dialog.close();window.close()

    def test_recording_prevents_preview_and_closing_stops_playback(self):
        from types import SimpleNamespace
        with patch.object(VoiceSettingsDialog,'work',lambda *args:None):
            window=Window(preview=True);dialog=VoiceSettingsDialog(window)
            window.voice_dialog=SimpleNamespace(capture=True)
            dialog.play_preview();self.assertIn('Finish recording',dialog.note.text())
            self.assertFalse(dialog.previewing)
            dialog.preview_stop.clear();dialog.close();self.assertTrue(dialog.preview_stop.is_set())
            window.voice_dialog=None;window.close()

    def test_settings_navigation_uses_svg_icons(self):
        from augmentor_linux.panels import SettingsDialog
        window=Window(preview=True);dialog=SettingsDialog(window)
        buttons=dialog.findChildren(QPushButton)
        labelled=[b for b in buttons if b.text() in ('Resonant Voice','Connect DSH','Recover connection','Save','Colours && visual effects','Prompt library','Memory','Support report','Done')]
        self.assertEqual(len(labelled),10)
        self.assertTrue(all(not b.icon().isNull() for b in labelled))
        dialog.close();window.close()

if __name__=='__main__':unittest.main()
