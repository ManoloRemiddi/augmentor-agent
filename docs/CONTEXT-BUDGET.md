<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Tool context budget

The [September 28 reliability correction](TASK-RELIABILITY.md) extends this adapter
with binary-evidence protection and advisory changed-command/progress checkpoints.
The [October 1 browser repair](BROWSER-OBSERVATION-REPAIR.md) preserves bounded
fresh browser observations for their first model step and adds direct recovery
references and literal excerpt search. The original contract below is historical
where it says every fresh result is trimmed before first use.

Augmentor's personal DSH presets now prune oversized tool-result text at each
step boundary, before the next model request. This uses DSH 0.1.5-rc.1's existing
`toolResultPruner` service and its configured head/tail budgets, independently of
the model's context capacity or automatic summary threshold.

Previously the upstream pruner ran only when compaction pressure qualified.
For example, a 1,050,000-token model with `thresholdRatio: 0.5` could accumulate
525,000 tokens before the configured tool-output limits took effect. A recorded
long diagnostic run accumulated roughly 360,000 characters of tool text,
including repeated tab inventories and two approximately 50,000-character dumps.
The output limit was configured but was not an admission limit.

`adapters/dsh-context-budget/index.mjs` is mounted inside the existing isolated
compaction group by `services/dsh/setup.py`, for both shared personal presets.
It respects existing pruner budgets. Fresh installations retain the package
budgets (8,192-character threshold, 4,096 head, 1,024 tail). It does not change
model selection, reasoning effort, model capacity or memory settings.

## Evidence and recovery

Pruning uses supported `compaction/prune` and replacement `tool/result` events.
Original events stay in the append-only session log, including tool identities,
errors and full content. Images and other rich blocks follow upstream behavior.
No completed tool is executed again and no summarizer/model request is needed.

`tool_result_excerpt` lists the last 20 large original results in this session
when called without arguments. Supply an original `seq`, code-point `offset`
and optional `limit` (maximum 2,048) to retrieve omitted text. It cannot read
another session. Text remains historical evidence, not new authority. The list
uses a 4,096-character cutoff; an already-known original seq can be read directly.

The human command `/trim-tools` applies the same deterministic trimming to an
idle existing conversation and flushes the saved session. It refuses active
agents and cancelled invocations. It makes no model call, so an unavailable
provider does not prevent this repair. Repeated invocation is idempotent.

After three identical outputs for the same tool name and canonical arguments
within a turn, one model-visible checkpoint asks the agent to reassess. It does
not prohibit user-requested polling, infer side effects from arbitrary tool
names, terminate the task, or claim success. Changes in output reset the count;
replacement notifications are not new executions. The ordinary execution
recovery contract continues to guard unknown outcomes and duplicate mutations.

## Qualification and limits

The real DSH fixture exercises a 1.05-million-token model: a 46 KB tool result is
trimmed before the next request, its omitted middle is retrieved correctly,
and the persisted log opens in a fresh process. Further cases cover repeated
results, other presets retaining upstream behavior, and manual repair without
inference or tool replay. Run `node --test tests/dsh-context-budget.test.mjs` with
the pinned DSH installation. Composition tests live in `tests/test_dsh_setup.py`.

This is a per-result text budget, not a hard cap on total context or a semantic
loop detector. Many small results can still accumulate. The checkpoint is model
guidance; it cannot guarantee good diagnosis. Head/tail pruning can omit decisive
middle evidence, hence the explicit excerpt tool. Replacing older effective
context invalidates the corresponding provider cache prefix; new outputs are
trimmed before their first use. Network timeouts, provider subscriptions and
upstream retry policies remain independent failure modes.

Installed activation must follow [desktop deployments](DESKTOP-DEPLOYMENTS.md):
stage a separate compatible artifact, point the owned preset composition to its
adapter, and load it only when the shared DSH host is idle. Source tests do not
prove installed adoption. Keep private histories and deployment backups outside
GitHub.

