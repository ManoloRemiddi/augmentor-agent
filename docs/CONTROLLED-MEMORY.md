<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Context selection and controlled memory processing

Current Pi qualification is recorded below on `feat/augmentor-harness`.
Earlier `productization/shared-memory-and-desktop` and installed artifact evidence
are historical checkpoints; source qualification does not activate an installed build.

## Actual Pi memory boundaries and unfinished pages — October 14

Implementation **1b69cc79d045c0a7bcc6861fbae2ae38d45d8ec6** fixes a failure
observed with the actual controlled Hindsight **0.10.0** engine: its unfinished
page body was `Generating content...\n`, while the existing exclusion matched
only the marker without whitespace. New snapshots and cached recall now exclude
that whole marker, including surrounding whitespace. Real page text remains
unchanged, including text that merely mentions the marker. Reading an older
cache does not rewrite it, contact the engine, reset budgets or retry processing;
independently extracted facts and new transcript capture remain available.
This changes the shared Python memory service on every platform, with Linux
live evidence and common tests; actual macOS/Windows engine/transport acceptance
remains separate. There is no UI, SDK/dependency, schema or model-setting change.

The isolated Linux proof uses a real managed Pi Host/AgentSession, the actual
shared memory companion and the independently owned engine described in the
next section. It has fresh synthetic conversation identities and a private
test journal/person/project, rather than an owner profile or production bank.
Its final sequence completes in **92.57 seconds**:

- Cached SQLite/project and concise-reply facts survive an earlier stopped page
  stage. Managed recall reaches the recorded SDK system context and provider
  body with exact-text presence. The unfinished page marker is absent.
- Pi captures the new user/assistant pair through its normal committed-event
  path. A separate synthetic source then changes Atlas to PostgreSQL through
  real Qwen extraction, consolidation and page generation. This new job completes
  all six stages at attempt zero, with **41.29 seconds / 40,852 tokens** remaining
  in the unchanged budget. The same parent AgentSession sees the updated facts.
- A branch at the first assistant boundary skips current memory recall, retains
  SQLite conversation evidence and excludes PostgreSQL/later parent messages
  from its recorded provider body. The parent native file is unchanged. Only
  the branch's new user/assistant pair is captured; inherited events are excluded.
- Cold history inspection preserves both native files byte-for-byte, creates
  no AgentSession/inference and leaves the exported memory journal unchanged.

The original synthetic job remains stopped at phase four with
`APITimeoutError`, attempt zero and **35.15 seconds / 36,271 tokens** remaining.
It is not retried or relabelled completed. Later page success does not establish
the cause or reliability of that earlier timeout. One intermediate probe also
failed because it parsed only the first 64-KiB observation page; the final probe
assembles the existing UTF-8 cursor pages. That was a qualification-driver error,
not evidence of corrupt stored context. Original failed attempts are retained
locally; credentials, transcripts and private URLs are excluded from publication.

To reproduce the boundaries, use a separate engine/data volume and the recipe
below; create separate shared state/data and Pi configuration/workspace paths,
with only that fixture's configuration. Start the normal shared memory service,
configure a synthetic person, bind a synthetic source and append one live user
record under its renewable tool-window lease. Pause processing after completed
fact extraction. Start the normal Host with the explicit existing local Qwen
model, read-only policy and payload capture; inspect `context/provenance` through
all payload cursor pages. Use the normal committed transcript/export APIs to
count captures. Derive the new fact under a different source lease, pause again,
and prompt the same parent owner. Branch through `session.branch` at the earlier
assistant sequence; compare recorded context, exact native bytes, exported
events and cold `session.history` inspection. Stop only the independently owned
companion/container after its work settles. Preserve absolute windows, request
limits, stopped receipts and Qwen/voice configuration throughout.

Validation: **37/37** common Python memory/provider/journal/budget cases, including
two new unfinished-page regressions; **12/12** Node context/client/provenance
cases, no skips. The twelve-case Hindsight focus is a subset of the Python total.
The live proof uses current Qwen and unchanged CPU ASR/VAD/GPU placement; voice
health is checked without recording or claiming physical speech acceptance.
The fixture is stopped with restart policy `no`; synthetic evidence is retained.
Production Qwen/Breeze/Resonant Voice/Hindsight remain healthy. Installed preview,
unsent draft, immutable candidate and manual-feedback profile are not updated.

