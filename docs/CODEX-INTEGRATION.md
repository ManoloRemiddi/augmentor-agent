<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Codex integration: implementation and evidence

Status: in development on `feat/codex-integration`, based on canonical main
`b70d965` plus the [build plan](CODEX-INTEGRATION-PLAN.md). Codex is selectable in development source; this is not an installed or qualified
Codex release. The complete C0–C9 acceptance scope remains in
the plan; no work package is certified complete by this foundation.

## Runtime foundation — 30 September 2026

`@openai/codex` is pinned to **0.159.2** in the application lockfile. The package
declares Apache-2.0 and platform-specific optional binaries. The installed Linux
x64 binary reports `codex-cli 0.159.2`. Mac/ARM and packaged redistribution remain
unqualified. Do not substitute the user's global CLI or inherit its auth cache.

`packages/codex-runtime/src/` currently contains:

- `rpc.ts`: stdio JSONL app-server transport, bounded frames/pending requests,
  correlated responses, server interaction replies, timeout/crash failure and
  process shutdown. Unknown request outcomes are never retried; unhandled
  unsupported interactions are rejected. Upstream stderr is consumed without publishing
  potentially private diagnostics.
- `config.ts`: isolated runtime state and allowlisted process environment;
  explicit provider/model configuration with retries disabled. Provider secrets
  enter the runtime environment rather than command arguments. Remote endpoints
  require HTTPS; local profiles require loopback; URLs cannot contain credentials,
  queries or fragments. The plan-usage endpoint is fixed to OpenAI. These are
  configuration primitives, not an implemented login or credential store.
- `storage.ts` / `operations.ts`: owner-only durable JSON replacement with file
  and directory sync; per-thread queued/accepted/terminal/unconfirmed ledger.
  Intent becomes unconfirmed before dispatch. Restarts preserve unknown outcomes
  and block subsequent admission until reconciliation. Duplicate request IDs
  cannot silently change their input or replay completed work.
- `session.ts` / `events.ts`: admission around Codex's native thread, queue
  pausing, Stop, native client-ID reconciliation, and conversion into existing
  Augmentor chat events. Public reasoning summaries can be displayed; raw
  reasoning content is excluded. No second agent loop is implemented.
- `host.ts` / `journal.ts` / `ipc.ts`: durable product session index, one worker
  per conversation authority, native-thread reopening, display history, bounded
  owner-only Unix socket, version handshake and per-session subscriptions.
  The host refuses changed profile revisions, unconfirmed creation and active
  worker release. Approval presentation now uses the shared broker described below;
  installed-service qualification remains pending.
- `profiles.ts` / `credentials.ts` and `services/codex/credentials.py`: versioned
  API/local profiles with opaque credential references, serialized replacement,
  explicit destination-change checks and an OS-store helper over private pipes.
  The helper directly selects Keychain or Secret Service, without loading a
  configured fallback backend. Subscription profiles require a future supported
  login flow and cannot be created by pasting a token into API setup.
- `browser.ts`: scoped executor ownership, bounded browser tool arguments/results,
  durable per-call admission and observation-bound mutations; see the Browser
  checkpoint below for supported tools and qualification limits.
- `desktop.ts`: scoped consented desktop tools, per-call/consent records, fresh
  observation-token admission and owned-sharing recovery; see the desktop checkpoint.
- `main.ts`: standalone shared host (`npm run start:codex` after building), with
  a private profile store and bounded socket. Startup recovers a stale socket only
  after an owned-socket check, a refused connection and unchanged inode. The
  existing lifetime-lease launcher and startup lock now recognize Codex.
- `apps/native/augmentor_linux/adapters/codex.py`: thin native wire adapter, model
  selection, saved chats and shared event subscription. Native and Browser engine
  selectors now expose Codex (development), with profile forms in existing setup
  entrypoints. `apps/browser/codex-bridge.mjs` transports native-messaging frames
  to the same host without depending on a Desktop window.

The actual generated schema was inspected using:

```sh
node node_modules/@openai/codex/bin/codex.js app-server generate-json-schema --out /tmp/augmentor-codex-schema
```

Generated schema and isolated native state are local test artifacts, not product
configuration. The stable protocol uses `clientUserMessageId` on `turn/start`
and `clientId` on native user-message items for reconciliation. This correlation
does not imply upstream idempotency. A history read that omits an operation never
proves it was not executed.

## Reproducible evidence

```sh
npm ci --ignore-scripts
npm run build
node --test tests/codex-*.test.mjs
```

On Linux x64 with Node 24.19.0, the focused suite now passes **27 tests**.
TypeScript checking and the normal build pass; the full root `npm test` suite
passes 220 tests, including the focused Codex tests. Evidence categories:

