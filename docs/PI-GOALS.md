<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Persistent Pi goals and continuation

One conversation has one durable current completion goal. Plans/todos remain
separate reported state. General background jobs and delegation remain accepted
migration work; this guide does not close their combined P1 gate.

## State and authority

Goal snapshots contain a stable UUID, positive integer revision, objective,
active/paused/blocked/complete phase and positive safe-integer round limit.
The default is 256 rounds; objectives are bounded to 8192 JavaScript string units.
Blocked state includes a normalized explanation and lower-kebab-case policy code
(128/4096 string-unit product bounds). Completion is the caller's report, not
independent evidence that a task succeeded.

Every mutation compares the exact current `{id,revision}`, or explicit `null`
when absent. An unfinished goal cannot be replaced. Edit changes only objective
or limit and preserves phase/counters. Pause requires active state; block requires
active state; resume accepts active, paused or blocked with capacity remaining;
complete accepts unfinished state; clear writes a tombstone. Revisions advance
one at a time. Mutation timestamps clamp to the preceding update if the clock
regresses. Cleared/replaced goal IDs cannot be reused on the selected ancestry.

Activation is **process-local** and separate from phase. New loaded owners,
restart, fork, resource reload and shutdown disarm automatic continuation.
The public model tools **get_goal**, **create_goal**, **update_goal** retain the
same policy/approval path as other reads and changes. Creation requires an
explicit user goal request; model creation/resume stores state disarmed.
Model pause/block/complete/clear disarms future continuation and allows its
current tool turn to finish. Goal state grants no additional tools or authority.
Read-only Native/Browser policy allows get_goal and refuses model mutations.

The authenticated operator RPC **session.updateGoal** accepts `{sessionId,change}`.
`change` contains `operation`, `expectedRef` and operation-specific fields.
Create/resume additionally requires explicit boolean `continueAutomatically`.
Only human/operator create/resume with `true` arms continuation. An unknown
queue receipt must be inspected and explicitly acknowledged before arming;
refusal occurs before goal mutation. Create/resume waits for the current turn
to settle. Operator pause and the existing Stop control pause an active loaded
goal, disarm it and cancel the actual owner. An unloaded saved goal is already
disarmed; Stop does not load resources merely to change cold state.

## One owner and admission

The existing Host serial admission and durable **PiPromptQueue** run each round
through the same public Pi AgentSession. Waiting ordinary inputs take priority.
Maintenance, MCP management/reload, prompt improvement, a running turn, paused
queue or uncertain receipt prevent admission. Settled steering/improvement RPCs,
MCP management receipts and completed configuration reloads wake still-armed
idle goals through the same serial pump; they do not re-arm a disarmed owner.
An actual slow prompt-improvement/cancellation fixture qualifies that barrier
and wake behavior without replaying the improvement. Automatic prompts are generated
from the current objective, skip prompt-template expansion, and retain approved
SDK input handlers and the conversation's current model/tool/policy settings.
No DSH driver/loop is transplanted and no second loop owns the conversation.

Only actual goal-sourced SDK **message_start** user admission increments the
round counter. Reserving/enqueuing a prompt, ordinary user input, steering,
model requests and tool calls do not. The native round receipt precedes its
SDK-persisted user entry; strict replay requires that user entry before another
goal record or message. The receipt has a unique durable queue request ID and
exact goal ID/revision/round plus a SHA-256 of the actual public user message role,
content and timestamp. Replay verifies the next user original against that digest,
so a later unrelated ordinary input cannot fill a missing admission. SDK admission,
native append acknowledgment, disk
persistence and verified external outcome remain distinct. A process-local known
live admission may briefly report `admissionPending` while an approved SDK
message-end extension awaits; inspection preserves its activation. Operator Pause
and Stop disarm immediately, report `pausePending`, cancel the owner and append
exactly one durable pause after that user entry settles. An orphan at settlement
or on cold reopen is unavailable, never silently associated with another input. The SDK defers saving
a blank session until its first assistant message; early accepted state can
therefore be in-memory only. Inspection exposes that boundary.

The configured limit counts admitted **goal rounds**, matching DSH's selected
contract. It is not a token, monetary or wall-clock budget. The driver blocks
with `round-limit` when capacity is exhausted; editing the limit does not invent
past rounds. Provider/work failure disarms and blocks active state with
`turn-failed`; an input extension that handles a goal prompt without admission
blocks with `goal-input-handled` and zero new rounds. A Stop pauses. There is no
automatic retry or external completion evaluator.

