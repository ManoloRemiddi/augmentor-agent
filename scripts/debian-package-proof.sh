#!/usr/bin/env bash
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"
version="$(python3 -c 'import json; print(json.load(open("package.json"))["version"])')"
debian_image="$(python3 -c 'import json; print(json.load(open("release/runtime.json"))["debianImage"])')"
container_engine="${AUGMENTOR_CONTAINER_ENGINE:-podman}"
export AUGMENTOR_DEBIAN_ARTIFACTS="${AUGMENTOR_DEBIAN_ARTIFACTS:-$project_dir/outputs/debian}"
python3 - <<'PY'
import hashlib, json, os
from pathlib import Path
root = Path(os.environ['AUGMENTOR_DEBIAN_ARTIFACTS'])
manifest = json.loads((root / 'artifacts.json').read_text())
assert manifest['version'] == json.loads(Path('package.json').read_text())['version']
for item in manifest['artifacts']:
    assert Path(item['file']).name == item['file']
    with (root / item['file']).open('rb') as stream:
        assert hashlib.file_digest(stream, 'sha256').hexdigest() == item['sha256'], item['file']
PY
"$container_engine" run --rm \
  -v "$AUGMENTOR_DEBIAN_ARTIFACTS:/artifacts:ro" \
  -v "$project_dir/scripts/installed-runtime-proof.py:/proof/installed-runtime-proof.py:ro" \
  -v "$project_dir/release/prove-debian-container.sh:/proof/run.sh:ro" \
  "$debian_image" bash /proof/run.sh "$version"
