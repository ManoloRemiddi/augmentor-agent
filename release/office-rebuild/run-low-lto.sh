#!/bin/bash
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
# Experimental low link-optimization profile. Use a separate private /office copy.
# Preferred source and runtime flags are unchanged; this output needs new qualification.
set -euo pipefail
umask 077
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_TERMINAL_PROMPT=0
export CCACHE_DIR=/office/low-lto-compiler-cache CCACHE_TEMPDIR=/office/low-lto-compiler-cache/tmp
mkdir -p "$CCACHE_TEMPDIR"
export EMCC_CORES=1 BINARYEN_CORES=1
export EMCC_CFLAGS='-Wl,--threads=1,--thinlto-jobs=1,--lto-O0,--lto-CGO0'
export EMCC_DEBUG=1 EMCC_TEMP_DIR=/office/linker-low-lto-tmp
mkdir -p "$EMCC_TEMP_DIR"
current_stage=preflight
phase() {
 python3 - "$1" "${2:-$1}" <<'PY'
from pathlib import Path
import json,os,sys,time
root=Path('/office');value={'phase':sys.argv[1],'stage':sys.argv[2],'time':time.time(),'pid':os.getppid(),'memoryPeakBytes':int(Path('/sys/fs/cgroup/memory.peak').read_text()),'memoryMax':Path('/sys/fs/cgroup/memory.max').read_text().strip(),'swapMax':Path('/sys/fs/cgroup/memory.swap.max').read_text().strip(),'cpuMax':Path('/sys/fs/cgroup/cpu.max').read_text().strip(),'threadControls':{name:os.environ[name] for name in ('EMCC_CORES','BINARYEN_CORES','EMCC_CFLAGS')}}
p=root/'status-low-lto.json';temporary=p.with_suffix('.tmp');temporary.write_text(json.dumps(value)+'\n');temporary.replace(p);print(json.dumps(value),flush=True)
PY
}
trap 'phase failed "$current_stage"' ERR
phase preflight
python3 - <<'PY'
from pathlib import Path
import hashlib,json,os
root=Path('/office');identity=root/'build-debian13/dsh-build-identity.json'
if not identity.is_file():raise RuntimeError('Use a separately copied, previously configured pinned build.')
value={'schema':'augmentor-office-low-lto-profile/1','compilerResourceFlags':{name:os.environ[name] for name in ('EMCC_CORES','BINARYEN_CORES','EMCC_CFLAGS')},'debugOutputOnDisk':os.environ['EMCC_TEMP_DIR'],'originalBuildIdentitySha256':hashlib.sha256(identity.read_bytes()).hexdigest(),'supplierIdentityCapturesExtraResourceFlags':False,'runtimeWasmThreadOrMemoryFlagsChanged':False,'fullLtoRetained':True,'linkOptimizerLevel':0,'linkCodegenLevel':0,'linkOptimizationProfileChanged':True,'compilerCacheDirectory':os.environ['CCACHE_DIR'],'outputComparisonQualified':False,'publicRedistributionQualified':False}
(root/'low-lto-resource-profile.json').write_text(json.dumps(value,indent=2)+'\n')
PY
for stage in verify compile package; do
 current_stage="$stage"
 phase "$stage"
 nice -n 15 /office/tools/node /office/recipe/engine/wasm-source/build.mjs --stage "$stage" --source /office/core --emsdk /office/emsdk --build /office/build-debian13 --tarballs /office/tarballs --output /office/dist-debian13 --jobs 1
done
phase complete
