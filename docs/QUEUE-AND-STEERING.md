<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Native queue and steering

## DSH

Enter during a running DSH response clears the composer immediately and adds a compact pending row above it. The DSH server owns accepted queued prompts and starts them after the active turn. Steer promotes the existing item with `session.updateQueue`, using its message ID. During text generation, the Linux steering hook cancels the obsolete model request while keeping inbox work, then wakes DSH with the same identified correction ahead of ordinary follow-ups. During a tool execution it waits for the next safe step boundary. It never resubmits a new copy of the prompt. The remove control removes that pending item. Stop remains available beside the queue/send control.

The `session/control` stream provides a complete queue baseline and live replacements. Each prompt carries a stable request ID, so optimistic rows are reconciled with backend items and delivered user messages. Ordered admission preserves rapid Enter submissions, including while the initial chat is being prepared. Transport failures are not automatically replayed; the row preserves the text and reports an unconfirmed outcome. Session switching and reconnect generations isolate queue updates.

This native queue UI is enabled for the DSH adapter, which advertises support. Codex source support is recorded below; Pi does not advertise this queue UI. The browser panel is unchanged by the original DSH feature.

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
Unknown active work must first be reconciled. Browser does not yet expose the
running-turn queue panel, promotion or removal controls.

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
