#!/usr/bin/python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Opt-in Linux shared binding around an existing, explicit DSH command."""
import importlib.util
import os
from pathlib import Path
import sys


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def main(args):
    if sys.platform!='linux':raise ValueError('Managed DSH shared launch is qualified only on Linux.')
    if not args or not Path(args[0]).is_absolute() or not Path(args[0]).is_file():
        raise ValueError('Supply the existing absolute DSH executable and its original arguments.')
    launch=load('dsh_selected_launch',Path(__file__).with_name('desktop-launch.py'))
    with launch.launch_guard():
        selected=launch.configuration();root=Path(selected['root'])
        env={**os.environ,'AUGMENTOR_PYTHON':selected['python'],'AUGMENTOR_PI_NODE':selected['node'],
             'PYTHONDONTWRITEBYTECODE':'1','PI_TELEMETRY':'0','PI_SKIP_VERSION_CHECK':'1'}
        if 'sharedProfile' in selected:env=launch.shared_helper(root).environment(selected['sharedProfile'],env)
        # Retain PATH, NODE_OPTIONS/preloads, DSH_HOME, credentials, working
        # directory and argv. This wrapper neither chooses nor upgrades DSH.
        lifetime=load('dsh_managed_lifetime',root/'services/lifecycle/lease.py')
        lifetime.hold('runtime')
        os.execve(args[0],args,env)


if __name__=='__main__':
    try:main(sys.argv[1:])
    except Exception:
        # The executable/arguments/environment can contain private service
        # settings. Keep diagnostics bounded and do not echo those values.
        print('Augmentor DSH launch failed; check the recorded command, selected deployment and shared-store readiness.',file=sys.stderr)
        raise SystemExit(1)