Each round retains the queue's durable terminal/unknown receipts. A crash leaves
dispatching/active input unknown and pauses the queue. A merely waiting automatic
reservation is removed on Stop and restart and never becomes an ordinary resumable prompt.
Ordinary waiting inputs remain paused. Explicit unknown-outcome acknowledgment
does not retry that input; a later explicit resume admits a new numbered round.

## Persistence and inspection

Full snapshots use native **augmentor/goal-change-v1** custom entries; admissions
use **augmentor/goal-round-v1**. The selected [DSH MIT strict fold](../packages/runtime/vendor/dsh-goal/SOURCE.md)
is pinned to public `d743267388641bc76f17c45ce8b4c231aed1d32c`; only its imports
and attribution header change. Its exact decoder/transition body is checked by
SHA-256. Original DeepSeek copyright and MIT license accompany compiled/staged
source. The minimal contracts and Host/native adapters are separately authored;
the product dependency graph and native components do not change.

Hot reads replay the entire selected native ancestry rather than trusting a
closure or latest snapshot. Cold **session.goal** uses verified **NativeHistory**
metadata/custom originals without opening/migrating an SDK manager, loading
resources, probing MCP, inference or replaying tools. Each selected ancestry is
bounded to 4096 entries, 4 MiB of custom entries, a separate 4 MiB of associated
admitted-user originals and 256 KiB per decoded custom/user record. Unrelated user
payloads are not decoded for this fold.
Bounds, invalid older records, revision/round gaps, reused IDs, an orphan admission
or incomplete saved tail return unavailable. There is no fallback to an older
apparently valid snapshot. Cold coverage reports its scan/byte limits and index
I/O separately; initial index construction can scan the whole source and block
verification has the existing index contract. These are explicit supported bounds,
not qualification of representative large-history performance.

Forks inherit only records on the exact selected boundary and start disarmed;
later abandoned futures are excluded. Editing a goal-sourced input removes its
matching admission receipt as well as that user message, so the replacement
ordinary input cannot inherit the removed round or a mismatched fingerprint.
Actual SDK branch/edit fixtures preserve earlier admitted counts. Child updates
preserve parent bytes and
retain their own native identity. Native/Browser approved layout is unchanged.
Their existing inspector reaches the standalone Harness **Goal** tab. It renders
safe text, phase/activation/rounds, original metadata and operator start/edit/
pause/resume/complete/block/clear controls. Edits retain both draft text and the
reference at which editing began across concurrent refreshes. Scoped read-only
inspectors have no mutation controls and cannot write or read another conversation.

## Qualification and remaining scope

`tests/pi-goals.test.mjs` drives the real pinned SDK/private owner against an
independently authored provider: sequential continuation, one owner/native ID,
ordinary input priority, revisions, model state-only creation, limits, Stop,
exact fork divergence, cold reopening, read-only Native/Browser, provider failure,
handled input, SIGKILL/unknown receipt acknowledgment without replay and a public
SDK extension holding user persistence while repeated inspection and operator
pause settle correctly.
`tests/pi-goals-barriers.test.mjs` adds the actual shared prompt service/public SDK
improvement barrier and cancellation wake. `tests/goals-history.test.mjs` covers retained MIT body/notice, strict cold ancestry,
older corruption, reuse/round gaps, missing admission, partial tails, limits and
restart removal of an undispatched automatic reservation. The actual Chromium
`tests/harness-goals-chromium.test.mjs` exercises controls, safe text, retained stale
drafts, scoped cold reads, denied writes and a 640-pixel viewport. These are
synthetic services/resources and source/staged evidence; physical/installed and
live-provider acceptance are separate. The current checkpoint in
[agent handoff](AGENT-HANDOFF.md) owns exact refs, counts and platform/CI status.

Full goals/jobs/delegation parity still needs general background jobs, child
authority/limits/Stop, durable outcomes and one-time usage accounting. Every
accepted P0/P1/platform/installed/privacy gate remains binding. Preserve DSH and
selected releases until their required workflows qualify. This state/continuation
port alone does not authorize a default switch, merge, promotion or DSH retirement.
