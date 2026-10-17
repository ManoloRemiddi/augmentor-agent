#!/usr/bin/python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Linux Native Messaging entrypoint following the same selected desktop build."""
import importlib.util
import os
from pathlib import Path
import sys


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def main(args):
    launch=load('managed_desktop_launch',Path(__file__).with_name('desktop-launch.py'))
    with launch.launch_guard():return run(launch,args)


def run(launch,args):
    selected=launch.configuration();root=Path(selected['root'])
    host=root/'apps/browser/native-host.mjs'
    if not host.is_file():raise RuntimeError('The selected deployment has no Browser companion.')
    env=launch.launch_environment(selected)
    for key in ('NODE_OPTIONS','NODE_PATH'):env.pop(key,None)
    # Preserve the same package lifetime contract as the system Browser entry.
    lease=load('managed_browser_lifetime',root/'services/lifecycle/lease.py')
    lease.hold('runtime')
    os.execve(selected['node'],[selected['node'],str(host),*args],env)


if __name__=='__main__':
    try:main(sys.argv[1:])
    except Exception as error:
        print('Augmentor Browser startup failed: '+str(error),file=sys.stderr)
        raise SystemExit(1)
