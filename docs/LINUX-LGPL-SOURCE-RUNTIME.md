<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

## October 4 actual application replacement progress

[The current checkpoint](../release/qualification/next-targets/20261004-native-upgrade-desktop-ending-checkpoint.json)
extends the retained source rebuild with installed Ubuntu Noble application tests.
All four marked replacement variants pass native ABI, complete file inventory and
official-runtime preservation. Core passes Desktop and both normal Browser
preference-child entrypoints; each loads the marked library, restores the official
runtime and starts another process with the marker absent. All twelve slots
and final independent preservation/closure now pass: all 32319 installed
application members, official/four recipient inventories and selector/process
ending checks remain exact. No model or voice starts occur in these checks. Graphical Browser,
other distribution ABIs, final corresponding-source/notice review and public
release remain open.

Exact source correspondence now covers all 72 linker/install transformations,
1770 direct object/compile joins, 68 Unity units with 932 additional CPP inputs,
and named generated-source controls. The 96 additional SPDX license texts are
separately authenticated. The generated QtQml grammar carries the Qt GPL
exception; its exact retained text matches the
[upstream 6.8.2 exception](https://github.com/qt/qtbase/blob/v6.8.2/LICENSES/Qt-GPL-exception-1.0.txt).
That exception describes conditions for generator output in a larger work;
applicability remains a recorded review, rather than a blanket GPL-only runtime
conclusion. The owner has not approved the 22-file licensing proposal. No license
or original build control changed. Historical failures below remain unchanged.

# Linux Qt/PySide source runtime work

The [source policy](../release/linux-lgpl-runtime-sources.json) pins seven official
Qt 6.8.2/PySide 6.8.2.1 archives and reviewed upstream commits. All actual archive
bytes and the official checksum records pass the
[acquisition report](../release/qualification/next-targets/20261002-lgpl-source-acquisition.json).
The acquisition tool saves partials on failure and refuses an unvalidated resume.
No detached archive signature or archive-to-Git equality is claimed. This is
source acquisition and the completed source build below; full product runtime,
closure/license review, independent rebuild, replacement and public release remain
false.

The [later PySide failure/checkpoint](../release/qualification/next-targets/20261002-qt-source-pyside-failure.json)
records all six Qt modules compiled/installed, Wayland client ON/server OFF and
actual shiboken library compilation before wheel creation refused missing
patchelf. That second image/tree/log is stopped and preserved. The recipe now
includes signed distro patchelf. The third fresh build also finishes all six
Qt modules, but wheel packaging refuses Ubuntu system Python's dist-packages
versus CMake's site-packages path. Its stopped tree/log is preserved. Pinned
upstream build_info_collector/ShibokenHelpers and actual sysconfig probes verify
the mismatch. The [official Linux venv workflow](https://doc.qt.io/qtforpython-6.8/building_from_source/linux.html)
makes both schemes agree. The fourth clean image creates a system-site-package
venv without pip/network; its driver verifies equal scheme suffixes and patchelf
before Qt compilation. All six Qt modules finish, but PySide QtQuick compilation
fails because its generated OpenGL header directory is absent. The supplied
subset configured OpenGL after Quick. Pinned upstream `collect_module_if_found`,
`HAS_QT_MODULE` and `check_qt_opengl` establish the ordering dependency; no upstream
source is patched. That fourth tree/log is stopped and preserved. A fifth fresh
root extracts the same verified archives, uses the same signed dependency image
and orders OpenGL before Qml/Quick. The fifth build now completes all19 commands
and three wheels. No intermediate binaries were reused. The
[completion report](../release/qualification/next-targets/20261002-lgpl-source-build-completed.json)
binds actual recipe, image, package inventory, logs, features and ELF discovery.
An [independent sixth container](../release/qualification/next-targets/20261002-independent-qt-source-rebuild.json)
also completes19 commands and all11 binding imports from fresh sources. All
producer/rebuilt wheel native member bytes agree. Of207 Qt ELF files,161 agree
and46 differ; generated Python config/cache/RECORD members and ZIP hashes differ.
This is a functional recipe rebuild, not bit-for-bit reproducibility or complete
recipient source-kit qualification. Historical failures remain preserved.

Build a separate artifact. Do not relabel the current vendor PyPI wheels, delete
their GPL-only libraries without closure review or assume a commercial license.
No owner runtime or selected desktop has changed. [Licensing](LICENSING.md) owns
the distribution conditions; this recipe is engineering work, not legal approval.

## Authenticated recipient toolchain reconstruction

The [410-row reviewed lock](../release/qualification/next-targets/20261002-ubuntu-source-toolchain-lock.json)
records binary architecture/version, matching source package/version, original
signed index path, package filename/size/hash and official acquisition URLs. It
matches the original [build inventory](../release/qualification/next-targets/20261002-qt-source-build-packages.tsv).
[Executed proof](../release/qualification/next-targets/20261002-ubuntu-source-toolchain-reconstruction.json)
is independent of the earlier local derived-image builds:408 exact installed
versions match four retained, verified Ubuntu releases and15 complete decompressed
Packages indexes. The two inherited audit packages at1:3.1.2-2.1build1.1 match the
actual signed20260825T120000Z noble-updates main Packages index; that snapshot's
complete matching Sources index also verifies. All410 signed binary records are
now covered. Only audit's corresponding Sources metadata was inspected; this is
not acquisition of all178 unique corresponding source pairs.

The five original InRelease files, seventeen complete plain indexes and original
keyring bytes are retained separately. [Acquisition tool](../release/acquire-ubuntu-toolchain.py)
requires the exact keyring hash and archive signer fingerprint, validates real
gpgv signatures and the full signed SHA256/size chain, then independently matches
binary/source versions and approved HTTPS pool paths before downloads. It does
not install packages, refresh APT or change trust. Actual410 .debs/395,555,966 bytes
match signed hashes/sizes. [Refusal probe](../release/probe-ubuntu-toolchain-auth.py)
executes ten invalid-key/release/index/package/source/URL/path/duplicate cases,
including a corrupted signed body with recomputed local hash and a modified cached
.deb. It changes only copies or in-memory policies; all originals are preserved.

With complete metadata under `metadata/` in a separate kit root, run the acquisition
tool with `--policy` pointing to the reviewed lock, `--root` pointing to that kit,
and `--acquire`. `gpgv` is required. Run the refusal probe with the same policy/root
after acquisition. Receipts are exclusively created; downloads may reuse an
existing file only after exact signed size/hash checks. No untrusted .deb runs
on the host. The [fresh builder recipe](../release/qt-source-runtime-recipient-builder.Dockerfile)
expects `debs/` and its exact locked SHA256SUMS in its build context. It verifies
both manifest and all bytes, installs absolute local package paths with Docker
`--network=none --pull=false`, then verifies the entire dpkg410-row inventory hash.

The first attempt with APT --no-download failed before installation at an internal
relative perl-base filename. Its recipe/log are preserved. Removing that option
allows the corrected network-disabled local-file install and exact inventory
comparison to pass. No APT network refresh or unsigned/trusted override was used.
The image derives only from the pinned public base plus authenticated package
objects, not the previous producer image. Normal UID1001, two CPUs,8GiB,512 PIDs,
no network/devices/host mounts/privileged mode then starts seven unchanged official
source archives with the published source-build driver; its dependency inventory
matches exactly. The earlier checkpoint observed one completed configure command;
[the later completion proof](../release/qualification/next-targets/20261002-authenticated-source-runtime-completion.json)
now records all19 commands and three produced wheels. No compiled producer
intermediates were copied. [Build verifier](../release/probe-source-qt-build.py)
checks all three RECORD inventories and imports all11 modules in both default and
explicit SDK environments. All native wheel members match the first producer;
161/207 Qt ELF files match and46 differ. A private probe copy initially refused
normal-user reading because it retained600 mode/root ownership; changing only
that fixture file's owner allowed its repeat, then the published verifier passed.
No source/build failure is inferred from that preflight permission error.

The second exact reviewed PySide producer hash is accepted by the derivation CLI
and gets the distinct6.8.2augmentor2 build tag. Its derivative has SHA256
5cb05190ddf1db3e2915662b8c744f56922f40bd03b84683b6651742cfb1c951.
A fresh runtime-only container from the reconstructed image has no producer tree
and passes11 imports, synthetic widget text, SVG red-pixel and QtQuick/plasma
component construction using the finite18-library scope. A fresh QtSvg recipient
source build finishes all three commands. The
[published replacement verifier](../release/probe-source-qt-replacement.py)
executes originalTrue/modifiedFalse results in fresh processes and checks every
original runtime file/symlink before and after; only Svg differs in the separate
candidate. These are explicit-path container probes, not product-entrypoint,
native graphics, complete source-kit or legal qualification.

[Ubuntu's snapshot service](https://snapshot.ubuntu.com/) supports historical
acquisition; the locally retained authentic objects/metadata make this finite
proof independent of future pool retention. A final offered kit still needs a
concrete corresponding-source/generated-shader/notice/control-script scope,
recipient instructions and suitable script permissions. Existing Augmentor source
licenses are unchanged; this checkpoint does not approve release licensing.

## Authenticated builder/base sources, shader and private kit checkpoint

[The October2 source-kit report](../release/qualification/next-targets/20261002-authenticated-recipient-source-kit.json)
extends the binary-only toolchain checkpoint above. The original builder has178
unique source package/version pairs; the public base has66, with64 shared and two
additional versions: openssl3.0.13-0ubuntu3.15 and perl5.38.2-3.2ubuntu0.4. The
[180-version source lock](../release/qualification/next-targets/20261002-ubuntu-builder-base-source-lock.json)
pins the original binary lock and [base inventory](../release/qualification/next-targets/20261002-public-noble-base-packages.json),
archive keyring, four signed releases, six complete compressed/plain Sources
indexes and565 original source objects. All565 files,1,358,989,460 bytes, were
actually acquired and match the authenticated signed size/hash chain. Every180
.dsc identity/checksum set matches Sources; uploader signatures are not separately
verified. Source objects were not extracted or executed.

[Source acquisition/recheck](../release/acquire-ubuntu-toolchain-sources.py) refuses
unsafe/symlink paths, changed cached files, mismatched source identities, missing
coverage and unapproved URLs. Publication uses an exclusive link and preserves
partial downloads; receipts use separate exclusively created temporary paths.
[The real refusal probe](../release/probe-ubuntu-toolchain-source-auth.py) passes12
altered-copy cases, including an invalid signed body with a recomputed local hash.
Eight small source-object refusal tests and six OCI/path tests also pass with
Python optimization enabled; those synthetic cases are distinct from actual
signed source acquisition and public-base verification.

[The base-export verifier](../release/verify-ubuntu-base-archive.py) verifies the
retained31,723,520-byte public OCI/Docker export, pinned original public index,
AMD64 manifest/config, all seven retained blobs, layer sizes and decompressed diff
ID. It does not import/extract/execute a filesystem or qualify an empty-daemon
restore. [Shader regeneration](../release/probe-source-plasma-shader.py) runs the
actual source-built qsb6.8.2 in the owned normal-user offline builder and reproduces
the exact published plasma.frag.qsb hash. Native shader rendering remains open.

The separately retained private kit18 has1,712 manifest files/2,072,651,811 bytes;
every path, size and hash was checked after assembly. It includes the seven Qt/
PySide archives and original checksum records,410 authenticated .debs, public base
export, all565 toolchain source objects and full original signed metadata,
146 upstream Qt/PySide notice members, published control/probe scripts and actual
build/runtime/replacement/shader evidence. Original toolchain archives retain485
regular copyright/common-license files and263 link references. The link map
resolves all410 builder and92 base package copyright paths against the correct
scope. This package-level collection does not prove compiled Qt file notice
mapping or package-specific legal compliance.

The README explicitly confines Augmentor's existing terms to Augmentor-authored
files, including controls, docs, policies and application shader/QML source.
Separately identified upstream components/notices retain their own terms;
generated outputs retain applicable underlying-source terms. A first kit17 scope
sentence was too broad about generated outputs; kit18 corrects it while preserving
kit17. Neither kit is publicly offered. The kit18 manifest hash is
0770ed3ccab87552b65c5c43fab77118f889f2019ef70a68ef076a43296d2229.
Suitable recipient control-script permissions, fresh README execution, empty-daemon
base import, compiled-content notice mapping, native/product/other-ABI runtime
qualification and final legal/release acceptance remain open. No repository
license change or selected installation change occurred.

Both hosted checks for the authenticated runtime completion8b7abed pass:
[Linux37047133286](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37047133286)
and [Mac37047133117](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37047133117).
The prior helper435eab2 also passes both
[Linux37045885191](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37045885191)
and [Mac37045885183](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37045885183).
This new source-kit checkpoint requires its own hosted checks.

## Completed build and separate runtime candidate

The [exact producer image recipe](../release/qt-source-runtime-builder.Dockerfile)
and [signed-package inventory](../release/qualification/next-targets/20261002-qt-source-build-packages.tsv)
identify the successful Noble x86_64/Python3.12 build. All11 requested binding
modules import with Qt6.8.2/PySide6.8.2.1. The actual build script differs from the
published driver only by two explanatory comments; an exact byte comparison
verified that claim. ELF inventory uses ZIP member magic bytes, including the
generator executable, rather than `.so` filenames. The generator wheel is for
building only.

Exact-source review found the unconditional PySide `QtExampleIcons` target offers
[GPL3 with Qt exception or commercial terms](https://github.com/pyside/pyside-setup/blob/f62088b4cd516a3080a6b2e68bc79903da8b67ce/sources/pyside6/qtexampleicons/module.c).
The module-subset/no-qt-tools options do not exclude it. The
[derivation tool](../release/derive-source-pyside-wheel.py) therefore verifies the
reviewed producer hash and every RECORD entry, writes a new build-tagged wheel,
removes only that unused extension/stub, regenerates RECORD and records provenance.
All other producer member bytes and wheel ABI/platform tags remain identical.
The original wheel remains unchanged. The
[receipt](../release/qualification/next-targets/20261002-source-pyside-derivation.json)
identifies both artifacts; this is a source-built derivative, not a relabelled
vendor wheel or a complete license approval. The generated distribution is
`PySide6`, not the existing managed profile's `PySide6-Essentials`; a distinct
runtime profile/lock is still required.

The [runtime stager](../release/stage-source-qt-runtime.py) follows actual SONAME
closure from the app's11 modules and explicit desktop/image/TLS/input/client
plugins. It copies only immediate members of QML, QtQuick, QtQml, Models and
WorkerScript modules. The
[full manifest](../release/qualification/next-targets/20261002-source-qt-runtime-stage.json)
records18 Qt libraries, every file/link and external SONAME. It excludes the SDK,
QmlCompiler and its tools, lint/debug plugins, unrelated QML trees and
[QuickControls test utilities](https://github.com/qt/qtdeclarative/blob/75534f3e7fff24ed7ccb364e2ed9950a73da879f/src/quickcontrolstestutils/CMakeLists.txt),
which build despite QT_BUILD_TESTS=OFF. Client Wayland plugins with `-server` in
the filename are retained according to their actual client source terms.

A [fresh runtime-only container probe](../release/qualification/next-targets/20261002-source-runtime-only-probe.json)
has no producer build tree and loads every mapped Qt library from the candidate.
The [probe source](../release/probe-source-qt-runtime.py) requires a fresh ordinary
UID1001 container built from the marked source image: copy the candidate as
`/work/qt`, the derived PySide/original shiboken wheels as `/work/wheels`, the
derivation tool as `/inputs/derive-source-pyside-wheel.py` and app effects as
`/work/effects`; run with Python3.12. It refuses an existing probe directory.
It verifies11 imports, offscreen widget synthetic text, an SVG red pixel, all
reported image decoder formats and QtQuick/plasma component construction with
QtExampleIcons absent. Explicit library/plugin/QML environment paths are required.
Software/offscreen Qt reports an unsupported size-hint warning, and the plasma
image provider is deliberately absent. Component construction is not ShaderEffect
rendering. Native Wayland/xcb, full app, accessibility, Browser, credentials,
physical speech, licensing closure, source rebuild and recipient-modified library
acceptance remain open. No selected artifact or owner runtime changed.

The exact sources identify additional embedded notice requirements: Core crypto,
Unicode/CLDR and MIME data; Network public suffix data; QML JavaScriptCore; Svg;
Wayland protocol copyrights; and PySide/shiboken PSF support. System-linked ICU74,
TLS, fonts and image libraries remain distro-owned providers. Their linkage does
not remove notices for embedded code. The [notice collector](../release/collect-source-qt-notices.py) verifies all seven
archive hashes and preserves146 original notice/attribution members (434226 bytes),
with [complete member hashes](../release/qualification/next-targets/20261002-source-notice-collection.json).
This conservative set includes unshipped modules/build tools and is not an exact
compiled-content mapping. Full archive/source kits and that mapping remain required; previous vendor ICU73 notice collections
must not be copied into this profile by assumption.

## Executed recipient library replacement fixture

The [recipient builder](../release/probe-source-qt-recipient-build.py) validates the
same official QtSvg archive, extracts fresh source/build roots and applies a
recorded one-function patch: `QSvgRenderer.isValid()` deliberately returns false.
It compiles/installs in a separate proof prefix using the unchanged matching Qt
SDK as a dependency; no compiled Svg intermediates are reused. Source before/after,
patch, recipe and library hashes are in the
[checked replacement report](../release/qualification/next-targets/20261002-source-qt-recipient-replacement.json).

A second runtime candidate preserves every original library except that deliberately
rebuilt Svg. The [execution probe](../release/probe-source-qt-recipient-execution.py)
runs fresh ordinary-user Python processes with each candidate's explicit runtime
environment. The original returns true for a valid synthetic SVG; the modified
one returns false. `/proc/self/maps` and hashes prove the changed library executes
from the recipient candidate, with no producer tree present. Original producer/
runtime and selected application remain unchanged. This verifies replacement in
the isolated source-runtime candidate. The final product's normal entrypoints,
complete offered source/toolchain kit and legal review still need acceptance.

## Build profile and dependency closure

The [marked Noble source-builder recipe](../release/linux-lgpl-source-builder.Dockerfile)
and [build driver](../release/build-linux-lgpl-runtime.py) now run in an isolated
offline container with two CPUs,8GiB and no host mounts/devices. Exact signed
distro build package inventory is hashed. The first Qt configuration disabled
AT-SPI/TLS/Fontconfig; its partial tree/logs are preserved and the container was
intentionally stopped, not promoted. The corrected empty-tree build requires all
nineteen tested cache features ON before compilation. QtBase,ShaderTools,Svg and
ImageFormats compile/install; QtDeclarative was still compiling at the
[checked boundary](../release/qualification/next-targets/20261002-qt-source-build-checkpoint.json).
That historical report is superseded by the later measured PySide failure above;
the fifth completed build supersedes it; downstream qualification remains open.
Actual PySide/shiboken .cmake.conf uses MICRO_VERSION2.1, producing6.8.2.1 despite
the archive's6.8.2 directory suffix. No selected runtime or owner packages changed.

The actual application uses Core/Gui/Widgets/Network/DBus, Svg, Quick/QuickWidgets
and QtTest qualification fixtures. PySide bindings also need Qml/OpenGL.
plasma.qml's ShaderEffect needs ShaderTools/qsb during the build. The source set
is qtbase → qtshadertools → qtsvg → qtimageformats → qtdeclarative → qtwayland →
pyside-setup. Each repository has a separate empty build directory and a common
prefix. Official [per-repository build documentation](https://wiki.qt.io/Qt_Build_System_Glossary#Per-repository_Build)
supports this route; qt-configure-module does not automatically build dependencies.

Keep xcb, Wayland client/EGL, Svg/image plugins and QtTest. Disable wayland-server
and omit QuickTimeline and QtTools. Qt QmlCompiler is built unconditionally and
has GPL-with-exception terms. Its recipient-runtime exclusion requires actual
ELF and dynamic-plugin closure proof; a few DT_NEEDED checks are insufficient.
QuickVectorImageGenerator is LGPL-capable, so do not blanket-label every vector
tool GPL-only. Preserve build tools needed by later modules until staging review.

## Executed recipe; downstream qualification still open

For Noble x86_64/Python 3.12, install matching signed distro build dependencies in
an isolated bounded builder and save their exact versions. Start qtbase with:

```sh
<qtbase-src>/configure -prefix <shared-prefix> -shared -release \
  -nomake tests -nomake examples -feature-testlib -feature-dbus \
  -feature-wayland -feature-accessibility -feature-accessibility-atspi-bridge \
  -icu -xcb -opengl desktop -egl -openssl-linked -fontconfig \
  -system-zlib -system-pcre -system-doubleconversion -system-freetype \
  -system-harfbuzz -system-libpng -system-libjpeg
cmake --build . --parallel 2
cmake --install .
```

`-icu` is the verified Qt option; `-system-icu` is not. Record the actual configure
cache/feature summary and library linkage, refusing unintended bundled fallbacks.
`-nomake tests` skips suites, while `-feature-testlib` retains QtTest for app checks.
Qt6 ignores the old license-selection flags: they are not licensing verification.
The pinned [configure help](https://github.com/qt/qtbase/blob/f1136de66638060b8a1ab9bc0cdf1a91dcb5ec01/config_help.txt)
and [module wrapper](https://github.com/qt/qtbase/blob/f1136de66638060b8a1ab9bc0cdf1a91dcb5ec01/bin/qt-configure-module.in)
are the command references.

Configure other modules with `<prefix>/bin/qt-configure-module <source>`, then
`-- -GNinja -DCMAKE_BUILD_TYPE=Release -DQT_BUILD_TESTS=OFF
-DQT_BUILD_EXAMPLES=OFF`. ImageFormats adds `-system-tiff -system-webp` before
`--`; Wayland adds `-feature-wayland-client -no-feature-wayland-server` before
`--`. Base configure flags cannot be blindly passed to module wrappers.

Build PySide using Python 3.12 and the reviewed setup.py options:

```sh
/work/build-python/bin/python3.12 setup.py bdist_wheel --qtpaths=<prefix>/bin/qtpaths \
  --module-subset=Core,Gui,Widgets,Network,DBus,Svg,OpenGL,Qml,Quick,QuickWidgets,Test \
  --no-qt-tools --limited-api=yes --parallel=2
```

Omit `--standalone`; it can copy ICU even when Qt used system ICU. Ship the
separately measured Qt closure and inspect actual wheel names, origins and RUNPATH.
The archive filename says 6.8.2.1 but its source directory may say 6.8.2; inspect
actual version metadata rather than infer equivalence. See official
[PySide build documentation](https://doc.qt.io/qtforpython-6.8/building_from_source/index.html)
and [pinned options](https://github.com/qt/pyside-setup/blob/f62088b4cd516a3080a6b2e68bc79903da8b67ce/build_scripts/options.py).

## New artifact and replacement gates

This needs a new source-build recipe/lock; the current managed policy explicitly
binds PyPI URLs and wheel inventories. A Noble build cannot be labelled as the
vendor manylinux_2_28 wheel or assumed compatible with another distro ABI.
Prove system ICU74 linkage, absence of copied ICU and all native/plugin mappings.
Record complete source/patch/generation inputs, compiler/dependency lock, logs,
configuration, SBOM and retained notices. Compare a second clean rebuild;
functional correspondence and byte identity are separate results.

The existing immutable runtime rejects changed libraries, so dynamic linking
alone is not recipient replacement acceptance. Implement an explicit user-selected
replacement root/profile with its own local hash receipt, same ABI/modules/target
and unchanged application identity. No vendor approval or administrator access
should be required for the user's library replacement; official validation stays
strict. Actually load a modified QtCore marker and independently replace
PySide/shiboken through every Desktop/Browser entrypoint. Verify loaded mappings,
Quick/QtTest, Wayland/xcb, GI, sound, Secret Service, restore and preserved user data.
Reject wrong ABI, malformed or interrupted replacement. Do not declare this passed
before the execution evidence exists.

Distribute complete corresponding source, patches, rebuild/install material and
notices to every recipient, with terms permitting the required library modification
and reverse engineering. Primary terms are
[LGPL3 §4](https://github.com/qt/qtbase/blob/f1136de66638060b8a1ab9bc0cdf1a91dcb5ec01/LICENSES/LGPL-3.0-only.txt)
and [Qt's LGPL obligations](https://www.qt.io/development/open-source-lgpl-obligations).
