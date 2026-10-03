# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual child-process bounds/cancellation; helper fixture establishes no trust."""
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'services'))
from updates.client import repository_request,node_executable


class UpdateClientTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);self.script=self.root/'services/updates/repository.mjs'
        self.script.parent.mkdir(parents=True)

    def call(self,**options):
        return repository_request(self.root,self.root/'cache',{'operation':'discover'},node=sys.executable,**options)

    def test_helper_json_progress_and_environment_are_bounded_without_preloads(self):
        self.script.write_text("import json,os,sys\nvalue=json.load(sys.stdin)\nprint(json.dumps({'bytes':12}),file=sys.stderr)\nprint(json.dumps({'preload':os.environ.get('NODE_OPTIONS'),'cache':value['cache']}))")
        progress=[];processes=[]
        with patch.dict(os.environ,{'NODE_OPTIONS':'inert fixture option'}):
            result=self.call(progress=progress.append,observed=processes.append)
        self.assertIsNone(result['preload']);self.assertEqual(progress,[12])
        self.assertEqual(result['cache'],str(self.root/'cache'))
        self.assertIsNotNone(processes[0].poll());self.assertIsNone(processes[-1])

    def test_oversized_stdout_stderr_timeout_and_cancellation_end_only_owned_child(self):
        for script,options,error in [
            ("print('x'*2100000)",{},ValueError),
            ("import sys;sys.stderr.write('x'*1000000)",{},ValueError),
            ("import time;time.sleep(10)",{'timeout':.05},TimeoutError),
            ("import time;time.sleep(10)",{'cancelled':threading.Event()},InterruptedError)]:
            with self.subTest(error=error):
                self.script.write_text(script);processes=[]
                def observed(process):
                    processes.append(process)
                    if process is not None and 'cancelled' in options:options['cancelled'].set()
                with self.assertRaises(error):self.call(observed=observed,**options)
                self.assertIsNotNone(processes[0].poll());self.assertIsNone(processes[-1])

    @staticmethod
    def cancelled():
        event=threading.Event();event.set();return event

    def test_deadline_also_bounds_a_child_that_never_reads_large_stdin(self):
        self.script.write_text('import time;time.sleep(10)')
        processes=[]
        with self.assertRaises(TimeoutError):
            repository_request(self.root,self.root/'cache',{'operation':'discover','padding':'x'*60000},
                node=sys.executable,timeout=.05,observed=processes.append)
        self.assertIsNotNone(processes[0].poll());self.assertIsNone(processes[-1])

    def test_installer_client_never_uses_an_environment_runtime_or_missing_bundle(self):
        with patch.dict(os.environ,{'AUGMENTOR_PI_NODE':sys.executable}):
            self.assertEqual(node_executable(self.root),Path(sys.executable))
            with self.assertRaisesRegex(ValueError,'bundled'):node_executable(self.root,require_bundled=True)

    def test_shared_cache_wait_is_bounded_and_cancellation_never_spawns_a_second_helper(self):
        self.script.write_text("import time,json,sys\njson.load(sys.stdin)\ntime.sleep(.3)\nprint('{}')")
        started=threading.Event();errors=[];first=[]
        def observed(process):
            first.append(process)
            if process is not None:started.set()
        def request():
            try:self.call(observed=observed)
            except Exception as error:errors.append(error)
        worker=threading.Thread(target=request);worker.start()
        try:
            self.assertTrue(started.wait(3));second=[]
            with self.assertRaisesRegex(TimeoutError,'cache is busy'):
                self.call(timeout=.05,observed=second.append)
            with self.assertRaises(InterruptedError):
                self.call(cancelled=self.cancelled(),observed=second.append)
            self.assertEqual(second,[])
        finally:worker.join(timeout=5)
        self.assertFalse(worker.is_alive());self.assertEqual(errors,[])
        self.assertIsNotNone(first[0].poll());self.assertIsNone(first[-1])
        self.assertEqual(self.call(),{})


if __name__=='__main__':unittest.main()
