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


## Opt-in upstream refresh-budget backport — October 16

Upstream [022583d43b3ae460233c9df880040c0770f24e0b](https://github.com/vectorize-io/hindsight/commit/022583d43b3ae460233c9df880040c0770f24e0b)
fixes this exact document-refresh default: refresh selects MID explicitly, which
uses the configured iteration count. The isolated proof can now select a small
backport with **`--refresh-budget-backport`**. The global configured maximum stays
**two**; the refreshed page can retrieve on its first iteration and synthesize on
its second. This changes the faulty operation default from half of the configured
allowance to the configured allowance. Overall 120-second/65,536-token job,
45-second/4,096-output per-call, 8,000-context Reflect and single-request limits
remain unchanged, as do retries/thinking/model/server/GPU settings.

Only three budget-related hunks are selected from that MIT fix. The pinned image's
1,087,129-byte public engine file is verified byte-for-byte against upstream base
**5d46f9c8c8eb4fb96f549aa63abe1191b82a7840**, Git blob
**df43b37f0093fb5d3c3037858126620f9e5b4790**. The exact MIT licence and a source/
adaptation manifest accompany the 1,437-byte patch under
[`services/memory/vendor/hindsight-refresh-budget`](../services/memory/vendor/hindsight-refresh-budget/SOURCE.json).
The expected source/patch/licence/output digests must match; a separate output is
compiled and mounted read-only into only the new proof container. The original
container/file, production installer, data and every existing review remain
unchanged. Other upstream API/UI/CLI/schema/default-option changes are not selected.
No network download is needed when applying the already reviewed backport.

The actual exact-source application/compilation check passes. Common Python now
passes **43/43**, including refusal before writing an unknown base and rejection of
changed supplier/overlay inputs. Fresh frozen and actual-engine qualification
remain required; the earlier failed/default proof is preserved. This is an opt-in
Linux proof candidate; installed adoption and Mac/Windows transport remain gates.

## First backport live result and concise page candidate

Frozen **3af7f3c62480bcc1f30aa0d5ae49df6addaada87** source/fresh ordinary pass
**43 Python / 30 shared Node** cases without skips, changed bounds or workers;
12 public source/licence cases also pass. The first attempted preparation process
is observed terminal before any engine record, container or cache was created;
its empty log/private marker remain. A fresh preparation is observed healthy and
then used once. This preparation failure is not live model evidence.

The actual default-mode backport run verifies a read-only overlay and reaches a
correct relationship page containing the synthetic calm preference. Reflect now
records **two iterations and one observation-retrieval tool**, proving the missing
retrieval is corrected. It spends 47.10 seconds on that page (including a 10.24
second length rewrite). The subsequent work-page model call stops at the original
absolute tool-window deadline: the persisted deadline maps to 01:39:51.880 UTC and
its gateway refusal is logged at 01:39:51.937 UTC. The job remains **stopped at phase
five**, nine admitted calls, zero budget failure charges, 7.21 job seconds/16,640
tokens left. This is **failed full acceptance**, despite the first corrected page.
No stage/window retry or limit extension occurs; all owned actors/engine terminate
and the private database/cache/failure log remain.

The next authored page policy asks for a compact factual note of at most 120 words,
omitting empty categories, generic advice and boilerplate while preserving
corrections/uncertainty. This makes the existing 768-token page target explicit in
the topic prompt, without changing any provider/output/time/context/token limit.
Policy revision **three** updates only managed page queries/options during normal
admitted preparation; page IDs and prior content stay until the normal refresh.
A migration case starts from revision two and verifies both page identity/content
retention and the new revision/query. Source Python remains **43/43**. Frozen/live
qualification of this concise policy remains next; no performance pass is inferred
from a shorter instruction.

## Concise-policy live result and outage observation correction

Frozen **a8f49ced0a86ec6256cc129e058815d59679593b** source/fresh ordinary pass
43 Python/30 shared Node cases. Both actual default-Qwen memory batches finish
all six stages without retries/failures: seed **eight calls**, 46.08 job seconds /
30,094 tokens remaining; correction **ten calls**, 24.41 seconds / 19,748 tokens
remaining. Both pages contain the expected facts. The first relationship page
now takes 8.20 seconds with no length rewrite, versus the prior run's 47.10 seconds;
these are two recorded live outcomes, not a general performance guarantee.

Actual fresh recall/provider/native brief and answer, person/project isolation,
PostgreSQL correction/new-conversation recall, exact historical SQLite brief with
no fresh recall or parent mutation, cold Pi/memory restart and paused capture/
recall with ordinary chat all pass. During the final memory outage ordinary chat
also succeeds, using one provider request and an empty managed brief. The proof
then fails immediately on **`Memory session is not bound`** after the memory
companion restarts. It has not yet proved durable recovery or completed acceptance.
All ten conversation requests and owned process/engine cleanup remain recorded.

The application already retries pending transcript capture after five seconds.
Socket readiness can therefore precede binding the newly created outage session.
The external proof now treats only that exact unbound-session read as a pending
observation within its unchanged **15-second** recovery bound. It never issues a
fixture bind, writes/retries a memory stage, replays a model/tool action or suppresses
another error. Required recovery remains exactly two source events and no extra
provider request. Application/runtime/compiled bytes and all earlier assertions
are unchanged. A new independent client case exercises the real existing timer:
it observes a healthy-but-unbound service, then one bind/append and exactly two
original source texts, without inference or duplicate capture. Source shared Node
now passes **31/31**; fresh frozen/live follow-up remains required.

## Unchanged-runtime rerun and focused outage case

Frozen application/external driver **03fb703958b161fc491498f510dd7e59d689dadf**
keeps the concise application's runtime bytes unchanged. Fresh ordinary passes
43 Python/31 Node, with source Node 31 and unchanged Python runtime/tests already
qualified. The full live rerun passes seed/fresh recall/isolation, then stops the
correction at phase five: its work-page gateway failure (01:56:03.820 UTC) follows
the persisted absolute-window deadline (01:56:03.803 UTC). Its remaining job budget
is 6.87 seconds/zero tokens, ten calls and zero failure charges. All owned actors/
engine terminate. The earlier complete correction/branch/restart/pause passes and
the first outage observation failure remain valid; this rerun does not close full
default-mode timing or exercise the corrected recovery observation.

A separate **`--scenario outage`** selection now exercises actual Pi/Qwen ordinary
chat while its actual memory companion is stopped, then source capture recovery.
It uses fresh state, paused memory inference, one conversational request and zero
SDK tools; all original outage assertions and the 15-second recovery observation
bound remain. The default **`full`** selection still requires every seed/update/
branch/restart/pause/outage assertion. A focused outage result cannot replace a
failed full scenario. This external-driver addition changes no application code,
page policy, inference limit or production/installed state. Focused live evidence
remains required. [Portable retained results](../release/harness-pi-memory-page-qualification-20261016.json).

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
