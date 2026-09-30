# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Thin native client of the shared Codex host; no model loop or credentials here."""
import os
from pathlib import Path
from ..pi_client import Connection, ContractError


class CodexAdapter:
    harness = 'codex'
    preset = 'augmentor-linux-codex'
    capabilities = {'branch': True, 'edit': True, 'memory': False, 'voice': True}
    supports_queue = True

    def __init__(self, base=None):
        self.state = Path(os.environ.get('AUGMENTOR_CODEX_STATE', Path(os.environ.get('XDG_STATE_HOME', Path.home()/'.local/state'))/'augmentor-codex'))
        self.base = base or os.environ.get('AUGMENTOR_CODEX_SOCKET', str(self.state/'runtime.sock'))

    def connection(self):
        connection = Connection(self.base, protocol='augmentor-codex/1')
        connection.socket.settimeout(65)
        return connection

    def call(self, method, payload=None):
        connection = None
        try:
            try:
                connection = self.connection()
            except (FileNotFoundError, ConnectionRefusedError):
                if method != 'host.describe' or os.environ.get('AUGMENTOR_CODEX_NO_AUTOSTART') == '1':
                    raise
                from ..runtime_start import ensure_running
                ensure_running('codex')
                connection = self.connection()
            return connection.call(method, payload)
        except (OSError, ValueError) as error:
            raise ContractError('Cannot reach the Codex runtime. Check its connection status.') from error
        finally:
            if connection:
                connection.close()

    def voice_ticket(self, session):
        return self.call('voice.ticket', {'sessionId': session, 'surface': 'linux'})

    supports_prompt_improvement = True

    def improve_prompt(self, text, instructions, selection):
        return self.call('prompt.improve', {'text': text, 'instructions': instructions, 'selection': selection})

    def respond(self, rpc_id, value):
        return self.call('interaction.respond', {'rpcId': rpc_id, 'sessionId': value['sessionId'], 'value': {**value, 'approvalId': rpc_id}})

    def state_path(self): return self.state/'session.json'
    def workspace(self): return Path(os.environ.get('AUGMENTOR_CODEX_WORKSPACE', Path.home()/'Augmentor Codex'))
    def model_catalog(self): return self.call('models.list')
    def validate_model(self, selection): return self.call('models.validate', selection)
    def session_rows(self): return self.call('session.list')['items']
    def running_state(self, session): return next((row['running'] for row in self.session_rows() if row['sessionId'] == session), None)
    def saved_chats(self, action='state', session=None): return self.call('chats.saved', {'action': action, 'sessionId': session})['saved']
    def setting(self, namespace): return None
    def profiles(self): return self.call('profiles.list')['profiles']
    def configure_profile(self, profile): return self.call('profiles.configure', profile)
