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
It verified 1,304 locked external archives and retained 4,688 notice/metadata files,
with 139 missing-notice sources explicitly pending. The payload verifier detects
drift but does not grant release clearance. Debian's unknown-native-file gate is
unchanged. C8 remains incomplete until notice/source coverage, Mac parity and real
artifact execution/rollback are qualified.
