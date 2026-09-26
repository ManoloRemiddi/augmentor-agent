# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""A Mac build without its bundled runtime must never fail silently.

The 0.2.8 Mac previews shipped no built-in DSH runtime. They passed identity and
signature checks, installed cleanly, and then fell through to the external-DSH
form with no explanation — which reads as "Augmentor wants a DSH you do not
have". These tests pin the two halves of the fix:

* the installer refuses such a candidate, before it can replace anything;
* first run names the gap instead of showing a form that cannot be satisfied;
* an *existing* incomplete installation is still replaceable, or the upgrade
  that fixes it could never run.
"""
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT/relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


install = load('mac_install_preflight', 'scripts/install-macos.py')
first_run = load('mac_first_run', 'apps/native/augmentor_linux/macos_setup.py')


def incomplete_bundle(directory, version='0.2.8'):
    """The shape of a pre-bundled-runtime build: identity present, payload not."""
    app = Path(directory)/'Augmentor Agent Desktop.app'
    resources = app/'Contents/Resources/app'
    resources.mkdir(parents=True)
    (app/'Contents/Info.plist').write_bytes(plistlib.dumps(
        {'CFBundleIdentifier': 'com.augmentor.Agent'}))
    (resources/'release.json').write_text(json.dumps(
        {'version': version, 'component': 'desktop', 'target': 'macos-arm64'}))
    return app


def complete_bundle(directory):
    app = incomplete_bundle(directory, version='0.2.12')
    resources = app/'Contents/Resources/app'
    for path, _ in install.RUNTIME_PAYLOAD:
        target = resources/path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('# payload\n')
    return app


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_complete_candidate_passes(self):
        install.validate_runtime(complete_bundle(self.tmp.name))

    def test_incomplete_candidate_is_refused(self):
        with self.assertRaises(ValueError) as caught:
            install.validate_runtime(incomplete_bundle(self.tmp.name))
        message = str(caught.exception)
        # Every missing piece is named, so the user knows what the build lacks.
        for _, label in install.RUNTIME_PAYLOAD:
            self.assertIn(label, message)
        self.assertIn('Nothing was installed', message)
        self.assertIn(install.GUIDE_URL, message)

    def test_partial_candidate_names_only_what_is_missing(self):
        app = complete_bundle(self.tmp.name)
        (app/'Contents/Resources/app/dsh/node_modules/@deepseek-ai/dsh/lib/bin.js').unlink()
        with self.assertRaises(ValueError) as caught:
            install.validate_runtime(app)
        message = str(caught.exception)
        self.assertIn('the bundled DSH runtime', message)
        self.assertNotIn('the bundled Node runtime', message)

    def test_an_existing_incomplete_installation_is_still_replaceable(self):
        """The upgrade that fixes an old copy must not be blocked by it.

        validate() is what runs against the existing destination; the payload
        check must live outside it, or 0.2.8 could never be updated.
        """
        app = incomplete_bundle(self.tmp.name)
        release = install.validate(app, development=True, verify=False)
        self.assertEqual(release['component'], 'desktop')
        with self.assertRaises(ValueError):
            install.validate_runtime(app)

    def test_installer_and_first_run_manifests_cannot_drift(self):
        self.assertEqual(tuple(install.RUNTIME_PAYLOAD),
                         tuple(first_run.RUNTIME_PAYLOAD))
        self.assertEqual(install.GUIDE_URL, first_run.GUIDE_URL)


class FirstRunDiagnosisTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.resources = Path(self.tmp.name)

    def test_missing_runtime_lists_every_absent_piece(self):
        self.assertEqual(first_run.missing_runtime(self.resources),
                         [label for _, label in first_run.RUNTIME_PAYLOAD])

    def test_complete_runtime_reports_nothing(self):
        for path, _ in first_run.RUNTIME_PAYLOAD:
            target = self.resources/path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('# payload\n')
        self.assertEqual(first_run.missing_runtime(self.resources), [])
        with patch.object(sys, 'platform', 'darwin'):
            self.assertEqual(first_run.runtime_problem(self.resources), '')

    def test_problem_names_the_missing_runtime_on_macos(self):
        with patch.object(sys, 'platform', 'darwin'):
            problem = first_run.runtime_problem(self.resources)
        self.assertIn('missing its own built-in runtime', problem)
        self.assertIn('the bundled DSH runtime', problem)

    def test_problem_is_silent_off_macos(self):
        """The Linux layout is different; this diagnosis is Mac-only."""
        with patch.object(sys, 'platform', 'linux'):
            self.assertEqual(first_run.runtime_problem(self.resources), '')

    def test_available_stays_false_without_the_bundled_cli(self):
        with patch.object(sys, 'platform', 'darwin'):
            self.assertFalse(first_run.available())


try:
    from PySide6.QtWidgets import QApplication
    HAVE_QT = True
except ImportError:                                   # pragma: no cover
    HAVE_QT = False


@unittest.skipUnless(HAVE_QT, 'PySide6 is required for the first-run dialog')
class SetupDialogChoiceTests(unittest.TestCase):
    """The order of the first-run decision is the fix.

    Before this, an incomplete copy fell through to the external-DSH form and
    silently asked for a DSH the user did not have.
    """

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        cls.app = QApplication.instance() or QApplication([])

    def _chosen(self, harness, problem, managed):
        from unittest.mock import MagicMock
        import augmentor_linux.window as window
        import augmentor_linux.macos_setup as macos_setup
        import augmentor_linux.dsh_setup as dsh_setup
        import augmentor_linux.setup as setup_module

        made = {}

        def factory(name):
            def build(*args):
                # The incomplete dialog takes (owner, problem); the rest take
                # just the owner.
                made['name'] = name
                return MagicMock()
            return build

        owner = SimpleNamespace(
            controller=SimpleNamespace(harness=harness, running=False, navigating=False),
            setup_dialog=None, set_status=lambda text: None)
        with patch.object(macos_setup, 'runtime_problem', return_value=problem), \
             patch.object(macos_setup, 'needed', return_value=True), \
             patch.object(macos_setup, 'available', return_value=managed), \
             patch.object(macos_setup, 'MacRuntimeIncompleteDialog', factory('incomplete')), \
             patch.object(macos_setup, 'MacSetupDialog', factory('managed')), \
             patch.object(dsh_setup, 'DshSetupDialog', factory('external')), \
             patch.object(setup_module, 'SetupDialog', factory('pi')):
            window.Window.open_setup(owner)
        return made.get('name')

    def test_missing_runtime_is_explained_not_redirected_to_external_dsh(self):
        self.assertEqual(self._chosen('dsh', 'missing its own built-in runtime', True),
                         'incomplete')
        # Even when the managed path claims to be available, the gap wins: the
        # app must not pretend it can set up.
        self.assertEqual(self._chosen('dsh', 'missing its own built-in runtime', False),
                         'incomplete')

    def test_complete_copy_still_offers_managed_setup(self):
        self.assertEqual(self._chosen('dsh', '', True), 'managed')

    def test_external_form_remains_the_last_resort(self):
        self.assertEqual(self._chosen('dsh', '', False), 'external')

    def test_pi_harness_is_untouched(self):
        self.assertEqual(self._chosen('pi', 'missing its own built-in runtime', True),
                         'pi')


@unittest.skipUnless(HAVE_QT, 'PySide6 is required for the first-run dialog')
class IncompleteDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        cls.app = QApplication.instance() or QApplication([])

    @staticmethod
    def _owner():
        """The dialog takes a Qt parent, so the owner must be a real widget."""
        from PySide6.QtWidgets import QWidget
        owner = QWidget()
        owner.setup_dialog = None
        return owner

    def test_dialog_explains_the_gap_and_offers_the_download_page(self):
        dialog = first_run.MacRuntimeIncompleteDialog(
            self._owner(),
            'This copy of Augmentor is missing its own built-in runtime: '
            'the bundled DSH runtime.')
        try:
            self.assertIn('missing its own built-in runtime', dialog.windowTitle()
                          + self._labels(dialog))
            self.assertIn('Open download page', self._buttons(dialog))
            self.assertIn('Use existing DSH instead', self._buttons(dialog))
        finally:
            dialog.deleteLater()

    def test_open_guide_uses_the_documented_page(self):
        dialog = first_run.MacRuntimeIncompleteDialog(self._owner(), 'incomplete.')
        try:
            with patch.object(first_run.QDesktopServices, 'openUrl') as opened:
                dialog.open_guide()
            self.assertEqual(opened.call_args.args[0].toString(),
                             first_run.GUIDE_URL)
        finally:
            dialog.deleteLater()

    @staticmethod
    def _buttons(dialog):
        from PySide6.QtWidgets import QPushButton
        return [b.text() for b in dialog.findChildren(QPushButton)]

    def _labels(self, dialog):
        from PySide6.QtWidgets import QLabel
        return ' '.join(label.text() for label in dialog.findChildren(QLabel))


if __name__ == '__main__':
    unittest.main()
