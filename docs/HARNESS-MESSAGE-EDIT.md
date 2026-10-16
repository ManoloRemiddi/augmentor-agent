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
compaction-blocked and read-only scopes are refused. Active voice/dictation must
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
Full source/fresh artifact qualification and a new MX review are pending at this
implementation checkpoint. The current memory review and selected installation
remain unchanged. This shared binding does not certify Windows/macOS/distro
adoption, full voice, arbitrary historical message editing, reconstruction of
unrecorded reference metadata, or the remaining Harness migration work.
