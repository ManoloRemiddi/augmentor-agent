# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Shared desktop participation in reversible component maintenance."""
from functools import wraps
from . import platform_runtime  # Expose the shared service modules in all bundles.
from lifecycle.admission import Admission, MaintenanceBusy
from PySide6.QtCore import QTimer


def admitted(method):
    """Fence a new controller operation before it changes state or queues work."""
    @wraps(method)
    def invoke(self, *args, **kwargs):
        with self.admission.work():
            return method(self, *args, **kwargs)
    return invoke


class WindowMaintenance:
    def __init__(self, window):
        self.window = window
        self.preview_gate = Admission()
        self.was_enabled = None
        self.timer = QTimer(window)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.refresh)

    @property
    def gate(self):
        return getattr(self.window.controller,'admission',self.preview_gate)

    def phase(self):
        return self.gate.control('host.maintenance.status', {})['phase']

    def refresh(self):
        phase = self.phase()
        if phase == 'ready':
            if self.was_enabled is not None:
                self.window.setEnabled(self.was_enabled)
                self.was_enabled = None
            self.timer.stop()
        else:
            if self.was_enabled is None:
                self.was_enabled = self.window.isEnabled()
            self.window.setEnabled(False)
            if phase == 'prepared':self.timer.start()
            else:self.timer.stop()

    def control(self, method, params):
        gate = self.gate
        # Atomically exclude new controller work while checking local drafts,
        # dialogs and activity. The GUI portion already runs on the Qt thread.
        with gate.lock:
            if method in ('host.maintenance.prepare', 'host.maintenance.commit'):
                if self.window.maintenance_state(include_reservation=False)['busy']:
                    raise MaintenanceBusy('The window has active work, a draft or an open dialog. Its work was preserved.')
            result = gate.control(method, params)
        self.refresh()
        return result
