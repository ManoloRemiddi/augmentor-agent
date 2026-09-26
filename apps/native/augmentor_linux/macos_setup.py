# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Visible lifecycle and browser access for the bundled, per-user Mac runtime."""
import json
import importlib.util
import time
from pathlib import Path
import subprocess
import sys
import threading
from PySide6.QtCore import QTimer, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QProgressBar

ROOT = Path(__file__).resolve().parents[3]

# What a usable Mac copy must carry inside itself, relative to
# Contents/Resources/app. scripts/install-macos.py keeps the same list so it can
# refuse an incomplete download before installing it; a test asserts the two
# never drift apart.
RUNTIME_PAYLOAD = (
    ('node/bin/node', 'the bundled Node runtime'),
    ('python/bin/python3', 'the bundled Python runtime'),
    ('dsh/node_modules/@deepseek-ai/dsh/lib/bin.js', 'the bundled DSH runtime'),
    ('dsh/node_modules/.bin/dsh', 'the DSH launcher'),
    ('dsh/node_modules/dsh-resonant-voice/bin/resonant-voice.js', 'the bundled voice plugin'),
    ('scripts/setup-macos.py', 'the macOS first-run setup'),
)
GUIDE_URL = 'https://augmentoragent.com/macos.html'


def missing_runtime(resources=ROOT):
    """Labels of the runtime payload absent from `resources`, in order."""
    return [label for path, label in RUNTIME_PAYLOAD
            if not (resources/path).is_file()]


def runtime_problem(resources=ROOT):
    """A sentence naming what this copy lacks, or '' when it is complete.

    Returning the reason rather than a bare False is the whole point: a copy
    without its bundled runtime used to fall through to the external-DSH form
    silently, which reads as a demand the user cannot meet.
    """
    if sys.platform != 'darwin':
        return ''
    missing = missing_runtime(resources)
    if not missing:
        return ''
    return 'This copy of Augmentor is missing its own built-in runtime: ' + \
        ', '.join(missing) + '.'


def needed():
    """First run is setup, not a failed connection to recover repeatedly."""
    if sys.platform != 'darwin':
        return False
    from .adapters.dsh import current
    return not current()


def available():
    from .adapters.dsh import current
    saved = current()
    return sys.platform == 'darwin' and not missing_runtime() and (not saved or saved.get('managed', {}).get('type') == 'launchd')


STEPS = {
    'model': 'Checking your model',
    'runtime': 'Installing DSH for this Mac',
    'integration': 'Adding Augmentor capabilities',
    'service': 'Starting the background service',
    'ready': 'Checking that your agent is ready',
}


def run_setup(request, progress):
    """Stream only the worker's fixed phase IDs; credentials stay on stdin."""
    unknown = {'ok': False, 'error': 'Setup stopped before confirming the result. Your data is preserved. Check the settings and retry to check or finish the same installation.'}
    with subprocess.Popen([sys.executable, '-I', '-B', str(ROOT/'scripts/setup-macos.py'), '--progress'],
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL, text=True) as process:
        process.stdin.write(json.dumps(request)); process.stdin.close()
        result = None
        for line in process.stdout:
            try: event = json.loads(line)
            except ValueError: continue
            if not isinstance(event, dict): continue
            if event.get('phase') in STEPS: progress(event['phase'])
            if isinstance(event.get('ok'), bool): result = event
        code = process.wait()
    if not result or code and result.get('ok'): return unknown
    return result


class MacRuntimeIncompleteDialog(QDialog):
    """Explain an incomplete copy, and offer the one action that fixes it.

    Shown instead of the external-DSH form when the bundled runtime is absent,
    so the user is told what is wrong rather than being asked for a DSH they do
    not have.
    """

    def __init__(self, owner, problem):
        super().__init__(owner)
        self.owner = owner
        self.setWindowTitle('Reinstall Augmentor')
        self.setModal(True); self.setMinimumWidth(470)
        layout = QVBoxLayout(self)
        note = QLabel(problem + ' Augmentor runs its agent from that runtime, so no model can be connected until this copy is replaced.')
        note.setWordWrap(True); layout.addWidget(note)
        guide = QLabel('Download the current Augmentor build. Quit Augmentor before replacing this copy. Your saved conversations and settings stay in your account. <a href="' + GUIDE_URL + '">' + GUIDE_URL + '</a>')
        guide.setWordWrap(True); guide.setOpenExternalLinks(True); layout.addWidget(guide)
        actions = QHBoxLayout(); layout.addLayout(actions)
        self.close_button = QPushButton('Close'); self.close_button.clicked.connect(self.reject); actions.addWidget(self.close_button)
        self.external = QPushButton('Use existing DSH instead'); self.external.clicked.connect(self.use_external); actions.addWidget(self.external)
        self.guide_button = QPushButton('Open download page'); self.guide_button.clicked.connect(self.open_guide); actions.addWidget(self.guide_button)

    def open_guide(self):
        QDesktopServices.openUrl(QUrl(GUIDE_URL))

    def use_external(self):
        from .dsh_setup import DshSetupDialog
        self.accept()
        self.owner.setup_dialog = DshSetupDialog(self.owner); self.owner.setup_dialog.show()


