<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Augmentor Agent Desktop release plan — updated 2026-09-14

Implementation is now authorized and underway. The planning-time observations
below remain historical context; use the
[release acceptance checklist](RELEASE-ACCEPTANCE-CHECKLIST.md) and
[candidate evidence](CROSS-PLATFORM-RELEASE-STATUS.md) for current progress.

## Approved scope and release priorities

The user revised the plan on 2026-09-14:

- The native product is **Augmentor Agent Desktop**; the Chromium interface is
  **Augmentor Agent Browser**. Both retain the shared services and harness adapters.
- Support **DSH and Pi only**. OpenCode is removed from the planned supported
  engines. Its implementation, dependencies, selectors, packaging and active
  documentation will be retired during implementation, preserving existing user
  data and historical records. No OpenCode port or release qualification is planned.
- The first release phase covers **Linux and macOS**. Windows is a later phase
  and is not a dependency of the Linux/macOS release. Broader Linux coverage can
  expand incrementally; it must not postpone macOS until every distro is covered.
- **DSH is the full-featured compatibility target**, including the DSH plugins
  required for the agreed product features. This is a release objective, not a
  statement that all current preview limitations have already been resolved.
- **Pi is a supported, usable subset**. Features requiring DSH plugins are not
  promised on Pi for this release. **Pi extensions for features currently requiring
  DSH plugins** are a separate future workstream; their design and implementation
  are deferred.
- The user has made a **network-accessible Mac Mini** available for macOS
  installation and testing. Verify its connection, processor architecture, macOS
  version and interactive desktop access when implementation starts. Access has
  not been tested as part of this planning update.

This update changes planning only. No application rename, engine removal, remote
installation or implementation is performed by updating this document. Existing
source paths, package identities and stored protocols remain compatibility concerns
for the implementation phase.

## Decision and current evidence

Maintain one product with browser and desktop interfaces, backed by shared services
and independently selected Pi or DSH harnesses. Use **Augmentor Agent Browser** and
**Augmentor Agent Desktop** in public-facing naming. Label platform support using
actual release evidence; macOS is a first-phase target, not yet verified support.

The following version and implementation observations were recorded on 2026-09-10.
Recheck them against the release candidate before treating them as current evidence.

The unified repository is `ManoloRemiddi/augmentor-agent`, currently private.
The separate public DSH-only extension is 0.1.32. Unified 0.2.8 is a local
compatibility preview, including the previously uninstalled desktop specialist.
The stable website download must not silently become a private GitHub link.

| Target | Existing implementation/evidence | Work before advertising support |
| --- | --- | --- |
| Linux x86-64, Debian 13, KDE Wayland | Runtime and desktop `.deb` builders; prior clean Debian container and full KDE VM evidence; current machine uses KDE Wayland | Run the new artifact through install, upgrade, reboot, browser registration, model task and desktop consent/Stop acceptance |
| Other Debian-family distros | Much of runtime/UI is reusable | Check Python/PySide6/Qt dependency availability and minimum versions; qualify each supported distro/desktop combination |
| Fedora/openSUSE/Arch | Shared JS/Python logic is reusable; no released installer | Add RPM or portable runtime packaging, dependency checks, desktop integration and clean-machine testing |
| Linux GNOME Wayland | No verified input backend | Adapt capture/input through available portals; remove KDE-specific window/control assumptions only after equivalent targeting and Stop checks |
| Linux X11/XFCE | Some UI/clipboard tests run on X11; full desktop control is not implemented there | Separate X11 observation/input/target verification backend and permission behavior |
| macOS, first release phase | Platform-neutral contracts and much of Qt UI can be reused; user-provided Mac Mini available over the network, access/architecture not yet verified | macOS backend, native dependencies, process/lifecycle/IPC adapters, browser registration, signing/notarization and installed tests on the Mac Mini; qualify other Mac architectures separately |
| Windows, later release phase | Platform-neutral contracts can be reused; no Windows executor or installer | Defer backend, process/IPC adaptation, native-host registration, installer and qualification until after the Linux/macOS phase |

No container, cross-compile or passing mocked test establishes macOS/Windows GUI
support. Linux distribution and desktop/session are separate dimensions: a package
installing on Fedora does not prove that its GNOME Wayland input path works.

## DSH and Model Picker

