<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Keep conversational checks separate from historical work

Review date: 15 October 2026. An EDGE user sent a conversational responsiveness
test. The exact sentence reached the native controller, but two independent
context producers redirected the answer: a process-wide Olares identity hook,
then automatic memory matching generic testing/performance vocabulary to an old
network test. Correcting the external hook alone still produced an irrelevant
reference to the older work. Private conversation text stays outside Git.

The shared TypeScript selector now excludes conversational/check-in vocabulary
from lexical topic matching. An explicit network/download query still selects
related network history; a single specific topic such as SQLite still works.
The context prefix states that recalled unfinished work is not automatically
the current chat's task. Exact current-session user receipts, constraints,
source links, bounds, relationship preferences and explicit recall remain.
No journal or derived memory is deleted, and capture/inference policy is unchanged.

Single-file TypeScript compilation and six context cases pass. The cases cover
typed/voice paraphrases, preserved direct restrictions, specific topic recall,
bounded context and historical provenance. This is bounded lexical filtering,
not a semantic relevance guarantee or a replacement for the memory engine.

Deployment must preserve the existing desktop and memory component identities.
Stage a separate artifact, update only the intended backend memory binding and
record selected versus running scope. Never patch an installed release in place
or clear the user's memory database to remove an irrelevant recall. Existing
conversations can retain earlier context; preserve them in history and verify a
fresh conversation before reporting the correction effective.

The Olares hook is owned by the separate Olares repository. Its identity reminder
is now limited to its configured workspace; tool and approval guards remain
unconditional. That external fix is distinct from this selector change.

## Installed Linux/EDGE qualification — 15 October

Implementation `584aa3aa` was compiled/tested, then applied as the **only file
change**, `dist/memory/src/context.js`, to a separate copy of the active memory
artifact `20261003-144055-0fa10098`. `augmentor-update stage` imported and
inventoried compatible product 0.2.11 artifact `20261015-222707-b9de1ead`, SHA-256
`6394ad11e4183dab21642b22f513273511a8433cb5e2966b563ab5bccb77a38d`.
Compiled context SHA-256:
`bafbf9eb4fb3b9afd04fc3e16c039d6b2d1b31054b166cacc75ce367705618d3`.

This artifact is used **only by the Linux preset's backend memory entry**.
Desktop selection remains `20261015-155352-7466460c`; no desktop downgrade or
native/UI/speech/model update was activated. Browser/workspace memory bindings
are unchanged. The 0.2 profile's Linux entry was changed with all agents idle,
then reconciled through the manager while keeping the preset enabled. Inventory
reports the new memory module active. All other profile semantics are unchanged;
the manager added only an equivalent `disabled: false` override for that preset.
DSH, memory service and model services were not restarted; databases were not
cleared. Existing sessions can retain earlier context and loaded code.

An initial attempt targeted an inactive legacy `.agent-presets` file and staged
an older memory base. Runtime inventory exposed the mismatch; that legacy file
was restored byte-for-byte and that artifact was never activated. A reply during
that attempt happened to be appropriate while its input still contained old work
claims, so it did **not** pass the context check. The binding above uses the actual
0.2 composition, not the legacy path. A first reconciliation audit also expected
an in-place flag change; inspection established the manager's appended equivalent
enable override, and the complete semantic comparison then passed.

Final real-model replay used the exact owner prompt privately, the existing
native controller/backend and unchanged selected local Qwen model. It completed
in 9.89 seconds, gave a relevant conversational answer, contained **zero Olares
hook messages and zero recalled work items**, and made no tool calls. Original
chat history remains intact. EDGE was reopened idle with a fresh session binding
and the same model so the earlier injected context is no longer current.
This one replay is regression evidence, not a general model-quality guarantee.

Rollback is scoped: restore only the Linux preset memory module name to its
previous artifact and reconcile that already-enabled preset, preserving later
configuration changes. The owner-local backup includes the original profile and
chat binding. Desktop rollback is unnecessary because selection did not change.
