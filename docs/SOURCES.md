<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Source baselines and migration inventory

Inspected 2026-09-05. These are provenance records, not claims that Pi integration has passed tests.

| Source | Recorded revision / status |
| --- | --- |
| [Augmentor Linux](https://github.com/ManoloRemiddi/augmentor-agent-linux/tree/473fecef71102460cf666d35d0f7bc78a69ac7db) | `473fecef71102460cf666d35d0f7bc78a69ac7db`; existing local checkout clean at inspection; README native alpha 0.5.0 |
| [DSH browser Augmentor](https://github.com/ManoloRemiddi/augmentor-dsh-extension-plugin/tree/a6a43fb150f2a8fed591d061541d32c4cd6d91b0) | `a6a43fb150f2a8fed591d061541d32c4cd6d91b0`; remote default branch `master`; README and root layout inspected |
| [Shared DSH prompt library](https://github.com/ManoloRemiddi/dsh-prompt-library) | `c92e1431546e564677cdcada8fbc18f373791a53`; README contract audited, explicit importer copies only pins and prompt-library content |
| [Pi upstream](https://github.com/earendil-works/pi/tree/da840b6216578c2a571d0374ac6a2091a83f9d91) | `da840b6216578c2a571d0374ac6a2091a83f9d91`; inspected main metadata plus SDK/RPC/package docs |

The original Pi repository URL `badlogic/pi-mono` redirects to `earendil-works/pi`. Upstream manifests and npm report `@earendil-works/pi-coding-agent` and `@earendil-works/pi-agent-core` at `0.85.1`, requiring Node `>=22.19.0`. The upstream `pi-ai` manifest is also `0.85.1`. Older examples use `@mariozechner`; do not mix scopes or copy obsolete SDK signatures. The installed lock resolves the three named Pi packages to 0.85.1; SDK signatures and behavior were checked against that installation. Local Node at inspection: `v24.19.0`.

## Linux migration map

Paths below refer to the legacy source tree. The Qt app and desktop helpers have been ported with attribution; transport and policy are implemented in the new Pi host.

| Existing component | Target treatment | Milestone |
| --- | --- | --- |
| `app/augmentor_linux/window.py`, `composer.py`, `surfaces.py`, `icons.py`, assets | Port Qt presentation; replace DSH labels/actions | L2 |
| `preferences.py`, `shortcuts.py`, `workspaces.py` | Reuse desktop/UI behavior with distinct Pi app identity and storage | L2/L3 |
| `dsh.py` | Replace HTTP/WebSocket API, DSH config lookup and request envelopes with Pi-host client | L2 |
| `controller.py`, `transcript.py` | Adapt streaming, turn/session state, history and reconnect semantics | L2/L3 |
| `panels.py` | Replace DSH versions/settings/approval UI and cross-agent history assumptions | L3 |
| `prompts.py` and DSH prompt-library namespace | Keep slash UX; replace backend, add shared editing and explicit import | L3 |
| `desktop.py`, `browser.py`, `doctor.py` | Port useful OS helpers, capability checks and diagnostics | L3/L4 |
| `plugin/src/index.js` | Rewrite registration as Pi tools; preserve helper behavior and bounded execution | L3 |
| `plugin/src/chats.js` | Replace DSH workspace/session association with Pi sessions and bookmark metadata | L3 |
| `presets/augmentor-linux/` | Adapt identity/instructions into Pi resources, remove DSH composition | L1/L3 |
| `scripts/install-preset.py`, DSH plugin manifest/patch | Retire in successor; replace with Pi resource setup | L4 |
| `scripts/augmentor-linux`, `scripts/install-desktop.py` | Adapt runtime startup and install paths; avoid shortcut collisions | L4 |
| Existing Python/Node tests | Port behavioral checks; replace DSH contract fixtures with Pi ones | L1–L4 |

## Parity boundaries

The old README reports working native chat/streaming, compact view, appearance, shortcuts, history/save/rename, model selection, prompt completion, reconnect and three Linux tools. Its live evidence is legacy evidence only; re-verify these behaviors on Pi.

The old app does not yet provide general desktop input, portal capture, dedicated OS customization, native self-update or broad Linux certification. DSH-wide historical browsing and continuing DSH conversations are not promised by the first Pi release. Preserve access to the original application while any explicit import tools are designed.

## Package references

- [coding-agent manifest at recorded revision](https://github.com/earendil-works/pi/blob/da840b6216578c2a571d0374ac6a2091a83f9d91/packages/coding-agent/package.json)
- [agent-core manifest at recorded revision](https://github.com/earendil-works/pi/blob/da840b6216578c2a571d0374ac6a2091a83f9d91/packages/agent/package.json)
- [Pi coding-agent on npm](https://www.npmjs.com/package/@earendil-works/pi-coding-agent)
- [Pi agent-core on npm](https://www.npmjs.com/package/@earendil-works/pi-agent-core)

## Composable migration, 2026-09-06

The browser baseline was imported with `git subtree` under `apps/browser`, retaining its history and attribution. The DSH wire client is isolated under `apps/native/augmentor_linux/adapters`. Pi SDK packages remain pinned at 0.85.1. Native and real Chromium integration evidence now covers both harnesses; see [implementation evidence](IMPLEMENTATION.md) for the exact distinction between deterministic fixtures and real local-model runs.

## Productization licensing, 2026-09-06

The native binding is now PySide6 Essentials/Shiboken **6.8.2.1**, verified with
the native suite and isolated X11 mouse/external-clipboard proof. This development
wheel evidence does not certify Debian's separately built packages. Pi's npm
0.85.1 metadata records git head `d981de1229ef899957bbe968bc8dcda02a21f477`;
its MIT notice is retained from that revision. See [licensing](LICENSING.md),
`licenses/catalog.json` for additional notice provenance, and the
[execution ledger](PRODUCTIZATION-STATUS.md) for outstanding artifact gates.

## Hindsight integration, 2026-09-06

Hindsight **0.9.2**, source `424601520456a6d06a81b2fdc709a0d023d800af`, is tested as
an independent HTTP service. The container digest and real retain/recall/UI/engine
checks are recorded in [MEMORY.md](MEMORY.md). Its root source license is MIT;
the OpenAPI metadata's Apache label is not a replacement for the root license.
Augmentor does not redistribute the server or its model dependencies.

## DSH and desktop preview, 2026-09-06

DSH's separately installed Node CLI is checked at **0.1.1-rc.2**, with host API
**0.0.1**, dsh-base/dsh-tools **0.1.1-rc.2** and schemastery **3.18.1**. Its
inspected source is `b8f772c6574f959daaa591948c62596c6e5b3ab0`. Both actual SDK
bindings are verified against the shared desktop executor and deterministic
model requests; DSH-SETUP.md records the guided profile fixture.

The desktop VM runs Debian 13.6, KWin 6.3.6, portal KDE 6.3.5 and Kate 25.04.3.
Its CPU model is pinned in `release/desktop-vm.json`; DESKTOP-CONTROL.md records
the independent QEMU TCG masked-load reproducer and the distinction between VM
input evidence and independent hardware/model qualification.

## OpenCode integration (2026-09-08)

The installed CLI was updated from 1.18.9 to **1.18.29**, with its previous package
backed up. The matching plugin package is pinned in package-lock.json. Inspected
[OpenCode server documentation](https://opencode.ai/docs/server/),
[custom tool API](https://opencode.ai/docs/custom-tools/), and the
[1.18.29 source tag](https://github.com/anomalyco/opencode/tree/v1.18.29). The
running 1.18.29 server's `/doc` OpenAPI schema was also captured for the audit.
Native fork's exclusive boundary, plugin tool session identity, SSE part deltas,
provider catalog and abort behavior were checked against this version. The
legacy MCP tool API at this tag does not supply session identity; the adapter
therefore uses OpenCode's native plugin context rather than inferring a session
from the model's tool arguments. See `OPENCODE.md` for acceptance evidence.

## Desktop specialist (2026-09-09 development)

Uses the existing **Pi coding-agent, agent-core and AI 0.85.1** dependencies;
no new dependencies or model packages. Inspected the installed SDK declarations
and implementation for `createAgentSession`, custom tool allowlists,
`SessionManager.inMemory`, resource isolation, `agent.streamFunction`,
`agent.shouldStopAfterTurn`, sequential tool execution and cancellation.
The [upstream SDK documentation](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/sdk.md)
is background; the pinned local package is the compatibility reference.
Actual SDK sessions are exercised by `tests/desktop-specialist.test.mjs` against
a deterministic HTTP model and simulated executor. This is not a live model,
desktop or Resonant CORE qualification. See [scope and limits](DESKTOP-SPECIALIST.md).

## Formatted transcripts (2026-09-14)

Native Markdown uses the existing Qt 6.8.2 parser in GitHub dialect with raw
HTML disabled. Code tokens use **Pygments 2.18.0**, pinned in development and
provided by `python3-pygments` in Debian packages. The browser retains its
vendored **marked 12.0.2** and now includes **highlight.js 11.11.1** from
`@highlightjs/cdn-assets`, bundled locally as an ES module (no CDN at runtime).
Both themes share the same syntax palette. Unknown/unspecified languages stay
plain; code strings and copy source are preserved. Colour-only spans with hexadecimal
colours are supported in prose; other raw HTML, unsafe links, and image resource
loading remain disabled. Both clients offer formatting colour overrides.

Inspected APIs: [Pygments lexers and token streams](https://pygments.org/docs/api/)
and [highlight.js highlighting API](https://highlightjs.readthedocs.io/en/latest/api.html).
Regression tests cover real Qt document formats, streamed Markdown, tables,
Unicode code, both themes, and both shipped marked 12 and test marked 18.

## Fluid halo transport (2026-09-14)

The interactive halo now uses persistent velocity and premultiplied colour
fields, semi-Lagrangian backtracing with bilinear interpolation, a pressure
projection, and swept mouse impulses. The implementation follows the methods
in [GPU Gems chapter 38](https://developer.nvidia.com/gpugems/gpugems/part-vi-beyond-triangles/chapter-38-fast-fluid-dynamics-simulation-gpu).
It is a visual smoke model, not a physical plasma simulation. A moving emitter
is sampled along its path; pointer motion adds velocity and never masks opacity.
NumPy 2.5.1 was tested locally and is pinned for development; the fluid tests
also pass with the installed Debian NumPy 2.2.4. Debian packages
use the system python3-numpy dependency (>=1.24). No external assets are loaded.
Tests cover fractional transport continuity, stationary pointer neutrality,
velocity persistence and decay, moving-window wakes, and click-through input.

## Fedora RPM preview (2026-09-15)

Fedora 44 x86_64 container validation passed for the 0.2.9 RPM built from the
checksum-verified Linux bundle, with the recorded RPM lifecycle adapter override.
Tested packages: Python 3.14.7-1.fc44, PySide6 6.11.2-1.fc44, NumPy 2.4.6-1.fc44
and Qt base 6.11.2-2.fc44. DNF install, non-root runtime startup and offscreen
native rendering, native window/Markdown regression tests, active maintenance
blocking, idle reinstall, removal and reinstall passed. Exact artifact hash and
results are recorded in `outputs/fedora-0.2.9/fedora-proof.json`.
This does not verify a real Fedora desktop session, browser attachment or DSH
model turn. See [Fedora preview](FEDORA-PREVIEW.md) for installation and limits.


Resonant Voice development integration (17 September 2026): protocol `resonant-voice/1`, local `dsh-resonant-voice` 0.1.0 preview. Added native push-to-talk using optional sounddevice 0.5.2 and existing websocket-client; Chromium uses AudioWorklet/WebSocket through the existing product-authorized native-host route. Engine implementations live in the separate Resonant Voice package. This source integration is not yet deployed or qualified with real microphone/GPU inference. Existing DSH session/model/queue authority is retained.

### Automatic dual memory, 2026-09-19

Inspected the installed DSH 0.1.5-rc.1 `session/event`, `session/flush`,
`agent/pre-step` and `agent/status` contracts and committed `tool-result` message
shape. Exercised them with real DSH/Pi lifecycles and a fixture model, including
nested structured voice reply capture and reload. Pi remains pinned to 0.85.1;
TypeBox remains 1.3.7. A separate live Qwen extraction/recall proof and an installed
DSH capture check are recorded in [Dual memory](DUAL-MEMORY.md); neither is claimed
as microphone or human listening acceptance.

### Hindsight engine migration, 2026-09-19

The custom automatic summary engine is superseded by **Hindsight 0.10.0**,
MIT, upstream commit `5d46f9c8c8eb4fb96f549aa63abe1191b82a7840` and image
`sha256:3edcb6165cefdeaa6721dd0fce43cfd13b7a9c346ce0d2c5f4b4bf7bc3c8ac0b`.
The versioned REST API was inspected and exercised against the actual image:
scoped bank creation, knowledge pages, asynchronous idempotent retention,
operation polling, automatic consolidation and hybrid recall. Local CPU
embeddings/reranking and the existing Qwen3.8-27B-GSQ-RCO-IQ3_S-mtp-262k endpoint
were used. A synthetic fresh-session answer correctly recalled calm check-ins,
SQLite and the unfinished export screen after bridge restart. No human microphone
or acoustic acceptance is implied. See [dual memory](DUAL-MEMORY.md).

Resonant Voice source package **0.1.14** is maintained in its
[separate repository](https://github.com/ManoloRemiddi/resonant-voice).
The source contains hands-free native protocol support, reference voices and
per-window playback settings. The earlier 0.1.0 paragraph records the initial
integration only; current deployment and limitations are in the voice repository.


## Original Desktop remote preview · 2026-09-19

The mobile remote surface uses the unmodified noVNC v1.6.0 ESM release archive,
locked with integrity in `apps/mobile/package-lock.json`, ws 8.21.0 and esbuild
0.25.12. It was tested with x11vnc 0.9.17-1 and LibVNCServer Debian packages
0.9.15+dfsg-1+deb13u2, plus the existing Xvfb and installed Desktop 0.2.8
Resonant Voice preview. The maintained Qt source remains 0.2.9; the launcher
selects the installed matching build rather than bypassing the DSH version gate.

[noVNC source/license](https://github.com/novnc/noVNC/tree/v1.6.0),
[noVNC API](https://github.com/novnc/noVNC/blob/v1.6.0/docs/API.md),
[x11vnc project](https://github.com/LibVNC/x11vnc),
[research and boundaries](MOBILE-REMOTE-PLAN.md),
[actual validation](MOBILE-REMOTE-VALIDATION.md).

Mobile HTTPS follow-up: xcompmgr **1.1.8-1** (Debian 13 amd64, X11 license) was
extracted rootlessly and verified with the original translucent activity halo
during live generation. Android Command-line Tools **22.0**, archive build
**15859902**, verified SHA-256
`4e4c464f145a7512b57d088ac6c278c03c9eea610886b35a5e0804e74eedf583`, and Emulator
**37.1.11** were installed for device qualification. Installation is not an
Android acceptance result. [Official tools](https://developer.android.com/studio),
[acceleration](https://developer.android.com/studio/run/emulator-acceleration).

Android internal APK build: Platform API **36**, revision **2**; Build Tools
**36.0.0**; Platform Tools **37.0.1-15733141**. Java **21.0.12.1**, compiler module
invoked through `java -m jdk.compiler/com.sun.tools.javac.Main` on this host because
the standalone javac launcher is absent. SDKmanager 22.0 emits a deprecation
notice in favor of Android CLI; the recorded commands still completed.

Android emulator image: Google APIs x86_64, API **36**, revision **7**,
`x86_64-36_r07.zip` (1,895,447,397 bytes), official repository SHA-1
`c6bf44bdcd885bb902b4ba752d111a073ad7a817` verified before extraction. The exact
archive was downloaded over HTTPS; SDKmanager recognized the extracted package.
[Official repository metadata](https://dl.google.com/android/repository/sys-img/google_apis/sys-img2-3.xml).

### Controlled memory and context, 2026-09-21

The same pinned Hindsight 0.10.0 image is now exercised with its supported HTTP
extension hook: synchronous `retain_batch_async`, scoped `run_consolidation_job`,
`get_bank_freshness` and `refresh_mental_model`, with the autonomous worker off.
The extension additionally uses the pinned engine's `_get_pool` for durable
receipts. Scoped consolidation uses the pinned engine module because the public
bank-wide wrapper cannot exclude historical pending facts. These internal
dependencies require requalification before upgrades.
Knowledge-page IDs and backing `mental_model_id` are kept distinct. Consolidation
completion is checked against durable failure counts because its public return
value omits internal failures. Streaming gateway assembly was tested against the
existing Qwen endpoint, including real cancellation. DSH surface replacement and
Pi lifecycle hooks retain their pinned versions. See [contract and evidence](CONTROLLED-MEMORY.md).
