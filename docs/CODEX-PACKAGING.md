<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Codex packaging inventory and remaining release gates

Status: source and supplier-payload audit for Codex **0.159.2**. This is not
redistribution clearance, an installed package, or completion of C8. The existing
Debian native-inventory gate remains enabled and still rejects the unreviewed
Codex component. Do not treat a matching hash as a complete license review.

## Pinned inputs

- [Source pin](../release/codex/source-pin.json): upstream commit
  `ff6aec96948b70d94983af2641a6b67c94faeff5`, source-archive SHA-256 and hashes of
  the original Cargo lockfile and build recipes.
- [Linux payload](../release/codex/native-linux-x64.json): the exact npm archive
  integrity and 32 ELF payload hashes, sizes, shared-library names and version
  requirements. Includes Codex, code-mode host, ripgrep, bubblewrap, patched zsh,
  voice host and voice libraries. No binary is accepted merely by its filename.
- [Locked external sources](../release/codex/locked-sources.json): 1,297 crates.io
  archives verified against the original lockfile and seven Git source archives
  pinned by commit. The source lock contains 1,472 packages including 159 workspace
  packages and 16 packages from the seven Git repositories.
- [Notice supplements](../release/codex/notice-supplements.json): 53 exact-commit
  repository archives with candidate notice paths and hashes. Applicability still
  requires review; these are not declarations of license clearance.
- [Source identity evidence](../release/codex/notice-source-identity.json): version,
  published VCS commit/path and Rust-file comparisons for each supplement package.
  Includes unresolved generated/changed files; it grants no redistribution approval.
- [Native source inputs](../release/codex/native-sources.json): dependency versions,
  upstream recipe provenance and retrieved archive checksums. This is not yet a
  complete inventory of the native code linked into Rust/V8/compiler binaries.
- [Native source notices](../release/codex/native-source-notices.json): compact
  receipt for the actual native collection, including notice counts, full-record
  hashes, original top-level notices and contained aliases. No license text is
  reconstructed from metadata.

The bundled patched zsh requires glibc 2.38. That is compatible with the documented
Debian 13 target, but does not qualify older Linux distributions or the complete
artifact. The inventory records all observed version requirements; no executable
was run to infer its shared-library dependencies.

## Reproduction

Download and verify the source archive from `source-pin.json`, then extract it into
an isolated directory. Retain the original source and lockfile. Use:

```sh
python3 scripts/collect-codex-sources.py --source <extracted-source> --cache <archive-cache> --out <new-collection-directory>
python3 scripts/collect-codex-native-sources.py --source <extracted-source> --cache <native-archive-cache> --out <new-native-collection-directory>
python3 scripts/verify-codex-native.py
PYTHONPATH=apps/native QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -p 'test_codex_*.py' -v
```

The collector downloads source archives, verifies crate checksums, retains notice
files with per-file hashes, and records unresolved attribution. It does not resolve
new dependency versions, execute build scripts, compile packages or approve binary
redistribution. Cached archives are checked again. New output directories prevent
mixing old and new collections. Unsafe archive paths and changed cache contents
are rejected.

The exact extracted release source failed `cargo metadata --locked`: Cargo wanted
to update the release lockfile. The collector therefore uses the original lockfile
directly. Its collection deliberately includes unused, development and other-platform
dependencies; it is not evidence that every collected package is linked into Linux.

## September 30 evidence and next work

The actual collection verified all 1,304 external source archives and preserved
4,690 notice/metadata files after including SPDX-named files inside `LICENSES/`
directories. Of these archives, 138 lack standalone notice files;
128 of those identify a VCS commit. The recorded missing-notice list includes
repository and VCS provenance for follow-up. A second collection using the pinned
archive catalog produced a byte-identical report from the verified cache before
the nested-license correction (4,688 files and 139 missing sources). The
Rust 1.95.0 source archive was also verified against its upstream checksum.
A license expression in Cargo metadata
is not substituted for the missing attribution text.

The initial supplementary collection also verified all 53 repository archives.
Their candidate index records 145 notice files, with candidates for 116 of the
remaining 138 missing-notice sources; 22 have no retrieved candidate. The collector
retains the full available notice set from those archives separately from the
locked-source collection. Candidate retrieval does not establish applicability or
linked-binary coverage. Metadata-only license declarations are not counted as
resolved standalone notices.

## October 1 version and source identity evidence

The collector now retains explicitly pinned inline license files as well as
standalone notices. `bech32 0.9.1` embeds the full MIT text and copyright in
`src/lib.rs`; its exact-commit supplement now preserves that original file and
checks its hash. The existing `pagable 0.4.1` repository archive also supplies a
candidate root notice for the version-matched `pagable_derive 0.4.1` package.
Candidate coverage is now 118 of 138 sources lacking standalone notices, leaving
20 without a retrieved candidate. The crate's original omission is still recorded;
a supplement does not rewrite the locked archive.

