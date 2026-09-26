<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Mac recovery and shared rendering qualification

This work continues the Mac feedback from the Sponsor management task. The target
is the owner's 32 GB M4 Mac Mini; the 16 GB Mac remains a separate working install.
Preserve the approved UI, runtime-first DSH setup in the three-dot menu, eight-edge
resizing, the first Fn+Space binding, and private models/conversations.

## Source convergence

Branch `fix/macos-recovery-parity` integrates the guided setup/menu/resize branch
(PR #13), platform contract (PR #14), and earlier flare correction (PR #15).
It does not contain Sponsor/workspace-embedding PR #12. That remains a separate
integration item. A clean build of this branch replaces the former source overlays.
No public release or Linux installed selection is changed by this source work.

## Two Mac shortcuts

Settings uses the shared first/second instance list. The Mac login service owns
both native Carbon registrations. Its protocol accepts an optional instance ID;
old requests still address main. Each activation targets its own IPC socket and
cold-launches with the appropriate instance argument. The existing primary
shortcut file is preserved; secondary gets a separate file only after assignment.
It starts unassigned, so no shortcut is invented or stolen from another app.
Conflicts and invalid instance IDs fail before changing either saved binding.
Closing a window does not unregister the login-owned shortcuts.

The Settings connection action now routes through the same `open_setup` action
as first run and the three-dot menu. No controls move. Maintenance status also
reports only whether a draft exists, never its text; maintenance close refuses
unsent or unacknowledged input as well as active work. This protects new builds;
older installed versions cannot prove or preserve an unsent draft through IPC.

## Shared native-resolution plasma

The previous CPU detail restoration still took about 25–29 ms per field on the
Mac and used a 40 ms timer. The new optional Qt Quick surface occupies only the
existing input-transparent exterior canvas. Chat controls and interior smoke
remain QWidget/QPainter. The same shader and field equations run through Qt RHI:
Metal on the tested Mac, OpenGL on the tested Linux desktop. Fine strands resolve
at physical framebuffer resolution; broad pointer transport retains its bounded
CPU grid. Colour mixing is premultiplied. The prior CPU renderer remains a fallback
for unavailable/failed graphics, offscreen tests and explicit
`AUGMENTOR_PLASMA_RENDERER=cpu`.

The shader package is compiled with Qt 6.8.2 qsb. The adjacent build record contains
its exact command and source/output hashes; the common build rejects stale bytes.
Mac packaging retains only the reviewed Widgets + Qml/Quick/QuickWidgets/OpenGL
closure and base imports. It removes optional QML modules, Designer and compiler
tools. Linux declares its Quick bindings/imports as system dependencies. Existing
Qt declarative source notices remain required. Qt's documentation informs the
implementation: [physical image density](https://doc.qt.io/qt-6.8/highdpi.html),
[transparent QQuickWidget and its offscreen render pass](https://doc.qt.io/qt-6.8/qquickwidget.html),
[portable shader packages and premultiplied alpha](https://doc.qt.io/qt-6/qml-qtquick-shadereffect.html).

## Evidence before packaging

- 516 native tests pass on Linux in isolated PySide6 6.8.2.1 (three environment
  skips); 182 Node tests and TypeScript check/build pass. The subsequent draft
  guard passes the 28-test window suite.
- The 32 GB Mac's real Cocoa/Metal fixture runs sustained animation, synthetic
  pointer transport, resizing, composer input, effect switching and idle shutdown.
  On its actual 1× BenQ display, CPU preparation median is about 10.3 ms; the
  six-second fixture observes about 50 Qt Quick render events per second.
  The trimmed runtime independently passes the same check.
- A synthetic 2× scale on that display passes with native-sized buffers and about
  10.4 ms median CPU preparation. This is not physical Retina qualification.
- Linux OpenGL passes the same fixture at its actual 1.6458× density, about 7.2 ms
  median preparation. Render events are not a physical refresh-rate measurement.
- Captures are the fixture's own Qt framebuffer/window, not screenshots of the
  owner's live conversation. Remote whole-display capture is denied by macOS;
  no privacy permissions were changed. Subjective appearance acceptance, physical
  keyboard/pointer actions and long-duration power measurements are distinct.

## Deployment gate

At this document's creation, no new candidate is installed. Required follow-up:
clean packaged build/inventory/signature checks, packaged native shortcut and chat
qualification, safe activation, exact installed read-back, then removal of obsolete
0.2.8 preview apps and stale native-host references. Preserve personal state and
one rollback archive outside application discovery. Report installed evidence here;
source tests alone must not be described as an installed fix.
