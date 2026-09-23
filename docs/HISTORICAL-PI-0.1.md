<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

Historical instructions, superseded by the current README and Debian package guide.

# Augmentor Agent for Linux — powered by Pi · 0.1.0

The native Augmentor Qt interface, now running on Pi instead of DeepSeek Harness. It uses the pinned Pi coding-agent SDK and agent-core `0.85.1`, with the existing Python/PyQt6 presentation and desktop helpers.

Verified target: MX Linux 25.2, KDE Plasma, Wayland with the app displayed through XWayland. This is an initial native release; the browser-extension successor remains separate and deferred.

## Use

Launch **Augmentor Agent · Pi** from the application menu, or run:

```sh
./scripts/augmentor-linux
```

The installer attempts **Super+Alt+Space** for show/hide and preserves existing bindings. Use More → Settings to change it. Ctrl+Shift+Space switches between the conversation and circular activity views. Pin follows all desktops. The app retains its appearance, placement and draft when hidden.

- Choose a model, type, and press Enter. Shift+Enter inserts a newline. Stop cancels active and queued work. No different model is silently substituted.
- New chat, Save/Unsave, History and double-click-to-rename keep their existing UI positions. Pi owns conversation persistence; saved-chat markers are Augmentor metadata.
- More → Prompt library creates, edits, renames and deletes reusable prompts. Use **Insert clipboard** in the prompt editor to add `[clipboard]` at the cursor. When you choose a saved `/prompt`, each `[clipboard]` is replaced with the current plain-text clipboard, ready to review before sending. Copy new text and reuse the prompt without editing the template. An empty or non-text clipboard keeps the draft unchanged and shows a message. Type `/` to insert a prompt without sending. Conflicting edits are rejected so another client's changes are preserved.
- More → Models & providers edits Pi model configuration. Right-click a model in the searchable picker to pin/unpin it. Models needing credentials are labeled.
- More → Approval mode sets the default for new chats: read-only tools, ask before actions, or automatic full access. Routine clock and system queries run without approval; changes and unrecognised commands still ask in the middle mode. Existing chats retain their policy. These are tool permissions, not an OS sandbox.
- Messages have **Copy** actions. Completed assistant replies also offer **Branch in new chat**, carrying Pi context through that reply. The latest user input offers **Edit**: revise it in the composer, then send to create a revised conversation from the context before that input. **Cancel** restores your previous draft. Originals remain in History; branch/edit actions are available when the chat is idle.
- Hiding the window keeps the runtime and task alive. Reopening restores the last session. A connection loss does not resend the prompt; a runtime crash is recorded as interrupted with potentially unknown action outcomes.

## Build and install

Requirements: Node >=22.19, npm, Python 3/PyQt6, Python GI/AT-SPI, and a desktop session. Python YAML is needed only for legacy settings import. KDE DBus tools support shortcut/pinning integration; Chromium is needed for visible browser opening. `scripts/doctor.py` reports actual dependencies and capabilities.

```sh
npm ci --ignore-scripts
npm run build
python3 scripts/doctor.py
python3 scripts/setup-local.py                 # verified local llama.cpp endpoint on port 8080
python3 scripts/install.py
```

`setup-local.py` discovers the advertised model from the local endpoint, preserves existing Pi configuration, and never reads DSH configuration. Its initial context/token settings match the tested MX Qwen setup; adjust Models & providers for another server. Skip this step when configuring another provider directly.

The installer copies a built release to `$XDG_DATA_HOME/augmentor-pi/app` (normally `~/.local/share/augmentor-pi/app`) and registers `com.augmentor.LinuxPi.desktop`. It does not replace the DSH app or its shortcut. The installed launcher pins the detected Node executable, so it works from a minimal desktop PATH.

For an archive release, extract it and run `python3 scripts/install.py`; compiled code is included, and the installer installs the locked production dependencies if needed. `--no-desktop` supports an independent runtime installation. `--prefix PATH` changes the application directory.

## State and migration

Configuration: `$XDG_CONFIG_HOME/augmentor-pi/`. Private runtime/session state and the socket: `$XDG_STATE_HOME/augmentor-pi/`. Standard XDG defaults apply. `AUGMENTOR_PI_CONFIG`, `AUGMENTOR_PI_STATE`, `AUGMENTOR_PI_SOCKET` and `AUGMENTOR_PI_WORKSPACE` support isolated deployments and tests.

Pi stores credentials/models/resources under `agent/` in the config directory. Clients never receive provider credentials from the runtime. The model editor reads the local user-owned configuration file. Pi conversation files and the private display/recovery journal retain conversation and tool content; full desktop observations are therefore part of session retention. Local endpoint labeling does not claim whole-process network isolation.

Explicitly copy reusable legacy data, preserving source files and existing Pi content:

```sh
python3 scripts/import-legacy.py --appearance ~/.config/augmentor-linux/appearance.json --settings ~/.dsh/settings.yaml
# Or import a prompt-library JSON export:
python3 scripts/import-legacy.py --prompts /path/to/prompts.json
```

Only appearance, model pins and prompt text are copied. Provider credentials, DSH sessions and DSH workspace IDs are not imported. The original DSH application remains available for old conversations.

## Pi resources and runtime

The host uses Pi's public SDK, model runtime, session manager, built-in tools and resource loader. There is one coding-agent session/agent loop per open conversation. The Node host can run independently of Qt:

```sh
npm start
```

To load additional Pi packages/extensions or skills, copy `config/resources.example.json` to the Augmentor config directory as `resources.json`, then add explicit package sources/paths and skill paths. Use exact package versions or commit refs. New sessions load these through Pi's resource loader; unrelated global/project extensions are not automatically imported. The configured code runs as the local user. Terminal-only extension components are unsupported; select, input, editor and confirmation dialogs use the native UI.

The runtime and versioned `augmentor-pi/1` client protocol live in this repository for future browser use. `AUGMENTOR_PI_LINUX_TOOLS=0` disables the built-in Linux package when running a headless host for another surface.

## Update, removal and verification

Build the new checkout/release and rerun its installer while Pi tasks are idle. One previous application directory is retained for rollback. Settings and conversations remain in separate directories. Quit the native UI before updating; relaunch it afterward to use the new Python code.

Run the installed `scripts/uninstall.py` to remove the default user installation and launcher, preserving all user data. For a custom prefix, remove that explicitly selected application directory after stopping its runtime; the uninstall command deliberately does not delete arbitrary source/custom directories.

```sh
npm run check
npm test
npm run test:native
node scripts/pi-spike.mjs
python3 scripts/live-acceptance.py
python3 scripts/desktop-acceptance.py
python3 scripts/ui-recovery-proof.py
npm run package
python3 scripts/install-proof.py
```

The live scripts use the running local Qwen endpoint. The desktop check opens one `https://example.com/` tab in Chromium. Deterministic runtime tests use a local fake model endpoint and the real Pi SDK; native tests use Qt offscreen. See [verification evidence](docs/VERIFICATION.md), [architecture](docs/ARCHITECTURE.md), [protocol](docs/PROTOCOL.md), and [source provenance](docs/SOURCES.md).

Current capabilities: native chat, models, history/save/rename, prompt editing, approvals/questions, resilient connections, read-only Linux profiling/AT-SPI observations and visible Chromium dispatch. Generic desktop input, portal screen capture, dedicated OS-setting adapters, automatic updates, broad Linux certification and ResonantOS integration remain future work. Dispatch is not proof of browser page loading.

License: MIT. Original Augmentor attribution is retained.
