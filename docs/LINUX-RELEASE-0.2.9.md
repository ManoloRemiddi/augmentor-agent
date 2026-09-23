<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Augmentor Agent Desktop 0.2.9 — Linux release candidate

The application displays **Augmentor Agent**. Augmentor Agent Desktop is the
project/product name. Version 0.2.9 gives the corrected name and header layout a
unique package version, replacing the repeated 0.2.8 development candidates.
Publication remains pending final artifact acceptance and public hosting.

## Supported first-release target

- Debian 13, amd64; desktop-control evidence is scoped to KDE Plasma Wayland.
- DeepSeek Harness (DSH) 0.1.5-rc.1, installed separately with a configured model.
- Chromium for the optional browser extension. Other browser/distribution
  combinations are not certified by this release.
- Model Picker Augmented 1.1.2 provides model curation. Other DSH plugins and
  external MCP servers remain separate services with their own requirements.
- Optional Hindsight memory is verified with 0.9.2 and must be configured explicitly.

macOS and Windows follow later. Pi support/qualification and additional Pi
extensions are deferred. Existing Pi data and code are retained. OpenCode is
retired; no existing conversations are automatically converted or replayed.

## Download contents

- `augmentor-runtime_0.2.9_amd64.deb`: application code, shared services and browser companion.
- `augmentor-desktop_0.2.9_amd64.deb`: desktop launcher and system dependencies.
- `augmentor-browser-0.2.9.zip`: optional unpacked Chromium extension.
- Exact source archive, SHA256SUMS, artifact manifests and release notes.

The desktop requires both Debian packages. Browser-only use requires the runtime
package and extension. DSH, third-party plugins, model files and credentials are
not included in the download. Install dependencies from configured Debian
repositories; installation does not require npm to build Augmentor.

## Fresh installation

Verify SHA256SUMS from the published release, then run from the download folder:

```sh
sudo apt install ./augmentor-runtime_0.2.9_amd64.deb ./augmentor-desktop_0.2.9_amd64.deb
```

Start Augmentor Agent from the application menu. Connect the supported running
DSH profile in Settings, using its current local launch URL when authentication
is requested. Review the detected installation before adding the integration.
After installing the integration, restart DSH and check/save the connection.
Use the same DSH profile and data directory for both products. Preserve launch
tokens and provider credentials as private data.

For the browser, extract the complete ZIP to a permanent directory and load it
with Chromium's **Load unpacked** control. It is not a browser-store installation.
Use the matching 0.2.9 companion and ZIP. See [browser installation](BROWSER-DISTRIBUTION.md).

## Upgrade and recovery

Finish active chats, disable/disconnect the browser extension and stop the DSH
host after confirming it has no running tasks. Then:

```sh
augmentor-maintenance prepare
sudo apt install ./augmentor-runtime_0.2.9_amd64.deb ./augmentor-desktop_0.2.9_amd64.deb
```

Proceed with installation only after preparation succeeds. Keep its private
backup and the previous package pair. Do not remove release locks or cancel tasks
to force installation. See [lifecycle and recovery](LIFECYCLE.md).

A DSH integration upgrade is separate from replacing Debian packages. The
installer preserves existing configuration and refuses to overwrite customized
owned presets. Such installations need a reviewed merge and backup, preserving
custom instructions, compaction settings, plugin choices and model curation.
Do not delete custom presets or add duplicate plugins to bypass that refusal.
Restart DSH after integration changes; verify the connection and retained chats
before enabling the browser extension again.

## Acceptance limits

The release status ledger records tests and candidate-specific evidence. Earlier
passing checks are not automatically evidence for every 0.2.9 artifact. Final
installed-package checks remain pending at preparation time.

Historical intermittent Wayland capture failures still require characterization.
Incomplete frames and unsafe targets are rejected; do not promise uninterrupted
capture in every environment. External MCP catalogs/read operations do not prove
all editing workflows. Comfy was unavailable during the last acceptance probe.
Full public-release readiness must be evaluated against these limitations; this
candidate is not advertised as universally supported Linux software.
