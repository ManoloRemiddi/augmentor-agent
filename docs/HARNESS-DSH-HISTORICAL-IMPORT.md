<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Native archives for recovered DSH histories — October 17

`augmentor-dsh-project-export/3` connects verified [historical source families](HARNESS-DSH-LEGACY-FAMILIES.md)
and [asset companions](HARNESS-DSH-LEGACY-ASSETS.md) to the native importer. It
preserves compressed originals, derived histories and attachments in one named
closure, without storing a second wrapped copy of every derived event. Version
one JSON and version two bundles remain supported.

Source qualification passes **490 Node / 92 Python** across 58 Node files,
sixteen Chromium files and 21 GUI cases, with two workers and no skips. An
independent public-codec pipeline imports authored v0/descriptor-v2 histories,
empty/20 MiB files and a child-only PNG through the new envelope. Original GUI
Fleet/Chat/Context source reads and actual Pi Host historical branching, fresh
work and cold continuation pass with authored data and a synthetic provider.
Ordinary/exact sealed qualification is recorded separately below.

**The five real recovered projects are not ready for native transfer.** They
export as v3 and pass closure reading, including 28 stored images, but all five
still refuse complete parent preparation: four first encounter older settlement
reasoning before a catalogue; one first encounters an unresolved compaction
lifecycle. Refusing preparation creates no target or model request. The earlier
**23-project / 64-parent** preparation assessment and owner pilot-feedback gate
remain unchanged. Do not relabel fixture success as owner migration acceptance.

## Archive and coordinate contract

`project.json` has exactly these fields:

| Field | Meaning |
| --- | --- |
| `schema` | `augmentor-dsh-project-export/3` |
| `profile` | `augmentor-dsh-historical-family/1` |
| `coordinates` | `derived-dsh-v4` |
| `view` | Exact historical view manifest object reference |
| `sourceFamily` | Exact original-family manifest object reference |
| `assets` | Exact referenced-asset companion object reference |
| `notices` | Named references for `FORMAT-LICENSE`, `SCHEMA-REFERENCE-LICENSE`, `SOURCES.json` |

Every reference is `{sha256, bytes}` with an existing hash-named object. The
reader resolves the manifests and registers their named closure once: original
compressed chunks, derived headers/event segments, notices and asset chunks.
Metadata fingerprints, root membership/organization, physical parentage,
catalogues, child creation evidence, occurrence ownership, complete file/image
hashes and source/view bindings must agree. Physical chunk hashes and complete
compressed-log hashes are both checked. No data-provided source path is opened,
no executable from the archive is loaded, and no legacy agent/runtime is started.

The [historical reader](../packages/runtime/src/dsh-historical-project.ts)
constructs opening snapshots and `{type: event, event: ...}` wrappers while
reading the retained derived segments. It caches at most one history; titles are
retained from actual `session/title` records rather than invented projection
metadata. Parent conversations become native imports. Descendants remain archived
read-only seats, with original scope/parent checks and no Pi worker or job.

Source events use **derived v4 coordinates**. Those coordinates are not original
physical JSONL row numbers: public migration can group stream chunks and insert
records. Native bindings, per-event display provenance, receipts and source cuts
retain the coordinate policy and original compressed-source identity. Parent
notices and archived source-entry boundaries state the distinction. The Context
entry viewer now renders archived boundary text and says “Saved DSH record”;
other original-entry workflows and the original GUI layout remain intact.

`dshCompressedSource` in the [shared archive reader](../packages/runtime/src/dsh-project-archive.ts)
returns a selected log's exact compressed bytes, format and hash after checking
its declared closure. This is an internal archive/operator API, not a new browser
endpoint. Physical-row browsing/downloading in the GUI is not implemented here;
no one-to-one source map is fabricated. The archived inspector shows the exact
saved **derived** records with their provenance label.

## Trusted export and native lifecycle

The [new export command](../scripts/export-dsh-historical-project.mjs) requires
pinned public sources, a retained-source view and its asset companion. Before
and after copying it recomputes the view and verifies assets through the trusted
operator tools. It copies complete named objects, retains metadata byte-for-byte,
then reads the unpublished result through the actual native archive reader.
Existing/raced destinations are protected by Linux no-replace publication.

Runtime admission verifies the operator-selected envelope SHA-256, its complete
data closure and supported contracts. Parser recompilation/recomputation occurs
in the trusted export command, not inside native import. A checksum by itself is
not upstream authentication or proof that an arbitrary third-party producer ran
that command. Processing fingerprints are retained provenance, never executable
authority or permission to contact an old provider.

