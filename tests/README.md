<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

`test_linux_system_qt.py` covers 11 synthetic cold-launch boundaries: pinned
manifest/profile scope, package-version/member/import drift, concurrent query
changes, loader injection and refusal before the ABI child executes. The
[actual Arch/Leap proof](../docs/LINUX-SYSTEM-QT-STACK.md) separately prepares fresh
runtimes, renders synthetic controls and executes CPU Silero VAD. Full product,
physical sessions/audio and live dependency maintenance remain unqualified.

The October 2 [Noble lifecycle/shortcut checkpoint](../docs/LINUX-DISTRO-ROLLOUT.md#noble-lifecycle-shortcut-defect-and-next-target-probes)
records actual Wayland lock/cold-launch acceptance separately from the failed
complete QMP shortcut proof. Extension regression covers visible focus outside
the actor inventory: it stays blocked with a null eligible target. The installed
fixture needs a separately staged fixed artifact before actual acceptance.

Codex runtime tests: build first, then run `node --test tests/codex-*.test.mjs`.
They cover real app-server operation against a synthetic Responses provider,
the native wire adapter, durable recovery, private IPC and profile contracts.
`test_codex_credentials.py` exercises a synthetic credential store.
`codex-chatgpt-auth.test.mjs` uses actual loopback callbacks and freshly signed
identity tokens with a mocked OpenAI transport. `codex-chatgpt-accounts.test.mjs`
covers protected-account/index contracts, rotation/crash fencing and logout.
The expanded `proof-codex-credentials.mjs` tests account save/rotation/reopen/logout
through real OS storage with synthetic tokens and renewal, including final cleanup.
No real OpenAI OAuth, account, inference or owner credential is involved. See
[account implementation and remaining host/UI work](../docs/CODEX-ACCOUNTS.md).
The Codex Chromium test loads the real extension/native host in a temporary Linux
profile and exercises a synthetic-model browser task, including the toolbar activeTab
grant and actual screenshot bytes through pinned Codex. It requires Chromium with
the DevTools `Extensions.triggerAction` command (testing-only extension-debugging
flag, temporary profile) and
is explicitly skipped on macOS because its native-host registration is Linux-specific.
No personal browser profile or provider credential is used.
See [Codex evidence and limitations](../docs/CODEX-INTEGRATION.md) before treating
these as real-provider, OAuth, OS-keychain, GUI or installed-release qualification.

The Codex desktop runtime test uses the real pinned app-server and Python desktop
socket handler with a synthetic OS backend. It proves transport/ownership/Stop,
not GUI control. `scripts/vm-codex-desktop-proof.py --vm-dir ...` adds actual
consent, capture, input and saved-file checks in the marked disposable Plasma VM,
with host desktop autostart disabled. Its deterministic provider does not establish
live-model vision quality or installed/macOS qualification.

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

The new `--observer-job` cases exercise explicit breakaway from a nested
kill-on-close Job. No `qualification_outer_job` fallback is used in these cases.
Both real Inno processes must be outside that observer Job, while an ordinary
child stays inside. After both normal observer exit and a deliberate crash,
the ordinary child must terminate and the exact retained Setup handle must stay
live through successful installation. Python compilation passes; these new
native fault cases await execution. The remaining hosted runner ancestor is
still recorded rather than claimed absent.


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

At `b6b2313`, [native Inno](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36421972168)
passes both CPUs at `74bda13605c23702802ac0ab1071a2675069b759`; downloaded reports
confirm synthetic source-health admission and its damaged/failed-probe refusal
checks. Fast Windows also passes both CPUs, including all five report-validation
cases. Actual independent full-payload UI health and interrupted restoration still
require their separate execution evidence.

At `c530fda`, full x64/ARM64 application qualification passes real independent
Windows UI health and complete inventory with its actual pending record preserved.
Merge checkout: `ad703348d4faa61cff8a11d44c996fd653510995`; see the
[full run](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36423029869).
This is actual rendering evidence, distinct from the preceding synthetic template.

The exact-template proof now uses `windows-template-update-proof.py` as a fresh
disposable coordinator for actual READY/APPLY and observed Setup exit. It checks
locked-directory refusal, saved journal/placement receipts, preserved unknown old
files, a complete clean replacement, and replacement with absent `current`.
Synthetic journal disposal is explicitly fixture-only. The full installed proof
separately requires old full-payload displacement and independent UI health.
Local package/update checks and Inno script compilation pass; new native placement
execution is pending. These same-build cases do not prove cross-version restoration.

At `e98a142`, both native templates pass clean/absent-payload placement and locked
folder preservation in run `36432080462`, merge checkout
`521151e33204421421981be0f1f35742bb1c688b`. Full app execution is still separate.
New template tests invoke `/augmentorrecover=source` under a busy writer, against
an incorrect recorded source, and successfully without installed runtime/metadata
while selection names a synthetic target. They require retained old bytes, exact
journal preservation, restored repair/source selection, ordinary-startup refusal
and independent synthetic health. The full app proof separately checks actual
source application and real UI health with the original record preserved. Native
execution is pending; no distinct-version or recovery-completion claim follows.

`test_update_source_restoration.py` adds thirteen real-storage/fault cases: distinct
source outcome with exact original target/history retained, phase ordering, live
writer exclusion, changed original/attempt, failed exit/health, child crash and
uncertain intent/completion/archive writes. All 62 update cases pass locally (one
existing Windows-only skip). The full app proof composes the shared attempt with
actual retained-source Setup exit, installed selection/registration checks, full
inventory and native health under read leases before archival/reopening. This new
native completion execution is pending; the original proposed target is synthetic.
Source application itself passes both native templates at `04f3317`, run
`36433486621`; template health is synthetic, not full Qt evidence.

Full clean placement passes both CPUs at `e98a142`, run `36432080543`, including
complete inventory, retained old payload and independent actual Windows UI health.
All 62 update cases pass fast Windows at `5277087`; the active-record pin added
during final health postdates that run. The two installer proofs now call the
actual extracted `/augmentorrecover=previous` observer instead of orchestrating
restoration/completion in fixture code. The template includes the pinned pywin32
distribution, a real Python/native bootstrap and synthetic health. The full proof
requires actual Qt health and reopening. Both require missing installed Python,
exact original archival, source selection/registration, complete inventory and
the distinct receipt. Private inner Setup logs are retained as failure artifacts.
Local update/package checks and script compilation pass; native observer, breakaway
on observer crash and actual distinct-version execution are still pending.

Codex production prerequisite: `tests/codex-external-runtime.test.mjs` starts
the actual pinned app-server through an external npm symlink from a simulated
production application with no bundled Codex package. It checks wrong/missing
CLI refusal and credential-free private version probes. `test_codex_packaging.py`
checks the maintained prerequisite, refuses nested supplier packages/production
dependency regressions and preserves unknown-native-file rejection. These checks
do not clear supplier redistribution or real model/account acceptance.
`scripts/proof-codex-prerequisite.mjs` repeats version/one synthetic turn/exact
native restart/history through the actual extracted Debian package and both Mac
bundles in CI, using packaged Node and a separately installed supplier CLI.
The loaded-Chromium Codex proof waits for each memory button to become enabled
before clicking once; a changed status label precedes completion of context
loading and is not sufficient evidence that the control can accept another click.

Codex draft transformation: `tests/codex-prompt-improvement.test.mjs` exercises
bounded Responses streaming, invalid/incomplete outputs, selected credentials,
redirect refusal, host shutdown and maintenance, and the actual native adapter
and Browser bridge against synthetic services. `tests/test_prompt_improvement.py`
and Browser `surface.test.mjs` cover revision protection and Undo. These checks
do not establish live-provider quality or full-window/device acceptance.


Codex Home: `tests/codex-home.test.mjs` covers durable calls, scoped receipt
ownership, legacy SQLite migration and no replay; `tests/home-client.test.mjs`
checks cancellation capability negotiation. `tests/codex-app-server.test.mjs`
uses pinned Codex and actual native/Browser bridges with a synthetic NAS,
including resumed tool definitions. Home's `identity.test.mjs` verifies that
request-specific cancellation cannot stop another client/chat or replacement
request. No test touches the owner's NAS or household devices.


Codex memory foundation: `tests/codex-memory.test.mjs` checks committed public
capture, duplicate/live/replay distinctions, concurrent tool activity and an
actual isolated companion with no configured model. `tests/codex-context-contract.test.mjs`
qualifies pinned Codex additional-context roles and persistence across updates,
omission and restart; its pass documents an API limitation, not completion of
replaceable continuity. Neither test enables production Codex memory.

`codex-memory-transport.test.mjs` qualifies bounded Unicode-preserving fragments,
current-request manifests, modality, unavailable/oversized recall and close races.
Its actual pinned-runtime fixture also verifies unchanged-data dedupe, historical
reply/edit context boundaries, supported native compaction, unchanged display
history and restart. Inference is synthetic; this is not a fixed lifetime
context-size or live-memory quality claim. Current launcher activation is below.

`codex-memory-host.test.mjs` now uses an explicitly injected memory client and
synthetic native events to verify pre-turn Stop, capture/recall order, restart
dedupe without leases, fixed source/tool scope, historical capture cutoffs,
native child revocation and awaited failed-worker cleanup. The session contract
also rejects stale native acknowledgment during preparation. These prove the
host wiring with synthetic native events; actual pinned-host, companion,
controlled-engine and loaded-UI proofs below qualify the development launcher.

`codex-memory-runtime.test.mjs` joins actual pinned Codex with the real isolated
Python memory and prompt-library companions. Three proofs cover canonical tool
registration, exact owned/denied foreign source retrieval, modality, historical
child capture cutoffs, capture pause/restart, Stop while a completed memory reply
is held at the transport boundary, explicit continuation and unavailable-service
recovery from public native history without model replay. Its service fixture
allowlists the child environment and uses empty state without owner configuration.
A further actual host/companion case captures emoji at both 8,000-unit chunk
boundaries with multilingual text, requires exact three-piece reconstruction,
and verifies identical durable IDs/content after restart without model replay.
Inference is deterministic; Hindsight is unconfigured. These are host/companion
transport proofs, not controlled-engine generation, live quality or installed UI
qualification. Run with `AUGMENTOR_PYTHON` pointing at the test Python environment.

The same file's optional Linux proof provisions a disposable pinned Hindsight
0.10.0 container/volume through the public controlled installer. It connects real
Codex Browser activity to the actual companion/gateway, holds synthetic model
generation and verifies Stop closes the upstream socket, stops the memory job
and prevents idle/reconstruction replay. It removes only its fresh named test
container/volume and empty configuration; cleanup failures fail the proof.
Requires local Docker and the pinned image; ordinary CI skips both engine cases:

```sh
AUGMENTOR_PYTHON=/path/to/test/python AUGMENTOR_CODEX_MEMORY_ENGINE_PROOF=1 \
  node --test tests/codex-memory-runtime.test.mjs
```

The held-generation case qualifies admission/cancellation with the real engine.
A second case completes all six retain/consolidate/page stages across both banks,
requires actual consolidated observations and generated-page cache, and verifies
a derived-page-only marker reaches the next Codex request. Idle/restart perform
no extra inference and preserve the exact stage receipt and remaining budget.
Both cases use deterministic synthetic model replies; they do not establish
semantic classification/page quality, Mac Docker or physical installed acceptance.

The standalone-launcher Qt case in `codex-memory-runtime.test.mjs` runs
`fixtures/codex/native-memory.py` with actual composer Enter/Send and existing
Memory dialog controls. It verifies paused capture, preserved records, resumed
continuity and hidden internal context against real isolated companions. The
loaded `codex-browser-chromium.test.mjs` also validates next-turn continuity,
exact parent/child source capture and actual Settings Memory pause/resume. Both
use synthetic inference; Qt is offscreen and Chromium uses an empty test profile.
The development launcher supplies the shared client following these proofs;
installed applications and existing memory/model configuration are unchanged.


### Codex paginated history

`codex-history.test.mjs` validates ascending turn/item pages, cursor loops,
malformed pages and foreign items. `codex-session.test.mjs` proves a failed
later page cannot resolve an unknown submission. The real pinned-runtime
`codex-app-server.test.mjs` forces one-item pages and verifies user correlation
and tool output, then exercises host recovery through native/Browser fixtures.
`codex-context-contract.test.mjs` also checks that updated then cleared
collaboration-mode developer instructions retain prior snapshots in model input.
These are synthetic-provider contracts, not live-account qualification.


### Codex active-turn steering

`codex-steering.test.mjs` runs the shared host with pinned Codex and a held
synthetic Responses stream. It proves same-turn delivery, duplicate-request
suppression, both native user client IDs, and host restart/history recovery.
`codex-session.test.mjs` covers early terminal events, lost acknowledgments,
client-ID reconciliation, stale target rejection and no conversion to queued
input. Native/Browser queue UI qualification remains separate.


### Codex native queue controls

`codex-steering.test.mjs` additionally launches `fixtures/codex/native-queue.py`
with real offscreen Qt controls, the controller/adapter/event stream and private
host socket. It exercises Enter, promotion, removal, event reconnect, same-turn
steering, FIFO next-turn delivery and restart history using pinned Codex plus a
synthetic Responses server. Python must include PySide6/QtTest; choose it through
`AUGMENTOR_PYTHON` (both platform workflows declare these dependencies).
`test_queue.py` also covers host action flags and exact observed turn identity.
Session/ledger tests qualify durable Stop pause, unknown promotion/no replay and
bounded aggregate queue admission. These tests do not activate installed apps.


### Codex Browser queue controls

`apps/browser/test/queue.test.mjs` checks serialized submissions/actions,
identity-based reconciliation, stale revision rejection, duplicate clicks,
unknown outcomes and session/read-only/disconnect boundaries. The existing
`codex-browser-chromium.test.mjs` now exercises actual composer Enter and row
Steer/Remove, panel reload and next-turn ordering through native messaging and
pinned Codex. It inspects synthetic provider inputs to exclude removed text and
duplicate steering. Set `AUGMENTOR_QUEUE_SCREENSHOT` to a temporary PNG path to
capture the waiting-row UI for visual inspection. The fixture is Linux-only;
DOM and shared host contracts run independently of that physical-browser route.


### Codex exact fork boundaries and host lifecycle

`codex-branch.test.mjs` covers exact message selection, refusal of mid-turn cuts,
complete item/status fingerprints and immutable journal lookup after restart.
`codex-fork.test.mjs` uses pinned Codex and a local synthetic Responses server.
It proves inclusive reply/exclusive edit/empty history, inherited tool results
and definitions, retained persona, no inference or tool replay during creation,
source preservation and independent workers sharing the supported native store.
The host case additionally verifies duplicate identity, concurrent admission,
paused-parent queues, descendant ownership, restart, profile changes, lost native
acknowledgment and history mismatch without another fork. No real account or
model credentials are required. Run after `npm run build`; these tests are in
the root Node suite. The following client proof enables the controls; unknown-creation reconciliation
remains a separate requirement.


### Codex Branch/Edit clients

The third `codex-fork.test.mjs` case launches `fixtures/codex/native-fork.py`
with the actual Qt Window/Controller/adapter/IPC host. It activates rendered
transcript actions, waits for asynchronous Send readiness and uses Enter to
edit the first input on an empty child. It verifies source history, draft
restoration and persisted child selection. Set `AUGMENTOR_PYTHON` to the test
Python with PySide6/QtTest, as for the native queue fixture.

`codex-browser-chromium.test.mjs` additionally clicks the loaded panel's Branch
and Edit controls, checks model-visible inherited tools and omitted later input,
and reloads the edited child without another submission. Both proofs use the
real pinned binary with a synthetic provider and isolated user state.
`test_codex_branch.py` and Browser `branch-request.test.mjs` cover interrupted
client recovery, identity retention and failed storage before dispatch. The
host test distinguishes in-flight creation, ready children and absent IDs.


Known-native-ID recovery is covered by `codex-fork.test.mjs`: a saved incomplete
child survives host restart, remains blocked on changed profiles, corrupted
read results, incomplete item pages and failed index replacement, then resumes
its original thread after successful verification. Fork-call and inference
counts cannot increase during recovery. The lost-acknowledgment case without
a recorded native ID still refuses replay. The index-write failure is injected
only inside the test's isolated temporary session directory.


### Codex worker idle/release checks

`codex-idle.test.mjs` covers loaded-descendant activity, background terminals,
unfinished goals, hooks, notification changes and complete inventory handling.
Its host fixtures check that a refused release retains the worker and that an
incoming prompt waits for successful release, then resumes the original native
thread without sending through a closed worker. `codex-fork.test.mjs` also checks
the native idle API against the real pinned runtime and synthetic Responses.
These checks precede automatic worker-pool reuse; the hard worker limit remains.


### Codex bounded worker pool

`codex-pool.test.mjs` covers idle least-recently-used replacement, native-ID
preservation, concurrent opening reservations, active and unknown dispatch
protection, unverified state, bounded reinspection, and retry after capacity or
initialization refusal. Undispatched records survive restart without becoming
unknown native work or blocking maintenance. The real `codex-fork.test.mjs`
host fixture runs with two chat workers, requiring retirement/reopen while
preserving exact fork history and keeping paused parent input out of inference.
The newly opened native idle check waits for stable authoritative state because
startup notifications can correctly invalidate an earlier snapshot.

### Local Qwen template diagnosis

`python3 scripts/prepare-qwen-codex-template.py --source ORIGINAL --out SEPARATE`
prepares a candidate file without restarting or modifying any installed service.
[The exact observed hashes and limits](../docs/CODEX-LOCAL-QWEN.md) record real
Codex HTTP 400 evidence, offline leading/later developer rendering, byte-identical
single-system output, retained system-image rejection and successful tool grammar
generation using llama.cpp's actual offline tools. Source/output/unknown-block
guard checks and Python compilation passed. This is not a live inference/tool
qualification and does not change the accepted provider matrix.

### Codex native credential storage

`python3 scripts/proof-codex-secretservice.py` creates a disposable Linux session
bus and encrypted keyring and runs the actual Node/Python store.
`AUGMENTOR_PYTHON=/path/to/python node scripts/proof-codex-credentials.mjs` uses
the intended interpreter and native OS backend. Both verify separate-reference
roundtrip, update, idempotent deletion and complete cleanup with synthetic values
only. [Release dependencies and qualification limits](../docs/CODEX-CREDENTIALS.md)
include the actual pinned-Debian proof, five verified Mac wheels and passing Mac
14/26 build/Desktop/standalone companion Keychain evidence at `0726234`.
These are not OAuth or paid-provider tests.

### Codex supplementary source identity

`test_codex_sources.py` covers source pin/checksum handling, unsafe/duplicate
archive members, explicit inline license integrity, unique versioned monorepo
paths, generated/changed source gaps and nearest-workspace metadata inheritance.
The actual [collection](../docs/CODEX-PACKAGING.md#october-1-version-and-source-identity-evidence)
rechecks all pinned archives and emits full Rust-file comparisons plus a compact
hashed inventory. Source matches do not automatically grant license applicability
or binary redistribution approval; unresolved records remain explicit.

`test_codex_native_sources.py` additionally covers rootless Gitiles archives,
retaining nested original notices and contained aliases without writing links,
wrong archive roots, escaping links, duplicate entries and traversal. The actual
native collector verifies all 28 pinned archives and retains 3,817 notice files;
two full collection reports match byte for byte. Its compact committed inventory
hashes each complete notice record. This is source/notice evidence, not final
linked-binary coverage or installer clearance.

Codex voice tests now use the independently authored [synthetic protocol peer](fixtures/codex/VOICE.md). They qualify Augmentor transport and client playback
plumbing, not the private Resonant Voice service or physical audio.
Task reliability: `tests/dsh-context-budget.test.mjs`, `tests/dsh-execution.test.mjs`,
`tests/test_reply_completion.py` and `tests/test_desktop_profile.py` exercise
deterministic evidence/recovery, UI and Linux capability-discovery contracts. The opt-in `scripts/task-reliability-proof.mjs` checks a real local
model with restricted read-only tools; see [scope and limits](../docs/TASK-RELIABILITY.md).

### Noble runtime selection

`test_linux_python_runtime.py`, `test_complete_setup.py` and
`linux-python-selection.test.mjs` cover runtime identity, checksum/path refusal,
bundle-target mismatch, service interpreter propagation and broken-policy
refusal. Python and Node calculate the same identity for both locked profiles.
`release/prove-noble-runtime-selection.py` requires a fresh ordinary-user Ubuntu
24.04 fixture, the verified seven-wheel cache, exact Silero v6.2.1 model and
bundled Node. Run it offline against the built source. It prepares both profiles,
reuses the runtime through setup, verifies selection/stage/rollback, executes
Node/Browser selection and the actual CPU VAD, and checks corruption refusal.
The [checked report and limits](../docs/LINUX-DISTRO-ROLLOUT.md#noble-runtime-selection-and-cpu-vad)
remain distinct from a package, connected harness, GNOME or physical audio proof.

`test_linux_wheel_inventory.py` uses synthetic wheels to check notice byte
preservation, versioned ELF/executable hashing, unsafe/duplicate archive members,
metadata mismatch and changed archive refusal. Distribution/setup cases check
the Noble contract, cross-target refusal and verification after completed setup.
`release/prove-linux-package.py` additionally prepares Noble's installed offline
cache as the ordinary user before rendering and exercising both package leases.
`release/prove-complete-linux.py` renders and runs helpers with the actual desktop
descriptor interpreter. The artifact review verifies whole wheel and embedded ELF
hashes, original notice bytes and pinned supplementary collections; its license
and corresponding-source completeness flags remain false.

### GNOME 46 profiles and signed guest preparation

`test_gnome_shortcut_settings.py` checks both GSD generations, partial/malformed
portal schemas, Save failures and rollback with foreign entries retained.
`gnome-observer-extension.test.mjs` executes the actual extension with synthetic
Shell objects: only 46's explicit Ubuntu/user inheritance is admitted; lock,
overview and modal guards remain; actor mapping and display monitor events bump
the serial without subscribing to nonexistent 46 window properties. Observer
protocol tests retain the compositor-owner/epoch fence and false input gate.

`test_gnome_vm_preparation.py` covers detached/clear-signed checksum matching,
duplicate lines, wrong signer/image, cross-fixture reuse and wrong backing image
refusal before boot. `test_noble_gnome_provisioning.py` checks the strict guest/
ordinary-user marker guard. `release/provision-noble-gnome-vm.py` additionally
requires clean installed Noble packages, AppArmor, the prepared verified Python
runtime and actual Ubuntu Wayland session; it refuses an existing user seat0
session. Its provisioning report does not prove login or application startup.
Actual GNOME shortcut/control/lock acceptance must be recorded independently.

`release/inspect-noble-gnome-vm.py --source FULL_COMMIT` is a read-only real guest
inspection using the selected verified Python. It requires the marked ordinary
QEMU user, pristine clean packages, canonical selection/service ownership,
AppArmor, actual seat0/session environment, Ubuntu/user observer and active
default extensions. It expects Wayland by default; `--session-type x11` explicitly
inspects fallback and cannot claim a Wayland pass. It observes the three-field
GSD profile without Save/delivery or input authorization. The checked
`release/qualification/ubuntu24.04/gnome-x11-a7ee9c5.json` additionally binds real
guest screenshots and focused idle readback; fixture timer/unlock controls and
connected/shortcut/physical limits remain explicit.

The separate `gnome-wayland-mesa2-a7ee9c5.json` checkpoint records one actual
Wayland login/startup/observer/UI pass with a coherent official Mesa .2 cohort,
independently verified archive signature/index/package hashes and controlled
networkd fixture recovery. The application uses XWayland. Latest .3 failure,
native Qt Wayland, repeated startup, delivery/lock and connected/physical tests
remain separate; neither checkpoint enables GNOME input tools.

### Cinnamon native shortcut and interrupted-worker proof

`test_cinnamon_shortcuts.py` covers desktop/Mac routing, shared machine key
identities, typed/bounded replies, private ownership, atomic pre/postcommit
failures and pending-intent refusal/shape boundaries. GNOME's seven adapter
regressions remain. `release/prove-cinnamon-shortcut-interruption.py` runs only in
the marked ordinary-user Mint ISO VM with the exact synthetic canonical launcher,
actual Cinnamon6.6.4/X11 and no app installation. Separately stage reviewed helper
and driver in that owned fixture, unlock through normal password authentication,
and run `/usr/bin/python3 ~/cinnamon-shortcuts-proof/prove-cinnamon-shortcut-interruption.py`.
It sends no keyboard events or lock commands. Four abrupt worker phases, a newly
allocated row and foreign takeover verify real DConf/ownership recovery. Do not
run its synthetic fixture on an owner's desktop. The
[checked report](../release/qualification/next-targets/20261002-cinnamon-native-shortcuts.json)
keeps initial timeout/default-lock/dependency refusals and current source hashes.
The inert spice under `tests/fixtures/cinnamon-shortcut-spice` is test-only and
must remain disabled after the owned VM conflict test.710 native cases/708 pass/
two platform skips is source evidence; physical keyboard and full Mint product
acceptance remain separate.


`test_desktop_worker.py` uses a real private GLib context and Qt event loop to
verify nested response waits cannot execute queued cleanup and GUI Stop/timers
remain responsive. `test_desktop_consent_session.py` uses synthetic bus replies
for unique-owner, expected-identity, generation/late grant and FD cleanup fences.
Eleven cases pass; these Linux GLib cases skip where that runtime is absent.
`release/probe-gnome-portal-consent.py` is an input-free actual Fedora QEMU probe,
separately staged as documented in the [GNOME plan](../docs/LINUX-GNOME-CONTROL-PLAN.md).
The [checked evidence](../release/qualification/next-targets/20261002-gnome-native-consent.json)
keeps first failures, exact candidates and source721-case regression separate from
production GNOME control, capture, lock/restart and public release qualification.

### Source runtime derivative and GNOME execution candidate

`test_source_pyside_derivation.py` checks producer preservation, member-byte/tag
preservation, new RECORD, deterministic derivation, hash/RECORD tampering,
unsafe/signed input refusal and overwrite refusal. The runtime stager is separately
executed against actual source-produced ELF/plugin/QML files; its fresh-container
import/widget/SVG/QML probe is recorded in [runtime work](../docs/LINUX-LGPL-SOURCE-RUNTIME.md).
It is not full graphics, audio, licensing or product qualification.

`test_gnome_control.py` covers logical source geometry/negative origin, scale1-only
refusal, owner/cancellation, fresh-scene and compositor point checks, terminal
observer/topology cleanup, idle lock/epoch watch and unqualified keyboard refusal.
`test_capture_stream.py` now proves private-context cancellation without actual
GUI/default-source delivery and checkpoint rejection of an arriving frame.
The full isolated Arch source suite runs739 cases:737 pass/two Mac-only skips.
The initial test-mocking failure is retained; no actual candidate pointer/keyboard
input, native capture, password/restart, production discovery or KDE service
threading acceptance is claimed. See the [checked source report](../release/qualification/next-targets/20261002-gnome-runtime-candidate-source-tests.json).

The separately executed recipient QtSvg proof validates archive/patch/library hashes,
rebuilds from fresh Svg source using the unchanged matching Qt SDK, and compares
actual native behavior in fresh processes. It requires explicitly marked owned
fixtures and two separate runtime candidates; it never swaps the selected app's
libraries. Final product entrypoint/complete legal/source-kit qualification remains
separate. [Evidence](../release/qualification/next-targets/20261002-source-qt-recipient-replacement.json).

### Native GNOME capture and first Stop reason

`test_gnome_control.py` now includes bounded consent timeout and shared-Event
first-cause preservation through repeated user/native Stop; the consent tests
also constrain reason enumeration. The exact source runs742 native cases in owned
Arch:740 successes/two Mac-only skips. The separately staged capture/GTK probes
pass real Fedora scale1 frame/token creation, visible Stop after capture, visible
Stop during a synthetic stalled frame and native sharing revocation after capture.
[Checked source hashes, failed candidates and limits](../release/qualification/next-targets/20261002-gnome-native-capture.json)
keep source tests, native capture and future input qualification distinct. No
Notify/action is invoked; production GNOME input remains disabled.

### Authenticated source toolchain and fresh reconstruction

`release/acquire-ubuntu-toolchain.py` executes real gpgv/full-index/package/source
checks against complete preserved Ubuntu metadata before obtaining separate bytes.
`release/probe-ubuntu-toolchain-auth.py` checks ten actual refusal paths against the
owned kit, including corrupted signed content and altered package bodies. These
require the separately retained complete metadata and acquired package objects;
they are not synthetic passing package-install tests. The fresh no-network builder
reconstructs the exact410-row inventory from the pinned public base and verified
.debs. [Proof, first failure and ongoing source-build boundary](../release/qualification/next-targets/20261002-ubuntu-source-toolchain-reconstruction.json)
remain separate from full recipient/runtime/license/release qualification.
