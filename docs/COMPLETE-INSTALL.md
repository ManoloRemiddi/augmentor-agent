<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Install Desktop, Browser and their shared components

This complete preview targets **Debian 13, x86-64**. Desktop-control acceptance
is scoped to KDE Plasma Wayland. macOS is the next compatibility phase; this
Linux installer does not establish macOS or Fedora feature parity.

The active project is [augmentor-agent](https://github.com/ManoloRemiddi/augmentor-agent).
The current downloadable preview is the previously published **0.2.10 complete preview**:
[download the archive](https://github.com/ManoloRemiddi/augmentor-agent-app/releases/download/v0.2.10-complete-preview.1/augmentor-0.2.10-complete-preview.1.tar.gz),
[verify SHA256SUMS](https://github.com/ManoloRemiddi/augmentor-agent-app/releases/download/v0.2.10-complete-preview.1/SHA256SUMS),
and read its [release record](https://github.com/ManoloRemiddi/augmentor-agent-app/releases/tag/v0.2.10-complete-preview.1).
These immutable downloads remain in the archived distribution repository and keep
their shipped licenses. Future releases belong in the active repository.
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

The installer requests administrator access through `sudo apt` for Debian
packages. DSH, model settings, tokens, plugins and user services are then installed
as your normal user. Internet access is needed for the pinned DSH dependency tree
and Python packages. Do not run the whole script as root.

## Included and configured

- Matching Augmentor Desktop and Chromium Browser 0.2.10 surfaces and companion.
- Pinned DSH 0.1.5-rc.1, with its own fresh data directory and a managed user service.
- Product, desktop-tools, browser-tools, prompt-library, dual-memory and execution-recovery adapters.
  Execution recovery is enabled once in both Augmentor presets; no separate plugin installation is needed.
  It bounds empty/truncated-response recovery, preserves Stop and user handoffs, and prevents
  exact duplicate changes during recovery. It does not certify that a model answer is correct.
- Model Picker Augmented 1.1.2, Adaptive Reasoning 0.2.3 and Resonant Voice 0.1.16.
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
source snapshots. Public snapshots exclude repository histories, local outputs,
configuration, credentials, conversations, memory databases, model weights and
microphone recordings. Downloadable synthetic voice references have the separate
speech-model terms described above.
