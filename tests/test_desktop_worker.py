# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real private GLib scheduling; never dispatch cleanup into a pending operation."""
import importlib.util
from pathlib import Path
import threading
import time
import unittest
try:from gi.repository import GLib
except ImportError:GLib=None
from PySide6.QtCore import QCoreApplication,QEventLoop,QTimer

spec=importlib.util.spec_from_file_location('desktop_worker',Path(__file__).resolve().parents[1]/'services/desktop/worker.py')
module=importlib.util.module_from_spec(spec)
if GLib is not None:spec.loader.exec_module(module)


@unittest.skipIf(GLib is None,'Linux GLib runtime required.')
class DesktopWorkerTests(unittest.TestCase):
    def test_qt_timer_and_stop_remain_responsive_while_worker_waits(self):
        app=QCoreApplication.instance() or QCoreApplication([])
        worker=module.Worker(lambda context:None);self.addCleanup(worker.close)
        stop=threading.Event();entered=threading.Event();ticks=[]
        def request():
            entered.set()
            while not stop.wait(.001):
                while worker.context.pending():worker.context.iteration(False)
        pending=worker.submit(request);self.assertTrue(entered.wait(1))
        loop=QEventLoop();timer=QTimer();timer.setInterval(5);timer.timeout.connect(lambda:ticks.append(True));timer.start()
        QTimer.singleShot(60,lambda:(stop.set(),loop.quit()))
        loop.exec();timer.stop();pending.result(1)
        self.assertGreaterEqual(len(ticks),3)

    def test_worker_owns_context_and_serializes_nested_response_wait(self):
        worker=module.Worker(lambda context:(threading.get_ident(),GLib.MainContext.get_thread_default()==context))
        self.addCleanup(worker.close)
        self.assertNotEqual(worker.backend[0],threading.get_ident());self.assertTrue(worker.backend[1])
        entered=threading.Event();release=threading.Event();events=[]
        def pending_request():
            events.append('request');entered.set()
            deadline=time.monotonic()+2
            while not release.is_set() and time.monotonic()<deadline:
                while worker.context.pending():worker.context.iteration(False)
                time.sleep(.001)
            events.append('response')
        first=worker.submit(pending_request);self.assertTrue(entered.wait(1))
        cleanup=worker.submit(lambda:events.append('cleanup'))
        time.sleep(.03);self.assertFalse(cleanup.done());self.assertEqual(events,['request'])
        release.set();first.result(1);cleanup.result(1)
        self.assertEqual(events,['request','response','cleanup'])

    def test_failed_operation_does_not_drop_next_cleanup(self):
        worker=module.Worker(lambda context:None);self.addCleanup(worker.close)
        def failure():raise ValueError('fixture error')
        with self.assertRaisesRegex(ValueError,'fixture error'):worker.submit(failure).result(1)
        self.assertEqual(worker.submit(lambda:threading.get_ident()).result(1),worker.thread.ident)

    def test_factory_failure_and_closed_worker_are_explicit(self):
        def failure(context):raise ValueError('fixture initialization')
        with self.assertRaisesRegex(RuntimeError,'initialization failed'):module.Worker(failure)
        worker=module.Worker(lambda context:None);worker.close();worker.close()
        with self.assertRaisesRegex(RuntimeError,'unavailable'):worker.submit(lambda:None)
