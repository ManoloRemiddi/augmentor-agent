<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Linux desktop control preview

Pi and DSH use the same per-user desktop executor. It captures a consented screen
and can click, send a short key chord or type up to 256 ASCII characters into an
accessible focused control. The browser role has no desktop input tools.

The current target is Debian 13, KDE Plasma Wayland, one active monitor and a
model configured for image input. The desktop package supplies the capture/input
dependencies. The Augmentor window and independent Stop control use XWayland;
the tested target application, Kate, uses native Wayland. Other desktops,
multiple monitors, password fields and non-ASCII typing are not supported.

## Using it

1. Open the intended application and a harmless test document. Enable
   accessibility for that application. Configure an image-capable model in Pi,
   or declare image input in the DSH provider configuration.
2. Ask Augmentor for a bounded action. The OS opens **Remote control requested**.
   Choose **Share** yourself to allow capture and keyboard/pointer input. If the
   dialog opens behind another window, select it with Alt+Tab. Declining or
   cancelling it leaves sharing closed.
3. Keep the independent **Stop desktop control** button visible. Either that
   button or chat **Stop** closes sharing and releases held keys. A turn ending
   also releases its owned connection; five idle minutes close unused sharing.
4. Inspect the application or saved file to verify the result. Input dispatch
   alone does not prove success. After cancellation, text may be partial; an
   uncertain action must not be replayed automatically.

Each action requires a screenshot with a fresh compositor-owned window identity.
Its target token expires after 30 seconds and is consumed once, including refused
actions. The executor rejects a changed or covered target, changed monitor
geometry, inaccessible keyboard focus and another chat's ownership. These checks
reduce accidental input; they are not an operating-system sandbox.

Screenshots go to the selected model and may remain in the harness conversation
history. The executor itself writes no screenshot file and does not use the
clipboard to type. See DATA-AND-SUPPORT.md for data locations and deletion limits.

The Pi development runtime now also offers a [bounded desktop
specialist](DESKTOP-SPECIALIST.md). Its screenshots stay in a separate worker
context and private local evidence files; the coordinator receives a short
structured result. This has different retention behavior from direct desktop
tools. The native executor and its platform limitations remain the same.

## Reproducible evidence

`scripts/vm-desktop-proof.py` drives a disposable full Plasma Wayland VM. It
checks declined consent, Stop during consent, target/owner/replay refusals, actual
Kate Save As contents, and interruption of a long write through the independent
Stop button. `--scale` selects 1, 1.25 or 1.5. By default it runs the installed
executor; `--source` explicitly records candidate source staging instead.

`scripts/vm-desktop-engines-proof.py` uses actual Pi and DSH SDK tools with a
deterministic HTTP model. A private SSH socket forwards only desktop operations
to that VM, while host desktop autostart is disabled. It verifies actual image
bytes reaching the model, exact saved-file text and cancellation. The model
fixture supplies known coordinates; this is not a visual-reasoning benchmark.

The exact tested candidate and scales are recorded in PRODUCTIZATION-STATUS.md.
Independent hardware/users and model quality remain beta gates. The VM uses a
consistent Nehalem CPU model: `release/vm-avx-mask-proof.c` reproduces a masked
AVX2 load fault in QEMU 10.0.11 TCG that also crashed Qt/Breeze. The test avoids
that emulator defect without changing Qt or the user's system.

## October 2: browser capability discovery and input dispatch

The local Desktop chat audit confirmed browser navigation, snapshots, clicks and
text input were available and used. The agent nevertheless handed routine form
creation back to the user and asserted a background-tab limitation without tool
evidence. Later native input dispatch acknowledgements did not establish saved
values. Private conversation content and document identifiers are excluded here.

`config/browser-recovery.md` now explicitly maps browser and Linux discovery
routes, requires checking real tool availability before claiming inability,
distinguishes screenshot visibility from DOM input, and forbids arbitrary test
text in live user documents. The persona adds ownership through completion.
These instructions do not grant tools or override OS consent. Existing identity
snapshots preserve historical persona text; the installed identity adapter reads
browser recovery separately. Adoption must update the actual adapter's referenced
immutable artifact/configuration, rather than assuming the selected UI release
also owns its running DSH plugins.

Browser input uses the native input/textarea value setter before an input event,
so an application-owned instance setter cannot prematurely update its value
tracker. Disabled, read-only and noneditable controls fail explicitly. An action
acknowledgement still requires fresh observation of the saved result; synthetic
input is not guaranteed to work in every web application.

Validation: four input regression tests exercise the actual injected handler,
including a framework-style value tracker and saved-state listener; 23 related
browser tests and the complete sidebar entrypoint passed. These are local DOM
and surface tests, not live Google Forms or unrestricted computer-control proof.
A private candidate was copied from the installed 0.2.11 extension with only the
input-handler patch. Installed extension, DSH preset references and running
conversations remain unchanged while the observed task is active. Reload and
coordinated harness adoption, followed by a harmless live browser proof, remain
required. No public release or repository push was performed.
