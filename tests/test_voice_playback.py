# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import unittest
from augmentor_linux.voice_playback import PlaybackBuffer


class PlaybackTests(unittest.TestCase):
    def test_measured_first_packet_gap_keeps_opening_word_continuous(self):
        # Observed live Breeze + tempo timings: 142ms at 220ms, then
        # 427ms at 463ms. Immediate playback would leave a 101ms hole.
        b=PlaybackBuffer();sent=bytes([17,4])*3410;later=bytes([18,5])*10240
        b.data.extend(sent)
        for i in range(12):self.assertEqual(b.read(960,.220+i*.020),b'')
        self.assertEqual(bytes(b.data),sent)
        b.data.extend(later)
        played=b''.join(b.read(960,.463+i*.020) for i in range(20))
        self.assertEqual(played,(sent+later)[:19200]);self.assertEqual(b.starvations,0)

    def test_completed_short_response_is_not_stuck_under_threshold(self):
        b=PlaybackBuffer();b.data.extend(b'\x01\x02'*100)
        self.assertEqual(b.read(960,1),b'');b.complete=True
        self.assertEqual(b.read(960,1.01),b'\x01\x02'*100)
        self.assertEqual(b.starvations,0)

    def test_startup_wait_is_bounded_and_starvation_rebuffers(self):
        b=PlaybackBuffer();b.data.extend(b'\x01\x02'*100)
        self.assertEqual(b.read(960,1),b'')
        self.assertEqual(len(b.read(960,1.251)),200)
        self.assertEqual(b.starvations,1)
        b.data.extend(b'\x03\x04'*100)
        self.assertEqual(b.read(960,1.27),b'')

    def test_interrupt_discards_pcm_and_a_new_burst_rebuffers(self):
        b=PlaybackBuffer();b.data.extend(b'\x01\x02'*6000)
        self.assertEqual(len(b.read(960,1)),960)
        b.reset();self.assertFalse(b.data);self.assertFalse(b.started)
        b.data.extend(b'\x03\x04'*100);self.assertEqual(b.read(960,2),b'')
        b.complete=True;self.assertEqual(len(b.read(960,2.01)),200)
        b.start();b.data.extend(b'\x05\x06'*100)
        self.assertEqual(b.read(960,3),b'')
