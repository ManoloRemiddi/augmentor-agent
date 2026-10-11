<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Pi background jobs and delegation

The shared Host owns a private durable job registry. A delegated worker has one
distinct Pi AgentSession and its own native history, queue and observations.
The parent continues through its existing owner. Background commands own separate
processes; they never create another agent loop. This source feature extends the
accepted P1 migration requirement. Live services, concurrent integration and
platform/installed acceptance remain required before DSH retirement.

## Streaming scheduling

All Pi conversation and specialist sessions use awaited public `message_update`
and `message_end` extension hooks to yield to Node's event loop. Buffered provider
output therefore permits RPC/Stop processing between events even when durable
Windows record writes take longer than the provider's output cadence. Each event's
listeners and checkpoints finish before the next event; output is not batched.
This permits scheduling, but does not make a blocking record operation interruptible
or put unbounded trusted extension code under a deadline. See the scoped actual SDK
regression and [Windows candidate evidence](PI-WINDOWS-HOST.md#october-11-buffered-stream-scheduling-candidate).

## Authority and admission

Model tools are `job_start`, `job_list`, `job_read`, `job_wait`, `job_cancel`.
Operator RPCs are `session.startJob`, `session.jobs`, `session.job`,
`session.jobHistory`, `session.jobNativeHistory`, `session.jobNativeRead`,
`session.jobObservations`, `session.jobPayload`, `session.waitJob`,
`session.cancelJob`, `session.removeJob`.
All read, wait, cancellation and child-history operations require the exact
parent conversation. A guessed job ID or a fork does not grant access. The
standalone Harness Jobs tab offers bounded start, evidence and Stop controls;
its scoped inspector permits only parent-owned reads. Native/Browser layouts
are preserved. Children are excluded from the ordinary conversation picker and
cannot be prompted, branched, reconfigured or armed independently.

A stable request ID plus normalized parameter fingerprint prevents replay.
Identical submissions return the existing job, including failed/cancelled/unknown
receipts; changed parameters at that ID are refused. A private `starting`
receipt is saved before producer dispatch. Registry limits are four active jobs
per parent, sixteen globally and 256 retained receipts. Removal is explicit,
requires settlement and saved accounting/notification, and does not delete child
native history. IDs and data remain private; public tests use independent
synthetic profiles and tasks.

Delegation takes a task brief and explicit exact tool names. It inherits the
parent's selected model, reasoning preference, workspace, permission preset and
configured approved resource list. It does not copy parent conversation messages.
Unknown/uncallable grants, job tools, goal mutation and recursive desktop
delegation are refused before start. Public active-tool selection narrows what
the model sees; public agent and extension-runner guards also fence root and
nested calls. Unavailable grants in the child registry fail explicitly rather
than silently disappearing. Changing grants require the existing permission
gate, then each child change retains its own ordinary approval gate. Approvals
appear on the parent UI with a child identity; cancelling that child resolves
its scoped interactions. Read-only parents cannot grant changing authority.
Browser parents cannot start shell commands or grant absent Native tools; their
authorized browser tools target the parent's attached BrowserBroker.

Approved extensions are trusted executable code, not a security sandbox. Resource
configuration is snapshotted, but source files/providers can change outside the
Host. Direct JavaScript effects inside a trusted extension are not confined by
model-tool grants. Concurrent workers share the selected workspace and may
conflict; this feature does not add filesystem isolation or transaction rollback.

## Desktop specialist jobs

`kind:desktop` uses the existing [bounded specialist](DESKTOP-SPECIALIST.md).
Its task is strict JSON with `task`, `successCriteria` and `constraints`; tool
names are fixed, and `allowedTools:[]` selects that set. Shell, file, memory,
parent resources and recursive delegation stay outside this child. The selected
image model and effective parent thinking level are snapshotted without fallback.
Defaults are 180 seconds, 24 provider requests, 40 tool dispatches and 24576 total
reported output tokens. Each request still has the specialist's 1024-token cap,
existing conservative context guard and two recent outgoing images.

The awaited `desktop_delegate` coordinator tool now starts this same durable
job and returns its structured result with job/child/run IDs. Only one such tool
is accepted per parent turn. Operator `session.startJob` and model `job_start`
can start a background specialist; one desktop job is admitted globally. This
is the existing public SDK specialist loop with one distinct native child owner,
not another loop for the parent. Child SDK history, screenshots, tool pairs and
provider observations survive disposal. Native files are tightened to 0600 after
public message events and settlement, inside private 0700 directories.

The OS executor and desktop evidence retain `pi:<parentId>` ownership so existing
consent, independent desktop Stop and `desktop_evidence` continue to work.
Restricted admission and each input approval route to the parent UI with a child
identity; individual Stop cancels that child's pending approval. Fresh screenshot
tokens remain single-use. Both saved action intent and the job checkpoint precede
input dispatch. Screenshots and detailed worker metadata stay outside ordinary
parent context; explicit evidence reads remain authorized operations.

Ordinary parent settlement preserves the child’s pending approvals and desktop
connection; direct desktop tools are fenced while its job owns admission. The
existing direct desktop Stop cancels the durable job as well.

Parent Stop, job Stop or child-session Stop cancel the actual worker and release
the consented executor. A failed release confirmation remains `unknown`, even
when cancellation or a time limit was requested. Crashes retain native originals,
known partial usage and attempted-input evidence without reconnecting or replaying.
The job's disposition is authoritative; a retained partial desktop result is a
checkpoint, not proof of eventual settlement. Completed still means a fresh
post-action screenshot and the worker's observed claim, not external verification.

The standalone Harness Jobs form exposes the strict desktop brief and bounds.
Parent-owned native history pages and hash-bound excerpts, plus child provider
observations and captured payload excerpts, also work through its scoped read-only
inspector. Reads perform no inference, producer dispatch or usage attribution.
Payload capture follows the existing optional observation/retention policy;
native screenshot history and desktop evidence are separate private stores.
Approved Native/Browser layout and model/speech/GPU settings are unchanged.

## Bounds, Stop and restart

General defaults are sixty seconds, sixteen provider requests, 64 tool dispatches and
8192 reported output tokens. Supported maxima are five minutes, 64 requests,
256 tools and 131072 output tokens. Provider requests are counted and saved at
the public stream seam before dispatch. Root/nested tool dispatches are counted
after policy approval and before execution. Each provider request receives the
remaining output-token allowance. Normalized output usage reduces the next
allowance; unavailable/inaccurate provider accounting cannot prove a strict
spending or total-context bound. Input tokens and currency are not independently
capped. Child automatic compaction and provider/session retries are disabled;
bounded execution uses the same product guard and inherited reasoning policy.

Parent Stop cancels its jobs even when its chat turn is idle. Individual Stop
aborts the actual child SDK owner and scoped interactions. Shell Stop signals
the exact owned Unix process group, then escalates after 500 ms. No saved PID is
adopted or killed after restart. Windows uses the owned [command supervisor](WINDOWS-SHELL-JOBS.md), which contains ordinary descendants in a kernel Job before releasing command text. Stop, parent-pipe EOF and supervisor exit terminate that owned range. A leader exit alone does not settle a live descendant. Missing receipts remain unknown. All eight helper proofs pass on real x64 and ARM64 Windows; actual Windows Host/SDK and assembled qualification remains pending. Linux skips do not prove Windows semantics. Process closure does not undo earlier side effects or prove effects outside the owned range stopped.

Cancellation waits at most five seconds for producer settlement. Failure to
confirm it records `unknown` and retains the live producer's capacity until it
actually settles. A late completion cannot overwrite that terminal receipt.
Timeout requests cancellation and reports a failed time limit when settlement
is confirmed. Stop/cancelled/completed are producer dispositions, not independent
task verification or rollback. A restart turns saved starting/running/stopping
receipts into `unknown`, preserves output and originals, and starts nothing.
Invalid/inaccessible saved job evidence disables job admission while ordinary chat remains available; originals are preserved. A later settlement-write failure records a process-local unknown persistence gap and disables further jobs. There is no automatic retry. Wait is separately cancellable, bounded to thirty
seconds, and does not stop the producer.

Ordinary parent inputs keep their priority. Armed goal continuation waits while
that parent's jobs are active, then wakes through the existing serial queue.
Shared provider/reasoning/MCP reconfiguration and maintenance shutdown refuse
while owned producers remain active. Runtime close requests their cancellation.

## Output and accounting

The selected public [DSH MIT output ring](../packages/runtime/vendor/dsh-jobs/SOURCE.md)
retains absolute UTF-8 byte offsets, labels and explicit gaps. Live retention is
64 KiB per job, trimmed to 16 KiB at settlement. Private atomic receipts persist
the validated retained snapshot. Adjacent same-channel chunks are coalesced; at most 128 retained chunk groups bound metadata, with explicit head loss if stream alternation exceeds that cap. Saved JSON is bounded to 1 MiB independently of UTF-8 output size. Reads return immutable chunks without advancing
another observer's cursor or re-adding usage. Old offsets yield an explicit lossy
read. Output is producer text; native child history and observations preserve
separate tool/request evidence. Jobs UI renders output and tasks as text.

Known child normalized usage is retained separately from result text. At settled
parent idle, one public native `usage` entry with kind `delegation` and stable
note `augmentor-job:<jobId>` attributes the child totals to that parent. A scan
for that marker precedes append, covering a crash between native append and
registry acknowledgment. Tool read/wait results have no SDK result-usage field.
A `augmentor/job-settled-v1` custom message reports settlement to the same parent
with `triggerTurn:false`; it never starts another turn. Both flags are confirmed
against indexed saved originals before being marked durable. Pi defers a blank
parent's file until its first assistant message; its accepted in-memory receipts
remain pending and can be reconciled once ordinary chat actually persists them.
Cold reads neither load the parent nor perform inference to settle accounting.

Child originals retain their own usage. Aggregate product reporting must count
parent attribution or child originals, never both. This increment does not add
a global account total. Interrupted provider calls may have unavailable usage;
retained normalized partial usage is evidence of only what was observed. Nested
tool usage is included in the child native aggregate, labelled under the
inherited model for attribution; it is not a provider-by-provider billing report.

## Qualification boundaries

Actual private SDK/provider fixtures cover permitted writes, denied root/nested
tools, request/tool/output limits, parent and individual Stop, scoped approvals,
real command processes, stable IDs, crash recovery and one-time native usage.
Actual Host/SDK/desktop-client fixtures cover awaited and operator desktop jobs,
pre-dispatch receipts, preserved screenshots and tool pairs, consent/input/Stop
failures, limits, scoped approvals, crash recovery and one-time usage. Their
independent peer is synthetic; it does not request physical OS consent.
Actual Chromium covers Jobs start/output/Stop, literal HTML rendering, narrow
viewport and scoped cold read-only inspection. Registry tests cover UTF-8
eviction/restart, owner fences, quotas and independent waits.

These are synthetic service and Linux source/staged checks, not live provider,
physical desktop/audio or installed Mac/Windows qualification. The desktop specialist now shares durable job lifecycle and usage accounting.
Actual concurrent Browser,
MCP and desktop jobs, all platform cancellation adapters, representative live
services and the full accepted P0/P1 migration/installed gates remain open.

Exact revisions, test counts and failures are recorded in the
[agent handoff](AGENT-HANDOFF.md). DSH and owner-selected releases remain available.

Historical general-jobs implementation `26a6c07a28f618a6446f64c40cd9ddbca16cb825`: 809 source cases/807 passes/two existing optional skips; ordinary unselected stage 19, Node 24.19.0, 187 passes across 45 files. See the handoff for retained failures and hosted gates.

October 11 specialist implementation `f3a3d4ac476f71c86ea0f2c9ffe3fcfb218cbb91`: final source **820 cases/818 passes/two existing optional skips**; ordinary unselected stage 20, Node 24.19.0, **212 passes across 47 files with four test workers**, no failures/skips and unchanged timeouts. The [current handoff](AGENT-HANDOFF.md#october-11-pi-desktop-specialist-jobs-checkpoint) records scope, retained fixture/timeout failures and all remaining migration/platform/installed gates.
