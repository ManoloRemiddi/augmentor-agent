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
