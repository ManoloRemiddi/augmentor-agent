#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Use the shared first-run DSH transaction with the Windows component owner."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'services'))
from dsh import managed
from platform_adapters.private_files import read_json, require_directory
from windows_supervisor import LABEL, ManagedAgent, managed_directory


def provision(root, state, request, **kwargs):
    return managed.provision(root, state, request, agent=ManagedAgent(root, state),
                             manager_type='windows-supervisor', **kwargs)


def start_saved(saved):
    manager = saved.get('managed', {})
    if manager.get('type') != 'windows-supervisor' or manager.get('label') != LABEL:
        raise ValueError('Unrecognized managed DSH owner.')
    state = managed_directory(); require_directory(state)
    record = read_json(state/'setup.json')
    if (manager.get('state') != str(state) or record.get('schema') != managed.SCHEMA or
            record.get('status') != 'ready' or record.get('appRoot') != str(ROOT) or
            record.get('home') != saved.get('home') or record.get('endpoint') != saved.get('endpoint')):
        raise ValueError('The managed DSH ownership record does not match this connection.')
    agent = ManagedAgent(ROOT, state)
    if not agent.owned(): raise ValueError('The managed DSH owner is missing. Its data was preserved.')
    agent.start()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--progress', action='store_true')
    args = parser.parse_args()
    if sys.platform != 'win32': parser.error('This setup requires Windows.')
    # The product launcher supplies private known-folder paths. Fail rather than
    # provisioning into a guessed location when launched outside that contract.
    if not os.environ.get('XDG_DATA_HOME'): raise SystemExit('Open the installed Augmentor application to set it up.')
    try:
        raw = sys.stdin.buffer.read(16385)
        if len(raw) > 16384: raise ValueError('Setup request exceeds its size limit.')
        request = json.loads(raw)
        if not isinstance(request, dict): raise ValueError('Invalid setup request.')
        def progress(phase):
            if args.progress: print(json.dumps({'phase': phase}), flush=True)
        result = provision(ROOT, managed_directory(), request, progress=progress)
        print(json.dumps({'ok': True, **result}))
    except Exception as error:
        print(json.dumps({'ok': False, 'error': str(error) if isinstance(error, ValueError) else
            'Setup could not finish. Its private data was retained for diagnosis and retry.'}))
        raise SystemExit(1)


if __name__ == '__main__': main()
