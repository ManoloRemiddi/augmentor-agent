# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Discover shared maintenance where the existing prompt/memory services bind."""
import os
from pathlib import Path


def shared_state_directory():
    # Match prompt-library.service.paths and memory.service configuration,
    # including the installed Mac launcher's XDG environment. Socket runtime
    # and persistent shared state are distinct locations.
    result=Path(os.environ.get('AUGMENTOR_SHARED_STATE',
        Path(os.environ.get('XDG_STATE_HOME',Path.home()/'.local/state'))/'augmentor'))
    if not result.is_absolute():raise ValueError('Shared maintenance requires an absolute existing state location.')
    return result
