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
named pipes. Long Unix state paths use a separate short, owner-only socket
directory without moving settings or authentication material.
`apps/native/augmentor_linux/dictation.py` is the client shared by
native settings, the Browser native host and capture coordination. It creates
private owner-only state/authentication material and bounds messages. The Handy
child accepts correlated JSON lines through its parent's private pipes; EOF
cancels capture and exits. Uncertain mutating requests are not replayed.

Resonant Voice acquires a token before opening its microphone and releases that
exact token when capture closes. Dictation cannot record while conversation
capture owns it, and conversation capture cannot interrupt dictation. A lost
acquire acknowledgement releases its token; dead process owners are reaped.
Acquire requests also carry an admission deadline: work queued behind a slow
model change cannot reserve the microphone after the caller has timed out.
The deadline is checked by the broker and native component before admission,
then by the broker after acknowledgement; it never expires active capture.
Maintenance refuses active capture and retires an idle broker before promotion.

| Platform | Shortcut / insertion adapter | Qualification boundary |
| --- | --- | --- |
| Linux X11 | Handy/Tauri global shortcut; standard X11 clipboard/paste | Actual component, separate Qt target, synthetic audio, live theme and real close-button click passed locally under KWin/Xvfb |
| KDE Wayland | Handy/Tauri shortcut; private non-root ydotool daemon for native Wayland insertion | Staged real component enabled with a separate shortcut and verified its private `0600` input socket/disable cleanup; physical capture and clean-system acceptance remain a release gate |
| Other Linux Wayland | XDG GlobalShortcuts portal; XWayland bottom pill; private ydotool daemon | Actual private D-Bus consent/press/release/denial fixture passes; compositor-specific physical acceptance is separate |
| macOS Apple Silicon | Handy native keyboard/accessibility/clipboard adapter; hidden nested helper app | Shared source and packaging wired; GitHub native build/lifecycle and existing Mac bundle qualification must pass |
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
Mac packaging gives dictation a hidden nested app with a stable bundle identifier,
Microphone/Apple Events usage descriptions and preserved resource/library paths.
The broker launches its actual executable. Both signed Desktop and Browser
companion bundles run the copied-component lifecycle proof, preserving the
original signatures and avoiding physical microphone or model downloads.
The immutable desktop deployment copier carries `components/` into staged builds.
Mac packaging explicitly signs each component Mach-O before sealing the enclosing
bundle, verifies those signatures and writes an external inventory of the signed
bytes. The component build inventory identifies the original pre-signing bytes.

`.github/workflows/handy.yml` builds Linux x86-64, Mac ARM64 and Windows AMD64,
checks Rust formatting/Clippy and runs the actual component protocol/lifecycle
proof on each runner. Linux/Mac product packaging consumes the matching artifact
from that run. A component build alone is not a complete installer qualification.
The workflow can reuse a compiled/formatted/linted component with an exact
OS/architecture/source/build-input cache key. Intake rechecks its full inventory,
and the actual lifecycle proof still runs; no partial-key restoration is allowed.
A cached build or a diagnostic artifact from a failed lifecycle job is not
qualified. Product packaging waits for successful component jobs.
Compiler intermediates have a separate cache that can restore previous source
fingerprints. They are never accepted as a component artifact: locked compilation,
source checks, notice collection, staging and lifecycle qualification still run.
Source preparation creates its own local build repository before applying the
patch; build and staging verify the reverse patch and owned source hashes.
This prevents Git from discovering the parent Augmentor checkout and silently
skipping Handy paths when preparing an extracted supplier archive.

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
The same proof also passes through the authenticated broker (`--broker`). Broad
local regression suites pass: 616 native cases (613 pass, 3 platform/opt-in
skips), 480 Node cases (478 pass, 2 opt-in skips), and 66 Browser cases. The native
settings visual proof exposed and corrected white scroll content under a dark
label palette; model-card links now use the accent colour. Both Debian packages
build with the runtime's checked native inventory and complete notices.

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
build and running windows after promotion.

## Owner's installed adoption — 2 October 2026

Feature source `c8f67a3391570c6a24f1502a9344da12e2c07846` was adapted narrowly
over the existing installed artifact
`b72b7f883e65c7b27d0e077892a9cdbf2744d56348d132796532b3efab62a29d`, preserving
the newer embedded settings frame and matching 0.2.11 product/DSH/speech contracts.
It was staged and activated through `augmentor-update`; selected build
`20261002-141437-663e6383` has artifact SHA-256
`a47433db434bf446d8001c18182d85b8318c0e78f92fd72f14f8131f75cfd308`.
Desktop and Mobile subsequently adopted that exact build and both reported
online, voice available and no pending update. The owner authorized the final
cutover after the UI became idle.

The existing standalone Handy process exited cleanly, its autostart entry was
moved to a private migration backup and the embedded broker enabled successfully.
Status reports ready, Ctrl+Space/hold, Parakeet Q8, default microphone, ydotool
insertion, no component tray and the owner's actual current palette. Saved
component settings confirm CPU for both accelerators, bottom/minimal overlay,
five-minute unload, no always-on microphone and no automatic submission.
Standalone software/model caches/history were not uninstalled or deleted.
The separate root input service remains independently owned; Augmentor uses its
own non-root daemon/private socket instead.

