#!/bin/bash
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
# Fresh source build only. Do not reuse full-LTO objects or an installed app.
set -euo pipefail
umask 077
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_TERMINAL_PROMPT=0
export CCACHE_DIR=/office/thin-compiler-cache CCACHE_TEMPDIR=/office/thin-compiler-cache/tmp
export EMCC_CORES=1 BINARYEN_CORES=1 EMCC_DEBUG=1 EMCC_TEMP_DIR=/office/thin-build-debug
# Emscripten appends these flags after gbuild's -flto. Its own thinlto sysroot
# directory is separate from full-LTO libraries. Keep ordinary -Oz optimization.
export EMCC_CFLAGS='-flto=thin'
mkdir -p "$CCACHE_TEMPDIR" "$EMCC_TEMP_DIR"
current_stage=preflight
phase() {
 python3 - "$1" "${2:-$1}" <<'PY'
from pathlib import Path
import json,os,sys,time
root=Path('/office');item={'phase':sys.argv[1],'stage':sys.argv[2],'time':time.time(),'memoryPeakBytes':int(Path('/sys/fs/cgroup/memory.peak').read_text()),'memoryMax':Path('/sys/fs/cgroup/memory.max').read_text().strip(),'swapMax':Path('/sys/fs/cgroup/memory.swap.max').read_text().strip(),'cpuMax':Path('/sys/fs/cgroup/cpu.max').read_text().strip(),'compilerControls':{name:os.environ[name] for name in ('EMCC_CORES','BINARYEN_CORES','EMCC_CFLAGS','CCACHE_DIR')}}
p=root/'status-thin.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(item)+'\n');tmp.replace(p);print(json.dumps(item),flush=True)
PY
}
trap 'phase failed "$current_stage"' ERR
phase preflight
python3 - <<'PY'
from pathlib import Path
import os,json,hashlib
root=Path('/office')
if (root/'build-thin').exists():raise RuntimeError('Use a fresh build directory; preserve existing build state.')
patch=root/'thin-linker-resources.patch';patch_target=root/'recipe/engine/wasm-source/patches/0032-augmentor-linker-resources.patch'
if patch_target.exists():raise RuntimeError('Use the pinned original recipe without an unreviewed additional patch.')
patch_target.write_bytes(patch.read_bytes())
profile={'schema':'augmentor-office-thin-lto-profile/1','compilerControls':{name:os.environ[name] for name in ('EMCC_CORES','BINARYEN_CORES','EMCC_CFLAGS','CCACHE_DIR')},'driverSha256':hashlib.sha256((root/'run-thin-lto.sh').read_bytes()).hexdigest(),'freshFullCompilationRequired':True,'oldCoreBuildObjectsReused':False,'preferredSourceChanged':True,'additionalBuildOnlyPatchSha256':hashlib.sha256(patch.read_bytes()).hexdigest(),'additionalPatchLicense':'MPL-2.0','runtimeWasmMemoryThreadFlagsChanged':False,'supplierIdentityCapturesCompilerOverride':False,'outputQualification':False,'publicRedistributionQualified':False}
(root/'thin-resource-profile.json').write_text(json.dumps(profile,indent=2)+'\n')
(root/'thin-probe.c').write_text('int augmentor_probe(void) { return 42; }\n')
PY
current_stage=compiler-probe
phase compiler-probe
nice -n 15 /office/emsdk/upstream/emscripten/emcc /office/thin-probe.c -Oz -flto -S -emit-llvm -c -o /office/thin-probe.ll
nice -n 15 /office/tools/node --input-type=module -e 'import {readFileSync} from "node:fs";import assert from "node:assert/strict";const ir=readFileSync("/office/thin-probe.ll","utf8");assert.match(ir,/\^0 = module:/);assert.match(ir,/summaries:/);console.log("Actual compile override emits ThinLTO summaries");'
for stage in prepare verify configure compile package; do
 current_stage="$stage"
 phase "$stage"
 nice -n 15 /office/tools/node /office/recipe/engine/wasm-source/build.mjs --stage "$stage" --source /office/core --emsdk /office/emsdk --build /office/build-thin --tarballs /office/tarballs --output /office/dist-thin --jobs 1
done
phase complete
