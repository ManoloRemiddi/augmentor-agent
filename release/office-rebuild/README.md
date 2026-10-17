<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

## Completed-build source and notice export — October 17

[`collect-source-inputs.py`](collect-source-inputs.py) exports the already completed
ThinLTO diagnostic's source inputs to a new private directory. It checks the exact
terminal producer, engine assets, Core/Emsdk revisions, source diff and resource
drivers before copying anything. No builder restarts, engine adoption, network
fetch or model request is involved. Two small read-only/no-network XSLT containers
use the pinned builder image to reproduce the original generated licence files.

```sh
python3 -B release/office-rebuild/collect-source-inputs.py \
  --cache "$BUILT_CACHE" --producer "$TERMINAL_CONTAINER" \
  --output "$PWD/outputs/office-new-source-inputs"
```

The actual corrected export contains **123 files / 661,286,937 bytes**: committed
Core/Emsdk snapshots, the exact separate Core patch, 65 external files verified
against Core's `download.lst`, 59 unpacked-source receipts, recipe/resource/build
inputs, and the generated `LICENSE`, `LICENSE.html` and `NOTICE`. Both generated
licence files reproduce byte-for-byte using the actual build configuration.

An initial export used `git archive`, which honours Core's `export-ignore` and
omits tracked schema sources. Its directory/log and the failing authored regression
are retained. The corrected exporter streams Git blobs directly. Independent
inspection verifies all **149,173 Core files, including 58 schema files**, and all
**138 Emsdk files** against their committed Git object IDs. The exported patch
applies to restored original files and reconstructs all **33 modified Core files**
exactly. Source/default/installed engines and the completed build remain unchanged.

The new eight-case source-export suite plus existing Office/private-public notice
and packaging checks pass **24 Python tests**, no skips. Shell/Make evaluation,
unsafe identities/paths, linked inputs, changed sources and existing outputs refuse.
Committed source survives export-ignore; generated/uncommitted files are excluded.
[Qualification](source-inputs-qualification-20261017.json).

This is a verified **input export**, not a claim of complete corresponding source
or public distribution approval. Three Core gitlinks are explicitly excluded and
recorded. Emscripten runtime/toolchain source and notices, submodule scope, complete
rebuild/source delivery, representative documents/fonts/resource/security and
installed promotion/rollback remain separate. The public Office gate stays intact.

The repaired low-optimization **full-LTO** attempt is now terminal: exit 1,
OOMKilled=true, exact **8 GiB** peak/zero swap at final link. Its failed tree is
retained. The separate [ThinLTO driver](run-thin-lto.sh) requires a **fresh Core
build directory**, emits a verified LLVM ThinLTO summary and retains normal
`-Oz` optimization. The actual standalone probe returns 42 and resolves the
pinned Emscripten `thinlto` sysroot. Full-LTO objects are not reused.

