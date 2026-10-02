<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Linux desktop control preview

Pi, DSH and opt-in Codex development source use the same per-user desktop executor. It captures a consented screen
and can click, send a short key chord or type up to 256 ASCII characters into an
accessible focused control. DSH and Codex personal Browser chats can use this executor; the Pi Browser role
retains its separate tool scope.

The current target is Debian 13, KDE Plasma Wayland, one active monitor and a
model configured for image input. The desktop package supplies the capture/input
dependencies. The Augmentor window and independent Stop control use XWayland;
the tested target application, Kate, uses native Wayland. Other desktops,
multiple monitors, password fields and non-ASCII typing are not supported.

Codex setup first requires an explicit successful **Check image response**, then
a new conversation. Its consent, target-token, durable-call and cleanup behavior
and actual disposable-VM evidence are described in the
[Codex desktop checkpoint](CODEX-INTEGRATION.md#consented-desktop-tools-and-plasma-vm-evidence).
This is development source; Codex packaging, macOS/device and complete product
qualification remain separate gates.

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

Validation on current main base `d91c520`: five input regression tests exercise
actual injected handlers, including framework-owned value tracking and stale
observations; all 70 Browser cases and nine browser-policy/desktop-capability/
Codex-instruction cases pass. All 480 root cases (478 passed, two opt-in skips), TypeScript checks/build and six DSH composition
checks pass. A real Chromium-based in-app-browser fixture ran the actual handler
against React 18 controlled input/textarea fields: their rendered saved state
updated and a read-only field stayed unchanged. This is synthetic application
evidence, not a live Google Forms acceptance claim.

The changes apply to the shared extension on Linux and macOS. Backend capability
checks retain Linux single-monitor/ASCII restrictions, Mac helper and consent
requirements, and unavailable Windows GUI input. No new universal desktop backend
or permission bypass is introduced. Ordinary GUI execution continues through the
existing supported desktop tools; browser DOM input does not require a vision
model, while screenshots/desktop observations do.

Installed Linux adoption uses a separately staged copy of the selected 0.2.11
artifact with only these prompt patches. The running DSH identity adapter owns
its own immutable artifact reference; change that reference to the staged copy
while preserving existing identity snapshots, then reload only while no task is
running. The unpacked extension upgrade retains its installed version/identity
and all unrelated code, with a complete directory backup before replacement.
The loaded extension must be reloaded before its cached executor adopts changes.
Public source is 0.2.13; do not copy that full extension over a 0.2.11 companion.
Source publication, installed selection and running adoption are separate checks.

### Installed Linux checkpoint

Implementation `dffa45c` is pushed in PR #31. Mixed release
`20261002-224825-07392208` is staged and selected through `augmentor-update`,
artifact SHA-256
`6394c68a74b45ba1f3a2acdb416594e9aca60a108f76f14f17b3938730ff2abc`,
over prior artifact
`ac681aadeea466f7ce280f5641e8c89ba01e216a299702de3f1de134886240b9`.
Only persona/recovery configuration changed in this native artifact; installed
0.2.11 UI/runtime/speech contracts are retained.

Both DSH personal-preset identity references point to the new immutable release;
other entries and saved soul snapshots were preserved, with private backups and
updated preset ownership hashes. Before the controlled backend restart, the
authenticated session list showed every listed chat idle. Afterwards, the model
catalog returned seven provider groups, and primary/mobile reported online,
model-ready, voice available and no restore error. An isolated invocation of
the actual installed identity adapter verified that the new capability guidance
is appended to an existing historical persona without rewriting its snapshot.
No model-obedience claim follows from this composition proof.

The native windows still run `20261002-160803-407ce464`; primary has a draft.
They were not closed. This UI build difference does not prevent the separately
reloaded DSH guidance from taking effect. Normal close/reopen adopts the selected
UI root. The installed unpacked 0.2.11 extension has only `actions.mjs` replaced,
with its complete previous directory retained for rollback. Manifest/version,
extension identity and all other files match the previous install. Its loaded
service worker still requires Reload in `chrome://extensions`: this Codex chat
has in-app browser access but no connection to the user's installed Chromium.
Mac installed adoption and live Google Forms verification remain untested.
