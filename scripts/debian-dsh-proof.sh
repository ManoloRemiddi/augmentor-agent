#!/usr/bin/env bash
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
# Qualify installed packages with an explicitly supplied, pinned DSH test host.
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"
: "${AUGMENTOR_DSH_TEST_ROOT:?Set the path to the pinned DSH package, including node_modules}"
export AUGMENTOR_DEBIAN_ARTIFACTS="${AUGMENTOR_DEBIAN_ARTIFACTS:-$project_dir/outputs/debian}"
python3 - <<'PY'
import hashlib,json,os
from pathlib import Path
host=Path(os.environ['AUGMENTOR_DSH_TEST_ROOT'])
assert json.loads((host/'package.json').read_text())['version']=='0.1.5-rc.1'
assert (host/'node_modules').is_dir()
root=Path(os.environ['AUGMENTOR_DEBIAN_ARTIFACTS'])
manifest=json.loads((root/'artifacts.json').read_text())
assert manifest['version']==json.loads(Path('package.json').read_text())['version']
for item in manifest['artifacts']:
    assert Path(item['file']).name==item['file']
    with (root/item['file']).open('rb') as stream:
        assert hashlib.file_digest(stream,'sha256').hexdigest()==item['sha256']
PY
picker_args=()
if [[ -n "${AUGMENTOR_DSH_PICKER_ROOT:-}" ]]; then
  test -f "$AUGMENTOR_DSH_PICKER_ROOT/lib/index.js"
  test -d "$AUGMENTOR_DSH_PICKER_ROOT/node_modules"
  picker_args=(-v "$AUGMENTOR_DSH_PICKER_ROOT:/picker:ro" -e AUGMENTOR_PROOF_MODEL_PICKER=/picker -e AUGMENTOR_PROOF_PICKER_UI=1)
fi
version="$(python3 -c 'import json; print(json.load(open("package.json"))["version"])')"
debian_image="$(python3 -c 'import json; print(json.load(open("release/runtime.json"))["debianImage"])')"
"${AUGMENTOR_CONTAINER_ENGINE:-podman}" run --rm "${picker_args[@]}" \
  -e AUGMENTOR_PROOF_EXISTING_PROMPTS="${AUGMENTOR_PROOF_EXISTING_PROMPTS:-}" \
  -e AUGMENTOR_PROOF_CUSTOM_COMPACTION="${AUGMENTOR_PROOF_CUSTOM_COMPACTION:-}" \
  -v "$AUGMENTOR_DEBIAN_ARTIFACTS:/artifacts:ro" \
  -v "$AUGMENTOR_DSH_TEST_ROOT:/dsh:ro" \
  -v "$project_dir/scripts:/proof/scripts:ro" \
  -v "$project_dir/tests/fixtures/dsh-approval.mjs:/proof/fixtures/dsh-approval.mjs:ro" \
  -v "$project_dir/release/prove-debian-dsh.sh:/proof/run.sh:ro" \
  "$debian_image" bash /proof/run.sh "$version"
