<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->
# Augmentor Desktop Remote

This preview displays and controls the **actual Qt Desktop application**. It has
no web reimplementation of the conversation, model picker or settings screens.
The separate web-chat prototype has been replaced following the user's correction.

`native_runner.py` loads the installed Desktop build and applies the maintained
`apps/native/augmentor_linux/touch.py` adapter in memory. A named `mobile` window
shares the existing agent services, history and prompt library, while keeping its
own current conversation, placement and appearance preferences. On this machine,
the installed voice-preview Desktop (0.2.8) matches the running DSH integration;
the source checkout (0.2.9) does not. The launcher selects the installed build
without patching its files or bypassing its version check. Use `--desktop-root`
to choose a different compatible build explicitly.

## Run

From the repository root, using Node 24 and the existing Desktop Python runtime:

```sh
sh apps/mobile/setup-runtime.sh
npm ci --ignore-scripts --prefix apps/mobile
npm run build --prefix apps/mobile
python3 apps/mobile/start.py --origin https://YOUR-COMPUTER.YOUR-TAILNET.ts.net:8443
```

The runtime helper extracts pinned official Debian 13 amd64 x11vnc/LibVNCServer
packages into `~/.local/share/augmentor-mobile-runtime`, without system installation.
Xvfb and xauth must already be installed (they are available on this machine).
The launcher uses an isolated authenticated X display, never the user's main
screen. x11vnc listens only on IPv4 loopback, has a random password, and explicitly
disables the library's separate IPv6 listener. The web bridge also binds loopback.

Open [the local preview](http://127.0.0.1:8765/) and enter the private key in
`~/.local/state/augmentor-mobile/pairing-key`. Keep this key private: it grants
control of the original Desktop application, including its settings and tools.
The browser receives a 12-hour HttpOnly cookie. One viewer controls the window at
a time. Disconnect releases control; reopening the connection does not replay
keystrokes or resend prompts. Restart revokes all sessions. The agent's durable
work remains in the existing harness.

For phone access on the same private tailnet, the one-time administrative command
is:

```sh
sudo tailscale serve --bg --https=8443 http://127.0.0.1:8765
```

Then use the configured private HTTPS origin on the phone. This command was
requested from the user because the daemon denies this session permission to
configure Serve. No public Funnel route is used. Inspect existing Serve routes
before changing them; this dedicated 8443 route can be removed with
`sudo tailscale serve --https=8443 off`.

The internal Android WebView host, APK build and emulator instructions are in
[android/README.md](android/README.md). Consult the validation record before
assuming a compiled APK has passed Android acceptance.

## Touch adaptations

- The original toolbar's buttons have 44×44 hit areas and 8-pixel gaps. The toolbar
  moves onto its own row on the compact touch surface.
- Original message-action artwork sits inside transparent 44×44 hit areas.
- The model picker, voice, Send/Stop and prompt-improvement controls are enlarged.
- Tap the native conversation title to rename; right-click-only workflows retain
  their original alternative menu entries where available.
- Original dialogs gain scrollable containment; menus stay within the transmitted
  viewport. Colors, skins, icons, message rendering and handlers remain Desktop's.
- The small browser footer provides transport utilities only: keyboard, restoring
  a hidden/compact app, copying the remote clipboard, and disconnecting.

A keyboard button brings up the phone's keyboard and forwards committed text to
the focused native field. This is separate from speech forwarding. The current
voice control still belongs to the host's audio devices; phone microphone and
speaker routing is **not implemented**. Do not mistake displayed voice controls
for verified phone voice support.

The app resizes at native scale rather than shrinking buttons to fit. The minimum
native viewport is 340×300; smaller browser areas can scroll. Real mobile keyboard,
rotation, accessibility and radio-transition acceptance remains required.

## Tests

```sh
node --test tests/mobile-desktop-server.test.mjs
QT_QPA_PLATFORM=offscreen timeout 15 .venv/bin/python apps/mobile/verify-native.py
PYTHONPATH=apps/native QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -p test_touch_layout.py -v
```

The web server tests cover pairing, throttling, Host/Origin checks, invalid resize,
unsupported routes, private-origin requirements, authenticated WebSocket relay,
single-viewer ownership and logout revocation. Native tests check unchanged normal
Desktop sizing, touch geometry, real menu actions and narrow-dialog containment.
The existing Window and message-action tests remain applicable.

## Shutdown and data

For login startup and crash recovery, install the per-user service:

```sh
python3 apps/mobile/install-service.py --origin https://YOUR-COMPUTER.YOUR-TAILNET.ts.net:8443
# Stop an existing foreground/development supervisor before starting the service.
systemctl --user start augmentor-mobile.service
systemctl --user status augmentor-mobile.service
```

The installer enables login startup and uses the detected Node executable's
directory. It does not configure Tailscale or administrator settings. Check
`journalctl --user -u augmentor-mobile.service` and component logs in the state
directory. Use `systemctl --user stop augmentor-mobile.service` to stop it, and
`systemctl --user disable augmentor-mobile.service` to disable login startup.
The user service does not promise availability before login or while the computer
is asleep. Service restart revokes browser sessions and requires pairing again.
Restart only after remote work is idle; do not replay tasks with unknown outcomes.

Ctrl+C stops the foreground supervisor and its isolated display, Desktop window,
VNC server and bridge. The development preview may run detached; its PID is recorded
at `~/.local/state/augmentor-mobile/supervisor.pid`. Stop that specific supervisor
with SIGTERM after checking its process identity. Do not kill unrelated Desktop,
DSH, Xvfb or VNC processes.

Remote appearance/session state uses Desktop's normal named-window mechanism.
Pairing and connection state are under `~/.local/state/augmentor-mobile`. The old
web-chat operation journal is retained but no longer used. No existing chats are
deleted. If the supervisor quits while work is running, reconnect to the original
harness to inspect task state; do not resend an unknown-outcome task.

## Dependencies and licensing

- noVNC **1.6.0**, MPL-2.0, pinned official release archive plus lockfile integrity.
  The npm CommonJS artifact has a top-level-await incompatibility with bundling;
  the unmodified release's ESM sources are bundled instead.
- ws **8.21.0**, MIT; esbuild **0.25.12**, MIT (build dependency).
- x11vnc **0.9.17-1**, GPL-2.0-or-later, and LibVNCServer distro packages
  **0.9.15+dfsg-1+deb13u2**. Their copyright/license files accompany the extracted
  runtime; do not remove them when packaging.
- xcompmgr **1.1.8-1**, X11 license. Composites the original translucent activity
  halo; without it the overlay obscures the interface during generation on Xvfb.
- Qt/PySide and the existing Desktop retain their existing license terms.

See [the updated plan](../../docs/MOBILE-REMOTE-PLAN.md) and
[validation record](../../docs/MOBILE-REMOTE-VALIDATION.md).