This is an installed Linux adoption, not public all-platform release qualification.
The first remote runs exposed source preparation discovering Augmentor's parent
Git checkout and silently skipping the supplier patch. Those compiled/linted
artifacts were standalone Handy, not qualified embedded components. Source now
establishes an independent build root and verifies all patch/source inputs before
compilation and staging. Full startup diagnostics identified the failure; the
workflow also uses isolated software-rendered X11 testing, explicitly disables
Windows Vulkan in CMake and retains checked builds for repeat proof.
Mac/Windows installer/compositor/permission acceptance remains open until those
jobs and the product package proofs pass. No physical microphone acceptance is
claimed from virtual input tests or successful enable/status alone.

### Verified source and installed follow-up

Source `f60148b8ccb7bfac49c4a8c02e7bd2c20978b513` fixes parent-checkout patch
skipping and adds deadline-fenced microphone admission. Fresh supplier preparation
inside a parent Git repository passes the regression fixture and the complete
actual reverse-patch/owned-source checks. Existing Linux runtime source already
contained the correct patch; its verified binaries were re-staged with current
build-input provenance. The authenticated virtual-microphone recording/paste
proof passes again. All 614 native cases pass (611 pass, 3 expected skips).

Both 0.2.13 Debian packages build from that clean source. The runtime package
SHA-256 is `53f1275b4b510c43b78f88b4bcad2697df747bc84e740402a09652374ebd7d3c`;
the Desktop package is `8a51cc02a21cea567ed33e3c0fcf8a99481eae035805a18b31f0bbf4c6e8d4b3`.
The extracted actual component passes lifecycle, theme, revision rejection,
exact-token ownership, no tray and parent EOF cleanup without microphone access.

The installed follow-up is separately composed over the preceding adoption,
retaining its newer UI and matching 0.2.11 dependencies. Managed stage/activation
selected `20261002-154843-0eedcd1a`, artifact
`eee72c10f9ad9268dc66c69de819536f033e3b6edd30b27366880526f8f5a478`.
Both idle windows closed through acknowledged maintenance and reopened through
the selected launcher; Desktop and Mobile now report that exact root, online,
voice available and no pending update. The idle broker was retired before
selection and restarted from the selected root. Ready/enabled Ctrl+Space,
CPU/current owner palette/no Handy tray and absent standalone autostart were
rechecked. Source qualification remains distinct from this mixed installed
0.2.11 artifact and physical microphone acceptance.

### Hosted source-preparation and voice checkpoint

At source `f60148b`, [Mac component lifecycle](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37015394290/job/110864893055)
passes the actual compiled embedded protocol, no-tray, theme, settings revision,
ownership and EOF proof. The Mac 14/26 product jobs then expose long Unix
socket names in private voice fixtures; a short owner-only endpoint fixes this
without changing audio/provider configuration. Actual long-path broker startup
and microphone lease round-trip pass in a regression fixture. Windows preparation
exposes Git's CRLF checkout against LF archive context; the patch stream is now
normalized and the independent source repository disables automatic conversion.
The regression fixture combines a nested parent checkout, Windows automatic
conversion and a CRLF patch. Native admission also rejects expired tokens before
reserving the microphone. Final hosted component/product proofs must qualify
these follow-up inputs before their complete platform artifacts are claimed.

### Current installed admission build

Source `85034acb8900082873a6e5b53117e8c6e43444d5` adds native token expiry,
Windows patch conversion and short private Unix endpoints. Local native release
compilation, formatting and Clippy pass; all 615 native cases pass (612 pass,
3 expected skips), including real long-path broker/lease startup. All seven
Codex voice integration cases pass, including native and Browser paths. The
actual component rejects expired native admission; the authenticated synthetic
recording/paste/theme/focus/cancel proof passes again.

Clean-source Debian runtime SHA-256 is
`c4c50fa9b059263fea40d28ba918e066ccb313f1d3489be3917b757dc7b0b344`;
Desktop SHA-256 is `7e3c96751da681775e13a73ce5f2b026f1542d256ffc299d3d7856f3a63f75f0`.
The separately composed compatible installed build is
`20261002-160803-407ce464`, artifact
`ac681aadeea466f7ce280f5641e8c89ba01e216a299702de3f1de134886240b9`.
Both Desktop and Mobile adopted this root through idle acknowledged maintenance,
with the original installed 0.2.11 UI/DSH/speech contracts retained. Both report
online, voice available and no pending update. Ctrl+Space remains enabled,
ready, CPU, current palette, no Handy tray, and standalone autostart is absent.

The subsequent platform-only follow-up explicitly decodes UTF-8 patch context
on Windows and gives the Mac microphone helper its own hidden, signed app bundle.
Its fixture verifies permission identity and unchanged executable/resource/
library/notice bytes; 131 Mac adapter cases pass locally (2 native-tool skips).
Real signed-bundle lifecycle and remaining hosted checks are separate evidence.

The final platform follow-up passes all 616 shared native cases locally (613 pass,
3 expected skips) and the real copied-component lifecycle proof with current
build-input inventory. Compiler caches accelerate source corrections but never
replace source validation or artifact qualification. Public application source
and the original canonical checkout's unrelated working files remain separate;
Mac-only packaging work does not change the installed Linux UI or model setup.
