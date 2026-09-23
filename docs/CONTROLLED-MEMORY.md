<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Context selection and controlled memory processing

Implemented and qualified in source on `productization/shared-memory-and-desktop`.
Installed artifact identity and activation are recorded separately below.

## Intent

Preserve useful continuity without treating historical assistant offers as new
orders or treating a saved conversation as permission for unattended inference.
The original transcript stays intact. Capture, context assembly, retrieval and
derived-memory computation have independent responsibilities.

## Model input

The shared context assembler selects bounded excerpts relevant to the current
request, with a 6,000-character total ceiling. It does not inject complete
relationship pages, unrelated project excerpts or the shared-commitments page.
Legacy derived text is labeled as an unverified claim with unknown authorization.
Selection is local and deterministic; it does not add a foreground model call.

Direct user receipts from the current session are separate from derived memory.
They preserve source sequence, input mode and exact text. Assistant progress
messages cannot crowd them out of the journal query. Oversized receipts are
omitted visibly rather than cut at an arbitrary first-N-character boundary.
This bounded selection is not a guarantee of complete semantic scope tracking.
The original user messages remain the authority. Existing scoped authorization
persists across turns; an assistant offer cannot create it, and a vague request
to repair something does not automatically revoke an earlier restriction.

DSH neutralizes prior memory surface nodes using the supported session
surface API and inserts the latest snapshot beside the current request. The original log survives, including source links for replacements.
Earlier legacy memory nodes are neutralized individually without replacing user
or tool messages. Pi assembles its current memory contribution on each user
request. Historical branches retain their existing exclusion from fresh recall.

## Computation admission

Capture immediately journals committed public conversation events. Backfilled
history and reconnection do not authorize inference. A live-event flag alone
also does not suffice: the companion requires a trusted harness activity lease.
Only explicitly selected archive intervals become eligible for historical
processing; importing an interval does not itself grant a processing window.

Each user turn has a separate owner and an absolute 120-second window that
renewal cannot extend. Restart grants no activity; reboot invalidates old owners.
Leases expire after six seconds and
are renewed every two seconds only while the agent is executing. Foreground activity in any participating Augmentor session blocks memory.
External programs using the model endpoint are outside this lifecycle contract. Only known ordinary I/O tools open a
spare-compute window; delegated agents, voice generation and unknown tools stay
foreground. Stop, end of the turn, disposal and lost renewal close access.
An open idle window is not activity. Short tasks can finish with memory still
pending; current user receipts and cached recall remain usable.

Hindsight remains the extraction, consolidation and knowledge-page engine. Its
autonomous worker, consolidation reconciliation, scheduled refresh ticks and
startup model probes are disabled. Existing asynchronous queues remain stored.
A pinned HTTP extension executes only the selected durable stage; it does not
claim old queued operations. New facts carry an exact batch tag. Consolidation
selects only that tag, so a new message cannot drain older unconsolidated facts.
Observation scope stays shared within the bank, preserving useful continuity. Stable IDs and stored outcomes prevent a lost
acknowledgment or restart from silently replaying an unknown operation.

All generative calls use a separate loopback memory gateway. Chat and speech
continue using their existing models, endpoints and GPU settings. Without an
active processing window the gateway opens no model connection. It streams upstream and assembles the response for Hindsight; closing an
in-flight stream when admission ends cancels actual model generation. A live
non-streaming experiment failed this property, which the mock test had missed.

Initial conservative limits per source batch, shared across both scopes and
all stages/attempts:

- 120 seconds of model connection time;
- 65,536 total model tokens, conservatively reserved before sending;
- 45 seconds and 4,096 output tokens per model request;
- one model request at a time; failures stop rather than retry invisibly.

Reservations survive a companion crash. Known usage refunds unused capacity;
unknown outcomes retain their reservation. These are per-batch limits, not a
claimed household energy measurement or a daily power cap. The controlled engine limits page reflection to two iterations, 8,000 context
tokens and 1,200 source-fact tokens. These are memory-engine request limits,
not changes to the chat model’s context, precision, concurrency or GPU placement.

A separate processing pause preserves capture and cached recall. The existing
whole-memory switch still disables capture and recall. Resuming capture does
not implicitly undo a processing pause.

## Outcomes and failure handling

A returned HTTP call is insufficient evidence of success. Hindsight 0.10.0 can
return from consolidation after internally failing a model call, while its
public result omits the failed count. The extension checks the change in durable
bank failure counts before accepting the stage as completed. Missing pages,
failed stages and unknown outcomes stay visible; cached pages are preserved.

The gateway controls retries below the memory engine. A failed operation must
not receive a new budget merely because another stage or process starts.

