# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real socket credentials and refusal behavior, on Linux and macOS."""
import importlib.util
import os
from pathlib import Path
import socket
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('platform_support', Path(__file__).resolve().parents[1]/'services/platform_support.py')
platform_support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(platform_support)


class PeerCredentialTests(unittest.TestCase):
    def test_kernel_reports_connected_user(self):
        left, right = socket.socketpair()
        with left, right:
            self.assertEqual(platform_support.peer_uid(left), os.getuid())
            platform_support.require_same_user(right)

    def test_foreign_user_is_refused(self):
        with patch.object(platform_support, 'peer_uid', return_value=os.getuid()+1):
            with self.assertRaises(PermissionError):
                platform_support.require_same_user(None)

    def test_unsupported_platform_cannot_skip_authentication(self):
        with patch.object(platform_support.sys, 'platform', 'unsupported'):
            with self.assertRaises(RuntimeError):
                platform_support.require_same_user(None)