## September 27 installed evidence

Implementation `f420a22`, with the read-only recovery-contract correction
`4d20f92`, passed TypeScript check/build, 186 Node tests, six Python setup tests
and 40 focused context/execution tests after the final correction. The fixture
and live cases remain distinct: fixtures exercise inference using a deterministic
provider; live maintenance invoked only the non-inference command.

Compatible managed artifact `20260927-231655-bf3642fa` is selected, based on
`20260926-204300-30f1286f`, with artifact SHA-256
`7eb047cf13accc278d55878d6f4d719df61604268de8836cc03d6f9736b35ca8`.
Existing embedding, Home, speech, product version and other DSH integration paths
were preserved. The shared DSH host was restarted only after all tasks became
idle. An existing conversation's 30 oversized results were trimmed without
inference: 241,512 characters removed; projected message tokens decreased from
119,419 to 59,036. Its model selection, turn/step counts and original log were
preserved. This is the message component of the token estimate, not total input.

Both final Desktop and Browser preset generations report the staged adapter
active, and `/trim-tools` succeeds through each actual host command route. A task
that began on the preceding generation was preserved while the final, read-only
excerpt contract was loaded for new agents. Such already-loaded agents acquire
the final correction on their next natural reload; they already have early
pruning. Native windows remain on their previous UI artifacts and are online
with voice available. This correction runs in their shared DSH backend and does
not require closing their windows. `updatePending` still reflects the separate
native UI selection. No Mac or public-download rollout is claimed.

Private original-preset/session backups and rollback records remain outside the
repository. Rollback of this adapter requires restoring the backed-up preset
composition as well as selecting the prior desktop artifact; changing
`desktop.json` alone does not change explicit DSH preset module paths.


## Pi Harness port — October 10 candidate

The [Augmentor Harness candidate](AUGMENTOR-HARNESS.md) implements the deterministic budget on published Pi SDK 1.1.0. `packages/runtime/src/tool-budget.ts` uses public native context-edit drafts at `turn_end`, preserves earlier extension drafts, and repairs projected results before loading a session. It shares the existing pure Augmentor binary-evidence helpers; it does not import a DSH execution engine.

Limits count Unicode code points across text blocks: 8,192 threshold, 4,096 head, 1,024 tail and an original-entry recovery notice. Images and other rich blocks are preserved. Immutable originals stay in native Pi history. Fresh browser snapshots/tab inventories receive one model step within an aggregate 64,000-code-point allowance per boundary; binary text is still withheld. This is neither a total-context cap nor a display-payload budget.

Pi `tool_result_excerpt` accepts `entryId` rather than DSH `seq`, an offset, limit up to 2,048 code points and optional literal case-insensitive `find`. Its manager is scoped to the current native branch: sibling/future results are excluded. Binary originals cannot be recovered as small text excerpts. [Retained MCP HTTP failures](MCP-TRANSPORT.md#agent-recovery-of-retained-http-bodies) use that same explicit read path, validate exact retained byte prefixes, list metadata only and preserve complete/partial/unavailable coverage. A transport request ID is never presented as an agent tool call ID. The manual `session.trimTools` method and Harness button refuse active turns, work without provider calls on cold current-format histories and refresh a loaded owner using supported `refreshContext()`. Repeated repair is idempotent; original entry bytes and past actions remain.

`tests/pi-tool-budget.test.mjs` checks Unicode/image preservation, literal search offsets, binary protection, branch isolation and browser allowances. `tests/runtime.test.mjs` uses an actual Pi loop to verify bounded subsequent input, original recovery, coexistence with preceding extension drafts, and idle/cold repair without inference or replay. The subsequent [Pi advisory port](AUGMENTOR-HARNESS.md#advisory-reassessment-and-home-build-correction) adds repeated/error/progress checkpoints. Bounded action-aware recovery remains separate and unported. Old-format session migration, large-history performance and live workflow acceptance remain required before cutover.
