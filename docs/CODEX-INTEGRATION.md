<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Codex integration: implementation and evidence

Status: in development on `feat/codex-integration`, based on canonical main
`b70d965` plus the [build plan](CODEX-INTEGRATION-PLAN.md). This is not an installed
or user-selectable Codex release. The complete C0–C9 acceptance scope remains in
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
  interactions are rejected. Upstream stderr is consumed without publishing
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
  worker release. Approval presenter integration and service bootstrap are pending.

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

On Linux x64 with Node 24.19.0, the focused suite now passes **21 tests**.
TypeScript checking and the normal build pass; the full root `npm test` suite
passes 214 tests, including the focused Codex tests. Evidence categories:

| Coverage | Evidence type and limit |
| --- | --- |
| Request correlation, malformed/oversized frames, timeout, crash, stale approval replies | Synthetic subprocess fixture; does not certify upstream approval UI |
| Streaming, saved thread reopen after app-server restart, harmless shell tool execution, Stop | Real pinned Codex binary against a deterministic loopback Responses SSE fixture; no real model or account involved |
| Session driver and normalized user/assistant events | Exercised through that same real app-server proof |
| Shared host restart and continuation with durable display history | Real pinned binary and fixture endpoint; not yet a packaged service |
| IPC handshake, subscription isolation and existing socket preservation | Real Unix sockets with a fixture dispatcher |
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
context/tool/voice spikes. C1 still needs service bootstrap/supervision, full
worker/profile authority verification, approval presenter leases, native-history
backfill and full recovery. Native paginated history must replace bounded full
history reads before large-conversation qualification.

C2–C9 still require protected profile credentials, real Desktop/Browser setup and
conversation paths, eligible OAuth flows, scoped product tools/persona, memory,
Resonant Voice, Linux/macOS packaging, migration/rollback and full acceptance.
The existing DSH/Pi interfaces and running installations have not been changed.
Subscription distribution eligibility remains unresolved; configuration code is
not permission to ship an authentication route.
