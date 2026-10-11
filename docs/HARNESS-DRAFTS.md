<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Original Harness composer drafts

## Storage and lifecycle

The original DSH composer now restores unsent text, file cards and image previews
from private Pi Host state instead of page-only Maps. The existing picker, editor,
cards, viewer, controls and supplier CSS are preserved. The Host remains the one
execution owner; draft reads do not load an AgentSession or submit a prompt.

Each profile/conversation has a versioned record under
`harness-drafts/v1/records` and immutable original bytes under `objects`. Text and
attachment revisions are separate; one field cannot silently overwrite another.
Records carry exact conversation-bound Pi upload receipts. Restoration fetches
the original bytes, verifies SHA-256 and length, and reconstructs real browser File
objects with their original name, type and timestamp. Receipt display names retain the
supplier’s cross-platform filename sanitization, separately from original names. It never substitutes dummy
files or uploads again. Ordinary reload and a cold Host on a different loopback
port restore the same identities. Different conversations have different drafts;
scoped read-only inspectors cannot read or edit unsent drafts or their bytes.

Both generic files and images are saved when picked. Image decoding/normalization
now occurs during that save, earlier than the preceding integration's Send-time
normalization; original bytes remain separately retained for draft previews. The
provider receives the actual verified normalized receipt only after explicit Send.
Original and normalized MIME types can legitimately differ, notably for GIFs.
The existing sixteen-attachment, twenty MiB file, eight-image, ten MiB per image
and twenty MiB aggregate image limits remain. Text is bounded to 65,536 UTF-16
units, metadata to one MiB per record, and the store to 1,024 records. Empty records
retain revisions. Removed cards revoke access through the draft-byte carrier;
private immutable objects/receipts remain retained, with garbage collection still
unimplemented. No new dependency or supplier source/licence is introduced.

Typing saves the latest text through serialized, revision-checked writes. Stale,
failed or malformed replies freeze mutations and preserve local text with the
existing error modal; no mutation is replayed. Copy unsaved local text before an
explicit page reload to read served state. Late reads cannot restore operator
content after revocation, and late acknowledgment cannot clear another session.

Before Send, an exact draft submission marker is committed with one request ID,
the saved text, attachment identities and normalized parts. The existing Pi queue
still owns admission and execution truth. A successful reply settles only the
matching accepted queue fingerprint and clears that draft. A lost reply or crash
between preparation and admission restores the marker and the existing
“Submission unconfirmed” controls; reopening cannot send it again. The existing
explicit acknowledgment clears only uncertainty and preserves draft content.
It does not assert that an external action did or did not occur.

`host.describe.unsentHarnessDrafts` reports dirty retained drafts. Guarded shutdown
refuses non-empty text, attachments or an uncertain marker, including drafts in
another window or a closed/archived conversation. Send or clear text/remove cards
through the original composer, and inspect/acknowledge uncertainty before
maintenance. Upload body reception/normalization/storage also keep the existing
`activeUploads` lease. Authenticated operator RPC carriers hold
`activeHarnessRequests` from body reception through response, covering the first
text save before a dirty record exists; abort/failure release their own count. Native retains its separate existing draft/maintenance
guard. This namespace belongs to the original Harness web shell; it does not
replace the Browser extension's independent input state or claim rich @-mention
reference support, which is not yet connected to this plain composer.

## Qualification

Eight authored store/client contract cases cover private cold reads, whitespace,
separate revisions, real byte/receipt identity, exact uncertain markers, bounds,
corrupt/symlink/non-private files, lost replies, conflict freezing, read-only and
late authority/session changes. The actual public SDK/Host/HTTP case proves slow
and aborted draft/file and first text-save reception, maintenance refusal, one accepted prompt with an
injected lost reply, fresh-client restoration, no inference/action replay,
explicit acknowledgment and final idle shutdown. The actual original-GUI Chromium
case covers text/file/PNG/GIF cards and previews, reload, fresh Host/new origin,
conversation isolation, stale second-operator refusal, inspector/foreign denial,
exact restored receipts, explicit one-time SDK/tool/image admission and retained
other-session maintenance veto. All fixtures and file bytes are independently
authored; owner MX acceptance is recorded separately.

Retained preparation failures: the old Context-modal test expected reload to
erase a changed draft; it now verifies persistence and clears through real keys
before its next scenario. Other fixture fixes wait for actual turn settlement,
avoid assuming an inserted edit sits at the end of the caret's paragraph, compare
retrieved text instead of a newline inside serialized JSON, and await the disabled
read-only command launcher. The component-only interaction fixture supplies the
new empty draft read seat. A real client validation bug initially required the
normalized MIME to equal the source MIME; public codec/GIF evidence corrects that
while preserving original-byte and normalized-receipt checks. Final filename
review also separates original File names from supplier-sanitized receipt names;
the actual Linux fixture uses a colon in its original filename. No guard, original
layout or deadline is weakened.

The first full run after adding operator request reception passed 265/266: its
generic maintenance message hid the existing prompt-improvement cancellation
instruction. Specific activity guards now retain their useful messages before
the generic request guard; both still veto shutdown. The corrected focused run
passes 11/11. Final source type/build and supplier hash/graph/notice checks pass;
the final 43-file cohort passes **266/266**, zero failures, skips or cancellations,
with the prepared QtTest interpreter, two workers and unchanged deadlines.

Ordinary/installed totals and tested revisions follow when complete.
This shared Host/web change adds no OS adapter. Windows, macOS, other Linux distro
acceptance and the full Harness/voice/services/migration/privacy/public packaging
gates remain open; the existing DSH installation stays available.
