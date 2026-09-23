#!/usr/bin/env bash
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
# Container-only harness acceptance; the pinned DSH fixture is mounted read-only.
set -euo pipefail
test -f /run/.containerenv || test -f /.dockerenv
version="$1"
export DEBIAN_FRONTEND=noninteractive
apt-get update > /tmp/apt-update.log
apt-get install -y --no-install-recommends \
  "/artifacts/augmentor-runtime_${version}_amd64.deb" \
  "/artifacts/augmentor-desktop_${version}_amd64.deb" \
  python3-pyside6.qttest > /tmp/apt-install.log
useradd --create-home beta
ln -s /dsh/lib/bin.js /usr/local/bin/dsh
mkdir -p /home/beta/proof/scripts /home/beta/proof/tests/fixtures /home/beta/proof/outputs
cp /proof/scripts/dsh-setup-proof.py /proof/scripts/proof_dsh_approvals.py /home/beta/proof/scripts/
cp /proof/fixtures/dsh-approval.mjs /home/beta/proof/tests/fixtures/
chown -R beta:beta /home/beta/proof
runuser -u beta -- env \
  PATH=/usr/lib/augmentor/node/bin:/usr/local/bin:/usr/bin:/bin \
  DSH_TEST_MODULES=/dsh/node_modules AUGMENTOR_PROOF_APP_ROOT=/usr/lib/augmentor \
  AUGMENTOR_PROOF_MODEL_PICKER="${AUGMENTOR_PROOF_MODEL_PICKER:-}" AUGMENTOR_PROOF_PICKER_UI="${AUGMENTOR_PROOF_PICKER_UI:-}" \
  AUGMENTOR_PROOF_EXISTING_PROMPTS="${AUGMENTOR_PROOF_EXISTING_PROMPTS:-}" \
  AUGMENTOR_PROOF_CUSTOM_COMPACTION="${AUGMENTOR_PROOF_CUSTOM_COMPACTION:-}" \
  AUGMENTOR_PROOF_APPROVALS=1 AUGMENTOR_PROOF_INTERACTIONS=1 AUGMENTOR_PROOF_EXACT_FORK=1 \
  PYTHONDONTWRITEBYTECODE=1 QT_QPA_PLATFORM=offscreen \
  python3 -B /home/beta/proof/scripts/dsh-setup-proof.py
