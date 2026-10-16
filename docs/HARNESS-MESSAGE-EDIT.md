<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Sent-message Edit in the original Harness GUI

The latest persisted human message offers **Edit message** beside Copy, using
the original DSH icon row, tooltip, icon and CSS. Edit creates a Pi child at the
native boundary before that message and restores the original submitted input
and attachments into the existing composer. Review the replacement and press
Send explicitly. Parent history and its unsent draft remain intact. Earlier
completed tool context is inherited; tools and prompts are not replayed.

The pinned public DSH source `d743267388641bc76f17c45ce8b4c231aed1d32c`
is MIT licensed. Its archived July 31 note, `drop-user-message-edit-stub.md`,
explains that upstream removed an unfinished Edit button without a mutation or
backend implementation. This integration restores that action affordance and
authors its Pi binding; it does not claim a working upstream editor was copied.
The two adapted supplier files retain their upstream hashes and record their
current hashes/adaptations in `apps/harness/vendor/dsh/SOURCE.json`.

## Runtime and recovery contract

`host.describe.capabilities.messageEditDrafts: 1` advertises the complete binding.
Older Hosts hide Edit. `session.prepareEdit` accepts only conversation/message
identity, checks the latest human input and exact native cutoff, verifies all
original attachments, and reserves a durable edit-child identity. It does not
load a child AgentSession or call a model. Running, archived, delegated,
compaction-blocked and read-only inspection scopes are refused. Active voice/dictation must
close before preparing an edit; no audio service is stopped automatically.

The private `harness-drafts/v1/edit-origins` directory stores a bounded prepared
candidate, source digest and applied marker outside the existing draft schema.
Verified original bytes are saved before publication. `session.branch` with the
exact prepared identity, `seedDraft: true` and matching `sourceHash` applies that
candidate before exposing child metadata. On Linux it uses the existing native/
display/metadata publication journal. An applied draft prevents a false
“not-created” settlement from discarding recovery identity. A crash before or
during publication preserves the exact child for explicit recovery.

Lost responses never trigger automatic branch creation, upload, prompt or tool
retry. Clicking Edit again at that boundary reads the saved identity. Once
applied, the original candidate cannot overwrite later typing, attachment edits,
submission receipts or the empty draft left after Send. Navigation or parent
draft changes while creation is pending prevent automatic child selection.

Each attachment gets a child-scoped receipt referencing the same immutable
supplier objects; source receipts do not authorize child submissions. File bytes,
original image bytes, normalized model image identity and display names are
retained. Missing/corrupt originals refuse the edit, including text-only
downgrades. Existing limits remain: 65,536 text units, sixteen attachments,
twenty MiB per file, eight images/ten MiB each/twenty MiB aggregate originals.
The edit-origin store permits 1,024 private bounded records without eviction.

The transcript does not retain original file modification times, general file
MIME declarations or every Lexical reference-chip identity. Recovered files use
an unspecified timestamp (`0`) and `application/octet-stream`; image MIME is
identified from its original bytes. Literal submitted text is preserved. These
metadata are not fabricated from the current filesystem. Explicit Send runs
the existing approved-resource/input pipeline and gets a fresh typed receipt,
including when the original input was spoken.

## Qualification and scope — October 16

Build/type checks pass. The focused source recovery cohort passes **19 cases**,
including real SDK/Host native cutoffs, exact original files/images, parent draft
preservation, changed-child protection, missing originals, archive/inspector
denial, cold identity recovery and a real SIGKILL during publication. Original
Branch regression passes. The actual Chromium pointer flow checks Light/Dark,
only the latest human action, normalized-image original recovery, pending clicks,
parent typing, corrupt acknowledgement, Host/browser replacement, reload and
explicit Send. No provider request occurs during Edit/recovery.

Initial failed evidence is retained: a corruption fixture first tried writing
the supplier's read-only object without making its own fixture writable; an
upload fixture used an incorrect route; the browser's final assertion initially
observed saved-draft acknowledgement before the new model turn settled. Fixture
corrections preserve assertions, timeouts, workers and production protections.
At application **dfe855f3**, source, fresh ordinary packaged copy and exact sealed
MX target each pass **769 cases/two existing optional skips**, zero failures or
cancellations, across **136 files/all 56 Harness Chromium files**, with two
workers and unchanged deadlines/limits. Nineteen licence/private-boundary Python
cases and eight actual installer-dependency cases pass. The preceding exact
sealed b7 build fails the new pointer case at its absent Edit action, as intended.
All 3,419 tracked inputs, 1,063 compiled files and 37,629 source dependency inputs
verify unchanged during source qualification; packaged Node/production npm/
components retain their exact baseline bytes. The later **a021d108** change only
declares Debian CI's missing `patch` prerequisite and documents it. Its preceding
hosted seven installer errors remain recorded; fresh hosted results are pending.

The **actual local Qwen** proof against the fresh ordinary copy passes. An earlier
native read result is inherited exactly, parent native bytes and its unsent draft
stay unchanged, and Edit creates no provider request. Explicit typed replacement
then answers from that earlier result with no additional tool call. The existing
262,144-context/8,192-output declaration, server, GPU and speech configuration are
preserved. This is a separate live model result, not a claim of physical voice
or wider provider-format acceptance.

## Qualified MX review — October 16

Separate unselected release **20261016-065534-c8cdf03c** runs application
**dfe855f3**, product **0.2.13/Pi 1.1.0**. All **24,529 sealed entries** verify,
SHA-256 **c242bfdb3f6fe6e1a7f07776eda298bdfaf9bd7e5d27c3206bd78ea9c13f7fca**.
Its empty profile imports no owner conversations, credentials or memory banks.
A separate installer-owned memory engine/volume uses the already qualified cached
MIT backport and explicit memory-only `off`; the original engine's default stays
intact. Existing private CPU recognition 0.1.22 is reused without changing it or
copying its source into public app/tests/CI.

Actual startup/browser QA verifies the original welcome/settings, both animated
2px Augmentor marks, black light-theme flare and readable Light/Dark settings,
permission/account confirmations without changing permissions or signing in,
keyless search, memory pause/resume with initial state restored, and cached English
CPU recognition readiness. There are zero sessions, memory events/jobs, model/tool
submissions, browser errors or failed responses; the QA browser exits. No physical
recording or audio playback is claimed. Thirteen previous/new seals, fourteen
review owners plus recognition, selection, 38 canonical/four private local changes
and six model/speech configuration hashes remain preserved. Qwen is online;
Breeze's GPU prerequisite remains unmet without retry, tuning or eviction.

For owner testing, use the private review link supplied in chat. Create a new
conversation, send a message, then use its Edit pencil after the turn settles.
Check the restored draft and attachments, replace text and press Send; the parent
conversation and any unsent parent draft should remain available. The review
starts with the existing Read Only tool-permission default; it permits composer
editing. A read-only inspection link does not.

No installed activation, merge or public binary follows. Physical MX feedback,
full voice/companion adoption, wider providers/load, remaining plugin/Home/Office
and data migration, distribution and later Windows/macOS/distro gates remain
open. Arbitrary historical editing and reconstruction of unrecorded chip metadata
are not certified. The active Harness goal remains incomplete.
[Portable evidence](../release/harness-message-edit-qualification-20261016.json).
