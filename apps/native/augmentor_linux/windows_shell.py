# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Qt-thread boundary for the Windows background owner's shell mechanisms."""
from concurrent.futures import ThreadPoolExecutor
import threading

from PySide6.QtCore import QObject, Qt, Signal, Slot

from .shortcut_activation import DesktopActivation
from .windows_shortcuts import ShortcutOwner, DEFAULTS
from .maintenance import Admission, MaintenanceBusy


class Shell(QObject):
    queued = Signal(object)
    def __init__(self, shortcuts=None, admission=None):
        super().__init__()
        # This owner stays on its creating Qt thread. Do not manufacture Qt
        # adopted-thread wrappers in short-lived Python pipe workers merely
        # to choose the dispatch path; their shutdown can outlive QApplication.
        self.owner_thread = threading.current_thread()
        self.shortcuts = shortcuts if shortcuts is not None else ShortcutOwner()
        self.admission = admission or Admission()
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
        lease=self.admission.work()
        try:lease.__enter__()
        except MaintenanceBusy:return
        try:
            future=self.pool.submit(self.activations[instance].activate)
            self.pending[instance]=future
            future.add_done_callback(lambda _result:lease.__exit__(None,None,None))
        except BaseException:
            lease.__exit__(None,None,None);raise

    def request(self, message, *, timeout=10):
        lease=self.admission.work() if message.get('action')=='shortcut-save' else None
        if lease:lease.__enter__()
        release_lock=threading.Lock()
        def release():
            nonlocal lease
            with release_lock:
                if lease:lease.__exit__(None,None,None);lease=None
        if threading.current_thread() is self.owner_thread:
            try:return self.shortcuts.dispatch(message)
            finally:release()
        item = {'message': message, 'done': threading.Event(), 'lock': threading.Lock(),
                'cancelled': False, 'started':False, 'release':release}
        try:self.queued.emit(item)
        except BaseException:release();raise
        if not item['done'].wait(timeout):
            with item['lock']:
                item['cancelled'] = True
                if not item['started']:release()
            raise ValueError('The shortcut response timed out. Reopen Settings to check the current shortcut before retrying.')
        if 'error' in item: raise item['error']
        return item['result']

    @Slot(object)
    def dispatch(self, item):
        with item['lock']:
            cancelled = item['cancelled'] or self.closed
            if not cancelled:item['started']=True
        try:
            if cancelled:item['error'] = ValueError('The shortcut owner is shutting down.')
            else:item['result'] = self.shortcuts.dispatch(item['message'])
        except Exception as error:item['error']=error
        finally:item['release']();item['done'].set()

    def close(self):
        if self.closed: return
        self.closed = True; self.shortcuts.close()
        self.pool.shutdown(wait=True, cancel_futures=True)
