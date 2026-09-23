<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Productization execution ledger

This is a dated plan/ledger, not the current source map. Read the
[agent handoff](AGENT-HANDOFF.md) and [current architecture](ARCHITECTURE.md)
for the present implementation, Git ref and qualification.

The full scope is [the release plan](PRODUCTIZATION-PLAN.md). This ledger records
completed work and remaining gates; a checked implementation item does not imply
the whole release is certified.

## Current preview checkpoint

The 0.2.3 candidate includes Linux lifecycle handling, shared Hindsight memory,
DSH Branch/Edit and guided connection, browser Pi setup and packaged delivery,
guarded KDE Wayland desktop input, and private support exports. The supported
scope is in FEATURE-MATRIX.md; data and release boundaries are in
DATA-AND-SUPPORT.md and RELEASE-REVIEW.md.

CI run `34050997830` passes the Debian build, installed package/lifecycle and
packaged browser jobs. Its browser regression waits for the visible save form
to finish before selecting a prompt, then verifies a real concurrent-edit
conflict preserves the draft. Subsequent final artifact identities and acceptance
results are attached to private [PR 3](https://github.com/ManoloRemiddi/augmentor-agent-history/pull/3).

The final code checkpoint at `7a36c74` also passes all three jobs in run
`34051829514`, including the new final artifact review. Downloaded packages and
ZIP record clean source `6c3ad44b0c36f8838d7c3bef52eb3378ba593e51` (PR merge
commit). The runtime package SHA-256 is
`4730d10b0fd60ddd2914dd2d0c4adf6414d1a9da79c46f27c8862e009774c9ba`.
The full VM upgraded from 0.2.1 to those packages and passed first-run/file work,
six external clipboard cases, hardware launch/hide/show, reboot persistence and
owned-shortcut removal. Subsequent documentation corrections do not change that
tested runtime. The beta kit uses these exact packages and matching extension.

Actual Pi and DSH SDKs have each passed image delivery, an exact file saved
through native Wayland Kate, and cancellation after text visibly appeared.
The fixture independently reads the focused editor text before Stop and then
the saved partial file, verifies sharing is closed, and checks no request replay.
DSH's actual model request includes both the screenshot and its image-handle
annotation; the proof accounts for that SDK format. Candidate input also passes
100%, 125% and 150% scaling. A two-GPU VM exposes two active monitors and is
refused before sharing; the original VM configuration is restored afterwards.
The final installed desktop/scaling evidence is tracked
with the artifact set, separately from source-staged checks.

Guided DSH setup and its browser-role execution boundary pass again at 0.2.3.
The current native suite passes 81 checks and Node passes 48. Those counts
supplement the external clipboard, browser DOM, saved-file and real Hindsight
evidence; they do not replace it.

The remaining external release gates are the unassigned 3–5 beta testers and
their update cycle, advertised live-provider/hardware qualification, and the
owner's public distribution decisions (store account/listing, durable downloads,
source availability and authenticated updates). No outreach or public release
has been performed. PRIVATE-BETA.md contains the assignments and invitation draft.

## Licensing first

- [x] Historical September 6 decision: MIT for Augmentor and replaceable PySide6/Qt under LGPL. Augmentor licensing is superseded by the [September 23 decision](LICENSING.md).
- [x] Migrate native imports/signals and developer tools from PyQt6 to PySide6.
- [x] Native About/Licenses exposes product/library notices and license texts.
- [x] Collect missing npm license texts from recorded sources, validate exact
  package versions/metadata and notice hashes, and reject unreviewed licenses.
- [x] Stage locked production dependencies with the SDK's unused optional terminal
  clipboard dependency excluded. Actual UI clipboard support is retained.
- [x] Inventory shipped native binaries, retain Node/esbuild/Go notices, exclude
  unused samples/foreign platform helpers, and rebuild the required Photon WASM
  module with locked Rust dependencies and complete collected notices.
- [ ] Finish the public-release artifact/source-availability review alongside
  final packaging and distribution. Current packages remain development previews.

