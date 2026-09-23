<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Native DSH queue and steering

Enter during a running DSH response clears the composer immediately and adds a compact pending row above it. The DSH server owns accepted queued prompts and starts them after the active turn. Steer promotes the existing item with `session.updateQueue`, using its message ID. During text generation, the Linux steering hook cancels the obsolete model request while keeping inbox work, then wakes DSH with the same identified correction ahead of ordinary follow-ups. During a tool execution it waits for the next safe step boundary. It never resubmits a new copy of the prompt. The remove control removes that pending item. Stop remains available beside the queue/send control.

The `session/control` stream provides a complete queue baseline and live replacements. Each prompt carries a stable request ID, so optimistic rows are reconciled with backend items and delivered user messages. Ordered admission preserves rapid Enter submissions, including while the initial chat is being prepared. Transport failures are not automatically replayed; the row preserves the text and reports an unconfirmed outcome. Session switching and reconnect generations isolate queue updates.

This native queue UI is enabled for the DSH adapter, which advertises support. Other harnesses do not advertise steering support yet. The browser panel is unchanged by this feature.

Reference interaction was checked in the installed Codex app's queued-message component: its Steer action applies an existing queued follow-up to the active run without interrupting the current model call. DSH implementation was checked against the installed 0.1.5-rc.1 `session.prompt`, `session.updateQueue`, and `session.control` APIs.

Verification: a real local-model DSH session queued two distinct prompts, promoted one to steering, then recorded the steering input before turn/end and the follow-up afterward, each exactly once. Native regression tests cover immediate entry, promotion without resubmission, duplicate clicks, consumed-event races, failure text retention, sequential admission, and cancellation during initial preparation.

A follow-up live regression test reproduced steering during a long story generation, not only during a tool call. The original request ended as superseded, the correction was delivered about 20 ms after the click, and the untouched follow-up ran afterward. The implementation uses public agent lifecycle hooks, `cancel({keepInbox:true})`, identified inbox operations, and `steer`; no private driver state is modified.

A second live test steered while a sleep command was executing. The command completed exactly once without cancellation; the correction was delivered afterward, and the other queued follow-up remained intact.
