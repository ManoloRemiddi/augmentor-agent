<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Bounded DSH execution recovery and response validity

The September 21 one-shot diagnostic stopped after 438 seconds. Research and
forecast retrieval succeeded, but one response consumed 32,768 output tokens
without an executed action. DSH ended with max-tokens; no software or tests were
delivered. This was an output limit, not evidence of context-window exhaustion.
Private transcripts and task data remain outside this repository.

## Contract

`adapters/dsh-execution/index.mjs` uses supported DSH 0.1.5-rc.1 lifecycle hooks
for Augmentor Linux/browser presets. Pi and delegated agents are excluded. It
creates no parallel agent loop. Normal request limits, model identity, saved
selection, memory policy and GPU/backend configuration remain unchanged.

On truncation or a normal stop containing no public text or tool call,
`agent/turn-stopping` steers the same turn from confirmed progress.
The plugin-sourced context retains user restrictions and grants no new authority.
It encourages one small executable step and subsequent verification. DSH skips
proposed tools in a truncated response; the plugin never executes them itself.
Unresolved recorded tool calls disable recovery. User Stop wins, including during
recovery. There is no automatic replay after restart, reconnect or cancellation.

Defaults: at most two recovery attempts per turn **shared across truncation and
empty responses**, 8192 output tokens per
recovery request, 64 further steps and ten minutes after recovery begins. Time
and step admission are checked between actions; an in-flight tool is allowed to
settle, so ten minutes is not a hard wall-clock kill deadline. Recovery effort
is unchanged unless configured with an exact provider/model/effort mapping in
`recoveryRoutes`; the adapter still validates provider support. Exhaustion emits
an explicit incomplete notice. A final answer means response-produced, never
proof that user acceptance criteria were satisfied. This is not a generic task
completion verifier or arbitrary tool-loop detector.

DSH 0.1.5 preserves max-tokens as a sticky turn-end reason even after continuation.
The hook must explicitly continue after recovered tool batches too. We preserve
that audit fact rather than patching core or falsifying the end reason. Native
history now explains it and directs the user to recovery/deliverable evidence.

## Settings and progress

Adaptive Reasoning deliberately selects its high tier for consequential work;
the installed Qwen mapping uses xhigh. The picker shows saved selection, while
request/header shows the request policy. The adapter displays both and any
recovery override; backend enforcement remains provider-dependent.

The native transcript hides only the exact successful opening notice
`Harness: Saved reasoning: minimal; requested reasoning: xhigh (request policy). Backend enforcement is provider-dependent.`
This presentation filter applies to live events and history replay. DSH retains
the event and request diagnostics; reasoning policy is unchanged. Errors, bounded
recovery notices, different reasoning values, additional diagnostic text and all
other DSH messages remain visible. User/assistant text is never filtered by this rule.

A 90-second model step without an executed action produces one notice. Long
reasoning is not automatically called a stall, and timers do not cancel tools.
Request metadata records selected/policy/requested effort, output cap, public
usage, elapsed time, time since the last tool result and recovery counts. Only
the last 128 requests per session are retained in an atomic private sidecar:
`~/.local/state/augmentor/execution/<session-id-sha256>.json`. Override the base
with AUGMENTOR_EXECUTION_STATE. No prompt, answer, tool argument or reasoning
content is logged there; optional telemetry failure cannot fail a task.

Notices use standard UI-only command/done records. They are not assistant
speech, add no model context and do not enter conversational memory. The record's
success kind describes the notice, not task completion. Recovery steering uses
logged plugin context, never a fabricated human request. No custom required
event types are added to DSH histories.

## Qualification and retesting

`node --test tests/dsh-execution.test.mjs` uses real pinned DSH and pi-ai with a
local deterministic HTTP fixture. Ten cases cover multi-step recovery, adaptive
versus recovery headers, repeated truncation, step/time exhaustion, unknown
outcomes, truncated unexecuted tools, no replay of confirmed actions, normal
answers, user cancellation at the boundary/during recovery and compressed history
reopening in a separate process without the plugin. Cold-read validation caught
an invalid assistant-source representation before deployment; standard status
records passed. Native tests cover output-limit visibility without an answer.
These original ten cases remain in the expanded suite described below. They are
lifecycle fixtures, not evidence of real-model task competence.

Preserve diagnostic A. Retest in a fresh session/directory with pristine inputs,
changing only the marker and absolute workspace references. Supply no oracle,
old implementation hints or cached live data. Keep the same model and memory
policy; record request policy changes. Score actual artifacts with the same
rubric/oracle and record recoveries, actions, tokens, elapsed time and interventions.
Monitor the whole turn, including recovery. A sticky length flag alone does not
establish success/failure of the software. Never repair the benchmark during its
run. One diagnostic pair does not demonstrate general improvement.

