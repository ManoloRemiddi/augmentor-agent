<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Nested tools in the original DSH interface

The source adapter connects Pi's public nested tool events to the copied DSH
Trajectory's existing **SUBTOOL** rows. A running parent carries both settled and
pending children; its final result retains their argument/result trees. Nested
results appear once in that tree. The original renderer, layout, inspector, CSS,
580 MIT GUI records and 108 Apache-2.0 dsh-context records remain unchanged.
Source, ordinary artifact and installed acceptance are distinct qualifications.

## SDK ownership and boundaries

One existing `AgentSession.subscribe` observes `tool_execution_start` and
`tool_execution_end`, including the SDK's explicit `parentToolCallId`. The Host
retains the same recorded request/message capture identities used for root calls.
This adds no tool, agent loop, permission decision, execution hook or dispatch.

**A start is entry into the SDK tool pipeline, before validation and approval.**
Its arguments are the public start-event input, not a promise of effective
post-hook executor input or a completed operation. The original Started seat
reflects that observed pipeline boundary. Approved `tool/dispatch` receipts,
native originals, SDK results and verification of effects remain separate.
Measured start/end intervals can include validation, approval and nested waits;
they are not executor-only benchmarks. Missing or ambiguous clocks remain unknown.

A child joins only a preceding active parent in the same Host turn and recorded
request/message scope. SDK IDs remain unchanged in saved records; internal view
IDs remain scoped as in [streamed arguments](TRAJECTORY-TOOL-ARGUMENTS.md).
Slash spelling is never evidence of a parent. Legal SDK child IDs can extend a
256-character provider root, so the recorded tool-ID boundary allows 4096
characters while request/capture identities keep their existing limits. Parent
ordering prevents cycles, and the presentation depth is bounded to 256.

Each completed child retains its own error flag, result, start and end, regardless
of the parent's outcome. An unresolved child has no fabricated result or end time.
Cold projection retains those observations; it does not resume a tool or assert
that an executor is still running. A missing/foreign parent leaves retained results
outside the tree rather than inventing ancestry. A result without an available
start/proposal has no fabricated call payload.

## Argument capture and privacy

Nested calls have no assistant-issued proposal of their own. Their public start
arguments are therefore retained in the existing private display journal as JSON,
with an explicit **before-validation** boundary. Each raw JSON object is capped
at 512 KiB; encoded argument snapshots share the existing 2 MiB SDK-message budget
with streamed proposals. JSON escaping counts toward that encoded budget. At most
256 nested argument captures are admitted per SDK message, resetting on the next
assistant message. Cyclic, undefined, oversized or exhausted captures retain a
static unavailable reason and no argument value. Inspection does not change native
SDK validation, tool execution or native original storage.

Older child events did not retain arguments. Their results remain inspectable,
with the original Payload seat unavailable; an empty object or a current registry
value is never substituted. Schemas come only from the matching retained request's
actual tool list. Hidden callable tools absent from that list have no invented
schema. Root proposals and child starts remain distinct evidence.

These arguments may contain private content. They are conversation display history,
not sanitized metadata, and disabling diagnostic provider-payload capture does not
delete them. Existing authenticated scope and conversation retention apply. No
telemetry exporter, network destination, credential flow or model setting is added.

## Chat and Context File Activity

The existing Chat tool seat receives that dispatch's retained child arguments and
result. Scoped bindings also prevent a foreign result with a reused raw ID from
settling the wrong Chat row. There is no new control or layout.

Original Context File Activity now reads each result's own retained start, or its
preceding same-scope root proposal for older records. It never builds a global map
that lets a later reused ID replace an earlier operation's arguments. Nested reads
therefore retain the correct path and request-local end time. Missing arguments or
ambiguous clocks remain unavailable. Proposals without results add no file activity;
error receipts remain failed attempts, not proof of successful effects. Activity
ordinals are presentation identities, independent of provider message ordinals.

The effective-context browser still uses retained provider snapshots. Nested
arguments are not inserted into a provider request that did not contain them.
File Activity and tool inspection do not manufacture model input, token usage,
schema authority or task-success evidence.

## Qualification and remaining work

Pure contracts exercise running/settled trees, repeated IDs across requests, exact
arguments/results/schemas/clocks, unchanged source events, long legal child IDs,
legacy missing arguments and absent/foreign parents. Context contracts protect
earlier root operations from later reused proposals, including a result settling
after a newer proposal. Capture contracts cover shared/encoded budgets, cyclic and
oversized values, count limits and next-message recovery.