def runtime_state(*, start=False, browser=False):
    """Inspect the saved profile; only an explicit Start/Open resumes its owner."""
    from .adapters.dsh import DshAdapter, current
    saved = current()
    if not saved:
        return {'ok': True, 'installed': False, 'online': False, 'modelCount': 0}
    try:
        if start and saved.get('managed', {}).get('type') == 'launchd':
            spec = importlib.util.spec_from_file_location('mac_runtime_owner', ROOT/'scripts/setup-macos.py')
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            module.start_saved(saved)
        adapter = DshAdapter(base=saved['endpoint'], home=saved['home'])
        deadline = time.monotonic() + (30 if start else 0)
        while True:
            try:
                adapter.call('host.describe')
                break
            except Exception:
                if time.monotonic() >= deadline: raise
                time.sleep(.3)
        catalog = adapter.model_catalog()
        configured = adapter.remote.configured_providers()
        result = {'ok': True, 'installed': True, 'online': True,
                  'modelCount': sum(len(g.get('models', [])) for g in catalog.get('groups', []) if g.get('provider') in configured)}
        if browser: result['browserUrl'] = adapter.remote.browser_url()
        return result
    except Exception:
        # Exception text may contain a credential-bearing request URL. Keep it
        # private; present the recovery action instead of echoing HTTP errors.
        return {'ok': False, 'installed': True, 'online': False,
                'error': 'DSH is not responding. Click Start DSH to reconnect its background service. Your conversations and settings are preserved.'}


