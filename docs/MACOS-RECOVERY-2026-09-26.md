<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Mac recovery and shared rendering qualification

The newer [September 27 appearance correction](MACOS-APPEARANCE-2026-09-27.md)
supersedes this record's installed build: `7ff6712` runs at 110% on the 32 GB Mac.
It removes the native effect-window shadow and adds the shared App size slider.

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

## Installed and verified

The clean candidate built from `c3a7fabf4466b41940548a30d059f308af9819c1` is
installed at `/Applications/Augmentor Agent Desktop.app` on the 32 GB M4 Mac.
It contains all integrated source, with no source overlays. Product version is
0.2.12; this is a private qualification candidate, not a replacement public release.

- ZIP SHA-256: `89655e2f4afbbdebacbdca73cb6c42ccd546ab4fcfcbdba4851f1c40fc26a2dd`.
- Application inventory SHA-256:
  `b439032fb23fafce118ceea4f18651ac0751875721d4f1f5fad1ad004cd628b7`.
- The archive's 585 application entries, retained Qt framework dependencies,
  native launchers and strict ad-hoc signature passed verification. Signature
  verification also passed after graphical qualification and installation.
- 519 native tests (three environment skips) pass on Linux. The real X11/KWin
  two-process test passes with OpenGL, including pinning/workspaces, stacking,
  desktop edges, compact mode, hide/show and minimize/restore.
- The final packaged Metal framebuffer, synthetic pointer transport, composer
  input, eight resize handles, compact restoration and exact menu placement pass
  on the 32 GB Mac. CPU field preparation is about 10.2 ms. Only isolated runs
  are suitable for frame-rate comparisons; simultaneous GUI fixtures interfere
  with scheduling/focus and do not establish a performance result.
- Real Carbon registrations, both independent native processes, targeted hide/show,
  conflict refusal, unsent-draft preservation and service restart/restoration pass.
  The test driver now allows Cocoa startup focus to settle and explicitly ends
  preview processes after their accepted close; preview windows intentionally
  lack the live controller's application-exit behavior. Normal native quitting
  and reopening were separately verified by the live chat test. The driver
  correction follows the binary ref above; no installed source was patched.
- The final artifact passes managed engine-first setup, plugin provisioning,
  authenticated browser handoff, deterministic chat and conversation restoration
  after owned launchd/DSH restart. These are isolated model fixtures.
- **Actual native-process live evidence:** Send completed a real DeepSeek-V41-Flash
  reply; reopening restored that same test conversation and Enter completed another.
  After installation, the canonical native launcher restored it and completed a
  third real reply. The owner's primary conversation was not used for these tests.
  Each qualification window then closed normally; the primary reopened normally
  with test control disabled, online/model-ready and without connection errors.

The installer paused the exact owned shortcut service, gracefully closed idle
windows, drained the owned DSH/shared helpers, and restored both login services.
Private DSH settings/connection digests and all three conversation metadata records
matched before/after installation (two existing conversations plus our named test).
The primary Fn+Space binding is unchanged and active under shortcut protocol 2.
Secondary remains unassigned until saved in Settings, as required by the audit.

## Clean application discovery

The target Mac contained the old 0.2.8 Desktop and Browser Companion previews,
seven orphan helpers launched from those bundles, four earlier candidate apps,
old rollback folders, and disposable test apps in the Trash. Merely hiding build
folders had not removed their LaunchServices registrations.

Cleanup stopped those seven verified legacy helpers and the old development
prompt-library helper, migrated the two existing
browser native-host manifests to the canonical desktop (same extension ID), removed
32 obsolete bundles/backups/candidates plus nine disposable uninstall-test bundles,
unregistered stale paths, and ejected the old mounted installer. One verified
rollback ZIP is retained in the private non-indexed cache; user data was not removed.
The extension migration is host registration evidence, not a new end-to-end browser
qualification. Temporary build apps created on the other Mac are also retired;
its working personal installation is unchanged.

Final LaunchServices and Spotlight read-back contain **only the canonical Augmentor app**;
there is **one Dock tile** and one app in the system/user Applications directories.
Launching by bundle identifier reopens the existing canonical process rather than
an old preview. The process remains online/model-ready, with no connection or
conversation-restoration error.

## CI and remaining boundaries

At binary source `c3a7fab`, Mac 14/26, Debian (including GPU workspace checks), Home,
and installed-package lifecycle CI passed. The browser package job exposed an
unrelated verification race: Chromium creates `DevToolsActivePort` before writing
it. The proof now waits for complete port/path contents and detects early browser
exit. This is a test-driver correction, not a browser product change; the final
validation at `ba09317` passed after this correction:
[Mac 14/26](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36273381199)
and [Debian, Browser, Home and installed-package lifecycle](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36273381242).
The local Chromium/native-host/Pi proof also passed navigation, snapshot, typing,
clicking, clipboard, reconnect without replay, branch/edit behavior, shared prompts
and private support export. Documentation-only follow-ups do not change the tested
application or installed artifact.

Whole-desktop capture and physical keyboard/microphone acceptance remain outside
this qualification; macOS permissions were not changed. The fine-resolution Metal
implementation is verified, but subjective flare appearance remains the owner's
assessment. Startup focus races should be qualified separately from steady-state
shortcut toggling before broad release.

The public website still serves `v0.2.12-macos-preview.1`; its published bytes were
not replaced. A new numbered preview, corresponding sources/notices and website
guide update are a separate publication step. Automatic updates, full removal and
Apple distribution signing/notarization remain preview limitations. Linux's
installed selection and Sponsor/workspace-embedding PR #12 were not changed.
