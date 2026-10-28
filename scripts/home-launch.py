#!/usr/bin/python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Launch Home from the selected desktop release, without starting an AI session."""
import importlib.util
import os
from pathlib import Path
import sys


def main(args):
    path=Path(__file__).with_name('desktop-launch.py')
    if not path.is_file():raise RuntimeError('Install the managed Desktop startup helpers before the Home launcher.')
    spec=importlib.util.spec_from_file_location('managed_home_launch',path)
    launch=importlib.util.module_from_spec(spec);spec.loader.exec_module(launch)
    with launch.launch_guard():return run(launch,args)


def run(launch,args):
    selected=launch.configuration()
    root = Path(selected['root'])
    if not (root/'apps/native/augmentor_linux/home_tray.py').is_file():
        raise RuntimeError('The selected Augmentor release has no Home launcher. Select a Home-enabled release.')
    env = {**os.environ, 'PYTHONPATH': str(root/'apps/native'), 'PYTHONDONTWRITEBYTECODE': '1'}
    if 'sharedProfile' in selected:env=launch.shared_helper(root).environment(selected['sharedProfile'],env)
    os.execve(selected['python'], [selected['python'], '-m', 'augmentor_linux.home_tray', *args], env)


if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except Exception as error:
        print('Augmentor Home: '+str(error), file=sys.stderr)
        raise SystemExit(1)
