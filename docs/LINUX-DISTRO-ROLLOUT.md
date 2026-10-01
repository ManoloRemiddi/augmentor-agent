<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Linux distribution rollout

## Objective and preserved contracts

Owner-authorized implementation, 1 October 2026: extend the same Augmentor
Desktop and Browser product to Fedora, Ubuntu and other major Linux distributions.
Baseline: public `main` at `8c3be5a`, product 0.2.13. Work occurs in a separate
canonical-repository worktree; the modified original checkout and installed
releases are preserved. Source changes do not activate an installed build.

The [platform contract](PLATFORM-PARITY-AUDIT.md) still applies. Keep the approved
UI, two independent instances, shared harness lifecycle, model selection, memory,
speech and history semantics. Missing desktop adapters remain unfinished parity
work; usable chat is an intermediate milestone, not completion of this rollout.
Preserve consent, fresh target identity, focus/occlusion refusal, independent Stop,
held-input release, active-work maintenance refusal and no replay after an unknown
outcome. Do not change the owner's model/GPU/audio services to run fixtures.

## Targets and release dimensions

First qualify x86-64 Debian 13 (regression), Ubuntu 26.04 LTS and Fedora 44,
with GNOME Wayland and Plasma Wayland/X11 as applicable. Next qualify Ubuntu
24.04 LTS/Mint 22.x, openSUSE Leap 16/Tumbleweed and a dated Arch snapshot.
Fedora 43 is an additional first-family target while maintained. ARM64 is a
separate artifact/qualification extension: current native payloads are x64.
Atomic Fedora and sandboxed browsers require explicit installation/channel
qualification; they must not inherit ordinary RPM/native-browser evidence.

Track separately: implemented source; package installation; real chat and Browser
connection; desktop/session behavior; optional voice/memory; published artifact;
selected versus running installed build. A container/offscreen pass proves neither
Wayland control nor microphone quality. Upstream support is not our acceptance.

## Ordered implementation and acceptance

1. **Installer and packaging** — extract OS/version/architecture detection and
   apt/dnf dependency plans from `setup-complete.py`; keep DSH/plugin/model/private
   setup shared. Make `--plan` read-only and include exact selected packages.
   Refuse mismatched bundle targets before creating private state. Generate
   current Fedora RPMs from verified current payloads, with provenance, Qt
   Quick/QML dependencies and lifecycle protections. Assemble target-aware complete
   bundles. Verify ordinary-user install/resume, real DSH integration, native
   rendering, extension registration, active-work refusal and removal retention
   in pinned Ubuntu/Fedora containers. Preserve legacy Debian bundle support.
2. **Capability selection** — inspect desktop/session, available D-Bus interfaces,
   interpreter/runtime and browser channel. Report actual backend availability
   independently of live permission and successful operation. Test unavailable
   dependencies and compositor combinations; do not advertise KDE execution on
   every Linux system. Keep Linux-only adapter changes from altering macOS.
3. **Shortcuts and startup** — probe GlobalShortcuts versions and use a qualified
   native adapter where the portal cannot preserve editable Save semantics (GNOME
   50 advertises version 1). Preserve choices, conflicts, two instance IDs,
   session reconnection and actual activation delivery. Preserve KDE KGlobalAccel
   and macOS adapters.
   Provide an owned launcher fallback for unsupported sessions and closed-app
   launch. Qualify login/logout/reboot/crash recovery and prevent duplicate
   autostart/service owners. Test GNOME and KDE in disposable full desktops.
4. **Window and GNOME control adapters** — preserve floating UI placement,
   workspace following and independent Stop on GNOME; qualify XWayland and use
   supported native activation/move/resize where needed. Separate portal capture/
   input transport from KWin observation. Implement a GNOME target-observation
   adapter with the existing identity/focus/occlusion checks; do not use unsafe
   GNOME Eval or simply delete the KDE guard. Prove consent refusal/revocation,
   successful harmless save, changed/covered-window refusal, scaling and Stop
   during consent/input on both supported desktops. Multi-monitor/Unicode limits
   remain explicit existing product boundaries unless separately implemented.
