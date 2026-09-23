# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import json
import io
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'services'))
from memory.dual import DualMemory
from memory.budget import InferenceBudget, BudgetDenied, JOB_SECONDS, JOB_TOKENS
from memory.gateway import Gateway, completion


class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.store = DualMemory(Path(self.tmp.name) / 'memory.sqlite3')
        self.now = 100
        self.budget = InferenceBudget(self.store.connect, lambda: self.now)

    def test_idle_reconnect_restart_and_expiry_grant_no_inference(self):
        with self.assertRaises(BudgetDenied): self.budget.open('job', 'session')
        self.budget.activity('session', 'owner', 'tools')
        token = self.budget.open('job', 'session')
        self.assertTrue(self.budget.valid(token))
        self.now += 7
        self.assertFalse(self.budget.valid(token))
        replacement = InferenceBudget(self.store.connect, lambda: self.now)
        with self.assertRaises(BudgetDenied): replacement.open('job', 'session')

    def test_foreground_in_another_window_revokes_and_cannot_revive_request(self):
        self.budget.activity('one', 'dsh', 'tools')
        token = self.budget.open('job', 'one')
        self.budget.activity('two', 'pi', 'foreground')
        self.assertFalse(self.budget.valid(token))
        self.budget.activity('two', 'pi', 'stop')
        self.assertFalse(self.budget.valid(token))
        self.budget.close(token)
        self.assertTrue(self.budget.allowed('one'))

    def test_renewals_and_restart_cannot_extend_absolute_processing_window(self):
        self.budget.activity('one', 'owner', 'tools')
        for _ in range(70):
            self.now += 2
            self.budget.activity('one', 'owner', 'tools')
        self.assertFalse(self.budget.allowed('one'))
        restarted = InferenceBudget(self.store.connect, lambda: self.now)
        restarted.activity('one', 'owner', 'tools')
        self.assertFalse(restarted.allowed('one'))
        restarted.activity('one', 'owner', 'stop')
        with self.assertRaises(ValueError): restarted.activity('one', 'owner', 'tools')
        restarted.activity('one', 'next-user-turn', 'tools')
        self.assertTrue(restarted.allowed('one'))

    def test_crash_reservations_and_failures_survive_new_windows_and_restart(self):
        self.budget.activity('one', 'dsh', 'tools')
        self.budget.open('job', 'one')
        charge = self.budget.reserve(1000, 200)
        restarted = InferenceBudget(self.store.connect, lambda: self.now)
        restarted.activity('one', 'new-owner', 'tools')
        restarted.open('job', 'one')
        with self.store.connect() as db:
            row = db.execute('SELECT * FROM memory_budgets').fetchone()
            self.assertEqual(row['seconds'], JOB_SECONDS-charge['seconds'])
            self.assertEqual(row['tokens'], JOB_TOKENS-1200)
        for _ in range(2):
            failed = restarted.reserve(1000, 200)
            restarted.settle(failed, failed=True)
        with self.assertRaises(BudgetDenied): restarted.reserve(1000)
        self.assertEqual(restarted.status()['stopped'], 1)

    def test_reboot_invalidates_old_monotonic_deadlines_and_foreground_still_blocks(self):
        self.budget.activity('one', 'old', 'tools')
        self.budget.boot = 'another-boot'
        with self.assertRaises(ValueError): self.budget.activity('one', 'old', 'tools')
        self.budget.activity('two', 'chat', 'foreground')
        self.now += 121
        self.budget.activity('two', 'chat', 'foreground')
        self.budget.activity('one', 'new', 'tools')
        self.assertFalse(self.budget.allowed('one'))

    def test_processing_pause_preserves_capture_and_survives_restart(self):
        self.store.call('memory.dual.bind', {'session': 'one'})
        self.budget.pause(True)
        self.store.call('memory.dual.append', {'session': 'one', 'events': [
            {'id': 'event', 'role': 'user', 'mode': 'text', 'content': 'Keep this original text.'}]})
        restarted = InferenceBudget(self.store.connect)
        self.assertTrue(restarted.status()['paused'])
        self.assertEqual(len(self.store.call('memory.dual.export', {'session': 'one'})['events']), 1)

    def test_gateway_denies_idle_caps_output_and_cancels_upstream_on_stop(self):
        calls = []
        received = threading.Event()
        disconnected = threading.Event()
        class Model(BaseHTTPRequestHandler):
            def log_message(self, *_): pass
            def do_POST(self):
                calls.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                received.set()
                self.connection.settimeout(3)
                if self.connection.recv(1) == b'': disconnected.set()
        model = ThreadingHTTPServer(('127.0.0.1', 0), Model)
        model.daemon_threads = True
        threading.Thread(target=model.serve_forever, daemon=True).start()
        self.addCleanup(model.server_close); self.addCleanup(model.shutdown)
        gate = Gateway(('127.0.0.1', 0), self.budget, {
            'modelUrl': f'http://127.0.0.1:{model.server_port}/v1', 'gatewayKey': 'x'*32})
        threading.Thread(target=gate.serve_forever, daemon=True).start()
        self.addCleanup(gate.server_close); self.addCleanup(gate.shutdown)
        def send():
            req = urllib.request.Request(f'http://127.0.0.1:{gate.server_port}/v1/chat/completions',
                data=json.dumps({'messages': [{'role': 'user', 'content': 'Fixture'}], 'max_tokens': 90000}).encode(),
                headers={'Authorization': 'Bearer '+'x'*32})
            try:
                with urllib.request.urlopen(req, timeout=4) as response: response.read()
            except urllib.error.HTTPError as error:
                return error.code
        self.assertEqual(send(), 409)
        self.assertEqual(calls, [])
        self.budget.activity('one', 'dsh', 'tools')
        self.budget.open('job', 'one')
        request = threading.Thread(target=send); request.start()
        self.assertTrue(received.wait(2))
        started = time.monotonic()
        self.budget.activity('one', 'dsh', 'stop')
        self.assertTrue(disconnected.wait(1), 'Stop must close the model socket promptly')
        self.assertLess(time.monotonic()-started, 1)
        request.join(2)
        self.assertFalse(request.is_alive())
        self.assertEqual(calls[0]['max_tokens'], 4096)
        self.assertTrue(calls[0]['stream'])

    def test_streamed_tool_fragments_usage_and_incomplete_outcome(self):
        class Response(io.BytesIO):
            def getheader(self, *args): return 'text/event-stream'
        chunks = [
            {'choices': [{'index': 0, 'delta': {'tool_calls': [{'index': 0, 'id': 'call-1', 'function': {'name': 'recall', 'arguments': '{'}}]}}]},
            {'choices': [{'index': 0, 'delta': {'tool_calls': [{'index': 0, 'function': {'arguments': '"query":"Atlas"}'}}]}, 'finish_reason': 'tool_calls'}]},
            {'choices': [], 'usage': {'total_tokens': 123}}]
        raw = b''.join(b'data: '+json.dumps(c).encode()+b'\n\n' for c in chunks)
        value = completion(Response(raw+b'data: [DONE]\n\n'))
        self.assertEqual(value['usage']['total_tokens'], 123)
        self.assertEqual(value['choices'][0]['message']['tool_calls'], [{'id': 'call-1', 'type': 'function', 'function': {'name': 'recall', 'arguments': '{"query":"Atlas"}'}}])
        with self.assertRaises(ValueError): completion(Response(raw))


if __name__ == '__main__': unittest.main()
