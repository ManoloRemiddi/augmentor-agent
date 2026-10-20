# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""The installed Augmentor Harness, using its supported Pi transport."""
from pathlib import Path
from ..pi_client import PiClient, Connection, ContractError
from ..ah_connection import selection, ensure_running, check_description, shared_environment


class AhAdapter(PiClient):
    harness = 'ah'
    preset = 'augmentor-linux-pi'  # Existing Host surface identity, not another loop.

    def __init__(self):
        self.binding = None
        self.problem = ''
        try:
            self.binding = selection()
        except Exception as error:
            self.problem = 'Augmentor Harness is not connected. Open its normal launcher, then reconnect. '+str(error)
        super().__init__(self.binding['profile']['socket'] if self.binding else 'augmentor-harness:not-connected')

    def connection(self):
        if not self.binding:
            raise ContractError(self.problem)
        if selection() != self.binding:
            raise ContractError('The selected Harness changed. Reconnect before continuing.')
        c = Connection(self.base)
        try:
            check_description(self.binding, c.call('host.describe'))
            return c
        except Exception:
            c.close()
            raise

    def ensure_running(self):
        if not self.binding:
            raise ContractError(self.problem)
        ensure_running(self.binding)

    def workspace(self):
        if not self.binding:
            raise ContractError(self.problem)
        return Path(self.binding['profile']['workspace'])

    def state_path(self):
        import os
        if self.binding:
            return Path(self.binding['profile']['state'])/'clients/desktop/session.json'
        return Path(os.environ.get('XDG_STATE_HOME', Path.home()/'.local/state'))/'augmentor-ah/session.json'

    def prompt_client(self):
        return AhPromptClient(self)

    def improve_prompt(self, text, instructions, model, *, request_id=None, expected_revision=None, session_id=None):
        # The retained 0.2.11 Desktop uses the three-argument surface contract.
        # Instructions still come from AH's own current shared store.
        import uuid
        if request_id is None:
            request_id=uuid.uuid4().hex
        if expected_revision is None:
            expected_revision=self.prompt_client().call('prompts.list')['improvement']['revision']
        return super().improve_prompt(text,instructions,model,request_id=request_id,expected_revision=expected_revision,session_id=session_id)


class AhPromptClient:
    def __init__(self, adapter):
        self.adapter = adapter

    def call(self, method, payload=None, request_id=None):
        from ..prompt_client import PromptClient
        a = self.adapter
        if not a.binding:
            raise ContractError(a.problem)
        if selection() != a.binding:
            raise ContractError('The selected Harness changed. Reconnect before continuing.')
        return PromptClient(environment=shared_environment(a.binding), root=Path(a.binding['root'])).call(method, payload, request_id)

    def setting(self, namespace):
        if namespace != 'prompt-library':
            return None
        result = self.call('prompts.list')
        return {'ns':namespace, 'revision':result['revision'], 'value':result}
