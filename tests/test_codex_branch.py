# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import json, os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from augmentor_linux.controller import Controller
from augmentor_linux.pi_client import ContractError

class CodexBranchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_unknown_reply_survives_controller_restart_with_same_request_identity(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ,{'AUGMENTOR_CODEX_STATE':directory,'AUGMENTOR_CODEX_SOCKET':directory+'/host.sock','AUGMENTOR_WINDOW_ID':'main'}):
            first=Controller(harness='codex');first.session='source';calls=[]
            def unknown(method,request):
                if method=='session.branch':calls.append(request);raise ContractError('Lost reply')
                return {'status':'creating'}
            first.client.call=unknown
            with self.assertRaisesRegex(ContractError,'Lost reply'):first.request_branch('source',4,'reply')
            saved=json.loads(first.state_file.read_text());self.assertEqual(saved['pendingBranch'],calls[0])
            first.close()
            second=Controller(harness='codex');second.client.call=unknown
            try:
                with self.assertRaisesRegex(ContractError,'Lost reply'):second.request_branch('source',4,'reply')
                self.assertEqual(calls[0],calls[1])
                with self.assertRaisesRegex(ContractError,'previous branch'):second.request_branch('source',5,'reply')
                self.assertEqual(len(calls),2)
            finally:second.close()
    def test_authoritative_absence_releases_failed_intent_and_storage_failure_prevents_dispatch(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ,{'AUGMENTOR_CODEX_STATE':directory,'AUGMENTOR_CODEX_SOCKET':directory+'/host.sock','AUGMENTOR_WINDOW_ID':'main'}):
            controller=Controller(harness='codex');controller.state_file=Path(directory)/'session.json';calls=[]
            def rejected(method,request):
                calls.append(method)
                if method=='session.branch':raise ContractError('Not a boundary')
                return {'status':'absent'}
            controller.client.call=rejected
            try:
                with self.assertRaisesRegex(ContractError,'Not a boundary'):controller.request_branch('source',4,'edit')
                self.assertIsNone(controller.pending_branch)
                controller.save_session=lambda:(_ for _ in ()).throw(OSError('Disk full'))
                with self.assertRaisesRegex(OSError,'Disk full'):controller.request_branch('source',5,'reply')
                self.assertEqual(calls.count('session.branch'),1)
            finally:controller.close()
