<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

[Native recovered-history archives](HARNESS-DSH-HISTORICAL-IMPORT.md) now provide an explicit v3 envelope over this unchanged companion and its view. All five frozen projects pass complete read-only preparation after the separately qualified historical admission fixes. Intermediate files alone remain refused. The asset-only checkpoint below and its 23/64 readiness count are historical; owner adoption and pilot-feedback gates remain separate.

# Assets for recovered DSH histories — October 17

The [complete historical families](HARNESS-DSH-LEGACY-FAMILIES.md) now have an
immutable, separately verified companion containing their referenced stored
images and files. The five frozen real families pass capture and independent
verification. Four reference no assets; one references **28 distinct images at
34 history locations**, totalling **3,991,330 stored bytes**. None references a
file attachment. File handling is qualified separately with authored binary,
empty and 20 MiB files, rather than inferred from that real image-only result.

This is an offline source-tool checkpoint. Neither the view nor its companion
is accepted by the native importer. No real project is transferred, no app is
updated, and preparation readiness remains **23 projects / 64 parents**.
[Portable evidence](../release/harness-dsh-legacy-assets-qualification-20261017.json)
records exact tested sources, fixture/live scope and remaining integration.

## Capture and immutable binding

[`capture-dsh-legacy-assets.mjs`](../scripts/capture-dsh-legacy-assets.mjs) first
runs the full retained-original view verifier against the pinned public parser
sources. It inventories complete normalized message records across every parent
and descendant, retaining each occurrence's exact source ID, derived sequence,
content index, kind and attachment metadata. Identical stored objects are copied
once while occurrence ownership remains explicit; a child-only image does not
become a parent's attachment.

The input view remains unchanged. The new `augmentor-dsh-historical-assets/1`
manifest binds its exact SHA-256 and original-family SHA-256, the complete asset
inventory and every captured content-addressed chunk. It explicitly declares
that working files are not captured and current Harness import compatibility is
false. Asset identities and lengths come only from actual history references;
paths or filenames supplied by those histories are never opened.

The Python [byte-capture helper](../scripts/capture-dsh-legacy-assets.py) reuses
the existing [project exporter's](../scripts/export-dsh-project.py) descriptor-
relative attachment reader. It opens only digest-named objects in the explicit
DSH home's image/file stores, validates regular-file type, exact length/hash and
stable physical revision, and refuses symlink namespaces, changed objects and
FIFOs. It does not enumerate the attachment store or call the DSH service.
All requests validate before the first source read. Missing assets refuse the
whole companion rather than silently dropping a record.

Capture writes a private unpublished sibling directory. It verifies the asset
companion, recomputes the original view again, checks unchanged inventory, syncs
the output and publishes through the existing Linux no-replace rename. Output
inside the source tree, view or DSH home is refused. Failure removes only this
invocation's stage; existing/raced outputs and all inputs remain intact.

## Verification and bounds

[`assets.mjs`](../adapters/dsh-legacy-format/assets.mjs) checks complete segment
coverage and asset occurrences, reference limits, object sizes/hashes, exact
whole-asset digests and the complete named object closure. A correctly hashed
replacement chunk cannot change an attachment's recorded digest. An altered
source ID, cut or content index fails the inventory binding. Empty files have
an empty chunk list and the actual empty-content hash.

[`verify-dsh-legacy-assets.mjs`](../scripts/verify-dsh-legacy-assets.mjs) first
recomputes the view from its retained original logs using trusted pinned sources,
then verifies the companion and repeats the inventory/object checks. It needs
no original DSH home, model, Host or network service. No executable supplied by
the data archive is loaded. Like the source view, the companion's format does
not assign a licence to owner data.

Existing limits remain: 10 MiB per image, 20 MiB per file, 10,000 distinct assets
per kind, 8 MiB capture chunks, 16 MiB per object and 32 MiB per manifest. Reference
metadata is bounded while collecting it. The **combined** view, source originals,
notices, companion metadata and expanded asset references must fit 256 MiB;
shared disk objects do not discount repeated logical references.

The largest real combined input uses **255,268,957 bytes**, about 243.4 MiB.
This matters for native integration: wrapping and storing all derived histories
again would exceed the bound. The next archive contract must resolve the existing
verified event segments once, retain original compressed logs and their provenance,
and construct native record wrappers when reading. It must still charge every
actual logical reference and refuse overflow; raising limits or dropping original
records is not the solution.

## Reproduction and evidence

Qualified on MX Linux x64 with Node 24.19.0, Python 3.13.5, `zstd`, locked
repository dependencies and the same pinned MIT format sources as the family
checkpoint. Windows/macOS publication and runtime adoption remain deferred.
All destinations below are new private directories with existing private parents:

```sh
node scripts/capture-dsh-legacy-assets.mjs \
  /private/public-source /private/verified-view /private/dsh-home /private/new-assets
node scripts/verify-dsh-legacy-assets.mjs \
  /private/public-source /private/verified-view /private/new-assets
```

Public tests need no owner data. The explicit full pipeline uses an authored
v0 parent/descriptor-v2 child, public codec restoration, a real PNG, empty file
and complete 20 MiB binary. It also checks native refusal, not native continuation:

```sh
node --test tests/dsh-legacy-assets.test.mjs tests/dsh-legacy-family.test.mjs tests/dsh-legacy-descriptor.test.mjs
python3 -B -m unittest discover -s tests -p test_dsh_legacy_assets.py -v
node scripts/proof-dsh-legacy-assets.mjs /private/public-source /private/new-assets-proof
```

The pipeline's negative native admission check requires the existing compiled
importer in `dist/`; build the app first if absent. **90 Node cases** (25 new asset
cases plus 65 descriptor/family regressions), **9 Python helper cases**, **16
licence/private-boundary/notice cases**, **9 authored pipeline groups** and app
type-check pass, no skips. The full pipeline verifies offline operation with the
original asset store renamed away, unchanged source bytes, child-only ownership,
large/empty files, corruption, forged ownership, missing-asset refusal, preserved
existing outputs and cleanup. The five same frozen real views recompute using a
second verified public source location, with unchanged view manifests.

Both existing owner PIDs, all 36 protected regular paths/contents, registry,
selected configurations and all 24,615 running sealed inputs remain exact.
Preceding application qualification is unchanged; this checkpoint adds no app
candidate or runtime/GUI cohort claim. The canonical dirty main checkout,
production Agent/Desktop, DSH and GPU/voice settings remain untouched.

Next: integrate an explicit original/derived archive coordinate contract with the
native reader/importer without duplicating segment storage. Then qualify original
Chat/Trajectory/Context/Fleet inspection, historical cuts and Pi SDK cold/new-turn
continuation with authored complete families. Fresh real preparation follows;
existing owner pilot feedback still gates further real transfers. Voice and
other operating systems remain deferred.
