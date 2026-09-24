<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Home desktop launcher

The optional Qt tray process opens the household's existing NAS web dashboard.
It owns no device integration, model, agent loop or NAS service. Closing the web
window or quitting the launcher leaves the home running. The NAS is configured
once; computers view the same dashboard.

## User experience

- Start **Augmentor Home** from the desktop application menu.
- On KDE, click the home tray icon to open the dashboard; click again to close
  its app window. A fresh compositor lookup handles manual window closing too.
- **Open Home** opens or raises the dashboard without toggling it closed.
- **Connection settings…** remembers the dashboard address.
- Startup at login launches the tray quietly; it does not open a window.
- **Quit launcher** stops only the local tray process.

Chromium/Chrome/Edge, when installed, opens the URL with `--app` in an app-style
window using that browser's normal profile. Otherwise the default browser opens.
This reuses installed browser rendering instead of bundling another WebEngine.
The owner signs in to Home Assistant normally on first use in that browser;
the Codex browser's session is not copied. Browser cookies remain browser-owned.

No API token, copied key or Home agent pairing code is required for this launcher.
Connecting an Augmentor conversation to the Home agent remains a separate scoped
capability. The tray is manual dashboard access, not an expansion of agent authority.

## Installation and persistence

Implementations: `apps/native/augmentor_linux/home_tray.py`,
`scripts/home-launch.py`, `scripts/install-home-tray.py`.

Stage and activate the tested native artifact through `augmentor-update`, following
[desktop deployments](DESKTOP-DEPLOYMENTS.md). Then run the selected artifact's
`scripts/install-home-tray.py`. It installs a stable `~/.local/bin/augmentor-home`,
desktop menu entry, and XDG login autostart entry. `--no-autostart` skips creating
the login entry. It backs up any entries it replaces. Existing desktop windows
and conversations are not restarted.

The stable launcher resolves `desktop.json` each time; it never hard-codes a
versioned release or checkout path. Existing running tray code stays on its
loaded release until restarted. A selected release without Home support reports
an explicit error. A per-user lock/socket forwards subsequent launches to the
same tray instance. If the desktop has no system tray, a connection window is
shown as a fallback.

The KDE toggle uses the existing desktop KWin helper and system Python/GObject
bindings, with a bounded compositor-authenticated reply. It matches Chromium's
URL app identity instead of the page title; normal browser windows are excluded.
Repeated explicit Open raises an existing app window. Lookup failure reports an
error rather than opening a duplicate. A brief click cooldown absorbs duplicate
activation events. Other desktops retain the original open-only behavior pending
a supported window-control adapter. Chromium's app identity omits scheme/port;
two app windows with the same host/path share this identity even across ports.

Configuration: `$XDG_CONFIG_HOME/augmentor/home-launcher.json` (default
`~/.config/augmentor/home-launcher.json`), atomically written mode 0600. Only a
dashboard URL is stored. Embedded credentials, query strings and fragments are
rejected to avoid storing pasted tokens. Household addresses are deployment data,
not hard-coded public source defaults.

## Verification

Six native tests cover URL validation/private persistence, browser dispatch,
settings/open actions, fresh-state toggle/manual closing, lookup failure and
selected-release resolution. A two-process check proves
the second settings invocation hands off to the primary and exits. These are
launcher tests, not physical device operations or cross-platform certification.

### Installed Linux evidence — 24 September 2026

**Latest selection:** toggle implementation `09a7dfb`, release
`20260924-205229-78c3c113`, artifact SHA-256
`6466feffb8661e73e9b8dba84565c18a420365e62f9930f9d61159fdd2ac3090`.
The tray was restarted onto this release; conversation windows retain the builds
listed below. Six native checks and an isolated window-identity script passed.
Live KDE StatusNotifier Activate calls opened one window, closed it on the second
click, and reopened one on the third. Explicit Open retained one window. The
compositor's unrelated window IDs were preserved. The shared KWin read-only
observation path was also exercised after extracting its script executor.
Managed staging/inventory/import and authenticated activation passed.

The following records the preceding initial installation:

Implementation `76cb697` was applied to a separate copy of the selected compatible
0.2.11 desktop artifact, preserving its other native/runtime patches. Managed
stage/import/inventory and authenticated activation preflight passed. Selected
release: `20260924-202032-d5e07a94`; artifact SHA-256:
`6540847733b8c49e9d7aa60b74cdc024639447993b0edd9f6018fc2a1fac5928`.

The stable menu and login entries were installed. On KDE/Wayland the running
tray registered as **Augmentor Home**, with StatusNotifier status `Active`.
The installed command opened a normal Chromium app window; KWin independently
reported its Home Assistant title and the configured dashboard path in its app
identity. Repeating the background command left one tray process. One idle sample
measured about 49 MiB proportional memory for the launcher, excluding the browser;
this is not a cross-hardware resource qualification. Login registration is checked,
but a physical logout/reboot has not been tested.

The tray runs the selected release. Main/mobile retain `20260924-125423-63307454`,
and secondary retains `20260924-125950-12694ac7`; all reported online with voice
available. They were not restarted. This deployment did not change NAS services,
device state, agent authorization or browser credentials. The owner may need the
normal Home Assistant login on first use in the external browser.
