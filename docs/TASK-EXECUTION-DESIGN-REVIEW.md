<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Task execution harness: challenge review

20 September 2026. Design review only; no runtime changes or deployment.
Companion to [the implementation plan](TASK-EXECUTION-HARNESS-PLAN.md).

## Decision

Retain the goal and the separation of model decisions from execution evidence.
Change the implementation order: test a small improvement to tool-result reporting
before building the proposed task store, model-facing task tools, and lifecycle UI.
The full architecture is a candidate destination, not an approved dependency of
every reliability improvement. Expand it only where experiments demonstrate need.

The original plan covers many mechanical risks but moves too quickly from one
observed incident to a general task-management subsystem. That could produce
cleaner internal records without improving what the agent actually does.

## Blind spots and design corrections

| Risk | Why the original plan is insufficient | Change and evidence required |
| --- | --- | --- |
| The same model defines the goal and judges success | Valid JSON, source references, and a finish call do not prove the interpretation includes every important user constraint. Wrong criteria can make wrong work look verified. | Distinguish verified operation effects from interpreted task completion. Preserve original requests and test omitted constraints, not only valid state transitions. Use independent fixture outcomes and human constraint review. |
| Planning overhead degrades the fixed model | New task tools add schema/context burden and may require additional inference steps. “Inside the existing loop” does not mean no extra calls or latency. | Begin without new task tools. Measure inference steps and tokens separately. Require later task operations to earn their cost through observed gains. |
| Too much infrastructure before causal evidence | Store, reducer, adapters, task UI and recovery could all change at once, making it impossible to identify the useful part. | Run a narrow result-reporting experiment first, then controlled additions. Keep independently valuable corrections independently shippable. |
| Missing capability mistaken for weak reasoning | Better task state cannot create an absent operation. A more verbose blocker is not increased ability to complete a solvable task. | Separate capability availability from selection/interpretation in evaluations. Keep tools identical between experimental arms; test capability additions in a different comparison. |
| Stronger guards make an already hesitant agent stop more | Broad stale-state rules or recovery quotas can penalize legitimate exploration, batch work and long operations. | Hard blocks only for demonstrated executable contradictions or existing permissions. Semantic uncertainty gets concise feedback. Measure false blocks and avoidable user intervention as primary outcomes. |
| Unsupported tools bypass the intended guarantees | Browser checks do not cover a shell or another connector changing the same resource. Incorrectly treating unsupported paths as prohibited can also cripple a general agent. | Publish the coverage boundary. Preserve existing tool access, but keep unsupported effects unverified. Test equivalent actions through different tools; never call the whole task verified based on a covered subset. |
| Task journal diverges from the real world | Two journals, transport retries, crashes, and external changes can leave durable but stale state. Internal deduplication does not make external effects exactly once. | First reuse existing event logs. If a task journal proves necessary, specify reconciliation and orphan handling. Say “one admitted resume per dependency revision,” not guaranteed exactly-once external execution. |
| One conversation contains multiple intents | A question, new task, correction, and cancellation can arrive in the same conversation. One mutable task record can mix them or block unrelated work. | Treat task/session relationship as one-to-many. Scope corrections explicitly; ambiguous scope must not rewrite or cancel all tasks. Add interleaved-task and partial-completion cases before durable task-state rollout. |
| A dependency is mistaken for a failure | Eventual consistency, build progress, downloads and indexing may return repeated states while legitimate work continues. | Recovery policy uses operation semantics and expected state changes; the suggested retry counts are experimental parameters, not universal law. |
| Structured evidence becomes false authority | External text can contain instructions or fabricated status fields. An envelope produced by the harness does not make embedded page/document content trustworthy. | Separate executor-observed metadata from external content and model inference. External content never sets authorization, evidence validity or task status. Include adversarial-content fixtures. |
| Model/tool compatibility is assumed | Rich schemas or a different result order may reduce comprehension or truncate the useful content on the selected model. | Test compact human-readable rendering versus existing results; retain raw tool content and image delivery. Pin exact model, template, tool schemas and loaded adapter versions. |
| Evaluation overstates confidence | Three trials are a smoke test, not a reliable estimate of stochastic quality. Shadow decisions cannot prove their own false-positive rate without an outcome oracle. | Use independent expected outcomes, paired resets, run-order balancing, confidence/variation reporting and more repetitions where results overlap. Freeze decision rules before candidate evaluation. |
| Maintenance burden shifts to every adapter | Resource revision and effect semantics differ; plugin upgrades can invalidate validators. | Version coverage and validator provenance. Unknown compatibility becomes unverified coverage, not silent trusted enforcement. Do not promise universal semantic verification. |

