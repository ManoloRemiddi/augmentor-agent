# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Setup handoff preserves work and rejects duplicate dispatch after restart."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import uuid
from augmentor_linux.onboarding import start

class OnboardingTests(unittest.TestCase):
    def test_preserve_work_and_persist_dispatch(self):
        with tempfile.TemporaryDirectory() as folder:
            calls=[]
            controller=SimpleNamespace(running=False,navigating=False,recovery_lock=SimpleNamespace(locked=lambda:False),state_file=Path(folder)/'session.json',send=lambda *args:calls.append(args))
            window=SimpleNamespace(controller=controller,editing=None,composer=SimpleNamespace(toPlainText=lambda:''),model_picker=SimpleNamespace(currentData=lambda:{'provider':'test','model':'test'}),new_chat=lambda:calls.append('new'),bring_forward=lambda:None)
            identity=str(uuid.uuid4())
            controller.running=True
            with self.assertRaisesRegex(RuntimeError,'current Linux action'):start(window,'memory',identity)
            controller.running=False;window.composer.toPlainText=lambda:'Important draft'
            with self.assertRaisesRegex(RuntimeError,'unfinished'):start(window,'memory',identity)
            self.assertEqual(calls,[])
            window.composer.toPlainText=lambda:''
            self.assertEqual(start(window,'memory',identity)['status'],'started')
            self.assertEqual(len(calls),2)
            self.assertIn('memory.check',calls[1][0]);self.assertIn('memory.configure',calls[1][0])
            # A new Window object uses the on-disk receipt; it cannot replay.
            self.assertTrue(start(SimpleNamespace(**window.__dict__),'memory',identity)['reused'])
            self.assertEqual(len(calls),2)
            self.assertEqual((Path(folder)/'onboarding-requests.json').stat().st_mode & 0o777,0o600)
            with self.assertRaisesRegex(RuntimeError,'Unknown'):start(window,'shell',identity)
            with self.assertRaisesRegex(RuntimeError,'Invalid'):start(window,'memory','bad')
