<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Original plan mode on Pi

The Harness retains the original MIT DSH plan chip, full review panel, plan cards
and sidebar. Its root conversation's existing Pi AgentSession owns the mode,
request guidance and `exit_plan_mode` tool. The separate [reported plan/todo
registry](PI-PLANNING.md)
continues to store progress; reviewing a plan does not update its steps or create
a persistent goal.

The pinned [original contract](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/plan/plan-mode/README.md)
uses advisory guidance, a persistent per-conversation state and human review of
the exact submitted Markdown. Tool availability and action permissions remain
independent. The port uses supported Pi extension tools/input handlers, public
Agent context hooks and custom SessionManager entries; it mounts no DSH agent or
plan backend.

## Use the controls

Type `/plan` to enter, `/plan <message>` to enter with the next instruction, or
`/plan off` to leave. Message and attachment admission retain the existing durable
queue and identified steering path. A queued command takes effect when dispatched;
an active-turn selection waits for the next model request. `/plan off` with
attachments is rejected before a mode change or queue admission. Bare mode
commands perform no inference and leave a new conversation's title available for
its first actual instruction. Their notices report the selected mode directly.

The plan-mode capability is explicit: older and other backend adapters retain
their existing reported-plan command when it is absent.

The original command-menu Plan action enters the mode after confirmed admission;
late replies cannot consume an edited draft or another conversation's selection.
The original chip occupies its original input-bar slot, shows the effective target
and lets an operator leave the mode. The existing Plan tab still opens reported
steps. Both upstream chip files/CSS are verbatim, pinned in the supplier receipt;
the MIT selection is **593 files**.

The model can call `exit_plan_mode` with complete Markdown beginning with a
same-line `#` heading. The validated document is at most 65,536 characters and
must fit the common 128 KiB question envelope. The original sidebar shows the full
submitted plan, including code. Its renderer retains the image-fetch opt-out.

**Approve** records the exact offered choice and selects an exit for the next
request boundary. The current tool batch retains its previous mode. **Keep
planning**, including custom feedback through the shared question contract,
returns that feedback with planning guidance still active. The original GUI's
**Request changes** closes this mode review and concludes the agent turn so the
human can write the next request. An armed persistent goal's automatic continuation
is disarmed; its objective and active phase remain intact. A saved plan card
reopens the submitted document without inference or filesystem reads. Generic
`ask_user` plan reviews keep their existing hide/reopen dismissal behavior.

Plan reviews start in the existing `waiting` phase, with no foreground deadline,
so reading a long plan does not silently time out. Operator liveness is checked
at the existing one-second interval. SDK abort, Stop, owner settlement and loss
of the interactive connection still end the review without an invented answer.
Action approvals retain their separate hard timeout and cannot select this
question-only waiting policy. Settled reviews do not accept late answers.

## State, ownership and observation

`augmentor/plan-mode-v1` is a private native custom entry containing a revision,
logged `active` value and optional pending human target. Whole-value replacements
use the selected native ancestry. Idle selections commit immediately; selections
during work commit their effective value at the next accepted request-context
boundary. Selecting the logged value cancels an opposite pending target. The tool
catalog remains stable while entering/leaving; every changing tool keeps its
existing role, sandbox and approval checks.

Pi creates a native file after its first user or assistant message. Before that,
the mode uses a private metadata bootstrap record. Loading restores that record
to the new native manager; the first real conversation message flushes the native
entry, and the metadata fallback is then removed. Existing native files remain
authoritative. No new model request is used to materialize an empty session.

Explicit human pending targets survive restart. A reviewed exit stays transient
until its request boundary; extension reload discards that uncommitted approval.
A superseded selection, cancelled signal or changed extension generation cannot
apply an old answer. Missing/invalid state fails explicitly and preserves its
original. Loaded reads identify native-session memory; cold reads distinguish
saved native entries from the pre-conversation metadata bootstrap. No failed RPC
or uncertain append is automatically replayed.

