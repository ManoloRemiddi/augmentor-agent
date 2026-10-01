# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""The capability report must distinguish discovery from tested control."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('desktop_doctor', Path(__file__).resolve().parents[1] / 'services/desktop/linux-support/doctor.py')
doctor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(doctor)


class DesktopProfileTests(unittest.TestCase):
    def test_wayland_discovery_does_not_execute_tools_or_infer_x11_ownership(self):
        installed = {'kscreen-doctor', 'xrandr', 'xset', 'gdbus'}
        with patch.object(doctor.shutil, 'which', side_effect=lambda name: '/usr/bin/' + name if name in installed else None), patch.object(doctor.subprocess, 'run') as run:
            result = doctor.report(environment={'XDG_SESSION_TYPE': 'wayland', 'XDG_CURRENT_DESKTOP': 'KDE', 'DISPLAY': ':1', 'PRIVATE_TOKEN': 'secret'})
        run.assert_not_called()
        self.assertEqual(result['session_type'], 'wayland')
        self.assertTrue(result['commands']['kscreen-doctor'])
        self.assertIn('--help', result['installed_utilities']['kscreen-doctor'])
        self.assertNotIn('swaymsg', result['installed_utilities'])
        self.assertEqual(result['portals']['status'], 'not_probed')
        self.assertIn('does not assess installed desktop utilities', result['assessment'])
        self.assertIn('XWayland', ' '.join(result['limitations']))
        self.assertNotIn('secret', str(result))

    def test_missing_commands_do_not_become_capabilities(self):
        with patch.object(doctor.shutil, 'which', return_value=None):
            result = doctor.report(environment={})
        self.assertFalse(any(result['commands'].values()))
        self.assertEqual(result['installed_utilities'], {})
        self.assertEqual(result['session_type'], 'unknown')

    def test_portal_probe_remains_explicit_and_separate(self):
        observed = {'status': 'observed', 'interfaces': {'RemoteDesktop': {'AvailableDeviceTypes': 3}, 'ScreenCast': {}}}
        with patch.object(doctor, 'inspect_portals', return_value=observed) as probe:
            result = doctor.report(probe=True, environment={'XDG_SESSION_TYPE': 'wayland'})
        probe.assert_called_once_with()
        self.assertEqual(result['portals'], observed)
        self.assertIn('Live consent, capture and input tests still required', result['assessment'])


if __name__ == '__main__':
    unittest.main()
