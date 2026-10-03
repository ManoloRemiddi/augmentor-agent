<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Ubuntu Qt test fixture correction

The Ubuntu 26.04 hosted suite's exit 139 is reproducible in the browser setup
dialog test alone. Replacing its class-level MagicMock method with a real
fixture subclass override passes both unchanged UI test bodies, including after
all 29 Window cases. The application UI, PySide/Qt runtime, dependencies and
test cases stay unchanged. See [the exact evidence](../release/qualification/next-targets/20261003-ubuntu-qt-fixture-correction.json).
This is a focused fixture correction; the complete hosted suite needs a fresh run.

The original clean `4f99696` source runs in an owned Ubuntu qualification image
with PySide/Qt 6.10.2 and Python 3.14.4. Hosted CI used Python 3.14.3; that difference
is recorded. The original dialog module exits 139. Its faulthandler traceback
points to `browser_setup.py:28`, connecting choose_browser, with native
`PySide::qobjectConnectCallback` on the stack. All 29 Window cases pass before the
same crash in the ordered repeat, so prior Window execution is unnecessary.

Independent synthetic dialogs distinguish ordinary and mocked class methods.
Plain and decorated base/derived connections pass. A class-level MagicMock
replacing an unrelated method crashes the undecorated connection; a real method
override or explicitly decorated synthetic slot passes. A private subclass with
a real load_registrar override then passes the two inherited public test bodies.
The corrected public fixture also passes its actual two cases and the 31-case
Window-then-Browser invocation in fresh UID1001 profiles with networking disabled.

The tagged [PySide reflection source](https://raw.githubusercontent.com/pyside/pyside-setup/v6.10.2/sources/pyside6/libpyside/dynamicqmetaobject.cpp)
examines callable class members' `_slots` attributes. The
[capsule decoder](https://raw.githubusercontent.com/pyside/pyside-setup/v6.10.2/sources/pyside6/libpyside/pysideslot.cpp)
returns null for a non-capsule value; MagicMock advertises `_slots` as another
mock. Those source facts support the inferred reflection mechanism, while the
exact crashing native instruction remains unsymbolized. The separate PYSIDE-3266
slot-with-result release note does not establish this issue's identity.

The cached fixture originally lacks QtTest. A preserved APT simulation and normal
official transaction add only libqt6test6 and python3-pyside6.qttest, without
upgrading/removing the existing stack. The failed first offline/network attempt
is retained. This is a test prerequisite, not a product dependency correction.
The first root follow-up driver also refuses its marker before any copy; the
exact-marker repeat succeeds. Original source archives, drivers and failing
traces remain separate from the corrected fixture results.

The distro workflow now enables Python faulthandler for native fatal traces.
No platform skip hides this dialog case. Windows' actual native desktop teardown
failure remains a separate unresolved issue; no teardown change follows from
these fixture findings. Complete session/audio/Browser/installers/source/legal
and release gates remain open, and all five rollout points stay active.