The full native suite runs 551 tests successfully with two skips in an isolated
environment containing the pinned PySide6/QtTest wheels. The default system
Python lacked QtTest and failed before that environment correction. No installed
desktop Python or Qt libraries were replaced.

| Coverage | Evidence type and limit |
| --- | --- |
| Request correlation, malformed/oversized frames, timeout, crash, stale approval replies | Synthetic subprocess fixture; does not certify upstream approval UI |
| Streaming, saved thread reopen after app-server restart, harmless shell tool execution, Stop | Real pinned Codex binary against a deterministic loopback Responses SSE fixture; no real model or account involved |
| Session driver and normalized user/assistant events | Exercised through that same real app-server proof |
| Shared host restart and continuation with durable display history | Real pinned binary and fixture endpoint; not yet a packaged service |
| IPC handshake, subscription isolation and existing socket preservation | Real Unix sockets with a fixture dispatcher |
| Standalone host startup, profile persistence, SIGKILL and socket recovery | Real host subprocess and local profile; no inference |
| Native Python adapter send/stream/saved chats/model identity | Real adapter, shared socket, pinned Codex binary and synthetic Responses provider; not the actual Qt window |
| Missing display completion recovered from native history without replay | Real Codex history with a deliberately removed synthetic display record |
| Credential replacement, locked-store failure, destination changes and concurrent revisions | In-memory keychain fixture plus private profile files |
| Intent persistence, restart, identity conflict, cross-thread/corrupt ledger rejection | Disk-backed automated tests |
| Completion before acknowledgment, unknown-outcome reconciliation, early Stop race, private reasoning exclusion | Focused fault/order fixtures |

The real-binary test asserts `stream: true` and `store: false` in its provider
request. It creates synthetic conversations in a temporary isolated CODEX_HOME,
uses no account tokens, performs only a harmless fixture shell command, and
removes its own test state. This is transport/tool evidence, not API-provider,
local-model, OAuth, desktop, browser, voice or installed-artifact qualification.

The harmless shell-tool fixture explicitly uses `danger-full-access` because
container CI cannot create Codex's Linux sandbox namespace. It uses a fixed
synthetic provider and temporary workspace. Production configuration remains
`workspace-write` with `on-request` approvals. Sandbox enforcement must be
qualified separately; this fixture is not evidence for it.

The first remote CI run exposed missing license/NOTICE files in the Codex npm
archives. The notice catalog now binds upstream texts to exact 0.159.2 package
versions and immutable upstream commit `ff6aec96948b70d94983af2641a6b67c94faeff5`.
Six license-inventory tests pass. This package-text correction does not complete
the native binary dependency inventory or release qualification.

At source `3ff5c5d`, Mac 14 and Mac 26 bundle workflows passed; these exercised
existing DSH/Qt packaging, not the Codex interfaces. Debian source checks passed
but packaging correctly refused the new unreviewed Codex native executable. The
native binary/dependency inventory is an open C8 gate. Do not bypass it merely
because npm license text is now present. The workflow now additionally runs the
shared Codex tests on Mac; results apply only after that newer commit runs.

`requirements-codex.txt` pins the credential helper's development dependency to
keyring 25.6.0. Its actual Secret Service write/read proof could not run on this
machine because the store was unavailable or locked; it returned the expected
explicit error without a plaintext fallback. No account token was used. Both OS
stores need successful platform proofs and release dependency locks before C2/C8
completion. The two Python helper contract tests use a synthetic store.

Profile catalogs distinguish configuration from inference validation. Listing a
configured model does not mean a live request succeeded. `models.validate`
currently validates selected profile/model and credential availability only and
returns `validation: configuration-only`; real connection-test UI remains work.

Observed protocol race: app-server can acknowledge `turn/start` before it accepts
`turn/interrupt`. The session driver retries only the definitive `-32600` "no
active turn" interrupt rejection, against the same turn, for a bounded interval.
It does not resend the prompt. Stop pauses admission of the next queued message;
an unconfirmed cancellation remains visible to the caller.

## Observed real local-provider incompatibility

A synthetic text-only request to the existing local Qwen server failed with its
template parser error: `System message must be at the beginning`. No model
settings, templates or service deployment were changed. This is a real-provider
failure, separate from the passing synthetic provider proof.

The pinned runtime's generated configuration schema permits only
`wire_api = "responses"`; starting it with `"chat"` terminates before initialize.
The configuration validator now rejects Chat Completions explicitly. Thus the
plan's possible legacy transport is unavailable on this chosen release. The
current Qwen endpoint cannot yet be advertised as compatible. Resolve its
Responses instruction/tool handling or qualify another compatible local
endpoint before C0/C2 completion; do not add a silent transport/billing fallback.

## Next work and release gaps

