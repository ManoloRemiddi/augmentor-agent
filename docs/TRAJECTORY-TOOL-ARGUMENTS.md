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
The first snapshot carries its full JSON base. Every update carries an opaque
message-capture ID and per-call revision; patches name their exact predecessor
revision. These are observer identities, not invented provider/request IDs. A
missing base or update, changed call identity, wrong request/message scope or
invalid patch shows an explicit unavailable block rather than borrowing earlier
arguments. A new unlinked SDK message cannot extend an older one. Per-request
timings still require an actual recorded request identity.

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

Five deterministic contracts cover sampling/final flush, exact Unicode patches,
interleaved calls, private-extra-field omission, missing/foreign/malformed bases,
Stop/completion, cyclic/oversized/count/budget failures and next-message recovery.
An actual isolated SDK/Host/Chromium test holds a deterministic provider's proposal,
inspects the original pending payload with **zero dispatches**, Stops it, and reopens
without replay. A second held proposal completes one real read; browser reopening
preserves its history with exactly three wire requests across the two turns.

The first focused GUI check expects an internal call ID as visible text; inspection
shows the original Payload panel renders arguments and Pending/unknown-start status.
The check is corrected to those actual controls without supplier changes. Final
focused source qualification initially passes **14/14**, and the first complete
source MX cohort passes **354/354 across 70 files**. Review then adds a lost-update
regression: the preceding d4e9510 code incorrectly applies a later patch to an old
base, yielding a valid but different argument value. The failure is reproduced
and retained before correcting capture/revision checks. Final focused source
qualification passes **15/15**, zero failures/skips/cancellations, including lost
updates and new unlinked messages. The revised complete run has **354/355 passes**:
the original shortcut test times out reopening the first window's reference while
the second window records a binding. An unchanged focused pair passes once, then
the failure reproduces; an explicit document-focus wait does not resolve it.
Temporary source diagnostics prove the first client is ready but its preference
scope is loading after a delayed self settings notification. The source probe and
its bundle are removed. [Attested shortcut settings revisions](HARNESS-SHORTCUTS.md#attested-settings-revisions--october-13)
prevent that redundant self reload while retaining peer/authority invalidation.
The combined argument/shortcut contracts and actual Chromium pair pass **15/15**.
The next full run has **355/356 passes**, exposing the same notification arriving
before an in-flight save reply. The scope now defers that notification until the
write settles, accepting only an exact tagged confirmation or reconciling newer
stored state without replay. Confirmed/peer/lost-reply contracts and the actual
Chromium pair pass **16/16**. Earlier failures and source diagnostics are retained.
Final strict check/build pass; the final complete source cohort passes **357/357
across 70 files**, zero failures/skips/cancellations, with Node **24.19.0**, two
workers, unchanged deadlines and matching isolated QtTest. Five notice/workspace
packaging cases also pass. Ordinary, immutable and manual installed qualification
follow separately.

Current selected/running private MX remains timing runtime 008ef295 / release
20261013-030020-abfa89ec; this source increment has not replaced it. The binding is
shared platform-neutral SDK/presentation code, with Linux Chromium qualification;
other-OS implementation remains deferred for owner MX feedback. Nested running-call
presentation, unlinked request attribution and the complete P0/P1/live/privacy/public
distribution/platform gates remain open. DSH remains available for unqualified
workflows.


## Request-scoped presentation identity — October 13 correction

The initial runtime b80c609 is selected in immutable private MX release
20261013-044026-4424a11e (artifact
a7905617fcadf79105104f9f09830ec4d50cad228d650524db957c53e4b30715).
Source and ordinary each pass 357/357 across 70 files and five packaging cases;
25 immutable contracts/Chromium cases pass. A separate actual installed manual
check confirms live pending arguments and zero dispatch on Stop, with an aborted
assistant retained as Failed. Owner Insights and the shortcut reference open
without a model request or preference edit; all twelve histories/queues and
23,889 entries verify. This evidence does not qualify complete reused-ID behavior.

The second manual held proposal uses the same provider call ID. Selecting its
second-turn Tool row opens the first turn's details: the copied renderer expects
unique presentation IDs, while valid Pi call IDs can repeat across requests. The
failure is retained as an installed screenshot and a pure regression reproduces
against the exact b80c609 authored projection. The immutable artifact remains
unchanged; the corrected source below is not installed yet. The held fixture later
settles without exposing Stop; it is inspected as terminal and its exact supervisor
is closed. That wait is not used as completion or tool-effect evidence.

The authored adapter now namespaces internal call identifiers by the Host turn
and actual request ID, or the observed message-capture ID when no request hook
exists. SDK IDs remain unchanged in native/recorded events, and are retained
separately as sdkCallId in presentation data. Final messages and actual tool
start/end display events carry the capture identity from the existing subscription.
There is no invented provider request, another SDK owner or supplier UI change.

Older events use their retained same-owner proposal/dispatch ordering. Tool results,
running seats, schema lookups and timings bind the same request; missing/ambiguous
timing records remain unknown. Chat tool rows gain their real dispatch sequence and
read that dispatch's proposal/result, avoiding an earlier same-ID argument object.
Projection never modifies the source events. The test checks repeated IDs across
turns and SDK requests within one Host turn, raw-ID preservation, exact result/
argument/schema/timing association, and unlinked message captures without invented
request timing. The enhanced actual Chromium case selects the second proposal and
keeps its details through completion. Its first check is occluded by the composer
at Chromium's small default viewport; the test now states its actual 1280×720
acceptance geometry without changing product layout, deadlines or concurrency.
Focused source passes 16/16 and strict check/build pass. Final source/ordinary/
immutable/manual qualification follows; full migration and platform gates remain
open, and further OS implementation still awaits owner MX feedback.

Final corrected source check/build and the complete Node 24.19.0 MX cohort pass **358/358 across 70 files**, zero failures/skips/cancellations, two workers/unchanged deadlines/matching QtTest. The old b80c609 projection fails the exact reused-ID regression; corrected source passes it. Ordinary and final installed acceptance follow separately.
