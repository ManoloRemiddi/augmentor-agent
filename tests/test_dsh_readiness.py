# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""A reachable catalog must not certify that the desktop can create its agent."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from augmentor_linux.adapters.dsh import DshAdapter
from augmentor_linux.adapters.dsh_wire import DshClient
from augmentor_linux.pi_client import ContractError


class DshReadinessTests(unittest.TestCase):
    def client(self):
        with patch('augmentor_linux.adapters.dsh.current', return_value={}):
            return DshAdapter(base='http://127.0.0.1:3080', home=Path(tempfile.gettempdir()))

    def test_pre_setup_window_is_not_ready_with_only_product_presets(self):
        adapter=self.client()
        with patch.object(DshClient, 'call', return_value={'presets':[
                {'id':'augmentor-linux-product'}, {'id':'augmentor-browser-product'}]}) as call:
            with self.assertRaisesRegex(ContractError, 'Connect DSH'):
                adapter.call('host.describe')
        self.assertEqual(call.call_args_list[0].args, ('agentPresets.list',))
        self.assertEqual(call.call_count, 1)

    def test_broken_matching_preset_is_not_ready(self):
        adapter=self.client()
        with patch.object(DshClient, 'call', return_value={
                'presets':[{'id':'augmentor-linux','broken':True}]}):
            with self.assertRaisesRegex(ContractError, 'preset is unavailable'):
                adapter.call('host.describe')

    def test_supported_legacy_preset_still_connects(self):
        adapter=self.client()
        def reply(method, payload=None):
            if method=='agentPresets.list':return {'presets':[{'id':'augmentor-linux'}]}
            self.assertEqual(method, 'host.describe')
            return {'version':'0.1.5-rc.1'}
        with patch.object(DshClient, 'call', side_effect=reply):
            self.assertEqual(adapter.call('host.describe'), {'version':'0.1.5-rc.1'})
