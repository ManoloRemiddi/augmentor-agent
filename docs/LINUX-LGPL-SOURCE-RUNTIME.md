<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

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
