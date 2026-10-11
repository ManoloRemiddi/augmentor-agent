<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Pi background jobs and delegation

The shared Host owns a private durable job registry. A delegated worker has one
distinct Pi AgentSession and its own native history, queue and observations.
The parent continues through its existing owner. Background commands own separate
processes; they never create another agent loop. This source feature extends the
accepted P1 migration requirement. Live services, specialist consolidation and
platform/installed acceptance remain required before DSH retirement.

## Authority and admission

Model tools are `job_start`, `job_list`, `job_read`, `job_wait`, `job_cancel`.
Operator RPCs are `session.startJob`, `session.jobs`, `session.job`,
`session.jobHistory`, `session.waitJob`, `session.cancelJob`, `session.removeJob`.
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

## Bounds, Stop and restart

Defaults are sixty seconds, sixteen provider requests, 64 tool dispatches and
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
adopted or killed after restart. Windows currently signals the direct process;
descendant-tree cancellation is an explicit unqualified adapter gap. Process
closure does not undo earlier side effects or prove escaped descendants stopped.

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
Actual Chromium covers Jobs start/output/Stop, literal HTML rendering, narrow
viewport and scoped cold read-only inspection. Registry tests cover UTF-8
eviction/restart, owner fences, quotas and independent waits.

These are synthetic service and Linux source/staged checks, not live provider,
physical desktop/audio or installed Mac/Windows qualification. The existing
desktop specialist remains a separately bounded awaited workflow; its durable
job lifecycle/usage consolidation remains required. Actual concurrent Browser,
MCP and desktop jobs, all platform cancellation adapters, representative live
services and the full accepted P0/P1 migration/installed gates remain open.

Exact revisions, test counts and failures are recorded in the
[agent handoff](AGENT-HANDOFF.md). DSH and owner-selected releases remain available.

Tested implementation `26a6c07a28f618a6446f64c40cd9ddbca16cb825`: 809 source cases/807 passes/two existing optional skips; ordinary unselected stage 19, Node 24.19.0, 187 passes across 45 files. See the handoff for retained failures and hosted gates.
