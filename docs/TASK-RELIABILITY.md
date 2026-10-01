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
tool results contain recognized errors, including mixed categories and failed commands inside
successful shell pipelines.
A separate checkpoint after eight completed tool calls asks whether further
investigation is necessary for the latest requested outcome. Each repeated error category and the mixed-error condition is warned
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

### September 28 installed Linux adoption

Implementation `5a7b496` is applied over selected `20260928-000201-bcc8c6e5`
(base artifact `bbb98668f777bd926705f047ed7fd8de4d0aa21303f4a16c046b6b9f148672ad`).
Only the context/execution adapter files and the native notice filter changed in
that compatible 0.2.11 artifact; the separate source branch targets current public
0.2.12. The candidate passed eleven native reply/history checks and authenticated
staging/promotion. Historical release `20260928-090939-8349fc33` was selected, with artifact
SHA-256 `25e2818df558e83ab82c57059213b322790be68f424f5a13b8659d937b5946db`.

Both owned personal preset module paths and ownership hashes were updated with
private backups. The shared host restarted after all tasks and native windows
were idle. Its actual Desktop and Browser compositions report both adapters
active; `/trim-tools` on separate diagnostic sessions returned the new sanitizing
contract without inference. The initial operator readiness probe used the newer
source adapter against the older installed product and correctly refused the
version mismatch. Rechecking with the matching staged adapter passed; no product
version was changed to bypass the check.

Primary, secondary and mobile then closed gracefully and reopened through the
canonical launchers. All three report this build, online/model-ready, voice
available, no restoration error and no pending update. Hash comparisons confirm
model settings and saved conversation selections were preserved. Source adapter
bytes match the staged copies. Private backup/rollback evidence stays local.

The shared DSH backend is active for Browser; this update does not require new
extension bytes. Browser already displays the policy notice. The installed Mac
and public downloads were not replaced. Source is published for review in
[PR #21](https://github.com/ManoloRemiddi/augmentor-agent/pull/21); merging and public
releasing remain separate operations.


### Follow-up from the full installed-model test

The first full personal-preset read-only check did not finish before its explicit
180-second diagnostic cancellation deadline (13 tool calls). The earlier restricted
tool proof therefore did not establish full-agent task reliability. The live result
exposed mixed CLI errors (`unknown option`, `command not found`, absent service)
inside shell pipelines whose overall results were successful. These were not counted
by the initial same-error-category detector. Parallel tool batches also delayed the
model-step-based progress checkpoint.

The follow-up recognizes those CLI diagnostics, counts three mixed errors in eight
results, and measures the advisory progress checkpoint after eight completed tool
calls rather than twelve model steps. The guidance asks the agent to reuse known
environment facts, discover installed utilities and read their help before guessing
low-level interfaces. It remains general guidance, not a monitor-specific command
rule or an authority/side-effect classifier. No reasoning effort was lowered to make
the proof pass. Subsequent validation and installed adoption are recorded below.


The follow-up implementation `1aaaa34` was adopted as
`20260928-092130-e736d3da` (artifact SHA-256
`d74cdde7c207663d35d2266aa41db01bc09c7cff48d19989221003759c4de154`).
All three native windows and both owned DSH presets adopted it while idle, with
model settings and selected conversations unchanged. Its full-preset read-only
check returned in 154 seconds with seven tools, but gave an incorrect answer:
it overlooked the installed KDE utility and misattributed physical output control
to an X server. This is failed answer-quality evidence, despite a completed turn.

The Linux system profile now inventories installed KDE, wlroots and D-Bus utilities
alongside X11 tools, with applicability and local-help guidance. Unprobed screenshot/
input portals no longer imply that ordinary desktop utilities are unavailable.
The report explicitly distinguishes XWayland presence from physical output ownership.
Discovery executes no new commands or controls; portal probing remains opt-in.
This OS-specific report is shared by the Linux DSH/Pi helpers; macOS discovery is
unchanged. Three Python checks cover mixed Wayland/X11 discovery, missing utilities,
private environment exclusion and explicit portal probing. Physical standby/wake
and general model answer quality remain separate from these capability checks.


### Final capability-report adoption

Implementation through `70c5c79` is selected/running as
`20260928-093018-2d4431f6`, artifact SHA-256
`43fb2a371dc59054dd7705836fb571ccae56a028bfb6fda6336eb61b507e18c0`.
This is a staged copy of the preceding compatible installed 0.2.11 artifact,
with only the Linux doctor implementation changed. Both owned DSH presets now
also resolve the desktop adapter from this release; that adapter and other Linux
helper bytes match their previously loaded copies. All three windows adopted it
while idle and report online/model-ready with preserved settings/conversation
selections. The source remains 0.2.12; no version check was bypassed.

Final local source regression: 194 Node tests passed; 542 native/Python tests ran
successfully with three environment-dependent skips. The prior unchanged Browser
suite passed 44 tests. The earlier TypeScript build/check passed. Linux/Home/
Browser/installed-package and macOS 14/26 CI passed for the preceding `1aaaa34`
revision; that does not qualify newer source or a new Mac installation.


The full installed personal-preset read-only retest on this final artifact completed
in 79.3 seconds using six tool calls. It inspected the updated profile, installed
`kscreen-doctor --help`, output inventory and `--dpms show`, identified
`kscreen-doctor --dpms off`, and reported physical standby/wake as unverified.
This qualifies command discovery and public completion for one observed run with
the actual personal context/tool set. It does not certify every sentence of the
answer, actual power control, future model reliability or a general performance
improvement. The final answer's closing reference to only two read-only queries
under-counted its other inspections; the recorded total is six tool calls.
No power-changing command was executed. The effective request still used xhigh
reasoning; 79 seconds remains slow for this task. Model/GPU settings were preserved.
Private full transcripts and rollback backups remain outside the repository.