The request-only guidance is applied after Pi's forced-prompt projection, through
the public Agent context hook. This preserves both memory-supplied prompt text and
the selected planning section, without changing the tool declarations. Compaction
and other non-admitted contexts do not consume a pending selection. Local
`planning/mode` observations record mode/revision metadata; complete plan bodies
and decisions retain the existing private tool-history and payload-capture scope.

`session.planMode` reads loaded or cold state. `session.setPlanMode` requires an
operator, a current revision and an eligible root conversation. Read-only
inspectors can read their scoped state and cannot mutate it. Archived/delegated,
compaction, model-account and resource-reload guards remain effective. The GUI
retires stale reads across newer refreshes, selection and reconnect, and updates
from peer mode notifications.

## Qualification and remaining work

The [separate Linux owner review](HARNESS-MX-REVIEW.md#separate-plan-mode-review--october-15)
now includes this mode on sealed runtime bd03b15. Its full sealed-target cohort
repeats 419/two optional skips/zero failures; the installed selection stays separate.

The new contracts exercise revisions, cancellation/no-op, corrupt records, actual
SDK compaction-entry ancestry, a refused append, forced prompt/tool preservation,
cancelled/unadmitted contexts, old reviews after reload and retired controller
reads. Real isolated SDK/Host/provider cases cover pre-chat restart and native
handover, saved native restart, exact branch ancestry, pending state after Stop,
message/attachment refusal, approval without write permission, feedback,
dismissal, Stop, inactive calls, an armed goal, Browser tool boundaries, queue and
identified steering. Original Chromium controls exercise both themes, the chip,
full review, Request changes, approval, saved reopening, reload and peer changes.

The first private request-hook attempt lost guidance after a forced prompt; its
failing test is retained. The post-projection hook preserves that prompt and the
planning section. A Browser-surface probe also retained its actual policy refusal
before the communication tool was added to the Browser allowlist; native tools
remain excluded. Earlier fixture-only failures are recorded separately from
product qualification. A separate retained command-menu control fails before the
explicit capability check and passes after it.

At **bd03b155f8478419a50bfb84edd9ac0e7cc42d78**, strict check/build and source/fresh
ordinary each pass **419/two optional skips/zero failures**, across **86 files**,
including all **47 Harness Chromium files**, with two workers per cohort and
unchanged bounds. Each also passes five separate interaction-wait cases; thirteen
shared offscreen dialog and eleven packaging/source-boundary cases pass. All
**1,019 compiled files** and **3,268 tracked inputs** match after testing; the
production dependencies remain 20,702 files/symlinks and 151 npm instances. All
593 supplier inputs verify, including the two verbatim MIT chip files; the prior
591 rows are unchanged. All four sealed inventories, five review processes,
selection and 38 canonical pre-existing changes verify; Qwen catalog and the
preceding review respond HTTP 200. That earlier review runs runtime ea3775b and
does not contain this plan-mode implementation.
[Portable qualification and exact cohort](../release/harness-plan-mode-qualification.json).

The first hosted run at d7e6318 passes Linux/macOS but fails Windows while
preparing the private companion, before any mode assertion. The source Windows
supervisor requires Qt; that workflow installed only pywin32. Its qualification
setup now uses the exact hash-locked Qt/shiboken/pywin32 subset of the existing
Windows x64 product lock. No runtime, test deadline or platform assertion changes.
The retained failure remains evidence; a passing new Windows run is still needed
before claiming that platform or the failure's complete cause qualified.

This is Harness/source integration, not installed adoption or complete migration.
Physical MX feedback, representative live providers, actual manual compaction with
active planning, hard-crash/write-fault coverage, complete attachment combinations,
floating Native/browser-extension presentation and platform release artifacts
still need acceptance. General late answers and question-draft persistence across
page reload remain separate gaps. The approved GUI, model/speech/GPU settings,
installed selection, prior owner reviews and the Office distribution boundary
remain preserved.

The first dependency-setup commit (32e6435) retained an invalid YAML plain scalar
containing `:all:`; its workflow did not start any jobs. The corrected folded
command parses locally and preserves every locked-install argument. This is
retained separately from the earlier actual Windows companion startup failure;
new hosted qualification remains required.
