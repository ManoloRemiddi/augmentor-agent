<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Linux Qt/PySide source runtime work

The [source policy](../release/linux-lgpl-runtime-sources.json) pins seven official
Qt 6.8.2/PySide 6.8.2.1 archives and reviewed upstream commits. All actual archive
bytes and the official checksum records pass the
[acquisition report](../release/qualification/next-targets/20261002-lgpl-source-acquisition.json).
The acquisition tool saves partials on failure and refuses an unvalidated resume.
No detached archive signature or archive-to-Git equality is claimed. This is
source acquisition with the measured partial builds below; full runtime, closure/
license review, independent rebuild, replacement and public release remain false.

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
and orders OpenGL before Qml/Quick. It is compiling QtDeclarative at this checkpoint;
no intermediate binaries are reused. Runtime completion and every downstream
qualification gate remain false. Historical checkpoints and all failures remain
in the report; a started build is not completion.

Build a separate artifact. Do not relabel the current vendor PyPI wheels, delete
their GPL-only libraries without closure review or assume a commercial license.
No owner runtime or selected desktop has changed. [Licensing](LICENSING.md) owns
the distribution conditions; this recipe is engineering work, not legal approval.

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
full Qt/PySide build and downstream qualification remain incomplete.
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
