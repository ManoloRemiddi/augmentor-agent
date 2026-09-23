# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from augmentor_linux.voice_input import EarlyVoiceInput

class EarlyInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def make(self):
        with patch.object(EarlyVoiceInput,'_open',lambda self:None):value=EarlyVoiceInput()
        self.addCleanup(value.close);return value

    def test_handoff_keeps_first_samples_and_next_live_frame_in_order(self):
        source=self.make();a=bytes([1])*1024;b=bytes([2])*1024;c=bytes([3])*1024
        source._frame(a,512,None,None);source._frame(b,512,None,None)
        got=[];source.attach(lambda pcm,*_:got.append(pcm));source._frame(c,512,None,None)
        self.assertEqual(got,[a,b,c]);self.assertTrue(source.receiving);self.assertFalse(source.frames)

    def test_close_or_overflow_never_replays_a_tail(self):
        source=self.make()
        for _ in range(321):source._frame(bytes(1024),512,None,None)
        self.assertTrue(source.error);self.assertFalse(source.receiving)
        with self.assertRaises(RuntimeError):source.attach(lambda *_:self.fail('Replayed'))
        source.close();self.assertFalse(source.frames)
        source._frame(bytes(1024),512,None,None);self.assertFalse(source.frames)

    def test_missing_frames_clear_readiness_and_device_loss_refuses_handoff(self):
        source=self.make();source._frame(bytes(1024),512,None,None)
        self.assertTrue(source.receiving)
        source.last_frame-=1;source._check_receiving();self.assertFalse(source.receiving)
        source._frame(bytes(1024),512,None,'overflow')
        with self.assertRaises(RuntimeError):source.attach(lambda *_:self.fail('Replayed'))

if __name__=='__main__':unittest.main()
