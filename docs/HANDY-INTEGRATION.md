<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Embedded Handy dictation

Implementation branch: `feat/handy-integration`, based on public main
`d91c52037d7bc26c82c702c25e1a779b0fca1f39`. This guide owns the implemented
contract; [the approved plan](HANDY-INTEGRATION-PLAN.md) retains its rationale.
Source, component qualification and installed promotion are separate evidence.

## User experience

Augmentor owns the tray and exposes **Voice dictation — Powered by Handy**
from Desktop settings and the Browser's existing settings panel/native bridge.
The component has no Handy tray, independent updater, autostart entry or main
settings window. Closing the primary chat hides it when the Augmentor tray is
available. Full Quit waits for dictation to stop before closing Augmentor.
Disable releases the shortcut, cancels recording, unloads the model and stops
the child and owned input helper. A Browser operation can start the common
service later; merely polling disabled settings does not open a microphone.

The initial shortcut is **Ctrl+Space**, hold to record and release to transcribe.
Users can change the shortcut, choose toggle activation, choose/download a
model, select a microphone, choose language/translation, paste/clipboard modes
and history retention. New installs start disabled until explicitly enabled;
the first selected model must be downloaded after reviewing its publisher terms.
Audio capture is explicit. Recognition uses CPU by default, leaving Augmentor's
separate Qwen/Breeze GPU placement and Resonant Voice configuration unchanged.
The English Parakeet default does not become multilingual when Language is Auto.

The bottom recording pill retains Handy's placement, waveform and close button.
Its left dot becomes Augmentor's animated circular mark, drawn using the native
VoiceButton's geometry. Background, foreground, accent, border, opacity and
animation follow explicit Augmentor appearance edits immediately, including
during capture, without activating the pill or moving focus. Opening another
window/settings panel does not overwrite that choice. Timestamped edits prevent
late delivery from replacing a newer colour selection. With animation disabled,
the mark is static; the microphone waveform continues to show incoming audio.

Settings polling preserves unfinished edits. Writes include the native revision
and child generation; another window's changes require **Reload saved settings**
before a stale draft can save. Model downloads require the explicit model-card
review action and have a cancellation control. No transcript is submitted to a
chat automatically, and no Enter key is sent by default.

## Ownership and operating systems

`services/dictation/server.py` owns one child per user/graphical session and
provides authenticated local JSON messages through Unix sockets or Windows
named pipes. `apps/native/augmentor_linux/dictation.py` is the client shared by
native settings, the Browser native host and capture coordination. It creates
private owner-only state/authentication material and bounds messages. The Handy
child accepts correlated JSON lines through its parent's private pipes; EOF
cancels capture and exits. Uncertain mutating requests are not replayed.

Resonant Voice acquires a token before opening its microphone and releases that
exact token when capture closes. Dictation cannot record while conversation
capture owns it, and conversation capture cannot interrupt dictation. A lost
acquire acknowledgement releases its token; dead process owners are reaped.
Maintenance refuses active capture and retires an idle broker before promotion.

| Platform | Shortcut / insertion adapter | Qualification boundary |
| --- | --- | --- |
| Linux X11 | Handy/Tauri global shortcut; standard X11 clipboard/paste | Actual component, separate Qt target, synthetic audio, live theme and real close-button click passed locally under KWin/Xvfb |
| KDE Wayland | Handy/Tauri shortcut; private non-root ydotool daemon for native Wayland insertion | Matches the inspected compositor; clean packaged-system/manual acceptance remains a release gate |
| Other Linux Wayland | XDG GlobalShortcuts portal; XWayland bottom pill; private ydotool daemon | Actual private D-Bus consent/press/release/denial fixture passes; compositor-specific physical acceptance is separate |
| macOS Apple Silicon | Handy native keyboard/accessibility/clipboard adapter; app-bundled component | Shared source and packaging wired; GitHub native build/lifecycle and existing Mac bundle qualification must pass |
| Windows | Handy native keyboard/insertion adapter; `.exe` component and named-pipe broker | Native component CI added; complete Windows app packaging belongs to the existing public Windows work and must converge before a supported installer is claimed |

Linux requires the existing WebKit/GTK runtime and the declared portal/Gio,
XWayland and clipboard packages. Debian installs a narrow `uinput` seat-access
rule and module configuration. The helper uses a user-owned `0600` socket;
neither root-run typing nor reading all raw keyboard devices is required.
If access is unavailable, enable fails visibly before capture starts. GNOME
requires a compositor portal supporting GlobalShortcuts and host app Registry;
accepted shortcut descriptions are displayed rather than pretending a denied
binding succeeded. The close button always cancels; global Escape requires the
upstream/native shortcut path and is not promised across portal-only compositors.
macOS still requires Microphone and Accessibility consent, and Windows still
requires the product's reviewed WebView2/VC runtime installation prerequisites.

## Pinned suppliers, models and notices

Handy is built from public `cjpais/Handy` v0.9.7 commit
`05e0aedd2906f0d82722735f930465950c476b90`, verified source archive SHA-256
`3e21340416d3c46ca4497329d5d0a17b5ef1bb12fe1f2ade35dec36fad71470b`.
`components/handy/upstream.json`, `augmentor.patch`, `embedding.rs` and
`AugmentorOverlay.tsx` are the maintained adaptation. Generated upstream source,
model caches and binaries are ignored. Changes preserve upstream notices and
do not import private Augmentor history or the owner's recordings/settings.

