# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import os
import unittest
from unittest.mock import Mock, patch

from augmentor_linux.voice_echo import EchoRoute, EchoRouteError, _pulse_device


class EchoRouteTests(unittest.TestCase):
    def test_environment_restored_even_when_stream_open_fails(self):
        with patch.dict(os.environ, {'PULSE_SOURCE': 'user-microphone'}):
            with self.assertRaises(ValueError):
                with _pulse_device('PULSE_SOURCE', 'session-aec'):
                    self.assertEqual(os.environ['PULSE_SOURCE'], 'session-aec')
                    raise ValueError('open failed')
            self.assertEqual(os.environ['PULSE_SOURCE'], 'user-microphone')

    def test_playback_monitor_cannot_become_microphone(self):
        with patch('augmentor_linux.voice_echo._pactl',
                   side_effect=['desktop.monitor', 'desktop']) as pactl:
            with self.assertRaisesRegex(EchoRouteError, 'physical microphone'):
                EchoRoute.create()
            self.assertEqual(pactl.call_count, 2)

    def test_missing_route_is_cleaned_up(self):
        with patch('augmentor_linux.voice_echo._pactl',
                   side_effect=['physical_mic', 'physical_sink', '25', '']) as pactl, \
             patch.object(EchoRoute, '_device_index', return_value=None), \
             patch('augmentor_linux.voice_echo.time.monotonic', side_effect=[10, 13]):
            with self.assertRaisesRegex(EchoRouteError, 'did not become available'):
                EchoRoute.create()
            self.assertEqual(pactl.call_args.args, ('unload-module', '25'))
            self.assertFalse(any('set-default' in str(call) for call in pactl.call_args_list))

    def test_stream_restoration_to_wrong_device_is_rejected_and_closed(self):
        route = EchoRoute('26', 'aec_mic', 'aec_sink')
        sd = Mock()
        with patch.object(route, '_device_index', return_value=81), \
             patch.object(route, '_process_streams', side_effect=[[], [{'index': 42, 'source': 90}]]), \
             patch('augmentor_linux.voice_echo._pactl'):
            try:
                with self.assertRaisesRegex(EchoRouteError, 'confirm echo-cancelled'):
                    route.open_input(sd, samplerate=16000)
                sd.RawInputStream.return_value.close.assert_called_once()
            finally:
                route.close()

    def test_successful_routing_does_not_depend_on_global_default(self):
        route = EchoRoute('27', 'aec_mic', 'aec_sink')
        sd = Mock()

        def constructor(**kwargs):
            self.assertEqual(kwargs['device'], 'pulse')
            self.assertEqual(os.environ['PULSE_SINK'], 'aec_sink')
            return Mock()

        sd.RawOutputStream.side_effect = constructor
        with patch.object(route, '_device_index', return_value=82), \
             patch.object(route, '_process_streams', side_effect=[[], [{'index': 43, 'sink': 82}]]), \
             patch('augmentor_linux.voice_echo._pactl') as pactl:
            try:
                stream = route.open_output(sd, samplerate=24000)
                stream.close.assert_not_called()
                pactl.assert_not_called()
            finally:
                route.close()
                route.close()
                pactl.assert_called_once_with('unload-module', '27')


if __name__ == '__main__':
    unittest.main()
