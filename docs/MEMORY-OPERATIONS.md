<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Automatic memory: operations and developer contract

The September 21 controlled implementation supersedes unattended maintenance.
See [controlled memory](CONTROLLED-MEMORY.md). Do not restore the old worker or
retry policy to clear a pending status; pending memory can be an intentional
result of no active processing window.

Read [dual-memory architecture](DUAL-MEMORY.md) first. This guide concerns the
Hindsight 0.10.0 automatic system, not the separate [manual library](MEMORY.md).

## First setup and normal operation

Follow the pinned installer and deployment commands in [Dual memory](DUAL-MEMORY.md#local-setup-and-deployment).
The installer needs Docker and an existing local compatible model endpoint.
It does not install or reconfigure the model server. Use `augmentor-update` for installed artifacts; preserve matching DSH integration.
Fresh package/source sessions can journal text before the engine is configured.

The companion starts on first use and journals committed text immediately.
Automatic inference requires a trusted activity lease, an open bounded window
and remaining batch budget. Hindsight remains a separate persistent service,
with its autonomous worker disabled. Idle/closed chats and reconnects do not
trigger archive work. Cached facts/pages and source receipts support continuity
while derived memory is pending or processing is paused.

## Health and troubleshooting

```sh
curl --fail http://127.0.0.1:8889/health
docker inspect --format '{{.State.Status}}' augmentor-hindsight
```

The Memory UI exposes status/pause. For the companion RPC below,
`memory.dual.describe` reports `configured`, `available`, `events`, `pending`,
`failures` and `message`. `pending` counts unassigned eligible records plus
pending batch jobs; it is not the external historical queue size. `failures`
counts stopped batch jobs, including an interrupted or unknown stage. The
`processing` field reports pause, active state, job counts and configuration.
A completed batch does not prove the correctness of every extracted claim.

| Symptom | Meaning and next check |
| --- | --- |
| Text preserved, engine needs setup | Journal works; configure the pinned engine before expecting derived pages |
| Pending remains while model works | Check engine/model health and workload; avoid increasing concurrency blindly |
| Old/empty page | Check capture count, pending delivery and Hindsight consolidation; cache freshness is exposed by recall |
| Hindsight unavailable | Cached recall may remain usable; semantic search reports unavailable; ordinary chat continues |
| Wrong engine version / changed destination | Restore the tested version or perform an explicit data migration; do not bypass the destination guard |
| Wrong project continuity | Inspect the trusted session binding; default scope is canonical working directory, not inferred project names |
| No capture after pause | Expected; paused event IDs are recorded without text and are not backfilled on reconnect |

Private Docker/model logs and raw exports may contain conversation text. Inspect
locally and redact before attaching evidence to GitHub. Never test by deleting a
bank, outbox or journal to see whether it recreates itself.

## Local protocol and source ownership

Socket default: `~/.local/state/augmentor/dual-memory.sock`.
`AUGMENTOR_SHARED_STATE` / `AUGMENTOR_SHARED_DATA` override companion directories.
The Unix socket checks same-user access. This is a trusted local service, not an
internet or multi-tenant API. Each request/response is a JSON line, at most 1 MiB.

Read-only request:

```json
{"protocol":"augmentor-prompts/1","id":"status","method":"memory.dual.describe","params":{}}
```

The envelope deliberately reuses `augmentor-prompts/1`; the returned memory
protocol is `augmentor-dual-memory/1`. Do not confuse either with the optional
manual provider's `augmentor-memory/1`.

| Method | Inputs and semantics |
| --- | --- |
| `memory.dual.describe` | No parameters; status, local PID and configured person |
| `memory.dual.configure` | Optional boolean `enabled`, optional trusted `person`; affects default binding for future sessions, not existing bindings |
| `memory.dual.bind` | Required stable `session`; optional trusted `person`, `project`, `cwd`; first binding is durable, repeated binding returns the existing scope |
| `memory.dual.append` | Bound `session`, up to 100 `events`; each has stable `id`, `role` user/assistant, `mode` text/voice, nonempty `content`, optional `status` complete/interrupted/error and trusted `live` flag; changed content under an existing event ID is rejected |
| `memory.dual.recall` | Bound `session`; cached relationship/work facts and pages, timestamps/stale flags, last 24 direct current-session user receipts |
| `memory.dual.search` | Bound `session`, nonempty `query` up to 4096 characters; searches only the two bound banks; pause suppresses results |
| `memory.dual.export` | Bound `session`, optional nonnegative `after` cursor; up to 100 raw events from the bound person's relationship scope, across that person's projects; use `next` until an empty page |
| `memory.dual.source` | Bound session and exact `seq`; original current-session event only |
| `memory.dual.activity` | Trusted bound session, lifecycle owner and foreground/tools/stop phase; six-second liveness, absolute 120-second window |
| `memory.dual.processing` | Optional boolean `paused`; inference-only pause preserves capture/recall |
| `memory.dual.jobs` | Bound session; recent stage status, reason and remaining budgets, without transcript text |
| `memory.dual.import` | Bound session and explicit `after`/`through` interval of at most 100 records; grants eligibility, not activity |
| `memory.dual.retry` | Bound session, job ID and `reviewed: true`; at most one retry within original remaining budget |
| Legacy `claim`, `commit`, `fail` | `claim` returns no job; `commit` and `fail` reject custom distillation. Do not revive the retired summarizer |

Only trusted host adapters bind identities and append events. The model-facing
`memory_recall` tool cannot choose arbitrary bank IDs. The single-user UI does
not authenticate speakers; changing a person's display name does not remap banks.

`services/memory/dual.py` owns journal/settings/binding and legacy tables.
`hindsight.py` subclasses it and replaces projection maintenance/retrieval.
`service.py` owns the socket and background worker. TypeScript capture/context
is in `packages/memory/src/dual.ts`; DSH hooks are in
`adapters/dsh-memory/automatic.mjs`; Pi hooks live in `packages/runtime/src/host.ts`.
Tests of the old `DualMemory` class alone are not proof of production Hindsight.

## Persistence, backup and rollback

The SQLite journal holds `settings`, `sessions`, `skipped`, `events`,
`event_scopes`, historical `projections`/`revisions`, and Hindsight's
`hindsight_destination`, `hindsight_banks`, `hindsight_outbox` tables.
The journal is authoritative for captured text. New `memory_eligible`,
`memory_jobs`, `memory_budgets`, `memory_windows` and `memory_processing` tables
hold admission/receipts; old outbox rows are retained but unused. Hindsight's
PostgreSQL volume holds documents, facts, observations, pages and the extension's
`augmentor_memory_stages` receipt table. Unknown stages stop rather than replay.

For package maintenance, the current `augmentor-maintenance prepare` refuses
active work, closes the idle companions (including automatic memory), and backs
up the shared data directory. The external Hindsight Docker volume is **not** in
that snapshot. Back it up separately using PostgreSQL backup tooling or a stopped
container volume copy. Preserve the volume during ordinary uninstall/reinstall.
See [lifecycle](LIFECYCLE.md). Do not point a journal at a different endpoint and
assume its cursors describe the new database.

Desktop rollback uses `augmentor-update rollback`; DSH plugin bindings and the
external memory engine need their matching saved configuration. Keep inference
paused throughout rollback: restoring the old worker can resume its historical
queue. Preserve the latest journal and engine volume. Do not overwrite new
conversations with an older backup merely to undo UI code.

## Explicit maintenance and recovery

```sh
python3 scripts/memory-processing.py status
python3 scripts/memory-processing.py pause
python3 scripts/memory-processing.py resume
python3 scripts/memory-processing.py jobs --session EXACT_BOUND_SESSION
python3 scripts/memory-processing.py import --session EXACT_BOUND_SESSION --after 0 --through 20
python3 scripts/memory-processing.py run --session EXACT_BOUND_SESSION --seconds 120
python3 scripts/memory-processing.py retry --session EXACT_BOUND_SESSION --job EXACT_JOB --reviewed
```

Import is optional, explicit and bounded; never select the entire archive as a
setup side effect. Review the stopped stage before retrying. Retry does not start
a window or replenish its budget. An exhausted job stays stopped for inspection.
The explicit `run` command opens a user-requested maintenance window; any live
foreground agent still takes priority. Ordinary operation needs none of these
commands. Stop/preemption can leave a stage for review, because an interrupted
write must not be assumed to have had no effect.

## Retention limits

Pause is not erasure. Raw events, derived memories and backups remain. There is
currently no supported automatic-memory erase UI or coordinated purge command.
Manual-library deletion does not erase these automatic banks. A future purge
must cover journal events/scopes, caches/outbox, Hindsight sources/derived data,
and retained backups with an explicit policy. Do not promise that removing a
page alone makes an automatically retained fact disappear permanently.

Corrections can be captured from later conversation and consolidated, but
contradiction resolution and long-term relationship quality remain model-dependent.
See [verification and acceptance](DUAL-MEMORY.md#verification).

## Historical TPS investigation — 19 September 2026

The timeout-only correction below was superseded by [controlled memory](CONTROLLED-MEMORY.md). It remains incident evidence, not current setup guidance.

The running IQ3_S Qwen model declares `qwen35.context_length=262144`.
The server reports two slots, each with `n_ctx=262144`, using total context
524288 and separate Q4 KV caches. This supports two concurrent contexts; it
does not establish full-window quality or equal single-request throughput.
No GPU, context, concurrency, cache precision or reasoning setting was changed.

The slow exchange contained no DSH subagent launch. Its memory check used
`memory_recall` directly. Separately, the Hindsight worker had started an
automatic `refresh_mental_model` operation before that question. The operation
repeatedly failed its 300-second wall deadline and was retried by the worker.
Within it, non-streaming `reflect_tool_call` requests hit the upstream
30-second per-call timeout, with four attempts per call. Logs show repeated
model cancellations and new approximately 40k-token prefills at these times.
Request attribution is based on worker stage, timeout and server cancellation
timing; the old logs lack a shared HTTP request ID.

For the measured foreground request, 41,681 prompt tokens took 15.057 seconds;
339 generated tokens took 18.258 seconds (18.57 TPS). Its observed generation
rate fell to 6.76 TPS during competing prefill and recovered to 75.10 TPS
afterwards. Breeze was not synthesizing during this particular slowdown.
There were no allocation failures in that interval or recorded GPU thermal
slowdown events in the inspected counters. This is evidence of prompt
processing contention aggravated by repeated cancelled work, not context overflow.

The installed server's batch builder places generating tokens first, then fills
the remaining logical batch with pending prompt tokens (default batch 2048).
A decode step therefore shares expensive prefill work; two slots do not provide
latency isolation. See the [upstream server documentation](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md).

The local Hindsight installer now explicitly sets
`HINDSIGHT_API_REFLECT_LLM_TIMEOUT=180` rather than inheriting 30 seconds.
This leaves the overall 300-second reflect wall deadline intact and allows a
healthy long-context response to finish without repeated premature retries.
Existing installations deliberately fail the installer's compatibility check
until explicitly migrated; running the installer must not falsely report that
an old container has acquired the new setting. Deployment and live outcome
are recorded below separately. This change does not itself provide foreground
priority or guarantee constant TPS during legitimate concurrent prefill.

Deployment: migrated only the memory container to the same pinned image and
existing named data volume, preserving all other environment settings, host
configuration and `unless-stopped` restart policy. The previous container is
retained stopped with restart disabled; its private inspect snapshot and
rollback name are under the local Augmentor backups directory. Foreground DSH
sessions were idle. Graceful shutdown returned unfinished background work to
the queue. Qwen and Breeze PIDs remained unchanged. Resolved runtime configuration
reports a 180-second reflection timeout and health is healthy.

Live verification: a memory call processed 24,331 prompt tokens in 7.672 seconds
and generated 7,629 tokens in 65.584 seconds (116.32 TPS), successfully continuing
past the old 30-second limit. During that generation a separate direct diagnostic
request processed 23 prompt tokens and generated 96 tokens at 92.80 TPS, with
1.105 seconds total client latency. It used no tools, memory writes or audio.
This proves simultaneous generation in the existing slots, not two fully
populated 262k contexts or representative conversation latency. The previously
failed project-summary operation was requeued through Hindsight's supported
retry API after applying the correction.

The first resumed memory-summary operation completed successfully in 118.314
seconds (three reflection iterations, four retrieval tool calls), and its
operation status became `completed`. The worker then advanced to queued retain
work. No reflection request timeout appeared before this successful completion.
The original project-summary retry remains queued behind existing work; do not
claim the entire backlog has drained. Long uncached prompts can still reduce
foreground generation speed through normal shared batching; scheduling/affinity
changes require separate measurement, not a GPU or context reduction.