The build pins Rust 1.97.1, Bun 1.3.10, upstream frozen lockfiles,
transcribe-cpp 0.2.3 and official Microsoft ONNX Runtime 1.24.2. Platform archive
digests are in `components/handy/onnxruntime.json`. `tauri/custom-protocol` is
required for the release frontend; a plain development build is not distributable.
Portable CPU builds disable native CPU tuning. The packaged Silero VAD v4
resource is checked against its pinned original MIT license and resource hash.

The MIT license of Handy and its inference libraries does not license all
weights. The initial Parakeet conversion card uses CC BY 4.0 and identifies the
original NVIDIA model under NVIDIA Open Model License. Both cards are exposed
before downloading. No recognition weights are bundled into the installer.
The exact default catalog snapshot is
`7e948f21b7bdbac698d3318db9d350f1096f3b6c`; its Q8 model checksum is
`4b50b6dd862bf6e346929aaf4f5eaacec003bfa3f56462d6c874b41ef2f38795`.
Other models retain their publisher terms; there is no blanket permissive-model
claim. Consult [Handy MIT](https://github.com/cjpais/Handy/blob/v0.9.7/LICENSE),
[ONNX Runtime MIT](https://github.com/microsoft/onnxruntime/blob/v1.24.2/LICENSE),
[the conversion card](https://huggingface.co/handy-computer/parakeet-unified-en-0.6b-gguf)
and [the original model card](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3).

The separate Linux ydotool executable is AGPL-3.0-only, rather than MIT.
The package includes its exact unmodified source archive, license and build
recipe alongside its executable and documented socket interface. Rust notices,
source archives where required, frontend runtime dependency notices, Rust's
standard-library attribution, ONNX notices and Silero attribution accompany
the runtime under `notices/`, also copied into the app's license directory.
Missing/unreviewed notices stop packaging. Third-party branding remains limited
to attribution and the Handy settings label; the feature does not imply endorsement.

## Build and reproducible evidence

Run `python scripts/build-handy.py` on the target OS with the pinned toolchain
and native build dependencies. For Linux, `components/handy/build-linux.Dockerfile`
defines the native compiler dependencies. Build jobs default to two. The output
is `components/handy/runtime`; `scripts/stage-handy.py` rejects mismatched OS,
source pins, patch/owned-source hashes, build inputs or altered file inventories.
Existing Debian, Mac and release packagers require and include this component.
The immutable desktop deployment copier carries `components/` into staged builds.

`.github/workflows/handy.yml` builds Linux x86-64, Mac ARM64 and Windows AMD64,
checks Rust formatting/Clippy and runs the actual component protocol/lifecycle
proof on each runner. Linux/Mac product packaging consumes the matching artifact
from that run. A component build alone is not a complete installer qualification.

Local verification on 2 October 2026 includes actual release compilation,
Clippy, TypeScript frontend/build checks, the broker authentication/revision/theme/
microphone tests, native settings draft/quit tests, Browser form draft/license tests,
and an isolated real D-Bus portal fixture. The real CPU recognition proof used
cached verified Parakeet weights with generated speech. `scripts/proof-handy.py`
uses only an owned virtual microphone in a private X11 session and verifies:
default Ctrl+Space, editable shortcut, exactly one transcript inserted into a
separate QTextEdit, live light/dark theme without focus changes, cancellation
through the actual close button, microphone exclusion, disable, no Handy tray
and parent-exit cleanup. It does not listen to the physical microphone.

```sh
PYTHONPATH=apps/native QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v
PYTHONPATH=. AUGMENTOR_PORTAL_PROOF=1 dbus-run-session -- python3 -m unittest discover -s tests -p test_dictation_portal.py -v
node --test apps/browser/test/*.test.mjs
xvfb-run -a python3 scripts/proof-handy-component.py
```

The recording proof additionally requires KWin/X11, ffmpeg/espeak-ng and an
owned PulseAudio null sink; its source contains the exact invocation. Keep proof
outputs/screenshots outside Git. Tests over virtual microphones and mock consent
must not be described as physical device or every-compositor acceptance.

## Installation and reversible migration

New installs obtain the matching native component through Augmentor's installer,
then enable/download within Augmentor. Existing standalone Handy is independently
owned: do not uninstall it, delete its cache/history or automatically read its
provider keys. A reviewed cutover may reuse a verified compatible cached model
and selected non-secret preferences, preserving originals and backups. Stop its
shortcut/autostart owner only after the replacement has passed acceptance.

Installed promotion must use a separate artifact and `augmentor-update`. Preserve
the selected product version and matching DSH/speech dependencies, plus newer
settings/layout work on this owner's machine; do not replace those files with an
older feature-base version. Record the exact source ref, artifact digest, selected
build and running windows after promotion. At this guide's initial checkpoint,
the integration remains a source/build candidate: no installed feature, standalone
Handy cutover, physical microphone test or public all-platform release is claimed.