5. **Older Ubuntu/Mint runtime and other packaging** — build a pinned isolated
   Qt/Python runtime or maintained dependency package for Noble-based systems.
   Preserve replaceable Qt libraries and exact redistributed-source/notices
   obligations; bridge system GI/PipeWire deliberately. Validate native component
   ABI requirements on the oldest target. Add separate openSUSE dependency mapping
   and Arch recipe; run the same lifecycle and actual desktop/browser checks.
6. **Browser, voice and memory qualification** — verify Chrome/Chromium native
   host handshake and real sidebar chat for each declared package channel. Audit
   Snap/Flatpak confinement before extending claims. Probe audio route, PortAudio,
   Pulse compatibility/ALSA plugin and echo-cancel support; exercise capture and
   playback in isolated fixtures and identify physical acceptance separately.
   Provide tested distro container-engine installation for optional Hindsight,
   retaining stores and controlled processing. Test Fedora with SELinux enforcing;
   add policy only for a reproduced denial. Do not replace an existing engine.
7. **Release and handoff** — run shared regressions and both OS impact checks;
   publish reviewed source/docs in the canonical repository and attach its PR.
   Produce checksummed, provenance-recorded candidates from one clean revision;
   expand public compatibility only for completed gates. Promotion to an owner's
   installed machine uses `augmentor-update`, never source-folder launchers.

## Completion evidence required

For each declared target, record OS/image digest, architecture, Python/Qt/Node
versions, source commit, artifact hash and test command/result. Acceptance covers
fresh-user install, a real harness fixture turn through native and Browser
surfaces, same-chat reopen, two independent instances, actual shortcut activation,
window/workspace behavior, session restart/reboot, recovery, upgrade, rollback,
interrupted setup/configuration and removal with private state retained. Desktop
control needs full-session consent/input/target/Stop evidence. Optional voice and
memory status must distinguish provisioning, synthetic tests and physical use.
Each unfinished item remains open; passing an earlier stage does not complete the
goal. Keep remaining gates and next commands in this guide and the handoff.

## Initial verified findings and sources

- `setup-complete.py` accepts only Debian 13 amd64 and installs with apt.
- Fedora's historical 0.2.9 RPM has container evidence, not current-product or
  real-desktop acceptance: [preview](FEDORA-PREVIEW.md).
