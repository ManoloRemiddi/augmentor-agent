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

This shared Host/web change adds no OS adapter. Windows, macOS, other Linux distro
acceptance and the full Harness/voice/services/migration/privacy/public packaging
gates remain open; the existing DSH installation stays available.

## Installed MX qualification — October 11

Tested runtime **6f6bf39071839d1e023a648247bb9ff89892b5ce** is selected
**and running** in private MX release **20261011-235335-2d8c7e8f**, product
0.2.13, artifact
**5cfd01bb69668bc52a2a5801cd1b9c7540f1fb1c6c28c9604007c38d0809f8d2**.
Subsequent qualification edits change documentation only.

Source and fresh ordinary bundled Node **24.19.0** each pass **266/266 across
43 files**, zero failures/skips/cancellations, prepared QtTest, two workers and
unchanged deadlines. All **481 compiled files** match the ordinary assembly.
The preceding release's **19,160 dependency files**, **131 npm instances**, six
native executables, bundled Node, **723 licence files** and **96 browser notice
records** match byte-for-byte. Public supplier selections, original CSS and
licence bodies remain unchanged; the authored bindings provide persistence.

Normal guarded staging/activation finishes before the stable Host launch; its
exact selected entry point and bundled Node are verified before stable Native
launch. Both running roots match selection, Native is online/model-ready/idle,
and all **21,792 installed inventory entries** pass after GUI acceptance.
No selected release is patched.

Actual installed acceptance uses the copied composer and File menu/picker on an
existing authored demo conversation. Unsent text and one authored 73-byte TXT
file restore after page reload with the exact saved revisions, original bytes,
attachment identity and single Pi receipt; restoration performs no new upload.
Guarded shutdown refuses the dirty draft both before and after reload. Original
keys and Remove file clear only that fixture; the Host then reports zero dirty
drafts, uploads, operator requests, turns and compactions. The five classified
private draft/object/receipt/alias records remain retained under the documented
retention policy, with exactly one owned receipt added and all preceding private
attachment files preserved. Original Context and Insights retained reads pass;
Insights remains open at the normal 513×715 viewport for owner feedback.

All **eleven histories and queue identities** remain preserved, with zero new
conversations, prompt admissions, provider requests or tool actions. Of **243
preceding saved files**, **233** are byte-identical; four original journals retain
their exact previous prefixes with only two saved-title/session_info, two
session/close and two session/load appends, plus six corresponding counter/index
derivatives. Private profile settings are unchanged. Production selection and
the running model router remain preserved, as do model/speech/GPU/context/
concurrency/precision and CPU ASR/VAD placement.

This qualifies original plain-composer drafts in the private MX preview. The
synthetic cold-Host/new-origin and lost-reply cases above remain distinct from
installed acceptance, which adds no owner inference. Rich references, retention
collection, broader migration, public packaging/privacy and other platforms
remain open; this increment does not complete the Augmentor Harness goal.
