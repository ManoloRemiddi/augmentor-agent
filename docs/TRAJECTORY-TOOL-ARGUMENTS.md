<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Streamed tool arguments in the original Trajectory

The copied DSH Trajectory now receives tool-call argument updates from the public
Pi SDK while the assistant is still generating. Its existing pending Tool row and
Payload panel show the proposed arguments; Started remains unavailable until a
real SDK tool dispatch is observed. Streaming a proposal grants no execution
authority, creates no running-tool receipt and invokes no tool.

## Ownership, representation and limits

The existing AgentSession subscription observes public `toolcall_start`,
`toolcall_delta` and `toolcall_end` events. The adapter reads only the public
ToolCall ID/name/arguments at that content index. These are **SDK-parsed argument
objects**, which can be incomplete or repaired by the SDK parser during generation.
They are not raw provider JSON fragments or proof of a completed proposal. No
private SDK properties or new agent loop are used.

One message-scoped observer samples delta snapshots at most every 50 ms per call;
start/end updates are not delayed. Identical snapshots are omitted. Changes use
bounded prefix/remove/insert patches in UTF-16 code units, preserving exact JS
strings, including Unicode, without journaling repeated complete JSON prefixes.
The first snapshot carries its full JSON base. A missing base, changed call identity,
wrong request scope or invalid patch shows an explicit unavailable block rather
than borrowing earlier arguments. Per-request timings still require an actual
recorded request identity.

Capture is bounded to 128 calls per message, 512 KiB per serialized argument object,
2 MiB of retained latest arguments and 2 MiB of encoded snapshot/patch capture.
Overflow, unserializable arguments or a missing base leave a visible gap; call-count
or cumulative capture exhaustion freezes this live capture until the next message.
The SDK's actual proposal, validation, execution and native persistence are unchanged.
Diagnostic failures are contained within the existing display observer.

These patches are **private conversation display history**, with the existing
authenticated/session-scoped reads and conversation retention policy. They are
not metadata-only observation records. Tool arguments can contain private content;
turning provider-payload capture off does not delete conversation/tool history.
No telemetry exporter, credential UI, model settings or network dependency is added.

Final assistant messages replace the provisional blocks, including SDK-aborted
messages. An absent final message freezes its captured prefix as interrupted;
completion time/usage remain unknown. Only actual public tool dispatch/results
populate running/settled tool seats. The original supplier renderer, widgets,
layout, CSS and all 580 MIT/108 Apache supplier source records are unchanged.

## Qualification and deployment boundary

Four deterministic contracts cover sampling/final flush, exact Unicode patches,
interleaved calls, private-extra-field omission, missing/foreign/malformed bases,
Stop/completion, cyclic/oversized/count/budget failures and next-message recovery.
An actual isolated SDK/Host/Chromium test holds a deterministic provider's proposal,
inspects the original pending payload with **zero dispatches**, Stops it, and reopens
without replay. A second held proposal completes one real read; browser reopening
preserves its history with exactly three wire requests across the two turns.

The first focused GUI check expects an internal call ID as visible text; inspection
shows the original Payload panel renders arguments and Pending/unknown-start status.
The check is corrected to those actual controls without supplier changes. Final
focused source qualification passes **14/14**, zero failures/skips/cancellations.
Strict check/build pass. The complete source MX cohort passes **354/354 across
70 files**, zero failures/skips/cancellations, with Node **24.19.0**, two workers,
unchanged deadlines and matching isolated QtTest. Ordinary, immutable and manual
installed qualification follow separately.

Current selected/running private MX remains timing runtime 008ef295 / release
20261013-030020-abfa89ec; this source increment has not replaced it. The binding is
shared platform-neutral SDK/presentation code, with Linux Chromium qualification;
other-OS implementation remains deferred for owner MX feedback. Nested running-call
presentation, unlinked request attribution and the complete P0/P1/live/privacy/public
distribution/platform gates remain open. DSH remains available for unqualified
workflows.