- [Ubuntu's PySide6 catalog](https://packages.ubuntu.com/python3-pyside6.qtcore)
  provides Resolute 26.04, not Noble 24.04. [Mint 22.x](https://linuxmint.com/download_all.php)
  uses Noble. PyQt6 is not a replacement for PySide6 imports.
- [Fedora PySide6](https://packages.fedoraproject.org/pkgs/python-pyside6/python3-pyside6/)
  differs from Debian's tested bindings; qualify Python as well as Qt.
- [GlobalShortcuts](https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.GlobalShortcuts.html)
  sessions belong to a running app. [RemoteDesktop](https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.RemoteDesktop.html)
  transport does not replace Augmentor's KWin window observations.
- [Qt Wayland positioning](https://doc.qt.io/qt-6.8/application-windows.html),
  [systemd desktop integration](https://systemd.io/DESKTOP_ENVIRONMENTS/),
  [native messaging](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging)
  and [Flatpak permissions](https://docs.flatpak.org/en/latest/sandbox-permissions.html)
  govern integration choices; test deployed implementations.

## Progress ledger

Planning and initial apt/dnf package adapters are implemented. The installer
requires the bundle's explicit distro/version/architecture, supports read-only
`--plan`, records its system plan and avoids installing another Docker engine
when a Docker executable already exists. Voice build dependencies follow the
selected feature flags. These are candidate adapters, not completed acceptance.

Fedora packaging consumes checksum-verified current Debian payloads, validates
matching runtime/desktop versions and source, retains the payload's lifecycle
implementation, records the maintainer-source hash and emits standard artifact
metadata. Python-dependent guards use `%pre` rather than `%pretrans`: Python can
then be provisioned in the same fresh-install transaction. This corrects a real
Fedora 44 fresh-install failure; see [RPM scriptlet ordering](https://rpm.org/docs/4.20.x/manual/lua.html).
A shallow installation path no longer makes Linux shortcut activation compute
a nonexistent macOS parent directory; installed Mac launch selection is retained.

Initial disposable-container evidence, against the working source based on
`8c3be5a` (not a clean release candidate):

| Gate | Ubuntu 26.04 | Fedora 44 |
| --- | --- | --- |
| Python / PySide / Qt | 3.14.4 / 6.10.2 / 6.10.2 | 3.14.7 / 6.11.2 / 6.11.2 |
| Bundled Node | 24.19.0 | 24.19.0 |
| Complete native suite | 560 tests, 2 skips, pass | 560 tests, 2 skips, pass |
| Ordinary-user offscreen render and runtime lease | pass | pass |
| Active-component maintenance refusal, idle retry, removal retention | pass | pass |
| Complete fresh-user DSH/plugin setup and fixture turns | pending | pending |
| Actual GNOME/KDE, graphical Browser, physical voice, SELinux | pending | pending |

The shared Node suite passes 207 tests. The host native run lacked QtTest; native
acceptance above uses each target's actual distro bindings, with test-only Git and
Node paths supplied explicitly. Container dependencies differ from host-installed
dependencies. Ubuntu's first install and Fedora's fresh Python/package transaction
passed. An already installed container was reused for Ubuntu lifecycle checks;
final candidate evidence must separately record whether its install was fresh.
Debian retains separate desktop/headless runtime packages: removing an unlocked
desktop while runtime is active is allowed; removing the leased component is
refused. Interrupted multi-package operations are retried while idle before
starting another component. Private files remain after package removal.

[Pinned base images](../release/linux-images.json) make the environment explicit;
repository package updates still need their actual versions recorded. Fedora 43
is catalog-checked separately; it has not inherited Fedora 44 acceptance.
[Package proof](../release/prove-linux-package.py) checks checksums, source,
ordinary-user rendering, both leases and real package-manager lifecycle operations.
[Complete proof](../release/prove-complete-linux.py) installs the bundle's exact
system plan, runs setup as an ordinary user, exercises both installed DSH roles
against a localhost model fixture and checks history/repeat-run preservation.
Its Browser-role adapter turn does not prove a graphical extension session.
Both scripts refuse execution outside a disposable container. Minimal container
images need Python installed to run the proof driver; this is test instrumentation.

Next: commit reviewed source, rebuild matching Desktop/Browser/RPM artifacts and
assemble complete bundles with the pinned standalone plugin source refs. Run
both proofs from those clean candidates, plus Debian regression, then publish
the source branch and draft PR. All desktop/older-runtime/other-distro stages
above remain open. The build host has Docker/Podman and QEMU, but no `/dev/kvm`;
full desktop VM work may use TCG. No public compatibility claim or installed
deployment has changed.

### Clean-source qualification checkpoint

Candidates built from clean `58150e58d4ca24e5034dd598a1231a64b28e8b2f` are now
assembled for Ubuntu 26.04 and Fedora 44 with the exact pinned Voice/Adaptive
source archives. Both actual ordinary-user setups install DSH and all three
plugins, render the native UI, register the matching Browser host, preserve
settings on repeat, complete Desktop/Browser-role fixture turns and retain
history on DSH restart without another model request. This exercises actual
installed adapters and roles, not a graphical browser. Corrected test
instrumentation is tracked in the follow-up source commit: DSH's persistence
normalizes an omitted `delegationDepth` header field to zero on reload. Its
upstream persistence and header equality code explicitly use that default;
every saved event and every other header field is still compared exactly.

Debian 13 clean-package regression passes fresh install, both component leases,
rendering, idle retry/removal retention and the full 560-test native suite
(two skips), with Python 3.13.5/PySide 6.8.2.1/Qt 6.8.2. Fedora 43 also installs
the current RPM and passes lifecycle/rendering and all 560 native tests (two
skips): Python 3.14.7/PySide and Qt 6.10.3. Its default npm provider is
`nodejs-npm` 10.9.7, while Fedora 44 uses `nodejs24-npm`; both application
runtimes continue using the pinned private Node 24.19.0. A new CI matrix runs
these package/native checks on the three added targets after building the
existing Debian artifact. Hosted CI execution remains to be confirmed.

Next source checkpoint includes the proven fixture-header normalization, fresh
container/source verification, proof-driver hashes and corrected Fedora 43
package mapping. Rebuild all candidates from that clean ref before final
complete-installer acceptance, including Fedora 43 and Debian. GNOME integration
and the remaining rollout stages stay open.

### Current-main integration

Canonical main advanced to `d91c520` with the shared Codex integration during
qualification. Merge `4183895` retains that product, both handoff histories and
the new distro CI job. Earlier `58150e5`/`a76fcda` candidates are historical
foundation checkpoints, not the final candidates for current main.
Type/build checks pass. Debian's complete 484-case Node suite now passes (482
pass, two opt-in skips), using actual Chromium, the declared locked DSH modules
and distro QtTest. Merged native checks pass on all four targets; Debian/Fedora 44
ran 607 tests before three source-reuse cases were added, Ubuntu/Fedora 43 ran
610. The next candidate qualification repeats the full current suite.

The RPM now includes the same native Secret Service dependencies as Debian:
`python3-keyring >= 25.6`, `python3-secretstorage`, `gnome-keyring`. Actual Fedora
43/44 repository catalogs provide these versions. Codex remains an external
0.159.2 prerequisite; supplier binaries, sign-in and subscription eligibility
are not provisioned or changed by this rollout. Keyring/live-session checks and
the upstream Codex acceptance gates remain explicit.

New complete bundles use `--source-bundle` to reuse the exact source snapshots
already published in the [0.2.13 complete preview](https://github.com/ManoloRemiddi/augmentor-agent/releases/tag/v0.2.13-complete-preview.1).
The downloaded archive verifies against published SHA-256
`6c327d99b04796f2901850364670aa61015b17f739582c64126421858b56b65d`;
the contained Voice/Adaptive snapshots verify against its bundle manifest.
Reusing those bytes preserves the approved private-dependency publication
boundary. No new source is copied from the private Voice repository. The new
manifest records the originating bundle ID/hash and source refs, while the
application snapshot still comes from the clean public source revision.

Next: commit this merged packaging correction, rebuild all candidates using the
checked published snapshots, run package/complete proofs on all four targets,
and publish the reviewed branch/draft PR. Fedora 44's complete 484-case Node suite passes (482 pass, two opt-in memory
skips), with the distro's `/usr/bin/chromium-browser`, test-only `procps-ng`,
locked DSH and QtTest. Its loaded extension performs actual observed typing,
clicking and screenshots in an isolated headless profile. The cancellation
fixture now waits for its first provider request with a bounded deadline,
replacing a one-second startup assumption while preserving cancellation,
maintenance fencing and no-replay assertions. The focused six cases pass too.
The actual Fedora Chromium executable contains `/etc/chromium/native-messaging-hosts`,
matching the standard system registration; default graphical profile registration
still needs the desktop acceptance stage. These checks do not qualify GNOME,
KDE, physical audio or enforcing SELinux.

### October 2 matching-candidate qualification

Clean source `a5d27c3053f3015dad27af3da8e39b53f63ccde7` builds matching Debian,
Fedora 43/44, Browser and all four complete bundles. Artifact/private-state/native
notice review passes. [Checked qualification reports](../release/qualification/a5d27c3/)
record exact package hashes, proof-script hashes, source, base-image digests,
dependency-cache provenance, runtime versions and separately qualified dimensions.
Old Augmentor payloads were removed in disposable containers before fresh installs;
these runs reuse dependency caches derived from the pinned bases.

Debian 13, Ubuntu 26.04, Fedora 43 and Fedora 44 all pass both component leases,
active maintenance/removal refusal, idle reinstall/removal retention, ordinary-user
complete setup/repeat preservation, real installed DSH/plugins, both role fixture
turns and restart/history preservation without replay. Every target passes 610
native tests (two Mac-only skips). Actual isolated Secret Service proofs also pass
on each target, including update, reference isolation, token rotation, restart,
logout and complete synthetic-entry cleanup. Fedora's minimal container needed
test-only `dbus-daemon` to supply `dbus-run-session`; its first proof attempt and
successful continuation are both recorded. Production graphical Fedora uses its
existing session bus; this test dependency is not an installer prerequisite.

These reports qualify the installer/package foundation. They do not qualify
actual GNOME/KDE sessions, default graphical Browser connections, physical voice,
memory provisioning, enforcing SELinux or older/other distros. The source-only
Debian/Fedora Node checks above remain separate from installed-candidate evidence.
Next: publish this foundation for review, then replace unconditional Linux backend
advertising with actual session/dependency/interface discovery before the GNOME
shortcut and observation adapters. Installed application/model/audio services
remain unchanged.

### Session discovery implementation

Desktop availability now comes from the selected Python interpreter's read-only
probe, shared by Pi, Codex and DSH registration. A KDE Wayland backend requires
its graphical session environment, an XWayland display for independent Stop,
Qt Widgets/GI/AT-SPI/GStreamer plus `pipewiresrc`, already-owned portal interfaces
advertising keyboard/pointer and monitor capture, and KWin's scripting interface
on running KWin 6.3.6 or later in the qualified major 6 API family. The KWin
version is read through `supportInformation`; only its version is used and no
hardware information is returned. The probe uses bounded D-Bus calls to unique
service owners without activation and opens no sharing session or observation.
[Portal properties](https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.RemoteDesktop.html)
and the [KWin observer API](https://develop.kde.org/docs/plasma/kwin/api/) remain
separate from live permission and successful control.

The desktop client and discovery share the same graphical environment allowlist
from the user's own manager, so an externally launched DSH process can discover
the logged-in session. No unrelated manager variables or private bus address
are returned. Discovery failure returns a reason instead of enabling input.
Results are cached for five seconds with environment changes invalidating the
cache. An inactive portal is unverified until it owns its bus name; discovery
does not launch it. DSH registration is fixed for that plugin lifetime; restart
its host after session/portal changes. Later shortcut/session recovery work
must address portal readiness and host registration refresh.

GNOME, X11 and headless sessions do not inherit the KDE input adapter. Pi and DSH
retain Stop while omitting unavailable input/delegation tools; Codex gates new
immutable desktop contracts by the same result. Existing Codex histories keep
their saved tool contracts and cleanup behavior. Mac helper discovery and live
permission gates are preserved. Synthetic OS-boundary tests inject availability
through internal constructors instead of inferring it from the operating system.

The working capability source passes type/build, 617 native cases per target
(two Mac-only skips), 490 Fedora Node cases (488 pass, two optional memory skips),
42 focused common/Pi cases and the real DSH/Pi synthetic memory lifecycle check.
Each headless target's actual probe reports unavailable. Read-only live discovery
on the existing KDE host observes KWin 6.3.6 and the required portal capabilities
without consent, screenshots or input. The last version-gating assertions also
pass the focused seven-case native discovery suite. Mac CI at the prior installer
checkpoint passes both macOS 14 and 26; current capability-source hosted CI still
needs confirmation. No new matching release artifacts have been built for this
capability source yet; `a5d27c3` reports above remain the installer checkpoint.

Initial Linux CI for the installer checkpoint failed at the memory restart
fixture after 489 passing Node cases. Inspection confirms socket removal can
precede interpreter exit/startup-lock release. That fixture now waits for the
old process to exit before restarting, while retaining all persistence, freshness
and no-custom-distillation assertions. The focused actual lifecycle check passes.
This test synchronization change does not qualify optional memory provisioning
or change the production companion's startup behavior. The next CI run confirms
its effect in the hosted environment.

Next source stage: actual GNOME/KDE session fixtures and the owned shortcut portal
adapter, followed by trusted GNOME window/occlusion observation. Backend discovery
does not complete those adapters or the remaining distro/hardware acceptance.

### Hosted capability checkpoint and GNOME fixture preparation

Source `89c7f507954a5fbb8723338a02156a7c28106c81` passes
[macOS 14/26 hosted CI](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36934724347).
The [Linux hosted run](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36934724286)
passes the root Node/memory lifecycle checks and reaches actual DSH/Qt setup; its
remaining failure is the old assertion that every Linux session must advertise
`linux_desktop_snapshot`. The setup proof now checks registration against observed
availability and always checks Stop. The full isolated Fedora DSH/Qt proof passes,
including preserved original profile, both personal surfaces, saved chats, actual
approval reject/allow/cancel, question delivery and exact branching without replay
(16 fixture requests). Hosted Linux acceptance for that correction remains pending.


### October 2 hosted corrections and fresh GNOME discovery

At `c964fd59c85d3f434dd1ded26bc6ab9bdb953bdc`, [Linux CI](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36936210109)
passes source, Home, Debian source/DSH/Qt, installed Debian lifecycle and packaged
Browser acceptance. All three distribution jobs pass their actual package proof,
then fail two native tests because the source checkout lacks compiled JavaScript.
The matrix now archives only committed public source for test instrumentation and
uses the installed payload's `dist` and production dependencies for those tests.
No tests are skipped. [Mac CI](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36936210260)
fails the new availability assertion because it probes the source helper while
DSH loads the packaged helper. Discovery now runs from the same application root.
These corrections still need hosted confirmation; `89c7f50` retains its earlier
passing Mac evidence.

Complete setup now compares installed `release.json` source/clean status/version
with its bundle before per-user runtime and credential writes, including the
internal skip-packages fixture path. This catches package managers retaining an
older payload with the same product version. Existing completed receipts preserve
the repeat-run contract. Seven focused setup tests pass, including actual setup
refusal before private data/configuration creation.

A fresh pinned Fedora 44 image runs GNOME Shell/Mutter 50.5, portal 1.22.1,
GNOME portal backend 50.0, PipeWire 1.6.9 and WirePlumber 0.5.18. The
[checked discovery report](../release/qualification/gnome50/fedora44-discovery.json)
records script/image/interface hashes. The compositor's D-Bus owner PID matches
our child. Its actual portal advertises RemoteDesktop 2, ScreenCast 5 and
GlobalShortcuts 1. This ordinary-user session uses a private bus, software virtual
monitor, no host devices and no network. GNOME's built-in dummy login manager is
explicit test infrastructure: input, consent and real login/reboot are untested.

Build without a repository context:

```sh
docker build -t augmentor-gnome-discovery - < release/gnome-discovery.Dockerfile
mkdir -p outputs/gnome-discovery
docker run --rm --network none --cpus 4 --memory 6g --tmpfs /run/systemd \
  -v "$PWD:/work:ro" -v "$PWD/outputs/gnome-discovery:/reports" \
  augmentor-gnome-discovery sh -c '
    set -eu
    mkdir -p /run/dbus
    dbus-uuidgen --ensure
    dbus-daemon --system --fork
    useradd -m -s /bin/sh augmentor-session-proof
    runuser -u augmentor-session-proof -- sh -c '\''
      mkdir -m 700 "$HOME/runtime"
      export XDG_RUNTIME_DIR="$HOME/runtime" DISPLAY=:0
      dbus-run-session -- python3 /work/release/prove-gnome-discovery.py --out "$HOME/gnome-proof"
    '\''
    cp -r /home/augmentor-session-proof/gnome-proof/. /reports/
    rpm -q gnome-shell mutter xdg-desktop-portal xdg-desktop-portal-gnome pipewire wireplumber > /reports/packages.txt
  '
```

Do not treat introspected `ConfigureShortcuts` as editing support. The
[tagged portal implementation](https://github.com/flatpak/xdg-desktop-portal/blob/1.22.1/src/global-shortcuts.c)
requires backend version 2; the
[GNOME 50 backend](https://github.com/GNOME/xdg-desktop-portal-gnome/blob/50.0/src/globalshortcuts.c)
advertises version 1. The
[tagged settings dialog](https://github.com/GNOME/gnome-control-center/blob/50.0/global-shortcuts-provider/cc-global-shortcut-dialog.c)
restores existing app/shortcut IDs and ignores changed preferred triggers. A new
session with the same IDs therefore cannot implement our existing Save action.
Human trigger descriptions are localized and are not machine-readable bindings;
portal success also does not establish delivery. The next shortcut adapter must
preserve the approved two-row Save semantics through a separately qualified
native GNOME mechanism, or record the parity gap. No GNOME input tools are enabled
by this discovery fixture.


### Native GNOME shortcut mechanism and final fixture corrections

[Mac CI at clean `5d97cf5`](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36938051200)
passes both macOS 14 and 26, including the packaged-helper availability check.
[Its Linux run](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36938051206)
passes Home/source boundaries but catches another fixture race: Browser voice PCM
can arrive before native turn completion durably updates the queue. The test now
waits, with its existing bounded deadline, for the actual completed queue record;
request identity, one model request and exactly one operation remain asserted.
All seven focused Codex voice cases pass in the Fedora native/Node fixture using
an independently authored synthetic voice peer, never private speech source.

The distro matrix also needs the separately installed Codex prerequisite for its
real idle-host maintenance test. It now installs the exact locked development
supplier package in a disposable `/tmp` prerequisite directory and selects it
explicitly. It does not add supplier files to the production payload. A local
reproduction using the actual CI `c964fd5` RPM payload, committed `5d97cf5` test
instrumentation and a separate pinned supplier passes all 619 native cases
(617 pass, two Mac-only skips). Installed compiled JavaScript and production
modules are used; the original checkout provides no missing source build files.
This is fixture validation across those stated revisions, not a newly qualified
complete candidate. Hosted Linux confirmation for the final corrections remains
open.

The native GNOME mechanism is now exercised through GSD MediaKeys 50.1 in the
same isolated Shell/Mutter 50.5 compositor. The
[checked mechanism report](../release/qualification/gnome50/fedora44-custom-shortcuts.json)
records exact proof hashes. Two custom bindings independently execute synthetic
commands; changing one releases its former combination, clearing one stops its
delivery, and a real daemon restart restores the persisted assignment. An unrelated
custom path and all its values survive. The proof uses one persistent private
Mutter connection and verifies compositor ownership before injecting synthetic
press/release events. The
[tagged Mutter input API](https://github.com/GNOME/mutter/blob/50.5/data/dbus-interfaces/org.gnome.Mutter.RemoteDesktop.xml)
is fixture infrastructure only; product control still requires the consent portal
and trusted observation.

The fresh user's modal welcome tour initially prevented normal shortcut delivery.
Only the disposable fixture marks that tour as previously shown before launching
Shell, matching the [tagged startup behavior](https://github.com/GNOME/gnome-shell/blob/50.5/js/ui/main.js).
Another fixture error retained Gio.Settings delay mode after an initial apply;
subsequent changes now explicitly apply before testing the old binding. These
failures are preserved in local logs; no failed run is described as a pass.

Repeat the discovery command above with `--exercise-custom-shortcuts` added to
its Python invocation. This tests the native mechanism with synthetic commands,
not our production adapter or actual Augmentor launch/focus. It does not qualify
physical keys, real login/reboot, consent or all conflicts. The production adapter
must use stable owned paths, preserve foreign settings, check writability and
normalized known conflicts, and save the canonical per-user launcher. The
[tagged GSD implementation](https://github.com/GNOME/gnome-settings-daemon/blob/50.0/plugins/media-keys/gsd-media-keys-manager.c)
does not acknowledge asynchronous custom grabs to applications. Retain the
existing “Saved. Press the shortcut to test this window” contract; never infer
active delivery solely from settings readback. GNOME shortcuts and trusted window/
modal/chrome observation remain the next production implementation stage.

### October 2 native GNOME Save adapter

The production shortcut path now routes GNOME sessions to
[`services/desktop/gnome_shortcuts.py`](../services/desktop/gnome_shortcuts.py)
through a bounded worker using the native window's selected Python. It requires
an owned live Shell/MediaKeys session, GNOME 50, GTK 4 GI and the actual graphical
display/settings schemas. Missing prerequisites produce an explicit unavailable
state in the existing rows. KDE KGlobalAccel and the Mac adapter retain their
paths; the shared capture fields, Save controls and layout are unchanged.

Each row owns a stable custom-keybinding path and saves the absolute canonical
`~/.local/bin/augmentor-agent` launcher, with `--instance secondary` for the second
window. Foreign commands/occupied paths and locked settings are refused. GTK
converts structured Qt key/modifier identities; system, custom and persisted
portal assignments are checked using normalized key symbols and hardware codes.
Saved portal assignments come from the machine binding arrays, not localized
trigger descriptions. Unsupported keypad/AltGr modifiers and unrepresentable
bindings are explicit errors; full physical keyboard/layout qualification remains
open. Saves serialize our writers, merge the latest parent path list and verify
actual persisted values. A failed registration restores only matching owned
fields and retains unrelated concurrent additions or a foreign takeover. This
does not promise atomic exclusion of all external settings writers.

The [checked adapter report](../release/qualification/gnome50/fedora44-augmentor-shortcuts.json)
records exact production/fixture hashes and packages: GNOME Shell/Mutter 50.5,
GSD 50.1 and PySide6 6.11.2. Actual shared Qt Save button clicks write the real
private dconf backend and GSD delivers both assignments. Changing, disabling and
restarting the daemon retain the previously proved behavior. Tests refuse actual
system/custom/portal/hardware-key conflicts, preserve a foreign owned-path
command, and inject a registration failure after real writes to verify rollback
and preservation of a concurrent foreign addition/takeover. The canonical path
contains an independently authored activation marker, not the actual Augmentor
process. The form uses Qt offscreen; GTK and shortcut delivery use the real
private Wayland compositor. Actual closed-app launch/focus, physical input,
login/reboot, portal consent and GNOME observation/control remain unqualified.
Settings readback always returns `functionalTested: false`.

Reproduce the adapter fixture by building the discovery image above, then its
test-only Qt layer without sending repository contents as a build context:

```sh
docker build -t augmentor-gnome-shortcuts \
  --build-arg GNOME_BASE=augmentor-gnome-discovery - < release/gnome-shortcuts.Dockerfile
```

Run the discovery command above with image `augmentor-gnome-shortcuts` and
`--exercise-augmentor-shortcuts` on the Python invocation. Repository state is a
read-only mount; all settings, launcher files and input belong to the ordinary
disposable user. Package repositories are mutable, so record the resulting image
ID and packages for each run rather than assuming identical resolved versions.

Seven focused GNOME Qt/routing cases and four KDE shortcut cases pass. The native
source suite passes 626 cases (624 pass, two Mac-only skips) before the final
GNOME rollback hardening, which passes the real compositor proof above. The
latest published mechanism checkpoint `4764b6f` passes
[Mac 14/26 CI](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36939492167).
[Its Linux run](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36939492367)
passes root, Home/source, Debian package/installed lifecycle/Browser and distro
package proofs, but all three distro native jobs stop at missing `npm`. The
test-only provisioning now installs verified Fedora 43 `nodejs-npm`, Fedora 44
`nodejs24-npm`, or Ubuntu `npm` before creating the external Codex prerequisite.
Product Node remains the pinned bundled runtime. Current-source hosted Linux and
Mac confirmation remains open until the next clean push is qualified. No
installed release, owner settings or model/audio services were changed.

The adapter is published at `8931cd8a19177d2ab9885abb50fbaa640e5e6ea9`.
A subsequent package-prerequisite audit reproduced missing GTK 4 GI imports in
the historical headless Ubuntu and Fedora package fixtures. Debian Desktop now
requires `gir1.2-gtk-4.0`; Fedora requires `gtk4`, which owns `Gtk-4.0.typelib`.
Actual package installs and API imports pass in disposable dependency fixtures:
Debian 13 GTK 4.18.6, Ubuntu 26.04 GTK 4.22.4, Fedora 43 GTK 4.20.4 and Fedora 44
GTK 4.22.5. These are supplemental dependency proofs against existing image
caches, not newly built Augmentor artifacts or GNOME acceptance on all four
targets. The installed-package proof now checks GTK 4's accelerator API through
the ordinary test user and records its actual version. Current-source package/
complete artifacts remain to be qualified after a clean push.
