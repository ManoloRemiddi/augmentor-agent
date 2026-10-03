# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Exercise off/refresh and enabled setup without a graphical user session."""
import unittest
from unittest.mock import call, patch
from augmentor_linux.dictation_settings_data import snapshot


class SettingsDataTests(unittest.TestCase):
    def test_disabled_refresh_never_bootstraps_the_component(self):
        disabled = {'enabled': False, 'installed': True, 'phase': 'disabled'}
        with patch('augmentor_linux.dictation.request', return_value=disabled) as request:
            self.assertEqual(snapshot('status'), {'status': disabled, 'models': [], 'devices': []})
        self.assertEqual(request.call_args_list, [call('status', None, timeout=75)])

    def test_turning_off_does_not_restart_for_model_or_device_lists(self):
        disabled = {'enabled': False, 'installed': True, 'phase': 'disabled'}
        with patch('augmentor_linux.dictation.request', side_effect=[{}, disabled]) as request:
            self.assertEqual(snapshot('enable', {'enabled': False})['status'], disabled)
        self.assertEqual(request.call_args_list, [call('enable', {'enabled': False}, timeout=75), call('status')])

    def test_enabled_setup_retains_model_device_and_current_revision_reads(self):
        initial = {'enabled': True, 'phase': 'setup-needed', 'revision': 1}
        refreshed = {**initial, 'revision': 2}
        models = [{'id': 'synthetic-model'}]; devices = [{'name': 'synthetic-microphone'}]
        with patch('augmentor_linux.dictation.request', side_effect=[initial, models, refreshed, devices]) as request:
            self.assertEqual(snapshot('status'), {'status': refreshed, 'models': models, 'devices': devices})
        self.assertEqual(request.call_args_list, [call('status', None, timeout=75), call('models', timeout=75), call('status'), call('devices', timeout=75)])


if __name__ == '__main__': unittest.main()
