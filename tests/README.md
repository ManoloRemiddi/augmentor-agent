<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

Codex runtime tests: build first, then run `node --test tests/codex-*.test.mjs`.
They cover real app-server operation against a synthetic Responses provider,
the native wire adapter, durable recovery, private IPC and profile contracts.
`test_codex_credentials.py` exercises a synthetic credential store.
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
| Mac packaging/runtime | `test_macos*.py`, `test_dsh_payload_staging.py`, `scripts/dsh-payload-proof.mjs <staged-dsh-root>` | Real compiled launcher test requires ARM64 Mac; payload proof uses actual FFI/search/shell/PTY. See [Mac evidence](../docs/MACOS-DISTRIBUTION.md); not signing/TCC acceptance. |
| Mac signing policy | `test_macos_signing.py`; `scripts/macos-signing.py <app> --plan` | Policy rejection tests and a real Mac framework seal fixture. [Candidate preparation](../docs/MACOS-RELEASE.md) still requires Developer ID credentials and signed-runtime/public-install acceptance. |
| Mac managed first run | `test_macos_managed_setup.py`, `test_macos_setup_ui.py`, `scripts/macos-managed-setup-proof.py` | Ownership/retry/secret handling, real Qt form with fixture worker, and private real launchd/DSH/model fixture. [Acceptance boundary](../docs/MACOS-MANAGED-SETUP.md) excludes signed end-user install and extra plugins. |
| Browser DOM | `node --test apps/browser/test/*.test.mjs` | DOM/bridge fixtures, not installed Chrome acceptance |
| Automatic memory | `python3 -m unittest discover -s tests -p test_hindsight_memory.py`; `node --test tests/dual-memory-integration.test.mjs` | Fake HTTP engine plus actual DSH/Pi lifecycle; follow workflow's locked DSH setup |
| Actual memory engine / model | `python3 scripts/proof-controlled-memory.py --help` | Disposable pinned engine, explicit fixture/live modes, archive isolation and bounded real-model completion |
| Maintenance | `python3 -m unittest discover -s tests -p test_lifecycle.py` | Lifetime locks, preserved backups, real temporary memory service shutdown |
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
