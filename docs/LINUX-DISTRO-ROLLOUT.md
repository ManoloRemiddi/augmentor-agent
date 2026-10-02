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

The current adapter report also records a repeated proof after fixing the
private D-Bus activation environment. Python originally set GNOME variables
after `dbus-run-session` started; early Shell/IBus activation could then choose a
generic portal backend. The fixture now propagates only its graphical variables
to its private bus before starting Shell and refuses discovery without
RemoteDesktop 2, ScreenCast 5 and GlobalShortcuts 1. The repeat passes those real
interfaces and every shortcut/rollback assertion. Earlier shortcut delivery
evidence is valid independently of portal selection; use the updated report/hash
to reproduce the combined GNOME fixture. This is test infrastructure, not a change
to the owner's activation environment. GNOME 49/48/46 and non-KDE/non-GNOME
desktop shortcut qualification remain open; the adapter currently admits GNOME 50.

### Researched GNOME observation design: next implementation stage

A version-qualified, read-only Shell extension is needed for the trusted observer.
The [tagged Shell introspection interface](https://github.com/GNOME/gnome-shell/blob/50.5/js/misc/introspect.js)
restricts callers to portal services, omits x/y and stacking, and filters some
popup windows. It cannot replace KWin observations. GNOME's
[extension guidance](https://gjs.guide/extensions/overview/updates-and-breakage.html)
requires version-specific qualification; begin with Shell 50, tested on 50.5.
This is a researched design, not an implemented or enabled input adapter.

Use public introspected APIs from the tagged
[window](https://github.com/GNOME/mutter/blob/50.5/src/meta/window.h),
[display](https://github.com/GNOME/mutter/blob/50.5/src/core/display.c),
[actor enumeration](https://github.com/GNOME/gnome-shell/blob/50.5/src/shell-global.c)
and [workspace manager](https://github.com/GNOME/mutter/blob/50.5/src/core/meta-workspace-manager.c):

| Observation | Planned API/identity contract |
| --- | --- |
| Focus | `global.display.get_focus_window()`; null is unavailable |
| Window | `get_stable_sequence()` plus fresh extension-enable epoch and pinned Shell bus owner |
| Bounds | `get_frame_rect()` in logical coordinates; no shadow/input-border inference |
| Visible windows | `global.get_window_actors()`, `get_meta_window()`, workspace membership, mapped/paint visibility and lifecycle filtering |
| Stacking | `sort_windows_by_stacking()` for managed windows; retain override-redirect/popups as blockers |
| Workspace | active object identity plus display index; handle sticky windows and dynamic removal/reordering |
| Monitors | `get_n_monitors()`, geometry and scale; retain one-monitor input limit |

Window [PID is client-spoofable](https://github.com/GNOME/mutter/blob/50.5/src/core/window.c),
so it is metadata for accessibility lookup, never target identity or authorization.
`get_tab_list()` is an Alt-Tab/MRU selection, not a complete stacking observation.
Closing actors can persist during animation. Track unmanaging/unmanaged and actor
destruction, and invalidate tokens on extension/Shell replacement. The extension
should export only typed Status/Read and a separately qualified InspectPoint on
Shell's D-Bus connection; no arbitrary code, focus or window-management methods.
The client pins the unique Shell owner, bounds requests and rejects malformed or
missing responses. An epoch and event serial must fence focus, geometry, stacking,
workspace, monitor, modal and lifecycle changes, including change-away/back.

Before GNOME actions, correct and qualify the shared portal checks that currently
exclude same-PID covering windows: application dialogs/popups remain blockers.
Mutter focus alone does not prove keyboard ownership. Snapshot Shell action mode,
modal count, stage key focus and stage grab actor; refuse Shell modal/overview,
lock/greeter, drag and unqualified transition states. `Meta.Display.is_grabbed()`
reports window dragging, not every keyboard/popup grab. See
[Shell modal handling](https://github.com/GNOME/gnome-shell/blob/50.5/js/ui/main.js),
[stage focus/grab/pick APIs](https://github.com/GNOME/mutter/blob/50.5/clutter/clutter/clutter-stage.c)
and [extension mode checks](https://github.com/GNOME/gnome-shell/blob/50.5/js/ui/extensionSystem.js).
`session-modes: ["user"]` still needs an explicit lock-state guard because parent
mode can keep an extension active.

Shell [chrome](https://github.com/GNOME/gnome-shell/blob/50.5/js/ui/layout.js) and
[workspace animation clones](https://github.com/GNOME/gnome-shell/blob/50.5/js/ui/workspaceAnimation.js)
are outside the managed-window list. Frame geometry alone cannot establish an
uncovered click target. Qualify stage point picking and actor ancestry against
the expected window actor; block other windows, chrome, clones and unknown picks.
[Surface input regions](https://github.com/GNOME/mutter/blob/50.5/src/compositor/meta-surface-actor.c)
affect picking; do not describe it as universal pixel-occlusion detection.
Preserve portal consent, capture-before/after fencing, one-use tokens, AT-SPI
keyboard checks, independent Stop and held-input release.

The private fixture must cover Wayland/XWayland, close/reopen identity, extension
restart and owner loss; focus changes and change-away/back; move/resize/minimize/
restore/restack; workspace switches/removal/sticky windows; same-process dialogs
and popup menus plus foreign covers; overview/animation/Shell menus/notifications/
on-screen keyboard; lock guards/errors; scale/topology and capture coordinates.
Only after those observer and point-guard proofs may capability discovery admit
GNOME control. Actual application launch/focus and full login/reboot remain the
preceding startup acceptance gates. All input fixtures remain in the private
compositor; never use Shell Eval or the owner's desktop to obtain this evidence.

### Hosted installer/shortcut checkpoint and first GNOME observer

Branch `6108a640c5590d4feb13e453ce529d466a56fe2c` passes
[Linux hosted CI](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36942865107)
and [Mac 14/26 hosted CI](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36942865099).
Linux passes source/Home/root checks, Debian package and installed lifecycle,
Browser acceptance, and all three Ubuntu/Fedora package/native jobs. Each distro
passes 626 native cases (624 pass, two Mac-only skips). The actual package source
is GitHub's clean merge `ff8f8a29c9bd4c763e60cf39001568f78b254d61`, with parents
`d91c520` and `6108a64`. Its verified tree
`6aad74fa6846db8ea62b09e9d94c4801b9783950` equals the branch tree; retain the actual
merge identity for artifact/setup matching. Checked reports for
[Ubuntu 26.04](../release/qualification/ff8f8a2/ubuntu26.04-amd64.json),
[Fedora 43](../release/qualification/ff8f8a2/fedora43-x86_64.json) and
[Fedora 44](../release/qualification/ff8f8a2/fedora44-x86_64.json) include package
hashes, image/proof/source hashes, runtime/GTK versions and ordinary-user API
imports. These package/native proofs do not replace the earlier `a5d27c3` complete
installer/harness/credential checkpoint or qualify full GNOME desktops.

The first [GNOME 50 observer bridge](../services/desktop/gnome-extension/README.md)
implements read-only Status/Read/InspectPoint on Shell's session-bus connection.
The Python client pins the unique Shell owner, bounds requests, validates metadata
and fences enable epochs. Fresh snapshots include stable-sequence window IDs,
frame geometry, managed stacking, visible workspaces/monitors and Shell/stage
guards. Tracked events advance a serial even when final state returns to its
earlier value. Newly discovered actors attach handlers when their compositor
actor becomes available; actor destruction releases those handlers before
disposal. Unsupported/malformed replies fail explicitly. No observer method
captures, inputs, evaluates arbitrary code or changes windows.

The [checked observer report](../release/qualification/gnome50/fedora44-observer.json)
passes in the same owned Shell/Mutter 50.5 software compositor, using real GTK
Wayland windows. It proves distinct same-process identities, focus away/back
serial advance, frame resize, reactive/painted window versus chrome picks,
close/reopen fresh identity and disable/re-enable epoch invalidation. The proof
verifies the loaded extension files against source and rejects source changes
during the run. The fresh fixture's overview/modal/grab values and missing screen
shield provider are recorded explicitly. Reproduce with
`--exercise-gnome-observer` in the existing discovery/Qt container command.

An initial fixture tried restoring focus with an untokened GTK `present()` call;
Wayland correctly refused. The proof now changes focus using synthetic
Alt+Escape through one owned, version-pinned private Mutter session, releasing
all held keys in cleanup. This does not qualify Augmentor's real canonical
launcher or focus behavior. A second issue accessed already-disposed actor
handlers; lifecycle cleanup now passes without GJS/GLib critical errors. Initial
point inspection immediately after resize observed an unsettled painted scene;
the fixture waits for a fresh matching read-only pick before asserting success.
There is no input action retry or portal-consent bypass in the product.

The bridge is packaged as inactive source and installed/enabled only in the
disposable fixture. GNOME capability registration remains unavailable;
`inputQualified` and complete actor-composition qualification remain false.
Fresh metadata and selected point picks are not universal occlusion/history
proofs. Public stage-grab notifications cover no-grab/any-grab transitions, not
every nested grab-owner change; any current grab blocks a candidate. Plain Shell
mode/modal variables and surface input-region changes also lack universal event
coverage. Keep the researched animation/chrome/lock/input-region tests open.

The shared Linux scene/action guard now includes same-PID covering windows in
freshness comparisons and point refusal. Six toolkit-independent scene cases and
three real Portal action-code tests prove same-process appearance/move/removal,
pre-dispatch refusal, token consumption and no replay; the transport peer in these
tests is synthetic. Seven observer protocol/fencing cases pass. The native Python
source suite, using its existing compiled JavaScript and cached bundled Node,
passes 642 cases (640 pass, two Mac-only skips) before the final observer
tracking/provenance hardening; final focused and real compositor proofs pass.
The first local broad run lacked Node on PATH; rerunning with the existing private
bundled Node path passes without production changes. Current observer-source
hosted/package/complete qualification remains pending after clean publication.

Next: actual application/canonical-launcher activation and single-owner startup
in full private login sessions; XWayland and independent window placement/
workspace following; complete observer/point-guard qualification; then consented
GNOME capture/input/Stop integration. Continue the remaining older Ubuntu/Mint,
openSUSE/Arch, Browser channel, physical voice, SELinux and release gates. No
installed owner application, graphical environment, model or audio configuration
changed.

### Existing Augmentor windows in private GNOME and observer-source CI

Clean branch `43618ea100058d1dbcd0d5782c8f6d02f3c8a81f` passes
[Linux CI](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36945980802)
and [Mac 14/26 CI](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36945980796).
All Linux source/Home/root, Debian/installed lifecycle, Browser and three distro
jobs pass. Each distro runs 642 native cases (640 pass, two Mac-only skips).
The actual artifact source is merge `f7d75859f5bd88fd99bec2b4904aae5fd3423ed7`
(parents `d91c520`, `43618ea`), tree `34330856d358cfe9ea64e666313e54df29b9f299`,
verified equal to the branch tree. Preserve that merge source identity when
assembling complete bundles. The checked [Ubuntu](../release/qualification/f7d7585/ubuntu26.04-amd64.json),
[Fedora 43](../release/qualification/f7d7585/fedora43-x86_64.json) and
[Fedora 44](../release/qualification/f7d7585/fedora44-x86_64.json) reports replace
the earlier hosted package checkpoint for this source. Complete setup and full
desktop acceptance remain separate gates.

The new private proof exercises actual Augmentor preview windows, their real
singleton sockets and the unchanged canonical launcher installed by
`install-desktop-startup.py` into the disposable user's HOME. GSD delivers the
configured shortcuts to both existing processes. In both
[XWayland/xcb](../release/qualification/gnome50/fedora44-native-ui-xcb.json) and
[native Wayland](../release/qualification/gnome50/fedora44-native-ui-wayland.json),
each window hides, restores, receives compositor focus and accepts a synthetic
letter in its own composer; the two original process IDs remain independent.
The observer is read-only and verifies actual compositor focus. XWayland uses
only the private Mutter authority file. No owner bus, display, devices or GPU are
mounted; input uses the already qualified owned Shell 50.5 fixture session and
releases held keys in cleanup. Loaded observer and exercised source hashes are
verified before/after each run.

This qualifies existing-window toggle behavior, not closed-app or user-systemd
startup. Initial processes use `--preview --ui-test-control`; repeat GSD commands
use the production canonical launcher without those flags. The test-only native
image adds distro Python imports and the existing bundled Node 24.19.0 binary.
It makes no harness/model request. Its selected source root is fixture metadata,
not an owner's installed deployment or a release promotion. The dummy login
manager still excludes login/logout/reboot, SELinux and physical keys. GNOME input
capability and complete observer composition remain unqualified.

Reproduce by building `release/gnome-native-ui.Dockerfile` with
`GNOME_BASE=augmentor-rollout-gnome-qt-fixture` and
`NODE_BASE=augmentor-rollout-fedora-node-cache`, using the existing disposable
discovery command with `--exercise-native-ui xcb` or
`--exercise-native-ui wayland`. The checked reports identify the exact base/test
image and source hashes; retain the older observer-only report's original
discovery hash as historical evidence.

Primary source research explains why shortcut delivery is a separate focus gate.
[Shell 50.5 supplies an activation token](https://github.com/GNOME/gnome-shell/blob/50.5/js/ui/shellDBus.js#L283),
but [GSD 50.1's handler](https://github.com/GNOME/gnome-settings-daemon/blob/50.1/plugins/media-keys/gsd-media-keys-manager.c#L2580)
does not consume it. Its [custom-command launcher](https://github.com/GNOME/gnome-settings-daemon/blob/50.1/plugins/media-keys/gsd-media-keys-manager.c#L999)
uses plain `GAppLaunchContext` and ignores its timestamp argument. GLib's
[plain context](https://github.com/GNOME/glib/blob/2.88.0/gio/gappinfo.c#L1841)
does not generate a startup ID. Qt's [Wayland show/activation path](https://github.com/qt/qtbase/blob/v6.11.0/src/plugins/platforms/wayland/plugins/shellintegration/xdg-shell/qwaylandxdgshell.cpp#L567)
differs from activating an old, already visible surface. The tested hide/remap
path passes with actual Qt 6.11.2; do not infer universal visible-window focus or
replace the current implementation based solely on missing launch tokens.

Next: full private GNOME login/user-systemd and closed-app startup, duplicate
owner/crash/reboot checks; workspace following/placement; full observer guards;
consented capture/input/Stop; older distro and release qualification.

### Full Fedora GNOME VM infrastructure prepared

The next full-system fixture now boots the pinned
[Fedora Cloud Base Generic 44-1.7 x86_64 image](https://download.fedoraproject.org/pub/fedora/linux/releases/44/Cloud/x86_64/images/Fedora-Cloud-Base-Generic-44-1.7.x86_64.qcow2).
`scripts/prepare-gnome-vm.py` verifies its signed checksum using the pinned
[Fedora 44 fingerprint](https://fedoraproject.org/security/) and
[official keyring](https://fedoraproject.org/fedora.gpg), then verifies all image
bytes. It creates a separate 32 GiB backing overlay, dedicated SSH key and
NoCloud seed beneath ignored `outputs/`, never attaching host filesystems,
devices or owner credentials. QEMU 10.0.13 uses TCG/Nehalem, four virtual CPUs
and 6 GiB RAM; only guest SSH is forwarded on loopback. Guest NAT is enabled for
package provisioning. The [checked infrastructure report](../release/qualification/gnome50/fedora44-vm-infrastructure.json)
records the signed/hash-verified base, successful dedicated-user SSH boot,
SELinux enforcing at initial Cloud boot, duplicate-running-PID refusal and
outside-worktree-output refusal. None is GNOME application acceptance.

Reproduce with `python3 scripts/prepare-gnome-vm.py --directory
outputs/linux-rollout/fedora44-gnome-vm --boot`. SSH uses that directory's
dedicated `id_ed25519`, `known_hosts`, port 22489 and `augmentor-proof` user;
credentials and seed remain private ignored files. The guest contains
`/etc/augmentor-test-vm`; verify it before guest changes. Repository metadata
confirms `gnome-desktop` and `workstation-product-environment`. GNOME group
provisioning is in progress; GDM login, graphical user-systemd, application
startup, reboot and desktop SELinux acceptance remain open. This is a
Cloud-derived GNOME system, not a qualification of the standard Workstation
installer. Fedora documents the [backing-overlay/cloud-init method](https://fedoraproject.org/wiki/QA%3ALocal_cloud_testing_with_virt-install)
and cloud-init documents the [NoCloud seed](https://docs.cloud-init.io/en/latest/reference/datasources/nocloud.html).

The actual existing-window xcb proof also exposes missing `wmctrl`: its status
reports that workspace pin could not be applied. The existing native surface
already uses `wmctrl` for its XWayland fallback, but current native package
dependencies omit it. The focus report qualifies only its stated toggle/typing
checks. The tool is available in [Fedora 43/44](https://packages.fedoraproject.org/pkgs/wmctrl/wmctrl/),
[Ubuntu 26.04](https://packages.ubuntu.com/resolute/wmctrl) and
[Debian 13](https://packages.debian.org/trixie/wmctrl). Next test actual pin/unpin
and independent workspace following in private GNOME, then provision the native
dependency. Native Wayland workspace following remains a separate adapter gap.

### GNOME XWayland workspace following and first-use unpin

The [new private actual-window report](../release/qualification/gnome50/fedora44-native-workspaces.json)
passes both initial sticky windows, workspace switches, independent first-window
unpin onto the current workspace, second-window following, first-window repin
and return across three fixed private workspaces. It uses the actual existing
pin button, compositor-owned stable identities and public-display EWMH state;
no new compositor writer or managed-display connection is added. Existing
canonical shortcut/focus/composer checks also pass. Native Wayland following,
real login, transient dialogs, monitor policy and full capture/input remain open.

The fixture first reproduced an additional bug after installing `wmctrl`:
before any workspace switch, `wmctrl -d` cannot read `_NET_CURRENT_DESKTOP`.
The original unpin code fails before removing sticky state, leaving the window
on all workspaces while its preference says unpinned. Tagged Mutter source
explains the on-demand XWayland [initialization path](https://github.com/GNOME/mutter/blob/50.5/src/core/display.c#L687)
and [active-workspace hint callback](https://github.com/GNOME/mutter/blob/50.5/src/x11/meta-x11-display.c#L1386).
The corrected GNOME path sends `remove,sticky` to Augmentor's own XID;
Mutter's [request handler](https://github.com/GNOME/mutter/blob/50.5/src/x11/window-x11.c#L3422)
and [unstick transition](https://github.com/GNOME/mutter/blob/50.5/src/core/window.c#L5201)
place it on the active workspace without guessing an index. The real proof
passes first unpin while the hint is absent, then unpin on workspace 1; after
the first switch the root desktop query succeeds. GNOME routing also avoids
probing KWin for this operation. KDE, generic X11 and the early macOS branch
retain their existing behavior.

Native Debian/Ubuntu and Fedora packages now declare `wmctrl`; the ordinary-user
package proof checks its actual binary version. Fresh packages from this changed
source still need hosted confirmation. The explicit UI-test interface adds
read-only pin state and an expected-state pin-button operation; normal launches
reject it. It requires a visible pin button and no dialogs. Five focused UI-test
cases pass, including stale/hidden refusal. The full native source suite passes
643 cases (641 pass, two Mac-only skips) using the existing compiled JavaScript
and bundled Node fixture. New-source Mac and package/complete qualification
remain pending after publication.

Reproduce with the test-only `release/gnome-workspaces.Dockerfile` over the native
UI image and `--exercise-native-ui xcb --exercise-workspace-follow` in the private
discovery command. The report records exact image/source hashes, the initially
missing root hint and actual `wmctrl` package. The full Fedora VM's GNOME group
installation has separately completed; graphical login/startup acceptance is
still next. No installed owner release, UI layout, model or audio settings changed.

### Full Fedora GNOME login and packaged startup checkpoint

The owned Cloud-derived Fedora 44 VM has completed distro `gnome-desktop`
installation and actual GDM autologin into an active seat0 Wayland user session.
The [checked startup report](../release/qualification/gnome50/fedora44-vm-startup.json)
records GNOME Shell 50.5, SELinux enforcing, package verification and the actual
user service owning Augmentor's non-preview process. Its canonical selection is
`/usr/lib/augmentor`; the initial Connect DSH dialog renders and receives compositor
focus above the main window in the same process. Connection remains intentionally
unconfigured, so this is startup/onboarding evidence without a harness/model turn.
After dismissing the setup dialog in the owned VM, the main window remains focused
and maintenance reports idle. No owner desktop or installed release is changed.

This guest contains the earlier clean artifact source `f7d7585`, RPM SHA-256
`831c1715e94305fa3d1ab4a0ad202fa92371c59cbea7517155f8b4ee51d51a57`, plus explicit
fixture `wmctrl`. It does not contain the later `8413c2c` workspace correction or
its declared dependency. Do not relabel this evidence as latest-source release
qualification or patch its installed package to imitate a newer artifact.

`release/provision-gnome-vm.py` runs only as the dedicated ordinary user in the
marked QEMU guest, verifies its clean installed package and SELinux, copies the
package's exact read-only observer into that user's extension directory, invokes
the package's real startup installer, and configures fixture-only GDM autologin.
The privileged guest change checks the marker again and preserves the original
GDM configuration. `release/inspect-gnome-vm.py` performs read-only inspection of
the actual session, service, singleton status, selection and compositor. Copy
these helpers through the fixture's dedicated SSH channel and run them inside
the guest. Their hashes and limits are recorded in the checked report. GDM's
[documented automatic-login settings](https://help.gnome.org/system-admin-guide/login-automatic.html)
are fixture provisioning, not manual authentication acceptance.

Unlike the headless compositor fixture, the full session has a real ScreenShield.
GNOME suspends this user-only extension while locked: the observer object becomes
unavailable, so observation fails closed. After unlock it returns with a new epoch;
old window identities must be discarded. The report does not claim a positive
locked scene or qualified input. Duplicate startup, crash/reboot, consented input,
complete actor guards and a standard Workstation installation remain open.

Clean `8413c2c` passes Mac 14/26, Linux Debian/root/Home/source, installed lifecycle
and Browser hosted checks. All three distro jobs stop after successful installation
because the newly added `wmctrl -V` check opens X before processing its version
option. The proof now starts and cleans up a private Xvfb display solely for that
ordinary-user read-only check. Xvfb is a test dependency, not a product dependency.
Actual corrected binary checks return `1.07` on Fedora 43, Fedora 44 and Ubuntu
26.04. Fresh complete package/native hosted confirmation follows this correction;
do not treat the failed matrix as a passed package qualification.