## One move with the best initial leverage: factual tool receipts

Replace ambiguous tool acknowledgments with a compact, executor-grounded report
of the operation's actual outcome. This is the first experiment, not a claim that
all failures come from formatting.

For covered actions, return the same small set of facts:

```text
Operation: update the selected document
Target: document D, revision 12
Execution: succeeded
Observed effect: revision advanced to 13; requested field now has value V
Not established: whether this document is the one the user intended
```

For a navigation operation the receipt might report the actual tab/window,
whether a tab was created or reused, and observed active/focus state. It must not
infer visibility from successful navigation, or invent desktop focus from browser
metadata. For a write without readback it must report acknowledgment and leave
persisted contents unverified.

### Scope of the experiment

1. Add a small shared result normalizer/renderer using existing post-execute hooks
   and tool executors. Keep the existing model, prompts, permissions, tools and
   execution owner unchanged, apart from necessary result-contract descriptions.
2. Cover at least two domains: browser actions and one existing file/artifact
   operation. Derive facts from native executor results or already available
   observations; do not add automatic readback or tool calls in this first arm.
3. Preserve underlying tool content, errors, images, call IDs and source references.
   Place the compact receipt where the selected model can see it. Avoid repeating
   large outputs or returning fields whose meaning the executor cannot support.
4. Distinguish executor-observed facts, externally supplied content, and unknowns.
   The renderer must never guess that a result satisfied the user intent.
5. Save receipts in the existing tool event stream. No new database, background
   scheduler, model-facing planning tools, evaluator agent, or live task monitor.
6. For unsupported tools, preserve current behavior and identify the limits of
   coverage. Do not fabricate receipts that merely paraphrase model expectations.

The change improves what the model can know after an action, rather than relying
on it to remember an abstract warning. It also creates better evidence for later
target guards and recovery decisions without committing to the full architecture.

### What this will not fix

- It will not create absent capabilities or fix target-selection bugs by itself.
- It will not prevent all unsupported claims in the model's prose.
- It will not make the model interpret every correction correctly.
- It will not independently certify that the user's entire task is complete.
- Existing tab lists already exposed some relevant facts in the incident; the
  model overlooked them. Richer receipts may help, but the benefit must be tested.

### Test the hypothesis before expanding

Hypothesis: with the selected model held fixed, precise action feedback reduces
unsupported claims and improves the next corrective action, with acceptable overhead.

Start with at least 12 synthetic scenarios, balanced across the two domains:
normal success, partial success, wrong-target evidence, changed target, unsupported
operation, and ambiguous/unknown result. Include a user correction and a repeated
unchanged observation where relevant. Match executor behavior across arms so that
improvement cannot be attributed to extra capabilities.

Baseline A uses current results. Candidate B uses receipts. An offline shadow run
can check data correctness, but **cannot establish model behavior improvement**;
that requires the unchanged model to receive each format in separate controlled
trials. Reset fixtures, alternate order, and reserve unseen variants. Begin with
five repetitions per arm/scenario for feasibility, then increase repetitions if
the evidence does not support a clear decision. This is not a claim of statistical
power in advance.

Primary outcomes: constraint-respecting verified success on solvable cases,
correct next action after a mismatch, unsupported success claims, appropriate
blocker/handoff on unsupported cases, and false blocks. Secondary outcomes:
model requests, tokens, wall time and unnecessary user questions. Simply stopping
more often does not count as improved performance.

Predefine correct outcomes and the adoption rule before trial runs. Adopt only if
the receipts are factually correct, candidate behavior improves without a material
regression on routine tasks, and the measured overhead is acceptable. If results
are mixed, inspect failure strata and test another small change; do not proceed
automatically to the larger state architecture.

## Revised decision ladder

1. **P0:** prove hooks and runtime identity; establish reproducible baseline.
2. **P0A:** test factual receipts with the unchanged model and capabilities.
3. If needed, test one correction-focused intervention using those receipts and
   the original user correction; do not introduce a full task ledger to obtain it.
4. Add deterministic target/version enforcement for demonstrated stale-target
   failures. Test whole-batch and interleaved-session semantics before broad blocking.
5. Add durable task state only for failures that require persistence, task
   dependencies or interruption recovery. Prove it improves behavior over the
   simpler configuration, including its inference overhead.
6. Add progress recovery and waits only where measured failure cases require them.
   Then qualify the reusable subset in Pi and the installed surfaces.

The end state remains extensible and shared; its size is determined by evidence.
This is an incremental product improvement program, not a requirement to implement
every planned abstraction before any benefit reaches the user.
