<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Original question controls on Pi

The original MIT DSH QuestionComposer now binds its countdown, **Take time**, editing and focus controls to the same Pi Host that owns the question. Supplier components, CSS and licences are unchanged. This is an Augmentor UI/Host binding through Pi 1.1.0's supported ExtensionUIContext, not a second question service or conversation loop.

The Host supplies a revisioned `wait` snapshot on `question/requested`: phase, remaining foreground budget and a deadline when counting. The initial budget is the smaller of the extension's requested timeout and the managed default (120 seconds unless explicitly configured). Validated plan reviews start waiting with that foreground budget paused, retaining operator liveness and cancellation; action approvals cannot use this policy. `interaction.wait` accepts only the exact pending question, session and operator client. Take time changes the question to waiting; the first edit changes it to editing. Both remove the foreground deadline until answer, cancellation or disconnection. Extension AbortSignal, parent/child Stop and owner settlement continue to cancel the request. This foreground-pause policy is implemented by the supported custom UI adapter; it does not promise an unmodified wall-clock timeout while the operator pauses it.

Focus temporarily freezes the pristine budget. Each client has a separate 15-second lease, renewed every four seconds while the selected question remains focused and polling succeeds. Releasing one client cannot release another's focus. The last release or expired lease resumes the remaining budget. A browser crash cannot retain an indefinite focus hold. The Host checks continued UI availability at least once per second; after the last operator watch expires or the last native subscriber disconnects, unanswered questions settle without an answer. Read-only inspectors cannot pause, engage, focus or answer.

Approval requests retain their existing hard timeout and cannot use these pause controls. They do not silently acquire indefinite approval waiting. Late answers and wait controls fail after settlement. Question expiry resolves the actual SDK dialog with no answer; no later-answer channel or fabricated “work continued and you can still answer” state is exposed. No answer, model request or external action is retried by these controls.

