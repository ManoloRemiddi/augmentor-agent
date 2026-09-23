<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->
# Automatic relationship and project memory

The September 21 implementation separates capture, selected context and bounded
inference. See [controlled memory](CONTROLLED-MEMORY.md) for the current contract
and qualification. Earlier background-worker behavior is superseded.

Architecture selected with the user on 19 September 2026: reuse **Hindsight
0.10.0**, MIT licensed, for memory extraction, consolidation, knowledge pages and
semantic retrieval. Augmentor supplies transcript capture, identity routing,
reliable delivery and context injection. It does not implement another memory
reasoning engine or another conversational agent loop.

For status, troubleshooting, RPC methods, backup/rollback and erase limitations,
see [memory operations](MEMORY-OPERATIONS.md). For the current Git ref and
continuation steps, see [agent handoff](AGENT-HANDOFF.md).

## Two memories with different purposes

| Memory | Scope | Maintained representation | Retrieval |
| --- | --- | --- | --- |
| Relationship | Person | Extracted facts/observations and Preferences and boundaries page | Selected cached preferences; scoped semantic recall on demand |
| Work | Person + project | Hindsight extracted facts/observations, plus Current project state page | Hybrid vector, keyword, graph and time retrieval; current-state snapshot |

Each scope has a separate Hindsight bank. Bank IDs are deterministically derived
by trusted host code; the model cannot select another person's or project's bank.
Extraction missions distinguish interpersonal knowledge from project details.
Both banks receive source conversation events, but extract different knowledge.
This classification relies on the memory model and is not a hard content filter.
The physical bank boundary does enforce person/project retrieval separation.

A default local person UUID persists across sessions. Voice does not identify
speakers. Projects default to the canonical conversation working directory;
trusted `memory.dual.bind` can supply a stable project ID before first capture.
Names mentioned in a common workspace do not automatically create new projects.
The current UI assumes one person; it is not a multi-speaker recognition system.

Hindsight owns extracted facts, observations and page content. Augmentor controls
when each stage may run. Only Preferences and boundaries and Current project state
are refreshed automatically; legacy pages remain stored. Managed pages use full
refresh with a bounded evidence search, avoiding the additional model-edit loop
of incremental page updates. Pages do not consume one another as evidence.

## Automatic lifecycle

1. DSH/Pi capture committed human and assistant text with source IDs, speaker,
   mode, completion status, session and timestamp. Audio, images, reasoning and
   tool internals are excluded; successful spoken reply text is captured.
2. The companion immediately journals text locally. Reconnection/backfill captures
   history without authorizing inference. Historical imports must be explicit.
3. Live harness activity admits memory only during known ordinary I/O tools,
   within an absolute 120-second window per user turn. Foreground inference,
   Stop, idle and expired leases close admission. A shared durable budget covers
   extraction, consolidation, pages and any explicitly reviewed retry.
4. Facts and pages are cached. New requests receive relevant excerpts, direct
   current-session user receipts and provenance within 6,000 characters. No
   foreground memory LLM call is required. `memory_recall` searches bound banks;
   `memory_source` expands an original current-session receipt.

Historical assistant offers cannot grant permission. Existing user authorization
persists within its scope; corrections govern immediately, and vague repair
requests do not erase restrictions. This context design helps interpretation;
it does not mechanically prove arbitrary natural-language scope or task success.
Voice changes response register, not identity or permission. Historical branches
retain their exclusion from newly recalled memory.

The companion can stay running, but an idle open window is not activity and it
cannot drain a backlog after chat ends or after a restart. Hindsight's autonomous
worker/reconciliation/ticks are disabled. Cached recall remains usable during a
separate processing pause. Short tasks may leave derived memory pending.

## Storage, migration and failure handling

- `~/.local/share/augmentor/dual-memory.sqlite3`: original events, session scopes,
  eligibility, stage receipts, budgets and a disposable read cache. Mode 0600, unencrypted.
- `~/.local/share/augmentor/hindsight.json`: local engine destination, version and
  image pin and private gateway credential. Mode 0600; never publish this file.
- Docker volume `augmentor-hindsight-data`: Hindsight's PostgreSQL/pgvector data,
  original documents, extracted facts, observations and pages.
- `~/.local/state/augmentor/dual-memory.sock`: private same-user RPC boundary.

