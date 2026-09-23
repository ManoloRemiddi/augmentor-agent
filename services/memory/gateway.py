# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Memory-only model gateway. Chat/voice model endpoints are never changed.

The pinned Hindsight instance uses this endpoint for every generative stage.
Closed admission means no upstream connection, including startup verification
and retries. Cancellation closes the upstream socket; no request is replayed.
"""
import hmac
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
import socket
import threading
from urllib.parse import urlsplit

from memory.budget import BudgetDenied


def completion(response):
    """Collect SSE without exposing chunks; streaming enables server cancellation.

    Tool names, IDs and arguments may arrive in separate deltas. Preserve their
    original indices and never try to repair or execute model output here.
    """
    if 'text/event-stream' not in response.getheader('Content-Type', ''):
        raw = response.read(2 * 1024 * 1024 + 1)
        if len(raw) > 2 * 1024 * 1024: raise ValueError('Memory model response too large')
        return json.loads(raw)
    result, choices, size, done = {}, {}, 0, False
    while True:
        line = response.readline(2 * 1024 * 1024 + 1)
        if not line: break
        size += len(line)
        if size > 2 * 1024 * 1024: raise ValueError('Memory model response too large')
        if not line.startswith(b'data:'): continue
        raw = line[5:].strip()
        if raw == b'[DONE]': done = True; break
        value = json.loads(raw)
        for key in ('id', 'model', 'created', 'usage'):
            if value.get(key) is not None: result[key] = value[key]
        for part in value.get('choices', []):
            index = part.get('index', 0)
            choice = choices.setdefault(index, {'index': index, 'message': {'role': 'assistant', 'content': ''}, 'finish_reason': None})
            message, delta = choice['message'], part.get('delta', {})
            for key in ('content', 'reasoning_content', 'reasoning'):
                if isinstance(delta.get(key), str): message[key] = message.get(key, '') + delta[key]
            for call in delta.get('tool_calls', []):
                calls = message.setdefault('tool_calls', {})
                current = calls.setdefault(call['index'], {'id': '', 'type': 'function', 'function': {'name': '', 'arguments': ''}})
                for key in ('id',):
                    if call.get(key): current[key] += call[key]
                if call.get('type'): current['type'] = call['type']
                for key in ('name', 'arguments'):
                    if call.get('function', {}).get(key): current['function'][key] += call['function'][key]
            if part.get('finish_reason') is not None: choice['finish_reason'] = part['finish_reason']
    if not done or not choices or any(c['finish_reason'] is None for c in choices.values()):
        raise ValueError('Memory model stream ended without a complete outcome')
    for choice in choices.values():
        message = choice['message']
        if 'tool_calls' in message:
            message['tool_calls'] = [v for _, v in sorted(message['tool_calls'].items())]
    return {**result, 'object': 'chat.completion', 'choices': [v for _, v in sorted(choices.items())]}


class Gateway(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, budget, configuration):
        url = urlsplit(configuration['modelUrl'])
        if (url.scheme != 'http' or not ipaddress.ip_address(url.hostname).is_loopback or
                url.username or url.password or url.query or url.fragment):
            raise ValueError('Memory gateway requires a numeric loopback HTTP model endpoint.')
        self.target = url
        self.key = configuration['gatewayKey']
        if not isinstance(self.key, str) or len(self.key) < 32:
            raise ValueError('Missing private memory gateway credential.')
        self.model_key = configuration.get('modelKey', 'local')
        self.budget = budget
        self.single = threading.Lock()
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass  # Never log prompts, credentials or provider bodies.

    def answer(self, status, value):
        raw = json.dumps(value).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        try:
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        if self.path != '/window' or not hmac.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + self.server.key):
            return self.answer(403, {'allowed': False})
        token = self.headers.get('X-Augmentor-Window', '')
        return self.answer(200, {'allowed': self.server.budget.valid(token)})

    def do_POST(self):
        self.connection.settimeout(5)
        if self.path != '/v1/chat/completions':
            return self.answer(404, {'error': {'message': 'Unsupported memory model route'}})
        if not hmac.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + self.server.key):
            return self.answer(403, {'error': {'message': 'Memory gateway credential required'}})
        if not self.server.single.acquire(blocking=False):
            return self.answer(429, {'error': {'message': 'A memory model request is already active'}})
        reservation = None
        connection = None
        finished = threading.Event()
        usage = None
        failed = False
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 128000:
                raise ValueError('Memory model request exceeds its input limit')
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError('Incomplete memory model request')
            body = json.loads(raw)
            # Images/audio are deliberately unsupported in background memory.
            if not isinstance(body.get('messages'), list) or any(
                    not isinstance(m.get('content'), (str, type(None))) for m in body['messages']):
                raise ValueError('Memory inference accepts text messages only')
            output = body.get('max_completion_tokens', body.get('max_tokens'))
            if output is not None and (type(output) is not int or output <= 0):
                raise ValueError('Invalid completion token limit')
            reservation = self.server.budget.reserve(len(raw) + 512, output)
            body.pop('max_completion_tokens', None)
            body['max_tokens'] = reservation['output']
            body['stream'] = True
            body['stream_options'] = {'include_usage': True}
            url = self.server.target
            connection = http.client.HTTPConnection(url.hostname, url.port, timeout=reservation['seconds'])
            connection.connect()
            upstream_socket = connection.sock

            def watch():
                while not finished.wait(.1):
                    if (not self.server.budget.valid(reservation['token']) or
                            self.server.budget.clock() >= reservation['deadline']):
                        try:
                            upstream_socket.shutdown(socket.SHUT_RDWR)
                        except OSError:
                            pass
                        return

            watcher = threading.Thread(target=watch, daemon=True)
            watcher.start()
            connection.request('POST', url.path.rstrip('/') + '/chat/completions', json.dumps(body).encode(),
                               {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self.server.model_key})
            response = connection.getresponse()
            if response.status != 200:
                raise ValueError('Memory model request failed')
            value = completion(response)
            usage = value.get('usage', {}).get('total_tokens')
            if not self.server.budget.valid(reservation['token']):
                raise BudgetDenied('Memory activity ended; model response discarded')
            self.answer(200, value)
        except BudgetDenied as error:
            self.answer(409, {'error': {'message': str(error)}})
        except Exception:
            failed = bool(reservation and self.server.budget.valid(reservation['token']))
            self.answer(503, {'error': {'message': 'Memory generation stopped or failed; previous memory is preserved'}})
        finally:
            finished.set()
            if connection:
                connection.close()
            if reservation:
                self.server.budget.settle(reservation, usage, failed)
            self.server.single.release()
