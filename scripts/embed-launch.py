#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Launch the Browser embedding service from the selected immutable product."""
import json
import importlib.util
import os
from pathlib import Path
import sys


def main():
    selected=Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local/share'))/'augmentor/desktop.json'
    config=json.loads(selected.read_text())
    bootstrap=Path(__file__).with_name('desktop-launch.py')
    if not bootstrap.is_file():bootstrap=Path(config['root'])/'scripts/desktop-launch.py'
    spec=importlib.util.spec_from_file_location('embedding_selected_launch',bootstrap)
    launch=importlib.util.module_from_spec(spec);spec.loader.exec_module(launch)
    # Keep the reader through Python's SDK adapter and Node exec. Even an idle
    # server can spawn a shared client, so its entire lifetime blocks rebinding.
    with launch.launch_guard():
        config=launch.configuration();root=Path(config['root'])
        entry=root/'apps/browser/embed/server.mjs'
        if not entry.is_file():raise RuntimeError('The selected deployment has no embedding service.')
        env=launch.launch_environment(config)
        for key in ('NODE_OPTIONS','NODE_PATH'):env.pop(key,None)
        adapter=root/'scripts/app-sdk-launch.py'
        if adapter.is_file():os.execve(config['python'],[config['python'],'-I','-B',str(adapter),'embed'],env)
        else:os.execve(config['node'],[config['node'],str(entry)],env)


if __name__=='__main__':
    try:main()
    except Exception as error:
        print('Augmentor embedding startup failed: '+str(error),file=sys.stderr)
        raise SystemExit(1)
