#!/usr/bin/env bash
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
# Exercise actual pointer events and the external clipboard on an isolated X server.
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export AUGMENTOR_PROOF_ROOT="$project_dir"
export AUGMENTOR_PROOF_OUTPUT="${AUGMENTOR_PROOF_OUTPUT:-$project_dir/outputs}"
export AUGMENTOR_PYTHON="${AUGMENTOR_PYTHON:-/usr/bin/python3}"
export AUGMENTOR_UI_PROOF="${AUGMENTOR_UI_PROOF:-$project_dir/scripts/copy-scroll-proof.py}"
proof_workspace="$(mktemp -d -t augmentor-x11-proof-XXXXXXXX)"
trap 'rm -rf -- "$proof_workspace"' EXIT
export XDG_CONFIG_HOME="$proof_workspace/config" XDG_DATA_HOME="$proof_workspace/data" XDG_STATE_HOME="$proof_workspace/state"
export AUGMENTOR_PI_CONFIG="$proof_workspace/config/augmentor-pi" AUGMENTOR_PI_STATE="$proof_workspace/state/augmentor-pi"
export AUGMENTOR_SHARED_DATA="$proof_workspace/data/shared" AUGMENTOR_SHARED_STATE="$proof_workspace/state/shared"
export XDG_RUNTIME_DIR="$proof_workspace/runtime"
# Xvfb needs window management, not compositing. KWin 6's X11 backend does
# not support QPainter compositing and exits if KWIN_COMPOSE=Q is forced.
export QT_QUICK_BACKEND=software KWIN_COMPOSE=N QT_QPA_PLATFORM=xcb LANG=C.UTF-8
mkdir -p "$AUGMENTOR_PROOF_OUTPUT" "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$XDG_STATE_HOME"
mkdir -m 700 "$XDG_RUNTIME_DIR"
"$AUGMENTOR_PYTHON" "$project_dir/scripts/x11-session.py" dbus-run-session -- bash -euo pipefail -c '
  kwin_x11 --replace > "$AUGMENTOR_PROOF_OUTPUT/x11-window-manager.log" 2>&1 &
  proof_wm=$!
  trap '\''proof_status=$?; if (( proof_status != 0 )); then xprop -root _NET_SUPPORTED _NET_SUPPORTING_WM_CHECK; cat "$AUGMENTOR_PROOF_OUTPUT/x11-window-manager.log"; fi; kill "$proof_wm" 2>/dev/null || true; wait "$proof_wm" 2>/dev/null || true; exit "$proof_status"'\'' EXIT
  for attempt in {1..100}; do
    supported="$(xprop -root _NET_SUPPORTED)"
    if [[ "$supported" == *"_NET_ACTIVE_WINDOW"* ]]; then break; fi
    kill -0 "$proof_wm"
    sleep 0.1
  done
  if [[ "$supported" != *"_NET_ACTIVE_WINDOW"* ]]; then
    cat "$AUGMENTOR_PROOF_OUTPUT/x11-window-manager.log"
    exit 1
  fi
  "$AUGMENTOR_PYTHON" "$AUGMENTOR_UI_PROOF"
'
