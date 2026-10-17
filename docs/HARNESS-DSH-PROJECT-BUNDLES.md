<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

[Native v3 recovered-history archives](HARNESS-DSH-HISTORICAL-IMPORT.md) now complement this v2 tier. They reuse verified derived segments and retain compressed originals/assets without duplicate histories; the five real legacy projects still fail later history checks and are not ready for transfer.

# Complete DSH project bundles

October 17 source and ordinary packaged qualification adds `augmentor-dsh-project-export/2` alongside
existing version-one JSON exports. A bundle preserves the complete captured JSON
values and exact stored image bytes across bounded files. It does not reconstruct
original DSH journal whitespace, camera uploads, signed provider state or usage.
The [migration guide](HARNESS-DSH-MIGRATION-PILOT.md) still owns pilot feedback,
format admission and adoption. [Qualification](../release/harness-dsh-bundle-qualification-20261017.json)
distinguishes source, package and real read-only evidence from owner transfers.

## Capture and import

Run from the qualified application root, with its matching Python and Node.
The output parent must already exist; the bundle destination must not exist.
The following are synthetic example paths, not instructions to import an owner's
projects before the pilot gate passes:

```sh
python3 -B scripts/export-dsh-project.py --project /absolute/project --output /private/backups/project-bundle --bundle
node scripts/import-dsh-project.mjs /private/backups/project-bundle/project.json /private/new-state MANIFEST_SHA256 CURRENT_PROVIDER CURRENT_MODEL
```

The export receipt reports the manifest SHA-256, manifest/expanded byte sizes,
object count and parent/child counts. Import takes **project.json**, with the
sibling `objects/` directory intact. The existing optional per-conversation model
map and cold batch importer also accept this manifest. Existing version-one
commands/archives remain supported. A directory without all named objects is not
a transferable export. Keep the complete directory together in private backups.

Capture uses only workspace/session catalogue reads, opening snapshots and paged
history reads. Existing idle, exact membership, stable cursor and recursive child
identity checks remain. Stored images are read through descriptor-relative,
no-follow, nonblocking POSIX opens and checked for exact size/hash and concurrent
changes. A FIFO is refused rather than waiting for a writer. No prompt, source
edit, job, permission or conversation migration is submitted by capture.

The exporter writes an unpublished private sibling directory, syncs its files and
directories, then publishes through Linux `renameat2(RENAME_NOREPLACE)`. A raced
file, symbolic link or even empty directory is preserved. Failures clean up this
invocation's unpublished stage; source data is never removed. Atomic bundle
publication is qualified on MX Linux. Other OS publication adapters remain open.

## Version-two layout and bounds

`project.json` holds schema, workspace membership/organization, session addresses,
opening/segment references, related-session descriptors and image references.
Each opening is one complete JSON snapshot object. Each history segment is a JSON
array of complete source event records with a starting sequence and record count.
Image objects contain exact binary bytes. Every object filename is its lowercase
SHA-256; references also declare exact byte lengths. Session descriptors contain
`address`, `opening: {sha256, bytes}` and
`segments: [{sha256, bytes, firstSeq, count}]`. Image descriptors contain
`attachmentId`, `bytes` and `sha256`, with matching image identity/hash.

| Item | Bound |
| --- | --- |
| Manifest | 32 MiB |
| One object / one complete record | 16 MiB |
| Segment target | 8 MiB / 512 records; a single larger record may use the object bound |
| Whole bundle | 256 MiB, manifest plus every expanded reference |
| Distinct objects | 16,384 |
| Stored image | Existing 10 MiB and pixel/dimension admission limits |
| Project parents / archived descendants | Existing 128 / 32 |
| Records per complete history | Existing 30,000 |
| Combined cold batch | Existing 256 MiB, now accounting for expanded bundle references |

Repeated references share disk bytes but **do not discount the expanded budget**.
The previous version-one 32 MiB/cumulative limits remain for version-one exports.
Version two is an explicit larger, segmented tier; it does not merely raise the
single-file limit or truncate histories. Conservative capture charging still
refuses on overflow before any bundle becomes visible. Values over these bounds
remain an explicit refusal, not an incomplete successful export.

## Runtime storage and lifecycle

The shared reader validates reference shapes, sequence coverage, object counts,
expanded budgets and every referenced object's exact size/hash. It reads only
named objects and refuses links, non-regular files, changed bytes, wrong owners
and non-private object paths. On MX, object reads are anchored to an opened
directory descriptor. Per-read allocations are bounded before reading; object
references outside the manifest cannot be opened through the reader.

The reader caches at most one raw session history and one opening at a time.
Preparation validates parents without retaining normalized copies of every parent.
Import freezes and revalidates the complete named closure into its unpublished
transaction, then projects one parent at a time from that frozen copy. Incoming
changes after preparation cannot be published. Display JSONL is written one event
at a time. Existing native history, setup-only handling, selected model,
read-only policy, no-replay rules and memory-history exclusions are retained.

Target storage is `dsh-imports/<manifest-sha>.json` and shared content-addressed
`dsh-imports/objects/<object-sha>`. The manifest SHA remains the native provenance
binding; it transitively binds every object. Originals, child-only images,
then-current compaction/offload/reply cuts and archived Fleet scopes resolve
through the same reader. Child objects never grant parent attachment receipts.
Cold native relocation copies/revalidates only the named closure, preserving
source and destination ownership. Existing 128 MiB native/display relocation and
4 GiB cold-profile transaction bounds remain separate limits.

Cold batch duplicate detection hashes record arrays incrementally. An identical
v1/v2 source cut retains the existing Harness continuation and model selection.
Divergence is refused. Source metadata, native bindings and full original archives
are never rewritten just to match a new export's checksum.

