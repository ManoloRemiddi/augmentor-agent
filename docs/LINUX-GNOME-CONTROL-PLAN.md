<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# GNOME consent and control implementation plan

Production GNOME observers remain read-only and inputQualified stays false.
The separate input-free consent candidate below now exercises real Fedora50
portal consent and Stop; it does not enable production GNOME control. Current
portal.py constructs KWin and rejects non-KDE sessions; service.py runs backend
calls on the GUI GLib loop. Both still need integration and KDE regression before
enabling GNOME input.

## Native capture candidate and cancellation evidence

The [checked Fedora report](../release/qualification/next-targets/20261002-gnome-native-capture.json)
qualifies only separately staged scale1 single-monitor capture, plus cleanup after
actual visible Stop and native GNOME sharing Stop. The normal UID1000 Fedora44
GNOME50.5 Wayland guest retains SELinux enforcing and its unchanged selected app.
[Capture probe](../release/probe-gnome-capture.py) and [GTK4 target](../release/probe-gnome-target.py)
require the exact owned marker, private candidate path and target PID/start-time;
they must never run on an owner's desktop. Stage peer worker/consent/control/
observer/portal/capture/scene modules with the two scripts. Start the GTK fixture,
run the capture probe with `--candidate gnome-execution-probe-vN`, exact selected
`--source` and `--target-pid`, visibly consent, activate only the owned target,
then create private0600 `trigger.capture`. The probe never calls action/Notify.
Its target fields remain empty and both button counts zero. JPEG bytes are not
saved or published; the report keeps dimensions and an encoded-image digest.

Current v7/v9 capture real1280×800 PipeWire RGB frames, validate the compositor's
logical scale1 monitor and issue fresh tokens. v7 visible Stop detaches resources
in0.300 seconds; six50ms Qt ticks continue through cleanup. v8 uses real native
consent but an empty synthetic GStreamer pipeline with30-second frame wait;
visible Stop cancels it and detaches in0.063 seconds. v9 native orange sharing
Stop after a real capture closes with `native-session-closed`, no Augmentor Stop
click. Its cleanup after the Qt notification takes0.010 seconds; this is not total
revocation latency. No active PipeWire failure/revocation-during-acquisition claim.

v1/v4 consent timeouts, v2 Overview guard refusal and v3 unexplained capture
cancellation are preserved. Later successful captures do not diagnose v3. v5/v6
passed capture/cancellation but lost Stop reason when the controller set the
shared Event before the session; v7/v8/v9 correct and retain first cause. v7's
idle-watch diagnostic records expected cancellation during cleanup. The optional
request observer/timeout serve fixture diagnostics; production default remains80
seconds, fixture180. Source742 cases pass:740 successes/two Mac-only skips.
Pointer/widget/keyboard, full AT-SPI delivery, normal password lock, owner/epoch
restart, scaled/far-edge/hover cases, Ubuntu/Leap/profile repetition and KDE service
threading remain open. Production discovery and inputQualified remain false.

## October 2 native consent and worker checkpoint

The [checked report](../release/qualification/next-targets/20261002-gnome-native-consent.json)
binds exact candidate bytes separately from the unchanged selected Fedora44
application. [ConsentSession](../services/desktop/portal_session.py) owns an
independent bus on a private GLib context. It pins frontend/backend/Shell owners,
registers the app only if advertised, subscribes before dispatch and validates
precomputed request/session identities. Cancellation advances a generation and
cancels the RPC immediately; an unanswered request or late session grant is
closed through its already retained owned identity. Cleanup detaches and closes
the PipeWire FD, session and request, with separate bounded uncancelled cleanup
calls. No input method is implemented or sent by this component.

[Worker](../services/desktop/worker.py) serializes tasks even while portal response
waits pump its private context. A second cleanup task cannot reenter a pending
connect operation. Qt stays on its own GUI thread; futures retain failures and
close checks worker termination. Eleven focused tests cover real nested GLib
scheduling, Qt timer/Stop responsiveness, owner/identity fences, late grants and
FD cleanup. Full isolated Arch source regression passes721 cases:719 pass/two
Mac-only skips. The initial invocation omitted Node/PYTHONPATH and is retained;
the corrected invocation uses the existing pinned Node24.19.0, compiled source
and exact production lock dependencies. Linux-only GLib tests skip where the
runtime is absent; hosted Mac remains an independent regression gate.