## Qualification so far

- TypeScript check and build pass.
- Eight budget/gateway tests cover idle, Stop, competing foreground sessions,
  expired/crashed owners, durable charges and independent processing pause.
- Four context tests cover unrelated offers, explicit boundaries, reversal,
  bounded input and derived-claim labels.
- Ten Hindsight adapter tests cover archive opt-in, isolation, live-event
  admission, unknown outcomes and pause behavior.
- Real DSH/Pi lifecycle integration confirms one effective continuity snapshot,
  preserved audit history, text/voice capture and cached context after restart.
- Native regression: 407 tests pass with QtTest available in the test environment.
- Node regression: all 118 tests pass. An earlier Chromium temporary-profile
  cleanup race passed on isolated rerun and in the final full run.
- A disposable instance of the pinned Hindsight image starts with the controlled
  worker policy. A fixture model proves retention into both banks and a visible
  stop on consolidation failure, with no subsequent retry.

- Three real-model runs completed extraction, consolidation and both pages in
  61.36, 69.17 and 52.26 seconds. The final scoped run used 23,729 tokens and
  50.89 seconds of model-connection time. Facts from both scopes remained cached. This is a
  small synthetic usefulness check, not a population-level quality claim.
- Real Stop cancelled the model slot in 0.191 seconds with streaming upstream;
  both GPU utilization counters then read 0%. Transient power remained elevated
  while clocks settled; this is not a measured daily energy reduction.
- A forced page failure preserved its previous 902-character body. Repeating
  the identical operation returned its receipt with no extra model request.
- A fixture model failure stops after two batch retentions and failed
  consolidation; subsequent scheduler passes make no further calls. The
  reproducible proof also seeds one historical fact and checks that it remains
  pending after consolidation of the new batch.

The 407-test native run preceded the final added streaming-parser test; the
eight focused budget tests pass with that addition. Lifecycle integration was
rerun after the final admission-order correction. No private conversation text
belongs in these fixtures or in public documentation.

## Reproduce the real-engine checks

Use a disposable engine/volume and ports, with no production PostgreSQL instance
using the host-network image's embedded port. Stop the fixture before production
startup. The same pinned installer supports `--name`, `--volume`, `--port`,
`--gateway-port` and a separate `AUGMENTOR_SHARED_DATA` directory. Then run:

```sh
python3 scripts/proof-controlled-memory.py --configuration /absolute/fixture/hindsight.json
python3 scripts/proof-controlled-memory.py --configuration /absolute/fixture/hindsight.json --live
```

Default injects a model failure. `--live` uses the configured model and asserts
both cached fact scopes and completed pages. It creates only synthetic banks and
a temporary local journal. The proof refuses the default production ports.

## Limits and operational intent

A short tool window may close before a derived update can finish. Interrupted or
unknown writes stop for review instead of being assumed safe to replay. Original
transcripts, current-session receipts and cached facts remain available. Explicit
maintenance windows/imports/retries are documented in [operations](MEMORY-OPERATIONS.md).
Older memories are not silently reprocessed during installation.

The context selector is bounded lexical selection with source labels, not an
authorization classifier. It does not guarantee every older constraint is selected
or prevent a model from disregarding a visible restriction. Neither this change
nor a short synthetic proof establishes general task-completion reliability. The
[earlier task-execution plan](TASK-EXECUTION-HARNESS-PLAN.md) remains a separate
proposal; no new general task supervisor or universal semantic validator is claimed.

## Installed Linux activation — 21 September 2026

Source `edf7d76` (following `78b64ee`) is deployed in a compatible incremental
0.2.8 artifact, release `20260921-011742-0b89b31a`, SHA-256
`c995e9f93bed937af4d3d5bad658da734e66b0370cbd5757497cb2369b5503f9`.
The actual staged candidate passed the DSH/Pi lifecycle test before activation.
Desktop, mobile and secondary report that root, online, voice available and no
pending update. The primary conversation/model state file was byte-compared before and after;
named windows reopened using their own stored state.

The previous Hindsight container and a stopped-volume backup are retained. Its
replacement uses the same volume, pinned image and model endpoint with controlled
worker policy. All original journal records remain. Reconnection created zero
eligible imports, jobs or budgets; both GPUs returned to 0% utilization (about
14.46 W and 11.49 W at the sampled idle point). A subsequent idle companion
restart preserved capture/cache and granted no activity or model budget.

No model service, GPU placement, chat context/concurrency/precision or speech
configuration was changed. Browser recovery policy was preserved in a separate
artifact with only the read-only `memory_source` allowance added. See the
[deployment ledger](DESKTOP-DEPLOYMENTS.md) for compatibility and rollback scope.
