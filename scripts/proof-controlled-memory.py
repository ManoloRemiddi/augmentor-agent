#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Opt-in controlled-engine proof using synthetic data and a disposable engine.

Start the pinned installer with separate --name, --volume, --port and
--gateway-port and AUGMENTOR_SHARED_DATA. Pass that directory's hindsight.json.
Default uses a fixture model and injects a consolidation failure. --live uses
the configured real model within the ordinary memory budget. Prints metadata
only; no prompt, reasoning, credentials or existing conversation is read.
"""
import argparse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'services'))
from memory.hindsight import HindsightMemory
from memory.gateway import Gateway


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--configuration', type=Path, required=True)
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    config = json.loads(args.configuration.read_text())
    if config['endpoint'] == 'http://127.0.0.1:8889' or config['gatewayPort'] == 8890:
        parser.error('Use a disposable engine with separate data and non-production ports.')
    calls = []
    class Model(BaseHTTPRequestHandler):
        def log_message(self, *_): pass
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            calls.append(body['max_tokens'])
            if len(calls) > 3:
                self.send_response(500); self.end_headers(); return
            content = json.dumps({'facts': [{'what': 'Legacy archive sentinel.' if len(calls) == 1 else 'Atlas uses SQLite.', 'when': 'N/A',
                'where': 'N/A', 'who': 'N/A', 'why': 'N/A', 'fact_type': 'world'}]})
            raw = json.dumps({'id': 'fixture', 'object': 'chat.completion', 'created': 0,
                'model': 'fixture', 'choices': [{'index': 0, 'message': {'role': 'assistant',
                'content': content}, 'finish_reason': 'stop'}], 'usage': {'prompt_tokens': 10,
                'completion_tokens': 10, 'total_tokens': 20}}).encode()
            self.send_response(200); self.send_header('Content-Length', str(len(raw)))
            self.end_headers(); self.wfile.write(raw)
    server = None
    if not args.live:
        server = ThreadingHTTPServer(('127.0.0.1', 0), Model)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        config['modelUrl'] = f'http://127.0.0.1:{server.server_port}/v1'
    with tempfile.TemporaryDirectory() as directory:
        memory = HindsightMemory(Path(directory) / 'memory.sqlite3', config)
        gate = Gateway(('127.0.0.1', config['gatewayPort']), memory.processing.budget, config)
        threading.Thread(target=gate.serve_forever, daemon=True).start()
        sid = 'synthetic-controlled-proof-' + uuid.uuid4().hex
        def call(action, **params):
            return memory.call('memory.dual.' + action, {'session': sid, **params})
        call('bind', person=sid, cwd='/synthetic/atlas')
        call('activity', owner=sid, phase='tools')
        stop = threading.Event()
        def renew():
            while not stop.wait(2): call('activity', owner=sid, phase='tools')
        threading.Thread(target=renew, daemon=True).start()
        call('append', events=[{'id': '1', 'role': 'user', 'mode': 'text', 'live': True,
            'content': 'I prefer concise answers. Atlas uses SQLite. Inspect the launcher but do not start downloads.'}])
        started = time.monotonic()
        try:
            if not args.live:
                # An old, unconsolidated fact must survive a new batch untouched.
                # Seed it through the same engine, under a different source tag.
                memory.processing.prepare()
                with memory.connect() as db:
                    bank = json.loads(db.execute('SELECT stages FROM memory_jobs').fetchone()[0])[0]['bank']
                budget = memory.processing.budget
                token = budget.open('sentinel-' + sid, sid)
                tag = 'augmentor-job-' + '0' * 64
                sentinel = {'window': token, 'id': 'sentinel-' + sid, 'stage': 'retain', 'bank': bank, 'sourceTag': tag,
                    'items': [{'content': 'Legacy archive sentinel.', 'document_id': 'archive-sentinel',
                    'tags': [tag], 'observation_scopes': 'shared', 'update_mode': 'replace',
                    'timestamp': datetime.now(timezone.utc).isoformat()}]}
                try: assert memory.processing.stage(sentinel)['status'] == 'completed'
                finally: budget.close(token)
            for _ in range(10):
                memory.step()
                status = memory.processing.status()
                if status['jobs'].get('stopped') or status['jobs'].get('completed'): break
            assert memory.last_error is None, memory.last_error
            if args.live:
                recalled = call('recall')
                assert recalled['relationship']['items'] and recalled['work']['items'], 'Both scopes must cache facts'
                assert status['jobs'].get('completed') == 1, call('jobs')
                assert all(recalled[k]['summary'] for k in ('relationship', 'work'))
            else:
                assert len(calls) == 4 and status['jobs'].get('stopped') == 1
                for _ in range(5): memory.step()
                assert len(calls) == 4, 'A failed operation must not retry automatically'
                old = memory.api('GET', memory.route(bank, 'memories/list?document_id=archive-sentinel&consolidation_state=pending'))
                assert len(old['items']) == 1, 'New consolidation must not drain historical facts'
            call('activity', owner=sid, phase='stop')
            count = len(calls)
            for _ in range(5): memory.step()
            assert len(calls) == count and len(call('export')['events']) == 1
            print(json.dumps({'proof': 'PASS', 'live': args.live, 'elapsed': round(time.monotonic()-started, 2),
                              'jobs': call('jobs')['jobs'], 'fixtureCalls': len(calls)}))
        finally:
            stop.set(); call('activity', owner=sid, phase='stop')
            gate.shutdown(); gate.server_close()
            if server: server.shutdown(); server.server_close()


if __name__ == '__main__': main()
