<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Augmentor Agent — Desktop & Browser

Augmentor Agent Desktop and Augmentor Agent Browser share a local Prompt Library
and support DSH and Pi. Linux and macOS are the first release targets; Windows is
deferred. This repository maintains both interfaces and their harness adapters.

DSH is the full-featured release target. Pi supports a declared subset; extensions
for features that currently require DSH plugins are future work. OpenCode support
has been retired, with its existing user data retained. macOS is under development;
successful development tests do not yet establish a public release.

Augmentor is currently a **development preview**. The release manifest is
[release/product.json](release/product.json). The Linux packages bundle the tested
Pi runtime; users connect their own model endpoint and credentials. DSH integration
is optional and retains the limitations in the [feature matrix](docs/FEATURE-MATRIX.md).

## Documentation and agent handoff

The public Desktop + Browser source is published at
[augmentor-agent-source](https://github.com/ManoloRemiddi/augmentor-agent-source)
under [MIT with Augmentor Resale Restriction](LICENSE). See the
[publication scope and privacy audit](docs/PUBLIC-SOURCE.md). Earlier binary
downloads retain their shipped licenses.

Start with the [current architecture](docs/ARCHITECTURE.md),
[complete installation guide](docs/COMPLETE-INSTALL.md), and
[documentation index](docs/README.md). The [development handoff](docs/AGENT-HANDOFF.md)
retains historical qualification evidence; links to private development commits
and artifacts are provenance references, not public downloads.

To inspect the public source:

```sh
git clone https://github.com/ManoloRemiddi/augmentor-agent-source.git
cd augmentor-agent-source
```

## Install and use

For a fresh Debian 13 amd64 installation, start with the
[complete Desktop + Browser setup](docs/COMPLETE-INSTALL.md), including pinned DSH,
plugins and optional local voice/dual-memory provisioning. Existing installations
use the reviewed update/migration path.

For individual packages, use the [Debian package guide](docs/LINUX-PACKAGES.md) and
[guided model connection](docs/FIRST-RUN.md). Choose a model before sending a task.
**Settings → Recover connection** checks the runtime, repairs verified duplicate
history files with backups, and reconnects without resending messages. See the
[recovery guide](docs/DESKTOP-OFFLINE-RECOVERY.md) for supported repairs and limits.

Stop cancels active work; reconnecting does not replay an action whose outcome is
unknown. Hiding the app keeps its current task running.

Open Prompt Library to create a named prompt. **Insert clipboard** adds
`[clipboard]`; selecting that `/prompt` inserts the current clipboard text into
its template for review before sending. Changes made in either interface use the
same prompt records on this computer.

Messages support Copy with a confirmation tick. Pi supports Branch and Edit in a new chat. DSH supports safe closed-turn
branches and refuses edits whose fork would retain a queued input. Original chats
are preserved.
The [feature matrix](docs/FEATURE-MATRIX.md) records each surface/harness combination.

[Connect DSH](docs/DSH-SETUP.md) for the optional separately installed engine.
[Automatic dual memory](docs/DUAL-MEMORY.md) uses Hindsight knowledge pages for
relationships and semantic retrieval for projects, with preserved transcripts and
automatic consolidation. The [manual memory library](docs/MEMORY.md) remains optional. Linux also offers a bounded
[KDE Wayland desktop control preview](docs/DESKTOP-CONTROL.md).

Use the [upgrade, rollback, migration and removal guide](docs/LIFECYCLE.md) for
package maintenance. Configurations, prompts and conversations are retained by
default. Load the Chromium extension through the
[private preview guide](docs/BROWSER-DISTRIBUTION.md). Public distribution and
independent [beta assignments](docs/PRIVATE-BETA.md) remain release gates.

See the [cross-platform release plan](docs/CROSS-PLATFORM-RELEASE-PLAN.md) for Linux
distro coverage, macOS/Windows backends and public browser/OS downloads.

## September desktop development

The current development branch includes [Resonant Voice](https://github.com/ManoloRemiddi/resonant-voice)
for local speech, hold-to-record and slide-to-lock controls, voice selection and
delivery, plus optional native [hands-free conversation](docs/HANDS-FREE-IMPLEMENTATION.md).
The existing DSH session remains the conversational agent. Speech model licensing
is separate from the Augmentor application code; see the voice repository before distribution.

Other accumulated work includes [skins and appearance](docs/SKINS.md),
[second-window behavior](docs/SECOND-WINDOW.md), configurable shortcuts,
[slash commands](docs/SLASH-COMMANDS.md), browser observation/recovery and a
[Fedora RPM preview](docs/FEDORA-PREVIEW.md). These development changes are not a
claim that every installed artifact or target platform has been released.

The [September development ledger](docs/DESKTOP-UPDATE-2026-09-19.md) records the
architecture, repositories, checks and remaining acceptance items together.

## Mobile remote preview

An Android-first remote view of the original Qt Desktop is available as an
internal engineering MVP, with opt-in touch sizing and native dialogs.
See the [research and roadmap](docs/MOBILE-REMOTE-PLAN.md),
[run instructions](apps/mobile/README.md), and
[validation evidence](docs/MOBILE-REMOTE-VALIDATION.md). Native packaging, Android
device qualification and complete Desktop parity remain staged work.

## Development

Use Node 24.19.0 and the Python dependencies declared in `requirements-dev.txt`.
The desktop uses replaceable PySide6/Qt system libraries.

```sh
npm ci --ignore-scripts
python3 scripts/sync-version.py --check
npm run check
npm run build
npm test
npm run test:native
python3 scripts/package-debian.py
bash scripts/debian-package-proof.sh
```

[Architecture](docs/ARCHITECTURE.md),
[implementation evidence](docs/IMPLEMENTATION.md),
[productization plan](docs/PRODUCTIZATION-PLAN.md), and
[execution ledger](docs/PRODUCTIZATION-STATUS.md) distinguish implemented features
from release gates that still need to pass. Historical Pi-only instructions are
retained [separately](docs/HISTORICAL-PI-0.1.md).

Augmentor-authored code uses **[MIT with Augmentor Resale Restriction](LICENSE)**.
You may read, inspect, use and modify it freely, including for business. Selling
or reselling Augmentor, including modified versions, requires prior written
permission from Manolo Remiddi. This is public source under a custom license.
Earlier releases retain their shipped licenses. Redistributed components retain their own licenses;
see [licensing](docs/LICENSING.md) and the installed **About & licenses** view.