Evidence on 2026-09-06: native suite passed 56 tests with PySide6 Essentials/Shiboken
6.8.2.1. Four additional license inventory rejection/preservation tests pass.
The isolated X11 desktop proof used actual xdotool press/release and an external
xclip reader: all six combinations of message position and prior selection
preserved exact clipboard bytes, scroll position and tick expiry. This establishes
X11 interaction behavior, not native Wayland control or clean-machine installation.
Initial `npm ci --omit=dev` staging collected notices for 254 package instances;
the Linux distribution now retains 229 after foreign-platform exclusions.
The native suite now passes 60 tests, including licensing checks. The rebuilt
Photon module also passes hash/inventory and pixel roundtrip/resize tests.
Original installed application preserved.

## Release foundation

- [x] Create the private unified repository `ManoloRemiddi/augmentor-agent`.
- [x] Push licensing/native-migration checkpoints to the private repository.
- [x] Make root CI pass all checks. Clean Debian Node/native suites pass after
  declaring YAML. The X11 failure was reproduced: forcing QPainter compositing
  made KWin exit on its unsupported X11 backend. With compositing disabled in
  the isolated test, all six real pointer/clipboard cases pass in clean Debian.
  Remote CI confirmed the change, first-run flow and package installation job in
  run `34033433220` at `feca1ff`.
- [x] Build runtime/companion and optional native UI Debian preview packages.
- [x] In a fresh Debian container under a separate user, prove packaged Node
  without system Node/Qt, real Pi file execution, shared prompts via native
  messaging, restart without replay, Stop, and SDK image read/resize. Install and
  render the desktop, then remove owned package files while preserving user data.
- [x] Add guided Pi setup for OpenAI-compatible endpoints: literal credentials,
  tool-free check, explicit save/selection and approval mode, stale-check rejection
  and cancellation. [First-run guide](FIRST-RUN.md).
- [x] Align the packaged desktop and shortcut identity; create trusted user
  launcher entries when a shortcut is saved and roll back failed registration.
  Installed X11 proof launches, hides and restores the same window with real
  Ctrl+Alt+J events, including after restarting KDE's shortcut service.
- [x] Finish guided DSH connection onboarding for the pinned fresh-profile path.
- [ ] Certify advertised live-provider models and customized DSH migrations.
- [x] Validate preview installation, fixture role tasks, upgrade, recovery and removal.

The actual Qt first-run proof also exposed a PySide signal conflict in the
controller's old `connect` method; renamed it and verified real startup, connection
setup, a Pi file task and reopening without replay. On 2026-09-06 the package proof
also passed this flow against `/usr/lib/augmentor`, as a separate ordinary user
with no checkout mounted. Node tests now pass 41 cases; Debian native tests pass
60 cases. GitHub run `34033192621` passed the packaging checkpoint; run
`34033433220` also passed the added first-run flow against installed packages.
The subsequent shortcut change passes the complete local installed-package proof
and its four registration/rollback tests; the native suite contains 61 tests.
An additional main-branch run exposed asynchronous Xvfb cleanup between consecutive
UI proofs. The test launcher now uses authenticated `-displayfd` allocation and
waits for its own server to exit. Nested display allocation and the consecutive
clipboard/first-run proofs pass in the Debian test image.

The complete foundation CI subsequently passed at `295dbc0` in GitHub run
`34034692905`. Its downloaded 0.2.0 packages were verified against the artifact
hash and size manifest and retained as the local upgrade baseline.

### Linux lifecycle continuation (0.2.1)

- [x] Generate component versions from `release/product.json`; include source
  commit and dirty-checkout status in package manifests.
- [x] Add lifetime leases and root-owned package maintenance boundaries. Refuse
  active replacement, keep desktop/runtime versions aligned, and block launches
  until an interrupted package configuration is completed.
- [x] Prepare the ordinary user's idle components, back up private data, and
  refuse active tasks without cancelling or replaying them.