Import keeps existing offline transaction, current explicit model selection,
Read Only policy, image/file admission and no-replay behavior. All parent
histories must validate before staging. Copying/reopening the complete named
closure prevents input changes after preparation from becoming a native import.
Native profile relocation uses the same closure reader. Historical reply cuts
retain their then-current derived context and full original archive; child-only
assets remain inaccessible as parent uploads. Old permissions, queues, tools,
plans, goals and memory-capture work are not resumed by history inspection.

## Bounds and commands

All existing import bounds remain: 128 parents, 32 archived descendants, 30,000
records per log, 16 MiB per object, 32 MiB envelope and 256 MiB expanded reference
budget. V3's referenced metadata manifests also fit the 16 MiB object limit;
larger metadata is explicitly refused. Source originals retain their 64 MiB
compressed-log and bounded-chunk limits. Images/files retain 10/20 MiB limits.
Repeated logical references still count even when disk objects share a digest.

The largest same-byte real v3 archive is **255,269,784 bytes** under the 256 MiB
expanded bound. Its derived event segments are stored once, alongside the exact
compressed originals and assets; neither originals nor history are discarded to
make it fit.

Use the matching compiled source/application and Node/Python, repository
operator dependencies, `zstd` and verified public parser sources. Operator paths
below are examples; all outputs are new private directories:

```sh
node scripts/export-dsh-historical-project.mjs \
  /private/public-source /private/verified-view /private/verified-assets /private/new-project
node scripts/import-dsh-project.mjs \
  /private/new-project/project.json /private/new-native-state MANIFEST_SHA256 CURRENT_PROVIDER CURRENT_MODEL
```

Do not run the second command for additional real owner projects before the
pilot-feedback gate passes. Source-format assessment can call
`prepareDshProject` without creating a native target or contacting any provider;
assessment-only model labels do not establish configured-route availability.

Public operator proof, requiring no owner data:

```sh
node scripts/proof-dsh-historical-project.mjs /private/public-source /private/new-proof
node --test --test-concurrency=2 tests/dsh-historical-project.test.mjs tests/dsh-historical-project-runtime.test.mjs tests/harness-dsh-family-chromium.test.mjs
```

Native-envelope unit fixtures are independently authored data, not an assertion
that their manually constructed envelope was produced by public codec migration.
The separate operator proof runs that actual codec chain, byte capture, native
export/import and exact compressed-original/attachment checks. Actual Host tests
separately establish SDK behavior with an independent local synthetic provider.

## Packaged qualification and owner preservation

Source and a fresh ordinary package each pass **490 Node / 92 Python** with
1,117 compiled inputs matching. The ordinary package also runs the six-group
public-codec/native operator proof from its own shipped code. Dependencies,
Node/native bytes and unchanged baseline files match the preceding sealed
`0a7b15f7` application. Exact separately sealed qualification is pending.

Both current owner PIDs, all 36 protected regular paths and contents, registry,
selected configurations and all 24,615 running sealed inputs remain exact. No
review is restarted or updated; no additional owner project is imported and no
owner model request is submitted. Source and packaged proof data stay separate
from the actual profiles. [Portable qualification](../release/harness-dsh-historical-import-qualification-20261017.json)
records the scope; a source commit is not an installed update.

## Current real refusal evidence and next work

All five frozen projects and their 35 descendants now form native-readable v3
archives. Complete preparation still refuses rather than bypassing older history
rules. The first reasoning refusals are manager-owned `subagent-settled` notices,
with exact known source keys and plaintext reasoning. Their matching catalogue
usually occurs later. The pinned public v3→v4 migration adds missing catalogue
records during `finish`, explaining why earlier-catalogue admission is too narrow
for some recovered views. One family's notices also lack a matching local
catalogue; do not borrow another family's child or claim its ownership.

Separately, one family first fails turn/compaction lifecycle correlation. Next
steps are explicit historical admission/labels and cuts for these recorded forms,
with public producer-contract evidence, synthetic regression/SDK/GUI tests and
same-frozen-input comparisons. Do not drop reasoning, invent catalogue events,
mark unknown compaction work completed or relax every lifecycle check to get a
passing preparation count.

MX Linux is the qualified target. Voice, other operating systems, owner transfers
and selected/running adoption remain separate. Both current owner reviews and
protected data stay unchanged during this checkpoint.
