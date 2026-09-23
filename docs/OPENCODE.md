<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Historical OpenCode harness · Augmentor 0.2.6

**Retired in 0.2.8.** Augmentor Agent Desktop and Browser support DSH and Pi.
The instructions below document the former 0.2.6 integration and do not apply
to current releases. Existing OpenCode conversations and configuration remain
preserved; they are not transferred or replayed into another harness.

OpenCode is the third engine behind the existing Linux window and Chromium
extension. Select **OpenCode** under **Settings → Harness** (Linux) or
**Settings → Harnesses** (browser). Each harness retains its own model selection
and conversations. Switching engines does not convert or replay a conversation.

The adapter requires the installed OpenCode CLI **1.18.29** and uses the matching
`@opencode-ai/plugin` package, locked in the product's npm dependencies. The CLI
is discovered in `~/.local/bin` or PATH; `AUGMENTOR_OPENCODE_BIN` can specify it.
The app reports missing/incompatible versions instead of silently choosing Pi
or DSH. OpenCode is an external prerequisite, not another bundled agent loop.

## Boundaries

- `packages/opencode` owns the adapter, its managed loopback OpenCode server,
  native session mapping, display journal and tool bindings. OpenCode owns model
  calls, tool execution, compaction and native history.
- `augmentor-opencode/1` reuses the normalized session/event shapes. The common
  native controller and browser socket bridge render all supported engines.
- Live SSE deltas supply streaming text. Native message reads reconcile final
  answers, reconnects and incomplete observations. Empty user records are held
  until OpenCode has inserted their text parts. A user Stop preserves partial
  output and is not displayed as an application failure.
- Native `session.fork` copies actual context, including tool results. Its cutoff
  is exclusive: a reply branch cuts before the following native message; editing
  cuts before the latest user message. Original sessions are unchanged.
- OpenCode's Linux role exposes normal OS tools and the shared desktop executor.
  The browser role denies shell, files, delegation and Linux tools. Only the
  attached browser executor and optional shared-memory recall are exposed.
  The tool router independently checks session ownership, surface and policy.
- The shared prompt service, clipboard expansion and memory service remain
  unchanged. Native and browser Copy, branch and edit use their existing UI.

## Configuration and lifecycle

The managed server binds loopback with a generated authentication password.
Its private socket and metadata live under
`$XDG_STATE_HOME/augmentor-opencode` (normally `~/.local/state/augmentor-opencode`).
Its native SQLite database is there too, through OpenCode's `OPENCODE_DB` option,
so the maintenance backup includes native context as well as display history.
The server and adapter hold package lifetime leases.

Provider definitions are read from the user's OpenCode configuration. Credentials
continue to use OpenCode's own supported authentication storage. The adapter does
not overwrite that configuration or attach to the user's OpenCode terminal.
Its separate configuration includes only the provider/model settings and the
Augmentor plugin and roles, with project configuration disabled. It does not
inherit unrelated plugins, MCP servers or agent roles into browser sessions.

After changing providers in OpenCode, use **Refresh** in Augmentor's model picker.
This reloads the managed OpenCode server only when its chats are idle. The current
model must remain available; sending never silently substitutes another model.
The model configured as OpenCode's default supplies the initial browser default.

New chats inherit the selected permission mode. Read-only blocks mutations;
workspace-write asks before mutations, with narrowly recognized routine shell
queries allowed; full access permits the surface's allowed actions. Questions
and approvals use Augmentor's existing controls. Desktop capture still requires
an image-capable model and the desktop executor's OS consent.

Submissions carry a durable request ledger. A transport failure or restart never
resends a submitted prompt. The adapter reconciles saved native history and
reports uncertain outcomes. An interrupted HTTP observation does not prove an
OS action was rolled back.

## Verification

- Contract regressions cover normalized streaming, incomplete user records,
  journal recovery, native branch boundaries and cross-surface tool rejection.
- `scripts/browser-composable-proof.py`, with `AUGMENTOR_PROOF_HARNESS=opencode`,
  runs actual Chromium, the extension, native bridge and OpenCode against a
  deterministic local model. It verifies navigation/snapshot/type/click against
  a real page, rendered Copy/clipboard/scroll, branch and edit with retained tool
  context, reconnect without replay, and shared prompt edits and clipboard tokens.
- `scripts/opencode-linux-proof.py` runs actual OpenCode and Qt controls against
  a deterministic local model. It executes Linux system inspection and shared
  memory recall, observes live text, clicks Copy and Branch, proves an OS write
  waits for a mouse approval, and clicks Stop during streaming.
- A separate smoke conversation used the user's configured local llama.cpp
  provider through OpenCode 1.18.29 and returned the expected answer.

Evidence lives in ignored `outputs/opencode-*-proof.json`,
`outputs/browser-opencode-proof.json`, and their test logs/screenshots. These
fixtures use separate state and do not send prompts into the user's existing
conversations. Desktop capture/input capability shares the existing executor;
this integration's Linux proof does not claim a new OS consent/capture test.
