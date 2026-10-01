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