class MacSetupDialog(QDialog):
    completed = Signal(object)
    progress = Signal(str)

    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner; self.busy = False; self.dismissed = False
        self.installed = not needed(); self.online = False; self.operation = None
        self.completed.connect(self.finished_operation)
        self.progress.connect(self.show_progress)
        self.setWindowTitle('Agent setup'); self.setModal(False); self.setMinimumWidth(460)
        layout = QVBoxLayout(self); layout.setSpacing(14)
        title = QLabel('Your Augmentor agent'); title.setStyleSheet('font-size:20px;font-weight:600;')
        layout.addWidget(title)
        intro = QLabel('Two steps: start DSH, then choose the model your agent will use. DSH is included with Augmentor.')
        intro.setWordWrap(True); layout.addWidget(intro)
        self.runtime_status = QLabel('1  DSH · Checking…' if self.installed else '1  DSH · Not set up yet')
        self.runtime_status.setStyleSheet('font-size:15px;font-weight:600;'); layout.addWidget(self.runtime_status)
        runtime_note = QLabel('Runs in the background and starts when you sign in to this Mac. You can open its browser interface here at any time.')
        runtime_note.setWordWrap(True); layout.addWidget(runtime_note)
        runtime_actions = QHBoxLayout(); layout.addLayout(runtime_actions)
        self.connect_button = QPushButton('Start DSH' if self.installed else 'Install and start DSH')
        self.connect_button.setDefault(True); self.connect_button.clicked.connect(self.install_or_start)
        runtime_actions.addWidget(self.connect_button)
        self.browser_button = QPushButton('Open DSH in browser'); self.browser_button.setEnabled(self.installed)
        self.browser_button.clicked.connect(self.open_browser); runtime_actions.addWidget(self.browser_button)
        self.model_status = QLabel('2  Model · Choose after DSH starts')
        self.model_status.setStyleSheet('font-size:15px;font-weight:600;'); layout.addWidget(self.model_status)
        model_note = QLabel('In DSH, open Settings → Models and choose your provider or local model. If DSH first asks for a DeepSeek key, choose Configure later to see other providers. Save your model, then click Check connection here.')
        model_note.setWordWrap(True); layout.addWidget(model_note)
        self.note = QLabel('No Terminal, server address or login key is needed to start DSH.')
        self.note.setWordWrap(True); layout.addWidget(self.note)
        self.progress_bar = QProgressBar(); self.progress_bar.setRange(0, 0); self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        actions = QHBoxLayout(); layout.addLayout(actions)
        self.later = QPushButton('Close'); self.later.clicked.connect(self.reject); actions.addWidget(self.later)
        self.refresh_button = QPushButton('Check connection'); self.refresh_button.clicked.connect(self.refresh)
        self.refresh_button.setEnabled(self.installed); actions.addWidget(self.refresh_button)
        self.chat_button = QPushButton('Return to chat'); self.chat_button.setEnabled(False)
        self.chat_button.clicked.connect(self.return_to_chat); actions.addWidget(self.chat_button)
        self.external = QPushButton('Advanced: connect an existing DSH')
        self.external.clicked.connect(self.use_external); layout.addWidget(self.external)
        if self.installed: QTimer.singleShot(0, self.refresh)

    def show_progress(self, phase):
        if self.busy and phase in STEPS: self.note.setText(STEPS[phase] + '…')

    def dispatch(self, operation, work):
        if self.busy or self.dismissed: return
        self.busy = True; self.operation = operation
        for button in (self.connect_button, self.browser_button, self.refresh_button, self.chat_button, self.external, self.later):
            button.setEnabled(False)
        self.progress_bar.show()
        self.note.setText('Checking DSH…' if operation == 'check' else 'Starting DSH…')
        def worker():
            try: result = work()
            except Exception: result = {'ok': False, 'error': 'DSH could not finish setup. Your data is preserved. Retry setup to continue.'}
            try: self.completed.emit(result)
            except RuntimeError: pass
        threading.Thread(target=worker, daemon=True).start()

    def install_or_start(self):
        controller = self.owner.controller
        if controller and (controller.running or controller.navigating or self.owner.editing):
            self.note.setText('Finish the current action before starting setup.'); return
        if self.installed:
            self.dispatch('start', lambda: runtime_state(start=True)); return
        def install():
            result = run_setup({'action': 'install-runtime'}, self.progress.emit)
            return runtime_state(start=True) if result.get('ok') else result
        self.dispatch('install', install)

    def open_browser(self):
        self.dispatch('browser', lambda: runtime_state(start=True, browser=True))

    def refresh(self):
        self.dispatch('check', runtime_state)

    def finished_operation(self, result):
        self.busy = False
        if self.dismissed: return
        self.progress_bar.hide()
        self.installed = result.get('installed', self.installed); self.online = result.get('online', False)
        self.later.setEnabled(True); self.external.setEnabled(True)
        self.connect_button.setEnabled(not self.online)
        self.connect_button.setText('DSH is running' if self.online else ('Start DSH' if self.installed else 'Retry installation'))
        self.browser_button.setEnabled(self.installed); self.refresh_button.setEnabled(self.installed)
        self.runtime_status.setText('1  DSH · Running' if self.online else ('1  DSH · Needs attention' if self.installed else '1  DSH · Not set up yet'))
        count = result.get('modelCount', 0)
        self.model_status.setText(f'2  Model · {count} configured in DSH' if count else '2  Model · Add a model in DSH')
        self.chat_button.setEnabled(self.online and count > 0)
        if not result.get('ok'):
            self.note.setText(result.get('error', 'DSH could not connect.')); return
        self.note.setText('DSH is running. Open its browser interface to choose a model.' if not count else
                          'Your model settings are saved. Return to chat and send a message to test the model.')
        if result.get('browserUrl'):
            if not QDesktopServices.openUrl(QUrl(result['browserUrl'])):
                self.note.setText('The default browser could not open. Set a default browser in macOS Settings and try again.')
        if self.operation == 'install':
            # The connection is saved only after the managed host is healthy.
            QTimer.singleShot(0, lambda: self.owner.switch_harness('dsh', reconnect=True))
        elif self.online and self.owner.controller:
            self.owner.controller.refresh_models()

    def return_to_chat(self):
        if self.busy: return
        self.accept(); self.owner.show(); self.owner.raise_(); self.owner.activateWindow()

    def use_external(self):
        if self.busy: return
        from .dsh_setup import DshSetupDialog
        self.accept()
        self.owner.setup_dialog = DshSetupDialog(self.owner); self.owner.setup_dialog.show()

    def reject(self):
        if self.busy: return
        self.dismissed = True; super().reject()
