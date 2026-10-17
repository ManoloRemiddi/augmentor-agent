<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Streamed tool arguments in the original Trajectory

[Current installed MX preview](HARNESS-BRANCH-CONTROLS.md#ordinary-and-installed-mx-qualification--october-13): runtime **a0c2011**,
release **20261013-090703-abddfcd6**, product **0.2.13**, selected and running.
Original message Branch and sidebar/keyboard Fork guard duplicate clicks, late
responses, changed drafts and explicit same-child reconciliation. Source/ordinary
each pass **380/380 across 74 files** plus five packaging cases; **68 immutable
tests** and installed original Context Insights reads pass. All **23,895** entries
and twelve histories/queues, drafts, profiles and model processes verify. Supplier
GUI/CSS, 580 MIT/108 Apache records, licence bodies and dependencies are unchanged.
Full migration, cold unconfirmed-branch recovery, live/privacy/distribution/platform
gates and CI failures remain open. Further OS implementation awaits MX feedback.

Earlier qualification checkpoints below are historical.

The copied DSH Trajectory now receives tool-call argument updates from the public
Pi SDK while the assistant is still generating. Its existing pending Tool row and
Payload panel show the proposed arguments; Started remains unavailable until a
public SDK tool-execution-start is observed. That event marks the pipeline before
validation/approval, not proof of approved dispatch or effects. Streaming a proposal grants no execution
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
completion time/usage remain unknown. Public SDK tool-execution-start/end events
populate running/settled seats; an error/result does not certify effects.
[Nested tools](TRAJECTORY-NESTED-TOOLS.md) retain explicit child relationships and
bounded start arguments without changing execution. The original supplier renderer, widgets,
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

At this historical source-only checkpoint, selected/running private MX remains
timing runtime 008ef295 / release 20261013-030020-abfa89ec. This checkpoint is
superseded by the final installed qualification below. The binding is
shared platform-neutral SDK/presentation code, with Linux Chromium qualification;
other-OS implementation remains deferred for owner MX feedback. Nested running-call
presentation, unlinked request attribution and the complete P0/P1/live/privacy/public
distribution/platform gates remain open. DSH remains available for unqualified
workflows.


## Request-scoped presentation identity — October 13 correction

The historical interim runtime b80c609 is selected in immutable private MX release
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
unchanged; the corrected source is not installed at this checkpoint. The held fixture later
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

## Ordinary and installed MX qualification — October 13

Final tested runtime **a49d58da343e17f7e671b203906979384b49528c** is selected and
running in private MX release **20261013-054009-ab664123**, product **0.2.13**,
artifact SHA-256
**f8d7431feb00d883dca0efe91dbc26a389835fa05ed13333ef0be7908a592f45**.
The final source and separate ordinary artifact each pass **358/358 across 70
files**, zero failures/skips/cancellations, with Node **24.19.0**, two workers,
unchanged deadlines and matching isolated QtTest. Each also passes the five
notice/workspace packaging cases; final strict check and build pass.

The ordinary assembly matches **663 compiled files**, **20,801 production
dependency files**, **151 npm instances**, **nine native/Wasm executables** and
**783 licence files**. All three generated distribution records and inherited
dependency/Node/native/licence bytes remain unchanged. All **580 MIT DSH GUI** and
**108 Apache-2.0 dsh-context** supplier records, layout and CSS remain unchanged
by this increment. No supplier or dependency is added. This is qualification of
the private MX preview; public distribution requirements remain open.

Supported update staging creates a separate immutable candidate. Explicit idle
and draft checks precede guarded Native/Host shutdown, actual process absence,
activation and sequential stable-launcher Host/Native startup. The selected Node
executable and runtime main match the candidate, and all **23,890** inventory
entries verify before and after GUI reads. Earlier immutable releases are retained
without modification. Documentation closeout does not replace this runtime.

**26 immutable tests** pass: six argument contracts, nine shortcut scope
contracts, the two actual original-GUI Chromium cases and nine existing DSH
contracts. The SDK/Host/browser cases use the immutable runtime and bundled Node
with authored controlled providers; pure projection/scope checks exercise the
matching assembly source. This is separate from owner live-provider evidence.

Manual acceptance on a separate authored installed profile uses two turns and the
same raw SDK call ID. The first held proposal displays pending arguments and is
Stopped with **zero dispatches**; its assistant stays aborted/Failed without a
fabricated result. The second proposal opens **Turn 2**, stays selected through
completion, and shows its own `note.txt` arguments, real read result, schema and
measured tool interval. Exactly **one tool dispatch/result** and **three wire
requests** occur across both turns. Explicit Trajectory reopening and second-call
selection after browser reload retain the correct Turn 2 details and request
count, without replay. Raw SDK IDs remain unchanged; distinct observer captures
and the actual request bind the second proposal/dispatch/result. Fixture stderr
is empty. Its browser tab and exact supervisor/Host are closed and actual process
absence is checked. The recorded 6 ms fixture read is not a performance claim.

Actual owner Insights opens with **eleven nonarchived metadata entries**, **seven
newest contexts** and **zero failed/partial/usage-gap reads**; its **21 older calls**
receive no invented SDK timing. No owner prompt, endpoint listing, credential
entry or configuration write is performed. After GUI reads, all **twelve** owner
histories/queue identities remain preserved, with twelve total sessions and no new
empty placeholder or request. Of **247 saved files**, **243 are byte-identical**;
one journal retains its exact prior prefix plus one close/one load, with three
corresponding derivative updates. Draft/attachment bytes, profile values/revision,
model/auth profile presence and bytes, production selection and router
executable/arguments remain preserved. Qwen/Breeze GPU placement and CPU ASR/VAD
remain unchanged. Canonical main's 38 pre-existing changes remain untouched.

Earlier lost-patch, shortcut notification and reused-ID failures remain retained
comparators, not passing evidence. The final source/ordinary/immutable/manual
checks above supersede the interim b80c609 qualification. CI at preceding published
head **188d9a1f7be85d1e4de61c78f3073a6d650294ff** is not fully green: inspected
Windows command-job logs fail on FortuneSheet's missing Immer default export;
Mac 14/26 packaging refuses unreviewed Darwin Office MPL-2.0/libvips
LGPL-3.0-or-later and missing reviewed Koffi licence text. Debian logs contain
file-preview, shortcut-recorder and Pi Browser trajectory timeouts; packaged
installation/browser jobs are skipped. Other reported contracts, desktop,
component, shared Qt, source-boundary and Home checks have successes. These are
prior-head results, not qualification of the new publication head; local MX
passes do not establish Debian or other-platform acceptance.

Full P0/P1 migration, nested running-call presentation, unlinked request
attribution, owner live-provider/privacy/public-distribution and physical/platform
gates remain open. Other-OS implementation remains deferred for owner MX
feedback. DSH remains available for unqualified workflows; no public binary is
published.
