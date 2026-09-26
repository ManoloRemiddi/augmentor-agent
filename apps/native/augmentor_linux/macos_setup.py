# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""First-run model connection for the bundled, per-user Mac runtime."""
import json
from pathlib import Path
import subprocess
import sys
import threading
from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpinBox, QVBoxLayout

ROOT = Path(__file__).resolve().parents[3]


def available():
    if sys.platform != 'darwin' or not (ROOT/'dsh/node_modules/.bin/dsh').is_file():
        return False
    from .adapters.dsh import current
    return not current()


class MacSetupDialog(QDialog):
    completed = Signal(object)

    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner; self.busy = False; self.dismissed = False
        self.completed.connect(self.finished_setup)
        self.setWindowTitle('Set up Augmentor'); self.setModal(True); self.setMinimumWidth(460)
        layout = QVBoxLayout(self)
        intro = QLabel('Connect your model to start chatting. Augmentor sets up and runs its agent automatically. You can use a local model or an OpenAI-compatible API.')
        intro.setWordWrap(True); layout.addWidget(intro)
        form = QFormLayout(); layout.addLayout(form)
        self.url = QLineEdit(); self.url.setPlaceholderText('https://your-provider.example/v1')
        self.model = QLineEdit(); self.model.setPlaceholderText('The model name from your provider')
        self.key = QLineEdit(); self.key.setEchoMode(QLineEdit.EchoMode.Password)
        self.key.setPlaceholderText('Leave blank for a local model without a key')
        self.context = QSpinBox(); self.context.setRange(4096, 2000000); self.context.setValue(32768)
        self.fields = (self.url, self.model, self.key, self.context)
        for label, field in zip(('Model API address', 'Model name', 'API key', 'Context window'), self.fields):
            field.setAccessibleName(label); form.addRow(label, field)
        self.note = QLabel('Connect sends a short test message to your provider. Your key is saved in your private Augmentor data folder on this Mac.')
        self.note.setWordWrap(True); layout.addWidget(self.note)
        actions = QHBoxLayout(); layout.addLayout(actions)
        self.later = QPushButton('Later'); self.later.clicked.connect(self.reject); actions.addWidget(self.later)
        self.external = QPushButton('Use existing DSH'); self.external.clicked.connect(self.use_external); actions.addWidget(self.external)
        self.connect_button = QPushButton('Connect'); self.connect_button.clicked.connect(self.connect_model); actions.addWidget(self.connect_button)

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
        for field in (*self.fields, self.later, self.external, self.connect_button): field.setEnabled(False)
        self.note.setText('Checking your model and starting Augmentor. This can take a minute…')
        def work():
            try:
                process = subprocess.run([sys.executable, '-I', '-B', str(ROOT/'scripts/setup-macos.py')],
                    input=json.dumps(request), text=True, capture_output=True)
                result = json.loads(process.stdout)
                if process.returncode and result.get('ok'):
                    result = {'ok': False, 'error': 'Setup did not finish successfully. Retry after checking your settings.'}
            except Exception:
                result = {'ok': False, 'error': 'Setup could not finish. Its private data has been retained for diagnosis.'}
            try: self.completed.emit(result)
            except RuntimeError: pass
        threading.Thread(target=work, daemon=True).start()

    def finished_setup(self, result):
        self.busy = False
        if self.dismissed: return
        for field in (*self.fields, self.later, self.external, self.connect_button): field.setEnabled(True)
        if not result.get('ok'):
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