- [x] Migrate recognized legacy launchers/shortcuts and browser registrations,
  with per-file backups and the legacy application preserved. Reject foreign
  or symlinked integration files before replacement.
- [x] Remove owned per-user integrations; actual KDE key checks confirm that the
  shortcut stays removed after restarting the shortcut service. Desktop-only
  removal preserves the companion, including an active Pi task.
- [x] Installed baseline upgrade, interrupted configuration, rollback, migration,
  removal and reinstall compare exact persisted history/prompts and verify no
  model request was replayed. Local Debian container proof passes.
- [x] Full Debian KDE Wayland desktop VM and reboot acceptance with clean CI-built packages.

The lifecycle Node suite contains 42 passing cases; the native suite now contains
64. Meaningful new checks exercise active shutdown refusal, real lifetime locks,
foreign/symlinked integration conflicts and configured backup paths. These tests
supplement the installed lifecycle and actual pointer/clipboard proofs.
The isolated VM uses Debian image build `20260831-2587`, verified against Debian's
published SHA-512, and boots a real Plasma Wayland login through QEMU TCG. Desktop
application and reboot checks have passed with the exact packaged source recorded below. See [lifecycle procedures and evidence scope](LIFECYCLE.md).

## Remaining product scope

- [x] Bounded KDE Wayland capture/input preview with a verified Stop path.
- [x] DSH Branch/Edit conformance and common behavior across both surfaces.
  Closed-turn/first-input semantics and unknown-outcome refusals pass the real
  DSH API, Qt pointer and Chromium extension checks; see FEATURE-MATRIX.md.
- [x] Hindsight integration, authorized scopes, data controls and failure tests.
- [x] Browser companion onboarding, private ZIP distribution and version compatibility.
- [x] Permission/credential/logging hardening and diagnostic export for the preview.
- [ ] Public browser store distribution and authenticated public update channel.
- [ ] Independent desktop VM certification and 3–5 external beta testers,
  including an update cycle, before public release.

The full desktop VM found a cold-start failure that container tests did not:
the shell launcher exited when Pi needed more than 15 seconds after login.
The window now opens first and its existing worker connects to Pi; native and
browser startup share the same startup lock and a 60-second allowance. With
those changes applied to the installed VM, real hardware-key launch/hide/show,
reboot activation without registration, and shortcut removal all passed. The
complete six-case external clipboard and first-run/file checks also passed.
The initial pass used patched installed code. The complete acceptance was then
repeated successfully after reinstalling the verified clean CI-built packages
from run `34041428460`, source commit
`c0ce31f772a13bc3ddf7d00644f69454d5f0df8b` (GitHub PR merge commit).
Package hashes and sizes match the downloaded artifact manifest. The guest was
Debian 13.6, Plasma/KWin 6.3.6, portal KDE 6.3.5 and Chromium 152.0.7977.82.
This proves deterministic fixture behavior in a real Wayland desktop; independent
human beta and live provider certification are still separate gates. The original lifecycle CI passed in run `34039214197`; its
verified artifact source is GitHub's PR merge commit `23f5c5386689518ab81ded99331d9fa2b0384958`.

### Shared memory and browser setup continuation

The optional Hindsight boundary and both configuration/data dialogs are implemented.
Actual Hindsight 0.9.2 retain/recall, asynchronous completion, user/project isolation,
source viewing, fact export, disable and remote/local source deletion pass. Real Pi
and DSH tool execution delivers the same retained fact to the next model request
on both surfaces. DSH preset mounting still needs guided installation. See
[the memory evidence and limits](MEMORY.md).

A fresh Chromium profile now completes checked Pi setup using the shared runtime,
then a real browser page task, Copy/Edit/Branch and shared prompt operations. The
browser memory form's pointer actions and downloaded JSON contents pass against
Hindsight. Diagnostics retain message metadata instead of typed text; DSH file
tracing is disabled by default. Source-level checks pass 79 native and 45 Node
cases at this checkpoint. These changes still require their new packaged CI run,
DSH setup and remaining computer-use/distribution/security/beta gates.

