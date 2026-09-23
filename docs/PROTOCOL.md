<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Augmentor Pi client protocol v1

Transport: UTF-8 newline-delimited JSON over an owned, mode-0600 Unix socket. Maximum frame: 1 MiB. Slow event consumers are disconnected rather than accumulating unlimited server buffers. This is the app's transport contract; Pi SDK types remain inside the host.

Begin every connection with `{"id":"hello","method":"host.hello","params":{"protocol":"augmentor-pi/1"}}`. The matching response has `id` and `result`; errors have `id` and `error.message`. An incompatible version is rejected. Request IDs are ASCII letters/numbers/underscore/dot/hyphen, up to 128 characters.

Commands:

| Methods | Parameters / result |
| --- | --- |
| `host.describe`, `host.shutdown` | Versions, capabilities, paths, PID and active-turn count; shutdown refuses active tasks |
| `models.list`, `models.validate`, `models.pin`, `models.reload`, `models.configure` | Catalog, exact provider/model validation, pins, local config reload and provider configuration |
| `session.create` | `sessionId`, absolute `cwd`, explicit `selection: {provider,model}` for new sessions; existing sessions attach without executing |
| `session.list`, `session.models` | Native rows and the saved selection |
| `session.selectModel` | `sessionId`, `provider`, `model`; unavailable/unauthenticated routes fail explicitly |
| `session.prompt` | `sessionId`, text `content` parts; returns `accepted` and `turnId`; a concurrent turn is rejected |
| `session.branch` | `sessionId`, caller-generated `newSessionId`, `messageSeq`, `mode: reply` or `edit`; returns a new native session row and inherited selection. Repeated identical targets with the same new ID return that branch. Reply mode includes the selected assistant message; edit mode excludes the latest user turn. Active sources, stale edits and unresolved tool-call messages are rejected. |
| `session.cancel` | Cancel active/queued work and pending interactions; does not kill unrelated applications |
| `session.history` | `sessionId`, optional `maxMessages` and `beforeSeq`; whole user-message groups and `hasMore` |
| `session.rename`, `chats.saved` | Title and saved metadata; no DSH workspace association |
| `events.subscribe` | `sessionId` or null; only that conversation's events on this connection |
| `interaction.respond` | `rpcId`, `sessionId`, `value`; late/duplicate answers fail |
| `prompts.list/save/delete` | Named Markdown prompt content; updates/deletes require the current per-prompt `expectedRevision` hash |
| `settings.describe/mutate` | New-chat tool policy, with namespace revision checking |

Unsolicited data is wrapped in `event`. Display messages use `method: session/event`, `payload.sessionId`, and `payload.event` containing a durable `seq`, display `type`, `data`, and when applicable a `turnId`. Display types include user/message, assistant/chunk, assistant/message, tool/call, tool/result, session/title, runtime/error and turn/start/end. Display events are a private recovery projection; Pi's session files own the conversation supplied to the agent.

Questions and approvals carry a unique `rpcId`. Subscription reattachment redelivers pending interactions; a resolution emits `interaction/resolved`. Default timeout is two minutes. Stop, timeout or losing the last subscribed UI resolves a pending action without permission to execute it. No connected UI means manual actions are denied. Completed interactions cannot be answered again.

The Python client never automatically retries prompts or tool actions. The host retains the last 100 accepted prompt request IDs per conversation to reject duplicate execution after a lost response. This is bounded deduplication, not an unlimited exactly-once guarantee. Reconnect reconciles history and live frames by `seq`. Restart records interrupted work; it never replays it. A prior external action may have completed before a crash, so a user must verify that outcome before asking for a retry.

The native policy values are `read-only`, `workspace-write` (UI label “Ask before actions”), and `danger-full-access`. The middle mode asks for all state-changing/unknown tools; its historical identifier does not imply an OS filesystem sandbox. Policies are snapshotted at chat creation.

The published distribution includes `dist/protocol/schema.json`, request/event fixtures in `dist/protocol/fixtures/`, and the TypeScript declarations in `dist/protocol/src/`. The schema validates the request envelope; method-specific validation is implemented in the host and covered by contract tests.

Literal Bash queries for the clock (`date` with display flags/format), working directory (`pwd`), identity (`whoami`, `id`), kernel (`uname`), uptime, memory (`free`) and disk usage (`df`) run without approval in both read-only and ask-before-actions chats. Only explicitly recognised arguments qualify. Shell pipelines, redirections, substitutions, clock-setting arguments and other commands keep the normal policy. This classification also applies when existing chats resume.

Message branching uses Pi SessionManager on a separately opened source. The child owns a separate Pi session file and display journal, inherits the source working directory, model selection and tool policy, and records its source and message sequence in metadata. Earlier tool calls/results remain context without executing again. Branching itself submits no prompt. Edited resubmission first creates an edit branch, attaches/subscribes to it, then sends the revised text through the usual prompt path. Original conversations remain unchanged. Display sequences are local to each conversation; clients must keep the conversation ID with an edit target.
