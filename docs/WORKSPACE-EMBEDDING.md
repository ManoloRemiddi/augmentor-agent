<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->
# Embedded Browser and specialist workspaces

Augmentor can host its existing Browser surface inside an application. The
product serves the same extension HTML, renderer, composer, history, branching,
voice, prompts and settings modules. `apps/browser/embed` supplies web hosting
and native-message transport. It does not implement another chat UI or agent.
DSH remains the conversation/context/compaction owner; the existing memory
companion remains the continuity owner. Pi remains available in the standalone
product; embedded profiles currently support DSH.

## Profile and application contract

Owner-installed JSON profiles in `~/.config/augmentor/workspaces` specify a
stable ID, display name, DSH preset, canonical cwd, relationship/project memory
identity, instruction files, direct tool plugins, permitted parent origin,
public proxy path, and a private proxy-token file. `index.json` registers the
profiles that the shared DSH integration recognizes. Configuration is trusted
local installation data, never accepted from a web page or email. Credentials
and machine-specific profiles must not be committed to this repository.

Run `scripts/install-workspace-profile.mjs /absolute/profile.json` from the
selected compatible release. It composes the specialist from the installed
Browser preset, retaining normal tools, compaction and execution recovery,
then adds the application's job description, skill instructions and tool set.
It does not invent a parallel agent loop. App capabilities can be direct DSH
tools over an authenticated API; MCP is optional, not required for that path.
The installer backs up existing preset files. Updating a profile never rewrites
conversation IDs or silently converts historical sessions to another role.

The native boundary enforces cwd/preset for lists and explicit operations.
Optional legacy presets can be listed/read in that cwd, but cannot be resumed
under a new role. New sessions bind workspace memory before the first input.
Automatic capture and `memory_recall` use that same identity; the optional
personal/manual library is excluded. Branching binds the actual returned child
ID. Personal memory administration stays in standalone Augmentor. Other shared
settings (models, voice, appearance, prompt library) keep their normal ownership.

The parent may send `{type:'augmentor-context',context:{...}}` after receiving
`augmentor-ready`. This is selected-record/page context, not authorization.
Only the configured parent window/origin is accepted. The product attaches a
bounded selection to the next prompt, and its workspace adapter injects it into
the existing DSH run. Current business evidence must still be read through app
tools. `augmentor-link`, `augmentor-settings`, `augmentor-hide` and
`augmentor-status` are presentation events for the host application.

## Hosting and release lifecycle

`augmentor-embed.service` listens on loopback port 8872. Install it with the
selected release's `scripts/install-embedding.py`. Its stable launcher reads
`desktop.json` at every start, so it follows managed product selection. Stage
and activate a complete compatible artifact using `augmentor-update`; never
patch selected files or point production at a development checkout. Coordinate
DSH plugin/preset upgrades with normal idle/compatibility checks. Existing
windows keep their loaded version until reopened.

An authenticated application reverse proxy exposes `/embed/<profile>/...` at
the profile's configured public path, adding a server-held bearer token. Both
HTTP and WebSocket require it; sockets additionally require the configured
Origin. Do not put this token in browser JavaScript or URLs. A private SSH
stream-local reverse forward can connect a NAS proxy to the host's loopback
service without opening any network listening port. The application must apply
its owner access policy before proxying upgrades as well as ordinary HTTP.

One live WebSocket connects to one actual product native host. There is no NAS
poll queue or copied runtime. Native histories up to 20 MiB can be delivered
without the former one-megabyte HTTP batch limit. Heartbeats and wake detection
replace stale connections; reconnection reloads the same DSH conversation.
Unknown prompt outcomes are never replayed automatically. Storage is private
per-profile product state, while DSH retains the authoritative transcript.
Keep DSH sessions, memory stores and product preferences in migration backups.
A sleeping/unreachable model host cannot generate replies; the UI recovers
when it returns without requiring a connector launch or losing the saved chat.

The existing extension remains the browser executor. Embedded panels do not
steal its action channel. Voice uses the existing native audio engine/devices;
an embedded web page is not a new remote microphone implementation. Registered
specialist voice roles require Resonant Voice's configurable workspace-role
contract (persisted preset + cwd + surface); speech settings/GPU placement stay
unchanged.

## Qualification

Source checks cover registered role/cwd boundaries, direct-ID denial, legacy
read-only history, memory binding mismatch, authenticated HTTP/socket access,
shared UI serving, preferences and >1 MiB history delivery. Existing DSH/native
host, interaction, branching, execution recovery and memory lifecycle tests are
retained. Tests use fixture models unless explicitly identified as live.
Deployment and actual conversation evidence is recorded below after cutover;
source tests alone do not claim an installed update or a physical sleep trial.

## Installed qualification — 26 September 2026

The private Linux/NAS application now consumes this product service instead of
its former copied host and polling connector. Source implementation starts at
`938d027`, with managed-directory asset correction `57b35c3` and internal
settings-navigation correction `f65cd2c` and dedicated-memory settings `958e17d`. A compatible 0.2.11 candidate was
built from the previous selected immutable release; this is not represented as
a complete source 0.2.12 upgrade. Final selection is
`20260926-094732-3b3861db`. The embedding service runs the selected artifact;
existing native windows were left on their earlier compatible releases.

Read-only live DSH verification used direct application tools, recognized the
assigned job and selected dashboard page, and reported actual connected and
unconnected data sources. No shell discovery was used. The owner's unfinished
conversation kept every original persisted record and its ID; one DSH lifecycle
record was appended on reopen. A native branch kept the profile and memory
identity. The Stop control produced a user-aborted turn. Original settings were
opened through the host UI. A compatible Resonant Voice 0.1.17 specialist ticket
handshake passed without changing the running speech companion or placement.

Forced embedding-service and SSH-tunnel termination recovered automatically
with the original chat selection and a visually verified unsent draft. No
unknown model action was replayed. These are process/connection fault tests,
not a physical suspend/resume or microphone/playback trial.

Source qualification: 56 relevant existing Node tests, three new workspace
embedding tests, 11 Python branch tests, and 35 voice-package tests. The host
application's 62 regression tests also passed. The first voice run lacked its
worktree dependency link; after provisioning the pinned dependencies all 35
passed. An installed-only asset-root failure and settings-anchor routing defect
were corrected in source and promoted through new staged artifacts, never by
editing selected files.

Deployment incident: an orchestration shell continued after an active-work
check failed, interrupting an unrelated DSH turn. It was reported to the owner;
the harness was restored, the interruption was verified, and that work was not
replayed. Follow-up commands fail immediately on errors. This deployment
incident is not described as safe idle restart evidence. Product/tunnel fault
tests did not restart the shared DSH harness.

Final selected artifact SHA-256: `62d488cb18c605ce14705fef74b530b9c2a6feb3f306c35db81650c841fb5346`.

### Resuming history

The inherited Browser history picker previously opened chats as read-only
previews. `dc1e2b2` adds an authorized resume operation in the product and uses
it for owned conversations: history selection preserves the persisted session
ID, model and role, reloads its events, and enables the composer. Registered
legacy roles remain read-only. Out-of-workspace and legacy resume attempts are
covered by the boundary tests. Opening history never submits a new prompt.

The installed 0.2.11 candidate applies the resume delta to its original
sidepanel module. Copying the complete newer source module initially omitted
its separate submit-feedback dependency; the actual Browser caught this and
the candidate was corrected before final acceptance. The added
`scripts/check-browser-assets.mjs` verifies all relative UI imports in both the
source and the compatible candidate (21 and 20 modules respectively). No
selected artifact was edited.