The 0.2.8 development adapter targets DSH 0.1.5-rc.1, with authenticated Typert
requests and streams. It reuses the browser compatibility transport from 0.1.32,
and updates native/setup/branching calls and preset `text` → `prefix` migration.
Model Picker Augmented 1.1.2 owns DSH curation; DSH surfaces read/write that settings
namespace. Pi keeps its own catalog and explicit selections.
Installing Model Picker does not automatically install a model or credentials.

There is a DSH fork limitation: the current API includes records between a selected
turn/end and the next turn/start. When an inbox-splice record containing a queued input occupies that interval,
Edit cannot remove it. Augmentor refuses this case before creating a child; it must
not claim successful editing while retaining the old input. Resolve this through an
upstream exact-prefix fork API or a separately validated host adapter before claiming
full DSH Edit parity. First-input editing and forks without that ambiguous suffix
remain separate cases. Pi editing remains a separate compatibility contract.

DSH approval/questions currently stay in DSH's authenticated web UI. The native and
browser clients must not silently approve, replay, or strand a waterfall. Restoring
Augmentor-native DSH interaction dialogs requires the new scoped event/reply contract
and explicit conformance tests. CORE compatibility remains an architecture boundary;
this preview does not claim a tested Resonant CORE integration.

## DSH completeness and Pi subset

Before implementation, turn the feature matrix into a release checklist with one
row per feature and columns for DSH, Pi, required plugin/version, Linux evidence
and macOS evidence. Inventory the actual DSH plugin dependencies, their startup
requirements and platform support. Define the exact features and contracts for
future Pi extensions when that workstream is scoped.

For DSH, full compatibility means every agreed release feature works with the
tested harness/plugin combination on each advertised platform. Resolve the
recorded branch/edit and approval/question limitations, or explicitly revise the
release scope before claiming full compatibility. Verify the current source first:
the dated observations above are not a substitute for fresh acceptance evidence.

For Pi, qualify core model connection/selection, chat and streaming, Stop, history,
supported file tools, shared prompts and every additional feature advertised for
Pi. Preserve working Pi functionality; do not disable it merely because another
feature depends on DSH. DSH-only functions must be clearly unavailable under Pi,
with a useful explanation. Do not silently change the engine of a conversation.
Pi release acceptance uses its declared subset, not DSH feature parity. The future
Pi extensions must not block this release.

## Platform seams to implement

Keep the coordinator, prompts, model selection, history, browser executor and
computer-use result contracts shared. Put the following behind platform adapters:

- Capture, accessibility tree, input, active-window identity and display coordinates.
- User consent, cancellation, independent Stop, screen lock and permission revocation.
- Runtime directories, private storage, local IPC and user identity checks.
- Process supervision, signals, release leases and installation/rollback hooks.
- Tray, shortcuts, clipboard and browser native-host discovery.
- OS-aware agent instructions, shell execution and command approval rules.

Retain PySide6/Qt and the shared runtime architecture. Isolate Linux imports and
dependencies so the core app can start on macOS. Keep interfaces suitable for a
future Windows backend, but do not implement Windows-specific components now.

The current code contains Linux-only `/usr/bin/python3`, `/run/user`, `os.getuid`,
`fcntl`, Unix sockets, systemd/KDE integration and a Debian-specific Node archive.
Renaming the app or wrapping those files in another installer cannot port them.

