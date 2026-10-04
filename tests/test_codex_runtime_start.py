# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Detached Codex uses the selected native interpreter for OS credentials."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from augmentor_linux import runtime_start


class CodexRuntimeStartTests(unittest.TestCase):
    def test_explicit_native_codex_selection_is_kept(self):
        from PySide6.QtWidgets import QApplication
        from augmentor_linux.window import Window
        app=QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ,{'AUGMENTOR_PI_CONFIG':folder,'AUGMENTOR_WINDOW_ID':'main'}):
            window=Window(preview=True,harness='codex')
            try:self.assertEqual(window.preferences.values['harness'],'codex')
            finally:window.close();app.processEvents()

    def test_selected_interpreter_reaches_the_detached_credential_helper(self):
        with tempfile.TemporaryDirectory() as folder:
            state=Path(folder)/'codex'
            probe=Mock();probe.__enter__=Mock(return_value=probe);probe.__exit__=Mock(return_value=False)
            probe.connect.side_effect=[FileNotFoundError(),FileNotFoundError(),None]
            with patch.dict(os.environ,{'AUGMENTOR_CODEX_STATE':str(state),'AUGMENTOR_CODEX_NODE':'/selected/node','AUGMENTOR_PYTHON':'/obsolete/python'}), \
                 patch.object(runtime_start,'LocalSocket',return_value=probe), \
                 patch.object(runtime_start.subprocess,'Popen') as spawn:
                spawn.return_value.poll.return_value=None
                runtime_start.ensure_running('codex')
            env=spawn.call_args.kwargs['env']
            self.assertEqual(env['AUGMENTOR_PYTHON'],runtime_start.sys.executable)
            self.assertEqual(spawn.call_args.args[0][0],env['AUGMENTOR_PYTHON'])
            self.assertEqual(spawn.call_args.args[0][3],'/selected/node')
            self.assertEqual(env['PI_TELEMETRY'],'0')
