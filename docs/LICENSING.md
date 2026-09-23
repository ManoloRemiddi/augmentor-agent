<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Licensing and distribution decision

## Augmentor source license — 23 September 2026

Augmentor-authored Desktop and Browser code uses **[MIT with Augmentor Resale
Restriction, version 1.0](../LICENSE)** (`LicenseRef-Augmentor-MIT-Resale-1.0`).
The full MIT text and the overriding resale condition form one combined license.
They are not an offer to choose unrestricted MIT instead.

Anyone may read, inspect, copy, use, modify and share the code. Personal and
business use, including production and paid work using Augmentor as a tool,
are free. Selling or reselling Augmentor itself, including modified versions,
requires prior written permission from Manolo Remiddi. The condition must travel
with copies and cannot be waived by redistribution or sublicensing.

[Request resale permission](https://augmentoragent.com/licensing.html#permission).
Describe the license in full; do not advertise this source as unqualified MIT
or OSI-approved open source. Package metadata uses `SEE LICENSE IN LICENSE`;
source headers use the custom SPDX identifier above.

This decision applies to source distributed with the new combined license and
future builds from that source. Previously distributed MIT copies and releases
retain their original permissions; no historical release is retroactively
relicensed. The September 6 MIT decision below is superseded for new source.

The public source repository is a clean snapshot of the maintained Desktop and
Browser code. Private development history and its artifacts are not published.
See [public source publication](PUBLIC-SOURCE.md) for scope and privacy checks.

The native application uses PySide6 with dynamically loaded Qt libraries under
their applicable LGPL terms. Separately identified components retain their own
licenses and notices.

## Native UI

PyQt is GPLv3/commercial, whereas Qt for Python offers LGPL licensing. Imports and
signals have been migrated to PySide6. Development is pinned to PySide6 Essentials
and Shiboken 6.8.2.1. The initial Debian package will depend on the distribution's
replaceable Python/Qt libraries, rather than embedding the development wheels.

Required UI modules: QtCore, QtGui, QtWidgets, QtNetwork, QtDBus and SVG image
support. QtTest is a test dependency. No GPL-only Qt module may be introduced into
the distributed application without a new licensing decision.

Desktop control additionally uses distribution-supplied GLib/GI, AT-SPI,
GStreamer (base/video and PipeWire), the desktop portal and KWin. These are
declared system dependencies, not copied into the Augmentor artifact. Record
their installed versions and retrieve the corresponding Debian source and
copyright records when reviewing that distribution. Any later bundle must
inventory those binaries and their transitive notices separately.

The release must:

- Identify PySide/Qt and the applicable licenses prominently in About/Licenses.
- Preserve copyright, LGPL/GPL license texts and third-party notices for every
  component actually redistributed; include the complete combined Augmentor license.
- Keep shared libraries replaceable, document installation/replacement and permit
  reverse engineering needed to debug library modifications. Do not add an EULA
  or technical check that removes these rights.
- Record exact library versions/source packages. If we redistribute LGPL binaries,
  provide their complete corresponding source and build/installation material by
  a compliant delivery method. A link to a moving upstream branch is insufficient.
- When dependencies are installed from Debian's repository instead of being
  redistributed inside our artifact, identify them and document Debian source
  retrieval. Review any later wheel/AppImage/Flatpak bundle separately.

This is a distribution engineering decision based on the official terms; full
artifact compliance remains a release gate, including the chosen delivery channel.

## Engines, memory and JavaScript dependencies

The pinned Pi packages declare MIT. The inspected DSH repository and Hindsight
repository also carry MIT. DSH and Hindsight are initially separately installed
services; their dependencies and model/service terms still need review if bundled.
API credentials and model weights are never part of an Augmentor release.

Production npm lock entries currently declare MIT, Apache-2.0, BSD-3-Clause, ISC,
0BSD, BlueOak-1.0.0 or Unlicense. Packaging inventories the actual installed tree,
checks it against the lock, and collects license/notice files. Missing texts need
reviewed, version-bound entries in `licenses/catalog.json`; an SPDX field by itself
is not sufficient. The catalog retains upstream source URLs and file hashes.
Dependency upgrades must pass this check again.

Pi's optional native terminal clipboard dependency is not part of our planned
distribution. Its upstream package omits a license text and includes additional
Rust code requiring a separate transitive audit. Pi explicitly tolerates its
absence; Augmentor's own Qt/browser clipboard operations do not use it. Remove it
only from staged release dependencies and prove the packaged Pi runtime and actual
UI clipboard behavior still work. Retain other optional dependencies needed by the
SDK, such as the appropriate esbuild binary. This is not a blanket omission of
optional dependencies.

Bundled executables require their own notice inventory, including Node and the
esbuild binary's Go/third-party components. Do not claim the npm metadata scan
alone audits code statically included in executables.

The binary scan identified Pi's bundled `examples/extensions/doom-overlay`
WebAssembly program. Upstream sample applications are excluded from the release
tree as a whole; they are not required by the SDK or Augmentor. The engine's
package-level MIT metadata must not be treated as the license for such samples.

The required Photon image module is rebuilt instead of excluding image support.
Its npm 0.3.4 release records source commit
`685f5b155b36c5611c08ca678bb78ddbab3edbac` (the Rust crate there identifies itself
as 0.3.3). `scripts/build-photon.py` pins that source, Rust 1.97.1, wasm-bindgen
0.2.100 and `release/photon/Cargo.lock`. The generated Node.js glue and WASM are
kept together in `vendor/photon-node`, with a modification/build record and hashes.
The upstream npm metadata version is retained; `distribution-overrides.json`
explicitly identifies the rebuild in installed packages.

The rebuild collects license texts for all 97 active normal/build Rust packages,
Rust's standard-library copyright inventory, and the embedded Roboto font's Apache
license and Google copyright. Its PNG/resize checks preserve exact fixture pixels;
the installed Pi SDK also successfully reads and resizes a 3200×2000 fixture to
2000×1250. These tests verify compatibility of the replacement, not arbitrary
image-processing algorithms. New dependency expressions or missing notices stop
the rebuild. Ordinary release builds verify the recorded artifacts and do not
silently re-resolve Rust dependencies.

## Authorship and repository

Preserve copyright attribution and the complete combined license on Augmentor-authored
files. Preserve existing third-party notices without applying Augmentor terms to them.
Third-party license text is reproduced verbatim with its original copyright;
Augmentor's header must not be prepended as if we owned it. Development of both
surfaces stays in one private unified repository. Public source publication uses
a separately audited snapshot; binary publication requires its own release
evidence and review for private configuration.

## Primary sources inspected

- [Riverbank PyQt license](https://www.riverbankcomputing.com/software/pyqt/intro)
- [Qt LGPL obligations](https://www.qt.io/development/open-source-lgpl-obligations)
- [Qt for Python licenses](https://doc.qt.io/qtforpython-6/licenses.html)
- [Pi license at the npm release's recorded git head](https://github.com/earendil-works/pi/blob/d981de1229ef899957bbe968bc8dcda02a21f477/LICENSE)
- [DSH license](https://github.com/ManoloRemiddi/deepseek-harness/blob/master/LICENSE)
- [Hindsight license](https://github.com/vectorize-io/hindsight/blob/main/LICENSE)
