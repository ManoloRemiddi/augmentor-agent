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
3. **Shortcuts and startup** — add a GlobalShortcuts portal adapter with version
   probing, retained choices, conflicts, two instance IDs, session reconnection
   and actual activation delivery. Preserve KDE KGlobalAccel and macOS adapters.
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
