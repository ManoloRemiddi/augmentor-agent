# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Qt-thread boundary for the Windows background owner's shell mechanisms."""
from concurrent.futures import ThreadPoolExecutor
import threading

from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot

from .shortcut_activation import DesktopActivation
from .windows_shortcuts import ShortcutOwner, DEFAULTS


class Shell(QObject):
    queued = Signal(object)
    def __init__(self, shortcuts=None):
        super().__init__()
        self.shortcuts = shortcuts if shortcuts is not None else ShortcutOwner()
        self.activations = {name: DesktopActivation(instance=name) for name in DEFAULTS}
        self.pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix='Augmentor activation')
        self.pending = {}; self.closed = False
        self.queued.connect(self.dispatch, Qt.ConnectionType.QueuedConnection)
        self.shortcuts.hotkeys.pressed.connect(self.activate)

    @Slot(str)
    def activate(self, instance):
        if self.closed: return
        previous = self.pending.get(instance)
        if previous is not None and not previous.done(): return
        # Never block keyboard dispatch on desktop start or pipe timeouts.
        self.pending[instance] = self.pool.submit(self.activations[instance].activate)

    def request(self, message):
        if QThread.currentThread() == self.thread(): return self.shortcuts.dispatch(message)
        item = {'message': message, 'done': threading.Event(), 'lock': threading.Lock(), 'cancelled': False}
        self.queued.emit(item)
        if not item['done'].wait(10):
            with item['lock']: item['cancelled'] = True
            raise ValueError('The shortcut response timed out. Reopen Settings to check the current shortcut before retrying.')
        if 'error' in item: raise item['error']
        return item['result']

    @Slot(object)
    def dispatch(self, item):
        with item['lock']:
            cancelled = item['cancelled'] or self.closed
        if cancelled:
            item['error'] = ValueError('The shortcut owner is shutting down.')
        else:
            try: item['result'] = self.shortcuts.dispatch(item['message'])
            except Exception as error: item['error'] = error
        item['done'].set()

    def close(self):
        if self.closed: return
        self.closed = True; self.shortcuts.close()
        self.pool.shutdown(wait=True, cancel_futures=True)
