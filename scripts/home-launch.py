#!/usr/bin/python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Launch Home from the selected desktop release, without starting an AI session."""
import json
import os
from pathlib import Path
import sys


def main(args):
    data = Path(os.environ.get('XDG_DATA_HOME', Path.home()/'.local/share'))
    selected = json.loads((data/'augmentor/desktop.json').read_text())
    root = Path(selected['root'])
    if not (root/'apps/native/augmentor_linux/home_tray.py').is_file():
        raise RuntimeError('The selected Augmentor release has no Home launcher. Select a Home-enabled release.')
    env = {**os.environ, 'PYTHONPATH': str(root/'apps/native'), 'PYTHONDONTWRITEBYTECODE': '1'}
    os.execve(selected['python'], [selected['python'], '-m', 'augmentor_linux.home_tray', *args], env)


if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except Exception as error:
        print('Augmentor Home: '+str(error), file=sys.stderr)
        raise SystemExit(1)