The [probe](../release/probe-gnome-portal-consent.py) requires the owned ordinary-user
Fedora QEMU marker, SELinux enforcing, GNOME Wayland and the exact unchanged
selected artifact. Separately stage its three hashed files in a private candidate
directory and run with `--candidate gnome-control-probe-vN --qt-platform xcb`
and `--source <exact selected source>`. It reuses only the installed unchanged
Banner class; the production client/launcher already selects xcb on Wayland.
The qualification probe allows180 seconds for manually inspected consent; the
component default is80 and all timeouts are bounded. Reports include the actual
platform, request phases, GUI ticks, source hashes and unchanged selection checks.
Never use this disposable fixture driver on an owner's desktop.

Actual Fedora50 RemoteDesktop2/ScreenCast5 advertises device/source/cursor masks7
and Registry. Native Cancel closes resources without input on the exact current
180-second probe, alongside separately hashed earlier candidates. Sharing with
remote interaction OFF is refused.
Explicit interaction ON and Share grants devices3 and one monitor node, logical
position(0,0), size1280×800, source_type1 and mapping_id. These observed values
still require strict geometry/topology validation before execution. Actual visible
Stop during consent discards the late result; Stop after successful consent closes
all resources and exits the probe. Qt ticks continue throughout cleanup. No
pointer/typing/capture, target selection or production integration is claimed.

The first probe timed out but left its banner/process alive due an error-cleanup
bug; it was terminated only after confirming the exact owned process. Its native
Qt Wayland Tool banner was unavailable on the normal desktop, so that run is
excluded from acceptance. Revised cleanup and current xcb runs are separately
recorded. QEMU captures also include partial redraws and the selected app can
cover the native portal; complete graphical rendering is not qualified. Dismissing
only the fixture DSH dialog's Later button changes no provider or configuration.
Native GNOME sharing Stop also closes this input-free probe with no Augmentor
Stop click. Execution-controller revocation, service/extension restart, password
lock, scaled/topology cases,
Ubuntu consent, input/scene/AT-SPI integration and KDE threading regression remain
open. All five original rollout points remain active.

## Guarded execution candidate; not enabled

[GnomeControl](../services/desktop/gnome_control.py) is a separate worker-owned
candidate; production discovery still rejects GNOME input. It owns independent
consent, pins the observer epoch, consumes one-use target tokens, checks the
current scene before each dispatch and uses compositor InspectPoint before
pointer motion/button press. Monitor source/position/size must match exactly one
compositor monitor at scale1. Frame caps must also match the logical monitor
before issuing a token. Observer/epoch/topology/capture failure closes resources;
a worker-context250ms watcher invalidates idle locked/replaced sessions.
Native scale1 capture/cancellation evidence is recorded above; dispatch guards
still have synthetic tests only. No native pointer/keyboard acceptance is claimed.

Pinned [frontend1.22.1](https://github.com/flatpak/xdg-desktop-portal/blob/1.22.1/src/remote-desktop.c),
[GNOME backend50.0](https://github.com/GNOME/xdg-desktop-portal-gnome/blob/50.0/src/remotedesktop.c)
and [Mutter50.5](https://github.com/GNOME/mutter/blob/50.5/src/backends/meta-screen-cast-monitor-stream.c)
show a scale-dependent transform/bounds discrepancy: portal metadata is logical,
while scaled stream capture/pointer transforms use monitor scale. Scale2/fractional
input is refused until actual caps, far-edge coordinates and widget outcomes are
proved. A metadata-only scale2 unit fixture is not coordinate qualification.

Capture now has a virtual frame-acquisition hook; the KDE implementation retains
its existing default-context route. The GNOME candidate passes only its worker
context and cancellation checkpoints, including after a sample arrives. Tests
attach real sources to both contexts and prove private cancellation without
GUI-source callback delivery. Native Session.Closed during capture still needs
live acceptance. Portal Notify ACK is asynchronous and cannot prove an actual
widget click or settled hover popup.

Inherited libatspi uses a global default context; Gio's thread-default context
alone does not migrate it. See the exact
[libatspi context implementation](https://github.com/GNOME/at-spi2-core/blob/2.60.0/atspi/atspi-misc.c).
This candidate returns no cached accessibility focus and refuses keyboard/type
until an isolated helper proves event-thread identity, focus-away/back, password
and inaccessible controls, new-app discovery and a11y owner invalidation. It does
not move the GUI process's singleton or claim per-character focus delivery.

Next native proof: GTK Wayland/XWayland pointer/widget outcomes; all
stale/focus/cover/hover fences; mid-capture Stop/native revocation/terminal stream
failures; isolated AT-SPI helper keyboard and partial-action Stop; normal password
lock and independent service/observer restarts. Repeat supported46/48/49 profiles
and real KDE threading regression before production integration.

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
