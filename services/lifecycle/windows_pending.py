# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Refuse unfinished Windows updates; saved records never authorize actions."""
from pathlib import Path
from platform_adapters.private_files import require_directory


def require_clear(runtime):
    directory=Path(runtime).parent/'updates'
    try:directory.lstat()
    except FileNotFoundError:return
    require_directory(directory)
    try:(directory/'active.json').lstat()
    except FileNotFoundError:return
    raise RuntimeError('An unfinished Augmentor update needs verification before reopening the application.')
