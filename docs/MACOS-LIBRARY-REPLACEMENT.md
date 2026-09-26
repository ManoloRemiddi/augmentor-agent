<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Replacing LGPL libraries in the Mac preview

You may modify and replace the LGPL libraries and reverse engineer the combined
work as needed to debug those modifications. Augmentor's resale restriction does
not change the licenses or these rights for third-party libraries.

The release provides Qt 6.8.2 and PySide/Shiboken 6.8.2.1 source archives and a
native-dependency source archive alongside its binary download. Full GPL/LGPL
texts and individual notices are inside `Contents/Resources/app/licenses`.
The application's source includes its build scripts and pinned Python wheel lock.

Work on a copy of the app, keep your data separately, and close running Augmentor
and browser connections before replacing libraries. Under
`Contents/Resources/app/python/lib/python3.12/site-packages`, replace the relevant
PySide6 Qt frameworks/plugins, PySide extensions or shiboken6 library with your
ABI-compatible build. Use the provided upstream sources and their build
instructions. Retain macOS framework install names and relative runtime paths.
The builder's Qt module list is in `scripts/stage-macos-qt.py`.

For libvips, use the supplied sharp-libvips recipe with the supplied dependency
archives/patches to rebuild its shared library. Replace the matching library in
`Contents/Resources/app/dsh/node_modules/@img/sharp-libvips-darwin-arm64/lib`.
Its wrapper is Apache-licensed sharp. The source archive includes the Rust crates
from librsvg's lock for reproducible source availability; expand them or configure
Cargo to use their contents when building offline. The original build recipe may
otherwise fetch those same versions online. The manifest records their checksums.

After changing native files, renew the local ad-hoc integrity signature on your
copy using macOS's `codesign --force --deep --sign - '/path/to/your/app.app'`, then
verify with `codesign --verify --deep --strict '/path/to/your/app.app'`. This does
not require an Apple Developer account, notarize the copy, or disable Gatekeeper.
macOS may ask you to approve your modified app again. No vendor signing key is
needed. Test your copy before replacing an installation; keep the previous copy
outside Finder-indexed application directories for rollback.

The Python and Node launchers dynamically load these libraries. Augmentor does
not enforce a vendor-only library signature or reject the modified library based
on a stored hash at runtime. Packaging-time inventories identify the distributed
release; they do not take away your ability to run a modified copy.
