<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

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