The isolated authored SDK/Host/Chromium fixture executes a real `read` under two
levels of approved extension tools. It uses the original Allow once controls,
once per observed approval key, before a held child actually enters its executor.
The first turn Stops that child and preserves independent error receipts; the
second reuses the same raw IDs, releases the held child and records a deliberately
failed sibling. The original pending/completed/failed details keep Turn 2 selection.
Nine SDK starts/results, two actual read calls and three provider requests are
retained across both turns. A fresh Host reads the same display history and the
original second-turn result without replay. All profiles, tools and provider
responses are independently authored; this is not owner live-provider evidence.

Earlier checks retain the original missing-tree failure, a blank-session fixture
that wrongly expected visible Chat tabs, and a fixture that stopped at the correct
original approval gate. The cold-navigation check initially expected the token to
remain in `location.href`; the application correctly consumes it. The corrected
check verifies the fresh Host identity and origin. It rejects all UI errors except
an exact old-Host `/api/events` connection refusal during the deliberate shutdown;
new-Host errors remain failures. Deadlines, geometry and two-worker scheduling are
unchanged. The first complete source run passes 365/365. A subsequent bounds audit
reproduces two defects in that interim source: escaped stored arguments exceed the
encoded budget, and long legal child IDs lose clocks/ancestry. Both are corrected
before final source/artifact qualification. Historical failures remain retained.

At this historical source checkpoint, private MX remains a49d58d /
20261013-054009-ab664123. The following interim qualification and Stop correction
supersede that checkpoint; full migration/platform gates remain open.

## Interim installed qualification and Stop correction

Runtime **02a55a922e1ff6a09ce6fcd1717590e260d35f0f** passes strict source check/build,
**366/366 across 72 files**, and five notice/workspace cases. A separate ordinary
artifact passes the same checks, preserving 663 compiled files, 20,801 production
dependency files, 151 npm instances, nine native/Wasm executables, 783 licence
files and all generated distribution/supplier records. The first unselected
staging inherits the preceding release's Node path. It is retained as a comparator;
a fresh staging explicitly selects its own bundled Node and verifies identical
files/artifact digest. Each immutable staging passes **49/49** targeted cases.

The corrected staging is selected through guarded idle shutdown and stable
Host/Native startup in private MX **20261013-064451-6b04982b**, product **0.2.13**,
artifact **f7d0af14733a58ac964af60f423a7f21fa4a0178c449b42ad21b02df8359988d**.
All **23,893** entries and twelve histories/queues verify. Of 247 saved files,
243 are identical; one journal preserves its exact prefix plus one close, with
three related derivatives. Draft/attachment, settings/model/auth and production
selection/router bytes are preserved. This is interim qualification, not passing
evidence for complete live Stop presentation.

Manual installed acceptance executes the real read, retains exact pending child
arguments/schema/start, and Stops the held executor with four SDK starts/results
and one provider request. After Stop, the current client loses the nested detail
tree until reload, although its saved history is intact. A separate buffer read
finds **74 frames with no gap**, and all sixteen display events match canonical
history exactly. Reload restores the full error/read tree. The failure is a
client reconciliation gap when idle metadata precedes its event poll; no SDK or
saved-history corruption is observed. The interim tab and exact fixture supervisor
are closed without altering the selected artifact.

The authored controller now reads canonical display history and observation
metadata after an acknowledged cancellation, merges them with newer already-live
events/older loaded records, then refreshes idle metadata. Stable original call IDs
retain selected child details. Family readers receive a revision notification.
Selection/epoch retirement drops late reads; general metadata refresh also refuses
retired responses. A failed receipt read reports the acknowledged Stop and unknown
details, preserving the prior ledger and submitting no cancellation or work retry.
No new endpoint, permission, execution owner, supplier/CSS or dependency is added.

Pure regressions reproduce missing receipts and foreign-selection replacement on
the interim controller. The corrected contracts preserve a later live diagnostic,
exact terminal children, family notification, retired readonly state and no replay
after a failed read. The initial revised fixture used observation records without
required IDs; assigning its authored IDs corrects the count assertion without a
product change. The enhanced actual SDK/Chromium case holds only its own event poll
at the request boundary, then Stops through the original button. Failed child
details, the completed read and Turn 1 selection must remain visible without
releasing that poll or reloading. The old immutable 02a55a9 fails this exact check;
corrected source passes it. A first assertion wrongly looked for the inner tool's
error inside the selected wait child's panel; it now checks the wait's actual SDK
abort result. Deadlines, 1280×720 geometry and two workers remain unchanged.

Final corrected source/ordinary/installed qualification follows separately. Current
selected/running remains the interim 02a55a9 until a new immutable release qualifies;
it is not patched in place. Full P0/P1, live/privacy/public distribution and
physical/platform gates remain open. Further OS implementation awaits owner MX
feedback.
