#!/bin/sh
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
# Debian 13 amd64 rootless runtime. Downloads official distro packages; does not install system services.
set -eu
[ "$(dpkg --print-architecture)" = amd64 ] || { echo 'This runtime recipe requires Debian amd64.' >&2; exit 1; }
RUNTIME_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/augmentor-mobile-runtime"
mkdir -p "$RUNTIME_DIR/debs" "$RUNTIME_DIR/root"
cd "$RUNTIME_DIR/debs"
apt-get download x11vnc=0.9.17-1 libvncserver1=0.9.15+dfsg-1+deb13u2 libvncclient1=0.9.15+dfsg-1+deb13u2 xcompmgr=1.1.8-1
for package in ./*.deb; do dpkg-deb -x "$package" "$RUNTIME_DIR/root"; done
printf '%s\n' 'Runtime extracted. Xvfb and xauth must also be available on the host.'
