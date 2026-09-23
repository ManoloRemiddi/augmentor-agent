#!/usr/bin/env bash
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
# Runs inside an ephemeral Debian container; never invoke on the host OS.
set -euo pipefail
trap 'code=$?; for log in /tmp/apt-*.log; do tail -60 "$log" >&2; done; exit "$code"' ERR
test -f /run/.containerenv || test -f /.dockerenv
version="$1"
export DEBIAN_FRONTEND=noninteractive
apt-get update > /tmp/apt-update.log
apt-get install -y --no-install-recommends "/artifacts/augmentor-runtime_${version}_amd64.deb" > /tmp/apt-runtime.log
useradd --create-home beta
runuser -u beta -- python3 /proof/installed-runtime-proof.py
apt-get install -y --no-install-recommends "/artifacts/augmentor-desktop_${version}_amd64.deb" > /tmp/apt-desktop.log
runuser -u beta -- env QT_QPA_PLATFORM=offscreen augmentor-agent --preview --screenshot /home/beta/preview.png
test -s /home/beta/preview.png
# Test-only GUI driver dependencies are added after the runtime/desktop install
# assertions so they cannot hide an undeclared application dependency.
apt-get install -y --no-install-recommends python3-pyside6.qttest xvfb xauth dbus-x11 kwin-x11 kglobalacceld xdotool x11-utils > /tmp/apt-ui-proof.log
runuser -u beta -- mkdir /home/beta/first-run-evidence
runuser -u beta -- env AUGMENTOR_PROOF_OUTPUT=/home/beta/first-run-evidence QT_QPA_PLATFORM=xcb python3 /usr/lib/augmentor/scripts/x11-session.py dbus-run-session -- python3 /usr/lib/augmentor/scripts/first-run-proof.py /usr/lib/augmentor
test -s /home/beta/first-run-evidence/first-run-proof.json
runuser -u beta -- env AUGMENTOR_PROOF_OUTPUT=/home/beta/first-run-evidence AUGMENTOR_UI_PROOF=/usr/lib/augmentor/scripts/shortcut-launch-proof.py bash /usr/lib/augmentor/scripts/native-x11-proof.sh
test -s /home/beta/first-run-evidence/shortcut-launch-proof.json
apt-get remove -y augmentor-desktop augmentor-runtime > /tmp/apt-remove.log
test -s /home/beta/augmentor-install-proof/result.json
test ! -e /usr/bin/augmentor-runtime
test ! -e /etc/opt/chrome/native-messaging-hosts/com.augmentor.agent.json
python3 -c 'print("Installed desktop first run and file task passed; removal preserved user data and removed owned host registration.")'
