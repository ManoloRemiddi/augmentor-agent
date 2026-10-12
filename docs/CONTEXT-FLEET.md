<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Original Fleet migration: recorded family identities

The next original dsh-context view needs a trustworthy parent/worker catalogue.
Pi's ordinary conversation forks are historical branches, while bounded jobs
have separate saved delegation identities and native histories. `session.family`
reads the selected parent's retained job catalogue without loading an
AgentSession, dispatching work, probing a provider or accounting usage. This is
the data foundation for the original Agent network/Fleet view; that GUI remains
unregistered and its preference remains disabled until its data and detail
bindings qualify. The installed original Context/sidebar preview remains the
separately recorded [Context sidebar runtime](CONTEXT-SIDEBAR.md).

## Read contract and scope

The request is `{sessionId}`. The response has `available`, `scope`, `items` and
`coverage`; an inaccessible/invalid saved job catalogue returns unavailable,
empty items and null coverage. This does not represent an empty family.

The available response includes the actual parent and only direct delegated
agent or desktop specialist children whose job receipt and saved metadata agree
on child ID, parent ID and job ID. Shell jobs, ordinary forks, missing or
contradictory identities, duplicate links and unknown state vocabularies never
become agent rows. Delegated workers cannot query another family or obtain parent
control through this method. The managed runtime currently forbids recursive
delegation; no speculative ancestor tree is invented.

Parent rows expose their selected conversation identity, bounded title, cwd,
own running flag and saved update stamp. Child rows expose their ID, parent/job
IDs, job kind, bounded title, durable reported state/update stamp, reported
request/tool/output-token tallies and two independent flags: usage recorded by
the producer, and usage accounted once in the parent. Titles longer than 512
characters carry `titleTruncated`; unreported/invalid counters are null, never
an inferred zero. Recovered job state overrides stale child metadata's running
flag. No prompt, task body, result text, raw usage object, credentials, resource
grants or private configuration is included in these identity rows.

Coverage distinguishes retained jobs, agent jobs, verified children, pending
children without an identity yet and unavailable child identities. It does not
claim complete historical discovery: explicitly removed job receipts are not
rediscovered from another conversation or arbitrary native files. `completed`
is a durable producer disposition, not verification of the task's effect.
Failed/cancelled/unknown states remain explicit. Reading cannot force an
unpersisted parent's pending usage attribution to become confirmed.

The existing Harness operator bearer exposes this read. A read-only inspector
can query only its bound parent, just as its existing parent-owned job and child
original reads do; a foreign parent, a direct child catalogue and a missing
scope are refused before Host dispatch. This grants no mutation, worker prompt,
file-preview, private profile or approval-presenter authority. Native IPC uses
the existing authenticated Host contract. Existing exact-parent job detail,
native original and provider-observation routes remain distinct.

## Evidence and remaining work

The independently authored public SDK fixture runs two actual bounded workers
under distinct parents and creates an actual native branch. Family reads then
verify the correct direct child, exclusion of the foreign worker and ordinary
branch, exact inspector isolation, unchanged provider request count and unchanged
parent/child native originals. A cold Host reads the same metadata without
inference. Deliberately contradictory child metadata is withheld after restart;
the read does not repair or resume it. A pure hostile-input case verifies both
authorities, unknown dispositions, invalid counters and inaccessible catalogues.

The first integration fixture wrongly required attributed usage in the foreign
parent that had no persisted assistant history, then used the outer history row
instead of its event's seq for branching. The corrected fixture waits for the
actual producer settlements and the owned parent's durable attribution, checks
the foreign flag as reported without forcing it, and uses the actual event
anchor. Deadlines, two-worker scheduling and product accounting are unchanged.

Source check/build and focused checks pass **6/6 across three files** on Linux,
using Node 24.19.0 and prepared QtTest. The wider source cohort passes **280/280 across 50 files**, zero failures,
skips or cancellations, with the same two workers and unchanged deadlines. Fresh
ordinary evidence must qualify separately. No installed promotion or original Fleet GUI acceptance
is established by this data contract. No supplier source, CSS, licence or
dependency changes are needed here; authored code retains its existing licence.

The next binding must execute the original Fleet tab registration and view,
scope its original head/detail caches by Host/role/parent, and read worker
originals only through the verified parent/job relationship. It must preserve
the original graph/inspector/list/comms presentation and keep absent Team and
mailbox semantics visibly unavailable. It must not turn historical branches
into workers, double-count parent-attributed usage, infer successful effects or
replay a worker to backfill the view. Source, ordinary, installed MX and live
other-platform acceptance remain separate. Full Harness migration and DSH
retention remain binding; further platform implementation stays deferred for
MX feedback.

To reproduce after the normal build with Node 24.19.0 and `AUGMENTOR_PYTHON`
pointing to the prepared PySide6/QtTest interpreter:

```sh
node --test --test-concurrency=2 tests/session-family.test.mjs tests/pi-session-family.test.mjs tests/harness-server.test.mjs
```

The wider cohort is the [48-file Context/sidebar qualification
recipe](CONTEXT-SIDEBAR.md#reproduce-the-public-fixture-checks), with these two
new family tests appended. Ordinary runs use the assembly's bundled Node and
`AUGMENTOR_PI_TEST_ROOT` pointing to that assembly. These synthetic fixtures do
not contain private owner source or conversation contents.
