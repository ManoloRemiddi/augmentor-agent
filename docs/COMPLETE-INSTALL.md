<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

Arch/Leap remain runtime candidates, with a new [pinned system Python/Qt inventory](LINUX-SYSTEM-QT-STACK.md).
Their [full native application packages and installed lifecycle](LINUX-SYSTEM-QT-PACKAGES.md)
now have private container acceptance, including cold Node admission. Complete
target installer adapters are implemented, with fresh matching complete bundle
execution and real desktop acceptance still open; these candidates are
not downloadable compatibility releases.

# Install Desktop, Browser and their shared components

The published complete preview targets **Debian 13, x86-64**. Desktop-control
acceptance is scoped to KDE Plasma Wayland. The
[Linux distribution rollout](LINUX-DISTRO-ROLLOUT.md) adds separate Ubuntu 26.04
and Fedora 43/44 candidate bundles; their package adapters do not establish full
desktop compatibility. Ubuntu 24.04 now has a separate private qualification
candidate with a verified managed Qt/Python runtime. Its fresh container package
and complete proofs pass; desktop and native-library release gates are tracked in
the rollout. Mint remains separate.
macOS uses its own matched release artifacts and qualification.

The active project is [augmentor-agent](https://github.com/ManoloRemiddi/augmentor-agent).
The current downloadable preview is the **0.2.13 browser reliability preview**:
[download the archive](https://github.com/ManoloRemiddi/augmentor-agent/releases/download/v0.2.13-complete-preview.1/augmentor-0.2.13-complete-preview.1.tar.gz),
[verify SHA256SUMS](https://github.com/ManoloRemiddi/augmentor-agent/releases/download/v0.2.13-complete-preview.1/SHA256SUMS),
and read its [release record](https://github.com/ManoloRemiddi/augmentor-agent/releases/tag/v0.2.13-complete-preview.1).
This release fixes the WebSocket receiver vulnerability. See the
[flare correction and upgrade guidance](RELEASE-0.2.13.md).
Extract the verified archive and open a terminal in its folder:

```sh
./install.sh
```

The script verifies every supplied file, then asks for your model's
OpenAI-compatible API URL and exact model ID. Enter your own API key when asked;
leave it empty for an unauthenticated local model. The key is entered privately
and stored only on your computer. For provider-specific APIs or advanced model
capabilities, use DSH Settings after this basic text-model setup. This wizard does
not download or select a chat model for you. The default context limit is 32,768;
pass `--context` with your model's supported limit if different.

For a newly assembled candidate, `./install.sh --plan` verifies the supplied files
and prints its system package/dependency command without prompting or writing
installation state. Use a bundle whose target matches your exact distribution,
version and architecture; Debian packages inside an Ubuntu candidate retain their
original build provenance. The older downloadable preview predates this plan mode.

The installer requests administrator access through `sudo apt` for Debian/Ubuntu
or `sudo dnf` for Fedora. DSH, model settings, tokens, plugins and user services are then installed
as your normal user. Internet access is needed for the pinned DSH dependency tree
and Python packages. Do not run the whole script as root.

New candidates verify the installed payload's clean source revision and product
version against the complete bundle before creating a private DSH runtime or
writing model credentials. Package managers may keep an older same-version
payload; a mismatch stops setup with package/update guidance. An already completed
installation keeps its repeat-run receipt and preservation behavior.

The Ubuntu 24.04 candidate requires its exact seven-wheel runtime contract in
both package and complete manifests. Its package carries a verified offline
wheel cache; setup creates the immutable environment as the ordinary user before
configuring DSH. Repeating completed setup verifies that environment without
repairing it. The package pre-install hook refuses other distro versions and
architectures. A Noble payload cannot be relabeled as a Fedora or system-Qt
complete bundle. This candidate is not a public compatibility release; native
binary license/source review, desktop and physical speech acceptance remain open.

The separately opt-in [Noble source-Qt candidate](LINUX-SOURCE-RUNTIME-ENTRYPOINTS.md)
adds a reviewed native payload and derivation receipt to that runtime contract.
Its system recipe supplies ICU74. Declared-runtime DSH services now enter through
the verified component wrapper before Node/speech children start. Neither this
source candidate nor its entrypoint fixture is a public compatibility release.

The complete qualification proof uses the installed runtime's verified
`environment(app, selected_python, inherited)` contract before its offscreen
preview and subsequent Node/Python workers. Source-Qt library, plugin and QML
paths come from that contract; system-Qt and legacy runtime loader behavior is
preserved. A changed runtime inventory or linked policy is refused without
falling back. The proof's separate 60-second readiness limits are unchanged.

The [Mint clean2035 checkpoint](../release/qualification/next-targets/20261003-mint2035-installed-setup-proof-loader.json)
records successful ordinary-user complete setup in a separate locked synthetic
account, with exact native packages and an installed receipt. Its unchanged
full proof then fails at direct preview launch because it omitted the source-Qt
environment. A read-only selected-runtime import using the production contract
passes. This establishes the proof correction, not a full connected-product or
desktop pass. The original account's older partial install remains preserved.
Repeating the same installed setup verifies identity without rewriting settings;
rerunning the fresh-user proof allocates new ports and cannot reuse those saved
fixture endpoints. Further acceptance requires an explicit post-install proof
using the existing synthetic endpoints, with no setup or model-setting replay.

The maintained `--owned-vm-post-install-fixture PATH` entry is restricted to the
explicit clean2035 Mint VM and ordinary UID1001 account. Its private fixture
record binds the original bundle manifest, installed receipt/source, five saved
settings hashes, initially empty workspace-store hash, and existing model/DSH
ports. Root-owned marker, exact VM/distro/root identity, private home, native
audit, immutable selected runtime and idle service/process checks precede any
model-server binding. The actual saved `dshService` remains
`augmentor-dsh.service`; writing that selection with `--no-services` does not
enable it. No configuration or installer step is replayed.

This is a one-shot qualification entry. A private exclusive run directory
records each mutating SDK request before dispatch; an existing run is preserved
and refused. Missing responses are never retried. Offscreen preview, two
run-owned fixture turns and a restart use the unchanged 60-second readiness/turn
checks. Settings and observed prior histories must be preserved, restart cannot
replay model requests, and cleanup covers only the owned test process/server.
Host-side VM identity and the older account's hashes must also be checked by the
explicit adapter. The reviewed external proof renders the installed source-Qt
preview, but its actual DSH startup misses the unchanged 60-second limit before
any SDK mutation. Native audits, five saved settings, old-account hashes, empty
workspace and owned-process cleanup all pass. This failure is retained beside
the original full-proof failure; neither establishes desktop/audio acceptance.

Preview and owned DSH children now use the verified synthetic home as their
explicit working directory. The narrowly defined `post-install-proof-cwd-v2`
fixture requires the exact initial failed journal hash, its pre-request failure
state, current idle guards and unchanged empty workspace. It preserves the old
journal and refuses any uncertain request or preexisting second-run journal.
The published `b12af5e` correction has now run once. Its preview succeeds,
but DSH again misses readiness before SDK mutations/model turns. Correct cwd,
an empty child log, CPU activity during startup and complete cleanup are
recorded separately from a successful connected-product proof. Both failed
journals remain preserved; no timeout widening or replay establishes a pass.

The clean7b6df59 source-runtime runtime/desktop packages now have actual
[ordinary-user offline installed startup evidence](LINUX-SOURCE-RUNTIME-ENTRYPOINTS.md#installed-ordinary-user-acceptance-of-clean7b6df59),
including cold Browser selection, offscreen Desktop, synthetic Qt and CPU VAD.
The source candidate still lacks complete connected-product, native-session,
graphical Browser, physical audio, upgrade and legal/release acceptance.

## Arch and Leap private installer candidates

The [native package/installer guide](LINUX-SYSTEM-QT-PACKAGES.md#complete-installer-adapters-fresh-execution-pending)
and [exact adapter checkpoint](../release/qualification/next-targets/20261003-system-qt-installer-adapters.json)
record source implementation and ordinary-user read-only outcome verification.
Matching new complete artifacts and fresh full installer/resume execution remain
required. No Arch/Leap compatibility download is published.

Candidate plans use pacman on the dated Arch snapshot and zypper on Leap16.0.
Arch's independent guard is installed and verified in its own prior transaction;
application installation follows only after its hooks and controls pass. Package
manager success alone is insufficient: both targets require matching registered
payload identity, complete application inventory, native audit and settled
maintenance before private configuration. Completed setup repeats those checks.

Leap bootstrap is explicitly Python3.13. Native npm runs under bundled Node,
with an actual engine-range check and a wrapper confined to the fresh private
installation. Base certificates and optional voice/GPU/Docker providers remain
separate per distro. Leap audio utility dependencies can add a server provider
through the solver even with no-recommends; graphical/physical audio acceptance
remains a separate gate. These source candidates preserve the approved UI and
leave owner deployments/services/models/devices unchanged.

## Included and configured

- Matching Augmentor Desktop and Chromium Browser 0.2.13 surfaces and companion.
- Pinned DSH 0.1.5-rc.1, with its own fresh data directory and a managed user service.
- Product, desktop-tools, browser-tools, prompt-library, dual-memory, context-budget and execution-recovery adapters.
  Execution recovery is enabled once in both Augmentor presets; no separate plugin installation is needed.
  It bounds empty/truncated-response recovery, preserves Stop and user handoffs, and prevents
  exact duplicate changes during recovery. It does not certify that a model answer is correct.
- Model Picker Augmented 1.1.2, Adaptive Reasoning 0.2.3 and Resonant Voice 0.1.19.
- Desktop login startup, connection recovery, consistent release selection and
  a separate second-window menu entry. On KDE, available defaults are
  **Super+Alt+Space** for the main window and **Super+Alt+Shift+Space** for the
  second window. Existing shortcuts are retained; conflicts are reported for
  selection in Augmentor Settings.
- Separate relationship/project memory code and the optional local engine setup.

Adaptive Reasoning is installed with empty routes. It preserves normal model
reasoning until you explicitly configure a supported provider/model/effort map.
This avoids applying the developer's Qwen settings to another person's model.
The public package includes the cold-history correction from 0.2.2.

Current source candidates also retain the Codex adapter, with
[Codex 0.159.2 as a separate prerequisite](CODEX-PACKAGING.md#separately-installed-runtime--october-1).
This installer sets up DSH and does not install Codex, sign in or enable
subscription eligibility. Candidate RPMs include the same native Secret Service
credential dependencies as Debian; live keyring/session qualification is separate.

The standalone Prompt Library plugin is not duplicated: the matching product
prompt adapter supplies the shared library. Wiki, Metafolder, external MCP
servers and unrelated developer utilities are optional additions, not required
for Augmentor desktop/browser/voice/memory to function.

## Finish the browser step

Chromium requires one explicit extension-loading action. The installer prints
the permanent extension directory and registers its matching native companion.
Open `chrome://extensions`, enable **Developer mode**, choose **Load unpacked**
and select that printed folder. Open Augmentor's sidebar and connect DSH using
the already configured shared connection. Use the matching extension; do not mix
this bundle with the older public Browser 0.1.32 companion.

## Local speech

The guided installer asks whether to provision speech. Acceptance applies to
Breeze's [research/non-commercial model and self-hosted output terms](https://huggingface.co/BreezeBlue/Breeze-TTS-2#license-and-responsible-use),
which are separate from [Augmentor's source license](LICENSING.md) and Resonant Voice's MIT source license.
Speech is optional; declining leaves the plugin installed for later setup.

If enabled, it builds the pinned Breeze C++ runtime, downloads and checks the
2.54 GB Q4 model, installs CPU ASR dependencies and synthetic voice references,
and enables speech services. Provide an NVIDIA GPU UUID when prompted to request
that exact GPU; Enter selects CPU, which is slower. It does not move, resize or
stop another model. GPU setup requires Vulkan and enough free memory; failure is
reported instead of silently switching devices. Whisper's pinned English ASR
model is downloaded on first use. First startup is slower than a warm session.

Use the desktop audio button for hold/release recording, slide-to-lock and the
optional hands-free mode. Actual microphone/speaker quality depends on the
machine and needs a local trial; installation checks are not acoustic acceptance.
No personal microphone recordings are distributed in the bundle.

## Dual memory

For a local numeric-loopback model endpoint, the installer can provision pinned
Hindsight 0.10.0 through Docker. It keeps relationship and project memory separate,
uses CPU embeddings/reranking and controlled processing. Extraction is paused by default;
review and start processing through the memory controls when wanted. It creates a
persistent named volume and fresh private stores; it never includes the author's
conversations or memories. The model must support memory extraction workloads.
The current guided memory path is for a local model; cloud-only users can defer
memory and configure a supported engine separately.

Docker may need administrator access on a fresh machine. Existing containers or
memory destinations that differ are refused for reviewed migration. Removal of
the application does not delete the memory volume or conversations.

## Repeatable command-line setup

```sh
./install.sh --non-interactive \
  --model-url http://127.0.0.1:8080/v1 --model YOUR_MODEL_ID \
  --api-key-env YOUR_PRIVATE_KEY_VARIABLE --context 32768
```

Add `--voice` to accept the speech terms and provision CPU voice, or
`--voice --gpu GPU-EXACT-UUID` for explicit NVIDIA placement. Add `--memory` for
local dual memory. Supply secrets using an environment variable or the private
prompt, never a command-line value or a shared installation transcript.

## Verify, recover and update

1. Open Desktop, select your model and verify one harmless response.
2. Open the second window; it should have a separate conversation and settings.
3. Load the Browser extension and verify its model list and a harmless response.
4. If enabled, try microphone/playback and check memory-engine readiness.
5. Log out/in and confirm Desktop reconnects. Use `augmentor-recover` if needed.

`augmentor-update status` distinguishes the selected release from running windows.
Future desktop updates use staged validation and atomic selection; see
[desktop deployments](DESKTOP-DEPLOYMENTS.md). A fresh installation wizard refuses
an existing Augmentor/DSH setup rather than replacing its profiles. Existing users
need the reviewed migration/update path; do not delete their data to bypass this.

The archive carries exact component/source references, SHA-256 checksums and
source snapshots with explicit coverage. For the current Voice 0.1.19 candidate,
`--source-bundle … --voice-distribution-source` reuses checked public Adaptive
0.2.3 source and preserves the exact already published Voice npm archive as
`sources/dsh-resonant-voice-0.1.19-distributed-source.tgz`. Its MIT notice and
shipped JavaScript, Python and C++ source remain intact. The manifest records
`npm-distributed-source`, archive/provenance hashes and
`fullRepositorySnapshot: false`; this package omits repository tests, lockfile,
workflows and history. The declared upstream Voice commit comes from public
release provenance and is not independently bound to the private repository
tree. This mode does not complete legal/source-kit or public-release acceptance.
See [the exact coverage](../release/dsh/voice-distributed-source.json).
The [Arch/Leap execution checkpoint](../release/qualification/next-targets/20261003-system-qt-complete-and-release-upgrade.json)
records full native and ordinary-user success for the exact clean8ad Leap bundle.
Arch's initial bundle stops at native npm's flattened semver layout. The corrected
helper first passes explicit diagnostic resume. A subsequent
[fresh cleanf85 Arch release4 bundle](../release/qualification/next-targets/20261003-arch-clean-complete-installer.json)
passes normal root native admission and complete ordinary-user setup/repeat,
actual DSH/plugins, fixture model roles and restart history without replay, with
matching bundled setup and no overlay. That container result does not qualify
graphical browser/session, boot or physical audio.
The qualification driver's `--setup-script` option records any external installer
override and its hash; that result cannot establish matching-bundle acceptance.
Public snapshots exclude repository histories, local outputs,
configuration, credentials, conversations, memory databases, model weights and
microphone recordings. Downloadable synthetic voice references have the separate
speech-model terms described above.

The isolated Mint readiness-only diagnostic later observes matching product HTTP
identity at 56.43 seconds and counts zero model/provider requests, using unchanged
installed bytes and GET only. Full adapter authentication/preset/SDK readiness is
not tested. The diagnostic retains its own failure because immediate cleanup
port binding is refused; later read-only native/settings/journal/workspace/idle
checks pass with no remaining listener. The two 60-second post-install failures
and original full-proof loader failure remain distinct and unchanged.

A subsequent one-call installed-adapter diagnostic succeeds with HTTP identity
at 60.41 seconds and authenticated full readiness at 62.94 seconds. Both product
presets are available; normal authentication and preset/catalog reads complete
in 0.81 seconds. It counts zero model/provider requests and preserves native
audits, settings, empty workspace and all three earlier journals, with idle
owned processes and no remaining listener. This establishes a startup-budget
shortfall in this run, not a public 60-second proof pass, model/history acceptance
or the cause of every earlier failure. Maintained executable bytes are unchanged.
