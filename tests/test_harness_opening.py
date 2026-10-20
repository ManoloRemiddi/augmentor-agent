# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Selected engine browser routing without opening an owner's real browser."""
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch
from augmentor_linux.window import Window


class HarnessOpeningTests(TestCase):
    def owner(self,harness='ah',url='http://127.0.0.1:12345/#token=authored'):
        client=SimpleNamespace(call=Mock(return_value={'url':url}),remote=SimpleNamespace(browser_url=Mock(return_value='http://127.0.0.1:5555/')))
        owner=SimpleNamespace(controller=SimpleNamespace(harness=harness,client=client),opening_dsh=False,set_status=Mock(),open_setup=Mock())
        owner.call_in_background=lambda work,done:done(work())
        return owner

    def test_ah_and_pi_open_the_selected_owner(self):
        for harness in ['ah','pi']:
            owner=self.owner(harness)
            with patch('augmentor_linux.window.QDesktopServices.openUrl',return_value=True) as opened:
                Window.open_harness(owner)
            owner.controller.client.call.assert_called_once_with('harness.open')
            self.assertEqual(opened.call_args.args[0].port(),12345)
            self.assertFalse(owner.opening_dsh)

    def test_dsh_keeps_its_real_browser_route(self):
        owner=self.owner('dsh')
        with patch('augmentor_linux.managed_setup.needed',return_value=False),patch('augmentor_linux.managed_setup.available',return_value=False),patch('augmentor_linux.window.QDesktopServices.openUrl',return_value=True) as opened:
            Window.open_harness(owner)
        owner.controller.client.remote.browser_url.assert_called_once()
        owner.controller.client.call.assert_not_called()
        self.assertEqual(opened.call_args.args[0].port(),5555)

    def test_stale_result_after_switch_does_not_open_the_old_backend(self):
        owner=self.owner()
        def background(work,done):
            result=work();owner.controller=SimpleNamespace(harness='dsh');done(result)
        owner.call_in_background=background
        with patch('augmentor_linux.window.QDesktopServices.openUrl') as opened:Window.open_harness(owner)
        opened.assert_not_called()

    def test_failed_and_unsafe_links_leave_chat_available(self):
        for url in ['https://outside.test/#token=authored','http://127.0.0.1/']:
            owner=self.owner(url=url)
            with patch('augmentor_linux.window.QDesktopServices.openUrl') as opened:Window.open_harness(owner)
            opened.assert_not_called();owner.set_status.assert_called_once();self.assertFalse(owner.opening_dsh)
        owner=self.owner();owner.controller.client.call.side_effect=RuntimeError('offline')
        with patch('augmentor_linux.window.QDesktopServices.openUrl') as opened:Window.open_harness(owner)
        opened.assert_not_called();self.assertIn('offline',owner.set_status.call_args.args[0]);self.assertFalse(owner.opening_dsh)
