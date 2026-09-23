#!/usr/bin/env bash
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"
baseline_dir="${1:-$project_dir/outputs/baseline}"
candidate_dir="${AUGMENTOR_DEBIAN_ARTIFACTS:-$project_dir/outputs/debian}"
debian_image="$(python3 -c 'import json; print(json.load(open("release/runtime.json"))["debianImage"])')"
"${AUGMENTOR_CONTAINER_ENGINE:-podman}" run --rm \
  -v "$baseline_dir:/baseline:ro" \
  -v "$candidate_dir:/candidate:ro" \
  -v "$project_dir/release/lifecycle-proof.py:/proof/lifecycle-proof.py:ro" \
  "$debian_image" bash -c 'set -e
apt-get update > /tmp/apt-bootstrap.log
apt-get install -y --no-install-recommends python3 > /tmp/apt-python.log
exec python3 /proof/lifecycle-proof.py /baseline /candidate'
