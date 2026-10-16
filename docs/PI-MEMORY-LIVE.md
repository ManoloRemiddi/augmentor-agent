<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Actual Pi memory qualification and gateway settlement

This work exercises the existing controlled memory architecture with the actual
Pi Host/SDK, shared prompt/memory companions, pinned Hindsight 0.10.0 and the
configured local Qwen provider. It does not introduce another conversational
owner or change the original DSH GUI. [Controlled memory](CONTROLLED-MEMORY.md)
owns the budgets, source selection, previous optional thinking-mode evidence and
production deployment boundaries.

## October 16 sequential-request race

The first new isolated proof reaches a real SDK-held tool window and retains
synthetic source text in both relationship/work banks. At consolidation phase
three it stops with a durable failed job: Hindsight receives the gateway's
`429 A memory model request is already active`. No memory-stage retry or budget
extension is attempted. All owned Pi/prompt/memory actors and its separate
Hindsight container stop cleanly; the private database and failure logs remain.
This is **failed live qualification**, not proof that the requested recall,
restart, historical branch, pause or outage scenarios passed.

The gateway wrote its successful HTTP body before its `finally` block closed the
upstream response/connection, settled the durable budget and released the single
request guard. Hindsight can read that body and begin its next sequential stage
while the old handler still owns the guard. The actual initial failed job and
real-HTTP controlled settlement test reproduce this boundary. That new test fails
against the preceding implementation: confirmation escapes a held settlement.

The candidate now prepares the response, joins its cancellation watcher, closes
the response/connection, settles once and releases the guard **before** sending
confirmation. Cleanup attempts remain independent, and a cleanup/settlement
failure returns failure without permanently stranding the guard. The already
durable reservation remains charged on an unconfirmed settlement. A genuinely
overlapping request is still refused; serialization is not weakened. The model
request is never replayed.

Existing 45-second per-call, 120-second job/absolute-window, 65,536-token job and
4,096-token per-call output budgets remain unchanged. No model context,
concurrency, precision, GPU placement, default thinking choice, retry policy,
active workload or installed service is changed to obtain a result. The existing
source/fresh-ordinary memory and native-snapshot evidence remains separately
dated. The combined frozen/live result below qualifies these ownership fixes but
retains failed page-semantic acceptance.

## October 16 status and settlement lock order

A second fresh application copy includes only the gateway fix. It no longer
records the spurious 429, but the default-mode live job still stops during phase
three, with one failed call and 84.26 seconds remaining. This remains a failed
proof; no later recall/branch scenario is credited. Its actors and separate
engine join cleanly and original services remain unchanged.

Investigation also finds that `describe` opened a journal transaction and called
bank discovery, which writes, before reading processing/budget status. Settlement
holds the budget lock before writing the journal. Concurrent status and settlement
could therefore wait on each other's locks. A deterministic independent SQLite
writer probe fails against the preceding status implementation with `database is
locked`; the corrected status reads processing before opening its read-only
journal observation. Status no longer discovers or writes bank rows. Actual
recall and processing retain their existing discovery behavior.

The test establishes the lock inversion, without claiming it explains every
elapsed second or the entire second live failure. Both source fixes together pass
**41/41 focused Python cases**: budget/gateway HTTP ownership, Hindsight status,
capture/scoping, isolated proof boundaries and setup compatibility. No test
workers, runtime budgets or live request settings change. The combined frozen
qualification below supersedes the pending follow-up, preserving both failures.

## Combined frozen qualification — October 16

At **934a280eb752347e28f01719968aa22520fdfd94**, source and a fresh ordinary
application each pass **41/41 Python** and **30/30 shared Node memory/SDK cases**,
without skips, changed bounds or worker counts (Node remains two). The fresh
application comes from that exact Git archive; all **3,395 tracked inputs**,
**1,060 compiled inputs**, one Node executable and **20,702 dependency file/link
inputs** remain unchanged after testing/live use. Twelve additional public
source/licence/nested-notice boundary cases pass. No GUI, SDK/dependency pin or
compiled JavaScript is changed by these Python service fixes.

The third fresh actual Pi/Hindsight/default-Qwen proof completes **all six seed
stages**, six model calls and **zero model-call failures**, with **47.82 seconds /
39,078 tokens** left. It no longer stops at phase three. However, the strict proof
still **fails** its required page semantics: two relationship and three work
claims include the expected synthetic preference/database, while both nonempty,
reported-fresh pages say no evidence was retrieved. The proof times out at its
unchanged assertion bound. Fresh conversation recall, correction, historical
branch, cold restart, pause and outage are **not reached** and are not credited.

