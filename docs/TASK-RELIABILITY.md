<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Task reliability: tool evidence and reassessment

The September 28 correction addresses a failure pattern where an agent repeatedly
misreads command errors as unavailable capabilities, expands a simple request into
unnecessary research, consumes binary output as text, and ends with no public
answer. It improves the shared DSH execution path; it does not certify task
completion or promise that every model will follow a checkpoint.

## Behavior

Both personal DSH presets use the existing context adapter and execution lifecycle.
Before the next request, binary-like text blocks in tool results are replaced with
an explicit omission notice. Originals stay in the append-only session history;
result identity, error flags, other text blocks and non-text blocks are retained.
Standard `compaction/prune` and surface replacement events preserve cold replay
and token accounting. The heuristic detects NUL, three non-text control characters,
or four Unicode replacement characters; ordinary Unicode and ANSI colour sequences
are allowed. It can withhold legitimate text containing those characters and cannot
detect every binary encoding. Withholding is neither a permission denial nor proof
of command failure.

Original-result excerpts list short binary-like results as well as large text.
A binary original cannot be reintroduced through a small excerpt: the tool returns
a notice instead. Inspect its source file with a suitable decoder or archive listing.
`/trim-tools` also sanitizes existing tool context without inference or action replay.

The model receives an advisory reassessment checkpoint when three of the last eight
tool results contain the same recognized error category, even when arguments differ.
A separate checkpoint after twelve tool-bearing model steps asks whether further
investigation is necessary for the latest requested outcome. Each category is warned
once per turn. The existing identical-result checkpoint remains. These checks do not
infer success, halt long tasks, change permissions, or authorize retries. Error text
is evidence for guidance only; it never changes the execution action ledger.

Reasoning-only recovery now explicitly asks the model to reassess the last command
and the latest request. On the last automatic attempt, it asks for a concise partial
handoff if no supported next action is known. Existing retry, time, token and action
limits remain. An empty final attempt still produces an explicit incomplete notice.

Native Linux and macOS show the existing saved-versus-requested reasoning notice in
both live and restored history, matching Browser. This supersedes the September 22
exact-notice hiding rule. No layout changes or reasoning-policy/model/GPU changes
are made. The saved picker value can still be overridden by Adaptive Reasoning;
the actual request value is now visible. Provider enforcement remains independent.

## Qualification

Run the normal build first, then:

```sh
node --test tests/dsh-context-budget.test.mjs tests/dsh-execution.test.mjs
PYTHONPATH=apps/native QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -p 'test_reply_completion.py'
```

The pinned real-DSH fixtures cover changed-command failures, continued long work,
turn resets, binary omission and excerpt protection, original evidence retention,
normal multilingual/coloured output, bounded recovery, user Stop, uncertain actions,
permissions and cold history. Native Qt checks cover live/reopened policy visibility
and incomplete notices. Shared backend behavior applies to Desktop and Browser;
Pi does not use these DSH adapters.

`node scripts/task-reliability-proof.mjs` is an opt-in local-model check. Set
`AUGMENTOR_PROOF_MODEL_CONFIG` to a private JSON file containing `provider`, `model`,
`settings` (the provider configuration) and `effort`; supply the referenced credential
through its environment variable. Only numeric loopback HTTP model endpoints are
accepted. Each separate proof session has a four-minute cancellation deadline. The
only executable desktop probes are fixed read-only argument arrays; the synthetic
fault tool has no system effects. Output defaults to ignored
`outputs/task-reliability-live.json`; never commit private model configuration.

Source validation: TypeScript check/build, 192 Node tests, 44 Browser tests,
and 539 native tests (three environment-dependent skips) passed. The initial
full-native attempt lacked websocket/PyYAML in its test venv; rerunning with the
complete existing test runtime passed.

The September 28 local-model run used the existing local Qwen route with its xhigh
request effort, context and precision unchanged. The first case identified the
installed display-standby command and current state in two read-only tool calls.
The second consumed three synthetic interface errors and binary text, received the
combined checkpoint, then inspected the real interface and produced a public
conclusion with verification limits (five tool calls). This demonstrates model and
adapter interoperability with restricted tools. It is not an A/B benchmark, a test
of the full 107-tool personal context, physical standby/wake qualification, or proof
of a general model-quality fix. The model still made an inference about the synthetic
error's cause; successful lifecycle tests do not validate every answer claim.

## Deployment

Source, selected desktop artifacts and loaded DSH presets are separate. Preserve
existing local source edits and selected runtime dependencies. Follow
[desktop deployment](DESKTOP-DEPLOYMENTS.md), stage a separate compatible artifact,
and update both owned preset module paths only after checking shared-host idle state.
An existing agent can retain its loaded module until reload. Preserve drafts,
conversations, model configuration, speech and unrelated preset entries. Rollback
requires both the previous desktop selection and backed-up owned preset files.

Installed evidence is appended after candidate verification and activation; the
source changes alone do not update an open window or running DSH generation.
