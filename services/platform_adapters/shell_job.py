#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Private stdio lease for one approved Windows command and its owned Job.

The existing OwnedProcess assigns its isolated worker before any workload runs.
Only this supervisor retains the unnamed kill-on-close Job handle. Command text
arrives through stdin; target output is framed separately and cannot forge a
control receipt. EOF/cancel stops the range; no saved PID is ever adopted.
"""
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

VERSION = 'augmentor-shell-job/1'
MAX_FRAME = 65536
WORKLOAD_READY = b'augmentor-contained-shell/1\n'


def command_request(raw):
    if not raw or len(raw) > MAX_FRAME or not raw.endswith(b'\n'):
        raise ValueError('Invalid bounded command request.')
    value = json.loads(raw.decode('utf-8'))
    if not isinstance(value, dict) or set(value) != {'version', 'command'} or value['version'] != VERSION:
        raise ValueError('Invalid command protocol.')
    command = value['command']
    if not isinstance(command, str) or not command.strip() or '\0' in command or len(command.encode('utf-8')) > 16384:
        raise ValueError('Invalid bounded command text.')
    return command


def workload():
    # process_worker.py has assigned this process before launching it. The
    # supervisor reads this private first frame before releasing command text.
    sys.stdout.buffer.write(WORKLOAD_READY); sys.stdout.buffer.flush()
    command = command_request(sys.stdin.buffer.readline(MAX_FRAME+1))
    executable, invocation = cmd_invocation(command)
    child = subprocess.Popen(invocation,
        executable=executable, creationflags=subprocess.CREATE_NO_WINDOW,
        stdin=subprocess.DEVNULL, stdout=sys.stdout, stderr=sys.stderr, close_fds=True)
    return child.wait()


def cmd_invocation(command):
    executable = os.path.join(os.environ['SystemRoot'], 'System32', 'cmd.exe')
    # /s removes only these outer quotes, preserving the approved command's own
    # quoting/operators. No C-runtime argv escaping is applied to CMD text.
    invocation = '"'+executable+'" /d /s /c "'+command+'"'
    if len(invocation.encode('utf-16-le'))//2 > 8191:
        raise ValueError('Command exceeds the Windows CMD limit.')
    return executable, invocation


def supervisor():
    from platform_adapters.processes import OwnedProcess
    owned = None
    stop = threading.Event()
    output_lock = threading.Lock()
    output_threads = []
    output_failed = threading.Event()
    dispatched = False
    # The lease may be blocked while a command exits naturally. Read raw stdin
    # so Python shutdown never waits for a daemon-held BufferedReader lock.
    input_stream = os.fdopen(sys.stdin.fileno(), 'rb', buffering=0, closefd=False)
    def emit(kind, **data):
        raw = (json.dumps({'version': VERSION, 'type': kind, **data}, ensure_ascii=True)+'\n').encode('ascii')
        with output_lock:
            try: sys.stdout.buffer.write(raw); sys.stdout.buffer.flush()
            except (BrokenPipeError, OSError): stop.set()
    def lease():
        try:
            while True:
                raw = input_stream.readline(MAX_FRAME+1)
                if not raw: break
                value = json.loads(raw.decode('utf-8')) if len(raw) <= MAX_FRAME and raw.endswith(b'\n') else None
                if value != {'version': VERSION, 'type': 'cancel'}: break
                stop.set(); return
        except (ValueError, OSError): pass
        stop.set()
    def output(channel, stream):
        try:
            while True:
                raw = os.read(stream.fileno(), 4096)
                if not raw: break
                emit('output', channel=channel, data=base64.b64encode(raw).decode('ascii'))
        except OSError: output_failed.set(); stop.set()
        finally: stream.close()
    try:
        command = command_request(input_stream.readline(MAX_FRAME+1))
        cmd_invocation(command)  # Refuse CMD overflow before releasing any work.
        thread = threading.Thread(target=lease, daemon=True); thread.start()
        if stop.is_set():
            emit('settled', state='cancelled', drained=True); return 0
        owned = OwnedProcess([sys.executable, '-I', '-Xutf8', '-B', str(Path(__file__).resolve()), '--workload'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        arrived = threading.Event()
        greeting = []
        def receive_ready():
            try: greeting.append(owned.process.stdout.readline(len(WORKLOAD_READY)+1))
            except OSError: greeting.append(None)
            finally: arrived.set()
        threading.Thread(target=receive_ready, daemon=True).start()
        bootstrap_deadline = time.monotonic()+10
        while not arrived.wait(.02):
            if stop.is_set() or time.monotonic() >= bootstrap_deadline:
                owned.terminate()
                if not arrived.wait(3):
                    emit('settled', state='unknown', drained=False); return 0
        if greeting != [WORKLOAD_READY]:
            raise RuntimeError('Contained workload did not confirm readiness.')
        emit('ready', range='windows-job', boundary='assigned-before-workload')
        for channel in ('stdout', 'stderr'):
            thread = threading.Thread(target=output, args=(channel, getattr(owned.process, channel)), daemon=True)
            thread.start(); output_threads.append(thread)
        if stop.is_set(): owned.terminate()
        else:
            dispatched = True
            owned.process.stdin.write((json.dumps({'version': VERSION, 'command': command}, ensure_ascii=False)+'\n').encode('utf-8'))
            owned.process.stdin.close()
        stopped = False
        deadline = None
        while not owned.drained():
            if stop.is_set() and not stopped:
                stopped = True; deadline = time.monotonic()+3
                owned.terminate()
            if deadline is not None and time.monotonic() >= deadline:
                owned.close()
                emit('settled', state='unknown', drained=False); return 0
            time.sleep(.02)
        code = owned.wait_graceful(timeout=0)
        for thread in output_threads: thread.join(timeout=.5)
        if output_failed.is_set() or any(thread.is_alive() for thread in output_threads):
            emit('settled', state='unknown', drained=True, exitCode=code); return 0
        emit('settled', state='cancelled' if stop.is_set() else 'completed' if code == 0 else 'failed', drained=True, exitCode=code)
        return 0
    except BaseException:
        emit('settled', state='unknown' if dispatched else 'failed', drained=False)
        return 0
    finally:
        if owned is not None:
            try:
                if not owned.drained(): owned.terminate()
            finally: owned.close()


if __name__ == '__main__':
    if sys.platform != 'win32': raise SystemExit('Owned Windows shell commands require Windows.')
    if sys.argv[1:] == ['--workload']: raise SystemExit(workload())
    if sys.argv[1:]: raise SystemExit('Invalid owned shell invocation.')
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    raise SystemExit(supervisor())
