<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# GNOME consent and control implementation plan

Production GNOME observers remain read-only and inputQualified stays false.
The separate input-free consent/capture candidates below exercise real Fedora50
portal consent and Stop. The source-only input candidate described next does not
enable production GNOME control. Current
portal.py constructs KWin and rejects non-KDE sessions; service.py runs backend
calls on the GUI GLib loop. Both still need integration and KDE regression before
enabling GNOME input.

## October 3 isolated-helper input candidate; native acceptance pending

[GnomeControl](../services/desktop/gnome_control.py) now binds a separately owned
[AccessibilityHelper](../services/desktop/a11y_helper.py) to the captured active
window PID and its native process start time. The consumed observation retains
the helper epoch, session/accessibility bus IDs, launcher/registry owners,
selected application owner, accessible path, raw state and event serial. Each
keyboard press, including every chord modifier and every ASCII character, asks
the helper for a fresh complete focus and then rechecks the compositor scene.
A cached serial alone cannot deliver the child's focus events to this worker.
Capture also rechecks its scene after the bounded accessibility walk.

The initial keyboard candidate requires focused, showing, nondefunct, sensitive,
editable, nonpassword controls. GTK4.22.5's raw ENABLED=false is preserved rather
than treated as disabled: its [pinned state collector](https://github.com/GNOME/gtk/blob/4.22.5/gtk/a11y/gtkatspicontext.c)
exports SENSITIVE from the disabled state and omits ENABLED. A valid incomplete
tree returns no keyboard target; a pointer observation can still be captured.
That incomplete helper is retired and cannot be replaced to authorize the old
keyboard token. A fresh capture can construct a new helper. Native identity or
transport failure invalidates sharing; password, insensitive, noneditable,
changed-focus/serial and scene refusal stop keyboard dispatch and detach state.
Stop also disposes the isolated helper. Helper cleanup failure is recorded and
cannot skip bounded held-input release against the pinned portal session.
The first native/user Stop cause remains retained across repeated cleanup.

A failed or cancelled Notify RPC is reported as an unknown outcome, with the
observation consumed, sharing stopped and no retry. A successful dispatch still
returns verified=false. This matches the [pinned frontend's asynchronous backend
call and immediate client reply](https://github.com/flatpak/xdg-desktop-portal/blob/1.22.1/src/remote-desktop.c);
actual widget state or saved bytes must establish the outcome independently.
Production service.py, capability discovery, the banner and historical probes
are unchanged; inputQualified remains false.

The new [owned input probe](../release/probe-gnome-input.py) and [GTK target](../release/probe-gnome-input-target.py)
require the dedicated Fedora GNOME QEMU marker, ordinary augmentor-proof UID1000,
SELinux Enforcing, unchanged exact clean managed selection and a fresh private
gnome-execution-probe-input-vN directory. Stage both files plus worker,
gnome_control, gnome, portal, portal_session, capture_stream, scene, a11y_helper
and a11y_service together; all module hashes are recorded. Run the target with
`--candidate gnome-execution-probe-input-vN --backend wayland` (repeat separately
with x11), then the probe with that candidate, `--source <selected commit>` and
`--selected-artifact <verified selected inventory SHA256>`,
`--native-source <audited native package commit>` and
`--target-pid <actual target PID>`. Before importing the candidate, Qt or banner,
the input probe uses the normal owned per-user desktop-deployment.py verifier
to verify every managed file and inventory digest. Its complete deployment
receipt must equal the exact selected configuration and explicitly requested
artifact hash. Selected/native release metadata must be clean Fedora44 builds
at the explicitly requested sources with matching product versions; distinct
reviewed selected/native sources are recorded separately. The selected and
executing interpreter must be /usr/bin/python3 with no virtual environment or
managed/source-Qt Python policy. Inherited loader/Qt/Python overrides are refused
and the native augmentor-agent RPM must pass a clean read-only rpm -V audit.
After this admission, candidate modules take precedence and the verified
installed services/desktop directory supplies unchanged dependencies before
Worker/GnomeControl import. In particular, candidate portal.py imports KWin even
though GnomeControl never constructs it. The eleven-file candidate does not add
a KWin source overlay or alter the selected payload.
The Qt banner retains the previously observed
xcb route. Consent and target activation must be actual inspected operations;
the probe never forces focus or infers input permission from readiness.

Only a private0600 trigger.input.json explicitly requests an operation:
`{"operation":"capture"}`, `{"operation":"action","params":{"token":"<fresh token>","kind":"type","text":"synthetic"}}`,
`{"operation":"inspect"}` or `{"operation":"finish"}`. Action params use the
existing click/key/type contract. Every action requires the owned fixture to be
the actual foreground target. Real multiline text-buffer changes and center/edge
button callbacks write private receipts; an actual Ctrl+S callback writes
input-target-saved.json from current widget buffers. It is a fixture save action,
not an assertion that another application supports that shortcut. Inspect the
receipt and fresh capture after dispatch; an immediate receipt may precede
asynchronous native delivery. The probe keeps capture dimensions/digests rather
than image bytes. Its recorded-helper absence check covers only recorded PIDs;
the external owned-VM driver must independently check for helpers after failed
reads and retain process/start identities. Visible Stop remains the banner's
actual button; a finish trigger is cleanup, not visible Stop evidence.

Ninety-four focused source cases pass: GNOME guards/keyboard, helper protocol,
worker/consent cancellation, portal targets, scene/capture and private-trigger
and selected-artifact refusals. The latter exercise the normal maintained
inventory verifier against synthetic managed releases, including changed or
added payload, stale receipt, wrong source/target/hash/version/interpreter,
managed policy and inherited loader/native-audit refusals. An isolated import
regression copies the real eleven staged files, resolves the real installed
kwin.py dependency, and rejects installed controller replacements without
constructing GUI or opening consent. These are synthetic contracts, actual
module imports and real isolated GLib scheduling, not
native pointer/chord/typing qualification. No VM input has been sent by this new
candidate. Fresh Fedora50 native widget/file outcomes, per-character focus and
password/Stop/lock/restart cases, terminal capture loss, other GNOME profiles and
actual KDE threading regression remain open. Scale2/fractional and multi-monitor
input remain refused. Promote production routing only after those gates pass.

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

## Native selected-application owner loss with a live process

[The two executed owner-loss cases](../release/qualification/next-targets/20261002-gnome-native-selected-owner-loss.json)
use the actual Fedora44/GNOME50 accessibility bus, registry and helper with a
separate synthetic two-node Gio exporter. [The owned probe](../release/probe-gnome-a11y-owner.py)
registers only its private exporter connection, closes that connection while its
process/PID/start identity remains alive, and observes the helper's permanent
native-owner refusal. The first case closes in0.023 seconds; the current probe
with fresh-path/acknowledgment identity checks closes in0.059 seconds. These are
request-to-child-disposal durations, not physical input latency.

Both live exporters answer supervisor pings after disconnection. Reconnection
creates a different unique accessibility owner in the same process. The retired
helper refuses to resume; a fresh helper discovers/pins the new owner. Session
and accessibility bus IDs, launcher and registry owners stay unchanged. All eight
owned parent/exporter/helper PIDs subsequently disappear. Selection bytes remain
unchanged and no keyboard/pointer input is sent. No GTK focus-event, widget or
product input acceptance is inferred from the synthetic tree's role/state values;
its serial stays zero and it emits no focus events.

The exporter follows pinned upstream [Application](https://github.com/GNOME/at-spi2-core/blob/66707c370bef824ed4edb08a909fc6a61449c12c/xml/Application.xml),
[Accessible](https://github.com/GNOME/at-spi2-core/blob/66707c370bef824ed4edb08a909fc6a61449c12c/xml/Accessible.xml)
and [Socket](https://github.com/GNOME/at-spi2-core/blob/66707c370bef824ed4edb08a909fc6a61449c12c/xml/Socket.xml)
contracts: actual two-word state bitmasks, private bus unique-name references,
one Embed per connection and empty P2P bus address. This is selected-application
owner loss, not launcher/registry replacement or full accessibility-tree fidelity.
The separate isolated native-daemon fixture below now proves global service
fences; existing owner/guest services are not restarted for this proof. Production
GNOME discovery/keyboard/pointer remain disabled.

## Isolated native launcher, registry and bus replacement

[The executed service-fence report](../release/qualification/next-targets/20261002-isolated-native-a11y-services.json)
adds three cases in a separate Fedora44 container using shipped native binaries:
registry replacement with the exporter process and selected owner still alive;
launcher termination with coupled accessibility-bus loss; and accessibility-bus
termination with coupled launcher loss. Each retired helper refuses reuse. After
native services are restored, a fresh helper pins the replacement identities and
reads the synthetic two-node exporter. Registry-only replacement keeps session/
accessibility bus IDs and launcher identity unchanged. The coupled cases preserve
the private session bus while changing launcher owner and accessibility bus ID.

The native launcher/registry hashes exactly match the original Fedora GNOME guest.
Recorded package headers identify at-spi2-core2.60.7-1.fc44, dbus-daemon1:1.16.2-1,
gsettings-desktop-schemas50.1-1, gobject-introspection1.86.0-3 and PyGObject3.56.3-1
with Fedora44 key signatures. DNF installs use GPG checks in the separate image.
The [published fixture recipe](../release/fedora-a11y-service-fixture.Dockerfile)
differs from the executed recipe only by its added copyright comment; both hashes
are recorded. [The bounded probe](../release/probe-a11y-service-replacement.py)
requires the exact owned marker, ordinary UID1000 and native binary hashes.

Run in a NEW owned container with Docker --init, networknone, no host mounts/
devices/privileged mode, all capabilities dropped, no-new-privileges, two CPUs,
2GiB and256 PIDs. Stage the exact probe, probe-gnome-a11y-owner.py and helper/service
files together under /work. The CLI requires a new /work proof root and --case
registry, launcher-bus or accessibility-bus. Each creates a separate native
DBus session/private0700 runtime directory, unsets inherited display/a11y/startup
bus variables and uses the memory GSettings backend. It starts native daemons
manually, without GNOME-session registration, and terminates only recorded owned
PID/start identities. Exported roles/states are synthetic; no focus events, UI
input, real GNOME compositor or product service restart is exercised.

The first image refused missing GSettings schemas. The second started daemons but
refused the missing DBus1.0 typelib; an actual Fedora package-provider query
identified gobject-introspection. The third passed native owner fences but left
exited forked bus children as zombies under sleep PID1. These failures/observations
remain retained. The fourth uses Docker init to reap orphans and passes all three
cases, with every recorded native-bus, launcher, registry, exporter and helper PID
confirmed absent afterwards. Source/native-library/package/recipe identities and
raw report hashes bind the evidence. Closure durations after native loss are
0.0034s/0.0013s/0.0014s for registry/launcher/bus requests, not physical-input latency.

The existing GNOME guest and owner services/devices/models/audio are unchanged.
This proves native helper fences in isolated sessions. Real GNOME service restart,
shell/controller integration, inaccessible/ambiguous trees, native per-action
widget/lock/Stop outcomes and other supported profiles remain open. Production
GNOME discovery/keyboard/pointer remain disabled.

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
The separate [read-only helper proof](../release/qualification/next-targets/20261002-gnome-native-accessibility.json)
now verifies ordinary-user GTK Wayland and XWayland targets, real callback-thread
identity, focus-away/back serial changes, password roles, discovery after helper
startup and process-disappearance refusal. Its parent hard deadline and cancellation
dispose a stalled child; all14 synthetic socket/protocol tests are separate evidence.
The original incomplete query and a later transient XWayland tree refusal remain
preserved. Production discovery still returns no focus and keyboard/type refuses.

[GTK4.22.5 collect_states](https://github.com/GNOME/gtk/blob/4.22.5/gtk/a11y/gtkatspicontext.c)
exports SENSITIVE from disabled state and omits ENABLED. The helper retains both raw
flags. Focus/showing may survive while another application covers the target; the
future controller must independently bind the shell's selected/active window and
geometry to the same PID, owner, epoch and fresh event serial. These facts are not
permission to type. Selected application owner loss now passes the separate
synthetic native-bus proof above. Isolated native-service replacement now passes the proof above; real GNOME
service restart, inaccessible
and ambiguous native trees, per-character/Stop/lock guards and matching GNOME/KDE
regressions remain open. The GUI process's singleton is untouched.

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

## Existing Fedora artifact admission

[The first input-candidate admission](../release/qualification/next-targets/20261003-fedora-gnome-old-payload-target-refusal.json)
refuses the preserved old native/selected payload metadata before any staging or
input. Both old release records still declare Debian13 although Fedora package
records declare Fedora44. Current packaging rewrites that target. The guard is
retained; a matching native/managed update and exact dependency/pending-transaction
review must complete before this candidate runs. No selected payload is patched.

The [owned clone adoption and first import refusal](../release/qualification/next-targets/20261003-fedora-gnome-clone141-adoption-input-import-refusal.json)
preserves the original VM's daemon-prepared offline update by normally powering
it off and using a separate thin clone. Both original backing disks remain
read-only with unchanged full SHA256; the original must stay off while any
dependent overlay is reusable. The clone installs the exact clean2035 Fedora
RPM through normal DNF, with eleven reviewed required dependencies and their
verified Fedora signatures. Only the clone's copied pending transaction is
invalidated. Native audit, protected settings and canonical managed
stage/activate/cold launch pass. Both new release records declare Fedora44;
the old selection is retained as previous, and strict candidate admission passes
without changing any guard.

The first exact0ab eleven-file candidate then fails before Qt/banner/portal
creation: portal.py cannot import kwin because the probe appends the verified
installed dependency path after GnomeControl import. The native GTK Wayland
target remains empty, both click counts and its save count remain zero, no
trigger or saved file exists, and independent cleanup confirms probe/target and
candidate helpers are absent. No consent or input was sent. The maintained
probe now resolves that dependency before controller import; its source-only
fix and import regression are review evidence, not a corrected native pass.
A fresh candidate directory and explicit reviewed probe revision/hash are
required for the next run; controller/helper bytes remain the reviewed0ab
candidate. Production GNOME discovery and input remain disabled.

## Corrected-probe consent pass and first capture timeout

The [fresh v2 checkpoint](../release/qualification/next-targets/20261003-fedora-gnome-v2-consent-pass-capture-timeout.json)
stages only probe4abe16a with the other ten files still exact0ab. Strict native
and selected source2035/Fedora44 admission passes against managed inventory
SHA53813618. The corrected import reaches the installed xcb banner and actual
Remote Desktop dialog. Its native portal PID/owner and foreground geometry are
checked before the observed interaction and Share actions. Connect reports
sharing=true after the existing keyboard/pointer/single-monitor checks; GUI
ticks continue during consent. This is real consent evidence, not widget input.

The first explicit capture fails after2.224seconds and closes sharing. Its
retained first failure is idle-watch / Error / g-io-error-quark timeout24;
cleanup completes in0.544seconds, with stopClicked=false. Both buffers remain
empty, center/edge/save counters stay zero and no saved file exists. Independent
checks find probe, target and candidate helpers absent; selected bytes and both
frozen original backing hashes are unchanged. A post-target-exit cleanup scanner
error on nonprocess /proc/dma is retained separately, followed by an independent
numeric-process scan; no SIGTERM or failed capture is replayed.

Fresh owner/scene readback remains valid. PipeWire logs target-not-found and
Broken-pipe messages overlapping teardown; they do not identify the first
failure's cause. Existing idle-watch reporting cannot distinguish its session
verification from the observer's owner/read calls. The failed operation remains
failed; pointer/chord/ASCII/save/visibleStop acceptance is still open.

The maintained probe adds optional `--trace-idle-watch` for the next reviewed
fresh diagnostic run. A probe-only subclass delegates the unchanged idle watcher
and temporarily wraps only its existing session/observer connections. It records
each synchronous GetNameOwner and observer Read method, verification/read stage,
public lookup alias, configured timeout and elapsed time, plus native error
kind/domain/code. It forwards the exact flags, parameters, cancellation object,
reply and exception without another RPC. Cleanup methods delegate normally;
captured connections are restored even after Stop detaches/disposes the objects,
without restoring sharing. No controller, observer, session, helper, production
guard or timeout is changed.

The current [session owner check](../services/desktop/portal_session.py) uses
1000ms; the [observer](../services/desktop/gnome.py) uses500ms for Shell owner
checks and1000ms for Read. The [GIO API reference](https://docs.gtk.org/gio/method.DBusConnection.call_sync.html)
documents milliseconds and synchronous blocking; the trace records the bounds
actually passed by these staged modules. It keeps the latest128 calls plus the
first error independently, recording rollover and diagnostic-sink failures.
It exports no RPC reply/parameter payload, accessible text or screenshot bytes.
Tracing defaults off. Synthetic tests exercise the actual maintained watcher,
session verification and observer read, preserving terminal timeout cancellation,
the original error, bounded history, detached cleanup and no retry. Those tests
do not diagnose the v2 timeout or qualify native input. The diagnostic probe
requires parent review/publication and a new private candidate before execution;
it has not run in the VM.
