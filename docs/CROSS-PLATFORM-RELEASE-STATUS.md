<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Cross-platform implementation status

Updated 2026-09-20. **The complete Debian preview is separately qualified; current macOS parity remains unfinished.**
See [the September 20 distribution audit](DISTRIBUTION-AUDIT-2026-09-20.md) for the current Linux release and next macOS gates. The evidence below records the earlier cross-platform candidates.
The approved scope remains [the release plan](CROSS-PLATFORM-RELEASE-PLAN.md):
DSH full compatibility, Pi's declared subset, Linux and macOS first. Windows and
additional Pi extensions remain deferred. Planning-only statements in the original
plan describe its drafting stage; implementation is now authorized and underway.

## Fresh evidence

- Linux: TypeScript build and all 80 JavaScript tests passed after platform
  capability reporting changes. Log: `outputs/cross-platform/linux-node-tests.log`.
  These checks do not establish installed desktop or browser acceptance.
- Mac Mini: SSH connectivity and ARM64 Darwin verified. The isolated development
  workspace is `~/.local/share/augmentor-development`; existing user DSH data is
  separate from these fixtures.
- Mac native suite: 153 tests ran with 152 passing and the Linux-only KWin test
  skipped. The run used the preview bundle's Node on PATH and the isolated Python
  environment. Log: `outputs/cross-platform/mac-native-tests.log`. These are
  offscreen UI and service tests, not successful macOS capture/input acceptance.
- DSH: installing only CLI 0.1.5-rc.1 selected rc.2 internal packages. The
  `release/dsh` manifest and lock now pin all 231 DSH packages, including the CLI,
  to rc.1. `npm ci --ignore-scripts` succeeded on the Mac Mini.
- Mac DSH setup proof passed using the actual DSH runtime, offscreen Qt widgets,
  and a deterministic HTTP model fixture. It exercised install, owned integration
  refresh, customized-preset refusal, checked save/reconnection, saved chats and
  the browser preset's OS-tool guard. Logs and JSON:
  `outputs/cross-platform/mac-dsh-setup.log` and
  `outputs/cross-platform/mac-dsh-setup-proof.json`.
  The legacy JSON field `linuxSavedChats` refers to the desktop preset identifier;
  this execution occurred on macOS. It is not live-model or GUI-control evidence.
- macOS runtime metadata now reports ScreenCaptureKit and Unicode, and requires
  the native helper before advertising input availability. Availability does not
  grant OS permissions. Windows remains unavailable. Two regression tests cover
  helper absence, disabled tools, platform selection and retained Linux limits.

## Installed macOS upgrade evidence

The development installer in `scripts/install-macos.py` now stages and verifies
bundles, refuses an occupied installation lease, retains the previous app, and
restores it if promotion fails. Four filesystem/lock regression tests passed on
Linux and the Mac Mini. These include rollback, active-lease refusal and symlink
lock refusal; they are not an interrupted-power-loss test.

Follow-up: replacement now synchronizes a transaction journal with old/new directory
identities before renaming. Under its exclusive lease, the next installer invocation
restores the old app if promotion was interrupted and refuses recovery over an
unrelated replacement. A fifth test forces a real subprocess to exit immediately
after moving the old directory, then verifies recovery. All five tests passed on
Linux and the Mac Mini. Power-loss and installed-bundle crash acceptance remain
separate gates.

Further recovery checks now cover completed promotion with an uncleared journal
and a concurrent replacement during failed promotion. Rollback refuses to move
the old bundle over that replacement and preserves the backup and journal for
review. All seven installer tests passed on Linux and macOS. The promotion-failure
test now injects failure after the backup rename, rather than failing validation
of a missing candidate before mutation.

Real upgrade verification exposed Python bytecode files added inside the prior
signed preview. Launchers now use `-I -B`, and Python/JS component environments
disable bytecode writes. The rebuilt development artifact has SHA-256
`0b8a74baf4728af7a72f93f0b13c603aa6a10683f192b92700495d0180bf18ab`.
It was installed over `~/Applications/Augmentor Agent Desktop Preview.app` using
the new installer; the old modified bundle was preserved, not executed or deleted.
The installed launcher screenshot and Pi first-run model/file/reopen fixture
passed, followed by successful `codesign --verify --deep --strict` after use.
This establishes ad-hoc seal preservation, not Developer ID or notarization.
The rendered window shows the full product name without clipping.

Local evidence: `outputs/cross-platform/mac-install-3.json`,
`mac-installed-first-run-3.json` and `packaged-window-3.png` in the same directory.
See [macOS installation instructions](MACOS-INSTALLATION.md).

## Remaining release gates

### Exact DSH Edit compatibility

The source product adapter now offers authenticated `exactFork` using pinned rc.1
host services: immutable observations, preset composition and seeded agent creation.
It checks role ownership, ordinary-session origin, completed-turn boundary, idle
state and source cursor before mutation. It preserves workspace attachment and
releases observations. The existing Python journal still records intent before
mutation and refuses replay of unknown outcomes. Both desktop and browser callers
negotiate `exactFork:1`; older integrations retain the conservative refusal.

Real DSH deterministic-model proofs passed through the desktop adapter on Linux
and macOS. The Mac headed browser proof now verifies successful Edit/resubmit,
excluded old input, preserved tool prefix and unchanged parents. Evidence:
`outputs/cross-platform/linux-dsh-exact-edit.log`, `mac-dsh-exact-edit.log`, and
`mac-dsh-exact-browser-proof.json`. All 83 JavaScript tests and the eight existing
Python branch tests passed, including unknown-outcome protections. This fixes the
previous queued-suffix Edit gap in current source, not every DSH parity issue.
Steered-input boundaries, native interaction dialogs and new installed candidates
still require work. The adapter depends on the inspected rc.1 host composition
services and must be requalified before any DSH upgrade.

Exact-fork recovery follow-up: all 11 Python branch tests pass, including explicit
coverage for the negotiated path's cursor, excluded legacy fork, lost acknowledgement
under a different request identity, and resuming model setup for a known child.
Real DSH proofs on Linux and macOS now create a child, deliberately discard its
acknowledgement, then verify that retrying with another identity invokes no second
creation and preserves parent history. Evidence:
`outputs/cross-platform/linux-dsh-exact-recovery.log` and
`outputs/cross-platform/mac-dsh-exact-recovery.log`. This is real service mutation
with transport-failure injection, not a live external-provider test.

### Installed macOS development candidate 4

Built and installed candidate 4 with shortcut and pinning changes, retaining the
previous preview as a rollback bundle. ZIP SHA-256:
`788e9be1a4999c8e189f4046b58b35ff006817be9f050fb73e591fb13cc62062`.
The installed app's Python and modules passed the actual Qt Settings Save-button
test with native hotkey registration, persisted choice, conflict preservation,
restore, function-key registration, navigation-key resolution and native pin/unpin
readback. Its ad-hoc code signature verified after these tests. Evidence:
`outputs/cross-platform/mac-shortcut-dialog-proof.json` and
`mac-shortcut-dialog.png`; the remote settings/pin proof JSON records the installed
app root. The initial dialog fixture omitted the controller worker dispatcher in
preview mode; attaching the real unconnected controller corrected the fixture.
No model connection or synthetic shortcut event was needed for these checks.
All 162 current Linux native tests passed. Actual global-key delivery, Spaces
navigation, login/closed-app launching and public distribution gates remain open.

### macOS hotkey backend in progress

Added `services/desktop/macos-hotkey.swift`, a Carbon hotkey registration helper
with newline JSON readiness/pressed events. It registers a single combination
exclusively, validates its arguments, and releases registration when the owning
process closes stdin. It uses registration rather than a keyboard event tap.
The SDK's `CarbonEvents.h` documents `kEventHotKeyExclusive`; the initial test
demonstrated that default registration permits duplicates, and the helper was
corrected to use exclusivity. Native Mac testing passed registration, duplicate
refusal and release/re-registration after owner EOF. Evidence:
`outputs/cross-platform/mac-hotkey-proof.json` from `scripts/macos-hotkey-proof.py`.
Actual key-event delivery, Qt settings integration, persistent launch behavior and
packaging are not yet implemented/qualified, so macOS shortcuts remain incomplete.

Follow-up: the helper resolves printable keys through the active Carbon Unicode
keyboard layout instead of assuming ANSI positions. The Mac proof checks
case-equivalent resolution and rejects invalid multi-character input. The macOS
builder now compiles the helper into the bundle, but a new packaged candidate
containing it has not yet been built. Layout changes during an active registration,
Qt settings integration and actual key delivery remain open.

The source now routes macOS Settings reads/saves to `macos_shortcuts.py` instead
of KDE. It restores the saved choice at desktop startup, owns the helper process,
and forwards pressed events to the window's show/hide handler through a Qt signal.
A new shortcut is registered and persisted before the previous registration is
released; failed replacement preserves the prior binding. Native Mac proof passed
save, conflict preservation, private configuration and restoration. Evidence:
`outputs/cross-platform/mac-shortcut-settings-proof.json`. All 21 Linux window
tests and four existing shortcut tests passed. Actual shortcut input delivery,
launch while the app is closed, login persistence, keyboard-layout changes and
installed-package acceptance remain open. Function/navigation keys are not yet
supported by the settings adapter; it reports that restriction rather than guessing.

Follow-up: the adapter now supports F1–F20 and standard navigation/editing keys
using the SDK's Carbon virtual-key constants. The native Mac settings proof passes
F19 registration and left-arrow resolution as well as the previous persistence
and conflict checks. The helper also observes input-source changes; the manager
re-resolves printable keys and replaces their physical binding, or releases a
stale binding and reports an error if re-registration fails. Swift compilation and
the native settings regression pass; actual input-source switching and key-event
delivery have not yet been qualified.

### macOS workspace pin implementation

Pinning now applies AppKit `canJoinAllSpaces` to the application's own Qt window.
Unpinning restores its prior Spaces flags and preserves unrelated collection
behavior. Access is limited to the GUI thread and Cocoa platform. Implementation
uses Qt's documented [NSView native handle](https://doc.qt.io/qt-6/qtdoc-demos-windowembedding-example.html)
and Apple's [canJoinAllSpaces behavior](https://developer.apple.com/documentation/appkit/nswindow/collectionbehavior-swift.struct/canjoinallspaces).
The actual Mac Cocoa-window proof passed repeated pin and unpin readback in
`scripts/macos-window-proof.py`; evidence is
`outputs/cross-platform/mac-window-proof.json`. Actual navigation between Spaces
and fullscreen/Stage Manager behavior remain unverified. This source change is
not yet part of the installed development-3 bundle. macOS global shortcut support
is still an independent implementation gap.

### Linux package qualification in progress

The current source built separate Debian 13 amd64 runtime and desktop candidates
in `outputs/debian-cross-platform-1`. Clean-container runtime-only installation
passed without system Node or Qt, including file work, shared prompts through the
native host, image resizing, Stop, maintenance backup and restart without replay.
Desktop first-run model setup and file work also passed. The shortcut test then
failed because it searched for the old window title. Its selector now uses
`Augmentor Agent Desktop`; candidate 2 passed the full container proof, including
shortcut launch, hide/restore, shortcut-service restart, maintenance shortcut
removal and uninstall with user data retained. Evidence:
`outputs/cross-platform/linux-package-proof-2.log` and
`outputs/debian-cross-platform-2/artifacts.json`. This is Debian 13 amd64 packaging
and isolated X11 GUI evidence, not Wayland input, reboot or all-distro qualification.
Candidate 1 does not have a passing full package proof. These builds record
the dirty source state and are development artifacts, not publishable releases.

### DSH Mac acceptance, 2026-09-14

The locked real DSH rc.1 environment passed the browser setup fixture through
the installed preview's extension and native host in headed Chrome for Testing.
It verified checked connection/save, desktop/browser role isolation (including
direct native-pipe requests), legacy update refusal, actual browser page result,
branching with tool history, unchanged parent history, and refusal of the known
ambiguous Edit before mutation. Evidence:
`outputs/cross-platform/mac-dsh-browser-proof.json` and `mac-dsh-browser-proof.log`.
DSH and its integration ran in the isolated source qualification environment;
the browser components came from the installed app. This is not a completely
self-contained installed DSH distribution or full Edit parity.

The native DSH reply fixture also passed saved-reply visibility, mouse copy,
scroll preservation and no replay, including an injected empty final event.
Both cases recorded `streamObserved:false`: the fixture does not establish
incremental streaming visibility. Evidence:
`outputs/cross-platform/mac-dsh-native-reply-proof.log`.

Follow-up: the fixture previously returned all text at once. It now flushes three
delayed SSE chunks for the reply regression request, and the native proof requires
visible partial text before completion. Fresh runs passed on both Linux and macOS
with `streamObserved:true` for normal and injected-empty-final cases, alongside
copy, scroll and no-replay checks. Evidence:
`outputs/cross-platform/linux-dsh-streaming-proof.json` and
`outputs/cross-platform/mac-dsh-streaming-proof.json`. These use real DSH and Qt
with a deterministic streaming model, rather than a live external model provider.

The installed Mac desktop helper reports both Screen Recording and Accessibility
permissions absent. Its permission request has been invoked and local user
approval requested; live input/capture remains pending. Code-signing identity
inspection still reports zero valid identities, so Developer ID signing remains
owner-dependent. Other implementation work can proceed independently.

### Mac browser acceptance, 2026-09-14

The installed preview's extension and native launcher passed the real headed
Chrome for Testing 153.0.8010.36 acceptance fixture on ARM64 macOS. Both existing
configuration and fresh browser setup passed. Checks exercised navigation,
snapshot, typing, clicking and actual page verification; clipboard copy and prompt
insertion; saved prompt conflict handling; branch/edit preserving tool context;
runtime exit/reconnect without replay; and private support-report download.
The model was deterministic, while the browser, native companion and Pi SDK were
real. This does not qualify DSH browser workflows, every browser tool, Chromium or
Brave distributions, or a browser-only companion package.

Evidence: `outputs/cross-platform/mac-browser-headed-proof.json`,
`mac-browser-fresh-proof.json`, and `mac-browser-headed.png`. The headless run
failed clipboard insertion; the headed run uses the real macOS pasteboard.
The test now accepts an explicit browser executable and installed native launcher,
uses macOS clipboard commands, checks process exit without `/proc`, and cleans up
the private prompt daemon through its fixture socket.

