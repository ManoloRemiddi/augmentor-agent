<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Verification map

Run from the repository root. The [agent handoff](../docs/AGENT-HANDOFF.md)
records the last qualified implementation and CI URL. The
[workflow](../.github/workflows/validate.yml) specifies clean Debian dependencies,
DSH installation/environment and package acceptance steps.

| Area | Checks | Evidence boundary |
| --- | --- | --- |
| TypeScript / SDK contracts | `npm run check`, `npm run build`, `npm test` | Real Pi SDK with deterministic model fixtures; inspect skipped integrations |
| WebSocket security | `tests/prepare-ws.test.mjs`, `tests/ws-security.test.mjs` (included in `npm test`) | Bounded loopback fragments in both directions; isolated vulnerable-version control and prepared production tree. See [preparation and evidence](../docs/WS-SECURITY-2026-09-24.md) |
| Native UI / service logic | `npm run test:native` | Python and real Qt widgets, usually offscreen; matching QtTest required |
| Windows installer candidates | `scripts/windows-installer-proof.py`, `scripts/windows-inno-proof.py`; native hosted workflows | Uniquely identified disposable installs only; [busy-uninstall findings and proof limits](../docs/WINDOWS-INSTALLER-DECISION.md). A successful feasibility run is not production installer approval. |
| Mac packaging/runtime | `test_macos*.py`, `test_dsh_payload_staging.py`, `scripts/dsh-payload-proof.mjs <staged-dsh-root>` | Real compiled launcher test requires ARM64 Mac; payload proof uses actual FFI/search/shell/PTY. See [Mac evidence](../docs/MACOS-DISTRIBUTION.md); not signing/TCC acceptance. |
| Mac signing policy | `test_macos_signing.py`; `scripts/macos-signing.py <app> --plan` | Policy rejection tests and a real Mac framework seal fixture. [Candidate preparation](../docs/MACOS-RELEASE.md) still requires Developer ID credentials and signed-runtime/public-install acceptance. |
| Shared managed first run | `test_macos_managed_setup.py`, `test_macos_setup_ui.py`, `test_managed_setup_ui.py`, `scripts/macos-managed-setup-proof.py` | Ownership/retry/secret handling, real Qt form with fixture worker, and private real launchd/DSH/model fixture. [Acceptance boundary](../docs/MACOS-MANAGED-SETUP.md) excludes signed end-user install and extra plugins. |
| Browser DOM | `node --test apps/browser/test/*.test.mjs` | DOM/bridge fixtures, not installed Chrome acceptance |
| Browser update reservation | `node --test apps/browser/test/maintenance.test.mjs tests/native-browser-maintenance.test.mjs`; `python3 -m unittest discover -s tests -p test_browser_control.py`; `AUGMENTOR_PROOF_MAINTENANCE=1 python3 scripts/browser-composable-proof.py` | DOM races, private transport and real isolated Chromium documents through the product owner/native host. Inventory, refusal/cancel/renew/expiry, idle commit, observed natural exit and same-build reconnection preserve pages/drafts/conversation. Compiled Windows discovery, relay Job identity and new commit coverage are separate in `windows-browser-host-proof.py`. No global update, Windows GUI, physical audio or live-model claim. |
| Automatic memory | `python3 -m unittest discover -s tests -p test_hindsight_memory.py`; `node --test tests/dual-memory-integration.test.mjs` | Fake HTTP engine plus actual DSH/Pi lifecycle; follow workflow's locked DSH setup |
| Actual memory engine / model | `python3 scripts/proof-controlled-memory.py --help` | Disposable pinned engine, explicit fixture/live modes, archive isolation and bounded real-model completion |
| Maintenance | `python3 -m unittest discover -s tests -p test_lifecycle.py` | Lifetime locks, preserved backups, real temporary memory service shutdown |
| Durable update record | `python3 -m unittest discover -s tests -p test_update_journal.py` | Real private-file writes, independent writer exclusion, child-process crash, lost flush/acknowledgment and preserved recovery state. Native Inno handoff uses it in disposable repair fixtures; no automatic recovery or customer-update claim. |
| Update decisions | `python3 -m unittest discover -s tests -p test_update_coordinator.py` | Real journal/admission with fixture graph and installer. Busy work, failed drain, readiness failure, durable intent and one-shot APPLY. Product backend/UI and recovery remain separate gates. |
| Release delivery and retained source | `python3 -m unittest discover -s tests -p test_update_release.py`; `python3 -m unittest discover -s tests -p test_update_installed_source.py` | Real Ed25519/private files with fixture keys and inert EXE bytes; forward-delivery vs recorded-recovery policy, exact native selection format and held-file ownership. Native publication/readback uses the application-template proof; complete cached-source application remains a separate installed proof. |
| DSH approval / questions / forks | `scripts/dsh-setup-proof.py` with workflow flags | Actual DSH and Qt, deterministic model |
| Native pointer / clipboard | `bash scripts/native-x11-proof.sh` | Isolated X11 desktop, actual input/clipboard |
| Flare workspace / stacking | `AUGMENTOR_UI_PROOF=scripts/flare-workspace-proof.py bash scripts/native-x11-proof.sh` | Isolated X11/KWin, two real native processes; requires wmctrl and xdotool |
| Prompt editor | `python3 scripts/prompt-editor-proof.py` | Qt and actual shared service |
| First run | `AUGMENTOR_UI_PROOF=scripts/first-run-proof.py bash scripts/native-x11-proof.sh` | Actual Qt model form and Pi with fixture provider |
| Installed Debian | `scripts/debian-package-proof.sh`, `scripts/lifecycle-proof.sh` | Container engine and built/checksummed packages required; upgrade/refusal/rollback/removal |
| Packaged browser | Workflow `browser-package` job | Real packaged companion and extension as ordinary user |
| Voice | [Separate voice checks](https://github.com/ManoloRemiddi/resonant-voice/blob/main/docs/AGENT-HANDOFF.md) | Engine/plugin tests distinct from physical microphone and listening acceptance |

Never run container-only package removal scripts directly on the host. Do not
reuse real user state for tests. Logs in ignored `outputs/` are local artifacts;
publish a concise result, exact ref, command and limitations in GitHub rather
than requiring future agents to find those files. Dated verification ledgers
remain valid only for their recorded builds and environments.


Native voice coverage includes `test_voice.py`, `test_voice_hands_free.py`,
`test_voice_input.py` and `test_voice_echo_guard.py`. Use the full discovery
command above so Qt gesture tests are included. The September 19 echo/buffer
change corrected three older gesture methods accidentally placed after the
unittest main guard; earlier suite totals did not include those methods.
Waveform fixtures check echo rejection and an independent signal, not human
listening quality. The [hands-free guide](../docs/HANDS-FREE-IMPLEMENTATION.md)
separates these from the physical capture/speaker probe and deployment scope.


## Restart reliability

`test_recovery.py` and `test_desktop_startup.py` cover saved-chat refusal, explicit
managed-runtime startup, multi-frame legacy-history repair and canonical launchers.
`scripts/proof-recovery.py` uses disposable real runtimes.
`scripts/startup-recovery-proof.py --live` deliberately stops idle installed
services and SIGKILLs the idle desktop to verify supervision; it refuses active
DSH/voice work. See [qualification and limits](../docs/RESTART-RELIABILITY-2026-09-20.md).

Controlled admission/context: `python3 -m unittest discover -s tests -p test_memory_budget.py` and `node --test tests/memory-context.test.mjs`. See [qualification](../docs/CONTROLLED-MEMORY.md).

- Bounded execution and terminal response validity (24 focused cases, including real DSH lifecycle and one isolated hook fixture): `node --test tests/dsh-execution.test.mjs` uses real pinned DSH with fixture HTTP; see [contract](../docs/BOUNDED-EXECUTION-RECOVERY.md).

Action-outcome contracts: `node --test tests/dsh-action-outcomes.test.mjs tests/dsh-execution.test.mjs`. Real DSH fixture coverage includes duplicate mutations, lost acknowledgments, background collection and concluding handoffs after truncation. The complete-container proof verifies the execution adapter is installed once in each preset and its dependent module is shipped.

## Shared personal surfaces · September 24

`test_dsh_status.py` covers stopped runtimes without terminal history and Stop
acknowledgements. `test_browser_voice.py`, `browser-shared-voice.test.mjs` and
`apps/browser/test/voice.test.mjs` cover the common voice transport, cancellation,
deduplication and sidebar gestures. `dsh-boundary`, `dsh-interactions` and
`dsh-exact-fork` verify shared personal aliases while excluding unrelated roles.
`scripts/dsh-setup-proof.py` with the approval/interaction/exact-fork flags runs
real isolated DSH and both presentation transports, using a fixture model.
This does not replace a physical microphone/speaker and loaded-extension trial.

### Mac live desktop chat

`scripts/macos-live-chat-proof.py` is an explicit `--live` check with real provider
usage. Run it with the packaged Mac Python and `--app-root`, a fresh `--out`,
`--instance` and `--marker`. It drives the packaged Qt composer and verifies the
rendered reply. Repeat with the same instance, a new output/marker,
`--previous-marker` and `--submit enter` to verify restoration and Enter submission.
It does not control an existing user's window. See
[Mac readiness evidence](../docs/MACOS-DISTRIBUTION.md#september-26-correction-verify-chat-readiness-and-the-actual-composer).

For the actual native executable, explicitly launch the chosen test instance with
`--ui-test-control`, then pass its owner-only `--native-socket` to the same driver.
The driver verifies the running app root, types into that process's composer and
checks its rendered reply. Normal app launches reject the test operations.
`test_ui_testing.py` verifies default denial, draft/dialog protection and
non-overwriting screenshot output. See the
[installed native acceptance](../docs/MACOS-DISTRIBUTION.md#september-26-follow-up-corrected-primary-mac-app-activated).

### Windows shortcut and executable checks

`test_windows_shortcuts.py` uses actual native registration, OS collision rejection,
failed-save rollback and posted `WM_HOTKEY` messages through Qt. These messages
are not physical keyboard input. `test_windows_supervisor.py` exercises both
settings through the authenticated owner pipe and verifies restart persistence.
The fast Windows desktop workflow runs these on x64 and ARM64. The full runtime
workflow separately builds `Augmentor.exe` and invokes `windows-window-proof.py
--launcher ...` to cover embedded Qt plugins and the shared Appearance control.
Keep source-preview results separate from compiled and installed artifacts.

`windows-managed-setup-proof.py` additionally launches the compiled GUI against
the actual isolated DSH and deterministic model. It uses the shared opt-in UI
commands for Send/Enter, verifies the native process image, closes/reopens the
same named chat and checks rendered history without duplicate submission. Its
test-owned Job bounds fixture cleanup; this is not normal product-wide Quit,
physical keyboard, external provider, browser or audio evidence.

`dsh-maintenance.test.mjs` uses the real pinned DSH services/agents, public gateway
and model-stream lifecycle to exercise reversible admission, retained input
references, active jobs, expiry and cancellation. `dsh_maintenance_proof.py` is
called only with disposable hosts by the Linux/Mac setup and Windows managed
setup proofs. It exercises the actual authenticated product/gateway endpoints,
history preservation and normal CLI shutdown. Its fixture-only observer requires
Node `beforeExit`; exit code zero alone cannot distinguish forced termination.
The Windows proof also refuses preparation during its held deterministic model
turn and verifies history after normal shutdown and explicit restart. None of
these component checks claims global Quit/update coordination or a live provider.

`test_desktop_maintenance.py` exercises actual Qt input suppression/restoration,
draft/dialog refusal, accepted and queued controller work, monitor suspension,
expiry and irreversible committed admission. `windows-window-proof.py` checks
the private protocol across two real preview processes without losing the other
window's draft. The compiled managed-DSH proof uses prepare/commit for each normal
chat-window close. A successful preview alone is not compiled or installed evidence.

Windows shell tests additionally fence queued activations and prove a lost
settings reply cannot make an executing Qt operation appear idle. Supervisor
tests refuse commit with live children, preserve shortcut settings across
prepare/cancel and close an empty native owner after an acknowledged commit.

On Windows, the two-window proof also discovers actual held instance locks,
verifies kernel pipe/process identity and executable/build ownership, refuses a
different build without changing either draft, and observes a normally exited
process through its retained handle. The source and compiled proof exercise the
same discovery client. This snapshot does not claim startup exclusion or a
complete update transaction.

`windows-launcher-lease-proof.py` builds the actual native launchers against a
fresh disposable bootstrap runtime. Copied binaries without Python must refuse
exclusive installation locks and invalid private paths before attempting to load
the runtime. Separate embedded-Python fixture entrypoints verify both launchers
hold the lease until normal exit. The full window proof reuses the negative cases
and tests the assembled desktop's lifetime lease. No existing application root
may be used for the fast probe; it refuses assembled payloads.

`browser-native-drain.test.mjs` runs actual native-messaging parent/bridge
processes against a delayed Unix prompt fixture, closes browser input with work
accepted, and requires a complete response plus an observed Node `beforeExit`.
It checks both parent-only and selected-child cases; native Windows transport
has separate qualification. `browser-shared-voice.test.mjs` additionally holds
worker closure and a submission independently, proving neither a UI close nor
the former two-second kill deadline clears busy state. These controlled voice
tests do not invoke audio/model engines.

The drain probe now invokes each DSH/Pi bridge directly as well, with a held
accepted prompt request and an explicit natural-exit observer. The DSH endpoint
is an isolated unavailable port, so this covers its offline lifecycle, not a
real connected model session. The native compiled-browser proof exercises the
updated Windows wrapper's complete-Job graceful wait against bundled DSH.

`test_windows_startup_fence.py` requires native Windows: concurrent startup
readers block the maintenance writer, the writer blocks new readers/other writers,
and an explicitly inherited duplicate retains exclusion after the coordinator's
normal exit or deliberate crash. The recipient can hold startup exclusion while
the independent final installation file opens with no sharing. No installer
is launched, no product data changes, and this primitive does not prove rollback.
The compiled launcher probe additionally checks the exported readiness release
leaves its lifetime lease held; full native window/browser proofs assert the
actual applications release startup exclusion once discoverable.

The Linux real Chromium maintenance proof now runs
`browser-maintenance-host-proof.py` once per native host. It uses the product
private-control server and verifies the exact Node child PID/executable. This
matches Windows ownership topology, but does not claim Windows Job evidence.
The prior singleton test owner raced when old/new native hosts overlapped during
initial DSH-to-Pi switching. `test_browser_control.py` now explicitly registers
two overlapping actual native hosts and observes that the replacement stays
registered after the old host exits normally. Failed real-page reservations
record only form/draft-presence flags and control metadata, never their values.

Native supervisor tests discover the actual background-owner pipe through a
retained process observation, reserve it, and verify prompt/memory peers against
its kernel Jobs. They reject cross-component/unrelated PIDs and unknown names.
This is identity/admission evidence, not a complete coordinated shutdown.

The same native supervisor proof now uses the actual companion participant
client to prepare, renew and cancel prompts/memory. Their authenticated pipe
peers must belong to the selected component's Job before any maintenance request
is sent. Portable contract tests reject active, expired, unbounded and malformed
reservation acknowledgments. Hosted native execution is still required.

`test_windows_http.py` uses actual Windows loopback HTTP processes. It compares
the kernel-reported peer with the launched child, checks that ownership/executable
refusals send no HTTP credentials, then lets the original exit and rebinds its
port with another process. The retained observation must refuse the replacement
before HTTP bytes. This is transport evidence, separate from real DSH/voice
integration and actual update transactions.

The compiled Windows managed-DSH proof now reserves the discovered background
owner, constructs the DSH participant from its private profile, and runs the
existing maintenance/history sequence through the kernel-bound HTTP client.
It confirms the observed server exits when the owner's whole Job drains, then
cancels owner reservation before explicitly restarting DSH. Linux/macOS keep
their existing direct component proof. No external provider or voice engine is
substituted for this deterministic owned-DSH qualification.

`windows-inno-proof.py` additionally invokes the disposable
`windows-inno-handoff-proof.py` coordinator. The actual extracted Inno Setup
process duplicates its startup writer, remains protected after that coordinator
exits or is deliberately crashed, completes repair and releases the gate. An
invalid handle is refused before a version change. These tests do not use a
customer installer or production handoff authentication; those remain separate.


`test_maintenance_reservations.py` uses actual shared Admission peers to cover
busy accepted work, independent heartbeat renewal, expired/lost acknowledgments,
reverse cancellation and cleanup waiting for an in-flight renewal. It never
commits shutdown. `test_windows_preparation.py` adds portable discovery/busy
failure unwinding; its discovery/kernel boundaries are controlled fixtures.
`test_windows_supervisor.py` additionally runs the whole actual prompt/memory
preparation on Windows, checks both startup exclusions and waits for real renewal
before restoring still-live services. `windows-managed-setup-proof.py` adds the
compiled desktop/DSH/companion group, restored transcript, and refusal while an
actual deterministic-model turn remains active. Those new native assertions
await hosted execution; they do not qualify voice, browser commit or an update.


The Inno handoff fixture now launches through the independent installer adapter.
Its bytes are copied into an explicit private fixture file; the test's digest is
not a publisher-signature claim. Wrong-digest launch must refuse. While the real
extracted Setup waits, the coordinator verifies its Job membership and refuses
its own unrelated PID; the parent verifies the artifact cannot be opened for
writing. Both normal close and deliberate coordinator crash must preserve Setup
and startup exclusion through successful repair. New native execution is pending.


The authenticated Inno extension compiles an x64 helper for the x64 Setup host
on both runner CPUs (the application/runtime still use their native target).
It tests a kernel-bound private pipe, recipient-side startup-handle checks,
READY/APPLY separation, cancellation and coordinator loss before authorization,
and Setup survival after an authorized coordinator exit/crash. The source helper
allows alternate roots only in a development build. The fixture records whether
its coordinator is inside an outer runner Job; it explicitly preserves that
runner boundary rather than claiming a production breakaway. New native tests
are pending after correcting process/thread generic access mapping.

The handoff proof additionally refuses an unrelated kernel pipe client without
disrupting the genuine prepared installer, and refuses a deliberately wrong
coordinator PID before gate acknowledgment. Its artifact-write probe uses the
native file adapter, preserving the actual Win32 sharing error rather than the
Python CRT's generic permission mapping. New assertions await execution.


The assembled graph fixture explicitly starts its prompt/memory services through
its existing disposable supervisor and waits for actual RPC readiness. They are
normally lazy, so merely sending a DSH turn is not evidence that both are running.
The two-window render proof allows 15 seconds specifically for a one-shot PNG
export, records its duration and verifies the success response/file signature.
Its normal control timeout remains three seconds; capture is never replayed.
The portable proof passes; corrected native graph/render assertions are pending.

Windows full application packaging: `test_windows_package.py` checks build intake;
`scripts/windows-application-install-proof.py` builds and installs the actual
payload into compiled-in disposable paths, checks live Qt draft refusal, repair,
redirect refusal and software-only removal with retained persistent data. Native
execution is required; this does not establish signed update/rollback or physical
hardware support. See [installer scope](../docs/WINDOWS-INSTALLER-DECISION.md#actual-application-installer-candidate).

Registered repair additionally deletes the installed launcher, Python runtime
DLLs, launch script and version metadata, executes Windows' actual ModifyPath
and reopens the repaired native application. The small exact-template test also
checks pending-update/removal refusal, another source's receipt and missing
ownership registration, plus damaged metadata and preserved settings. These new
cases require native x64/ARM64 execution; local compilation is not repair evidence.

The installed proof also starts the real owner and native preview, invokes
`scripts/windows-application-update-proof.py` as a separate coordinator, and checks
actual same-build Inno application after observed graph/coordinator exit. This
qualifies the Windows apply adapter when native CI passes; N-to-N+1, signing,
recovery and rollback remain separate gates.

Journal completion adds fault checks for unknown APPLY followed by independent
health, failed health/wrong release preservation, pre-APPLY refusal and failed
archive recovery by fresh inspection. These are storage/decision tests; they do
not stand in for native installed health or rollback qualification.

`test_local_health.py` renders the actual shared preview widget and rejects an
unexpected Qt backend while asserting no controller, subprocess or preference
write. It runs on Linux and in the Windows/Mac GUI jobs. The compiled launcher
proof adds unresolved-record/unsafe-directory refusal before Python, exact health
action routing, binary output and maintenance exclusion. Its recording script is
inert. The full installed proof exercises the actual native Windows health script
with disposable profile cleanup, missing-helper and mismatched-metadata refusal,
preserved journal/data, and ordinary reopening only after archival. These native
cases require fresh execution; portable rendering alone does not qualify them.

At `3674b4a`, both native launcher guard/routing reports pass. The new Windows
font-health test fails under offscreen QPA, while the existing Windows-QPA proof
passes actual font coverage. The test now runs in the Windows-QPA step and no
longer overrides the selected backend. Font coverage remains mandatory; corrected
native execution and installed health are still pending.

The corrected Windows-QPA health tests and all fast desktop checks pass both CPUs
at `8997b4e` ([run](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36412274580)).
This qualifies source UI health and compiled entry routing, not the full installed
health observer. Five additional journal cases cover cancellation before shutdown,
unknown release, commit/APPLY refusal and failed phase-write/archival. Two platform
tests compose actual reservation cleanup with the shared coordinator and preserve
active work or an unresolved record as appropriate. The native managed DSH proof
adds a real held-turn cancellation case with synthetic artifact identity and no
installer invocation; execution of that addition is pending.

`test_payload_integrity.py` uses real files to verify sealed payloads, same-size
corruption, missing/changed installed metadata, obsolete files/directories, alias
refusal and malformed/colliding inventories. Eight portable cases pass; Windows
also runs its junction case. Packaging tests reject changed and extra staged
files without resealing. The installed Windows proof now calls the product
inspector before local health instead of comparing a private reference-tree
walk. Native template/full-package execution of this addition remains pending.

The initial `8ae02e9` Windows inventory suite and template both fail ordinary
files because cached DirEntry metadata omits their link counts. The implementation
now obtains full no-follow stat metadata; the same tests must pass on both native
CPUs, including the hard-link and junction refusals. No alias assertion is waived.


Payload identity now uses explicit Windows birth time across path/handle stat;
handle-to-handle change time is still checked. The suite adds real file replacement
and modification-during-hash refusal, plus native creation/change timestamp
separation. Local: ten passing cases and two native skips. `84f2e95` x64 Inno passes
inventory integration; fast Windows fails only the timestamp fixture's missing
pywin32 constant, corrected to supported `GENERIC_WRITE` access.

The Windows exact-template and full installed proofs now execute the retained
installer's independent `/augmentorinspect=1` worker without installed Python,
launcher or metadata, and with an unresolved journal. They require matching
artifact-bound reports, preserved data/journal and no repair side effects. Inno's
intentional nonzero no-install exit is never counted as success by itself. The
new helper/worker is not yet native-qualified. Actual Inno script compilation,
four package tests and Python compilation pass locally.


At `cca5907`, all fast desktop tests, including all 12 inventory cases, pass x64
and ARM64. Exact-template independent inspection passes x64; ARM64 fails after
extraction without a report. Follow-up diagnostics expose only numeric native
stage/error and Python phase, and the helper observes whole-Job exit within its
original deadline. The packed extraction order is also corrected. Native rerun
and complete installed qualification remain pending.


[Inno at 11c1706](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36416227313)
passes both CPUs at merge checkout `9e126b38d98961ecc5e9fbaff3b2a30c5d1f891a`;
both reports confirm independent damaged-runtime inspection and preserved pending
state/data. The prior ARM64 failure's exact cause was not recorded. Full installed
integration remains pending and now explicitly requires independent inspection
refusal while a real window retains an unsent draft. Python compilation and
whitespace checks pass for that additional assertion.


`test_recovery_source.py` adds six read-only cases: exact source/digest binding,
same-version foreign build/installer refusal, incompatible schemas, unknown
shutdown PIDs retained as history, non-apply observations for terminal/prepared
phases, and bounded/duplicate/malformed records. All six plus 43 update tests and
four package checks pass locally. Native template tests add live writer exclusion,
private record alias refusal, missing-runtime source assessment, foreign/malformed
source refusal and unchanged data. The full installed proof assesses its actual
unresolved same-build journal. New native execution is pending; matching never
implies apply/rollback authorization or publisher trust.


Native `4b2bfaa` reaches successful source assessment and active-writer/record-alias
refusal on both CPUs, then catches a fixture write that leaves trailing bytes.
The corruption fixture now truncates its existing descriptor and checks exact
intended bytes before launching Setup; post-inspection preservation checks remain.
Two additional inventory cases cover an entirely absent final root (all entries
missing, no directory creation) and refusal of missing ancestors/wrong root types.
Local inventory: 14 cases, 12 pass and two native skips. Four package cases and
script compilation pass. The native missing-payload repair fixture now requires
inspection before and after restoration while retaining disabled startup/data;
corrected/new native qualification remains pending.

At `3b3f89f`, [Inno qualification](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36418939338)
passes both CPUs, including corrected corruption fixtures, exact recorded-source
assessment and absent-root inspection/repair. Fast Windows passes all 14 inventory
cases and six source-assessment cases. Full x64 at `4412deb` passes busy-draft
inspection refusal, inventory, isolated native health and reopening; ARM64 is still
running. These separate evidence scopes supersede the preceding pending entries.

`test_update_recorded_source.py` adds six private-file lookup cases: missing,
damaged and newer selection; absent source without fallback; corrupt source or
receipt; CPU/malformed/incompatible-record refusal; aliases; and Windows file
pinning. Run the existing `test_update_*.py` discovery: 49 cases, 48 local passes
and one Windows-only skip. All six independent source-assessment cases also pass.
The actual native template now locates the real cached source with a deliberately
changed selection, then verifies the independent inspection's record, transaction
and metadata hashes. Its new native run is pending; no interrupted restoration,
N-to-N+1 or rollback is claimed by this lookup fixture.

At `68062de`, both native Inno/fast Windows jobs pass the changed-selection lookup
and all 49 update cases. Full `4412deb` also finishes successfully on both CPUs
and Mac Qt; downloaded Windows inventories have no differences and native UI
health identifies the exact source. This predates the new independent health path.

`test_health_report.py` adds five portable groups covering exact metadata bytes,
foreign build/CPU/QPA, rendering/fonts/dimension types, protocol/field shape and
bounded duplicate/malformed input. Both health observers share this validator.
These five, six source-assessment cases, 49 update cases (one native skip locally)
and four package cases pass. Python and Inno compilation pass. New native template
checks use `windows-health-fixture.py`, whose synthetic UI fields qualify only
kernel admission and failure handling through the actual bootstrap/private Python.
The separate full-payload proof requires real native UI health from the standalone
installer, exact identity and an unchanged active record. Native execution of this
new path is pending; neither fixture proves completed interrupted restoration.
