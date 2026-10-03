# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Own a GLib context on one worker; never pump Qt's GUI context from it."""
import threading
from concurrent.futures import Future
from collections import deque
from gi.repository import GLib


class Worker:
    def __init__(self,factory):
        self.ready=threading.Event();self.failure=None;self.backend=None
        self.queue=deque();self.mutex=threading.Lock();self.busy=False;self.scheduled=False
        self.thread=threading.Thread(target=self.run,args=(factory,),name='augmentor-desktop-worker',daemon=True)
        self.thread.start()
        if not self.ready.wait(10):raise RuntimeError('Desktop worker initialization timed out.')
        if self.failure:raise RuntimeError('Desktop worker initialization failed.') from self.failure

    def run(self,factory):
        self.context=GLib.MainContext.new();self.context.push_thread_default()
        try:
            self.loop=GLib.MainLoop.new(self.context,False)
            try:self.backend=factory(self.context)
            except Exception as error:self.failure=error
            finally:self.ready.set()
            if self.failure is None:self.loop.run()
        finally:self.context.pop_thread_default()

    def submit(self,work):
        if not self.thread.is_alive():raise RuntimeError('Desktop worker is unavailable.')
        future=Future()
        with self.mutex:
            self.queue.append((work,future));self.schedule_locked()
        return future

    def schedule_locked(self):
        # Portal response waits pump this context. Never dispatch a second
        # operation from that nested loop while the first still owns resources.
        if self.busy or self.scheduled or not self.queue:return
        self.scheduled=True
        source=GLib.idle_source_new()
        source.set_callback(self.execute)
        source.attach(self.context)

    def execute(self,*_):
        with self.mutex:
            self.scheduled=False;self.busy=True;work,future=self.queue.popleft()
        try:
            if future.set_running_or_notify_cancel():
                try:future.set_result(work())
                except Exception as error:future.set_exception(error)
        finally:
            with self.mutex:self.busy=False;self.schedule_locked()
        return False

    def close(self):
        if not self.thread.is_alive():return
        self.submit(self.loop.quit)
        self.thread.join(2)
        if self.thread.is_alive():raise RuntimeError('Desktop worker did not finish cleanup.')