## Oversized display events

The connection frame limit stays at 1 MiB. Previously, one larger saved event could
block a complete Chat/history page. Oversized imported events now carry a clearly
labelled bounded **display preview**. Complete source and display journals stay
unchanged; SDK context and branch reconstruction continue using full originals.
Tool identities, source sequence/binding and bounded image references remain.
Normal events and oversized live non-import events retain existing behavior.

The preview points to its exact source entry/hash. Parents use **Saved conversation
originals → Search saved originals → Original display journal**, backed by the
existing bounded `session.originalRead` API. Archived children use their existing
source-entry reader and `session.archiveRead`. Preview text is never presented as
complete output, native usage or model context. No new layout or control placement
is introduced.

## October 17 evidence and limits

Source check/build and **174 Node cases** across 28 files pass, with two workers,
no skips and unchanged deadlines. Eight Chromium files exercise eleven cases,
including v1/v2 variants of original images/reasoning, archived Fleet/source
excerpts and historical reply/lost-acknowledgment recovery. **47 Python cases**
include 24 existing/export cases, seven new bundle cases and sixteen
licence/private-boundary/notice cases. Synthetic tests cover complete tool history
and raw image collections over 32 MiB, actual SDK continuation, cold reopening,
relocation, mixed-format retention, named closure copying, expanded quotas,
corruption/link/FIFO refusal and exact pageable originals behind previews.

Seven additional real size-refused projects were inspected through read APIs.
Five now capture completely: **17 parents / four children / 28,877 parent records /
878 child records / 188 image objects**. Each passes object verification and
count/cut comparison. Replaying those exact frozen source responses through the
unchanged v1 capture path refuses all five at its original size bound. Bundle
expanded sizes range from 28,323,483 to 47,545,853 bytes.

Two projects/five parents pass read-only preparation. Three refuse independent
content formats: unsupported attachment/reasoning content, non-assistant reasoning,
and unmatched historical tool results. Two further projects fail source history
observation; no complete bundle is claimed for them. No real destination, current
model assignment, continuation or further owner transfer is performed. Assessed exports
remain private. Temporary captures are removed after validation; one separately
retained frozen input supports same-input packaging checks. This is not a fresh
whole-catalogue readiness or owner acceptance result.

The first implementation's regression suite caught reversed source array order;
publication now follows exact workspace membership order. A writer-level private
manifest permission assertion also caught reliance on the CLI umask; the writer
now creates its manifest explicitly with mode 0600. Initial fixture errors and
failing logs remain private; passing checks use original scope and deadlines.
The separate ordinary packaged copy passes the same 174 Node / 47 Python
cases, with all 1,108 compiled files and 23,511 unchanged baseline inputs verified.
The identical retained real bundle passes preparation for two parents/24 images.
The exact separate seal passes the same 174 Node / 47 Python cases and identical
real-input preparation. All 24,630 sealed / 1,108 compiled inputs verify afterward.
Candidate **20261017-003712-3e22586d**, application
**7372061b11a05f877d93d40330d545e73d19e036**, SHA-256
**d54ec1becd7204b7a1fe7124a7fdcf2ae6154b3dfc3d6c11a9b47ba719b7bd08**
is private and unselected. Both running owners remain on
**20261016-220504-b91df2e4 / 1633e00f**: their PIDs, complete 36 protected regular
file sets/hashes, registry and selected configurations stay unchanged; all 24,615
existing sealed inputs verify. No owner restart, adoption, model work or extra
project transfer follows. Use `-B` for standalone Python tool invocations from a
sealed root, as the managed launch environment also disables bytecode writes.
Installed adoption and owner pilot feedback remain separate gates. Voice,
other operating systems and wider owner migration remain deferred.


## Verbatim file objects — October 17

Exports now capture referenced `file` bodies as well as stored images. Only exact
content-addressed source `attachments/v1/file-objects` entries are opened, through
non-following directory/file descriptors. Size, regular-file type, timestamps and
complete SHA-256 are rechecked. File aliases, unrelated source files and the
attachment store are not scanned. An explicit DSH home is required; missing or
changed bodies fail the export before publication. All source cursors/membership
are rechecked after both image and file reads.

The optional `files` array is distinct from normalized image `attachments`.
Version one stores canonical base64 with the exact `attachmentId` and `bytes`.
Version two stores `attachmentId`, `bytes` and ordered `chunks`, each an existing
bounded `{sha256, bytes}` object reference. Files keep the existing **20 MiB** upload
bound; 8 MiB chunks retain the **16 MiB object** ceiling. Empty files have the
empty-content digest and an empty chunk list. Original sanitized names remain in
each source message, allowing multiple names for the same complete byte sequence.
Whole-file digest, chunk order/size and every object are verified; referenced
bytes count toward the existing **256 MiB** expanded project/batch budget.
Manifest, record, transport and object-count bounds are unchanged.

The importer validates complete bodies and exact reference fields before staging.
It refuses missing/extra/unreferenced bodies, duplicate identities, noncanonical
encoding, unsafe names, unknown metadata, invalid sizes and file offload flags.
Only that parent receives matching file receipts. Child-only files stay within
the verified archive and original read-only seat, without parent receipts or jobs.
Full raw records and file bodies survive exact archive closure copying.

[Continuation, Edit, branches and relocation](HARNESS-DSH-MIGRATION-PILOT.md#historical-file-attachments--october-17)
retain names and use the existing verbatim store. Qualification and deployment
scope are tracked in [the file evidence](../release/harness-dsh-files-qualification-20261017.json).