## Deployment

Use a separate compatible artifact and [desktop update workflow](DESKTOP-DEPLOYMENTS.md).
Fresh guided setup includes the plugin; existing owned presets need a preserved,
backed-up entry referencing the staged artifact. Rollback restores both preset
entry/configuration and desktop selection. Installation/running identity and
real-model evidence are recorded separately below when qualified.

## September 21 deployment evidence

Implementation `588b8f1`: ten real-DSH lifecycle fixtures and compressed cold-read
passed; full native/Python suite 409 passed. Eight focused native tests also passed
against the compatible candidate, not only source. Selected release
`20260921-093509-f1711e55` is the prior compatible 0.2.8 artifact plus the execution
adapter and four-line native output-limit notice. Existing window processes retain
the prior UI until naturally reopened; no active window was interrupted. Both
owned DSH presets reference the staged adapter, with backed-up prior configuration.
The existing Qwen route uses low effort only during recovery; normal xhigh requests
and 32768 output limit are unchanged. A fresh real-model retest is running; its
first request confirms the adapter's setting notice and unchanged normal header.
No retest success is claimed before artifact assessment.

## General response-validity correction — September 21

A later diagnostic ended with provider stopReason=stop, a reasoning-only final
message, no public handoff and missing requested deliverables. The output limit
was not reached. The loop reported completed and the old adapter recorded
response-produced. This is a lifecycle defect regardless of task domain; no
benchmark prompt, private transcript, expected output or domain rule is included
in this implementation or its synthetic fixtures.

The adapter now checks the latest original model message at the stopping boundary:

- A non-whitespace text response is accepted unchanged. Short answers, questions,
  refusals and honest partial handoffs are valid; there is no required checklist
  format or domain-specific definition of success.
- A tool call is not an empty response. Ordinary tools keep DSH's normal lifecycle;
  tool-concluded questions/voice replies remain legitimate handoffs. Empty-only
  recovery does not force continuation after such handoffs. The existing special
  continuation for DSH's sticky truncation reason stays isolated to truncated turns.
- Reasoning alone or whitespace-only text without a tool call triggers the shared
  bounded recovery budget. The notice explains why another step is running. Its
  plugin message preserves existing user authority, distinguishes acknowledgment
  from verified outcome, and asks for authorized continuation, an answer in the
  requested form, or an honest partial handoff. It does not reveal reasoning,
  create a second agent, replay tools or append a fabricated human message.
- On exhaustion or uncertain tool outcome, a durable UI status says Task incomplete;
  sidecar outcome is incomplete and incompleteReason explains why. Cancellation
  wins. Fresh user turns reset the per-turn budget. Context replacement records
  are not treated as new actions/responses.
- A completely content-free provider response is already rejected by pinned pi-ai
  as an explicit error before this stopping hook. It remains an error, with sidecar
  incomplete; the adapter does not silently recast it as success or automatically
  retry arbitrary provider errors.

DSH's original turn/end reason is retained as audit evidence: a completed loop is
not proof of completed work. After successful empty-response recovery the sidecar
says response-produced or tool-handoff, never verified-success. The UI-only
incomplete notice survives live completion and history reopen even when DSH's end
reason says completed. No native production code change is necessary.

This first increment **does not implement** semantic requirement extraction, a
persistent task checklist, provenance validation for arbitrary artifacts, generic
loop detection, or changes to memory selection. A plausible but incorrect answer
can still pass response validity. The next checkpoint/evidence work must remain
optional to task shape, separate facts from hypotheses and authorization, support
unverified/partial outcomes, and validate evidence appropriate to the action. It
must not force every conversation into a software-building workflow. Pi is still
outside this DSH adapter; cross-harness parity is separate work.

### Qualification

The expanded focused suite has **24 passing cases**: 23 exercise real pinned DSH
and pi-ai against deterministic local HTTP responses; one isolated-hook fixture
checks replacement-event handling. Coverage includes synthetic analysis, document
work and planning prompts; blank/whitespace responses; mixed truncation/blank
budgets; preserved user restrictions; confirmed action no-replay; unknown outcomes;
Stop at boundary/in flight; step/time limits; valid short/partial/question/refusal
answers; tool-concluded handoffs; browser preset and excluded subagents/presets;
new-user-turn reset; provider no-content error; and cold compressed-history reopening.
Tests simulate model output and do not establish live model quality or broad task
success rates. No benchmark was dispatched to the user's agent.

Full Node regression:142 passing. Full native/Python regression:410 passing.
Native response/handoff suite:9 passing,
including the durable incomplete notice across live completion and reopening.
Use the development `.venv` with QtTest; the installed speech Python lacks QtTest
and is not the native test environment. CI installs the pinned DSH host before
running npm test and exports DSH_INSTALL_ROOT explicitly.

