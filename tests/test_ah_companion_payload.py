# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""The Qt-free companion must retain its actual AH resolver/transport imports."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

class CompanionPayloadTests(unittest.TestCase):
    def test_restricted_packaged_native_subset_imports_ah_without_qt(self):
        spec=importlib.util.spec_from_file_location('mac_package',ROOT/'scripts/package-macos.py')
        package=importlib.util.module_from_spec(spec);spec.loader.exec_module(package)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);native=root/'apps/native/augmentor_linux';native.mkdir(parents=True)
            for name in package.COMPANION_NATIVE_MODULES:shutil.copy2(ROOT/'apps/native/augmentor_linux'/name,native/name)
            shutil.copytree(ROOT/'services/platform_adapters',root/'services/platform_adapters')
            script=root/'check.py';script.write_text("import sys\nsys.path.insert(0,"+repr(str(native.parent))+")\nimport augmentor_linux.ah_connection, augmentor_linux.pi_client, augmentor_linux.prompt_client\nassert not any(k.startswith('PySide6') for k in sys.modules)\n")
            subprocess.run([sys.executable,'-I','-B',str(script)],check=True,capture_output=True)
