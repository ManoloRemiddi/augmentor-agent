# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import unittest
from unittest.mock import patch, Mock
from augmentor_linux.browser import open_url


class BrowserTests(unittest.TestCase):
    def test_named_browser_uses_existing_profile_and_preserves_url_as_one_argument(self):
        url = 'https://www.amazon.it/s?k=RTX+5090&literal=$(ignored)'
        with patch('augmentor_linux.browser.shutil.which', return_value='/usr/bin/chromium'), \
             patch('augmentor_linux.browser.desktop_environment', return_value={'DISPLAY': ':1'}), \
             patch('augmentor_linux.browser.subprocess.Popen') as launch:
            launch.return_value.wait.return_value = 0
            result = open_url(url)
        self.assertEqual(launch.call_args.args[0], ['/usr/bin/chromium', '--new-tab', url])
        self.assertEqual(launch.call_args.kwargs['env'], {'DISPLAY': ':1'})
        self.assertTrue(result['dispatched'])
        self.assertFalse(result['verified'])

    def test_invalid_url_and_other_browser_never_launch(self):
        with patch('augmentor_linux.browser.subprocess.Popen') as launch:
            for url in ['--headless', 'file:///etc/passwd', 'javascript:alert(1)',
                        'https://name:secret@example.com/', 'https://example.com/\n--flag', None]:
                with self.assertRaises(ValueError):
                    open_url(url)
            with self.assertRaises(ValueError):
                open_url('https://example.com', browser='brave')
            launch.assert_not_called()

    def test_missing_desktop_does_not_launch_and_browser_failure_is_reported(self):
        with patch('augmentor_linux.browser.shutil.which', return_value='/usr/bin/chromium'), \
             patch('augmentor_linux.browser.desktop_environment', side_effect=RuntimeError('No desktop')), \
             patch('augmentor_linux.browser.subprocess.Popen') as launch:
            with self.assertRaises(RuntimeError):
                open_url('https://example.com')
            launch.assert_not_called()
        with patch('augmentor_linux.browser.shutil.which', return_value='/usr/bin/chromium'), \
             patch('augmentor_linux.browser.desktop_environment', return_value={}), \
             patch('augmentor_linux.browser.subprocess.Popen', return_value=Mock(wait=lambda **_: 1)):
            result = open_url('https://example.com')
            self.assertFalse(result['ok'])
            self.assertFalse(result['verified'])