Continue C0 proofs against a real compatible local model/API, eligibility and
context/tool/voice spikes. C1 still needs installed-service supervision, full
worker/profile authority verification, approval presenter leases and broader
recovery qualification. Native paginated history must replace bounded full
history reads before large-conversation qualification.

C2–C9 still require successful OS credential proofs, real Desktop/Browser setup and
conversation paths, eligible OAuth flows, scoped product tools/persona, memory,
Resonant Voice, Linux/macOS packaging, migration/rollback and full acceptance.
The existing DSH/Pi interfaces and running installations have not been changed.
Subscription distribution eligibility remains unresolved; configuration code is
not permission to ship an authentication route.

## Desktop and Browser profile setup checkpoint

Both source interfaces now provide API/local profile creation and editing,
OS-backed credential submission/removal, and an explicit text response check.
An empty key preserves an existing credential; removal is deliberate. Forms clear
entered secrets after successful saves, preserve drafts after failures, and
require edited settings to be saved before checking them. Profile name changes
preserve the connection revision; endpoint/model/key changes invalidate previous
validation. A late check cannot validate a changed profile.

The check calls the configured Responses endpoint with a short synthetic message,
`store: false`, streaming enabled, no tools and no conversation history. It requires
a completed text response and reports `responses-text`, not agent/tool compatibility.
Redirects are rejected and provider error bodies are not displayed. API checks may
be billed by the selected provider. This is independent of the real Codex runtime
proof, which still uses a synthetic local provider.

The real native-messaging entrypoint now passes initialize/create/send/history and
saved-chat checks through the pinned Codex process, with no Desktop window. Browser
DOM and Qt form tests cover credential clearing, explicit checks and stale edits;
these are fixtures, not installed Browser or live-provider UI qualification.
Root Node coverage passes 225 tests, Browser DOM coverage passes 45, and three
focused Qt setup tests pass. The complete native suite runs 554 tests with two
skips after fixing the settings preview without a controller. A rendered offscreen
Qt setup dialog was inspected for readable fields and unclipped controls. Subscription sign-in remains unavailable in both
forms. Browser tool execution, approval presentation, memory and speech remain
pending; no installed application was updated by this checkpoint.

## One-presenter approval broker

`interactions.ts` maps pinned app-server command and file-change approvals to
Augmentor's existing allow-once/deny UI. Runtime configuration explicitly selects
human approval review. No session-wide or persistent execution rule is granted.
File approval requires a complete proposed-change preview and rejects requests
for a persistent grant root. Network requests show the network destination;
oversized or incomplete previews fail closed. Structured questions are mapped in the following checkpoint. Dynamic tool execution
and additional server-request types still require their own mappings.

The IPC event subscription owns presentation. Only one subscriber receives an
opaque reply capability; it is never journaled or broadcast to viewers. Disconnect
transfers the request to another subscriber with a new capability. Old replies,
wrong-session replies and repeated replies are rejected. With no presenter, on
timeout or on upstream resolution, no action is authorized. Responses use the
existing per-request native connection or Browser bridge and the shared host.