For Wayland, build against the actual
[RemoteDesktop and ScreenCast portal contracts](https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.RemoteDesktop.html)
and query supported capabilities at runtime. For macOS, implement capture with
[ScreenCaptureKit](https://developer.apple.com/documentation/screencapturekit/capturing-screen-content-in-macos)
and a native accessibility/input adapter, with user-granted OS permissions.
For the later Windows phase, evaluate UI Automation and a native input/capture adapter;
[SendInput is subject to UIPI](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendinput),
so unsupported elevated/secure surfaces must be reported, not bypassed.

## Packaging and publication sequence

1. Finalize the DSH/Pi feature checklist and plugin inventory. Plan the visible
   rename and OpenCode retirement, including preserved user data, stable browser
   host identity and compatibility for existing sessions, tools and protocols.
2. Establish the Linux baseline and inspect the Mac Mini environment. Prove a
   packaged Qt launch, bundled runtime startup, private IPC, one model exchange
   and Stop on macOS early. Test capture, permissions and target verification
   before committing to the complete macOS backend. These are implementation
   milestones; no installation is part of the present documentation update.
3. Extract platform adapters and implement macOS while preserving Linux behavior.
   Complete the agreed DSH feature set and qualify the Pi subset on both systems.
   Keep source/artifact identity, hashes, backups and rollback artifacts together.
4. Qualify the first Linux distribution/desktop targets and the Mac Mini's macOS
   target. Prefer DEB/RPM packages where qualified; evaluate AppImage for broader
   Linux reach after checking host ABI and browser registration. Treat Flatpak
   separately because its [sandbox/portal model](https://docs.flatpak.org/en/latest/basic-concepts.html)
   needs a deliberate companion and desktop-control design. Broader Linux support
   proceeds incrementally alongside macOS readiness.
5. Package the macOS application with its runtime dependencies, Developer ID
   signing and [Apple notarization](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution).
   Test the signed installed artifact on the Mac Mini, including permission
   attribution to helpers and behavior after upgrade. Account/certificate
   enrollment is owner work when required.
6. Freeze a public preview candidate from a clean commit. Decide whether to make
   the unified source repository public or publish artifacts in a dedicated public
   distribution repository. A private repo's GitHub Actions artifacts are not
   durable public downloads. Complete the existing third-party notices/source
   availability review for the actual packaged binaries.
7. Publish immutable GitHub release assets for the qualified Linux/macOS targets:
   extension ZIP, runtime-only companion, desktop packages, checksums and
   installation/upgrade/rollback notes. Browser-only
   users need the companion but should not have to install the desktop Qt UI.
8. Add two website download cards: **Augmentor Agent Browser + companion** and
   **Augmentor Agent Desktop**. Both show version, release channel, supported OS/architecture,
   system requirements and matching companion version. Offer manual OS selection;
   unsupported platforms show an honest development status, not a working download.
9. Add a browser-store listing after validating its final extension ID and native
   host allowlist. Direct unpacked ZIP distribution can precede a store listing.
   Keep release discovery, signed update metadata, interrupted-update recovery and
   rollback consistent across the companion and extension.

After the Linux/macOS release phase, scope and implement Windows support with its
own installed acceptance gates. Develop the additional Pi extensions in a separate
future phase; its timing relative to Windows is not yet specified.

## Mac Mini acceptance environment

Use the available network connection to stage builds, install candidates, collect
logs and run tests during implementation. Record hardware architecture, OS version,
dependency versions and the exact installed artifact. Do not assume the machine
is Apple Silicon or that it qualifies Intel Macs as well.

Remote shell access alone is not evidence of an interactive desktop session.
Verify access to the logged-in GUI and arrange direct user interaction only where
macOS permission dialogs require it. Exercise screen capture/accessibility consent,
denial and revocation using the packaged application identity. Preserve existing
Mac Mini applications and user state; use isolated test data and retain rollback.
The Mac Mini can establish real-machine acceptance for its target; clean-user
installation and additional supported OS/architecture combinations need their own
recorded evidence.

## Acceptance matrix

For each advertised Linux/macOS target and supported harness subset, test as a fresh ordinary user: install, first model
connection, browser registration, new chat and streaming, all browser tools, native
file work, consented desktop capture/input and visible Stop, restart without replay,
old-data upgrade, rollback, uninstall with retained user data and reboot activation.
Test desktop capture/input with permission denied/revoked, screen lock, display
changes, fractional scaling, multiple monitors, non-US keyboard/Unicode input and
a changed active target. Browser packaging must distinguish conventional packages
from sandboxed Snap/Flatpak browsers. Qualify x86-64 and ARM64 artifacts separately.

DSH release acceptance includes every agreed required plugin and full-feature
workflow. Pi acceptance includes its declared subset plus clear handling of
DSH-only functionality. Unsupported multi-monitor, Unicode or desktop-environment
cases must be explicit and safely refused until qualified.

Release order: **Linux and macOS first; Windows afterward; additional Pi extensions in a
separately scoped future phase.** Publish each target only when its installed
artifact and advertised capabilities pass. Pi feature parity and exhaustive Linux
distro coverage are not prerequisites for the first release phase.
