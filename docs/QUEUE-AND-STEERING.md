<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Queued prompts and steering

## DSH

Enter during a running DSH response clears the composer immediately and adds a compact pending row above it. The DSH server owns accepted queued prompts and starts them after the active turn. Steer promotes the existing item with `session.updateQueue`, using its message ID. During text generation, the Linux steering hook cancels the obsolete model request while keeping inbox work, then wakes DSH with the same identified correction ahead of ordinary follow-ups. During a tool execution it waits for the next safe step boundary. It never resubmits a new copy of the prompt. The remove control removes that pending item. Stop remains available beside the queue/send control.

The `session/control` stream provides a complete queue baseline and live replacements. Each prompt carries a stable request ID, so optimistic rows are reconciled with backend items and delivered user messages. Ordered admission preserves rapid Enter submissions, including while the initial chat is being prepared. Transport failures are not automatically replayed; the row preserves the text and reports an unconfirmed outcome. Session switching and reconnect generations isolate queue updates.

This native queue UI is enabled for the DSH adapter, which advertises support. Codex source support is recorded below. The original DSH feature did not advertise Pi support or change the Browser panel; the October 10 Pi candidate below adds durable waiting inputs and a separately qualified responsive-steering slice.

Reference interaction was checked in the installed Codex app's queued-message component: its Steer action applies an existing queued follow-up to the active run without interrupting the current model call. DSH implementation was checked against the installed 0.1.5-rc.1 `session.prompt`, `session.updateQueue`, and `session.control` APIs.

Verification: a real local-model DSH session queued two distinct prompts, promoted one to steering, then recorded the steering input before turn/end and the follow-up afterward, each exactly once. Native regression tests cover immediate entry, promotion without resubmission, duplicate clicks, consumed-event races, failure text retention, sequential admission, and cancellation during initial preparation.

A follow-up live regression test reproduced steering during a long story generation, not only during a tool call. The original request ended as superseded, the correction was delivered about 20 ms after the click, and the untouched follow-up ran afterward. The implementation uses public agent lifecycle hooks, `cancel({keepInbox:true})`, identified inbox operations, and `steer`; no private driver state is modified.

A second live test steered while a sleep command was executing. The command completed exactly once without cancellation; the correction was delivered afterward, and the other queued follow-up remained intact.


## Codex development integration

The Codex native adapter now enables the same Enter/queue, Steer and Remove
controls. Presentation and placement are unchanged. The shared host owns waiting
items and emits `session/queue` baseline/replacement frames on the existing event
subscription. Delivered user messages include the queue request identity, so
optimistic rows disappear when native Codex receipts reach the transcript.

Steer promotes the existing ledger item atomically with its original identity.
The controller passes the active turn ID observed in its queue snapshot; the
host refuses stale targets and never substitutes a new turn. Waiting items can
be removed, and rejected items can be dismissed while their durable records stay
available. Dispatched or uncertain inputs cannot be removed or silently retried.
Uncertain rows retain their text and disable both actions. New admission is
bounded by 100 waiting/visible queue items and 512 KiB of serialized queue state,
leaving room for the client frame envelope. It refuses overflow before dispatch.

Stop persists a paused queue across worker/host restart. Reconnecting alone does
not resume it. A deliberate idle Send resumes remaining waiting prompts in FIFO
order and appends the new prompt after them; `session.continueQueue` is also an
explicit host operation. Both native and Browser idle Send use this contract.
Unknown active work must first be reconciled. Browser running-turn controls
are qualified in the following checkpoint.

The real offscreen Qt fixture drives Enter, Steer and Remove through the native
controller/adapter and private IPC into pinned Codex. It reconnects the event
stream, restores a waiting row, verifies removed prompts never reach inference,
delivers the steering correction in the first turn and the untouched follow-up
in the second, then checks native identities after host restart. The provider is
synthetic. This is Linux source/Qt/runtime evidence, not physical desktop use,
installed activation or macOS runner evidence for this exact checkpoint.

