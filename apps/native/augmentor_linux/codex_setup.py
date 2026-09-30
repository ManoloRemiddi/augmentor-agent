# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Codex connection UI; profile and credential logic stays in the shared host."""
import uuid
from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QCheckBox, QPushButton
from .ui_scale import scaled


class CodexSetupDialog(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.owner = window; self.controller = window.controller; self.client = self.controller.client
        self.rows = []; self.profile_id = None; self.busy = False; self.dismissed = False
        self.setWindowTitle('Connect a model · Codex'); self.setModal(True); scaled(self).setMinimumWidth(470)
        layout = QVBoxLayout(self)
        intro = QLabel('Use a Responses-compatible API provider or a model running on this computer. Subscription sign-in is not available in this development build.')
        intro.setWordWrap(True); layout.addWidget(intro)
        form = QFormLayout(); layout.addLayout(form)
        self.profiles = QComboBox(); self.profiles.addItem('New connection', None); self.profiles.currentIndexChanged.connect(self.selected)
        self.kind = QComboBox(); self.kind.addItem('API provider', 'api'); self.kind.addItem('Local model', 'local')
        self.name = QLineEdit('My Codex model'); self.name.setMaxLength(100)
        self.endpoint = QLineEdit(); self.endpoint.setPlaceholderText('https://provider.example/v1 or http://127.0.0.1:8080/v1')
        self.model = QLineEdit(); self.model.setPlaceholderText('Exact model ID')
        self.key = QLineEdit(); self.key.setEchoMode(QLineEdit.EchoMode.Password); self.key.setPlaceholderText('Optional; leave blank to keep an existing key')
        self.remove_key = QCheckBox('Remove the saved key')
        for label, widget in [('Saved connection', self.profiles), ('Connection type', self.kind), ('Connection name', self.name), ('Endpoint URL', self.endpoint), ('Model ID', self.model), ('API key', self.key)]:
            widget.setAccessibleName(label); form.addRow(label, widget)
        form.addRow(self.remove_key)
        notice = QLabel('Keys are stored in the operating system credential store. Check text response sends a short test message; your provider may charge for it. It does not send your files or conversation history, and does not verify tools.')
        notice.setWordWrap(True); layout.addWidget(notice)
        self.note = QLabel('Loading saved connections…'); self.note.setWordWrap(True); layout.addWidget(self.note)
        buttons = QHBoxLayout(); layout.addLayout(buttons)
        self.close_button = QPushButton('Close'); self.close_button.clicked.connect(self.reject); buttons.addWidget(self.close_button)
        self.check_button = QPushButton('Check text response'); self.check_button.clicked.connect(self.check); buttons.addWidget(self.check_button)
        self.save_button = QPushButton('Save connection'); self.save_button.clicked.connect(self.save); buttons.addWidget(self.save_button)
        self.fields = [self.profiles, self.kind, self.name, self.endpoint, self.model, self.key, self.remove_key]
        for field in [self.name, self.endpoint, self.model, self.key]: field.textChanged.connect(self.edited)
        self.kind.currentIndexChanged.connect(self.edited); self.remove_key.toggled.connect(self.edited)
        self.dirty = False
        self.request('profiles.list', {}, self.loaded)

    def edited(self, *_):
        self.dirty = True; self.check_button.setEnabled(False)

    def selected(self, *_):
        self.profile_id = self.profiles.currentData()
        row = next((row for row in self.rows if row['id'] == self.profile_id), {})
        self.name.setText(row.get('name', 'My Codex model')); self.endpoint.setText(row.get('endpoint', '')); self.model.setText(row.get('model', ''))
        self.kind.setCurrentIndex(self.kind.findData(row.get('kind', 'api'))); self.key.clear(); self.remove_key.setChecked(False)
        self.dirty = False; self.check_button.setEnabled(bool(self.profile_id) and not self.busy)
        self.note.setText('Text response checked; tool compatibility is not verified.' if row.get('validation') == 'responses-text' else 'Save a connection, then check its text response.')

    def loaded(self, value):
        self.rows = value['profiles']; selected = self.profile_id
        self.profiles.blockSignals(True); self.profiles.clear(); self.profiles.addItem('New connection', None)
        for row in self.rows: self.profiles.addItem(row['name'], row['id'])
        self.profiles.setCurrentIndex(max(0, self.profiles.findData(selected))); self.profiles.blockSignals(False); self.selected()

    def request(self, method, payload, callback):
        if self.busy: return
        self.busy = True
        for field in [*self.fields, self.save_button, self.check_button, self.close_button]: field.setEnabled(False)
        def work():
            try: return self.client.call(method, payload), None
            except Exception as error: return None, str(error)
        def finished(result):
            if self.dismissed: return
            self.busy = False
            for field in [*self.fields, self.save_button, self.close_button]: field.setEnabled(True)
            self.check_button.setEnabled(bool(self.profile_id) and not self.dirty)
            if self.owner.controller is not self.controller: self.reject(); return
            if result[1]: self.note.setText(result[1]); return
            callback(result[0])
        self.owner.call_in_background(work, finished)

    def save(self):
        if self.busy: return
        payload = {'id': self.profile_id or str(uuid.uuid4()), 'name': self.name.text().strip(), 'kind': self.kind.currentData(), 'endpoint': self.endpoint.text().strip(), 'model': self.model.text().strip()}
        if self.remove_key.isChecked(): payload['credential'] = None
        elif self.key.text(): payload['credential'] = self.key.text()
        self.note.setText('Saving connection…')
        def saved(row):
            self.profile_id = row['id']; self.key.clear(); self.remove_key.setChecked(False); self.dirty = False
            self.controller.refresh_models()
            if not self.controller.session:
                selection = {'provider': row['id'], 'model': row['model']}; self.controller.choose_model(selection); self.owner.set_selection(selection)
            self.request('profiles.list', {}, self.loaded)
        self.request('profiles.configure', payload, saved)

    def check(self):
        if self.busy or self.dirty or not self.profile_id: return
        self.note.setText('Checking a text response…')
        def checked(_):
            self.note.setText('Text response verified. Tools and Codex agent compatibility still need a chat test.')
            self.controller.refresh_models()
        self.request('profiles.test', {'id': self.profile_id}, checked)

    def reject(self):
        if self.busy: return
        self.dismissed = True; self.key.clear(); super().reject()