The former custom summarizer and autonomous outbox paths are retired. Their
records remain for rollback. Existing Hindsight queues are preserved but never
claimed by the controlled scheduler. No archive import is implicit.

Stable batch/stage and document IDs preserve identity across lost acknowledgments.
Unknown or failed outcomes stop visibly; they are not automatically replayed.
One explicitly reviewed retry uses the original remaining budget. Exhaustion
requires investigation, not an automatic budget reset. A failed page retains its
previous content; successfully consolidated facts are cached before page refresh.
Changing the engine URL still requires explicit data migration.

The whole-memory pause blocks capture and recall and also pauses processing.
Skipped IDs are retained without text so reconnection cannot backfill them.
The separate processing pause preserves capture and cached recall. Resuming the
whole-memory switch does not implicitly resume processing.

Back up both the SQLite journal and the PostgreSQL volume. The journal can rebuild
memory, but restoring the engine database also preserves its derived history.
Stop the Hindsight container for a consistent volume copy, or use PostgreSQL backup
tooling. Retain backups during upgrades and never remove the data volume as part
of a routine reinstall.

## Local setup and deployment

The tested Linux deployment is **Hindsight 0.10.0**, upstream commit
`5d46f9c8c8eb4fb96f549aa63abe1191b82a7840`, Docker image digest
`sha256:3edcb6165cefdeaa6721dd0fce43cfd13b7a9c346ce0d2c5f4b4bf7bc3c8ac0b`.
Its API uses numeric loopback port 8889; the private gateway uses port 8890. CPU embeddings and reranking use
Hindsight's bundled models; all generative stages pass through a memory-only gateway.
The local memory model is explicitly configured separately from each chat model.
The installer does not change chat selection, GPU placement or model-server settings.
Memory processing still shares inference capacity with chats using that endpoint.

```sh
python3 scripts/setup-hindsight.py \
  --model-url http://127.0.0.1:8080/v1 --model YOUR_EXISTING_LOCAL_MODEL_ID
npm run build
# Stage and activate a compatible artifact using augmentor-update; see link below.
```

The setup helper requires Docker and an existing local compatible model. It
refuses to replace a running mismatched engine. `--replace-stopped` first backs
up its data and preserves the former container, then starts the controlled
configuration using the same volume. Startup grants no processing window.

Use [desktop deployments](DESKTOP-DEPLOYMENTS.md) for compatible, separately staged
artifacts and matching DSH adapters. The historical preview mutation helper is
not the managed update path. No model/speech service or GPU setting is replaced.

Fresh source installations preserve transcripts while awaiting engine setup;
there is no hidden fallback to the retired custom summarizer. The optional manual
Hindsight library remains separately configured; its legacy 0.9.2 connection is
not silently redirected into these automatic banks.

## Verification

- `tests/test_hindsight_memory.py`: archive opt-in, source/bank isolation, failed
  stages, original-budget retry, fact cache, page policy and pause behavior.
- `tests/test_memory_budget.py`: activity, crash/reboot, shared budgets, streaming
  tool fragments, cancellation and processing pause.
- `tests/memory-context.test.mjs`: offers, constraints, explicit reversal, source
  omission and bounded context.
- `tests/dual-memory-integration.test.mjs`: real DSH/Pi adapters with explicitly
  labelled fixture engines, text/voice capture and one effective context snapshot.
- `scripts/proof-controlled-memory.py`: opt-in disposable pinned-engine proof;
  default fixture model injects a failure, `--live` uses the existing model within
  the normal budget. See [the controlled guide](CONTROLLED-MEMORY.md).
- `scripts/hindsight-proof.py` records the former autonomous-worker proof and
  is not the current controlled-processing acceptance entrypoint.

A two-session human microphone/speaker trial remains the acceptance check for
recognition quality and how continuity feels. Automated text and audio fixtures do
not establish acoustic interruption quality or conversational latency.

Upstream: [MIT license](https://github.com/vectorize-io/hindsight/blob/v0.10.0/LICENSE),
[versioned API](https://github.com/vectorize-io/hindsight/blob/v0.10.0/hindsight-docs/static/openapi.json),
[knowledge pages](https://hindsight.vectorize.io/developer/knowledge-pages),
[retrieval](https://hindsight.vectorize.io/developer/retrieval).
