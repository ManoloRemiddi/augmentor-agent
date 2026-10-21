<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Public-source Office entry

This MPL-2.0 component is built from the 32 preferred TypeScript source files in
`preferred-source/`. `UPSTREAM.json` identifies the immutable public archive,
original and adapted file hashes, and the small Augmentor modifications. The
original `LICENSE` and `NOTICE` apply to the source and compiled adapter. This is
**0.1.3-augmentor.1**, not recovered preferred source for the opaque npm 0.1.5 entry.

From the Augmentor repository root, with Node 24.19.0:

```sh
npm ci --ignore-scripts --no-audit --no-fund
node scripts/build-office-entry.mjs --check
node scripts/build-office-entry.mjs
```

The root lock pins TypeScript 5.9.3, esbuild 0.28.2, fontkit 2.0.4, saxes 6.0.0
and fflate 0.8.3. The builder verifies source hashes, type-checks the public source,
compares all 31 tracked declarations, and builds four ESM entry points. It emits
the complete preferred source, declarations, notices, source maps, dependency
lock and builder into `dist/runtime/vendor/office-entry`. `SOURCE.json` binds
their exact bytes and toolchain. Use `--write-types` only when intentionally
reviewing a source/type change; ordinary builds refuse stale declarations.

A compiled component's `build-support/` contains copies of the root manifests
and builder. To reconstruct its original source layout, place those manifests
at the repository root, the builder at `scripts/build-office-entry.mjs`, and this
component's preferred source, declarations, provenance, notices and configuration
at `packages/runtime/vendor/office-entry/`. The full public Augmentor checkout
also supplies the `apps/harness` npm workspace manifest required by the root lock.

Linux uses the separately pinned Wasm engine 0.1.5. The public entry's original
native package mappings remain unchanged and need separate platform qualification.
Building this JavaScript adapter does not rebuild LibreOffice, qualify native
engines, or grant public binary distribution approval. The engine's source/link,
licence, font and platform gates remain explicit in the Office preview guide.
