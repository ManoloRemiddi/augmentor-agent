# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Access the shared OS mechanisms from the native presentation package."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]/'services'))
from platform_adapters.paths import private_directory, runtime_directory
from platform_adapters.transport import LocalSocket