Inspection of the exact pinned public engine explains the retrieval gap. Page
refresh invokes Reflect without an explicit budget; its LOW default halves the
configured two iterations to one. The agent's final iteration removes tools,
so the first iteration becomes a forced answer with no bank retrieval. Actual
logs confirm both pages use one iteration and **zero tool calls**, despite
successful consolidation/recall of observations. No engine source/configuration,
iteration/token/time allowance, request thinking choice, retry or model setting
is changed to bypass this gate. Evidence-bearing page generation within the
accepted processing policy remains work. Earlier separately dated optional-mode
proofs do not qualify this fresh default-mode candidate.

All owned Pi/prompt/memory actors and the third labelled engine are terminal;
the private database/cache and raw failures remain outside Git. Its 43 public
cache inputs and original memory engine identity/health verify unchanged. Postflight
also verifies eleven sealed inventories, twelve existing review owners plus the
separate recognition owner, selected installation, 38 canonical/four original
private changes and six model/service configuration hashes. The MX microphone
review remains unchanged and available. These fixes are source/fresh-copy work,
not an installed update or a whole-Harness completion claim.

[Portable acceptance and retained failure metadata](../release/harness-pi-memory-settlement-20261016.json).

Reproduce the common cases from either the source tree or its fresh ordinary copy:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tests python3 -m unittest -v \
  test_memory_budget test_hindsight_memory test_hindsight_isolated_proof \
  test_dual_memory test_hindsight_setup
node --test --test-concurrency=2 tests/memory-client.test.mjs \
  tests/memory-context.test.mjs tests/pi-memory-snapshot.test.mjs \
  tests/pi-input-mode.test.mjs tests/pi-context-provenance.test.mjs \
  tests/pi-mcp-options-memory.test.mjs
```


## Isolated proof ownership

[`hindsight-isolated-proof-engine.py`](../scripts/hindsight-isolated-proof-engine.py)
explicitly prepares a separate labelled container, new PostgreSQL volume and
API/gateway/database ports. It uses the already installed exact image by digest
with `--pull=never`, CPU embeddings/reranking, disabled autonomous processing,
offline model loading and telemetry opt-outs. Only the two declared public model
cache directories are copied from the existing container into private proof
storage and mounted read-only. Owner databases, banks, credentials and source
extension code are not copied. The HTTP extension comes from this public source.
The original container's immutable identity/configuration digest is checked
before/after; no original container is stopped, reconfigured or replaced.

The helper preserves the existing memory-only default/off request choice rather
than silently selecting the faster option. Its three pure input/ownership cases
exercise local provider/unchanged limits, forbidden credentials/cache link escape
and refusal to manage a changed container identity. The first engine's pg0 auto
allocator selected its own 5433 instance on a fresh volume; new preparation also
sets an explicit separate PostgreSQL port for auditable isolation.

[`harness-live-memory-proof.mjs`](../scripts/harness-live-memory-proof.mjs) owns
fresh home/config/journal/workspace/socket state and actual Pi/prompt/memory
processes. A transparent local memory-protocol observer records method/session
identities; the provider observer records only this proof's synthetic requests
inside private output. It runs the original SDK lifecycle with an independently
authored held tool, with no physical browser action. It requires actual automatic
retain/consolidate/page results, then tests fresh recall, person/project isolation,
a corrected current fact, exact historical native brief, cold owner/memory
restart, capture pause and ordinary chat during/recovering from memory outage.
It verifies original provider context, native receipts, tool execution counts and
no model/tool replay. These are required assertions, not inferred from an engine
health response or nonempty page. Physical voice remains separate.

The final report also refuses success and returns a failing exit status if any
owned cleanup fails or an actor/engine is not terminal, even after assertions pass.
This reporting-only follow-up does not rerun or relabel the failed frozen proof.

Failures keep their records and stop the owned actors. Stopped memory jobs are
never automatically retried or relabelled; new experiments use fresh proof state.
The private stopped container/database/cache are retained for investigation. A
fresh proof directory must be outside the immutable application, mode 0700, with
its `proof-owner.json` marker. Its provider file accepts only an unauthenticated
numeric-loopback declaration and the unchanged 262144/8192 model limits.

```sh
python3 scripts/hindsight-isolated-proof-engine.py prepare \
  --root /absolute/private-proof-directory \
  --provider-json /absolute/local-provider-declaration.json
node scripts/harness-live-memory-proof.mjs \
  --app /absolute/frozen-application --python /absolute/python \
  --provider-json /absolute/local-provider-declaration.json \
  --engine-root /absolute/private-proof-directory
```

These commands are opt-in live tests, not installation or automatic CI. They
create no owner conversation, change no selected review and publish no transcript,
model weights, private configuration or token. The broader Harness migration,
production memory adoption, default-mode performance/semantics, physical speech
and platform/distribution acceptance remain open.
