#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Inspect or explicitly run bounded memory maintenance without a model agent."""
import argparse
import json
import os
from pathlib import Path
import socket
import time
import uuid


def call(action, **params):
    state = Path(os.environ.get('AUGMENTOR_SHARED_STATE', Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local/state')) / 'augmentor'))
    request = {'protocol': 'augmentor-prompts/1', 'id': uuid.uuid4().hex,
               'method': 'memory.dual.' + action, 'params': params}
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(5)
        client.connect(str(state / 'dual-memory.sock'))
        client.sendall((json.dumps(request) + '\n').encode())
        with client.makefile('rb') as stream:
            value = json.loads(stream.readline(1024 * 1024))
    if 'error' in value:
        raise ValueError(value['error']['message'])
    return value['result']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('status', 'pause', 'resume'): sub.add_parser(name)
    for name in ('jobs', 'import', 'retry', 'run'):
        command = sub.add_parser(name)
        command.add_argument('--session', required=True, help='Exact bound dsh: or pi: session ID')
        if name == 'import':
            command.add_argument('--after', type=int, required=True)
            command.add_argument('--through', type=int, required=True)
        if name == 'retry':
            command.add_argument('--job', required=True)
            command.add_argument('--reviewed', action='store_true', help='Acknowledge review of the failed/unknown stage; does not reset its budget')
        if name == 'run':
            command.add_argument('--seconds', type=int, default=120, help='Explicit maintenance window, 1–120 seconds')
    args = parser.parse_args()
    if args.command == 'status': result = call('describe')
    elif args.command in ('pause', 'resume'): result = call('processing', paused=args.command == 'pause')
    elif args.command == 'jobs': result = call('jobs', session=args.session)
    elif args.command == 'import': result = call('import', session=args.session, after=args.after, through=args.through)
    elif args.command == 'retry': result = call('retry', session=args.session, job=args.job, reviewed=args.reviewed)
    else:
        if not 1 <= args.seconds <= 120: parser.error('Choose a window of 1–120 seconds.')
        status = call('describe')
        if not status['enabled'] or status['processing']['paused']:
            raise ValueError('Memory capture or processing is paused; resume it explicitly before running maintenance.')
        owner = 'maintenance:' + uuid.uuid4().hex
        deadline = time.monotonic() + args.seconds
        try:
            while time.monotonic() < deadline:
                call('activity', session=args.session, owner=owner, phase='tools')
                time.sleep(min(2, max(0, deadline - time.monotonic())))
        finally:
            call('activity', session=args.session, owner=owner, phase='stop')
        result = call('jobs', session=args.session)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(str(error)) from None
