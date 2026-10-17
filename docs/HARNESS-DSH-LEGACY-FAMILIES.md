<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

[Referenced assets](HARNESS-DSH-LEGACY-ASSETS.md) now have a separately verified immutable companion. [Native v3 archives and historical admission](HARNESS-DSH-HISTORICAL-IMPORT.md) qualify authored SDK/GUI continuation and all five frozen projects' read-only preparation. Real transfer/adoption still require the owner pilot gate. The source-family/view format and the earlier source-only evidence below stay unchanged.

# Historical DSH source families — October 17

The offline tools now capture complete physical parent/subagent families and
produce a reproducible historical view without asking DSH's failing legacy reader
to migrate its original store. All five previously reader-blocked projects pass
this stage: **42 roots, 35 descendants, 77 original compressed logs and 80,992
derived records**. This is source-tool qualification on MX Linux, not a native
Harness import or an update to either running review.

The existing [readiness assessment](HARNESS-DSH-MIGRATION-PILOT.md#full-migration-readiness-refresh--october-17)
therefore remains **23 projects / 64 parent conversations**. The five families
have cleared offline decoding and membership checks; attachment capture, the
native archive contract and continuation remain before they can join that count.
See the [portable qualification](../release/harness-dsh-legacy-family-qualification-20261017.json).

## Capture and source binding

[`capture-dsh-legacy-family.py`](../scripts/capture-dsh-legacy-family.py) reads
`workspace.list` and `session.list` only. It verifies exact project membership,
working-folder binding, pin/archive membership and idle parent sessions before
and after capture. It does not follow/page histories, create sessions or request
source migration. The owner-selected DSH home is explicit.

[`dsh_legacy_family.py`](../scripts/dsh_legacy_family.py) scans canonical log
headers across the source sessions tree, following the public persistence rule:
choose the numerically highest `session.vN.jsonl.zstd` generation, with
`session.jsonl.zstd` representing v0. Other encodings, future generations,
symlinks, duplicate IDs and ambiguous headers are refused. Only children whose
header records `origin: subagent` and the actual parent are included, recursively;
ordinary user forks and unrelated project logs are not borrowed.

The capture compares generation/header membership before and after and selected
source physical revisions during and after copying. Nanosecond/device/inode
values use lossless strings. Each selected compressed original has a full hash
and bounded content-addressed chunks. The source-family manifest retains exact
headers, raw header fingerprints, parent relations, organization and the local
header-index witness. The five qualified captures each witnessed 1,250 headers.
This is evidence of those recorded cuts; it does not assert every descendant was
idle or that the whole live source store was stopped atomically.

Output must be outside the original DSH home. A new sibling temporary directory
is fsynced and published with Linux no-replace rename; failure removes only that
temporary directory. Existing or raced destinations remain intact. Originals are
never rewritten. Attachments and working files are explicitly absent, so a
source-family capture is not a full project backup.

## Derivation and verification

[`build.mjs`](../adapters/dsh-legacy-format/build.mjs) verifies all 52 pinned
public source/licence inputs and constrains the compiled graph to 51 MIT parser
modules plus the authored assembly/descriptor validator. Two virtual overlays
retain known descriptor-v2 support; supplier files remain unchanged. The older
BSD-3-Clause schema is a reference only, with its notice retained separately.
The graph has no Host, active agent loop or provider transport; external imports
are limited to `node:path`, `node:crypto` and `node:util`.

[`family.mjs`](../adapters/dsh-legacy-format/family.mjs) first restores each
historical child to v3, derives its own descriptor facts after its inherited cut,
and supplies those facts only to its actual direct parent for the v4 edge. This
avoids guessing an empty child catalogue. V4 sources retain their recorded
catalogue. Every resulting catalogue must agree with complete physical family
membership; missing, foreign, orphaned, cyclic or uncatalogued children refuse
publication. Coordinates in the resulting view are explicitly **derived current
coordinates**, separate from the retained original physical records.

[`export-dsh-legacy-view.mjs`](../scripts/export-dsh-legacy-view.mjs) publishes
`augmentor-dsh-offline-project-view/1`, profile
`augmentor-dsh-historical-family/1`. It retains the source-family manifest
byte-for-byte and all compressed originals, then adds normalized headers,
segmented records, direct-child evidence and processing fingerprints. These
include the supplier ledger, compiled parser and owned producer sources. The
archive includes `FORMAT-LICENSE`, `SCHEMA-REFERENCE-LICENSE` and `SOURCES.json`;
the format notices do not assign a licence to owner data. No compiled executable
is retained in this view.

[`verify-dsh-legacy-view.mjs`](../scripts/verify-dsh-legacy-view.mjs) checks every
referenced object and notice, rebuilds from trusted pinned sources, and recomputes
the full view from retained originals in a separate temporary location. Full
manifest equality includes processing fingerprints. A second verified location
of the same source tree produces the same compiled fingerprint. Rehashing also
refuses changed view objects after recomputation. Matching object hashes alone
cannot make a forged derived record pass. Verification executes no code supplied
by a data archive and creates no native session or model request.

The view is versioned against its exact processing sources. Changes to those
sources can make an earlier view fail strict recomputation; preserve it as dated
evidence and create a fresh view from its retained originals. Do not rewrite old
receipts to match newer processing code.

## Bounds and reproduction

Linux, Node 24.19.0, Python 3.13.5, `zstd` and the repository's locked esbuild are
the qualified environment. macOS/Windows capture and atomic publication adapters
remain deferred. Existing bounds stay in place: 128 roots, 32 descendants,
30,000 normalized records per log, 64 MiB compressed per source, 128 MiB decoded
per log, 16 MiB per object, 32 MiB manifest and 256 MiB expanded reference budget.
Compressed originals use 8 MiB chunks; views use at most 512 records per segment.
Oversized or incomplete records refuse rather than truncate.

With repository dependencies installed, fetch the public sources to a new
private directory using the [pinned source recipe](HARNESS-DSH-MIGRATION-PILOT.md#legacy-descriptor-v2-offline-format-proof--october-17).
The following commands use authored data and require no owner corpus:

```sh
node --test tests/dsh-legacy-family.test.mjs tests/dsh-legacy-descriptor.test.mjs
python3 -B -m unittest discover -s tests -p test_dsh_legacy_family.py -v
node scripts/proof-dsh-legacy-format.mjs /private/public-source /private/new-format-proof
node scripts/proof-dsh-legacy-family.mjs /private/public-source /private/new-family-proof
```

The pipeline proof also requires the repository's existing compiled importer in
`dist/`; build the app if absent. It demonstrates that the native importer
**rejects** this intermediate schema without creating a target. It is not a
positive import or continuation test.

For an explicitly selected idle project, private operator commands are:

```sh
python3 -B scripts/capture-dsh-legacy-family.py \
  --dsh-home /private/dsh-home --project EXACT_WORKSPACE_ID \
  --output /private/new-source-family
node scripts/export-dsh-legacy-view.mjs \
  /private/public-source /private/new-source-family /private/new-historical-view
node scripts/verify-dsh-legacy-view.mjs \
  /private/public-source /private/new-historical-view
```

All output directories must be new and private. Do not commit their manifests,
objects, raw hashes, project identities or paths. No owner data is required by
public tests or CI.

## Qualification and remaining work

Source tests pass **65 Node / 20 Python family cases**, **8 Python fetch cases**,
**16 Python licence/private-boundary/notice cases**, **16 parser groups** and
**7 complete-pipeline groups**, with app type-check passing and no skips.
Five identical frozen source families are exported and independently recomputed
using two verified public source locations; every frozen source file stays exact.
No new app candidate or ordinary/sealed app cohort is claimed for these tool-only
changes. The preceding qualified application remains `0a7b15f7`; both running MX
reviews remain on `1633e00f / 20261016-220504-b91df2e4`.

Both running owner PIDs, all 36 protected regular paths and contents, selections,
registry and 24,615 sealed inputs remain exact. No additional real project is
transferred, no owner is restarted, and no model, voice or GPU setting changes.

Next, capture and bind required assets; define the original physical-record versus
derived-coordinate archive contract accepted by the importer; then qualify
original Chat/Trajectory/Context/Fleet reads, exact historical cuts and Pi SDK
continuation using authored families. Only after those pass can a fresh real
read-only preparation change readiness. Existing owner pilot feedback still gates
further real transfers. Voice and other operating systems remain deferred.