Chrome for Testing was installed only under the isolated development directory,
from the [official availability listing](https://googlechromelabs.github.io/chrome-for-testing/).
Downloaded mac-arm64 ZIP SHA-256:
`1f701ef60757c63c6ccf98afaf28291dd0c8d1457d3d738e81fd62201c230ad0`.
This hash records the downloaded test artifact; it is not an upstream signature.

macOS Chromium registration now points at the installed preview's browser host.
The registered launcher passed direct native-message framing checks for the
matching-version handshake, retired-harness refusal and version-mismatch refusal.
Evidence: `outputs/cross-platform/mac-native-host-proof.json`. Two registration
regressions cover preserved manifests/idempotence and symlink refusal. The app's
signature still verified after registration. The headed Chrome for Testing evidence above adds browser acceptance for its
specific tested workflows; this direct pipe test alone would not establish it.

These are incomplete until evidence for the actual candidate is recorded:

- Complete and qualify the DSH feature/plugin matrix, including ambiguous Edit
  boundaries and native approval/question handling. Qualify Pi's declared subset.
- Real macOS capture/input with user-granted Screen Recording and Accessibility;
  visible independent Stop, denial/revocation, focus changes, secure surfaces,
  Unicode, display changes and restart without replay.
- macOS browser installation/native-host registration and browser tool acceptance;
  tray/shortcut/Spaces behavior and an independently installable browser companion.
- Installed Linux candidate acceptance, upgrade/reboot/rollback/uninstall, and
  explicit distro/desktop support labels. Unit tests cannot qualify other distros.
- macOS upgrade locking, rollback and retained-data uninstall; final installed
  artifact acceptance. Existing ad-hoc development builds are not public releases.
- Developer ID signing, notarization, packaged dependency licenses/source notices,
  source and artifact identity, checksums and clean-user installation evidence.
- Public distribution assets and matching website download information, with
  supported platforms and version requirements stated accurately.

Preserve existing user changes and legacy OpenCode data while retiring its active
support. Do not treat a source test, fixture model, ad-hoc signature or successful
launch as proof that these release gates are complete.

Native DSH interaction work in progress: the product adapter now owns an ephemeral
broker and authenticated interaction operation handler. Every operation checks the
persisted desktop preset and refuses subagents. Leases expire automatically using
a monotonic clock; expiry and disposal delegate pending requests without granting
approval. Focused tests cover ownership, stale replies, cancellation, question
validation and role changes before an answer. DSH approval/request and
user-questions/request listeners now forward only leased desktop sessions;
browser, subagent and unowned requests delegate to the existing handlers.
Seven broker/listener tests pass. A direct check using the pinned DSH Cordis
and dsh-scope packages verified scoped approval delivery, explicit rejection
and fallback after disposal. This checks request routing, not the complete
DSH approval service audit or native dialog presentation. The native client
presentation path and installed release acceptance are still pending.

The native interaction transport now translates pending broker records into the
existing approval/question dialog frames and has an authenticated adapter request
method. Three Python tests verify single presentation, host cancellation,
session isolation, release without an answer, and no answer replay after a lost
acknowledgement followed by polling. EventStream now claims and polls the selected
session, routes replies through its active owner, and releases ownership on close
or stream failure. The host advertises nativeInteractions:1; the adapter enables
this path only after checking its descriptor and home identity. Two additional
tests cover reply routing and cleanup without clearing a replacement connection;
23 focused Python DSH tests pass. Live service/dialog and installed acceptance
remain pending; these unit checks do not establish complete DSH compatibility.

Running-service follow-up: the setup fixture now opens a native interaction
stream, polls its authenticated lease, closes it and immediately reconnects to
the same desktop session. This passed on Linux and the networked ARM64 Mac Mini
using the isolated source checkout and deterministic model. Logs are
`outputs/cross-platform/linux-dsh-interaction-stream.log` and
`outputs/cross-platform/mac-dsh-interaction-stream.log`. The complete native
Python suite also passed (170 tests). This verifies startup and ownership
lifecycle, not actual approval/question presentation or installed package parity.

Question service follow-up: the real Linux fixture initially failed because the
desktop preset omitted `dsh-tool-ask-user`, then exposed ordering behind DSH's
remote question handler. The preset now includes the question tool and native
listeners prepend, delegating whenever they do not own the requesting desktop
session. The rerun delivered an actual `ask_user_question` request through the
native stream and returned the selected answer to the deterministic model as a
tool result (`outputs/cross-platform/linux-dsh-question-3.log`). This exercises
the real question service and transport, with a programmatic answer; Qt dialog
interaction, approval audit, and packaged candidate checks remain outstanding.
The same real question round trip also passed on the ARM64 Mac Mini from the
isolated source checkout (`outputs/cross-platform/mac-dsh-question.log`).

Qt question follow-up: the Linux fixture now presents the real DSH question
through `Window.on_interaction`, fills the input and clicks the Qt OK button;
the selected answer reaches the model tool result. The captured dialog was
visually inspected (`outputs/dsh-question-dialog.png`). A new Qt cancellation
test verifies that host resolution closes the dialog without answering or
stopping the conversation. It also caught and fixed late delivery of an already
resolved request, which now remains invisible. This is one single-choice question;
multi-select, richer question detail, approval dialogs and installed acceptance
still need qualification.
The same Qt question fixture passed on macOS using the offscreen Qt backend
(`outputs/cross-platform/mac-dsh-question-dialog.log`); this does not establish
Cocoa focus, keyboard navigation or installed app behavior.

The question UI now uses explicit single/multiple selection controls, displays
review detail as plain text, supports custom answers and refuses empty answers
through the OK button. Three Qt tests cover multi-select labels, literal review
detail, single selection, blank-answer validation and cancellation. The updated
real DSH question fixture passes on Linux with the new selection control
(`outputs/cross-platform/linux-dsh-choice-dialog.log`); 23 focused Python DSH
tests also pass. The new dialog still needs macOS rerun and richer live question
cases; prior macOS text-input results do not qualify this replacement.

Cocoa follow-up: the setup fixture now accepts an explicit test Qt backend.
The replacement choice dialog passed the real DSH question flow on the ARM64
Mac Mini with `AUGMENTOR_PROOF_QT_PLATFORM=cocoa`; the captured dialog was
inspected (`outputs/cross-platform/mac-dsh-choice-cocoa.png`, matching `.log`).
This remains source-checkout testing with a deterministic model. Five focused
Qt tests now also verify approval default-No, cancellation without an answer,
and explicit Yes/No mapping to one-time approval/rejection. Actual DSH approval
service audit and installed artifact acceptance are not yet established.

Approval service follow-up: an opt-in fixture plugin registers a harmless tool
that invokes the actual DSH approval service and returns its outcome without
performing an external action. The Linux running-service proof clicks No and Yes
in the native dialog and verifies one matching `approval/asked` and
`approval/decided` pair per request, with the expected rejection/one-time approval
and a subsequent turn end (`outputs/cross-platform/linux-dsh-approvals.log`).
This verifies service audit and native transport decisions; sandbox escalation,
Stop/disconnect during a real pending approval, and installed packages remain
separate acceptance cases.
The same rejection/one-time-approval audit proof passed on the ARM64 Mac Mini
with Cocoa (`outputs/cross-platform/mac-dsh-approvals-cocoa.log`). Both runs
used the isolated source checkout, a deterministic model and the harmless test
tool, not the installed release candidate or an escalated OS command.

Pending approval cancellation: the Linux running-service fixture now cancels
the session while the Qt approval dialog is open, waits for host resolution,
verifies no UI answer was sent, attempts and rejects a late approval, and checks
one matching audit pair with outcome `cancelled` followed by turn end. Rejection
and one-time approval cases also still pass
(`outputs/cross-platform/linux-dsh-approval-cancel.log`). The cancellation uses
the native adapter's session.cancel operation; this is not yet a physical Stop
button or process/network-loss test.
The same three-outcome audit and late-answer refusal passed on macOS Cocoa
(`outputs/cross-platform/mac-dsh-approval-cancel-cocoa.log`).

macOS development candidate 5: rebuilt on the Mac Mini with the exact-fork and
native interaction changes, verified its ad-hoc signature, and installed it as
`~/Applications/Augmentor Agent Desktop Preview.app`. The previous app was retained
as `Augmentor Agent Desktop Preview.before-91de76e066b84661bd65a4ad43485de3.app`.
The ZIP is 287178190 bytes, SHA-256
`1c37396c0070897056a238e5494af28447475a4ae27ad02e4c3282ba48b57649`, under
`outputs/macos-development-5` on the Mac. Public-release readiness remains false.
Local regression checks passed 90 JavaScript and 175 native Python tests; an old
question-dialog test was updated to the new choice control after its obsolete
QInputDialog assertion stalled the first run. Candidate 5 installed acceptance
is still pending. Build/install logs: `outputs/cross-platform/mac-package-5.log`
and `outputs/cross-platform/mac-install-5.log`.

Candidate 5 installed-code acceptance: the DSH setup fixture now accepts an
explicit application root and records the imported adapter file. Running with
the installed bundle's Python and Node on macOS Cocoa passed native question
answers, rejection/one-time approval/cancellation audits, exact Edit with model
continuation, and no replay after a lost exact-fork acknowledgement. Evidence
records both root and adapter under `~/Applications/Augmentor Agent Desktop
Preview.app/Contents/Resources/app` (`outputs/cross-platform/mac-installed5-dsh.log`).
Installed shortcut persistence/conflict/re-registration and AppKit pin-state
readback also passed (`outputs/cross-platform/mac-installed5-native.log`). These
do not test physical global-key delivery, closed-app launch or Spaces navigation.
The installed bundle passed `codesign --verify --deep --strict` after these runs.
It is still an ad-hoc development build, not Developer ID signed or notarized.

Linux candidate 3: rebuilt the Debian 13 amd64 runtime and desktop packages in
`outputs/debian-cross-platform-3`. Archive inspection confirms inclusion of the
exact-fork adapter, interaction broker, native interaction transport and question
dialog. Runtime SHA-256:
`081e3509cbd6fbf03c322101278bf3b9a02a03f4070aa701e916a7abcc803ce4`;
desktop SHA-256:
`11a7492d4208024190404d5a55d29f6d0175402a3944f45218f2a42dd999dd05`.
The manifest records a dirty source checkout; these are development artifacts.
Candidate 3 clean Debian container acceptance completed successfully: standalone
runtime/file/image/prompt operations, Stop/restart without replay, desktop first
run, shortcut launch/hide/restore and service restart, then package removal
preserving user data and removing owned registration. Evidence:
`outputs/cross-platform/linux-package-proof-3.log`. This is Debian 13 amd64 X11
fixture evidence, not other distributions, KDE Wayland or reboot qualification.

macOS notice inventory: inspection of candidate 5 found no recorded notice files
for PySide6_Essentials 6.8.2.1 or shiboken6 6.8.2.1, including a search inside
their package directories. Other installed Python distributions retain notices.
The packaging script now generates `licenses/python-inventory.json` with exact
versions, notice paths/hashes and missing entries. This report explicitly does
not certify license compliance or cover embedded native-library source
obligations; the missing Qt/PySide notices and source obligations remain an open
distribution gate. The inventory generator ran against candidate 5 without
modifying its signed bundle; its build-time integration awaits the next build.

PySide notice follow-up: fetched upstream v6.8.2.1 from code.qt.io, verified its
resolved commit `f62088b4cd516a3080a6b2e68bc79903da8b67ce`, and preserved 11
license/COPYING files under `licenses/pyside-6.8.2.1` with per-file hashes and
provenance. These will be included by the existing license-directory packaging
step; they do not complete Qt's embedded third-party notices or source delivery.
The macOS release configuration now pins the entire tested Python distribution
set, and the packager refuses added, removed or changed distributions. The current
Mac bundle matches that set; the build check includes the copied base interpreter's
packages as well as the venv (pip is inherited from the base). A rebuilt candidate with these additions
has not yet been produced.

The revised Python dependency check was verified against the Mac venv plus base
interpreter and matches all seven pinned distributions. Candidate 5's Qt runtime
reports 6.8.2; this is now pinned separately from PySide 6.8.2.1. A new build-side
Qt inventory records framework names and SHA-256/size of shipped framework and
dylib binaries after signing, outside the sealed bundle. It ran successfully
against candidate 5 (`outputs/cross-platform/mac-qt-binaries.json`). The inventory
includes optional QML/designer/image-format components shipped by Essentials;
their notice/source coverage is not established merely by this inventory.

Prepared the pinned upstream PySide source archive under `outputs/native-sources`
using `scripts/package-native-source.py` and `release/native-sources.json`. The
exporter refuses a mismatched or dirty checkout and unresolved submodules.
Archive SHA-256: `eba6f92b4f6d735e911095fd2d8e5e6de0938ad37d00fb5e65b965d756da0e67`;
size 19178995 bytes. All archive file contents were checked against Git blob IDs;
only four Git metadata files marked export-ignore upstream are omitted. The
PySide notice collection now also contains both runtime Python attribution
records and their referenced license files. This archive is not published;
wheel build provenance, Qt source modules and replacement instructions remain
unverified or incomplete, as recorded in the source manifest.

Qt source preparation: pinned upstream Qt Base v6.8.2 to commit
`f1136de66638060b8a1ab9bc0cdf1a91dcb5ec01` in the source manifest. Its clean
checkout download is in progress. Added a collector for upstream attribution
records, referenced license files and LICENSES texts, retaining paths and hashes.
A PySide trial preserved 15 files and reported three unresolved records (including
malformed upstream example JSON), rather than claiming complete coverage. All
collected file hashes were verified. This preparation does not close the native
source/notice distribution gate. The Qt Base checkout subsequently completed;
collection preserved 122 files from 48 attribution records, with 14 unresolved
items to inspect (`outputs/qtbase-notice-collection/collection.json`). Its pinned
source archive export is now running.

Qt Base source export completed: 62967100 bytes, SHA-256
`af23bb3d19599787ab40847021dfb30094ae5e17b2a3c2fb0c905171e9f417be`, in
`outputs/native-sources/qtbase-6.8.2-source.tar.gz`. Attribution collection now
supports upstream literal control characters, LicenseFiles and CopyrightFile,
plus exact LicenseId matches in the upstream LICENSES directory. The resulting
`licenses/qtbase-6.8.2` preserves 57 records and 132 files with zero unresolved
file references. All copied hashes and nine LicenseId mappings were checked.
This resolves collection references, not binary-to-source provenance or the
other Qt modules' notice/source obligations. Next packages will include the
collection through the existing license-directory copy step.

Qt SVG and image formats: pinned and exported upstream 6.8.2 source archives
and collected their attribution/license files under `licenses/qtsvg-6.8.2` and
`licenses/qtimageformats-6.8.2`. Both collections have zero unresolved references
(9 and 11 files); notice and archive hashes were verified. Source SHA-256 values:
qtsvg `b8826812ca5af34fded65146c3ea34d56ce75043ac0953775ac22db9909a8f41`;
qtimageformats `6d80c112541568c9af5d90a9a98694c275b78fd498897e947fc9718edb36b7c0`.
The collector regression test covers multiple license references, CopyrightFile,
exact LicenseId resolution, explicit missing-file reporting and dirty-checkout
refusal. Remaining bundled Qt modules and binary build provenance are still
open; these source artifacts have not been published.

Further Qt modules: pinned qtdeclarative, qttools and qtquicktimeline 6.8.2 to
their upstream release commits. Qt Quick Timeline source export completed
(SHA-256 `92afd3bd9c80b2608ef0aed4c1c1df7d4ec1ac303b51a4f196d5b3e7f7d7f6a8`,
104398 bytes) with four verified license files. Qt Tools collection preserved
15 verified files, but source export correctly refused its unresolved qlitehtml
submodule at commit `2992a310640697325791a5494ca8f4d4552de368`.
Fetching that pinned submodule and the Qt Declarative checkout is in progress.
Neither is yet a complete prepared source archive.
Both downloads completed. Qt Declarative collection contains seven attribution
records and 20 files with no unresolved notice references, but its archive also
requires submodules. The fetched qlitehtml revision itself pins litehtml at
`6ca1ab0419e770e6d35a1ef690238773a1dafcee`; recursive source export and notice
collection must account for this nested dependency before completion.

Recursive source exports now verify every initialized submodule's repository
root, pinned commit and clean state, then merge its Git archive at the original
path. Qt Tools export includes qlitehtml and nested litehtml; Qt Declarative
includes its pinned test262 suite. Both exports completed, with per-submodule
commit records. Qt Tools archived files were checked against Git blob IDs, with
export-subst `.tag` checked against its commit; all three repositories contributed
entries. Qt Declarative verification encountered a tree-ID `.tag` format and
needs a corrected check before full content verification is established. SHA-256 values:
qttools `c99340a42d0ad3444ee42c22218069913b7c0695ed406055749dff077cde47ed`;
qtdeclarative `90bf2ce7663a656a0c3e3e8352d8c33a80514b233ad3e22409e5062c0aa6e071`.
Checks also verified refusal of a wrong commit and an uninitialized submodule
path falling back to its parent repository. Binary build provenance and nested
third-party notice review remain open; no source archives have been published.

Recursive archive verification completed with a reusable checker. It verifies
archive SHA-256, pinned repository/submodule state, unique expected file entries,
Git blob content, explicitly attributed export substitutions/CRLF conversion,
and upstream export-ignore attributes for every omitted file. Qt Tools verified
4738 entries (two transformations, 15 upstream omissions); Qt Declarative verified
53080 entries (two transformations, 13 upstream omissions), including test262.
Reports are `outputs/native-sources/qttools-verification.json` and
`qtdeclarative-verification.json`. A negative check removed build files and
recomputed the archive checksum; the checker still refused unexplained missing
source. This closes the previously incomplete archive-content check, not binary
build provenance or release publication.

Nested Qt Tools notices: collected qlitehtml's two attribution records, including
Gumbo and litehtml, with nine verified files and no unresolved references in
`licenses/qlitehtml-2992a310`. The collector now resolves each exact upstream
license text in simple AND expressions; its regression test covers that case.
The candidate 5 plugin dependency scan also found optional plugins whose Qt
framework dependencies are absent, including PDF, WebEngine and virtual-keyboard
plugins (`outputs/cross-platform/mac-optional-plugin-dependencies.json`). This
does not contradict the tested desktop flows, but the packaged plugin set needs
review before a final distribution and notice/source coverage claim.

Added an explicit macOS staging policy for the 16 optional plugins whose Qt
frameworks are absent from the pinned Essentials wheel. The staging tool scans
all dylibs and requires an exact match with that reviewed dependency list before
removing anything; it preserves other plugins and records removed-file hashes.
Augmentor's native imports use Qt Widgets rather than these absent engines.
Two focused tests verify refusal before mutation on changed dependencies and
preservation of required plugins. Candidate 6 is now building on the Mac with
this staging step, the collected notices and pinned Python/Qt checks. It is not
yet installed or accepted; build log: `outputs/cross-platform/mac-package-6.log`.

Candidate 6 completed and was installed as the Mac Preview, retaining candidate
5 at `Augmentor Agent Desktop Preview.before-8d3a8be37f054bafac2d251831919645.app`.
ZIP size 283475148 bytes; SHA-256
`a0a38735ec504e4bdbe63764c4fbbb7bbc7282b59dacb8f3bec4b0a9d2eef22d`.
The staged removal record verifies all 16 reviewed plugin files are absent;
the signed inventory records 64 Qt frameworks and 155 binary entries. Installed
Cocoa checks passed PNG/JPEG/WebP encode-decode and SVG rendering, plus real DSH
questions, all three approval outcomes, exact Edit and lost-fork-acknowledgement
recovery. Imported paths point into the installed bundle. Post-use strict deep
code-sign verification passed. Evidence: `outputs/cross-platform/mac-install-6.log`
and `mac-installed6-acceptance.log`. Public-release readiness remains false;
Developer ID/notarization, full platform acceptance, source distribution and
remaining product features are still open.

### Shortcut activation prerequisite

Added `shortcut_activation.py` for an external macOS shortcut owner to deliver
the existing desktop IPC toggle or launch the desktop when the listener is
absent. Requests during child startup are coalesced. A connection timeout,
permission error or failed send never triggers a fallback launch, avoiding
duplicate instances or replay of an uncertain toggle. Launch arguments remain
an argument vector so installed paths containing spaces work without a shell.

Four focused tests pass on Linux and the network Mac Mini. One uses a real Unix
socket listener; process launch and transport failure cases use controlled
substitutes. This is a prerequisite, not completed closed-app shortcut support:
the external shortcut owner, settings handoff, login registration and physical
key acceptance are still pending. Candidate 6 has not been rebuilt with this
module, and its installed behavior is unchanged.

### Separate macOS shortcut service

Added a per-user shortcut service and a settings client, using a private Unix
socket and an exclusive process lock. The service owns the native hotkey helper
and uses the desktop activation component. A connected desktop delegates saves
to the service; closing that client leaves the registration running. Invalid or
oversized messages preserve the prior binding. Uncertain service responses do
not cause the desktop to take competing local ownership. The component launcher
now accepts `shortcut-service` and acquires the installation lifetime lease.

Five focused service tests pass on Linux and macOS, using real IPC and a fixture
helper. A separate Mac Mini proof starts a real service subprocess with the
installed Carbon helper: native exclusive registration survives client close,
termination releases the key, and process restart restores the persisted key.
Evidence: `outputs/cross-platform/mac-shortcut-service-proof.json`. Helper pipes
are now closed after failed registration and normal watcher completion.

This service is not yet registered at login or included in a refreshed installed
candidate. LaunchAgent installation/removal, upgrade coordination, and physical
shortcut delivery through the full app remain open. Existing source launches
retain local shortcut ownership when no service is listening.

### macOS login registration lifecycle

Added an owned per-user LaunchAgent registrar with install/start/stop/remove
actions, explicit installed-code signature validation, immutable argument arrays,
private plist creation and refusal of foreign registrations. The desktop avoids
taking local shortcut ownership while a registered service is unavailable.
Registration removal preserves saved settings. Automatic installer suspension
and resumption remain pending; the documented update workflow stops the service
before taking the installation lease and starts it afterward.

Four registrar tests pass. A Mac Mini source fixture passed real launchd
bootstrap, native Carbon registration, bootout, restart with the saved key and
removal preserving settings. The initial restart test exposed asynchronous
bootout: launchd briefly still reported the departing service. Stop now waits
until the service disappears from launchd before returning, and the real proof
passes. Its temporary login registration was removed. Evidence:
`outputs/cross-platform/mac-shortcut-login-proof.json`. This does not establish
actual logout/login behavior or acceptance of a newly signed installed bundle.

### Installer shortcut coordination and candidate 7

The installer now serializes shortcut suspension, bundle replacement and service
resumption under a separate coordination lock. It releases the installation write
lease before resuming the service, including failure paths. Active conversation
leases still refuse replacement; an initially stopped shortcut service stays
stopped. Registered installations refuse rollback to candidates without service
support. Ten installer tests pass, and the full native suite passes 194 tests.

Built and installed development candidate 7 on the Mac Mini. ZIP size 283489940;
SHA-256 `545795f0bc9377c1ae4e043673b6f1a1fbaff8cfcf618aa936c0a812a6ffef4f`.
The initial install retained candidate 6 at
`Augmentor Agent Desktop Preview.before-b8d7f5003cf146358942540808e9d227.app`.
A second real installed upgrade ran while its launchd shortcut service held the
shared installation lease. The service was suspended and resumed with a new PID
and the persisted native Carbon key; the previous bundle was retained at
`Augmentor Agent Desktop Preview.before-30dacff81b5d4b03a2fd5cd7dde070ce.app`.
Strict deep signature verification passed after use. The proof's temporary login
registration was removed, preserving normal user settings.

Evidence: `outputs/cross-platform/mac-package-7.log`, `mac-install-7.log`,
`mac-shortcut-upgrade-proof.log` and `mac-shortcut-upgrade-proof.json`.
Candidate 7 remains ad-hoc signed and not notarized. Physical key delivery,
logout/login, abrupt installer termination and power-loss restoration of service
state are unproven. Full candidate acceptance and the other public-release gates
remain open; this upgrade proof does not replace them.

### Durable shortcut resumption after installer interruption

The source installer now persists a private shortcut-resume record before
bootout, bound to the destination and the current registration digest. A later
installation can distinguish a service stopped by the interrupted installer
from one that was already stopped intentionally. It recovers any bundle journal
before resuming, verifies the remaining bundle, and removes the record only after
launchd accepts startup. Changed registrations and unresolved bundle recovery
retain the record and refuse automatic resumption.

Twelve installer tests pass on Linux and the Mac Mini, including real subprocess
exits during shortcut stop, after backup rename and after candidate promotion.
These tests use a controlled registrar; they prove durable recovery decisions
and filesystem behavior, not launchd behavior during an actual crash or power
loss. Evidence: `outputs/cross-platform/mac-installer-recovery-tests.log`.
The new recovery code has not yet been packaged into an installed candidate.

### Real launchd interruption recovery

The Mac Mini proof now supports a deliberate installer subprocess exit after
the real registrar completes bootout. Against installed candidate 7, the source
installer persisted its recovery record, stopped the actual launchd service,
and exited with the injected status. A second source-installer run upgraded the
bundle, restored native Carbon registration with the saved key and a new service
PID, and removed the recovery record. Strict deep signature verification passed.
The previous bundle remains at
`Augmentor Agent Desktop Preview.before-cdeb1bb0eafe46f4b101a6c968659a95.app`.
The proof removed its temporary login registration after success.

Evidence: `outputs/cross-platform/mac-shortcut-interruption-proof.log` and
`mac-shortcut-interruption-proof.json`. This proves actual launchd recovery after
process termination at this boundary. It does not prove power-loss recovery,
physical key delivery, or that candidate 7 contains the newer source installer.
Failed proof runs now retain their isolated settings for recovery instead of
deleting settings still referenced by a pending recovery record.

### Settings-managed login shortcuts and candidate 8

Packaged macOS settings now enable the login service when the user saves a
shortcut. The app validates the key, releases local ownership, registers the
service and sends one save request. An uncertain reply does not cause competing
local registration or a repeated save. Opening an app with no login registration
preserves its existing in-app key until saving, so removing registration is not
silently undone. The Settings dialog explains that saving enables login startup.

Five new settings tests pass; the complete native suite passes 201 tests.
Candidate 8 was built and installed on the Mac Mini. ZIP size 283494868; SHA-256
`dd6f9a848827f3c253d6a89b98b0e5a18c9aa854f2c947733c0f6cd88f209bc3`.
The initial install retained candidate 7 at
`Augmentor Agent Desktop Preview.before-ad18b1ae9e2a4eeab38066861959f282.app`.
The installed Qt Settings Save button created the login registration, saved the
native Carbon key and left the service running after its client closed. The
dialog capture was visually inspected and its instructions and controls fit.
Evidence: `mac-shortcut-dialog-8.log` and `mac-shortcut-dialog-8.png` under
`outputs/cross-platform`.

The interruption proof then used candidate 8's packaged installer, without a
source-installer override, to recover after a forced exit following real bootout.
It restored the saved native key and passed strict deep signature verification.
Backup: `Augmentor Agent Desktop Preview.before-4609ed2f8e114d768876b836fa3b468f.app`.
Evidence: `mac-shortcut-interruption-8.log` and `mac-shortcut-interruption-8.json`.
Both proofs removed their temporary login registrations. Candidate 8 remains an
ad-hoc development build; physical key delivery, logout/login, power loss and
the remaining public-release gates are still unproven.

### Candidate 8 harness acceptance refresh

The installed candidate 8 DSH adapter passed its Cocoa fixture against the pinned
DSH host: checked setup with profile preservation, saved chats, question answers,
one-time approval/rejection/cancellation, browser OS-tool isolation, exact Edit
continuation and refusal to replay lost child-creation acknowledgements. The
fixture made twelve deterministic local model requests and records imported
adapter paths inside the installed app. Evidence:
`outputs/cross-platform/mac-installed8-dsh-acceptance.log`.

Pi browser acceptance passed in Chrome for Testing 153.0.8010.36 with the installed
extension and native-host launcher. Both configured and fresh-model setup runs
verified actual page interactions, macOS clipboard/scroll behavior, reconnect
without replay, branch tool context, single Edit resubmission, shared prompt
conflicts and private support export. Each made eight fixture model requests;
fresh setup also made two endpoint checks. Optional memory and DSH browser tools
were not exercised by these Pi runs. Evidence: `mac-installed8-browser-pi.log`
and `mac-installed8-browser-pi-fresh.log` under `outputs/cross-platform`.

The first browser attempt exposed an overlong Unix socket path in the proof's
macOS temporary directory. The fixture now uses a short `/tmp` location, matching
the installed launcher's runtime strategy. The original failure remains in
`mac-installed8-browser-pi-temp-path-failure.log`; both corrected runs passed.
These results do not establish external-model, desktop-permission or universal
browser compatibility.

### Owned browser registration removal

Added the macOS browser registrar's `--remove` operation as a prerequisite for
complete uninstall. It retires only the exact matching registration into a
uniquely named backup; changed or other-installation manifests, links and unrelated
files are preserved. Missing registration is an idempotent no-op. Five focused
registrar tests pass on Linux and the Mac Mini, covering removal, backup retention,
repetition and refusal paths. Evidence:
`outputs/cross-platform/mac-browser-removal-tests.log`.
This source change is not in candidate 8. Complete app uninstall and its installed
acceptance are still pending; the registration helper alone does not satisfy that
release gate.

### macOS app uninstall

Added a source uninstaller that verifies the app, serializes maintenance, stops
the owned shortcut service and refuses removal while a shared task lease is
active. It moves the app and exact matching registrations into a uniquely named
Trash directory with an original-location receipt. Changed and unrelated
registrations, user data and previous app backups remain. Failed moves roll back
when identities still match; an active-task refusal restores the previous
shortcut service after releasing maintenance locks.

Five focused tests pass. The Mac Mini proof copied signed candidate 8 to a
disposable app, registered a real launchd shortcut service and an isolated browser
host, and uninstalled that copy using the real user Trash. The service stopped,
owned registrations disappeared, settings remained and the retained app passed
strict deep signature verification. The primary preview app was preserved.
Receipt: `/Users/example/.Trash/Augmentor-uninstall-vab5mywd/receipt.json`.
Evidence: `outputs/cross-platform/mac-uninstall-proof.log` and
`mac-uninstall-proof.json`. This source uninstaller is not yet packaged, and
interrupted-uninstall recovery remains unverified.

### Receipt-based uninstall recovery

The source uninstaller now writes and syncs its receipt before stopping the
shortcut service. Its `--restore` operation validates the complete recorded path
set, retained identities and original-location occupancy before moving files,
and verifies the retained app's signature. It accepts already-restored entries
on retry and resumes the prior shortcut service after releasing the write lease.

Seven focused tests pass on Linux and the Mac Mini. Actual subprocess exits
after a browser-manifest move and after the app move recover successfully;
repeated restoration is accepted. A new app at the original location refuses
recovery before any manifest is moved. These filesystem tests use controlled
signature and service calls. Evidence:
`outputs/cross-platform/mac-uninstall-recovery-tests.log`. Real launchd restore,
power-loss behavior and packaging remain open.

### Real uninstall restoration on macOS

Restored the prior disposable candidate 8 copy from its Trash receipt using the
source uninstaller. The app passed signature validation, its browser registration
returned, launchd restarted the shortcut service and the saved native key was
active. User-data sentinels remained intact. The proof then uninstalled the copy
again, leaving the primary preview app in place and retaining a new receipt at
`/Users/example/.Trash/Augmentor-uninstall-q2gjutj3/receipt.json`.
Evidence: `outputs/cross-platform/mac-uninstall-restore-proof.log` and
`mac-uninstall-restore-proof.json`. This verifies real service restoration from
completed uninstall; interruption during real restoration and power loss are
still unproven.

### Candidate 9 packaged uninstall and restore

Built and installed candidate 9, including browser unregistration and the
receipt-based app uninstaller. ZIP size 283505685; SHA-256
`f5776918c55ecb5890b602c72a7202d0f23c19bcd68a8c12e6adfaeac3224c6a`.
The previous preview remains at
`Augmentor Agent Desktop Preview.before-79e53357a22c4fea87e473237f845567.app`.
All 211 native tests pass.

The installed uninstaller passed a real Mac Mini cycle on a disposable signed
copy: stop launchd, retire owned browser/login registrations and app, preserve
settings, restore the app and registrations, restart the native shortcut, then
uninstall the copy again. Both proof records identify the uninstaller inside the
installed preview bundle. The main preview remains installed. The final retained
copy and receipt are at
`/Users/example/.Trash/Augmentor-uninstall-emalhcbx/receipt.json`.
Evidence: `outputs/cross-platform/mac-package-9.log`, `mac-install-9.log`,
`mac-uninstall-cycle-9.log`, and `native-after-uninstall-recovery.log`.
This development artifact is still ad-hoc signed and not notarized. Real
interrupted-uninstall/restore behavior, power loss and the remaining public
release gates are not established by the completed-cycle test.

### Debian candidate 4 and installed DSH acceptance

Built refreshed Debian 13 amd64 packages from the current dirty development
checkout. Runtime size 54794732; SHA-256
`8634b6a3daeb866b2c16b038ef4a08d273127c9c38ac888bf60e14b88b1a85c0`.
Desktop size 4240; SHA-256
`11a7492d4208024190404d5a55d29f6d0175402a3944f45218f2a42dd999dd05`.
Artifacts and manifest: `outputs/debian-cross-platform-4`.

The clean-container package proof passed runtime operation without system Node
or Qt, file/image tools, shared prompts through the native host, Stop/restart
without replay, first-run desktop setup/file task, global shortcut launch and
hide/restore across service restart, and removal preserving user data. Evidence:
`outputs/cross-platform/linux-package-proof-4.log`.

Added a separate installed-package DSH proof using a read-only host package and
an ordinary container user. Candidate 4 passed setup/profile preservation,
questions, approval/rejection/cancellation, browser OS-tool isolation, exact Edit
continuation and no replay after lost child-creation acknowledgement. The evidence
records the adapter at `/usr/lib/augmentor/apps/native/augmentor_linux/adapters/dsh.py`
and twelve deterministic model requests. Evidence:
`outputs/cross-platform/linux-installed4-dsh.log`.
Both disposable containers exited and were removed; existing host services were
unchanged. These tests do not establish reboot/upgrade, actual KDE Wayland desktop
control, external models or additional Linux distributions.

### Debian 0.2.7 → 0.2.8 lifecycle qualification

The preserved 0.2.7 packages and Debian candidate 4 passed the full lifecycle
fixture in a disposable Debian 13 container. In-use upgrade/downgrade was refused
without aborting the active task. Desktop-only removal preserved the active
companion. Interrupted dpkg configuration blocked launches until configuration
completed. Upgrade, rollback and reinstall preserved conversation events, shared
prompt IDs/content/revisions/timestamps, library revision and model-request counts.
Legacy integration migration retained the old application; removal retained
unrelated files. Custom prompt-improvement instructions also survived rollback
to 0.2.7 and subsequent 0.2.8 reinstall.

The first run exposed a fixture assumption: 0.2.8 adds an `improvement` response
field absent from 0.2.7. The lifecycle test now compares every persistent prompt
field and library revision exactly, and explicitly tests preservation of the new
custom instructions across the older release. The original failure is retained
in `outputs/cross-platform/linux-lifecycle-027-to-028-snapshot-failure.log`;
the completed passing run is `linux-lifecycle-027-to-028.log` in that directory.
The container exited and was removed. This qualifies the tested package-version
transition, not a machine reboot, KDE Wayland control or other distributions.

### Candidate 4 Plasma Wayland and reboot acceptance

Created `outputs/desktop-vm-cross-platform4` as a copy-on-write overlay of the
preserved desktop test VM; the original disk and evidence were not modified.
Booted it with software emulation and upgraded its installed 0.2.3 packages to
Debian candidate 4. The marked guest runs Plasma Wayland (KWin 6.3.6), with the
Qt app using XWayland (`xcb`). The VM observer was updated to match the renamed
`Augmentor Agent Desktop` window title.

Installed acceptance passed first-run setup and file work, six external clipboard
and scroll cases, QEMU hardware-key launch/hide/show, a real guest reboot and
shortcut launch afterward without re-registration. Maintenance leases were
recreated after reboot, and removal disabled the owned shortcut. The model was
a deterministic fixture. Evidence: `outputs/cross-platform/linux-vm-upgrade-4.log`,
`linux-wayland-reboot-4.log`, and
`outputs/desktop-vm-cross-platform4/acceptance.json`.

The isolated overlay VM remains available on SSH port 22487 for the next desktop
control checks. This result verifies the tested startup/shortcut lifecycle; it
does not yet qualify current-artifact capture/input/Stop behavior or other Linux
desktops and distributions.

### Candidate 4 installed Wayland desktop executor

Added `--vm-dir` to the desktop proof so the copy-on-write overlay keeps its
evidence separate from the preserved VM. The installed `/usr/lib/augmentor`
executor passed the full native Wayland Kate fixture at 100% scale: denied
consent leaves sharing inactive; Stop closes pending portal consent; foreign
ownership, unsupported text, replayed observations, outside clicks and changed
active windows are refused. The permitted ASCII input and Save As sequence
produced the exact expected file.

A QEMU pointer click on the visible Stop button interrupted a 256-character input
after 15 characters. Saved partial contents remained unchanged after waiting,
sharing stopped and the old action could not restart. The captured desktop image
was inspected: Kate and the visible desktop-control Stop banner were present.
Evidence: `outputs/cross-platform/linux-desktop-control-4.log` and
`outputs/desktop-vm-cross-platform4/desktop-control-scale1.json` (plus the saved
`desktop-observation-scale1.jpg`). No source-executor override was used.
This qualifies the direct installed executor at the tested scale; current-package
harness-driven desktop tasks, fractional scaling and multi-monitor acceptance
remain separate checks. The VM remains available with control stopped.

### Candidate 4 installed Wayland at 125% scaling

The installed executor also passed the full disposable Kate fixture at 125%
scaling. Consent refusal, pending-consent Stop, ownership and coordinate guards,
exact saved ASCII input, and refusal to replay after Stop all passed. Clicking
the visible Stop button interrupted typing after 12 characters; the saved partial
contents remained unchanged. No source override was used. Evidence:
`outputs/cross-platform/linux-desktop-control-4-scale125.log`,
`outputs/desktop-vm-cross-platform4/desktop-control-scale125.json`, and
`desktop-observation-scale125.jpg`. The 150% run is a separate pending check.

### Candidate 4 installed Wayland at 150% scaling

The 150% run completed successfully against the installed executor: denied and
pending consent handling, ownership/replay/window/coordinate guards, exact Kate
file editing, and visible Stop interruption all passed. Stop interrupted the
256-character sequence after 70 characters; the saved partial content stayed
unchanged and the action could not replay. Evidence:
`outputs/cross-platform/linux-desktop-control-4-scale150.log`,
`outputs/desktop-vm-cross-platform4/desktop-control-scale150.json`, and
`desktop-observation-scale150.jpg`. Together with the separate 100% and 125%
runs this qualifies these three scales on the tested Debian Plasma Wayland VM.
It does not establish support for other desktop environments or distributions.

The harness-driven proof now accepts `--vm-dir` and writes results there, allowing
subsequent Pi/DSH checks to preserve the original VM evidence. The two-display
refusal proof is running against the isolated candidate-4 overlay.

### Candidate 4 two-display refusal

The isolated VM booted with two actual virtual displays (one retaining 150%
scaling). The installed executor refused connection before opening a sharing
session, reporting the current one-connected-monitor requirement. The proof
verified inactive sharing and restored the original single-GPU VM; the process
exited successfully. Evidence: `outputs/cross-platform/linux-multi-monitor-4.log`
and `outputs/desktop-vm-cross-platform4/multi-monitor-proof.json`. This validates
the documented refusal, not multi-display desktop-control support.

The Pi/DSH deterministic harness desktop proof has now started against the
installed guest executor. Its host SDK/adapters run from the current workspace,
so any result must distinguish those from the installed guest component.

### Current harness desktop acceptance: partial evidence and capture failure

The current workspace Pi SDK/adapter passed deterministic desktop file editing
and cancellation against the installed candidate-4 executor. DSH test setup
needed its launch-token authentication and persona `prefix` field updated to
match pinned DSH 0.1.5-rc.1 (the production setup already uses `prefix`).

After these fixture corrections, DSH reached desktop control, but a snapshot
returned `No screen frame was received. No input was sent.` The scripted fixture
continued with a previously consumed observation; the executor refused it as
stale. The final exact-file assertion failed. This is not passing DSH acceptance.
Investigate capture availability and make the fixture fail directly on tool errors
before claiming a successful task. Evidence: current
`outputs/cross-platform/linux-desktop-engines-4.log` and the fixture
`/tmp/augmentor-vm-sdk-2cuucgfv/model-requests.json` (image payloads omitted).
Earlier setup failures remain in the `-auth-failure.log` and
`-persona-failure.log` files. The failed run exited and cleaned up its services.

### Focused DSH desktop run passed; intermittent capture issue remains

After fixing the fixture authentication and persona schema, a focused DSH run
passed both exact external file editing and cancellation during typing. Real
screenshots reached the deterministic model and sharing was released in both
cases. The process exited successfully. Evidence:
`outputs/cross-platform/linux-desktop-engines-4-dsh.log` and
`outputs/desktop-vm-cross-platform4/desktop-engines-dsh-proof.json`. The SDK and
adapter are from the workspace; the guest executor is installed candidate 4.

The fixture now ends its model turn on an explicit tool error and fails with that
error, instead of continuing its fixed action sequence. It also accepts
`--harness` to isolate failures. The earlier no-frame failure remains unresolved;
a subsequent passing run does not establish capture reliability. Its evidence is
preserved in `linux-desktop-engines-4-capture-failure.log` and the prior fixture
directory. Further repeated-capture diagnostics are required.

### Thirty consecutive installed captures and follow-on checks

Candidate 4 passed 30 consecutive captures in the Debian Plasma Wayland VM at
100% scale. Each returned a distinct observation token and a 1280×800 image.
Measured RPC durations through the VM transport were 2.465–3.504 seconds
(median 3.010 seconds); these are not native capture-only benchmarks. The same
run then passed target guards, exact file editing, visible Stop interruption
after 11 characters, and no replay. The process exited successfully.

Evidence: `outputs/cross-platform/linux-capture-reliability-4.log`,
`outputs/desktop-vm-cross-platform4/capture-reliability-30-installed4.json`,
`desktop-control-capture30.json`, and `desktop-executor-capture30.log`.
The guest reports PipeWire/gstreamer1.0-pipewire 1.4.2-1 and GStreamer 1.26.2-2;
installed source properties were obtained through GI because gst-inspect is
not installed. These diagnostics are saved in `linux-pipewire-environment-4.log`
and `linux-pipewiresrc-properties-4.json` under `outputs/cross-platform`.

The earlier intermittent no-frame failure is still open. Both VM proof runners
now accept `--capture-debug` for scoped PipeWire/GStreamer executor logging. A
mixed Pi/DSH run with that logging is active to reproduce the original sequence.
No capture backend behavior has been changed on the strength of passing reruns.

### Mixed harness capture diagnostics and macOS restore retry

The mixed Pi-to-DSH desktop sequence completed all four file-editing and
cancellation cases with detailed PipeWire logging enabled. The executor log
contains zero GStreamer critical messages. Evidence:
`outputs/cross-platform/linux-desktop-engines-4-debug.log`,
`outputs/desktop-vm-cross-platform4/desktop-engines-mixed-debug-proof.json`, and
`/tmp/augmentor-vm-sdk-fncr9n4x/executor.log`. This does not resolve the earlier
intermittent no-frame result; that failure remains an open capture investigation.

Fixed macOS uninstall restoration unnecessarily requiring an exclusive lease
when all recorded files were already restored. Such a retry now verifies every
recorded identity and the app signature, then resumes the shortcut if required.
Actual moves still require exclusive access. Nine recovery tests pass on Linux
and the Mac Mini, including a running-app shared lease and refusal to move files
while that lease is held.

A real Mac lifecycle proof using the updated source uninstaller restored a
disposable signed preview copy, retried recovery with its launchd shortcut
service running, and verified that the service PID did not change. Browser
registration and user-data checks passed; the disposable copy was uninstalled
again, leaving the main preview intact. Logs: `mac-uninstall-retry-unit.log` and
`mac-uninstall-running-retry.log` in `outputs/cross-platform`. Final retained
receipt: `~/.Trash/Augmentor-uninstall-m60r4yf3/receipt.json` on the Mac Mini.
Candidate 10 is being built to include the fix; packaged acceptance is pending.

### macOS candidate 10 packaged restore retry

Built macOS ARM64 development candidate 10, version 0.2.8, with the restore-retry
fix. ZIP size: 283506188 bytes; SHA-256:
`226797744d2a7da80c0efcf09c2ae0fa341bf5ed70075470a66ffa00cc53c5d7`.
The bundle remains ad-hoc signed, not notarized, and not publicly release-ready.
Build evidence: `outputs/cross-platform/mac-package-10.log`.

Using candidate 10's bundled Python and packaged uninstaller, a disposable copy
of the existing preview passed uninstall, restore, and retry with the real
shortcut service running. The retry retained its PID; browser registration and
user-data checks passed. The disposable copy was then uninstalled again.
Evidence: `outputs/cross-platform/mac-uninstall-cycle-10.log`; final retained
receipt on the Mac: `~/.Trash/Augmentor-uninstall-akjzw87o/receipt.json`.
This verifies the packaged recovery tools, with no injected process interruption
in this particular real-service run. Installation into the preview is underway.

### Installed candidate 10 and interrupted restore tests

Candidate 10 is installed at `~/Applications/Augmentor Agent Desktop Preview.app`
on the Mac Mini. The prior preview is retained as
`Augmentor Agent Desktop Preview.before-800b7a1d6da74bf48aaa35d9d01512ea.app`.
Strict deep signature verification passed after installation, bundled Qt reports
6.8.2, and bundled Node reports 24.19.0. Evidence:
`outputs/cross-platform/mac-install-10.log` and `mac-installed10-integrity.log`.

Added subprocess tests for abrupt exit immediately after moving either the app
or browser registration during restore. A fresh process retries the same receipt
and verifies the original app contents and manifest. All ten recovery tests
passed locally and on the Mac Mini (the latter using installed candidate 10's
Python against the source test module). Logs:
`uninstall-restore-interruption-unit.log` and
`mac-uninstall-restore-interruption-unit.log` in `outputs/cross-platform`.
Signature validation is mocked in these filesystem tests; no power-loss or
real-launchd interruption claim follows from them. The separate packaged
real-service restore/retry proof remains the evidence for those integration paths.

### Installed candidate 10: real signed-app interrupted restoration

Extended the Mac restore proof with an optional subprocess exit immediately
after the real app-bundle rename, before registrations are restored. On the Mac
Mini, the test used installed candidate 10's Python and uninstaller with actual
signature validation. The child exited with the injected status; retry from the
same receipt restored browser/login registrations, restarted the real launchd
shortcut, and preserved fixture user data. A further retry with the service
running retained its PID. The disposable copy was uninstalled again and the main
preview remained intact.

Evidence: `outputs/cross-platform/mac-installed10-interrupted-restore.log`; final
retained receipt: `~/.Trash/Augmentor-uninstall-a_4gosfj/receipt.json` on the Mac.
This verifies abrupt process exit at that restore boundary, not machine power
loss or every filesystem durability boundary. The proof script changed; candidate
10's recovery implementation was used unchanged.

### Current Linux memory acceptance and Mac installed check

Created a new isolated Podman Hindsight 0.9.2 service named
`augmentor-hindsight-cross-platform`, retaining the earlier acceptance container
and its volume. The new instance binds only 127.0.0.1:8887 and uses the existing
local Qwen model through 127.0.0.1:8080; no external model credentials were copied.
The current source memory proof passed Qt check/save/retain/view/disable, real
asynchronous retention, independent Node recall, user/project isolation, fact
export, remote deletion and local source purge. Real Pi and pinned DSH tool
execution returned recalled context in both surface roles (eight deterministic
harness-model requests). Hindsight extraction/recall used the local model.
Evidence: `outputs/cross-platform/linux-memory-current.log` and
`linux-memory-current.json`; prior 2026-09-06 evidence was preserved.

Updated the memory harness fixture for DSH launch authentication and persona
`prefix`, and added installed-app selection to the memory runner. Test output
stays outside the installed app. A Cocoa run against installed Mac candidate 10
is active through an SSH reverse tunnel to the same isolated Hindsight instance,
using newly generated test-bank names and private temporary app state.

### Installed Mac memory acceptance and remaining product-name labels

Installed candidate 10 passed Cocoa memory controls, actual Hindsight retention
and recall, scope isolation, export, remote deletion and local source purge.
Real Pi and DSH bindings received recalled facts in both surface roles. The
Hindsight service ran on the Linux test host behind an SSH reverse tunnel; this
does not establish a bundled or locally installed Mac Hindsight server. The
tunnel ended with the completed proof. Evidence: `mac-installed10-memory.log`,
`.json`, and `.png` in `outputs/cross-platform`, plus
`mac-installed10-post-memory-signature.log` (strict signature check passed).

Visual inspection found an outdated “Linux app” label. Corrected that native
memory introduction and corresponding browser memory/model-setup/settings and
native onboarding text to use Augmentor Agent Desktop and Browser. Existing
workspace defaults remain compatibility paths. Browser modules pass syntax
checks. These text changes are in source and await the next package build.
Browser memory DOM acceptance remains separate from the native/role checks.

### Installed Mac browser memory UI acceptance

Candidate 10's installed extension, native host and runtime passed the headed
Chrome for Testing 153.0.8010.36 browser fixture with real Hindsight memory.
Pointer-driven connection, retention, source viewing, disable and deletion
passed; the downloaded fact export and independent companion recall were
verified. The ordinary Pi browser navigation, clipboard, branch/edit, shared
prompt and support-export checks also passed. This run does not exercise DSH
browser model execution. Evidence: `mac-installed10-browser-memory.log`, `.json`
and `.png` in `outputs/cross-platform`. Strict installed signature verification
passed afterward (`mac-installed10-post-browser-memory-signature.log`).

Two fixture issues were corrected: waiting for asynchronous Memory settings
mounting, and scoping the open-dialog selector to the Memory section. The hidden
Support report shares a CSS class and had been mistaken for the Memory form.
The diagnostic log preserves that DOM evidence. No application rendering fix was
needed for these failures. The screenshot was inspected at 440px viewport width;
it shows the scrollable connection/data controls, not the full form in one image.

### Naming corrections packaged: Debian 5 and macOS 11

Built Debian candidate 5 and macOS candidate 11, retaining previous artifacts.
Debian runtime SHA-256: `27fb6ab477615c99b260c2df3bb34d09595fb12aca4a4743734477a05db2195c`
(54806528 bytes). Desktop package remains 4240 bytes with SHA-256
`11a7492d4208024190404d5a55d29f6d0175402a3944f45218f2a42dd999dd05`.
Mac ZIP SHA-256: `ddfcbeb9fc484534bf5e907b3aaa482e0c1dd87a5a6f06d45ef0f3d038418110`
(283516803 bytes). All remain version 0.2.8 development artifacts.

Mac candidate 11 is installed in the Preview location, with candidate 10 retained
as `Augmentor Agent Desktop Preview.before-2a48a70cc63b4fdaacce4fbe2e636566.app`.
Strict deep signature verification and installed-content checks confirm the
native/browser naming corrections and historical OpenCode retirement notice.
Evidence: `mac-package-11.log`, `mac-install-11.log`, and
`mac-installed11-content-integrity.log` in `outputs/cross-platform`.
The Mac remains ad-hoc signed and not notarized. Debian candidate 5's package
acceptance is running; its runtime-only phase has passed so far.

### Debian candidate 5 package acceptance completed

The clean Debian 13 container proof exited successfully. Runtime-only checks
passed without system Node or Qt: file work, shared prompts through the native
host, Stop, history-preserving restart without replay, image resize, and idle
maintenance backup. Desktop installation then passed first-run/file work, real
X11/KGlobalAccel launch/hide/restore, shortcut-service restart, and maintenance
removal. Package removal preserved user data and removed owned host registration.
Evidence: `outputs/cross-platform/linux-package-proof-5.log`. This container test
does not qualify a new Wayland capture backend or other Linux distributions.

A read-only status query to installed Mac candidate 11 reports one display with
Accessibility and Screen Recording both ungranted. Recorded as
`outputs/cross-platform/mac-installed11-permissions.json`; no permission prompts
or permission changes were made. Mac desktop-input/capture acceptance is pending.

### macOS browser-only companion implementation underway

Added `--component companion` to the Mac builder. It uses a separate
`com.augmentor.Agent.Companion` bundle identity and omits PySide/Qt, NumPy,
desktop UI modules, capture helpers and the global-shortcut helper. Shared
Node/Python services and the extension remain bundled. Pure Python socket
clients are retained for shared-service integrations and acceptance tests.
Companion release metadata now records only the shipped Python dependencies
(PyYAML and websocket-client), without a Qt dependency claim.

Installer validation accepts matching companion identity/component metadata and
uses a separate default destination. It refuses replacing a different component
at the same location and leaves an unrelated desktop login service alone.
Fourteen installer tests pass, including new identity and separate-shortcut
checks. Browser registration accepts the companion identity. Guided desktop
setup reports a desktop requirement when its script is absent, pointing users
to manual memory connection settings.

Initial companion builds succeeded at approximately 144 MB, but are not release
qualified. Candidate 3 is building with the minimal socket clients and corrected
manifest. Installed browser, coexistence, upgrade and removal qualification
remain required. The desktop's existing release gates are unchanged.

### Installed companion candidate 4: browser workflow passed

Companion candidate 3 installed alongside the desktop preview and passed strict
signature/no-Qt/no-desktop-helper checks, but browser startup failed because
`ensure-runtime.py` imported an omitted non-GUI preferences module. Candidate 4
includes that module, and explicit harness startup no longer imports preferences
unnecessarily. The failed candidate and logs are retained.

Candidate 4 ZIP SHA-256 is
`e23ab388ed492e0bd6bd7cb8e88d46a1084c48f4a8d5c8fd8e81e70277c7c49c`
(144462325 bytes). It is installed at
`~/Applications/Augmentor Agent Browser Companion Preview.app`, with candidate 3
retained as `Augmentor Agent Browser Companion Preview.before-3ef7a3fca3334599b92fb29274e264e6.app`.
Chrome for Testing's native-host registration points to this companion.

The installed companion passed the headed Chrome 153 Pi fixture: actual page
navigation/type/click, clipboard/scroll, reconnect without replay, tool-preserving
branch/edit, shared prompts and private support export. Eight deterministic model
requests were observed. Evidence: `mac-companion-installed4-browser.log` and
`.json` under `outputs/cross-platform`. Memory and DSH execution were not enabled
in this run. Fresh model setup is a separate run currently in progress.

### Companion candidate 4: fresh setup and recovery evidence

The fresh Pi setup rerun completed with two setup requests and eight deterministic
model requests through the installed companion and Chrome 153. Evidence:
`outputs/cross-platform/mac-companion-installed4-browser-fresh.log` and `.json`.
An earlier run timed out during clipboard prompt expansion after its browser
workflow; its failure is retained in
`mac-companion-installed4-browser-fresh-expansion-failure.log`. The passing rerun
does not resolve that intermittent failure. Failure diagnostics now record focus
and fixture-match booleans without logging clipboard contents.

The installed-tools companion lifecycle proof passed on a disposable signed
copy. A held shared installation lock refused removal; uninstall and repeated
restore preserved the signed bundle, matching browser registration and fixture
user data. The desktop login registration bytes remained unchanged. This was a
held-lock test, not a running browser task or crash-interruption test. Evidence:
`outputs/cross-platform/mac-companion-installed4-lifecycle.log`. The final recovery
receipt remains at `~/.Trash/Augmentor-uninstall-c8vgeoyb/receipt.json` on the Mac.

Companion-specific installation instructions now describe bundle selection,
registration replacement, shared maintenance locking and guided-setup limits.
DSH browser and memory workflows through the companion remain unqualified.

### Companion candidate 4: installed DSH browser acceptance passed

The new `AUGMENTOR_PROOF_COMPANION_DSH=1` mode in `dsh-setup-proof.py`
omits Qt and uses the installed companion's PromptClient to start its packaged
shared service. That service checked, installed and saved the integration into
an isolated DSH home, preserving the original profile patch. A source DSH adapter
is explicitly test instrumentation for fixture setup and history inspection;
it is not shipped as desktop UI in the companion.

On the Mac Mini, the installed companion and Chrome 153 passed browser DSH
connection/save, actual navigation/snapshot/type/click with page-result checking,
role isolation, rejected legacy updates, Branch with tool history, exact Edit
replacement and unchanged parent history. The real pinned DSH runtime made eight
requests to the deterministic local model fixture. This is not live-model or
full-plugin qualification. Evidence: `outputs/cross-platform/mac-companion-installed4-dsh.log`
and `.json`; fixture `/private/tmp/augmentor-dsh-setup-o6z_vp9q` on the Mac.
Companion memory acceptance and the other release gates remain open.

### Companion candidate 4: installed browser memory controls passed

The installed companion passed manual memory connection, retain, view, independent
recall, browser fact-export download, disable and deletion against the isolated
Hindsight 0.9.2 service. The Mac connected through a loopback SSH tunnel to the
existing Linux test container, which used the local Qwen model for memory work.
The same run passed the real Pi SDK browser workflow with eight deterministic
fixture model requests. DSH execution was not enabled in this memory run, so this
does not establish DSH memory-tool acceptance through the companion.

Evidence: `outputs/cross-platform/mac-companion-installed4-browser-memory.log`,
`.json` and `.png`; Mac fixture `/private/tmp/augmentor-browser-proof-cduo2dyx`.
The browser deleted the retained fixture document. The test container and volume
are preserved for subsequent qualification. Guided setup, the intermittent
clipboard failure, desktop platform acceptance and public distribution gates
remain open.

### Prompt completion refresh race: source fix awaiting packaged acceptance

Inspection found that every completion-menu refresh replaced all suggestion
buttons, including unchanged periodic refreshes. Replacement between pointer
press and release can detach the intended click target. The source now preserves
buttons when the rendered choices and selection are unchanged, while continuing
to reposition the menu and restore its active-option accessibility attribute.

A regression test holds a completion target across a refresh and verifies that
it stays connected and inserts the selected draft. All five browser prompt tests
pass. This is a plausible contributor to the earlier clipboard-expansion timeout,
not a confirmed diagnosis of that captured failure. The fix has not yet been
packaged or accepted on macOS; installed companion candidate 4 remains unchanged.

### Companion candidate 6: installed completion refresh acceptance passed

Candidate 5 stopped during staging because the remote build PATH omitted npm.
The failure log is retained. Candidate 6 built with the corrected PATH and
installed alongside the existing desktop, retaining companion 4 as
`~/Applications/Augmentor Agent Browser Companion Preview.before-3fc7af9bbb5e47d88ba404e19f835e9c.app`.
Its ZIP SHA-256 is `36b2745ae5eb4d740bb57b4e47f4d01637a718d128bc31a61c941bc1179a8977`
(129064612 bytes). The changed artifact size still needs an inventory comparison
before treating it as equivalent to the previous bundle beyond tested features.

The installed Chrome 153 proof now supports `AUGMENTOR_PROOF_PROMPT_REFRESH=1`:
it presses a suggestion, triggers an input refresh before releasing the pointer,
checks that the same button remains attached, and verifies clipboard expansion.
Candidate 6 passed this check, fresh model setup, actual page interaction,
Branch/Edit, reconnect without replay, prompt conflict preservation and private
support export with eight deterministic Pi model requests and two setup requests.
Evidence: `outputs/cross-platform/mac-companion-installed6-browser-refresh.log`
and `.json`. Fixture: `/private/tmp/augmentor-browser-proof-dzkz1zta` on the Mac.
This proves the controlled refresh behavior; the original timeout's precise cause
remains unconfirmed. DSH and memory evidence still refer to companion 4.

### Companion 4-to-6 archive inventory explains size change

Compared both ZIP inventories and hashed the regular files in the preserved
candidate 4 and installed candidate 6 bundles. No regular application files were
removed: 27310 became 27311, with the companion lifecycle proof added. Total
regular-file content grew from 395039620 to 395056135 bytes. Changes comprise
the prompt-menu fix, proof scripts, documentation, signature records, generated
Python bytecode and npm's internal lockfile.

All 30317 removed ZIP entries are under `__MACOSX/`; no application archive entries
were removed. This metadata difference explains the smaller download, rather than
missing runtime contents. The retained full archive comparison is
`outputs/cross-platform/mac-companion-4-to-6-archive-inventory.json`.

Candidate 6 also passed installed DSH browser acceptance with eight deterministic
model requests: checked setup/save, original profile preservation, page result,
role isolation and exact Branch/Edit history checks. Evidence:
`outputs/cross-platform/mac-companion-installed6-dsh.log` and `.json`;
Mac fixture `/private/tmp/augmentor-dsh-setup-e_hlva4_`. The source adapter remains
explicit test instrumentation; the installed companion supplies the service,
native host and extension. Memory evidence still refers to candidate 4.

### Desktop candidate 12: shared builder regression checked

Built the full desktop with the builder's explicit `--component desktop` path
after adding companion packaging. ZIP SHA-256:
`bca1c81d0c59d05f7757bb1091c20a934fb877ad96c8bcadbe3cdd2cde0da67f`
(268726413 bytes). Installed at `~/Applications/Augmentor Agent Desktop Preview.app`,
retaining candidate 11 as
`Augmentor Agent Desktop Preview.before-9c364ff932224cc6ba3bc0e7dd3a3de6.app`.
The companion remains separately installed.

Installed Python/PySide opened a Cocoa window and passed PNG, JPEG, WebP and SVG
codec checks. AppKit pin/unpin behavior bits were verified and restored; this
does not test navigating Spaces. Strict deep signature verification passed after
these checks. Two Qt staging unit tests also passed. Evidence:
`outputs/cross-platform/mac-package-12.log`, `mac-install-12.log` and
`mac-installed12-qt-window.log`. Desktop capture/input permissions, full harness
qualification, public signing and other release gates remain open.

The source feature matrix's current version guidance now names pinned DSH
0.1.5-rc.1 and separates Linux Chromium from Mac Chrome for Testing evidence.
Older DSH results remain explicitly historical. That documentation correction
was made after candidate 12 staging and is not claimed to be in this bundle.

### Linux capture failure classification added in source

Frame acquisition now checks GStreamer startup failure, asynchronous error
messages, end-of-stream without a frame, cancellation and the bounded timeout.
Errors report a category rather than raw pipeline debug text. Capture still
invalidates the prior observation before acquisition, tears down the pipeline
in its existing `finally`, and performs no input or automatic retry on failure.

Four tests using real local GStreamer 1.26.2 pass: frame delivery, empty EOS,
failed source startup and pre-cancellation. Tests explicitly skip when the
GStreamer introspection or test plugins are unavailable. This improves diagnosis;
it is not a fix for the intermittent PipeWire failure. The new helper and portal
change are not yet packaged or exercised against the installed Wayland executor.

### Debian candidate 6 installed for capture regression

Built `outputs/debian-cross-platform-6` and upgraded the disposable Plasma Wayland
VM successfully. The installed runtime contains `services/desktop/capture_stream.py`.
Runtime package SHA-256 is
`81a68741fd39f9a8fc79125252402175931977b599f2851c1cb1d17e338be6f7`
(54819144 bytes); desktop package SHA-256 is
`11a7492d4208024190404d5a55d29f6d0175402a3944f45218f2a42dd999dd05`
(4240 bytes). Build/install evidence: `outputs/cross-platform/linux-package-6.log`
and `linux-vm-install-6.log`. Previous VM evidence is preserved before the new run.
Installed capture/Stop acceptance is running separately; installation alone does
not close the intermittent capture gate.

Candidate 6's running Wayland proof completed ten consecutive 1280×800 captures
with fresh tokens (2.459–3.074 seconds each), plus consent denial, stopping pending
consent and the owner/text/replay/point/window guards. File-save and active-input
Stop checks are still running; no completed suite result is claimed yet.

The local real-GStreamer tests now additionally cover asynchronous stream errors,
timeout without a frame and cancellation during acquisition. All seven pass.
These cover the helper's failure paths, not the unresolved intermittent PipeWire
problem in an installed desktop session.

### Debian candidate 6: installed Wayland capture and Stop regression passed

The running acceptance process exited successfully. In addition to the ten
consecutive captures and guards above, the installed executor saved the exact
expected Kate file. An actual Stop click interrupted typing after 14 characters;
the saved partial content stayed unchanged and further input with the old token
was refused. The run used Debian Plasma Wayland at scale 1, KWin 6.3.6 and portal
KDE 6.3.5, with `candidateSource: false`.

Evidence is retained under `outputs/desktop-vm-cross-platform4/` as
`desktop-control-acceptance-installed6.json`, `capture-reliability-installed6.json`
and `desktop-executor-installed6.log`, alongside
`outputs/cross-platform/linux-installed6-capture.log`. The executor log contains
no `CRITICAL`, `ERROR` or `gst_buffer_peek_memory` occurrences. The previous
intermittent failure remains unresolved; this run qualifies the diagnostic helper
on this installed configuration rather than proving capture reliability across
all sessions or distributions.

### Current source regression suites

TypeScript checking and all 90 root Node tests pass. All five browser prompt tests
pass separately. The initial system-Python native run lacked QtTest and failed;
the development venv run then exposed two shortcut-fixture failures because its
Python path contains spaces. The fixture now uses a quoted shell launcher rather
than an invalid interpreter shebang. The complete venv native suite passes:
223 tests in 24.716 seconds. Logs are retained as
`outputs/cross-platform/current-node-regression.log`,
`current-browser-prompt-regression.log` and
`current-native-venv-regression-fixed.log`, with both prior failures retained.

CI's Debian dependency setup now includes GStreamer introspection and base plugins
so the real capture-stream tests run there rather than skipping for missing
dependencies. That workflow edit has not been executed remotely. These source
suite results do not replace installed platform acceptance or close public
distribution gates.

### Debian candidate 6: clean runtime-only acceptance passed; desktop run pending

The clean-container package proof verified artifact hashes and installed the
runtime as an ordinary-user test environment before adding Qt or system Node.
It passed bundled Node startup, file tools, shared prompts through the native
host, restart preserving history without replay, Stop, image read/resize and idle
maintenance with data backup. The result explicitly reports `systemNodeAbsent`
and `qtAbsent`. Evidence: `outputs/cross-platform/linux-package-proof-6.log`.
The same container is still installing desktop dependencies for its remaining
GUI, shortcut and removal checks; do not treat this as a completed package suite.

A remaining Debian package description was renamed in source from “Augmentor
Linux desktop application” to “Augmentor Agent Desktop application.” Legacy
workspace directories remain compatibility paths. This description-only change
is not included in candidate 6; its builder syntax check passes.

### Debian candidate 6: clean package suite completed

The same clean-container process exited successfully and its disposable container
was removed. Installed first-run UI verified a tool-free connection check,
rechecking edited settings, private saved configuration, explicit model selection,
a real file task and reopening without replay. The X11 shortcut fixture verified
launch, hide, restoring the same window, service restart and removing the owned
shortcut during maintenance. Package removal preserved fixture user data and
removed the owned native-host registration. Full evidence remains in
`outputs/cross-platform/linux-package-proof-6.log`.

An additional ordinary-user check imported the installed capture helper and
received a synthetic GStreamer frame, confirming the installed dependencies.
Evidence: `outputs/cross-platform/linux-installed6-clean-capture-dependencies.log`.
This synthetic check is not desktop capture; real Wayland evidence is recorded
separately above. The clean suite does not establish other distributions, sessions
or macOS behavior, and does not close the intermittent capture issue.

### macOS Desktop candidate 12: installed DSH acceptance passed

The real DSH 0.1.5-rc.1 fixture passed using candidate 12's installed Python,
adapter and shared service with Cocoa dialogs. It checked installation/save,
profile preservation, refusal to overwrite customized presets, saved chats,
interaction lease claim/release, approval rejection/allow-once/cancellation,
question answers returned to the model, and the browser-role OS-command guard.
Exact-prefix child continuation and refusal to replay a lost acknowledgement
after real child creation passed. The fixture made 12 deterministic model requests.

Evidence: `outputs/cross-platform/mac-installed12-dsh-acceptance.log` and `.json`;
Mac fixture `/private/tmp/augmentor-dsh-setup-y14w289e`. Strict deep signature
verification passed afterward (`mac-installed12-post-dsh-signature.log`). These
checks do not certify external models, additional DSH plugins, Model Picker
curation in this run, or macOS capture/input permissions.

### Desktop candidate 12: Model Picker adapter qualification

Staged local Model Picker Augmented 1.1.2 in a separate Mac test directory with
schemastery 3.18.0 and React 18.3.1, using an isolated DSH profile. The installed
desktop adapter successfully pinned a fixture model and read back pinned/hidden
curation through the plugin's settings namespace. Checked setup, preserved
profile, saved chats and browser-role OS-command refusal also passed; three
deterministic model requests were observed. This is adapter/settings integration
evidence, not pointer-driven picker UI or provider-discovery acceptance.

Evidence: `outputs/cross-platform/mac-installed12-model-picker.log` and `.json`;
fixture `/private/tmp/augmentor-dsh-setup-5eoqkwr7`. The fixture dependency lock and
local plugin source hashes are retained in
`mac-model-picker-fixture-package-lock.json` and
`model-picker-1.1.2-source-hashes.txt`. Normal DSH profiles were not changed.

### Native picker visibility fix in source

UI inspection found that hidden models were excluded from pinned rows but could
reappear under their provider. The native picker now filters hidden models from
provider/search results and automatic fallback selection. Explicit existing
selections remain preserved; hiding a model does not silently change a chat's
model. Shared picker labels no longer incorrectly name Pi when DSH is selected.

The window regression suite passes, followed by targeted visibility and selection
preservation checks after the fallback adjustment. This closes a source UI defect
that the prior adapter-only Model Picker proof did not exercise. The fix still
requires installed macOS/Linux picker acceptance and is not in current artifacts.

### Desktop candidate 13: installed Cocoa picker fix verified

The new picker UI fixture exposed `hidden-fixture` in installed candidate 12's
provider rows. Its initial assertion also excluded unrelated DSH built-in models;
the fixture was corrected to scope the assertion to the fixture provider. The
failure output is retained in `mac-installed12-picker-ui-before-fix.log`.

Candidate 13 installed with ZIP SHA-256
`01f9bc7d06d6329f4d2b41a8f74eee1cf10631cf997209025c3096d238eb197b`
(268735890 bytes), preserving candidate 12 as
`Augmentor Agent Desktop Preview.before-0a0a0759edb24626a011200f60091f4b.app`.
The corrected source proof uses installed candidate 13's adapter and ModelPicker.
It verifies the hidden model is absent from provider rows and search, then uses
a Qt mouse click to select the visible pinned model. Three deterministic DSH
model requests also complete the setup/preset guard checks.

Evidence: `outputs/cross-platform/mac-installed13-picker-ui.log` and `.json`;
fixture `/private/tmp/augmentor-dsh-setup-p4zs74lq`. This closes the demonstrated
native picker defect on macOS. Linux installed acceptance and Model Picker's
provider-discovery behavior remain unqualified. Candidate 13's bundled proof
predates the fixture-provider assertion correction; the external source proof
was used without modifying the signed application.

### Debian candidate 7 built; installed DSH picker run started

Candidate 7 contains the native picker visibility fix and updated package name.
Runtime SHA-256: `9c0d1ed13c5e3a23e22312da188908b77d6ad9021de5fcfc1f8ec5815172aa96`
(54811864 bytes). Desktop SHA-256:
`81709e971efb74600200819c59773f0fc436c211a13111b7601299b11539be42`
(4236 bytes). Artifacts are in `outputs/debian-cross-platform-7`.

The clean DSH container runner now accepts `AUGMENTOR_DSH_PICKER_ROOT`, mounting
the supplied plugin read-only and enabling the picker UI proof. An installed
candidate 7 run is active with pinned DSH 0.1.5-rc.1 and local Model Picker 1.1.2.
It uses Qt's offscreen platform, so any passing result establishes installed Qt
interaction behavior rather than real compositor/input delivery. Evidence will
be in `outputs/cross-platform/linux-installed7-dsh-picker.log`; no completed
result is claimed yet. The Wayland VM remains on candidate 6.

The candidate 7 clean DSH process completed successfully. Installed Qt picker
visibility/search/selection checks passed alongside setup preservation, native
approval/question decisions, exact child continuation and no replay after a lost
acknowledgement. Twelve deterministic model requests were observed. This uses
Qt offscreen and does not establish compositor input delivery.

Inspection then found the same hidden-model provider-row omission in the browser
picker. Source filtering is corrected, and the DSH browser proof now checks hidden
rows, hidden-model search and a pointer-selected visible model when Model Picker
is enabled. Syntax checks pass; this browser change is not yet packaged or
accepted. Do not transfer the native picker result to the browser implementation.

### macOS companion 7: browser picker fix accepted

The headed Chrome proof reproduced the browser hidden-model defect in installed
companion 6 at the explicit hidden-row assertion. Failure evidence is retained in
`mac-companion-installed6-picker-before-fix.log`. Companion 7 then passed the same
test with Model Picker 1.1.2 enabled: hidden model absent from provider and search
rows, visible model selected by pointer, and full DSH page/Branch/Edit checks.
Eight deterministic model requests were observed through the installed companion;
the source adapter remains explicit setup/history instrumentation.

Companion 7 ZIP SHA-256:
`3fbefeb163a66f820313ef4ef4b9f0c38b6f2662ee70df52b7d1f9e94c56a313`
(129074183 bytes). Previous companion 6 is preserved as
`Augmentor Agent Browser Companion Preview.before-eedc0bb1b6b64bb4a5ed750d932d1df5.app`.
Evidence: `outputs/cross-platform/mac-companion-installed7-picker-ui.log` and
`.json`; fixture `/private/tmp/augmentor-dsh-setup-5c0v3rza` on the Mac.
The general JSON result does not carry a separate picker flag; the supplied
Model Picker environment enabled the assertions in the retained proof source.
Desktop 13 and Debian 7 predate this browser fix and still need matching updates.

### Matching picker fixes packaged: Desktop 14 and Debian 8

Both builds completed. Desktop 14 ZIP SHA-256 is
`abd0c790f6ed349fbca355f9de7cfdea2e25edcbb3ea90ae641f13f3a9094569`
(268737586 bytes). It is installed at the desktop Preview location; its previous
bundle backup is recorded in `outputs/cross-platform/mac-install-14.log`.
Debian 8 runtime SHA-256 is
`12a8f2b383181095d13f13c21d057d31426ea93f2b767d6412833fccd4c59a88`
(54815264 bytes); desktop SHA-256 remains
`81709e971efb74600200819c59773f0fc436c211a13111b7601299b11539be42`
(4236 bytes).

The browser and native picker source bytes match the packaged Debian files and
installed Mac files. Evidence: `linux-package8-picker-content.json` and
`mac-installed14-picker-content.log` under `outputs/cross-platform`. This content
check is not a replacement for new-artifact acceptance. Picker proof JSON now
records UI coverage explicitly, with a separate native adapter flag; prior results
remain unchanged. Companion 7 remains installed, and the Wayland VM remains on
Debian 6. Full release qualification is still incomplete.

### Desktop 14: combined installed DSH and picker acceptance passed

The installed Cocoa run passed Model Picker adapter and UI checks together with
DSH setup/save, preserved profile, saved chats, scoped interaction lifecycle,
approval rejection/allow-once/cancellation, question replies, browser-role command
guard, exact child continuation and no replay after a lost acknowledgement.
The fixture made 12 deterministic model requests and reports both
`modelPickerAdapter: true` and `modelPickerUi: true`.

Evidence: `outputs/cross-platform/mac-installed14-dsh-picker.log` and `.json`;
fixture `/private/tmp/augmentor-dsh-setup-064wx0yc`. Strict deep signature check
passed afterward (`mac-installed14-post-dsh-signature.log`). This is current
desktop-candidate evidence for those workflows, not qualification of additional
plugins, model-provider discovery, live external models or desktop permissions.

### macOS application-content inventory added to builder

Future Mac builds will include `application-inventory.json` inside the sealed
bundle and its SHA-256 in the external artifact report. It records hashes/sizes
for shipped application code and documents and records symlink targets without
traversing them. Bundled runtimes, generated native binaries and third-party
notices remain outside this inventory's scope and need their existing separate
provenance checks. This is not a claim about a clean source commit.

The inventory test verifies content-change detection, exact file hashes and
non-traversal of linked runtime directories. It passes, as does builder syntax
validation. Current installed artifacts predate the inventory; a new build and
archive verification are required before relying on this metadata in a release.

### Companion 8: application inventory verified in actual archive

Companion 8 built with ZIP SHA-256
`8ff1f6aa8aea36b7832802a13aa37399f17e3c558e2f543ff4f35fe2b9120d0c`
(129093085 bytes). Its application inventory SHA-256 is
`bebd504151cf926616c92c7ed0e929941d3a61bb3b0f2fa6fb3c5f8bbce36342`.
The new `verify-macos-application-inventory.py` verified all 326 listed entries
directly against the ZIP, plus archive and inventory hashes. Evidence:
`outputs/cross-platform/mac-companion8-inventory-verification.log`.

Verifier tests pass for a valid archive, altered content despite an updated ZIP
checksum, and a refused parent-relative inventory path. The verifier does not
claim signature, notarization, runtime acceptance or complete source provenance.
Companion 8 is built but not installed; companion 7 remains the installed preview.
The verifier was authored after staging and is external to this candidate.

### Companion 8 installed; disposable recovery passed

Companion 8 is now installed, preserving companion 7 as
`Augmentor Agent Browser Companion Preview.before-25b390e18bf24080b9b60d263fa9f029.app`.
Its packaged recovery tools passed on a disposable signed copy: held shared-lock
removal refusal, uninstall, repeat restore, registration restoration, retained
fixture data and unchanged desktop shortcut registration. This uses a held lock,
not an active browser task or injected crash. The original installed bundle was
preserved throughout.

Evidence: `outputs/cross-platform/mac-companion-install-8.log` and
`mac-companion-installed8-lifecycle.log`; fixture
`/tmp/augmentor-companion-lifecycle-2it37aq1`, retained final recovery receipt
`~/.Trash/Augmentor-uninstall-t7mpw_rj/receipt.json` on the Mac. Fresh Pi browser
acceptance is running separately and is not yet claimed complete.

### Companion 8: clipboard-expansion failure reproduced, rerun passed

Fresh Pi browser acceptance failed at clipboard prompt expansion. The diagnostic
reported document focus true, active element without an ID, the input still
containing `/proof-renamed`, one completion button, and the clipboard still equal
to the fixture. Thus the earlier unchanged-menu refresh fix does not close the
intermittent failure. Evidence: `mac-companion-installed8-browser.log`.

Added bounded pointer/focus event diagnostics to the source proof, recording
element tags/IDs/classes and coordinates rather than clipboard contents. The
instrumented rerun passed fresh setup and the full Pi workflow, including forced
refresh during click, with two setup checks and eight model requests. Evidence:
`mac-companion-installed8-browser-pointer.log` and `.json`; fixture
`/private/tmp/augmentor-browser-proof-_pxmoh_r`. The passing rerun did not capture
the failed pointer sequence. Keep the failure open; do not replace its evidence
with the passing run or claim the cause is confirmed.

### Clipboard failure traced to a hidden target in the acceptance driver

The next instrumented failure captured mouse-down/up/click on `HEADER` at `(0,0)`,
followed by composer blur. The completion menu was hidden. The proof waited only
for a button node, but hidden menus retain their buttons and return a zero-sized
bounding rectangle. Thus this captured failure is a test-driver click-target
race, not failed clipboard reading. Evidence:
`outputs/cross-platform/mac-companion8-pointer-attempt2.log`.

The proof now waits for an unhidden, positive-sized, hit-testable completion
button before sending pointer events. It still forces refresh between press and
release and verifies clipboard expansion. The corrected test passed fresh Pi
setup and all browser checks through unchanged installed companion 8, with two
setup checks and eight model requests. Evidence:
`mac-companion8-pointer-target-fixed.log` and `.json`. Earlier uninstrumented
timeouts are consistent with this race but cannot be attributed with the same
certainty. No product code was changed for this driver correction.

### Companion 8: interrupted restoration recovered

The lifecycle proof now optionally terminates its restore subprocess immediately
after the app bundle's real rename, before browser registration restoration.
With `AUGMENTOR_PROOF_INTERRUPT_RESTORE=1`, the installed companion 8 recovery
code recovered that partial state, passed a repeated restore, verified the signed
bundle and restored matching registration and fixture data. The desktop shortcut
registration and original installed companion remained unchanged. The disposable
copy was uninstalled again, retaining its final receipt.

Evidence: `outputs/cross-platform/mac-companion-installed8-interrupted-restore.log`;
fixture `/tmp/augmentor-companion-lifecycle-a8zezi87`, final receipt
`~/.Trash/Augmentor-uninstall-wakjtl3u/receipt.json` on the Mac. This establishes
process-exit recovery at the tested boundary, not power-loss durability or every
possible interruption. The external proof changed; the installed product did not.

### Companion 8: packaged native host holds the removal lease

The lifecycle proof's `AUGMENTOR_PROOF_REAL_HOST_LEASE=1` mode launches the
disposable signed bundle's actual `augmentor-browser-host` executable and exchanges
framed protocol handshakes. Removal was refused while that host ran; the same
process stayed alive and answered a second handshake afterward. Closing its stdin
released it, after which uninstall and interrupted/repeated restore passed.

This proves lease inheritance across the packaged launcher/Node exec path, beyond
the earlier synthetic held-lock test. It does not represent an active model turn
or a browser's own connection. The desktop shortcut registration, fixture data
and original installed companion remained preserved. Evidence:
`outputs/cross-platform/mac-companion8-real-host-lease.log`; fixture
`/tmp/augmentor-companion-lifecycle-8cs3zrpy`, retained final receipt
`~/.Trash/Augmentor-uninstall-vbjdeaa_/receipt.json` on the Mac.

### Native source archive content verification

All seven staged PySide/Qt source archives were rechecked against the clean,
pinned upstream Git checkouts, including initialized recursive submodules.
The archive receipts also match the current native source manifest identities.
A total of 85280 entries passed Git blob or declared export-transformation
comparison; missing tracked paths were accepted only under upstream export-ignore
rules. Per-archive counts, commits and SHA-256 values are recorded in
`outputs/cross-platform/native-source-archive-verification.json`; detailed
transformation/omission lists remain in `outputs/native-sources/*-verification.json`.

This closes the staged archive content check, not the native dependency release
gate. Matching wheel build provenance/configuration, complete embedded-source
coverage, replacement/relinking instructions and public source hosting remain
unverified. `release/native-sources.json` still correctly marks completeness and
binary build provenance as false.

### Debian candidate 8 installed DSH acceptance

A fresh disposable Debian container installed the candidate 8 runtime and desktop
packages after verifying their manifest hashes. The installed service and adapter
passed checked setup/save with profile preservation, saved chats, Model Picker
1.1.2 curation and actual Qt provider/search visibility and selection, interaction
leases, rejection/allow-once/cancellation, question reply, browser OS-tool refusal,
exact-prefix fork/continuation and no replay following a lost acknowledgement.
The pinned DSH 0.1.5-rc.1 host made twelve deterministic local-model requests.

Evidence: `outputs/cross-platform/linux-installed8-dsh-picker.log` and the
companion JSON report, which records the tested package manifest. Qt used its
offscreen backend; this is not physical compositor/input acceptance. The
container exited successfully and was automatically removed. Other current
artifact checks and the platform/publication gates remain open.

### Debian candidate 8 clean package lifecycle acceptance

The full clean-container package proof exited successfully for candidate 8 after
checking artifact hashes. Runtime-only installation passed with no system Node
or Qt: installed file tools, shared prompts through native messaging, history
preservation without replay, Stop, SDK image resizing, and idle maintenance
backup/service shutdown. Desktop installation then passed first-run model setup
and file task in an isolated X11 session. KGlobalAccel keyboard delivery launched,
hid and restored the same window, survived shortcut service restart, and removed
the shortcut during maintenance. Package removal preserved user data and removed
the owned native-host registration.

Evidence: `outputs/cross-platform/linux-package-proof-8.log` and its JSON report
with the tested artifact manifest and emitted structured checks. The temporary
container was removed. This does not qualify physical desktop input, additional
distros, or the outstanding intermittent Wayland capture issue.

### Linux DSH priority: expanded desktop preset

The reference Linux preset exposed materially more capabilities than the
product preset. `release/dsh/desktop-capabilities.json` now carries forward
eleven entries, preserving isolated planning, compaction and workflow realms,
plus filesystem search, jobs, skills, goals, to-dos and web search. Source setup
adds these to the desktop preset only. Upstream MIT attribution is retained
in `release/dsh/desktop-capabilities.LICENSE` and the fixture README.

The expanded source integration passed the actual DSH setup/approval/question/
exact-fork/no-replay fixture (twelve model requests), then a focused catalog
check confirmed all nineteen required additional tool names reach the model.
Evidence: `outputs/cross-platform/linux-expanded-dsh-preset.log`,
`linux-expanded-dsh-catalog.log` and `linux-expanded-dsh-tools.json`. The proof
now asserts those required names. This is source/offscreen evidence, not yet a
new installed package or execution qualification of each added workflow.

The composed reference host configuration is recorded, with all configuration
values omitted, in `linux-dsh-effective-composition.json`. Conditional gates
remain marked as expressions, not assumed enabled. Full host plugin parity
remains open. Existing customized live presets were not overwritten.

### Debian candidate 10 expanded DSH installed acceptance

Candidate 9 was rejected: its installed setup failed because the Debian builder
omitted the new desktop capability data file. The builder now explicitly stages
that JSON and its upstream MIT license. Candidate 10 archive inspection confirms
byte-for-byte agreement for both files and the invalid-frame capture guard.

Candidate 10 then passed clean installed DSH 0.1.5-rc.1 acceptance with Model
Picker 1.1.2, nineteen required additional model-facing tool names, profile
preservation, approvals/questions, exact fork and no replay after lost
acknowledgement. Twelve deterministic model requests; Qt offscreen. Evidence:
`outputs/cross-platform/linux-installed10-dsh-picker.log` and its JSON report;
`linux-package10-changed-content.json` binds the changed archive contents.
Candidate 9 failure evidence remains retained.

New source preferences now default to DSH for fresh profiles and invalid/retired
choices. A focused read-only preference check confirmed saved DSH/Pi choices and
file bytes remain preserved. The OpenCode retirement message now names DSH.
These preference changes are not in candidate 10. The macOS builder needs the
same capability-file staging when macOS work resumes. Individual added workflow
execution, host-plugin parity and Linux capture reliability remain open.

### Linux DSH first launch and legacy helper parity

Unconfigured DSH now offers setup once on its first connection result, including
failure; saved conversations and configured connections do not reopen setup on
disconnect. All 24 window tests pass (`linux-dsh-first-launch-window.log`).

The working Linux integration's `linux_system_profile`, `linux_browser_open`
and bounded read-only `linux_desktop_observe` helpers were carried forward with
MIT headers into `services/desktop/linux-support` and the DSH adapter. The
browser helper now resolves the new native app lock (`augmentor-linux-pi.lock`).
These helpers register only on Linux. A direct adapter check verified actual
MX/KDE/Wayland profiling, non-HTTP launch rejection and pre-cancelled launch
refusal. A real source DSH run confirmed all three names reach the model,
with setup and browser OS-tool guard still passing (three fixture requests).
Evidence: `outputs/cross-platform/linux-dsh-support-tools.log`.

No visible browser launch or live accessibility tree was qualified in that
check. Those remain required. The changes in this entry are source-only and
not part of candidate 10. Host-plugin parity and capture reliability stay open.

### Live Linux helper acceptance and session routing fix

Accessibility observation now resolves the verified native app graphical
environment before importing AT-SPI, clearing stale inherited graphical/AT-SPI
variables in its disposable helper process. With the caller graphical variables
removed, a real host check listed 34 AT-SPI applications and observed the verified
native Augmentor process with 120 bounded nodes (truncated as intended). Only
counts/result metadata were retained, not application text. Evidence:
`outputs/cross-platform/linux-accessibility-session-recovery.json` and
`linux-accessibility-native-tree.json`.

The actual visible-browser helper then dispatched one unique localhost page to
the user Chromium. A subsequent bounded accessibility observation found its
unique page title, independently verifying the launch result. No headless
browser was used; dispatch itself still correctly reports `verified:false`.
Evidence: `outputs/cross-platform/linux-visible-browser-open.json`. The temporary
HTTP server was stopped; one local verification tab remains in Chromium.
These are source helper checks on the actual MX/KDE/Wayland host; candidate 10
does not contain the helpers or first-launch changes. The capture timeout and
remaining external DSH plugin workflows remain separate release gates.

### DSH-only VM capture investigation

Revalidated the live disposable VM and ran the DSH-only SDK desktop task/Stop
fixture with PipeWire source/pool diagnostics. The task passed actual model
screenshot, external editor/file result and sharing release. The Stop case
failed before typing: `The focused control is not accessible` was correctly
returned by the executor. Consequently Stop-during-typing was not qualified.
The log contains no GStreamer critical or empty-buffer errors; successful
negotiations wrapped MemFd buffers. The historical capture failure remains
unresolved, not disproved by this run. The next Stop check must establish
accessible editor focus before input. No pipeline settings were changed.

Evidence: `outputs/cross-platform/linux-dsh-capture-investigation.log` and JSON;
full temporary fixture `/tmp/augmentor-vm-sdk-y_66fqao`. Guest remains candidate
6; this is diagnostic evidence, not current-artifact acceptance. Previous VM
summary was preserved before the run. Upstream source inspected for the buffer
path: [PipeWire 1.4.2 pool](https://github.com/PipeWire/pipewire/blob/1.4.2/src/gst/gstpipewirepool.c).

### Accessible-editor precondition and live host plugin inventory

The DSH-only VM proof now waits for the newly opened editor's initial fixture
text through its focused AT-SPI text interface before starting each model task.
Tool failure during the Stop wait is surfaced directly rather than misreported
as a generic typing timeout. With this independent readiness check, both full
DSH desktop task and Stop-during-typing cases passed, including real screenshot,
external result and sharing release. No GStreamer critical/empty-buffer errors.
Evidence: `outputs/cross-platform/linux-dsh-accessible-focus-proof.log` and JSON;
fixture `/tmp/augmentor-vm-sdk-8vx0j_47`. This does not prove the previous failure
was solely startup timing or resolve the historical capture issue. Guest remains
candidate 6, so current-artifact verification is still needed.

The actual running DSH `pluginInventory/list` API provided 196 host entries
and 14 preset inventories without changing the host. Twelve active reference
plugin instances were identified: context, wiki tools/skills, Model Picker,
prompt library, adaptive reasoning, Metafolder, free web search and four MCP
instances (Comfy, Playwright, Blender, Unreal). Eleven versions resolved from
installed package manifests; the unresolved one remains explicit. Evidence:
`linux-live-dsh-plugin-inventory.json` and `linux-dsh-required-host-plugins.json`
in `outputs/cross-platform`. Runtime activity is not workflow qualification.

### Preserve a working host prompt-library plugin

Setup now reads the live DSH inventory and verifies the prompt-library list
endpoint before reusing an independently installed active prompt library. It
rechecks that identity before installation, preserves the existing profile entry,
and omits its duplicate product prompt entry. Multiple active libraries and
incompatible responses fail explicitly. Product-owned entries are excluded from
external-reuse detection. Other custom Augmentor migration refusals remain.

Four focused tests passed. Real isolated source DSH checks passed both fresh
installation and an existing active prompt plugin. The latter fixture patch was
inspected: its original entry occurs once and no product prompt duplicate was
added. Evidence: `outputs/cross-platform/linux-dsh-prompt-reuse-unit.log`,
`linux-dsh-prompt-reuse-fresh.log`, `linux-dsh-prompt-reuse-existing.log` and JSON.
This is source evidence; the live user configuration was not modified.

### Debian candidate 11 consolidated DSH-first build

Candidate 11 includes DSH-first preferences, one-time unconfigured-DSH setup,
Linux system/browser/accessibility helpers with session routing, expanded
desktop capability data and existing-prompt-library reuse. Eight changed source
files were compared byte-for-byte against archive members; evidence in
`outputs/cross-platform/linux-package11-changed-content.json`.

Clean installed DSH/Model Picker acceptance passed: checked setup/profile
preservation, expanded tool catalog (including all three restored Linux helpers),
model curation and Qt selection, saved chats, approvals/questions, exact fork,
browser OS-tool refusal and lost-ack no replay. Twelve fixture model requests;
Qt offscreen. The temporary container exited successfully and was removed.
Evidence: `outputs/cross-platform/linux-installed11-dsh-picker.log` and JSON.
This does not replace current-artifact Wayland qualification, the historical
intermittent capture investigation, full host-plugin workflow parity, or final
release publication requirements. The source identity remains dirty.

### Candidate 11 installed Wayland task pass; Stop still unqualified

Candidate 11 was installed into the marked disposable VM with no live executor
at upgrade time. Five installed files, including capture guard, setup and
preferences, match source SHA-256 values (`linux-vm-installed11-content.json`).
Install log: `outputs/cross-platform/linux-vm-install11.log`.

The DSH fixture passed the full task against the installed backend: real model
screenshot, external editor/file result, sharing release. Stop failed before
typing because accessible focus was unavailable, despite readiness before
consent. No GStreamer critical/empty-buffer errors. Evidence:
`linux-installed11-wayland-dsh.log`, fixture `/tmp/augmentor-vm-sdk-xqja93si`.

The proof now accepts `--case stop` to avoid rerunning an already-passing task,
and uses snapshot/click/snapshot before typing in that case. The focused rerun
still returned inaccessible focus before typing (`linux-installed11-wayland-stop-focus.log`).
Therefore the consent-focus explanation remains unproven. Do not count Stop as
qualified for candidate 11. Next diagnosis must distinguish no focused control
from bounded/incomplete traversal or AT-SPI errors. Product input guards remain
unchanged, and the VM is now candidate 11 rather than candidate 6.

### Diagnosed bounded focus traversal timeout; staged fix passes Stop

An opt-in VM wrapper traces only focus-return counters, exception type and
elapsed time; it records no node text or names and does not modify installed
files. Candidate 11 returned no focus after 127 nodes with 16 pending, despite
finding nine focused entries, at 3.178 seconds. This identifies its three-second
traversal cutoff as a concrete cause of the generic inaccessible-focus refusal.
Evidence: `linux-installed11-focus-diagnostic.log`; full fixture
`/tmp/augmentor-vm-sdk-ztwjuhrb`. Trace overhead may affect timings; earlier
uninstrumented runs also failed, so do not infer an exact latency distribution.

Source traversal now has a six-second bound, checks cancellation inside the
loop, and reports an incomplete inspection distinctly. It still rejects every
partial traversal and keeps node/focus/target guards. The updated services were
staged at `/home/beta/augmentor-focus-candidate-12`, leaving installed candidate
11 intact. The DSH Stop-only proof passed actual screenshot, partial typing,
cancellation, unchanged result afterward and sharing release. All traced
traversals completed (146 nodes, zero pending), several around 3.4 seconds.
Evidence in `outputs/cross-platform`: `linux-staged-focus-budget-stop.log`,
matching JSON and `linux-staged-focus-budget-diagnostics.json`. The test runner
now supports an explicit staged `--guest-root`, mutually exclusive with
`--installed`, avoiding repeated package builds for diagnosis.

This fix is staged/source evidence, not a new released package. The historical
PipeWire capture failure remains a separate unresolved issue.

### Staged six-second focus bound: repeated capture and backend acceptance

The direct backend proof now accepts an explicit staged guest root and records
that root in capture evidence. Against `/home/beta/augmentor-focus-candidate-12`,
all ten successive 1280×800 captures passed with fresh tokens, taking 5.183–5.99
seconds in the software-emulated VM. The same run passed consent denial, Stop
during pending consent, foreign-owner/unsupported-text/replay/outside-target/
changed-window refusals, exact native Wayland Kate Save As result and independent
Stop with partial text remaining unchanged.

Evidence in `outputs/cross-platform`: `linux-staged-focus-capture10.log` and JSON,
`linux-staged-focus-backend.json`, `linux-staged-focus-executor.log`. Previous VM
evidence was retained before the run. No claim of universal capture reliability
follows from ten passing observations; the historical intermittent PipeWire
error remains unresolved. This is staged source/backend evidence, not a Pi SDK
qualification or an installed release with the new focus bound.

### Candidate 12 packages verified focus fix; desktop-only review mode

Debian candidate 12 was built and its archived `services/desktop/portal.py`
compared byte-for-byte with the staged source that passed DSH Stop and the
ten-capture/full backend run. Evidence: `outputs/cross-platform/linux-package-build-12.log`
and `linux-package12-focus-content.json`. Candidate 11 remains installed in the
VM; candidate 12 has not yet received installed-artifact acceptance.

The artifact reviewer now permits omission of `--browser` for a desktop-only
distribution; it reports extension review as null, not passed. Package hashes,
contents, binary notices and clean-source checks are unchanged. A direct CLI
check confirms candidate 12 is still rejected because its source is dirty.
No public-release review pass is implied. Source Linux guidance now presents
DSH first and Pi qualification as paused. These documentation/reviewer edits
postdate candidate 12. Public source freeze and applicable release gates remain.


## Linux candidate 12 installed Stop verification

Candidate 12 installs successfully and its installed focus backend hash matches
source. The uninstrumented installed-backend DSH Stop proof passes: model
screenshot, independent editor output, and released screen sharing. Evidence:
`outputs/cross-platform/linux-installed12-wayland-stop.{log,json}`. The proof
uses source-side harness orchestration and the installed VM desktop backend.
The native regression suite passes 232 tests; TypeScript and whitespace checks
pass. Capture reliability, full active-plugin workflow parity, clean source
freeze and public distribution remain open. Pi and macOS qualification stay
paused under the Linux/DSH-first priority.


## Linux candidate 12 existing-plugin acceptance

The disposable Debian proof now forwards the existing-prompt-library fixture
flag through the container and ordinary-user environment. Against installed
candidate 12, that fixture passes the 12-request DSH test: Model Picker Qt
controls, checked save, profile preservation, saved chats, approvals/questions,
exact child continuation and lost-acknowledgement no-replay. Evidence:
`outputs/cross-platform/linux-installed12-existing-prompts.{log,json}`.
The ephemeral container was removed normally; the user DSH profile was untouched.
This is existing-plugin setup compatibility, not all native prompt-editor workflows.


## Linux candidate 12 installed capture and input acceptance

The installed Debian backend passes 30 consecutive fresh captures and the full
Wayland backend proof, including declined/pending consent, target/refusal checks,
actual editor input and visible Stop. Evidence is retained as
`outputs/cross-platform/linux-installed12-capture30.{log,json}`,
`linux-installed12-backend.json`, and `linux-installed12-executor.log`.
This is the Debian 13/KDE Wayland disposable VM, not a claim for all Linux
distributions. Thirty passing observations do not establish the root cause or
resolution of the historical intermittent PipeWire failure. The test executor
exited normally; the reusable VM and original backing image remain preserved.


## Linux candidate 12 custom-compaction compatibility

The installed DSH fixture passes with the reference compaction settings
(threshold 0.5, retainTokens 0, maxTokens 8192; tool-result limits 4096/2048/512)
and expanded desktop capabilities. It also explicitly verifies one existing
prompt entry and no duplicate product prompt entry. All 12 deterministic
model requests, native picker, approvals/questions and exact-fork checks pass.
Evidence: `outputs/cross-platform/linux-installed12-custom-compaction.{log,json}`.
This verifies configuration loading and those workflows, not a forced compaction
at the context threshold. The host profile is unchanged. A proposed additive
merge preserving six existing entries and adding eleven is saved separately in
`outputs/cross-platform/linux-dsh-preset-migration/`, including source/candidate
hashes. Applying that migration and qualifying other active plugins remain open.


## Source checkpoint for the Linux-first candidate

The host `/usr/lib/augmentor` runtime predates candidate 12 and lacks
`adapters/dsh-desktop/linux-support.mjs`; the proposed preset merge remains
unapplied until a compatible runtime upgrade. No running DSH sessions were
reported by the read-only preflight, but that must be rechecked at install time.
The source checkpoint includes the existing cross-platform implementation and
license work, while Linux/DSH is the qualification priority. It is not a public
release or a claim that plugin parity, capture reliability or distribution gates
are complete. Current native/TypeScript evidence and candidate-specific installed
checks are recorded above. The subsequent clean build will carry this checkpoint
identity in its artifact manifest.


## Wiki Tools and Wiki Skills desktop workflow

The source DSH desktop adapter passes a deterministic model workflow using the
installed Wiki Tools 0.14.0 and Wiki Skills 0.2.1 packages with a temporary vault.
The model receives the actual `wiki_query` hot-cache marker and the actual
`wiki-query` skill body. Six requests also cover ordinary desktop setup and
browser OS-tool refusal. Application code matches candidate 13; this run uses
the source adapter, not an installed package. Evidence:
`outputs/cross-platform/linux-dsh-wiki-parity-2.log` and
`linux-dsh-wiki-parity.json`. The first attempt stopped after the deterministic
model mistook an injected skill reminder for the original user request. The
proof driver now recognizes its explicit wiki task across user messages.
No application change was required and the real vault was not accessed.
Write/rename/archive workflows, other host plugins and final installed
reference-host qualification remain open.


## Context and Adaptive Reasoning desktop compatibility

Context 0.48.0 and Adaptive Reasoning 0.2.0 pass alongside Wiki Tools/Skills
in an isolated DSH desktop preset. Context headers and timeline projections are
nonempty. The adaptive decision retains the selected provider/model; its effort
matches both the persisted request header and the actual model HTTP request.
Evidence: `outputs/cross-platform/linux-dsh-context-adaptive-3.log` and
`linux-dsh-context-adaptive.json` (six requests, source adapter). Two earlier
fixture attempts exposed missing reasoning capability declarations in the test
model and the chat-history API omitting plugin bookkeeping events. The fixture
now declares supported efforts and inspects only its own compressed session log
using `zstd`; application code is unchanged. Original native desktop inspection
found no Context/Metafolder/Adaptive native UI controls to port. A separate
read-only live Metafolder API probe returned 404, recorded in
`linux-live-metafolder-read.json`; it does not qualify that plugin persistence.


## Free search and MCP availability

Free Web Search is version 0.1.0 in the shared DSH profiles node_modules.
The source desktop adapter returns live Debian documentation results from
`web_search` to the deterministic model. Evidence:
`outputs/cross-platform/linux-dsh-free-search-2.log` and
`linux-dsh-free-search.json`. The first fixture incorrectly supplied singular
`query`; the corrected fixture uses the documented required `queries` array.
Application code is unchanged.

A read-only MCP SDK initialize/tools-list probe returns 24 tools from Playwright,
26 from Blender and 3 from Unreal. No MCP tools were executed. Comfy fails
initialization, and a separate TCP probe confirms connection refused at the
configured endpoint. Evidence: `linux-mcp-tools-read.json` and
`linux-comfy-connectivity.json`. This is server availability, not complete
desktop workflow qualification. The private temporary copy of connection
configuration was removed after probing; the live profile remains unchanged.


## Live Linux upgrade prerequisite

The host read-only administrator preflight (`sudo -n /usr/bin/true`) reports
that a password is required. No unattended live package upgrade is available.
No application process was stopped and the prepared preset migration remains
unapplied. The reviewed candidate 13 package pair is available locally, but the
user must enter administrator credentials through their normal package manager
for a host upgrade. This blocks that live-host step, not independent release
work. Lifecycle instructions now use 0.2.8 for the current upgrade and label
older rollback examples as historical.


## Locked DSH CI coverage

The Debian CI job now declares `python3-websocket` and `python3-numpy`, required
by the DSH transport and native rendering/tests. It installs DSH through the
existing `release/dsh` npm lock and runs checked setup, existing prompt reuse,
approvals/questions and exact branching with the locally installed CLI. The
locked npm install succeeds and the corresponding 12-request proof passes
locally in `.venv`; evidence is `outputs/cross-platform/linux-ci-dsh-install.log`
and `linux-ci-locked-dsh-proof-venv.log`/`linux-ci-locked-dsh-proof.json`.
The host system Python attempt lacks QtTest; CI already explicitly installs
that Debian package. This is local validation, not a completed GitHub Actions
run. No application code or candidate 13 package content was changed.


## Complete RGB buffer validation

The desktop backend now checks fixed RGB dimensions and the complete padded row
size before passing mapped memory to Qt. A real GStreamer truncated-frame
fixture proves refusal; all 10 capture tests pass. Staged source in the disposable
Debian/KDE Wayland VM passes three fresh captures and the complete backend proof,
including exact saved editor input, visible Stop with 13 partial characters and
no replay. Evidence: `outputs/cross-platform/linux-capture-buffer-layout.log`,
`linux-staged-frame-layout14.log`, `linux-staged-frame-layout14.json` and its
`-captures.json`. This closes incomplete-buffer validation, not the historical
intermittent PipeWire root cause. Candidate 13 does not contain this change.

The host already has preview version 0.2.8 installed. Updated instructions use
`apt install --reinstall` for another candidate with the same preview version.
Public releases must use distinct versions. Live installation still requires
the user administrator step; no host package or preset was changed.


## Candidate 14 evidence applicability audit

Runtime archive hashes show that application code under apps/native, services,
adapters and dist differs from candidate 12 only in `services/desktop/portal.py`
and `services/desktop/capture_stream.py`. Candidate 14 therefore retains the
unchanged DSH adapter/setup/UI implementation covered by installed candidate 12
fixtures. All four maintainer scripts of each Debian package match candidate 8
byte-for-byte. Evidence: `outputs/cross-platform/linux-candidate14-prior-code-comparison.json`
and `linux-candidate14-hook-comparison.json`. The acceptance checklist now records
these specific carry-forwards and the completed clean-build review rather than
stale development-worktree and candidate-8-only entries. The comparison does not
close previously untested feature workflows or the live-host migration.


## Candidate 14 prompt editor workflow

A new proof exercises the real Qt Prompt Library dialog and shared prompt
service using candidate 14 runtime files extracted without system installation.
It verifies save, external-update draft retention, stale-save refusal, reload,
rename preserving identity, and both cancel/confirm delete. DSH is pointed to a
reserved unused loopback port so its ordinary offline controller dispatches UI
work without contacting the user host. Data is isolated. The first fixture used
preview mode, which intentionally has no background controller; the next picked
the other tab's Reload button. The final fixture uses the normal offline window
and scopes buttons to Saved prompts. Application code is unchanged. Evidence:
`outputs/cross-platform/linux-candidate14-prompt-editor-3.log` and
`linux-candidate14-prompt-editor.json`. This is offscreen Qt against extracted
package code with development Qt dependencies, not a whole-machine install or
physical clipboard test. The source proof is added to Debian CI; remote CI
execution remains pending.


## Candidate 14 prompt clipboard selection

The packaged-code editor proof now also selects a saved prompt through the
composer slash menu using a Return key event. Both placeholders receive the
clipboard text, including an embedded literal `[clipboard]` that is not expanded
recursively. The composer submit signal is not emitted; a subsequent clipboard
change does not alter the inserted draft. The existing conflict/rename/delete
checks still pass. Evidence: `outputs/cross-platform/linux-candidate14-prompt-clipboard.{log,json}`.
This uses offscreen Qt clipboard state and extracted candidate 14 files; it does
not replace the independent X11/Wayland external clipboard and browser checks.
Application code is unchanged.


## Remote CI corrections after DSH acceptance

CI run 34946933078 passed the DSH assertions but could not write evidence because
a fresh checkout lacked `outputs`; the proof now creates that directory. Run
34947246638 passed DSH acceptance and reached 234 native tests. It exposed a
missing `qt6-svg-plugins` dependency in CI and the Debian desktop package (the
SVG library alone does not supply its image loader). Both declarations are now
corrected. The host already has that plugin, which explains the earlier local
passes. Candidate 14 does not contain the dependency declaration correction.
The prompt-improvement test now polls for its observable result with a three-
second deadline instead of assuming delivery 60 ms after its 700 ms Qt timer.
Its four targeted tests pass locally. No application animation code changed.
The failed CI evidence is retained in `outputs/cross-platform/ci-34947246638-failed.log`.


## Linux CI lifecycle verification

Run 34948392210 passed the Debian build, locked DSH acceptance, native tests,
prompt editor, browser package, and installed DSH shortcut checks. Lifecycle
comparison failed because 0.2.0 returns redundant streaming deltas that the
current history API suppresses. The proof now compares the persisted journal
byte-for-byte as well as history normalized for that documented display change.
Upgrade, interrupted configuration recovery, rollback, removal and reinstall
passed locally against downloaded CI packages from run 34947658445 and the
frozen 0.2.0 baseline. Prompt preservation and no-model-replay checks remain.
Evidence: `outputs/cross-platform/linux-ci-lifecycle-journal-proof.log`.
The lifecycle script accepts `AUGMENTOR_DEBIAN_ARTIFACTS` to test downloaded
packages directly. Remote CI verification of this correction remains pending.
Live host installation, customized preset migration and the remaining release
acceptance gates remain outstanding; macOS and Pi work remains paused.


## Current Linux CI artifacts and additional DSH acceptance

CI run 34950178526 passed all three jobs: Debian build/234 native tests/DSH
contracts/editor, installed packages and 0.2.0 upgrade/rollback lifecycle, and
browser package acceptance. Clean artifact source is
`9d9ff4a9170c0d608bc442680db9b678609f8f4c` (PR merge for c62c0a3). Downloaded
package/extension hashes and notices pass local review. All 170 application
files under apps/native, adapters, services and dist match candidate 14.
The packages include the corrected SVG plugin dependency. Exact downloaded
packages pass the 12-request installed DSH/Qt fixture with Model Picker,
existing prompts, custom compaction, approvals, questions and no-replay branching.

Extracted current package code also passes native support export using the real
shared service and Qt file chooser: saved contents equal the preview and service
response, mode is 0600, synthetic private values are absent. Hindsight 0.9.2
passes native retention/recall/isolation/export/disable/delete checks against
the same package code. This memory run does not repeat harness tool execution.
The disposable Hindsight service was stopped afterward with its volume retained.

The downloaded extension and companion additionally pass the isolated DSH-only
Chromium fixture with Model Picker, checked connection, role isolation, actual
page navigation/type/click results, completed-tool branching and exact editing
with the parent unchanged (eight deterministic model requests). The fixture
initially reused a stale launch token from its append-only log after restarting
DSH; it now reads only output emitted by the new process and enters the current
launch URL through the connection form. No application code was changed.

Evidence is under `outputs/cross-platform/linux-ci-34950178526-*`, including
`browser-dsh.json`, `browser-dsh-4.log`, `native-support.json`, `memory.json`,
`installed-dsh.log`, `review.json`, and `code-comparison.json`.
`outputs/cross-platform/LINUX-DSH-CHECKPOINT.md` contains the exact live upgrade
commands and outstanding gates. Live administrator installation and preset
migration remain pending; external-plugin workflow and capture/distribution
requirements are not declared complete. macOS and Pi remain paused.


## Packaged Wiki write, rename and archive acceptance

The frozen 34950178526 package code passes the optional
`AUGMENTOR_PROOF_WIKI_MUTATIONS=1` fixture with real Wiki Tools 0.14.0 and
Wiki Skills 0.2.1 in an isolated temporary vault (ten model requests). The model
queries/loads a skill, writes a page from a synthetic raw source, writes an
inbound link, renames the page, and archives the raw source. Independent disk
checks verify preserved page content, updated inbound link, old title absence,
archived source bytes and removal of the source manifest entry. The live vault
is not used. Evidence: `outputs/cross-platform/linux-ci-34950178526-wiki-mutations.{json,log}`.
No application code or frozen release artifact changed. Live reference-host
migration and external MCP/capture/distribution gates remain outstanding.