A first ThinLTO configure fails because global compiler flags included link-only
options under a strict C++ check. The [additional MPL-2.0 build patch](thin-linker-resources.patch)
puts one-thread/cache controls in the Emscripten link rule. Its initial placement
conflicted with an earlier patch's reverse-check context; that failed tree is
retained. The final appended rule passes **all 18 original reverse checks and its
own reverse check** before launch. All original 39 recipe/source files are retained;
the copied experimental recipe adds this one public patch. Its preferred source
change is explicit. No warning check, module, format, runtime thread/memory policy
or application dependency is removed. The final fresh attempt now completes
**compile and package**, exit **0 / OOMKilled=false** at **09:01:32 UTC**, with
**6,951,043,072-byte** cgroup peak under the unchanged 8 GiB/zero-swap cap,
two CPUs, one job/nice 15 and no network. Six actual authored formats through
the original provider match the pinned engine's text, pages, missing-font sets
and all ten pages' raw pixels at 96 DPI. This is basic diagnostic output parity;
representative documents, fonts/performance/security, source/notice distribution,
GUI candidate integration, platforms and public redistribution remain unqualified.
[Exact evidence](thin-engine-qualification.json),
[owning guide](../../docs/HARNESS-OFFICE-PREVIEWS.md#fresh-thinlto-engine-build--october-15).

## Inspect a completed ThinLTO build without changing the app

Use the exact Node **24.19.0**, locked source dependencies and a fresh direct
child of this checkout's ignored `outputs/`. `UNSELECTED_APP` must be an ordinary
private app under `outputs/`, with the current default engine/entry identities.
`BUILT_CACHE` is the retained successful driver's `/office` mount source;
`TERMINAL_CONTAINER` identifies that exited successful builder. These commands
do not restart the builder or use an owner profile:

```sh
node release/office-rebuild/prepare-thin-candidate.mjs \
  "$UNSELECTED_APP" "$BUILT_CACHE" "$TERMINAL_CONTAINER" \
  "$PWD/outputs/office-thin-new-candidate"
node release/office-rebuild/compare-thin-candidate.mjs \
  "$PWD/outputs/office-thin-new-candidate/app" "$UNSELECTED_APP" \
  "$PWD/outputs/office-thin-new-comparison"
```

The builder requires terminal exit 0/no OOM, complete package receipt, pinned
builder/resource/driver/patch/source identities and exact output hashes. It
clones only `dist`, `node_modules`, Node and package manifests, retains MPL and
supplier notices, and gives both experimental engine and entry explicit own
versions. Their preferred source and resource profile are included; the source
closure for public distribution is still a separate gate. Existing outputs and
sealed bases are refused before writes. Failed diagnostic trees are retained.

The comparison runs each original provider in a separate process and uses the
same authored inputs for both. It needs Python/LibreOffice fixture generation,
Poppler (`pdftotext`, `pdfinfo`, `pdftoppm`) and the root's locked Sharp. It
checks exact input bytes/cache ownership/font notices and 96 DPI pixel parity;
`comparison.json`, PDFs and PNGs remain private for inspection. The lower-level
`source-entry-probe.mjs` keeps its default entry mode; `--thin` is explicit and
`--fixtures` copies only the six named authored inputs for paired tests. No
claim of a speed improvement follows from one short diagnostic run.

## Earlier experiments and default entry

The separate [low link-optimization driver](run-low-lto.sh) retains full LTO and existing Wasm runtime/thread/memory flags, but explicitly sets `--lto-O0 --lto-CGO0` alongside the existing one-thread controls. A small authored Wasm function compiles, executes to 42 and shows both flags exactly once in the pinned real linker invocation. The full source attempt uses a separately copied failed cache, the same **8 GiB/zero-swap** cap, two CPUs/one job/nice 15 and no network. It is an experimental build profile requiring its own output, performance and source/licence qualification; it does not update any application dependency or public release gate. The first full attempt fails before link because ccache writes outside the writable mount. Its complete failed tree/logs are retained. The repaired driver uses explicit `CCACHE_DIR`/`CCACHE_TEMPDIR` beneath `/office`; a separate copied cache reaches the real final linker, where both optimization flags and unchanged runtime memory/thread/table/entry flags are verified. The [environment record](environment.json) records the point-in-time process state, not a presumed build success. The source-built entry and public engine gate remain unchanged.

The October 15 default entry is [built from complete public source](../../packages/runtime/vendor/office-entry/BUILDING.md) as `@augmentor/office-entry@0.1.3-augmentor.1`. This replaces the opaque npm JavaScript entry; its default Wasm dependency remains unchanged. The earlier one-thread full-LTO **8 GiB** final-link retry OOMs (exit 1, exact cap, zero swap). The environment record retains all failed attempts separately from the successful ThinLTO diagnostic. Public binary approval remains open; no unchanged retry or memory-cap increase follows automatically.

[Admitted native actor completion](admitted-actor-completion.json) registers monitor/namespace identities before parsing, then verifies kernel exit/reaping before known-root cleanup. Final b3003bd source/ordinary 285-case and both original-viewer proofs pass; supplier/dependency/GUI and owner state are preserved. System Dash carries separate BSD/public-domain/GPL notice records. All-owner/durable/pre-ready/caller-PDF/full-native/distribution/OS and the preceding hosted Search GUI failure remain open; no promotion follows. [Owning scope](../../docs/HARNESS-OFFICE-PREVIEWS.md#admitted-native-actor-completion--october-15).

[Original-provider scratch ownership](provider-scratch-ownership.json) establishes an independent cleanup owner before authorized source copying, while retaining the MIT queue/cache and original GUI. At fc34230, focused 19/19 and both native viewers pass; source 281/282 retains a real guard-loss completion failure, ordinary 282/282 passes. Full qualification and promotion remain false; actor-completion, durable/all-owner and release gates remain. [Owning scope](../../docs/HARNESS-OFFICE-PREVIEWS.md#original-provider-scratch-ownership--october-15).

[Live-owner guard fault qualification](native-guard-drain.json) at edf50db closes stopped/killed guard admission stalls with direct Node supervision and broker death ownership. Source/ordinary 272-case and both original-viewer proofs pass; default/public/installed and full durable/crash/font/security/OS gates remain open. [Owning contract](../../docs/HARNESS-OFFICE-PREVIEWS.md#native-guard-loss-and-bounded-live-owner-drain--october-15).

[Independent native scratch guard qualification](native-independent-cleanup.json) at 8ce4334 adds actual owner/converter-group and stopped-tree recovery, with source/ordinary 270-case and both original-viewer proofs. It preserves the default engine/public gate; guard loss, durable/outer/caller-PDF recovery, fonts/security/native distribution and other OS mechanisms remain open. See [the owning contract](../../docs/HARNESS-OFFICE-PREVIEWS.md#independent-native-scratch-cleanup--october-15).

# Pinned Linux Office engine rebuild

This is a build environment and preparation record, not a qualified replacement
engine or public binary. The exact entry-package preferred source, a completed
engine build, actual output/conversion comparison and remaining notice/release
gates are still required. [Office qualification](../../docs/HARNESS-OFFICE-PREVIEWS.md#isolated-linux-engine-build--october-14)
records the current result. The original GUI and installed engine remain pinned.

The input is the **39 hash-verified source files** already shipped in
`@deepseek-ai/libreoffice-kit-wasm@0.1.5`. Its own scripts select LibreOffice
**bce0998afefdbc355585ca324285661a2170ba77**, Emsdk
**5eb0bde7585670252e8ba05e9d361627bffd08b5** and Emscripten **4.0.10**. Keep the
original MPL/MIT/third-party notices. These components are not relabelled MIT.

`Dockerfile` pins the Debian 13 base digest and installs the host build tools.
`host-packages-debian13.txt` records the actual package versions. Apt repository
contents can change: differing package versions require a new environment record.
This is not a claim of bit-identical image or engine reproduction. The earlier
Debian 12 definition/inventory are retained: GCC 12.2 fails Core's GCC >=13 check.
The successful preparation then uses GCC 14.2 with a fresh build directory.

## Reproduce in a fresh private directory

From this checkout after the locked npm dependencies are prepared, first validate
all real supplier files with the existing identity verifier:

```sh
python3 - <<'PY'
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('office', 'scripts/office_engine.py')
office = importlib.util.module_from_spec(spec)
spec.loader.exec_module(office)
office.validate_inputs(Path.cwd())
PY
```

Provide Node **24.19.0** for this Linux x64 trial and record its actual hash.
Create an empty cache on a filesystem with build space; do not use a selected
release, an existing source checkout or a RAM-backed temporary directory:

```sh
mkdir -p outputs
office_build_root="$(mktemp -d "$PWD/outputs/office-rebuild.XXXXXX")"
mkdir -m 700 "$office_build_root/tools" "$office_build_root/home" "$office_build_root/image-context"
cp -a node_modules/@deepseek-ai/libreoffice-kit-wasm/sources "$office_build_root/recipe"
cp -L "$(command -v node)" "$office_build_root/tools/node"
test "$("$office_build_root/tools/node" --version)" = v24.19.0
sha256sum "$office_build_root/tools/node"
docker build --file release/office-rebuild/Dockerfile --tag augmentor-office-rebuild:local "$office_build_root/image-context"
docker run --name augmentor-office-rebuild-local --init --read-only \
  --cap-drop=ALL --security-opt=no-new-privileges \
  --cpus=2 --memory=6g --memory-swap=6g --pids-limit=1024 \
  --user="$(id -u):$(id -g)" --workdir=/office \
  --env HOME=/office/home --env LANG=C.UTF-8 --env LC_ALL=C.UTF-8 \
  --env PATH=/office/tools:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  --env GIT_CONFIG_NOSYSTEM=1 --env GIT_CONFIG_GLOBAL=/dev/null --env GIT_TERMINAL_PROMPT=0 \
  --mount "type=bind,src=$office_build_root,dst=/office" \
  --tmpfs /tmp:rw,nosuid,nodev,size=536870912 \
  augmentor-office-rebuild:local /bin/bash -c '
    set -euo pipefail
    umask 077
    node /office/recipe/scripts/checkout-wasm.mjs
    for stage in prepare verify configure compile package; do
      nice -n 15 node /office/recipe/engine/wasm-source/build.mjs \
        --stage "$stage" --source /office/recipe/.build/wasm/core \
        --emsdk /office/recipe/.build/wasm/emsdk --build /office/build \
        --tarballs /office/tarballs --output /office/dist --jobs 1
    done'
```

The reviewed trial fetches the same pins directly into `/office/core` and
`/office/emsdk`; its fresh second build is `/office/build-debian13`. These paths
are container-local, so the supplier's no-whitespace path restriction is met even
when the host checkout has spaces. Path/environment differences are captured by
the supplier build identity. The trial's one-job/two-CPU/6-GiB limits are a local
resource profile, not acceptance of upstream automated-release resource gates.

Retain failed logs, directories and container identity. Inspect actual container
state and the build receipt before resuming; a timeout alone does not establish
termination. Use a fresh build directory after compiler/environment changes.
The supplier refuses changed input or incomplete output identity. No copied
prebuilt `soffice.wasm`, changed approval label or successful configuration can
stand in for a successful compile receipt. Keep generated source, toolchain,
external archives, logs and binaries outside Git; publish only reviewed evidence.

The October 14 Debian 13 trial passed configuration and reached final `soffice.js`
linking, but `wasm-ld` received SIGKILL and the container exited 1 with
`OOMKilled=true` under the 6 GiB limit. That profile is insufficient for the
observed final link. Keep its failed state; assess available host resources and
record a separate resource profile before any resumed attempt. No engine receipt
or conversion/rendering comparison is qualified.

## Controlled final-link experiment — October 14

`run-thread-limited.sh` resumes verify/compile/package in a **separate copy** of
the configured Debian 13 trial, preserving the failed original tree and the same
container-local `/office` paths. The driver expects `core`, `emsdk`, `recipe`,
`tools/node`, `tarballs` and `build-debian13` under that private root. Copy these
inputs with their original paths before invoking it; do not run it in a selected
application or the original failed-build directory. Mount the reviewed driver
read-only in the same pinned container, with the preceding CPU/RAM/swap/PID caps.

The actual pinned linker reports **LLD 21.0.0**. `EMCC_CORES=1` and
`BINARYEN_CORES=1` limit compiler helpers; `EMCC_CFLAGS` explicitly forwards
`-Wl,--threads=1,--thinlto-jobs=1` to native `wasm-ld`. Full `-flto`, runtime
Pthread pool and memory flags remain unchanged. Debug intermediates go to disk.
The driver records these extra resource flags separately because the supplier's
existing build identity does **not** capture them. Never infer byte identity or
public approval from that original identity after adding flags.

A tiny authored C++ probe first compiles and runs with both native flags. The
actual full-engine relink also receives both flags, but exits **1 / OOMKilled**
at **18:20:29 UTC**, with a **6,442,450,944-byte** cgroup peak, exactly its limit.
Both original and controlled failures remain retained. Reducing linker threads
alone does not qualify a 6 GiB build or solve the missing preferred-entry source.
See the [environment record](environment.json) and
[Office guide](../../docs/HARNESS-OFFICE-PREVIEWS.md#controlled-linker-resources--october-14).

## Native sandbox feasibility probe

`native-sandbox-probe.py` is an independently authored **Linux x64 diagnostic**,
not a shipped Host helper, automatic fallback or qualified replacement engine.
It requires already installed Debian-compatible LibreOffice Writer/Calc/Impress,
bubblewrap, Liberation fonts, fontconfig, liblangtag, Python 3.13 and Poppler.
It installs no package and refuses an existing output directory:

```sh
python3 -B release/office-rebuild/native-sandbox-probe.py \
  --source-ref "$(git rev-parse HEAD)" \
  --output "$PWD/outputs/native-office-new-attempt"
```

The script creates independent flat ODF fixtures, exports all six required Office
formats, then reads actual converted PDF text. Each command gets fresh private
profile/home/cache directories, a read-only input and bounded read-only system
payload, dropped capabilities, cleared environment and separate network/PID/user
namespaces. No owner home, GPU, display, DBus, service, model or personal document
is exposed. The fixed payload is deliberately x64/Debian-specific; a different
architecture or filesystem layout needs its own adapter qualification.

Synthetic negative checks cover outside-file/host-environment/process/loopback
access, read-only input/system files, bounded Liberation font availability and
owned-process cancellation at startup and after export dispatch. A 1,200-pixel
image at two inches tests actual 192 DPI PDF downsampling. Host deadlines,
per-process address-space/CPU/file-size limits and disabled core dumps bound the
experiment. Those limits are not a full engine cgroup or production archive,
aggregate scratch, admission and font-contract qualification.

Retain failures and their private diagnostics. The cancellation observer walks
children of every thread in the **owned** tree; a main-thread-only list misses
LibreOffice's worker-thread child. No unrelated processes are enumerated or
terminated. Generated profiles/documents/PDFs stay outside Git.

The original MIT GUI/provider/queue and pinned kit/Wasm remain unchanged. Native
integration still requires complete authorized-read/error/queue/cache/font/ZIP/
timeout/disposal semantics, macro/external-resource negative cases, complex
layout and original-GUI proofs, dependency/source/notice packaging and explicit
platform gaps. LibreOffice and its linked dependencies retain their own licences.
The [owning Office guide](../../docs/HARNESS-OFFICE-PREVIEWS.md#native-linux-office-feasibility--october-14)
records exact-source results; this diagnostic never relaxes the packaging gate.