This qualifies those source Pi boundaries, including recall from a stopped
projection. It does not establish exact replay of an earlier recalled system
brief: branches deliberately skip current managed memory. Full historical memory
snapshot fidelity, semantic quality, broader failures/concurrency, person/project
migration, physical voice, sealed/installed adoption and cross-platform/public
distribution remain required. Latest full CI acceptance is also separate; see
[retained GUI failures](HARNESS-PLUGIN-PARITY.md#ci-readiness-barriers-and-retained-failures--october-14).

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

## Isolated current-Qwen engine qualification — October 14

At source **ada6e4378093bf50613e07b6f35702fbab6a24c0**, the existing public
`proof-controlled-memory.py` passes both the deliberate-failure and live-model
checks through a disposable Hindsight **0.10.0** engine, pinned image
**3edcb6165cefdeaa6721dd0fce43cfd13b7a9c346ce0d2c5f4b4bf7bc3c8ac0b**.
The mounted authored extension is byte-identical to current source, SHA-256
**f301dccab0c2874eb66c8f9f2b344ef553a7f05f78aa99e441730803c232d092**.
Separate container/data volume and API/gateway/database ports prevent access to
production PostgreSQL and journals. The engine reports the controlled protocol,
worker disabled, zero reconciliation and zero LLM retries. Its restart policy is
`no`; no production engine, model/speech configuration or user data is changed.

The fake-model check makes exactly four calls, stops the failed operation for
review with zero retries and retains the unrelated old fact. The live check uses
current **Qwen3.8-27B-GSQ-RCO-IQ3_S-mtp-262k** through its existing loopback endpoint.
It completes all six stages in **75.42 seconds**, with **45.97 seconds** and
**39,883 tokens** remaining in the original job budget, zero failures and attempt
zero. Both relationship/project scopes have cached facts and completed summaries/
pages. The input is one independently authored synthetic text record; it includes
communication preference, project fact and a restriction, rather than private
owner conversation or audio. Stop closes the activity lease; subsequent steps
do not submit new work. Processing limits and model context/concurrency/precision/
GPU placement are unchanged.

This qualifies the actual controlled Hindsight/gateway/current-Qwen engine layer.
It does **not** qualify automatic Pi capture/recall/branch cutoff, actual person/
project migration, semantic relationship quality, physical ASR/TTS or all OS
memory transports. The temporary proof journal is disposable. The stopped test
container/labelled synthetic volume and metadata logs are retained privately for
follow-up; production Hindsight and Qwen still report healthy. The installed
97897cf preview, owner draft, 454db9d immutable candidate and manual feedback
profile are untouched. The full migration remains open.

A production engine can remain online for this fixture when the pinned engine is
explicitly configured with a different embedded PostgreSQL port. The inspected
0.10.0 `parse_pg0_url` supports `pg0://instance-name:port`. This proof uses Docker
environment `HINDSIGHT_API_DATABASE_URL=pg0://hindsight:18442`, separate API/gateway
18440/18441, a new labelled container/volume, the cached exact image, the same
`setup-hindsight.environment` policy and a read-only preferred-source extension
mount. Ports must be unused, and the container/volume must be new. No installer
or production descriptor is rewritten. The older default-port recipe below still
requires avoiding a production embedded-port collision. Stop only the exact
owned fixture after verifying its container identity/label and confirming its
proof handle is terminal; retain its data if further inspection is needed.

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


## Codex development boundary

The [Codex memory foundation](CODEX-INTEGRATION.md#memory-capture-foundation-and-context-api-qualification)
provides a tested adapter for committed transcript capture and separate live
activity; it is not activated in the host yet. Codex's pinned additional-context
API appends historical fragments rather than replacing them. Full integration
must resolve context lifecycle, compaction/fork exclusions, host wiring and
settings before claiming the shared memory contract. Existing DSH/Pi behavior,
companion budgets and installed data are unchanged.
