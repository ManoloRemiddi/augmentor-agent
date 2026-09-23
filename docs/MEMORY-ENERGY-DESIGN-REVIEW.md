<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Memory processing and energy review — 21 September 2026

Historical incident review. The subsequently implemented and installed correction
is recorded in [controlled memory](CONTROLLED-MEMORY.md). The containment and
proposal below describe the state before that implementation.

Original status: investigated; revised lifecycle proposed, not implemented or deployed.
The immediate local containment is a stopped Hindsight container with automatic
restart disabled. Its data volume is preserved. Cached context and transcript
capture are separate from that container; live retrieval and derived-memory
updates are unavailable while it is stopped.

## Requirement and original intent

The user explicitly rejects sustained GPU work while no agent is in use.
Automatic continuity must not imply unrestricted background inference.

The implementation introduced in `b8bfefd` deliberately kept memory running
after conversations ended. The original [memory guide](DUAL-MEMORY.md) says:

> The companion continues processing after a conversation ends.

The intended benefit was relationship and project continuity without waiting
for extraction or summary generation on the next conversational turn. A durable
outbox recovered interrupted processing, and archive migration rebuilt memory
from original evidence. Those are useful goals, but the implementation omitted
an activity boundary and a total cost budget. The guide's statement that the
architecture was selected with the user is not evidence that the user requested
or accepted unrestricted inference. This incident corrects that assumption.

## Verified causal chain

1. `scripts/setup-hindsight.py` installed a persistent Docker service with
   `unless-stopped` restart. Its API process includes an enabled background worker.
2. `services/memory/service.py` runs maintenance every five seconds, independently
   of agent activity. `HindsightMemory.step()` explicitly documents that it runs
   without an open chat.
3. `banks()` discovers all archived scopes; new banks start with cursor zero.
   `advance()` submits original events from the archive to both relationship and
   work banks. Idempotent delivery prevents simple duplicate submissions; it does
   not make extraction free or limit the total historical work.
4. Retention triggers consolidation, which triggers knowledge-page refreshes.
   The configured 120-second refresh interval is a minimum spacing, not a
   processing deadline or permission check.
5. One worker and one concurrent model call limit parallelism, not runtime or
   energy. A single model request can saturate the GPU.
6. Pause prevents further companion delivery but does not revoke work already
   submitted to Hindsight. An idle or closed chat does not pause it at all.

Local process sampling attributed 93–94% GPU utilization to `llama-server` and
its active connection to Hindsight. Logs showed transcript fact extraction,
consolidation queues and page refreshes. Stopping Hindsight reduced GPU activity
to 0% while Qwen and Breeze remained loaded. This separates model residency from
the source of active computation.

## Failure amplification

A page refresh started at 23:45:36 local time on September 20. Its reflection
completed, but the subsequent structured page-edit calls repeatedly timed out.
Four attempts used the configured 180-second per-call timeout. At 00:00:33 on
September 21 the page update failed and was scheduled for retry. The same
operation was claimed again at 00:03:52, after a transcript batch completed.
The engine preserved the previous page rather than replacing it with incomplete
content; the energy problem was the work and retry policy, not evidence of lost
page content.

The pinned container source confirms:

- `max_tokens=768` on a knowledge page is a desired page length. It is not an
  inference budget. Reflection's provider completion-token limit defaults to
  unset, and other stages make additional calls.
- The 300-second reflection deadline does not bound the entire page-refresh
  operation, which includes structured delta edits and retries.
- Model-call retries and worker-level retries are separate. The companion also
  resubmits failed/cancelled retain operations, without a durable terminal retry
  limit. The companion issue is an additional risk; it is not evidence that it
  caused this particular page-refresh retry.
- Periodic consolidation reconciliation can schedule eligible unscheduled work.
  Controlling only new transcript submissions is therefore insufficient.

The existing September 19 timeout adjustment addressed prematurely cancelled
healthy model calls. It did not establish an energy budget or an idle policy.
Increasing that timeout again would not resolve this incident.

## Proposed permanent contract

Keep journal capture, cached context and read-only retrieval separate from
generative maintenance. Saving new conversation text is cheap and should remain
reliable even when no computation is permitted. Pending derived memory must be
reported as pending, not discarded or marked complete.

All generative stages need one admission policy, covering extraction,
consolidation, page refresh, retries, reconciliation and archive migration.
The policy must be enforced at the worker/model boundary, including already
queued work, rather than only at the transcript sender.

The user's remaining policy choice is whether computation is allowed within a
bounded active-agent session or only during an explicit memory-update action.
No numeric budget or post-session grace period has been accepted. Neither an
open idle window, a service restart, a reconnect nor a backlog constitutes new
permission to spend inference time.

For activity-based operation, trusted DSH/Pi lifecycle signals must grant short,
expiring permission. A process crash must expire permission automatically.
Foreground responses have priority. Any definition of session activity must
state precisely whether the gaps between human turns are allowed; a persistent
saved chat cannot keep permission alive indefinitely.

Use a shared wall-time and model-token budget across all stages and attempts.
Bound failures durably, preserve prior content, expose the problem, and require
a deliberate retry once the limit is reached. Restarting a worker must not
reset its budget or terminal failure state. Changing Qwen's chat settings, GPU
placement or context size is unnecessary.

Fresh events should be coalesced for processing. Historical archive ingestion
needs a separate visible, bounded import action; it must not silently acquire
the same priority or budget as a new conversation. Pages should refresh only
when their source evidence changes and when the processing policy allows it.

A resident retrieval API with a separately controlled inference worker is a
candidate deployment architecture. It still needs verification against pinned
Hindsight 0.10.0: disabling one worker must not leave another synchronous or
periodic route able to call the model. Simply stopping the API on every turn
would impose startup costs and unnecessarily disable retrieval.

## Acceptance before calling the fix complete

- With an existing backlog, no agent activity and after a reboot: zero
  memory-originated requests reach the model, without deleting pending work.
- Cached context remains available. Live retrieval's permitted computation is
  documented and verified separately from maintenance generation.
- A new conversation is captured once and can update both scopes within the
  selected policy. Memory work does not displace the foreground response.
- Ending activity, pressing Stop, losing the client or crashing the harness
  revokes permission, including in-flight inference within a measured bound.
- Exhausting the total budget leaves work pending. Per-call retries, worker
  retries, refresh triggers and restarts cannot bypass the limit.
- A deliberately failing page update reaches a visible stopped state instead
  of repeatedly spending the same budget. Its previous page remains intact.
- Historical migration is explicit, bounded, resumable and idempotent.
- Multiwindow DSH, Pi, browser and voice lifecycle tests cover shared ownership.
- Test with disposable data/model fixtures first, then a bounded real-model
  sample and idle GPU measurement. Report source and installed artifact identity
  separately using [desktop deployment rules](DESKTOP-DEPLOYMENTS.md).

## Current limits

This review is based on repository history, read-only local journal aggregates,
container logs and source copied from the stopped pinned container. It does not
establish how much energy was consumed over the entire day, that every operation
was failing, or that the backlog could never finish. No private transcripts,
bank identifiers or credentials are included here.

At the time of this review, no permanent scheduling implementation had been
promoted and Hindsight remained stopped. This conclusion is superseded by the
qualified [controlled implementation and activation](CONTROLLED-MEMORY.md).
