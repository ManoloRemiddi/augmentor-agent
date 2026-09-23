# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Named windows share a harness but keep their UI/session state and IPC separate."""
import json
import os
import re
from pathlib import Path


def validate_name(value):
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,31}', value):
        raise ValueError('Window name must contain 1–32 lowercase letters, digits or hyphens, starting with a letter.')
    return value


def current_name():
    return validate_name(os.environ.get('AUGMENTOR_WINDOW_ID', 'main'))


def configure(name):
    os.environ['AUGMENTOR_WINDOW_ID'] = validate_name(name)


def scoped_path(path):
    path = Path(path)
    return path if current_name() == 'main' else path.with_name(f'{path.stem}.{current_name()}{path.suffix}')


def ipc_basename():
    return 'augmentor-linux-pi' + ('' if current_name() == 'main' else '-' + current_name())


def desktop_component(base):
    return base if current_name() == 'main' else base.removesuffix('.desktop') + '.' + current_name() + '.desktop'


def window_label():
    return 'Augmentor Agent' if current_name() == 'main' else 'Augmentor Agent · ' + ('Second window' if current_name() == 'secondary' else current_name())


def load_session(path):
    """A new named window inherits the selected model, never the primary chat."""
    path = Path(path)
    if path.exists() or current_name() == 'main':
        return json.loads(path.read_text())
    primary = path.with_name(path.name.replace('.' + current_name() + '.', '.', 1))
    data = json.loads(primary.read_text())
    return {'endpoint': data.get('endpoint'), 'selection': data.get('selection'), 'session': None}
