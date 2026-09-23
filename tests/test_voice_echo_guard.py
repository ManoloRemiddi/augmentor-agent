# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import unittest
import numpy as np
from augmentor_linux.voice_echo_guard import PlaybackEchoGuard

class EchoGuardTests(unittest.TestCase):
    def fixture(self):
        rng=np.random.default_rng(51)
        x=np.convolve(rng.normal(size=4800),np.ones(5)/5,'same')*.16
        pcm=(x*32767).astype('<i2').tobytes();guard=PlaybackEchoGuard()
        guard.played(pcm,at=10)
        ref=np.interp(np.arange(0,len(x),1.5),np.arange(len(x)),x)
        return guard,ref

    def test_delayed_attenuated_playback_is_rejected_before_barge_in(self):
        guard,ref=self.fixture()
        echo=(ref[480:992]*.25*32767).astype('<i2').tobytes()
        self.assertTrue(guard.is_echo(echo,now=10.1))
        self.assertFalse(guard.is_echo(echo,now=10.5),'Old output must not suppress a later turn')

    def test_independent_voice_and_dominant_double_talk_remain_eligible(self):
        guard,ref=self.fixture();rng=np.random.default_rng(71)
        human=np.convolve(rng.normal(size=512),np.ones(5)/5,'same')*.15
        self.assertFalse(guard.is_echo((human*32767).astype('<i2').tobytes(),now=10.1))
        mixture=human+ref[480:992]*.1
        self.assertFalse(guard.is_echo((mixture*32767).astype('<i2').tobytes(),now=10.1))

    def test_residual_silence_only_suppressed_during_recent_playback(self):
        guard,_=self.fixture();self.assertTrue(guard.is_echo(bytes(1024),now=10.1))
        self.assertFalse(PlaybackEchoGuard().is_echo(bytes(1024),now=10.1))

if __name__=='__main__':unittest.main()
