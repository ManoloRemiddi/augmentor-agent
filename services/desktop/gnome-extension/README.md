<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# GNOME window observer

`observer@augmentoragent.com` is the first read-only GNOME 50 compositor bridge.
It supplies Status, Read and InspectPoint on `/com/augmentor/GnomeObserver` through
Shell's existing session-bus connection. It adds no UI, capture/input transport,
arbitrary-code or window-management methods. It is included as source and is not
automatically installed/enabled in user sessions. GNOME input registration remains
gated until the full [rollout acceptance](../../../docs/LINUX-DISTRO-ROLLOUT.md) passes.

[`gnome.py`](../gnome.py) pins the unique Shell bus owner, bounds requests, checks
the typed JSON protocol and fences extension epochs. Window identities namespace
Mutter's stable sequence with a fresh enable epoch. Tracked focus, frame, stacking,
workspace, monitor, lifecycle and relevant Shell/stage events advance the serial
without deduplicating identical final state. Metadata PID is not authorization.
Snapshots include fresh Shell modal/mode/overview/grab/lock-provider observations.
Missing lock providers are explicit blockers. Closed actors are released through
their lifecycle rather than accessed after disposal.

Point inspection checks both reactive and painted picks against the expected
window actor's ancestry; other windows, chrome, clones and unknown results fail
that match. It still reports `inputQualified: false`. Full actor-composition and
surface-input-region history are not covered by this first bridge. An event
serial describes tracked scene events, not every possible input-routing change.
Do not turn its current candidate point match into input authorization.

The [checked private proof](../../../release/qualification/gnome50/fedora44-observer.json)
uses GNOME Shell/Mutter 50.5 with real GTK Wayland windows: distinct same-process
identities, focus away/back, resize, window/chrome picking, close/reopen identity
and extension disable/re-enable invalidation. Synthetic Alt+Escape on the owned
private Mutter connection changes focus; that version-pinned API is fixture
infrastructure. A normal untokened Wayland `present()` request correctly cannot
restore the older window's focus. Input events never reach the owner's desktop.

Build the private discovery/Qt images as documented in the rollout guide, then
use `--exercise-gnome-observer` with `release/prove-gnome-discovery.py`. This copies
the extension into the disposable user's home before starting the owned Shell.
The proof verifies loaded/source hashes and refuses source changes during a run.
Real login/reboot, XWayland, modal/popups, full animation/chrome/lock handling,
capture-coordinate mapping and consent/input/Stop remain open qualification work.

The separate actual-Augmentor [XWayland](../../../release/qualification/gnome50/fedora44-native-ui-xcb.json)
and [Wayland](../../../release/qualification/gnome50/fedora44-native-ui-wayland.json)
proofs now use the read-only observer to verify compositor focus after canonical
launcher hide/restore, with a real letter reaching each independent composer's
preview window. This narrower XWayland focus observation does not qualify the
full XWayland identity/occlusion/input contract. Initial preview launches, dummy
login and no model requests still exclude full startup and desktop acceptance.
Use `--exercise-native-ui xcb` or `--exercise-native-ui wayland` in the native UI
fixture described in the rollout guide; the observer remains inactive in normal
product sessions.
