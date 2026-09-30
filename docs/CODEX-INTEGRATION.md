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

On Linux x64 with Node 24.19.0, the initial focused suite passes **17 tests**.
TypeScript checking and the normal build pass; the full root `npm test` suite
passes 210 tests, including the focused Codex tests. Evidence categories:

| Coverage | Evidence type and limit |
| --- | --- |
| Request correlation, malformed/oversized frames, timeout, crash, stale approval replies | Synthetic subprocess fixture; does not certify upstream approval UI |
| Streaming, saved thread reopen after app-server restart, harmless shell tool execution, Stop | Real pinned Codex binary against a deterministic loopback Responses SSE fixture; no real model or account involved |
| Session driver and normalized user/assistant events | Exercised through that same real app-server proof |
| Intent persistence, restart, identity conflict, cross-thread/corrupt ledger rejection | Disk-backed automated tests |
| Completion before acknowledgment, unknown-outcome reconciliation, early Stop race, private reasoning exclusion | Focused fault/order fixtures |

The real-binary test asserts `stream: true` and `store: false` in its provider
request. It creates synthetic conversations in a temporary isolated CODEX_HOME,
uses no account tokens, performs only a harmless fixture shell command, and
removes its own test state. This is transport/tool evidence, not API-provider,
local-model, OAuth, desktop, browser, voice or installed-artifact qualification.

Observed protocol race: app-server can acknowledge `turn/start` before it accepts
`turn/interrupt`. The session driver retries only the definitive `-32600` "no
active turn" interrupt rejection, against the same turn, for a bounded interval.
It does not resend the prompt. Stop pauses admission of the next queued message;
an unconfirmed cancellation remains visible to the caller.

## Next work and release gaps

Continue C0 proofs against a real compatible local model/API, eligibility and
context/tool/voice spikes. C1 still needs the supervised shared host, private IPC,
worker/profile authority separation, durable display history, approval presenter
leases, and full recovery. Native paginated history must replace bounded full
history reads before large-conversation qualification.

C2–C9 still require protected profile credentials, real Desktop/Browser setup and
conversation paths, eligible OAuth flows, scoped product tools/persona, memory,
Resonant Voice, Linux/macOS packaging, migration/rollback and full acceptance.
The existing DSH/Pi interfaces and running installations have not been changed.
Subscription distribution eligibility remains unresolved; configuration code is
not permission to ship an authentication route.
