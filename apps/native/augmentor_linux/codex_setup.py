# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Codex connection UI; profile and credential logic stays in the shared host."""
import uuid
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QCheckBox, QPushButton, QMenu
from .ui_scale import scaled


class CodexSetupDialog(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.owner = window; self.controller = window.controller; self.client = self.controller.client
        self.rows = []; self.profile_id = None; self.busy = False; self.dismissed = False
        self.account_busy = False; self.account_status = {}; self.owned_attempt = None; self.profile_account_id = None
        self.setWindowTitle('Connect a model · Codex'); self.setModal(True); scaled(self).setMinimumWidth(470)
        layout = QVBoxLayout(self)
        intro = QLabel('Use a Responses-compatible API provider or a model running on this computer. ChatGPT account availability is shown below.')
        intro.setWordWrap(True); layout.addWidget(intro)
        form = QFormLayout(); layout.addLayout(form)
        self.profiles = QComboBox(); self.profiles.addItem('New connection', None); self.profiles.currentIndexChanged.connect(self.selected)
        self.kind = QComboBox(); self.kind.addItem('API provider', 'api'); self.kind.addItem('Local model', 'local')
        self.kind.addItem('ChatGPT plan', 'chatgpt-plan')
        self.name = QLineEdit('My Codex model'); self.name.setMaxLength(100)
        self.endpoint = QLineEdit(); self.endpoint.setPlaceholderText('https://provider.example/v1 or http://127.0.0.1:8080/v1')
        self.model = QLineEdit(); self.model.setPlaceholderText('Exact model ID')
        self.model_menu = QMenu(self)
        self.key = QLineEdit(); self.key.setEchoMode(QLineEdit.EchoMode.Password); self.key.setPlaceholderText('Optional; leave blank to keep an existing key')
        self.remove_key = QCheckBox('Remove the saved key')
        for label, widget in [('Saved connection', self.profiles), ('Connection type', self.kind), ('Connection name', self.name), ('Endpoint URL', self.endpoint), ('Model ID', self.model), ('API key', self.key)]:
            widget.setAccessibleName(label); form.addRow(label, widget)
        form.addRow(self.remove_key)
        self.accounts = QComboBox(); self.accounts.setAccessibleName('ChatGPT account'); self.accounts.addItem('Add a ChatGPT account', None)
        self.accounts.currentIndexChanged.connect(self.account_selected); form.addRow('ChatGPT account', self.accounts)
        self.account_note = QLabel('Checking ChatGPT account availability…'); self.account_note.setWordWrap(True); layout.addWidget(self.account_note)
        account_buttons = QHBoxLayout(); layout.addLayout(account_buttons)
        self.sign_in_button = QPushButton('Sign in with ChatGPT'); self.sign_in_button.clicked.connect(lambda: self.account_start(False)); account_buttons.addWidget(self.sign_in_button)
        self.plan_button = QPushButton('Allow ChatGPT plan usage'); self.plan_button.clicked.connect(lambda: self.account_start(True)); account_buttons.addWidget(self.plan_button)
        self.cancel_login_button = QPushButton('Cancel sign-in'); self.cancel_login_button.clicked.connect(self.account_cancel); account_buttons.addWidget(self.cancel_login_button)
        self.sign_out_button = QPushButton('Sign out'); self.sign_out_button.clicked.connect(self.account_sign_out); account_buttons.addWidget(self.sign_out_button)
        notice = QLabel('Keys are stored in the operating system credential store. Checks send a short tool exercise or a synthetic image; your provider may charge for them. The Codex check uses one harmless test tool and sends no personal files or chat history. The image check enables screenshots for new chats.')
        notice.setWordWrap(True); layout.addWidget(notice)
        self.provider_notice = notice; self.api_notice = notice.text()
        self.note = QLabel('Loading saved connections…'); self.note.setWordWrap(True); layout.addWidget(self.note)
        buttons = QHBoxLayout(); layout.addLayout(buttons)
        self.close_button = QPushButton('Close'); self.close_button.clicked.connect(self.reject); buttons.addWidget(self.close_button)
        self.check_button = QPushButton('Check Codex connection'); self.check_button.clicked.connect(self.check); buttons.addWidget(self.check_button)
        self.image_button = QPushButton('Check image response'); self.image_button.clicked.connect(lambda: self.check('image')); buttons.addWidget(self.image_button)
        self.save_button = QPushButton('Save connection'); self.save_button.clicked.connect(self.save); buttons.addWidget(self.save_button)
        self.models_button = QPushButton('Choose ChatGPT model'); self.models_button.clicked.connect(self.load_account_models); buttons.addWidget(self.models_button)
        self.fields = [self.profiles, self.kind, self.name, self.endpoint, self.model, self.key, self.remove_key]
        for field in [self.name, self.endpoint, self.model, self.key]: field.textChanged.connect(self.edited)
        self.kind.currentIndexChanged.connect(self.kind_changed); self.remove_key.toggled.connect(self.edited)
        self.dirty = False
        self.account_timer = QTimer(self); self.account_timer.setInterval(1000); self.account_timer.timeout.connect(self.refresh_accounts); self.account_timer.start()
        self.account_controls(); self.refresh_accounts()
        self.request('profiles.list', {}, self.loaded)

    def account_controls(self, *_):
        attempt = self.account_status.get('attempt') or {}
        pending = attempt.get('state') in ('opening', 'waiting', 'saving')
        allowed = self.account_status.get('enabled') is True and not pending and not self.account_busy and not self.busy
        self.sign_in_button.setEnabled(allowed)
        self.plan_button.setEnabled(allowed and bool(self.accounts.currentData()))
        self.cancel_login_button.setEnabled(pending and not self.account_busy)
        self.sign_out_button.setEnabled(bool(self.accounts.currentData()) and not pending and not self.account_busy and not self.busy)
        self.accounts.setEnabled(not pending and not self.account_busy and not self.busy)
        self.kind.model().item(self.kind.findData('chatgpt-plan')).setEnabled(self.account_status.get('enabled') is True)
        plan = self.kind.currentData() == 'chatgpt-plan'
        row = next((row for row in self.account_status.get('accounts', []) if row['id'] == self.accounts.currentData()), {})
        ready = not plan or self.account_status.get('enabled') is True and row.get('signedIn') is True and row.get('planUsage') is True
        if not plan or not ready: self.model_menu.clear()
        self.models_button.setVisible(plan); self.models_button.setEnabled(plan and ready and allowed)
        for field in (self.endpoint, self.key, self.remove_key): field.setEnabled(not self.busy and not plan)
        self.save_button.setEnabled(not self.busy and ready)
        self.check_button.setEnabled(not self.busy and ready and bool(self.profile_id) and not self.dirty); self.image_button.setEnabled(self.check_button.isEnabled())
        self.provider_notice.setText('This connection uses the selected ChatGPT plan. Connection checks consume plan usage and send only synthetic test input. No API key is used. Enter a model ID and check its availability before starting a chat.' if plan else self.api_notice)

    def account_selected(self, *_):
        self.model_menu.clear()
        self.profile_account_id = None
        if self.kind.currentData() == 'chatgpt-plan': self.edited()
        else: self.account_controls()

    def kind_changed(self, *_):
        self.model_menu.clear()
        if self.kind.currentData() == 'chatgpt-plan':
            self.endpoint.setText('https://api.openai.com/v1'); self.key.clear(); self.remove_key.setChecked(False)
        self.edited()

    def load_account_models(self):
        if not self.models_button.isEnabled(): return
        account_id = self.accounts.currentData(); self.model_menu.clear()
        self.account_note.setText('Loading models for the selected ChatGPT account…')
        def loaded(value):
            if self.kind.currentData() != 'chatgpt-plan' or self.accounts.currentData() != account_id or value.get('accountId') != account_id: return
            for row in value['models']:
                action = self.model_menu.addAction(row['name'] + ' · ' + row['id']); action.setData(row['id'])
                action.triggered.connect(lambda _checked=False, model=row['id']: self.model.setText(model))
            self.account_note.setText('Choose a model, save the connection and check it before starting a chat.' if value['models'] else 'This account returned no models to display.')
            if value['models']: self.model_menu.popup(self.models_button.mapToGlobal(self.models_button.rect().bottomLeft()))
        self.account_request('accounts.models', {'accountId': account_id}, loaded)

    def account_loaded(self, value):
        self.account_status = value; selected = self.profile_account_id or self.accounts.currentData()
        self.accounts.blockSignals(True); self.accounts.clear(); self.accounts.addItem('Add a ChatGPT account', None)
        for row in value.get('accounts', []):
            self.accounts.addItem(row['label'] + (' · selected' if row.get('active') else ''), row['id'])
        self.accounts.setCurrentIndex(max(0, self.accounts.findData(selected))); self.accounts.blockSignals(False)
        attempt = value.get('attempt') or {}
        message = (value.get('notice') or attempt.get('message') or
            ('Complete sign-in in your browser.' if attempt.get('state') in ('opening', 'waiting') else 'Saving the verified account…' if attempt.get('state') == 'saving' else 'Account login is available. Model connections are configured separately.'))
        self.account_note.setText((value.get('reason') + (' ' + value['notice'] if value.get('notice') else '')) if value.get('reason') else message)
        if attempt.get('id') == self.owned_attempt and attempt.get('state') not in ('opening', 'waiting', 'saving'): self.owned_attempt = None
        self.account_controls()

    def account_request(self, method, payload, callback):
        if self.account_busy or self.dismissed: return
        self.account_busy = True; self.account_controls()
        def work():
            try: return self.client.call(method, payload), None
            except Exception as error: return None, str(error)
        def finished(result):
            self.account_busy = False
            if method == 'accounts.start' and result[0]:
                self.owned_attempt = result[0]['attempt']['id']
                if self.dismissed or self.owner.controller is not self.controller:
                    self.cancel_owned_login()
                    if not self.dismissed: self.reject()
                    return
            if self.dismissed: return
            if self.owner.controller is not self.controller: self.reject(); return
            if result[1]: self.account_note.setText(result[1]); self.account_controls(); return
            callback(result[0]); self.account_controls()
        self.owner.call_in_background(work, finished)

    def refresh_accounts(self):
        self.account_request('accounts.status', {}, self.account_loaded)

    def account_start(self, plan_usage):
        if not self.sign_in_button.isEnabled(): return
        payload = {'requestPlanUsage': bool(plan_usage)}
        if self.accounts.currentData(): payload['accountId'] = self.accounts.currentData()
        def started(value):
            self.account_status['attempt'] = value['attempt']; self.account_status.pop('notice', None); self.account_loaded(self.account_status)
        self.account_request('accounts.start', payload, started)

    def account_cancel(self):
        attempt = self.account_status.get('attempt') or {}
        if attempt.get('id'): self.account_request('accounts.cancel', {'attemptId': attempt['id']}, lambda _: self.refresh_accounts())

    def account_sign_out(self):
        if not self.sign_out_button.isEnabled(): return
        def signed_out(value):
            self.account_loaded(value['status'])
            self.account_note.setText('Signed out; remote revocation and local cleanup confirmed.' if value['remoteRevocationConfirmed'] and value['localCleanupConfirmed'] else
                'Signed out. ' + ('Remote revocation is unconfirmed. ' if not value['remoteRevocationConfirmed'] else '') + ('Unlock the OS credential store to finish local cleanup.' if not value['localCleanupConfirmed'] else ''))
        self.account_request('accounts.signOut', {'accountId': self.accounts.currentData()}, signed_out)

    def cancel_owned_login(self):
        attempt = self.owned_attempt; self.owned_attempt = None
        if not attempt: return
        def work():
            try: self.client.call('accounts.cancel', {'attemptId': attempt})
            except Exception: pass
        self.owner.call_in_background(work, lambda _: None)

    def edited(self, *_):
        self.dirty = True; self.check_button.setEnabled(False); self.image_button.setEnabled(False)
        self.account_controls()

    def selected(self, *_):
        self.model_menu.clear()
        self.profile_id = self.profiles.currentData()
        row = next((row for row in self.rows if row['id'] == self.profile_id), {})
        self.profile_account_id = row.get('accountId')
        self.accounts.blockSignals(True); self.accounts.setCurrentIndex(max(0, self.accounts.findData(self.profile_account_id))); self.accounts.blockSignals(False)
        self.name.setText(row.get('name', 'My Codex model')); self.endpoint.setText(row.get('endpoint', '')); self.model.setText(row.get('model', ''))
        self.kind.setCurrentIndex(self.kind.findData(row.get('kind', 'api'))); self.key.clear(); self.remove_key.setChecked(False)
        self.dirty = False; self.check_button.setEnabled(bool(self.profile_id) and not self.busy); self.image_button.setEnabled(self.check_button.isEnabled())
        self.note.setText('Codex tool check passed for this connection.' if row.get('toolsVerified') else 'Image response checked; screenshots are available in new chats.' if row.get('imageValidatedAt') else 'Text response checked; tool compatibility is not verified.' if row.get('validation') == 'responses-text' else 'Save a connection, then check it with Codex.')
        self.account_controls()

    def loaded(self, value):
        self.rows = value['profiles']; selected = self.profile_id
        self.profiles.blockSignals(True); self.profiles.clear(); self.profiles.addItem('New connection', None)
        for row in self.rows: self.profiles.addItem(row['name'], row['id'])
        self.profiles.setCurrentIndex(max(0, self.profiles.findData(selected))); self.profiles.blockSignals(False); self.selected()

    def request(self, method, payload, callback):
        if self.busy: return
        self.busy = True
        self.account_controls()
        for field in [*self.fields, self.save_button, self.check_button, self.image_button, self.close_button]: field.setEnabled(False)
        def work():
            try: return self.client.call(method, payload), None
            except Exception as error: return None, str(error)
        def finished(result):
            if self.dismissed: return
            self.busy = False
            for field in [*self.fields, self.save_button, self.close_button]: field.setEnabled(True)
            self.check_button.setEnabled(bool(self.profile_id) and not self.dirty); self.image_button.setEnabled(self.check_button.isEnabled())
            self.account_controls()
            if self.owner.controller is not self.controller: self.reject(); return
            if result[1]: self.note.setText(result[1]); return
            callback(result[0])
        self.owner.call_in_background(work, finished)

    def save(self):
        if self.busy: return
        payload = {'id': self.profile_id or str(uuid.uuid4()), 'name': self.name.text().strip(), 'kind': self.kind.currentData(), 'endpoint': self.endpoint.text().strip(), 'model': self.model.text().strip()}
        if self.kind.currentData() == 'chatgpt-plan':
            payload['accountId'] = self.accounts.currentData()
            if not self.save_button.isEnabled(): return
        elif self.remove_key.isChecked(): payload['credential'] = None
        elif self.key.text(): payload['credential'] = self.key.text()
        self.note.setText('Saving connection…')
        def saved(row):
            self.profile_id = row['id']; self.key.clear(); self.remove_key.setChecked(False); self.dirty = False
            self.controller.refresh_models()
            if not self.controller.session:
                selection = {'provider': row['id'], 'model': row['model']}; self.controller.choose_model(selection); self.owner.set_selection(selection)
            self.request('profiles.list', {}, self.loaded)
        self.request('profiles.configure', payload, saved)

    def check(self, capability='agent'):
        capability = 'image' if capability == 'image' else 'agent'
        if self.busy or self.dirty or not self.profile_id: return
        self.note.setText('Checking a synthetic image…' if capability == 'image' else 'Checking Codex chat and tool support…')
        def checked(_):
            self.note.setText('Image response verified. Start a new chat to use browser screenshots. General vision and tool accuracy still need a chat test.' if capability == 'image' else 'Codex chat and the test tool worked. Browser and desktop tasks still need their own checks.')
            self.controller.refresh_models()
        self.request('profiles.test', {'id': self.profile_id, 'capability': capability}, checked)

    def reject(self):
        if self.busy: return
        self.account_timer.stop(); self.cancel_owned_login()
        self.dismissed = True; self.key.clear(); super().reject()
