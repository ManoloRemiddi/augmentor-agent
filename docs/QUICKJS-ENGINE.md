<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Minimal QuickJS engine for Pi codemode

Normal production staging now supplies a retained source rebuild of the QuickJS-WASI engine used by Pi 1.1.0 codemode. The executable, complete pinned engine/libc sources, compiler-runtime source subtree, original notices and build evidence travel together. This replaces the earlier temporary execution probe described in [managed MCP qualification](AUGMENTOR-HARNESS.md#managed-mcp-and-preserved-tool-originals). It qualifies this packaging dependency; live MCP/OAuth, physical platforms, installed updates and the full accepted P0/P1 migration remain open.

## Reviewed inputs and replacement

[`release/quickjs/build.json`](../release/quickjs/build.json) pins the following public inputs. [`artifact.json`](../release/quickjs/artifact.json) independently pins all 23 retained artifact files, including `BUILD.json`. Original source copyright and license headers remain in the archives and notices.

| Input | Version or source identity | SHA-256 |
| --- | --- | --- |
| [QuickJS-WASI source](https://github.com/vercel-labs/quickjs-wasi/tree/5a7a0eeda87c99542f8cf3095b6d61ecfa755977) | 3.6.2; `5a7a0eeda87c99542f8cf3095b6d61ecfa755977` | `cb3a2e58fd7187104b9294962e205c28433ecb7653d75771a35ef98dfdfb8484` |
| [QuickJS-NG source](https://github.com/quickjs-ng/quickjs/tree/6d46d07d04041b40f4f49eaa7fdebe44c314c699) | upstream gitlink `6d46d07d04041b40f4f49eaa7fdebe44c314c699` | `a62cf1ff7d6d2f82b90a2d247a57e9eb56b81c03feb1f372a53923426e358cb0` |
| [WASI SDK](https://github.com/WebAssembly/wasi-sdk/releases/tag/wasi-sdk-32) | 32.0, Linux x64 | `55fc523ebfbc98f69d1034fcfcb83d1ff5610cd9ab7eceef6cd097a30ba4ef93` |
| [WASI libc source](https://github.com/WebAssembly/wasi-libc/tree/2fc32bc81b9f07f8d9525edea59bfbaf760c06d6) | SDK source pin `2fc32bc81b9f07f8d9525edea59bfbaf760c06d6` | `d12a1568d9394e693e6b189277ba70446f96b81a4790c515427865a0d5412372` |
| [LLVM compiler-runtime source](https://github.com/llvm/llvm-project/tree/4434dabb69916856b824f68a64b029c67175e532/compiler-rt/lib/builtins) | SDK source pin `4434dabb69916856b824f68a64b029c67175e532`; selected tracked subtree export | `56a18a20ccd53c978dedf39eb34011338853d5d4bcf6e41a7db5c6586b15ea06` |
| [Binaryen](https://github.com/WebAssembly/binaryen/tree/cb55d05caf7c33bc267d6281c197befe54e4dd54) | npm 130.0.0; build tool only | `127c4c2f06d4b802f5e507d6822d31bde1792d5af89a7d7e2444ef9c7899510b` |

The retained **638,390-byte** engine has SHA-256 **`79505123d7f65bd01202f41b40c2166952454950573402ef23b0bbf557775c82`**. It explicitly replaces the npm **637,405-byte** engine, SHA-256 `d4c9375f2b1ca4dc95f72c8aa2982a7a9951ac8011490d79c6582df732b4bbd9`. This is a source rebuild with different bytes; it is not claimed to reproduce the published npm binary. npm JavaScript and its version remain unchanged, and `distribution-overrides.json` records both executable hashes and the replacement.

The engine/interface sources are unmodified. The upstream Makefile requires WASI SDK 32; a README v30 example is not evidence for this release. The build retains upstream optimization/LTO/strip flags and adds linker map, extraction and trace reporting. SDK Clang identifies itself as `22.1.0-wasi-sdk` at the recorded LLVM commit. Two builds from separate freshly extracted temporary directories produced identical bytes for **all 23 retained files**. Node's WebAssembly module inspection found the same **12 imports and 450 exports** as the npm executable, compared as unordered declarations. ABI declarations and fixture execution establish the tested compatibility scope, not equivalence for every possible QuickJS program.

## Static source and notice coverage

`vendor/quickjs-engine/third-party/components.json` records the exact hashes of the SDK's LTO libc archive, compiler builtins archive and reactor startup object. `link-extraction.tsv` records **250 libc members and 16 compiler-runtime archive members** before LTO. `build-log.txt` retains normalized compiler/linker commands and trace; machine-specific directories are replaced with `$SDK`, `$SOURCE` and `$BUILD`. Extraction does not prove that every function remains after optimization.

The paired material includes:

- Full pinned QuickJS-WASI, QuickJS-NG and WASI-libc source archives, with their original headers.
- The pinned LLVM `compiler-rt/lib/builtins` subtree and LLVM/compiler-runtime license files, exported only from selected tracked files with Git blob identities checked. Untracked checkout files are excluded.
- Original QuickJS MIT texts; WASI-libc umbrella, Apache, LLVM exception and MIT texts; musl copyright, cloudlibc BSD, dlmalloc source with its notice, and LLVM/compiler-runtime texts.
- emmalloc source and musl-fts BSD notices conservatively accompanying the complete libc source archive. Their inclusion is not a claim that these implementations were linked.
- Source paths/hashes for each extracted builtins member. The SDK's `math-builtins.c.obj` comes from WASI-libc's math wrapper rather than the LLVM subtree; that distinction is recorded.

The **SDK libraries are verified release inputs and are not independently rebuilt here**. The source pins, release hash, selected object hashes and complete source/notices make that boundary explicit. This checkpoint rebuilds the engine; it does not claim an independently rebuilt compiler or SDK. Build tools are not copied into application packages. All third-party texts retain their own terms; Augmentor's source license does not replace them.

## Common staging and distribution checks

`scripts/build-quickjs.py` performs the reviewed source rebuild on Linux x64. Normal platform packagers use `scripts/quickjs_engine.py` through `stage-production.py`; they verify the retained portable WASI artifact rather than downloading the build toolchain.

```bash
python3 scripts/build-quickjs.py --out outputs/quickjs-rebuild-check
python3 scripts/stage-production.py --out outputs/production
python3 -m unittest discover -s tests -p test_quickjs_packaging.py
```

The rebuild refuses an existing output directory and any source/tool or executable hash change. The tool cache remains under ignored `outputs/`; LLVM export avoids `git archive` fetching an entire partial clone. Any intended change requires review of the source/build records and artifact pins.

Staging resolves the active engine from the actual Pi codemode import condition, supporting root and nested npm layouts. It checks Pi/codemode 1.1.0 and QuickJS-WASI 3.6.2 identities, the original npm executable hash and the exact optional extension inventory before substitution. The **five URL, encoding, headers, crypto and structured-clone WASM extensions remain excluded** with their exact original hashes: Pi codemode does not load them. They need separate qualification if a future feature requires them.

The engine remains at its SDK-resolved npm path. `licenses/quickjs/` contains the source/notices and build record, plus `native-component.json`; it does not duplicate the executable. Hash-bound verification rejects missing or changed executable/source/notice files, linked artifacts, unexpected native payloads, changed versions, path escapes and locally rehashed bundle records. `.gitattributes` preserves the reviewed supplier bytes on every checkout platform. The same staging checks run for Debian, macOS and Windows. Debian's strict native scan additionally requires this active engine; the tested common stage records **four components: Node, esbuild, Photon and QuickJS**. Full installers also inventory their platform/dictation components. Unknown or inactive executables still fail.

## Execution qualification and remaining gates

Implementation revision: **`d05043c153241d92d4fd96193546f6f60f1c5d86`**. [The handoff checkpoint](AGENT-HANDOFF.md#october-10-minimal-quickjs-packaging-checkpoint) records final focused checks, byte correspondence, prior-head hosted status and remaining acceptance scope.

The ordinary unselected production stage, using bundled **Node 24.19.0**, passes **64 cases with zero failures or skips**. This run includes actual Pi SDK MCP stdio/HTTP/codemode execution, private IPC, offscreen Qt, the loaded Browser, Harness controls and WebSocket boundaries with independently authored synthetic inputs. It uses the retained rebuild from normal staging with **no diagnostic overlay**. The source dependency's original npm WASM remains unchanged.

The eight new packaging cases exercise actual Node import/nested resolution and adversarial executable, static source/notice, inventory, version, symlink, foreign native and Git export failures. Existing packaging prerequisite/unknown-native cases (**four pass**) and npm-license cases (**seven pass**) also pass. Final fresh staging produces the same **19,088 production dependency files** and override/exclusion/prerequisite/notice bytes as the tested stage. All **287 compiled files** match and the npm inventory remains **126 named instances**. The handoff binds this evidence to the implementation revision; historical source-runtime counts remain scoped to their original revisions.

This does not qualify live provider/MCP endpoints, MCP OAuth UI/refresh, expired-session/auth/drop retry behavior, physical audio or macOS/Windows installed use. Matching-head platform/package checks and physical installed/update/rollback/privacy acceptance remain required. Browser-only MCP remains unavailable. The complete accepted P0/P1 migration is still binding, including context provenance/history/performance, embedded/live routing/resources, live Hindsight, integration receipts, Resonant Voice, wiki/search, plans/jobs/delegation, Home/mobile and multiple windows. The candidate remains unselected; do not merge/promote it, choose an owner release, retire DSH or mark the full goal complete from this packaging checkpoint.
