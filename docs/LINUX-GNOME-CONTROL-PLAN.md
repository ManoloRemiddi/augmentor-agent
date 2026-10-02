<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# GNOME consent and control implementation plan

This is pinned source research, not executed control qualification. Existing
GNOME observers are read-only and inputQualified stays false. Actual GNOME48/46/
50 observer sessions do not grant control consent, input or visible Stop passes.
Current portal.py constructs KWin and rejects non-KDE sessions; service.py runs
backend calls on the GUI GLib loop. Both need explicit adaptation and regression
qualification before enabling GNOME input.

## Portal negotiation and identity

Pinned xdg-desktop-portal-gnome backends
[46](https://github.com/GNOME/xdg-desktop-portal-gnome/tree/81c74e0a29537e1bb29a40554e9bf9c41a272148),
[48](https://github.com/GNOME/xdg-desktop-portal-gnome/tree/357847a5f876947c7931d7fa2c68ce8b8d0d48ae),
[49](https://github.com/GNOME/xdg-desktop-portal-gnome/tree/0a3499e0e04f4f9b657bf404f9266dd23d03d2ae)
and [50](https://github.com/GNOME/xdg-desktop-portal-gnome/tree/c9a231d3a0c77b6b14f998653b7323858d559dd7)
advertise RemoteDesktop2/ScreenCast5, NotifyKeyboardKeysym and ConnectToEIS.
Inspect actual installed interfaces/version/bitmasks; Shell major does not prove
portal capabilities. The 1.22.1 frontend clamps ScreenCast to backend capabilities,
so GNOME50 does not provide its version6 pipewire-serial extension.

For the initial Notify* transport, use RemoteDesktop.CreateSession then
SelectDevices(types3,persist0), ScreenCast.SelectSources(types1,multiplefalse,
hidden cursor only if advertised), RemoteDesktop.Start, and OpenPipeWireRemote.
Require both keyboard/pointer device bits and exactly one monitor stream; decline,
cancel or remote-interaction-disabled refusal closes everything. No restore token
or clipboard. Preserve foreground selection after actual monitor consent, with
no forced focus and the existing 30-second single-use owner token.

[Stream position/size](https://github.com/flatpak/xdg-desktop-portal/blob/1.22.1/data/org.freedesktop.portal.ScreenCast.xml#L213)
are compositor-logical coordinates, not JPEG pixels. Validate metadata and map
captured image to stream logical/compositor geometry; refuse missing/ambiguous
mapping. PipeWire node IDs are session-local. Topology/stream loss invalidates
them. Version5 mapping_id is relevant to optional EIS regions, not version6
serial guarantees.

When advertised, register com.augmentor.Agent on a fresh independent helper bus
connection through
[org.freedesktop.host.portal.Registry](https://github.com/flatpak/xdg-desktop-portal/blob/1.22.1/data/org.freedesktop.host.portal.Registry.xml#L43)
once per portal owner before requests. Noble frontend1.18.4 lacks that interface;
1.20.3/1.22.1 provide it. A late failed Register is not identity proof. Retain the
product's named visible control banner even where the GNOME consent dialog does
not use the passed app_id as its display name.

## Target guards and cancellation

Use the GNOME observer's versioned live window/focus/geometry identity and
InspectPoint checks, including before click and after pointer movement. Preserve
AT-SPI focused-control/password checks and per-character verification. Cover
refusal includes same-PID and override-redirect actors. PickMode.ALL does not
prove complete painted coverage. Keep completeActorCompositionTracking false;
do not invent a complete history or compositor-atomic dispatch requirement beyond
the approved KDE check-then-dispatch contract.

Watch unique owners of org.freedesktop.portal.Desktop,
org.freedesktop.impl.portal.desktop.gnome, org.gnome.Shell and the helper connection.
Stop on replacement/loss, Session.Closed, invalid observer epoch/UnknownMethod,
PipeWire EOS/error, incompatible monitor metadata or transport loss. Increment
the generation, discard snapshots, detach Session/FDs, close pending Requests,
then perform idempotent held-input cleanup. Late consent callbacks cannot restore
stopped state. Terminal capture error must close sharing, not just fail a read.

Portal Notify replies acknowledge IPC dispatch, not application outcome. Keep
verified false and no replay. Timeout/loss after dispatch is partial/unknown and
non-retryable. Unlock requires a new selection/session/consent. Normal nonheadless
[Shell lock](https://github.com/GNOME/gnome-shell/blob/50.5/js/ui/main.js#L138)
inhibits remote access; [Mutter session closure](https://github.com/GNOME/mutter/blob/50.5/src/backends/meta-dbus-session-manager.c#L491)
propagates to portal Session.Closed. Headless bypass is not desktop evidence.
The [Shell sharing indicator](https://github.com/GNOME/gnome-shell/blob/50.5/js/ui/status/remoteAccess.js#L182)
provides extra revocation, while Augmentor must retain its visible Stop.

The GNOME observer uses synchronous D-Bus; merely swapping it into the GUI-loop
executor risks delaying Stop. Keep GUI delivery responsive with explicit worker
ownership and serialized cancellation. If using a dedicated GLib worker context,
create an independent GIO connection and context there, adapt existing KWin's
default-context pumping, and never iterate the GUI context from that worker.
This is an identified source risk, not an executed Stop failure. Actual KDE
regression is required after any shared threading change.

## Finite graphical acceptance

Start with full Fedora44/GNOME50, then repeat unchanged candidate on Noble46,
Leap48 and Fedora43/GNOME49. Record exact artifact, runtime, backend/frontend and
security state for each; do not infer pass from another Shell version.

1. Actual decline, interaction disabled, cancellation and Stop during consent.
2. Owned native GTK Wayland and XWayland applications: click/chord/ASCII typing,
   exact saved file and fresh captured result, with token expiry/reuse/foreign
   conversation refusal.
3. Focus/popup/foreign/same-PID covers, input-region full/empty/full and painted
   click-through Shell overlays with truthful coverage limits.
4. Scales1/2 and monitor/topology invalidation with logical-coordinate checks.
5. Actual QMP-clicked visible Stop while waiting, during partial typing and held
   input; GUI remains responsive and cleanup completes.
6. Actual Shell sharing-indicator revocation, not just a mocked session signal.
7. Normal password lock during consent, active session and partial input; correct
   unlock needs fresh consent and never replays the interrupted action.
8. Distinct frontend/backend/Shell/helper loss and reply loss after dispatch:
   partial unknown outcome, invalid generations, no automatic replay.

EIS is optional after this bounded Notify path. ConnectToEIS may be called once
after Start; Notify methods are then forbidden. Use a pinned native libei sender
shim, actual device/seat capabilities and keymap/frame/region handling rather
than inferred GI APIs. Pause/removal/disconnect cancels old actions. Neither EIS
framing nor Mutter's accumulation code creates atomic target compare-and-dispatch.
