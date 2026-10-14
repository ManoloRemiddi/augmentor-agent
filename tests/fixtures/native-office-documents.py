#!/usr/bin/python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Produce independent Office test files in the caller's fresh private tree."""
from pathlib import Path
import importlib.util
import json
import sys

source = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('office_probe', source / 'release/office-rebuild/native-sandbox-probe.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
root = Path(sys.argv[1]).absolute()
if not root.is_dir() or list(root.iterdir()):
    raise RuntimeError('Use a fresh private fixture directory.')
result = []
for extension, (flat, office_filter, _pdf_filter) in probe.FORMATS.items():
    seed = root / ('authored-' + extension + '.' + flat)
    seed.write_bytes(probe.authored_document(flat))
    scratch = root / ('create-' + extension)
    probe.run(scratch, probe.office_command(scratch, seed, extension + ':' + office_filter))
    file = scratch / 'work/out' / ('source.' + extension)
    target = root / ('authored.' + extension)
    target.write_bytes(file.read_bytes())
    result.append({'extension': extension, 'file': str(target)})
print(json.dumps(result))