For a staged adapter, reuse the same tests without changing its files:

```sh
AUGMENTOR_EXECUTION_ADAPTER=file:///absolute/candidate/adapters/dsh-execution/index.mjs \
  node --test tests/dsh-execution.test.mjs
```

Installation identity and native regression results are recorded separately when
complete. Do not equate source tests with activation or controlled live-model
improvement. Retesting should be visible and user-started, across varied tasks,
with the harness version and unchanged model/settings recorded.

### Installed selection for response validity

Source implementation `1c8c1b7` passed142 Node and410 native/Python tests.
A separate copy of compatible0.2.8 artifact708d66c9… received only the reviewed
execution-adapter change and its owning guide. Candidate and final staged adapter
both passed the24 focused checks (23 real-DSH fixture cases plus one isolated hook).
Stage/import/inventory and authenticated activation preflight passed.

Selected release:`20260921-132038-7fd1a0ae`; artifact SHA256
`76c10abd7e98ab6f4bf83ad0a489198d956d9dc6ea9c28a300d94a2aede6db6a`.
Linux/browser owned presets now reference that immutable adapter. Their prior
checksums were verified; only the plugin path changed, recovery route/settings
were preserved, and ownership checksums updated. Both presets report healthy.
Preset/ownership/previous-selection backups live under the user's private
augmentor-general-response-deployment state directory. Restore those entries and
selection together for rollback; desktop rollback alone does not change presets.

No DSH task was running at cutover. No model request, user task, service restart
or window restart was dispatched. Desktop/mobile/secondary windows remain online
on20260921-011742-0b89b31a with updatePending=true. Use a fresh visible task for the
next live retest; a pre-existing instantiated agent may retain its prior plugin.
Installed fixture qualification is not a claim of an observed real-model recovery
or general performance improvement. The user's next benchmark remains user-started.

## Action-aware recovery — 0.2.10 preview

The adapter also uses supported `tools/pre-execute` and `tools/result` hooks.
This is one source-bundled component of the complete installer, enabled exactly
once in both Augmentor presets, not a second conversational loop or a standalone
package that users must install separately.

Within a turn it records normalized action identity and execution outcomes:
completed, failed, failed-before-dispatch, unknown, running and waiting. Completed
means tool execution acknowledgment, **not verified fulfillment of the task**.
During automatic recovery it denies exact repeated non-read operations and new
changes while a prior outcome is unknown, running or waiting. Read operations
remain available to inspect evidence. Two denied recovery actions end with an
explicit incomplete notice. Normal user-directed repeated actions outside recovery
are unchanged. A successful concluding tool result always hands off control,
including after truncation; recovery cannot continue past a question or voice reply.

Pinned DSH bash canonical results are inspected: nonzero exit, timeout, signal or
abort is uncertain even when the outer result says `isError: false`. A background
job acknowledgment stays running. `job_output` updates the original operation by
exact job ID; a failed/killed job remains uncertain because it may have produced
partial effects. Shell command display descriptions/timeouts do not defeat
same-command detection. Arbitrary shell strings are never inferred read-only.
Only explicit tool contracts and the pinned read operations get that treatment.

Third-party tool authors can attach this optional trusted-code contract to the
registered ToolDefinition (it is not model-facing):

```js
augmentorExecution: {
  effect: args => args.operation === 'inspect' ? 'read' : 'external',
  outcome: (args, value) => ({status: value.receipt ? 'completed' : 'unknown'})
}
```

Effects: `read`, `change`, `external`, `unknown`. Outcomes use the statuses above;
`jobId` is optional. Use `failed-before-dispatch` only when the operation provably
did not start. Use DSH's `exec.concludeTurn()` for authoritative handoffs. Invalid
or throwing contracts fail conservatively. Result text, model arguments and
retrieved pages cannot supply a contract. Unclassified successful tools retain
transport acknowledgment only; unclassified errors are uncertain.

The ledger is private, in-memory and per turn; sidecar diagnostics retain only
status/effect counts represented as entries, without arguments or job IDs. It is
not a cross-session transaction ledger or an exactly-once guarantee. Semantically
equivalent commands expressed differently, effects outside registered tools,
and hidden partial failures in adapters without canonical outcome contracts are
not automatically resolved. Existing durable unresolved-call detection remains.
Restart never automatically resumes a task. Changed scopes, compensation and
external reconciliation require the normal user-directed workflow. This layer
adds no authorization, new approvals, model routes or task-specific rules.

Qualification uses real pinned DSH with deterministic provider fixtures plus
pure outcome-contract tests. Cases include lost acknowledgment, repeated sends,
read-after-error, background job collection, handoffs after truncation, malicious
result text, cancellation and shared recovery budgets. It establishes lifecycle
behavior, not real-model task competence or cross-session memory quality.