### Browser delivery and diagnostics continuation (0.2.2 candidate)

- Extension/companion handshake rejects different product versions before
  shared-data writes or harness startup. Both components use the release manifest.
- A deterministic ZIP includes a stable extension identity, exact file hashes,
  Augmentor's license and the separately vendored Marked 12.0.2 notice.
- Actual Chromium 152.0.7977.75 first-run setup, page actions, copy/scroll feedback,
  Branch/Edit context, restart without replay and prompt conflicts pass with the
  handshake. Both surfaces offer reviewable support metadata; the browser's real
  downloaded report is checked independently for exact contents and omitted data.
- Trace files are off by default. Opted-in files contain allowlisted metadata,
  stop at 1 MiB, and rotate five recent files with seven-day expiry on the next
  trace start. Raw legacy traces are not included in support exports.
- Guided model setup can explicitly test an image payload. This establishes API
  acceptance, not visual reasoning quality or provider certification.
- Node checks pass 46 cases; native checks pass 79. A new CI job exercises the
  ZIP and installed companion as a separate user; its first result is pending.

Desktop input is still under investigation. A candidate executor has saved exact
text in native Wayland Kate and stopped an active write through its independent
button. Expanded repetition also reproduced a compositor crash inside Qt/Breeze
window-decoration painting. A single successful run is insufficient to close that
release gate. Candidate desktop input has not been deployed to the user's app.

### DSH onboarding and candidate desktop continuation (0.2.3)

The 0.2.2 distribution checkpoint passes all root CI jobs in run `34048917170`:
Debian build, ordinary-user installed packages/lifecycle, and actual Chromium
against the extension ZIP and installed companion. Downloaded artifacts record
clean source `c95167ce2c4f16e18124fbe33530d2f81f798a46` (PR merge commit). The
browser restart assertion now recognizes a terminated zombie under a container
PID 1, while still requiring a new runtime identity and no model-request replay.

Guided DSH setup now exists in both UIs. A fresh real DSH 0.1.1-rc.2 profile passes
Qt installation/check/save, exact original-composition preservation, owned refresh
without duplicate entries, custom-preset replacement refusal, and saved chats.
Its Chromium test passes checked connection, browser DOM changes, Branch/Edit
with tool history, and an unchanged source conversation. Direct native requests
for Linux chats, provider settings, legacy plugin updates and raw trace probes
are refused. An actual browser-role model tool call to bash creates no file.
The exact proof scripts and fixture model scope are in DSH-SETUP.md.

The candidate executor passes native Wayland Kate save/Stop checks at 100% scale.
The earlier repeat crash has an independent reproducer: the AVX2 masked load from
Qt/Breeze's core dump passes on the host and SIGSEGVs in QEMU 10.0.11 TCG, even in
a small C program with no Qt/portal/Augmentor. `release/vm-avx-mask-proof.c` records
it. The VM now uses the consistent Nehalem/SSE4.2 CPU model to avoid that emulator
fault. A mixed `max,avx2=off` CPU was rejected after it caused SDDM illegal
instructions; it is not the acceptance configuration. Fractional scaling, both
SDK bindings, repeated input and final installed-package desktop acceptance are
still being completed. No candidate desktop change has been deployed to the
user's existing application.

The support-dialog test uses an actual Qt file chooser and pointer click, then
reads the exact saved JSON and 0600 permissions. A simulated full disk preserves
an existing report and leaves no temporary report behind. The release preparation
now includes shared harness configuration in backups and refuses runtime
maintenance while the configured DSH integration is running.

The independent assignments and update-cycle instructions are ready in
[PRIVATE-BETA.md](PRIVATE-BETA.md). [DATA-AND-SUPPORT.md](DATA-AND-SUPPORT.md)
records provider/clipboard/screenshot/history flows and support-report contents.
No external tester result, public-store review, independent security audit or
provider-quality certification is claimed by these automated checks.