The browser reads canonical phases and revisions, ticks only the displayed remaining count and never settles a question using its own timer. Older event/RPC snapshots cannot replace newer state. A stable original pending carrier avoids releasing focus during an ordinary timing update. Draft stores are scoped per conversation, so another conversation cannot prune or display an unfinished answer. The original store now persists each conversation separately in browser local storage; collapse/remount, conversation switching and full page reload preserve its current unfinished answer and page. [The scoped binding](#conversation-scoped-saved-question-drafts--october-15) replaces the earlier shared-key behavior. Pending Host questions do survive page reconnect within the running process; Host restart does not reconstruct or replay them.

[Persistent advisory plan mode](PI-PLAN-MODE.md) now binds the original chip and
review to the same Pi owner. Generic plan-intent questions retain their existing
hide/reopen behavior; `exit_plan_mode` dismissal concludes its active turn.

## Conversation-scoped saved question drafts — October 15

The copied MIT store already implemented browser `localStorage` persistence, but
our binding created every conversation with its default shared key. The earlier
memory-only description was inaccurate. An actual two-conversation original-GUI
control reproduces the first conversation's lost unsent note after reload; the
second conversation's draft still restores. Initial driver-only failures used a
wrong pager label and then an incorrectly quoted selector; those remain distinct
from the retained exact-content failure against the sealed bd03b15 control.

The binding now passes the exact conversation ID to the original store's supported
scope argument. Original components, styles, navigation, choices, custom text,
explicit Skip and waiting controls are retained. The latest pending snapshot
prunes only the selected operator conversation's settled drafts; loading, changed
selection and read-only scopes cannot prune another conversation. Ordinary
refreshes do not rewrite unchanged drafts. Returning to a resolved conversation
clears its scoped draft; no answer or model/tool operation is sent by restoration.

For compatibility, only an exact currently pending request ID in the old shared
record may migrate. Question count, page, offered selections, wait vocabulary,
text and byte bounds are checked; an existing scoped draft wins. The old record
stays untouched because an older open client may still own its content. This is
local browser state, not native tool history or a second answer channel. Browser
storage unavailability retains the original non-fatal in-memory controls; it
cannot guarantee reload restoration in that case. Host restart still settles
pending dialogs rather than reconstructing/replaying them.

Strict check/build and six focused files pass **46/46** on Linux. The original
513×715 GUI checks independent notes/pages/selections in two real SDK conversations,
exact unchanged native/display histories, two provider requests and no submissions,
then Stop and selected-snapshot cleanup. Fourteen common binding cases cover
migration/refusal/storage/selection and cleanup. Full source/ordinary results and
publication scope follow: at **df5aa20374a03f026d5cf174d32915edf69d83a2**, source
and fresh ordinary each pass **439/two optional skips/zero failures**, across
**89 files/all 48 Harness Chromium files**, two workers and unchanged bounds.
All **1,019 compiled/3,274 tracked files** match after testing. The 20,702 production
dependency entries/151 npm instances, Node 24.19.0, 1,932 browser-test entries,
593 supplier inputs and original CSS remain unchanged; runtime bytes retain
bd03b15. Eleven packaging/source-boundary cases pass. All five sealed inventories,
six review processes, selection and 38 canonical changes verify; Qwen/current
review respond HTTP 200. That preceding bd03b15 review lacks this fix; the newer
[drafts/cold-history review](HARNESS-MX-REVIEW.md#drafts-and-cold-history-review--october-15)
now includes it on 6bc2b0d and passes the 91-file sealed-target cohort.
[Portable qualification and exact cohort](../release/harness-question-draft-qualification.json).
Installed owner reviews, prior sealed builds, selection and model/speech settings
remain unchanged. Physical MX, live providers, other platform presentation,
late-answer continuation and the complete migration gates remain separate.

## Structured batches and original plan review — October 15

The following is the preceding structured-batch checkpoint; its draft limitations
are superseded by the scoped-store qualification above.

Native-profile `ask_user` now accepts either its existing `question`/string
`options` call or `questions`: an ordered batch of stable IDs, text, optional
headers/details, labelled options/descriptions and multi-selection. It registers
through a product extension on the existing public Pi tool lifecycle, beside the
same native-tool enablement boundary. It is no longer an OS helper's single-question
wrapper. Browser/Home and desktop-specialist grants are not expanded. The ordinary
SDK `select`, `input`, `editor` and `confirm` bindings retain their earlier behavior.

A batch is limited to eight questions, sixteen choices per question and 128 KiB
in total. Question/answer text is at most 16,000 characters; detail is at most
65,536. Duplicate/blank IDs or choices, mixed legacy/batch inputs and incomplete
plan intents are refused before a question is published. A submitted answer must
name every question exactly once, with unique offered selections and single/multi
cardinality. A single-select custom answer replaces selection; the common Qt
dialog now matches that existing DSH encoding. Empty selections without custom
text record the human's explicit Skip. Partial, duplicate, foreign or malformed
answers fail before settlement and leave the same pending question available.
An explicit cancellation, tool AbortSignal, Stop, owner settlement or disconnect
returns no invented answer. No automatic resend/replay is added.

The existing original QuestionComposer supplies paging, multiple selection,
custom answers, Skip, Take time and per-conversation drafts. A current root-owned
tool question may hide and reopen from its exact latest tool row without
answering or making an RPC. Stale duplicate tool-call IDs cannot reopen the old
row; changed selection/generation/phase/access and resolution retire the local
hidden state. The original close copy now reflects that hide behavior. Questions
without a matching root tool row, including the earlier SDK-dialog and delegated
carriers, keep their cancellation path rather than becoming unreachable.
Hiding alone does not pause the existing foreground budget; Take time still
owns that choice. A page reload restores a pending Host question, with earlier
draft-persistence limits unchanged.

One complete question with `intent: {kind: "plan-review", approve: "<offered label>"}`
and plan Markdown in `detail` uses the original MIT DSH PlanReviewPanel,
PlanReviewOpen, PlanPreview/Title and PlanCards. The full plan opens in the original
right sidebar and retains its original narrow/fullscreen and Light/Dark CSS.
**Request changes** hides the review and returns to the composer without an
answer, approval or model continuation; its tool-row opener restores it.
**Approve** returns the asker's exact offered label once. This decision grants
no tool permission and does not mutate the separate planning registry. Submitting
changes uses the existing explicit input/queue/steering controls. A saved plan
card can reopen the exact submitted document from the current tool's retained
arguments/result after page reload, without inference or filesystem reads.
Read-only inspectors retain ordinary argument/result/native inspection; this
operator-sidebar opener does not expand their authority.

Eight additional pinned public DSH files supply the plan components, style,
locales, transient review store, address helpers, error text and package notice.
Seven are verbatim; PlanPreview has a marked image-policy adaptation. The existing
QuestionComposer has the same small adaptation: untrusted question/plan Markdown
renders text and image alternatives without fetching remote or local images.
No layout or supplier CSS is rewritten; no DSH agent/plan backend is mounted.
The MIT selection is now **591 files**. Product and other dependency licences
remain distinct. Temporary plan navigation/drafts stay in UI memory; actual
question arguments and answers persist in private native SDK tool history.
See [data scope](DATA-AND-SUPPORT.md#question-batches-and-plan-previews).

Focused runtime/SDK/controller checks pass **31/31**, common Qt dialog checks
**5/5**, and one actual original-GUI/SDK flow passes at **513×715**, including both
plan themes. A controlled preceding sealed artifact fails the same complete-batch
case because the old `ask_user` schema requires a single `question`; its original
SDK validation error is retained. The corrected flow submits three complete
answers, hides/reopens a selected multi-choice draft, reads the entire plan,
hides/reopens Request changes without a provider request, approves once and
reopens the saved plan without replay. Actual provider inputs and two native tool
results are checked; new detail/preview renderers attempt no external image URL.
The separate SDK case rejects a partial reply, cold-resumes real prior tool
context, keeps legacy text replies and cancels a waiting batch through Stop.
Preceding implementation **5eba45a0453808be5bd9b6d32317cb199d1a0e9a**: source and fresh ordinary each pass **388 checks / two existing optional Codex
skips**, zero failures/cancellations, across **81 files / all 45 Harness Chromium
files**. Both retain two workers and unchanged deadlines. All **1,013 compiled
files / 2,149 executable inputs** match; the 20,702 production dependency entries /
151 npm instances, bundled Node 24.19.0, 1,932 browser-test dependency entries and
82 source-built Office entry files retain their existing bytes. Nine Office
public-gate and two source-boundary regressions pass without relaxing refusal.
[Portable checkpoint](../release/harness-question-batches-qualification.json)
records exact source, scope and retained failures.

A final presentation follow-up supplies the original shared locale fallback to
the copied plan components. Code-containing plans now expose readable code/copy/
wrap labels instead of raw locale keys. The same actual full-plan test includes
a fenced code block and checks its readable toolbar in both-theme qualification.
The earlier separate ordinary assembly is retained as a controlled negative;
final source/ordinary results and source identity are recorded in the portable
checkpoint rather than relabelling the earlier 5eba45a counts.

The locale product remains **d8520d5fe6b7e8eaa232835be54ec0759b88c566**.
Its initial full source repeats **388 pass/two existing optional skips**; its fresh
ordinary cohort retains **387 pass/one failure/two skips**. The one failure is
`codex-browser-chromium`: after six actual synthetic provider requests and five
function-call outputs, the final model input has no screenshot image. All new
question/plan cases pass. The first failure did not retain the tool-output body,
so its exact transport/target/permission cause is unproven. Six isolated private
diagnostic runs and one later source/ordinary case each pass, but do not
supersede that failed full cohort. The unchanged assertion now includes authored
tool outputs with image bytes omitted on failure; it adds no retry or timeout
change. Final compiled/executable/dependency parity still verifies. Qualification
and promotion remained **incomplete** at that checkpoint; the failed result is retained.

The subsequent [toolbar fixture correction](CODEX-INTEGRATION.md#verified-fixture-toolbar-selection--october-15)
**14224cb** establishes the actual work-tab selection before Chromium's toolbar
command. A controlled wrong-tab negative fails with permission denial; the exact
corrected positive and four paired ordinary runs pass. Full source and ordinary
now each pass **388/two optional skips/zero failures**, across the same 81 files/
45 Harness Chromium files, with two workers per cohort and unchanged deadlines.
Application/GUI/permissions remain unchanged. This qualifies those local cohorts;
it does not prove the original lone failure's sole cause or installed/live/full
migration acceptance. [Portable follow-up](../release/harness-browser-toolbar-qualification.json).
Preceding b1b1986 SDK Linux/macOS/Windows, Home and both Windows desktop jobs pass;
its broader Linux run retains one post-Unarchive reopening GUI timeout (1,234
pass/one failure/44 skips). New-head hosted and all remaining release gates stay open.

Plan-review intent retains the same configured foreground question bound; it
does not establish indefinite plan-mode waiting. Long-review behavior, alongside
the original full plan-mode bridge, remains to qualify.

Retained driver failures are explicit: an unsupported `session.open` RPC,
incorrect original Approve/text-row selectors, one newly quoted selector producing
a syntax error, and assuming a legacy Light preference followed OS dark mode.
Drivers now use actual history/explicit continuation, original accessible labels
and the private profile's System choice; scope and deadlines are unchanged.

At preceding **476d7be**, the [three-OS SDK contracts](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/38692312973)
and [Home job including both actual Pi image modes](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/38692313466/job/116280861710)
pass. The wider Linux run retains a Context placement-menu `Tab` pointer failure;
its exact cause is unresolved and this local passing cohort does not establish
that older hosted interleaving or a fix. New-head hosted and Mac/Windows packaging/
job qualification remain separate.

This is shared source and isolated Linux qualification, not an installed owner
update. Pending questions are not reconstructed after Host restart; no late-answer
continuation channel, generic settled-question composer reopening, persistent
answer draft, automatic plan-mode/command bridge or physical/live-provider
acceptance is claimed. The original full plan-mode controls and remaining
migration/platform/privacy/distribution gates stay open. The common contract/
controller cases enter the existing Linux/macOS/Windows SDK matrix; physical Mac/
Windows implementation remains deferred for owner MX feedback.

## Qualification and remaining scope

Pure runtime cases exercise countdown, multiple focus clients, lease expiry, Take time, edit engagement, exact-session denial, hard approval timeout, explicit timeout, AbortSignal, owner Stop, disconnection and late/duplicate refusal. Controller cases exercise stale/read-only selections, revision ordering and a lost control reply without retry. The actual SDK cohort holds a question beyond its original 300 ms budget, sends the human answer once, and separately cancels an engaged question with Stop without another provider request.

Original Chromium controls at 513×715 use the real Interactions coordinator to verify countdown, Take time, confirmed waiting, answer selection and collapse/expand without losing the draft. A separate actual Pi SDK/Chromium case uses an independently authored approved extension and loopback provider: original Send invokes the question; Take time survives the original three-second deadline and page reconnect with one provider request; original Submit delivers one answer; verified native originals contain the real tool result; saved reopening adds no inference. Fixtures use public SDK/UI contracts and independently authored data, not private histories or repository source.

Retained initial failures were fixture issues: a deferred mock response was asserted before its JSON callback existed; the new browser case used `Send` instead of the supplier's actual `Send message` label (an initial escape replacement did not change it); native metadata was mistaken for the separately readable original body. Fixtures now await the actual response boundary, use the original label and read the hash-verified native entry. No product assertion, deadline, permission policy or supplier UI was weakened. The authored question fixture uses the existing read-only `ask_user` registration name rather than granting another tool new authority.

The source/ordinary/installed checkpoint is recorded in the current handoff and MX preview. Installed live-provider questions, full plan-mode and generic settled-question composer reopening, full original command/UI parity, persistent answer drafts, other platforms and the complete Harness/migration acceptance remain open. Linux source evidence does not qualify physical macOS/Windows installations; those implementations remain deferred for MX feedback. Existing DSH paths remain available.

Final source passes **203/203 across 27 files**, zero failures/skips/cancellations, prepared QtTest/two workers/unchanged deadlines. The preceding 202-case cohort passed before the integrated SDK/browser case was added. One first final runner exited 143 (SIGTERM) before its terminal summary; authoritative process inspection confirmed it had stopped with no matching owned fixture left. The termination cause is unestablished. The unchanged cohort retry passes all 203 checks. No timeout, assertion or configuration is relaxed. Ordinary and installed acceptance remain separate checkpoints.

## Installed MX qualification — October 11

The tested runtime **65b0a498e93d8453062f63eaf9e0806101f39fed** is selected and running as private MX **20261011-184609-8cac1bd0**, product 0.2.13, artifact SHA-256 **8c9c01c8e3d53a384c63bbc2211ab0f545bb1568fbdacbc06cbcaaf780a16615**. Ordinary idle shutdown, updater staging/activation and stable Host/Native launch succeed. Both roots match selection; Native is online/model-ready/idle. Full **21,742-entry** verification passes before and after browser reads. All eleven baseline histories and queue identities remain unchanged, with no new installed histories/admissions/provider requests. Production selection SHA-256 remains **cb426b4a2daa960f66533f28fb2b164385c243c1ba53fc18e61ca33fb4256be7**; the existing model-router process and model/speech/GPU/context/concurrency/precision settings are preserved. The original Context stats, retained request body and Apache notice are visually inspected at normal **513×715** and remain selected for feedback.

Source and fresh ordinary bundled Node **24.19.0** each pass **203/203 across 27 files**, with zero failures/skips/cancellations, prepared QtTest, two workers and unchanged deadlines. All **475 compiled files** match source. The assembly preserves **19,160 production dependency files / 131 npm instances**, **723 licence files / 96 browser notice records**, supplier selections/source hashes/CSS and six native executable paths/hashes. Inherited native records are validated; the pre-existing public Debian Sharp/libvips collector/source/rebuild gate remains open and is not relaxed.

An additional separate visual SDK fixture uses an independently authored question and loopback provider, with a 30-second starting budget for manual inspection. Original Send/Take time displays confirmed waiting; original Submit produces one real answer through two provider requests. The original panel is visually inspected at the normal wide **1280×720** browser size; the qualified automated cases cover 513×715 and the original three-second deadline/reconnect. This is synthetic source execution, not an installed live Qwen question. The temporary fixture/tab close cleanly and its screenshot remains supplementary private evidence. It does not add installed history or alter the installed model/profile.

Retained preparation failures: the first private assembler was invoked from the candidate directory rather than source, so it found no source dist/Node and the attempted ordinary command exited 127 before testing. Running the unchanged assembly procedure from source resolves it; only the complete verified assembly runs the passing ordinary cohort. Native maintenance.close returns accepted, rather than a closed field assumed by the first probe; process inspection confirms the acknowledged Native exited before ordinary Host shutdown. No close is repeated and no forced kill is used. The first whole-source comparison for retiring the prior redundant Compact assembly encounters requirements-codex.txt, intentionally excluded by the installed manifest. Runtime/dependencies/Node/licences are then compared explicitly; whole-source equality is not claimed.

Disk headroom is recovered only by retiring the prior redundant Compact assembly and this turn’s redundant ordinary question assembly after matching **20,351 runtime/dependency/Node/licence files** to their retained immutable installed selections. Source commits, selected releases, supplier records, assembly manifests and complete test/failure logs remain preserved. No source, owner state, old installed candidate or unrelated local work is removed. All test/build/stage/fixture handles settle; the selected Host/Native remain running for feedback. This qualification documentation changes no runtime or selected artifact. Full Harness/question/plan-review/command, live-provider/service, migration/privacy/public-package/platform gates remain open; Windows/macOS/other distro implementation stays deferred for MX feedback.