The real pinned runtime now requests escalated execution of a fixed synthetic
command through each client bridge. Both fixtures deny it, Codex receives the
denial and completes its turn. This exercises the production approval policy
without executing that command. Broker/IPC tests additionally cover single-owner
presentation, transfer, expiry, stale replies, file preview requirements and
upstream cancellation. Actual modal UI interaction, successful approved execution
under the OS sandbox, structured questions and installed cross-surface behavior
remain qualification work. Reference: [app-server approvals](https://learn.chatgpt.com/docs/app-server#approvals).

Approval-checkpoint validation: build passes, root Node suite passes 232 tests,
Browser DOM suite passes 45, and the final focused Codex run passes 39 after
explicitly pinning human approval review. The earlier 554-test native-suite record
belongs to the setup checkpoint; this checkpoint additionally exercises the actual
Python adapter against the real Codex process. The host broker guarantees one subscribed client connection. The following
Browser refinement adds document ownership behind that connection.

Browser refinement: each panel maintains a named extension connection. The service
worker grants each pending Codex approval to one live document, checks that owner
again on reply, and releases claims when the document disconnects. A second panel
cannot open the same approval prompt. Panels reconnect their presenter registration
after service-worker loss; native-bridge failure clears stale requests and claims.
Registry tests cover competing documents, disconnect transfer, expired ownership
and foreign origins. Browser DOM coverage now passes 46 tests. This is source/DOM
evidence; loaded Chromium multi-panel and actual modal acceptance remain pending.

## Structured-question checkpoint

The pinned runtime requires `features.default_mode_request_user_input = true` to
permit its question tool during ordinary conversations. With that explicitly
configured, both actual client bridges now complete a `request_user_input` round
trip against the real Codex process and synthetic provider. The provider observes
the selected answer in the subsequent tool output. No second agent loop is added.

Questions use the same single-presenter capability and Browser document claim as
approvals. The host validates question IDs and complete, bounded answers, and maps
Augmentor answers into Codex's ID-keyed response. Cancellation, expiry and missing
presenters return no fabricated answers. Secret-entry questions are rejected;
protected profile setup remains the credential entry path. This is an explicit
capability limit, not a generic secret-input implementation.

Native reuses the existing question dialog. Browser now shows a cancellable form
with all questions, optional choices and free text. Nothing is preselected; empty
or partial submissions are disabled. Model text is literal text, not HTML. Upstream
resolution and page closure dismiss the form, and input fields are cleared when
it closes. DSH's existing question flow is unchanged.

Validation: build passes; root Node suite passes 234 tests; focused Codex suite
passes 41; Browser DOM suite passes 48; eight existing offscreen native interaction
checks pass; complete sidebar boot/send proof passes. These are real-runtime,
fixture, DOM and offscreen evidence, not a loaded Chromium or installed-platform
release claim. The Debian job for `bc60f80` still fails at the reviewed-native-binary
inventory gate for Codex, after application checks; no bypass was added.

## Packaging inventory checkpoint

[Codex packaging](CODEX-PACKAGING.md) records 32 supplier native-file hashes and
ABI requirements, the exact upstream source pin and a reproducible source collector.
It verified 1,304 locked external archives and, after the nested-license scan fix,
retained 4,690 notice/metadata files with 138 missing-notice sources. Another 53
exact-commit archives supply candidate attribution for 116 of these; 22 remain
without a retrieved candidate. Candidate applicability is still pending. The payload verifier detects
drift but does not grant release clearance. Debian's unknown-native-file gate is
unchanged. C8 remains incomplete until notice/source coverage, Mac parity and real
artifact execution/rollback are qualified.

## Shared persona and instruction snapshots

New Codex chats load the maintained `config/agent-persona.md` into the supported
`developerInstructions` field. Augmentor does not replace Codex's base/system
instructions. The shared host adds an explicit current-capability statement so
the persona's references to Browser, desktop, memory, Home, voice and metrics do
not imply those unfinished adapters are available. Future tool registration must
update this capability statement together with its negotiated product flags.

The private conversation index stores the instruction text, format revision and
SHA-256 hashes of the persona and combined instructions before starting the native
thread. Resume uses that same snapshot rather than reloading a changed persona.
Corrupt snapshots fail to load; old conversations without a snapshot retain their
existing native instructions. Both surfaces use the same host path. The real
runtime/provider fixture verifies the Augmentor persona arrives once on initial
inference and still occurs once after restart, without accumulating duplicate
instructions. This completes the persona binding, not C5's tool or prompt-library
integration, and does not qualify live-model personal-assistant behavior.

Validation for the persona checkpoint: TypeScript checks and build pass, the root
Node suite passes 235 tests, and the focused Codex suite passes 42 tests. These
include the real pinned-runtime fixture with a synthetic Responses provider.

## Maintenance admission checkpoint

`host.prepareShutdown` now atomically checks activity and enters a reversible
maintenance state. It refuses while requests, profile resolution, thread creation,
submission acknowledgments or interactions are pending, or while any saved thread
has active/unconfirmed work. A stopped worker is not evidence that an uncertain
operation never ran. Incomplete thread creation also prevents readiness.

After readiness, new work and profile mutations are rejected; local status/history
remain readable. Existing session queue pumps are suspended so a scheduled callback
cannot start a prompt after the check. `host.cancelShutdown` reopens admission and
restores normal queue processing while retaining Stop's independent queue pause.
The state is process-local and exposed by `host.describe.maintenance`.

Validation: build passes; 239 root Node tests passed, followed by an additional
focused direct-creation race test. Five maintenance cases cover admission freeze,
in-flight profile resolution, saved uncertain operations, scheduled queue dispatch
and direct creation. The standalone host/socket proof also exercises prepare,
rejected configuration and cancellation. These are fixture/process checks.
Installer orchestration, maintenance ownership across process restart and actual
upgrade/rollback remain unfinished; this endpoint alone does not qualify C1/C8.

## Worker subprocess ownership and CI cleanup failure

The `feaede6` [Debian run](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36733028675)
and [macOS run](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36733028680)
failed the real Codex fixture during directory cleanup: an upstream plugin-catalog
Git helper was still writing after its parent exited. Those runs stopped before
packaging; the earlier native-inventory failure remains a separate unresolved gate.

On Linux/macOS, each Codex RPC worker now starts in its own process group. Shutdown
signals that owned group, waits for the wrapper exit with bounded TERM-to-KILL
escalation, then kills remaining members. An unexpected wrapper exit also triggers
group cleanup. It does not enumerate or signal unrelated user processes. This
covers ordinary inherited helpers; intentionally detached descendants require
separate supervision and are not claimed covered by this mechanism.

Validation: build and all 242 root Node tests pass locally, including the real
pinned-runtime/provider/client fixture and two subprocess cases with a descendant
that ignores TERM (normal close and unexpected wrapper crash). macOS CI after
this correction is still required; Linux fixture success is not macOS evidence.

## Linux maintenance orchestration and local backups

The private socket now supports `host.shutdown`. It freezes socket admission
before awaiting the host's activity check, refuses pipelined cancellation or new
work during that decision, flushes the accepted response, and closes the host and
workers. A refused shutdown leaves the server reachable. `host.describe` includes
the process ID used by the existing maintenance process-identity check.

`scripts/maintenance.py prepare --component all` now discovers the configured
Codex socket alongside Pi. It prepares Codex before closing any surface, stops an
idle host through its RPC, and cancels preparation if a later check fails. Failure
to reopen admission is reported explicitly. Browser-process detection includes the
Codex bridge. The existing local backup now includes `state/codex`, preserving
profile references, conversation metadata and native history while omitting sockets.
OS credential-store entries remain outside this file backup.

Validation: build and 244 root Node tests pass; five new Python cases cover busy
refusal, UI-busy rollback, ordered shutdown, backup preservation, and an actual
standalone Codex host exiting through the maintenance script. Two socket tests
cover pipelined requests and failed shutdown. All use isolated state. The prior
process-group correction has passed the shared-contract CI step on Debian and
macOS 14; the remaining jobs were still running when checked.

This is Linux maintenance source integration, not an installed upgrade or removal
qualification. Existing package lifetime leases remain the installer boundary;
macOS installer coordination and complete artifact/rollback acceptance still need
qualification. No installed application or user service was stopped by these tests.

## Scoped Browser tools and loaded Chromium evidence

New Codex conversations register five existing Augmentor browser tools: tab listing,
navigation, DOM snapshot, clicking and typing. This uses the pinned app-server's
[experimental dynamic-tool protocol](https://learn.chatgpt.com/docs/app-server),
with `experimentalApi` enabled only for conversations carrying the versioned
`browserTools: 1` contract. The generated schema was inspected with
`app-server generate-json-schema --experimental`. Codex persists the definitions
and restores them on native thread resume; no second agent loop is introduced.
Older conversations retain their previous tool and instruction contracts.

The existing browser executor/broker is reused. An executor must attach to its
subscribed chat and only that socket can answer its requests. Changing subscriptions
or disconnecting revokes ownership and settles pending calls without retrying.
New native conversations can also use these tools when their chat is explicitly
attached in Browser. Without an attached extension, execution fails visibly.

The host validates arguments and bounded results and writes a private per-call
record before dispatch. Completed calls return their recorded result when repeated;
unconfirmed records report an unknown outcome instead of executing again. Cached
snapshots never grant fresh action authority. Only one dispatch may be pending per chat. Stop,
upstream resolution, turn completion and worker loss invalidate pending calls;
there is no claim that a dispatched browser side effect can be undone.

Clicking and typing require an exact enabled-control selector from a successful
snapshot in the current turn. The host passes the observed tab ID, URL and document
origin timestamp separately from model arguments. The extension checks the tab
before dispatch and the URL/timestamp inside the injected action before touching
the element. Mutations, failed observations and executor changes invalidate the
observation. This detects navigation/document replacement, not every possible DOM
change inside an existing document. Dynamic-tool events use the existing chat log.

At this initial five-tool checkpoint screenshots were not registered. The image
qualification checkpoint below supersedes that restriction for explicitly checked
profiles and new chats. Desktop GUI tools, Home, memory, voice and prompt improvement
remain separate unfinished work.

Validation: build passes; all 252 root Node tests and 48 Browser DOM tests pass.
The real pinned Codex fixture round-trips browser observation and a targeted action
through native messaging, then repeats after reopening the saved thread. The new
`tests/codex-browser-chromium.test.mjs` loads the actual unpacked extension in an
isolated Linux Chromium profile, connects its native host to the shared Codex host,
and uses a deterministic local Responses provider. Through the normal panel message
API, it creates a first chat, reads a local fixture page, types in its observed input,
refreshes the observation, clicks once, and verifies both the real DOM and the final
reply rendered in the panel. This found and fixed a first-chat error: the host's
missing-conversation message now matches Browser's explicit not-found distinction.
Socket/unit tests cover foreign owners, stale replies, cancelled/timed-out calls,
unknown saved dispatches and changed tab/document rejection.

This is real Chromium/native-messaging/runtime evidence with a synthetic model,
not live-model quality, physical user acceptance, macOS Browser qualification or
an installed release. The Linux native-host registration used by the test is confined
to its temporary profile. User browser profiles and installed services are untouched.
The preceding `73cc076` macOS 14/26 bundle jobs passed; Debian reached packaging and
still rejected the unreviewed Codex executable. Current Browser changes need their
own CI evidence and do not waive the remaining C0–C9 gates.


## Image qualification and actual Browser screenshot transport

Both native and Browser connection forms now offer **Check image response** for a
saved, unchanged API/local profile. It makes an explicit potentially billable
Responses request containing only a synthetic PNG with four random colored cells.
The answer is checked against the pixels; a generic successful text response does
not qualify. No user files, history or tools enter this probe. The format follows
[Responses image input](https://developers.openai.com/api/docs/guides/images-vision).
This checks basic input transport and interpretation, not general vision quality,
tool accuracy or any subscription entitlement. Model behavior may change behind
an unchanged provider/model ID; the recorded timestamp is evidence of the last
successful check, not an ongoing availability guarantee.

The host alone records image qualification. Renaming preserves it; changing the
model, endpoint, connection kind or credential clears it. A stale check cannot
qualify a newer profile revision. New chats persist their image capability and
matching instruction snapshot; existing chats do not silently gain a new tool.
Qualified chats register `browser_screenshot` alongside the five existing tools.
Screenshot replies become app-server `inputImage` content, with bounded JPEG data
URLs and text metadata. Arbitrary remote image URLs are rejected. Images are kept
in private per-call records and Codex native history; the display journal includes
text metadata only. They use the existing thread retention/backup boundary.
Screenshots revoke selector authority: clicking/typing still needs a fresh DOM
snapshot. Replay returns a recorded result without recapturing the page.

The loaded Chromium proof exposed a real permission mismatch. Chromium's automatic
side-panel toolbar action deliberately skips the activeTab grant (see
[Chromium action runner](https://chromium.googlesource.com/chromium/src/+/refs/heads/main/chrome/browser/extensions/extension_action_runner.cc)).
The extension now opens the same panel through an explicit toolbar action handler,
which grants activeTab for the clicked tab. No broader host permissions were added.
The existing visible-tab/target-change checks remain in the capture executor.

Validation: type checking/build, **256 root Node tests**, **48 Browser DOM tests**
and **three offscreen native Qt setup cases** pass. The image-probe fixture decodes
the generated PNG and returns its pixel-derived answer, then verifies rejection
of a wrong answer. Profile, cached-result, size/type, capability and setup checks
cover the relevant failure paths. The real Linux Chromium proof verifies capture
is denied before the toolbar action, invokes that action using Chromium's isolated
DevTools extension interface, then transports actual captured JPEG pixels through
the native host and pinned Codex to the synthetic Responses provider. It also
retains real DOM typing/clicking and final-panel rendering checks. The qualification
flag in this transport proof is fixture-supplied; it is not a live-model vision test.
The temporary browser uses an explicit testing-only extension-debugging flag.

No installed application or personal browser profile was changed. Live-provider
vision quality, macOS loaded-extension behavior, native desktop GUI execution,
OAuth, memory, speech and complete artifact qualification remain unfinished.
At the preceding `4cc21f0` source checkpoint, macOS CI run
[36737148617](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36737148617)
passed; Debian run
[36737148571](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36737148571)
passed application checks and stopped at the unreviewed Codex native executable
inventory gate. This checkpoint does not bypass or resolve that packaging gate.


## Consented desktop tools and Plasma VM evidence

New image-qualified conversations on a supported desktop backend now register the
existing `linux_desktop_connect`, `linux_desktop_snapshot`, `linux_desktop_action`
and `linux_desktop_stop` tools. The legacy names also serve macOS. This is available
to both Augmentor clients through their shared Codex host; an open Qt window is not
required. The existing OS executor, consent prompt and independent Stop control
remain authoritative. The macOS helper must be present before new chats advertise
the tools. Older chats retain their persisted definitions and instructions.

The new bridge binds ownership as `codex:<conversation>`, validates bounded tool
arguments/results and returns JPEGs through app-server image content. An action
needs a token from a fresh capture in the same turn. Tokens are consumed before
dispatch and the existing executor additionally checks their expiry, current
window/focus and geometry. Cached captures cannot grant fresh action authority.
The bridge records each call before dispatch and returns recorded results without
repeating side effects. Unknown outcomes stay unknown; they are never replayed.
Consent requests are durably limited to one per turn, including after restart.
A declined or uncertain consent request cannot trigger another dialog in that turn.

Stop aborts the pending helper request, waits for it to settle, then checks and
releases only this chat's sharing. Turn end, worker failure, idle release and host
shutdown also release ownership. Durable lease markers let a newly listening host
reconcile surviving sharing after a crash; a duplicate host that fails socket
ownership does not stop the live peer. An uncertain/busy ownerless executor is
not treated as confirmed cleanup. Unconfirmed sharing blocks maintenance and
profile changes and produces a saved runtime-error message using both existing
chat renderers. The independent OS Stop button remains the immediate fallback.
A hard-killed host cannot synchronously guarantee cleanup; startup reconciliation
and the existing executor idle expiry are separate safeguards.

Images live in Codex native history and private per-call records; display history
contains text metadata. No new inference engine, automatic billing fallback,
broader OS grant or desktop specialist model is introduced. Existing Linux limits
(single-monitor KDE Wayland, ASCII text up to 256 characters) and macOS executor
requirements remain. These target checks do not constitute an OS sandbox.

Validation at this checkpoint:

- Type checking/build and all **265 root Node tests** pass. Nine desktop tests
  include the actual pinned runtime, real Python desktop client/socket handler
  and a synthetic OS backend. The runtime sends image bytes, resumes persisted
  tool definitions, denies consent, cancels an in-flight action and releases
  sharing. Contract cases cover stale/replayed tokens, cross-owner cleanup,
  unknown dispatches, repeated consent, overlapping calls and failed cleanup.
- **16 focused native Python cases** pass, including two real socket/client cases
  for the Codex owner namespace, foreign-owner rejection, token replay and the
  explicit non-starting status probe. These are fixtures, not native-device tests.
- `scripts/vm-codex-desktop-proof.py` passes against an isolated Debian 13 Plasma
  Wayland VM with staged candidate source, one monitor, scale 1.0 and pinned Codex
  0.159.2. It uses the actual native adapter and an explicitly forwarded private
  desktop socket with host desktop autostart disabled. The provider is a
  deterministic Responses fixture, including pixel decoding for profile
  qualification; it is not a visual-reasoning benchmark.
- The VM rejects declined OS consent, transports an actual screenshot to Codex,
  edits Kate and saves exactly `CODEX desktop verified` followed by a newline,
  then verifies sharing closes at turn end. A separate turn is stopped after
  partial text input begins; the saved file remains partial and unchanged after
  waiting, with no additional provider request or input replay. This qualification run used
  an overlay of the existing disposable VM image; the original image and the
  owner's desktop remain untouched.

The final VM run passed all three cases on exact source
`ce77fa68721ed8b4923ba038e8edf49d0829b439` with Codex 0.159.2. Its disposable
overlay VM was powered off after the proof. The proof records source revision,
runtime pin and tested input hashes locally.
The owning public documentation records the sanitized outcomes; VM keys, model
payloads and private paths are not publication artifacts. Run it only against the
marked disposable VM:

```sh
npm run build
python3 scripts/vm-codex-desktop-proof.py --vm-dir /absolute/path/to/disposable-vm
```

The loaded macOS desktop-control path, actual Augmentor Qt send/tool UI, live-model
vision quality, multi-monitor support and installed artifacts are not qualified by
this proof. C0–C9 remains open, including OAuth eligibility/login, Home/MCP tools,
prompt improvement, controlled memory, speech, remaining conversation operations
and packaging. At the preceding image checkpoint `ed5af14`, macOS run
[36739219839](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36739219839)
passed; Debian run
[36739220130](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36739220130)
passed application checks and still refused the unreviewed Codex native executable
at packaging. That gate remains in force.


## API/local draft improvement

Codex's Desktop and Browser adapters now expose the existing Improve prompt
operation. Both use the selected API/local connection profile and shared saved
improvement instructions. The shared host resolves credentials privately and
makes one tool-free Responses request; this auxiliary transformation neither
starts a Codex conversation nor appends to existing history. Codex still owns
all conversational turns and tools. Subscription profiles remain unavailable;
there is no fallback to DSH or another provider/account.

Only the draft (up to 6,000 characters) and improvement instructions (up to
8,000 characters) are sent. Requests use `stream: true`, `store: false` and an
empty tool list. The host accepts only a completed assistant rewrite with bounded
output; malformed, partial, clarification, refusal and tool outputs leave the
draft unchanged. Provider error bodies are not surfaced. Redirects are refused,
requests are not retried, and the 60-second deadline bounds a pending rewrite.
This follows the official [Responses streaming contract](https://developers.openai.com/api/docs/guides/streaming-responses)
and [stateless request guidance](https://developers.openai.com/api/docs/guides/migrate-to-responses).
`store: false` is not a promise about the provider's separate logging policy.

The host allows one pending rewrite, prevents profile changes and maintenance
while it runs, and aborts it on host shutdown. Existing composer Cancel, typing,
session changes and Undo preserve draft revisions. As with DSH, dismissing the
preview discards its late result but does not promise cancellation of already
started inference; its selected provider can still charge for that request.
No control layout was changed. Shared TypeScript/Python code applies to Linux
and macOS; device/UI and live-provider qualification remain separate.

Type checking/build, all **270 root Node tests**, **48 Browser tests**, four
native prompt-editor cases and **29 Home tests** pass locally. Five focused
Codex contracts cover bounded/malformed output, selected profile and
secret isolation, redirect refusal, shutdown cancellation, maintenance admission
and overlapping requests. The actual native Python adapter and actual Browser
bridge round-trip through the shared Unix host and synthetic Responses endpoint;
Browser reads saved instructions through a fixture of the shared prompt service.
The proof verifies no chat, runtime worker or history is created. This is not a
live-model rewrite-quality test or full native-window acceptance.

At preceding desktop source `ce77fa6`, both macOS jobs passed in
[36742665813](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36742665813).
Debian's application checks passed before the unchanged native executable review
gate failed in [36742665709](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36742665709).
That run also exposed a Home test's 100 ms race: its deadline could fire before
MCP dispatch. The test now holds an acknowledged dispatched call and triggers
the actual deadline callback, then verifies a subsequent model-requested write
is blocked by the unknown-outcome record. All 29 Home tests pass locally; no
Home runtime behavior or timeout was changed.


## Paired Home tools

New Codex chats now register the existing shared Home capabilities: status,
owner-enabled devices, direct changes, read-only requests, delegated Home
requests, receipt lookup and request-specific cancellation. Desktop and Browser
use the same host and persisted tool contract. Existing chats keep their recorded
capabilities; they do not silently acquire Home tools. Browser pairing settings
now route through the same shared prompt-service Home configuration as Desktop.
Unpaired calls report that Home is unavailable; no NAS address or credential is
invented from a prompt.

The NAS remains DSH-owned. Codex does not start a second Home agent locally,
connect directly to Home Assistant, or change the NAS model. Direct `home_set`
uses the NAS device-action endpoint without another model call. Delegated
`home_request`/`home_read` retain the existing NAS model and permission policy.
Only their explicit request text is passed, not the surrounding conversation.

The Codex adapter validates bounded arguments and durably records each tool
identity before dispatch. A changed or interrupted call is not replayed. The
existing SQLite Home receipts remain authoritative for NAS request IDs and
unknown-outcome admission. A separate receipt-ownership table records hashed owners atomically with new
receipts; the original four-column table stays compatible with older clients.
Existing rows are preserved with no invented ownership. Codex can retrieve or
cancel only IDs recorded for its conversation and current pairing. A global
unknown receipt can block another chat's write without granting that chat access
to the original request. No credentials are included in Codex tool-call records.

Home adds `requests.cancelById: true` to `/capabilities` and
`POST /requests/<request_id>/cancel`. The server checks both the paired client
and currently admitted request before signaling cancellation. A delayed cancel
cannot stop a newer request; even an owner client cannot use this scoped route
to cancel another client's request. Existing `/cancel` callers retain their
legacy behavior. Codex requires an explicit request ID and checks server support;
there is no fallback to broad cancellation on older NAS versions. Those servers
need this source update to support scoped cancellation; no deployed NAS was
modified by this checkpoint.

Stopping Codex interrupts waiting, but an already admitted NAS operation may
continue. Receipt lookup and scoped cancellation remain explicit operations;
neither a cancel acknowledgment nor ending a chat undoes a device change.
Instructions and failures preserve that distinction. Physical device state and
human acceptance are not established by a model's completion message.

Validation: build/type checks and **276 root Node tests**, **48 Browser tests**
and **30 Home tests** pass locally. Eleven focused Home/Codex-client cases cover
receipt ownership, schema migration, unknown outcomes, durable call replay,
argument validation and old-server cancellation refusal. The real pinned Codex
0.159.2 runtime invokes Home through both actual native and Browser adapters with
a synthetic Responses provider and isolated NAS HTTP fixture. A resumed Browser
chat retains its Home tool definitions; the three requested direct actions each
dispatch once. Real Home HTTP-service tests verify cross-client, wrong-request
and stale-cancel rejection. No real household or Home Assistant device was used.

The preceding `372dcfe` passed both macOS jobs in
[36744256437](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36744256437)
and Home CI, including the corrected deadline test. Debian
[36744256503](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36744256503)
failed earlier in the Chromium fixture: CDP discovered a target before its
extension document exposed `chrome.runtime.sendMessage`. The fixture now waits
for the exact extension URL, complete document, composer and messaging API before
sending its first message. The loaded Chromium proof passes locally after that
correction; the next CI run must qualify it on the Debian runner. The native
packaging review gate remains separately unresolved.
