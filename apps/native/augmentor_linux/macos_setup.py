# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""First-run model connection for the bundled, per-user Mac runtime."""
import json
from pathlib import Path
import subprocess
import sys
import threading
from PySide6.QtCore import QTimer, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpinBox, QVBoxLayout, QWidget, QProgressBar

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
    return not missing_runtime() and needed()


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


class MacSetupDialog(QDialog):
    completed = Signal(object)
    progress = Signal(str)

    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner; self.busy = False; self.dismissed = False
        self.completed.connect(self.finished_setup)
        self.progress.connect(self.show_progress)
        self.setWindowTitle('Install DSH'); self.setModal(True); self.setMinimumWidth(480)
        layout = QVBoxLayout(self)
        self.runtime_status = QLabel('DSH · Setup required')
        self.runtime_status.setStyleSheet('font-weight:600;font-size:17px;'); layout.addWidget(self.runtime_status)
        intro = QLabel('DSH runs your Augmentor agent. It is included in this app. Augmentor will install it, connect it and keep it running for you. No Terminal or separate download is needed.')
        intro.setWordWrap(True); layout.addWidget(intro)
        model_note = QLabel('Choose the AI model your agent will use. Enter an OpenAI-compatible provider or a local model server. Installing DSH does not download a model.')
        model_note.setWordWrap(True); layout.addWidget(model_note)
        form = QFormLayout(); layout.addLayout(form)
        self.url = QLineEdit(); self.url.setPlaceholderText('https://your-provider.example/v1')
        self.model = QLineEdit(); self.model.setPlaceholderText('The model name from your provider')
        self.key = QLineEdit(); self.key.setEchoMode(QLineEdit.EchoMode.Password)
        self.key.setPlaceholderText('Leave blank for a local model without a key')
        self.context = QSpinBox(); self.context.setRange(4096, 2000000); self.context.setValue(32768)
        self.fields = (self.url, self.model, self.key, self.context)
        for label, field in zip(('Model API address', 'Model name', 'API key'), self.fields):
            field.setAccessibleName(label); form.addRow(label, field)
        self.advanced = QPushButton('Advanced model settings'); self.advanced.setCheckable(True)
        layout.addWidget(self.advanced)
        self.advanced_fields = QWidget(); advanced_form = QFormLayout(self.advanced_fields)
        self.context.setAccessibleName('Context window'); advanced_form.addRow('Context window', self.context)
        self.advanced_fields.hide(); layout.addWidget(self.advanced_fields)
        self.advanced.toggled.connect(self.advanced_fields.setVisible)
        self.note = QLabel('Install DSH sends a short test message to your model. Your key is saved in your private Augmentor data folder on this Mac.')
        self.note.setWordWrap(True); layout.addWidget(self.note)
        self.progress_bar = QProgressBar(); self.progress_bar.setRange(0, 0); self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        actions = QHBoxLayout(); layout.addLayout(actions)
        self.later = QPushButton('Later'); self.later.clicked.connect(self.reject); actions.addWidget(self.later)
        self.external = QPushButton('Use existing DSH'); self.external.clicked.connect(self.use_external); actions.addWidget(self.external)
        self.connect_button = QPushButton('Install DSH'); self.connect_button.setDefault(True)
        self.connect_button.clicked.connect(self.connect_model); actions.addWidget(self.connect_button)

    def show_progress(self, phase):
        if self.busy and phase in STEPS:
            self.note.setText(STEPS[phase] + '…')
            self.runtime_status.setText(f'Step {list(STEPS).index(phase)+1} of {len(STEPS)}')

    def connect_model(self):
        if self.busy: return
        if not self.url.text().strip() or not self.model.text().strip():
            self.note.setText('Enter your model API address and model name.'); return
        controller = self.owner.controller
        if controller and (controller.running or controller.navigating or self.owner.editing):
            self.note.setText('Finish the current action before configuring a model.'); return
        request = {'url': self.url.text().strip(), 'model': self.model.text().strip(),
                   'apiKey': self.key.text(), 'context': self.context.value()}
        self.busy = True
        for field in (*self.fields, self.advanced, self.later, self.external, self.connect_button): field.setEnabled(False)
        self.connect_button.setText('Installing…'); self.progress_bar.show()
        self.show_progress('model')
        def work():
            try:
                result = run_setup(request, self.progress.emit)
            except Exception:
                result = {'ok': False, 'error': 'Setup could not finish. Its private data has been retained for diagnosis.'}
            try: self.completed.emit(result)
            except RuntimeError: pass
        threading.Thread(target=work, daemon=True).start()

    def finished_setup(self, result):
        self.busy = False
        if self.dismissed: return
        self.progress_bar.hide()
        for field in (*self.fields, self.advanced, self.later, self.external, self.connect_button): field.setEnabled(True)
        if not result.get('ok'):
            self.runtime_status.setText('Setup needs attention'); self.connect_button.setText('Retry setup')
            self.note.setText(result.get('error', 'Setup could not finish.')); return
        self.key.clear(); self.accept()
        QTimer.singleShot(0, lambda: self.owner.switch_harness('dsh', reconnect=True))

    def use_external(self):
        if self.busy: return
        from .dsh_setup import DshSetupDialog
        self.key.clear(); self.accept()
        self.owner.setup_dialog = DshSetupDialog(self.owner); self.owner.setup_dialog.show()

    def reject(self):
        if self.busy: return
        self.dismissed = True; self.key.clear(); super().reject()