Local checks: 293 root Node tests (including the Qt/runtime fixture), 48 Browser
DOM tests, eight shared queue UI tests and 16 focused Codex Python tests. Build
and type checks pass. See [Codex evidence](CODEX-INTEGRATION.md#native-queue-controls-and-durable-pause)
and [agent handoff](AGENT-HANDOFF.md) for remaining C0–C9 work.


## Codex Browser queue

Codex Browser now uses Enter/Send during a running turn to add a compact waiting
row above the composer. Stop stays available. Each row has Steer and Remove;
they use the same host admission/promotion/removal contracts as native Desktop.
This Codex slice left DSH/Pi Browser sending behavior unchanged. Read-only views, disconnected
panels and a changed session cannot issue queue mutations.

The native bridge forwards subscription queue snapshots. The service worker
keeps current-session queue state separately from transcript history and returns
it when the panel reloads. Queue mutations carry stable request and observed-turn
IDs. Local submissions and actions are serialized, including typing immediately
after Steer. A failed acknowledgment retains the pending text; native delivered
message IDs suppress duplicate/late optimistic rows. Nothing is automatically
resent after a disconnect.

The ledger now persists a monotonically increasing queue revision across pause,
mutations and host restart. Browser ignores older snapshots, preventing a delayed
poll response from resurrecting removed rows. Missing revisions in older ledger
files start at zero; the host emits the explicit revision on every snapshot.

The loaded isolated Linux Chromium test types into the real composer, clicks
Steer and Remove, reloads the panel, verifies waiting-row restoration, and runs
an untouched follow-up in the next native Codex turn. The synthetic provider's
actual inputs prove the correction appears once, removed text never arrives,
and the follow-up arrives only in the next turn. The previous observed browser
click/type/screenshot proof also passes. A captured panel image was visually
inspected: two compact rows fit above the composer and Send/Stop remain visible.
This is source/isolated evidence, not the owner's installed Chrome profile.

Build/type checks, 294 root Node tests and 53 Browser DOM tests pass locally.
The preceding native queue source `3fd287b` passed both macOS jobs in
[36750430904](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36750430904).
Its [Debian application checks](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36750430782)
passed before packaging stopped at the known unreviewed Codex executable gate.
Mac loaded-browser/device qualification and complete release remain separate.


## Pi durable waiting queue — October 10 candidate

The Augmentor Harness branch adds one persistent FIFO around the supported Pi session. Harness, Native and Browser accept Enter while working, preserve stable IDs, remove existing waiting items, reconcile delivery by `source.rpcId`, and restore complete monotonic queue baselines after reconnect. Stop, error and cold restart pause waiting work. An explicit idle Send resumes older waiting inputs before the new input; reconnect alone does not. Unknown dispatched receipts cannot be removed, steered or automatically retried. Keep interrupted acknowledges that receipt and leaves waiting work paused, with an honest persisted notice; it does not verify an external action.

This historical queue-only checkpoint reported queue support but **no responsive steering yet**. Waiting items never enter Pi's transient string queue; each normal follow-up is admitted through the existing SDK session only after its predecessor settles. The bounds, crash semantics, actual Qt/Browser-bridge/GUI evidence and full suite counts are recorded in [Harness qualification](AUGMENTOR-HARNESS.md#durable-prompt-queue--october-10-source-candidate). The following steering slice supersedes its capability declaration; the full P0 gate remains open. Existing DSH and Codex semantics are retained.

## Pi responsive steering — October 10 source candidate

The current Pi owner advertises queue and steering. Steer promotes the existing waiting item, preserving its request identity, fingerprint and accepted text. Native, Browser bridge and Harness provide the active turn ID from their queue snapshot. The host rejects stale targets, Stop or a settling turn before promotion. A repeated click cannot submit a second correction; one correction may await delivery, and later corrections may follow after delivery.

The AgentSession's public owned Agent queues an identified user message. A separate abort signal cancels only the obsolete provider request, so the SDK continues within that same session and host turn. Tools already dispatched retain their original run signal and settle before the correction; obsolete later proposals are blocked. Ordinary FIFO follow-ups begin after the original SDK prompt finishes. The per-turn action ledger keeps completed and unknown outcomes across corrections, allowing reads while blocking duplicate mutations or new changes after uncertain actions.

Stop pauses the product queue, clears the SDK queue, and restores only owned corrections still present in the public queue preview to waiting work. Unconfirmed selected delivery remains unknown. Cold recovery marks active/promoted nonterminal receipts unknown and never resends them. A confirmed delivery carries the original request ID in `user/message.data.source.rpcId`; identical text cannot confuse receipt ownership. Terminal receipt settlement is atomic with the root turn.

That historical source slice passed literal product text through the public owned Agent and declared input-handler/skill/template expansion unavailable. The approved-input follow-up below supersedes that limitation. Actual SDK generation/preparation/payload/tool/Stop/crash tests, real offscreen Qt controls, the scoped Native Messaging bridge and the Harness GUI pass with independently authored synthetic inputs. Exact source, full suite counts and remaining full-migration gates are in [responsive-steering qualification](AUGMENTOR-HARNESS.md#responsive-steering--october-10-source-candidate) and [the protocol](PROTOCOL.md). Source qualification does not remove DSH or change an installed release.

## Pi approved steering input — October 10 source candidate

The identified correction now runs the public SDK input chain (`rpc`, `steer`), followed by only the session's approved skills and loaded templates. Transform chains retain image content. Selected MIT Pi argument/substitution functions preserve quoted arguments, defaults, slices and nonrecursive replacement; their original notice ships beside the compiled utility. Registered extension commands fail before queue admission/promotion. Browser retains its restricted extension/resource policy.

Promotion remains synchronous and durable; asynchronous processing does not hold the host state lock. Obsolete generation stops immediately, and the public SDK finish boundary waits for preparation and its durable result. A handler may consume the correction: its receipt completes once with no claimed model delivery, and a durable notice/execution `input-handled` outcome explains it. Duplicate actions do not rerun handlers. Stop releases even a stuck processing handler; its receipt becomes unknown and waiting work stays paused. Late results cannot restart the provider. Failure and process death during preparation likewise never cause automatic handler/input replay.

Display history retains the original submitted text separately from prepared native SDK content. Native/Browser/Harness Chat and Pi conversational memory prefer the original words; Context and branch matching use actual prepared SDK content. This preserves exact branch/edit behavior without presenting expanded instructions as the user's typed message. Handled notices are not memory items.

Implementation source `2f40eb7801fa68e995a90c8dcb672efa46c7c9b1` passes real SDK transform/image/template/skill/handled/command/async/Stop/crash and exact branch fixtures, actual Qt Steer and scoped Native Messaging bridge checks. The Harness GUI shows original submission after reload and expanded text in Context. Full counts and evidence scope are in [SDK input qualification](AUGMENTOR-HARNESS.md#sdk-input-compatibility-and-original-submissions). Loaded Pi Chromium, representative live providers, full prompt/command controls and installed/platform acceptance remain separate migration gates.