The actual collection verifies all 1,304 locked and 53 supplementary archives.
All 128 supplementary package records match their published VCS commit/path and
upstream package version, resolving inherited metadata from the nearest enclosing
workspace. Older crate metadata without a package path requires a unique
name/version manifest; this corrects the apparent root-path mismatches for
`dasp_sample`, `schemafy_core` and `schemafy_lib`. All published Rust files match
byte for byte for 109 records. Nineteen records retain missing or different Rust
files, including generated Apple bindings and `debugserver-types`; these require
further attribution/source review. No generated code is fabricated or executed.

`collection.json` records every compared Rust-file hash. The new
`notice-source-identity.json` output summarizes the same evidence and hashes each
package's full comparison list; the committed inventory is a copy of that output.
Candidate notices must agree with the archive inventory and their actual bytes.
Eight focused tests pass, including changed/missing inline notices, ambiguous
monorepo identity, mismatching versions/generated files, workspace inheritance,
duplicate files and archive traversal. These checks establish source identity,
not complete license applicability or linked-binary coverage. The installer gate
remains enabled.

The native verifier matches all 32 installed supplier payloads and returns
`releaseApproval: false`. It detects added, missing, modified and symlinked files.
Nine focused Python tests pass, including four new source/inventory cases and the
existing Codex credential/setup cases, using the isolated Qt test environment.

Required next steps before accepting the payload into an installer:

1. Resolve missing crate notices from version-matched upstream sources, recording
   exact URLs/commits and hashes. Investigate the ten archives without VCS metadata.
2. Complete source/notice coverage for statically linked native components, V8 and
   its dependencies, Rust runtime code, bubblewrap/libcap, patched zsh and ripgrep.
   Collect dependency sources needed for redistribution and preserve upstream
   patches/build recipes. The top-level Codex Apache license is insufficient.
3. Account for every voice shared library and source archive, with its existing
   upstream notices; do not confuse Codex's voice runtime with Augmentor's separate
   Resonant Voice integration.
4. Collect and verify the corresponding macOS target and signing/sealing behavior.
5. Wire reviewed evidence into both packaging paths, then run real Debian/macOS
   builds, clean-user setup, runtime execution and upgrade/rollback checks. Keep
   the existing unknown-native-file rejection until these records are complete.

No installed application, runtime cache, model service or global Codex CLI was
changed by this audit. The large downloaded source archives are local build inputs;
the durable public handoff is the pinned manifest, collector and verification code.

## October 1 native source collection and V8 inputs

The native catalog now includes 28 verified archives. Eleven newly retrieved
inputs account for V8 15.0.245.2, Highway 1.2.0, fast_float 8.0.2, simdutf 7.7.0,
the exact Chromium libc++/libc++abi/llvm-libc revisions, ICU, Dragonbox, FP16 and
Abseil. Archive checksums come from the pinned Codex module/patch files or the
actual exact-commit Gitiles archive. Abseil is **20250814.1**, selected by the
module lock rather than V8's initial 20250814.0 declaration; its registry source
metadata was checked against the module lock before retrieving its archive.
Additional compressed inputs total 116,626,737 bytes and remain in the local cache.

The source pin now retains 25 original source/build files, including the native
build scripts, V8 manifests, build definitions and upstream patches. The new
collector rechecks the archive and source-file hashes, retains original notices
and copies the pinned recipes into a separate artifact. It supports rootless
Gitiles snapshots, reads each archive once and records contained notice aliases
without creating filesystem links. Escaping links, wrong roots, duplicate files
and unsafe paths are rejected. Three focused native-source tests pass.

The actual collection retains 3,817 original notice files across all 28 archives,
totaling 20,451,780 bytes. Every archive has notice text, and every observed notice
alias has its target retained. Two full collections produce byte-identical
`collection.json` reports. The committed compact receipt matches the collector's
`native-source-notices.json` output. Neither the collector nor its manifests grant
redistribution approval or execute downloaded code.

This improves corresponding source/notice inputs; it does **not** prove complete
linked-binary coverage. Musl/compiler runtime coverage, final crate attribution,
generated source review, Mac payload correspondence and installer execution/
migration/rollback remain open. `2641227` passed both Mac jobs and Debian application/
credential/Home checks; Debian packaging still stops at the same unreviewed Codex
executable notice gate. The installed app, private Resonant Voice source and live
Qwen/Breeze services are unchanged.
