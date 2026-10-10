<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Managed MCP dispatch and failed acknowledgments

The accepted Harness migration requires unknown action outcomes to survive reconnect without replay. Pi 1.1.0's SDK retries any MCP request once after `McpSessionExpiredError`, assuming an HTTP 404 means the server did not execute it. An independently authored actual HTTP/SDK-owner fixture disproved that assumption for a server that applied a mutation before returning 404: one logical tool call changed the fixture twice. This is a reproduced integration failure, not a claim that compliant MCP servers normally behave this way.

Augmentor now supplies `managedMcpTransport` through the supported `createMcpExtension({createTransport})` hook. The pinned public `@earendil-works/pi-mcp` **1.1.0** transport package is declared directly; it was already present in the production lock graph. The SDK retains its existing AgentSession, MCP clients, discovery, tool pipeline, nested calls, OAuth credentials and lifecycle. No separate agent loop or SDK-private import is added.

## Dispatch boundary

HTTP JSON-RPC `tools/call` requests receive manual redirect handling. A failed HTTP response after dispatch becomes a public `McpHttpError` with its real status and an explicit unknown outcome; it cannot become the SDK's automatically retried session-expiry error. Error bodies remain private original evidence rather than being inserted into model context. A dropped acknowledgment remains a failed, unknown dispatch through the existing SDK and action ledger.

Before SDK result normalization, the managed owner appends **`augmentor-mcp-transport/1`** native custom entries containing the configured server name, transport request ID, actual dispatched method/parameters, status/content type and retained error body. Transport request headers, their bearer credentials and the configured server URL are not copied into that entry. Dispatched parameters and returned bodies retain their original private data. It is independent of diagnostic capture and does not insert a model message or memory source. Existing native original search/read/export can inspect it. The agent’s `tool_result_excerpt` currently reads SDK/tool-result originals; exposing these separate HTTP originals through that tool remains work. The transport request ID is not claimed to be a canonical agent tool-call ID; complete causal provenance remains separate work.

Body retention captures up to **1 MiB**, with a **500 ms** body-read deadline, exact retained bytes as base64, a retained-prefix SHA-256 and decoded text. Complete, partial and unavailable coverage plus reasons distinguish a full body from truncation, failed reads or a stalled stream. A failed native save adds an explicit evidence-gap message. Successful JSON-RPC tool results continue through the existing SDK/tool-original path; this entry covers failed HTTP acknowledgments, not exact transport bytes for every MCP interaction. These native entries share Pi session privacy, retention and deletion semantics; clearing optional diagnostics leaves them intact.

On a 401 or a 403 `insufficient_scope` challenge, the SDK-supplied auth provider may refresh credentials or record its authorization challenge. The failed tool call is still rejected; refreshed credentials do not authorize resending that call. Pre-dispatch token refresh remains owned by the SDK. Auth-provider failures retain their SDK handling. HTTP metadata/resource requests retain the normal SDK retry/auth behavior because they do not dispatch tools.

After a guarded HTTP tool failure, the old connection closes once its concurrent tool requests settle. Auth-provider exceptions still take the SDK’s own error/close path; concurrent authorization-failure receipts and cancellation/timeout combinations require further qualification. Public response listeners retain pending IDs through asynchronous SSE receipts; SDK cancellation removes timed-out/cancelled IDs. The failed request is rejected before reset. A later explicit operation can initialize a new SDK connection. The guard does not patch private SDK/client fields or change an active conversation's model, tool permissions, approved settings or owner release.

Stdio retains the public SDK transport and platform home/cwd/shell behavior. The selected MIT [configuration resolver](../packages/runtime/vendor/pi/SOURCE.md#configuration-value-resolver) preserves environment references, literal escapes and trusted command values. Its only source edit uses the public SDK shell export. Missing configuration values produce a sanitized error. Managed configuration remains `agent/mcp.json`; project files and other Pi profiles remain excluded. Server logs remain opt-in and private.

## Qualification scope

Implementation revision: **`e4cb3f34637c01fa4004894432764f1bb8c060fb`**. [The handoff checkpoint](AGENT-HANDOFF.md#october-10-mcp-failed-acknowledgment-checkpoint) records final **704 source cases/702 passes/two optional skips**, **11 focused passes** and **75 ordinary staged passes** with bundled Node 24.19.0. All **293 compiled files** and locks/catalog/selected notices match the staged tree; the inventory remains 126 npm instances and four common-stage native components. These are synthetic source/package fixtures, not live OAuth or installed-platform acceptance.

`tests/pi-mcp.test.mjs` runs actual Pi SDK sessions through the private owner and synthetic provider. Its HTTP server records mutations before returning 401, scope-required 403, session-expired 404, 500, a dropped socket or a redirect. Direct and codemode-nested expired calls retain one mutation and an unknown action outcome. A later explicit read succeeds through the same AgentSession without replaying the failed mutation. The existing approval, Stop, lost-ack recovery, original evidence, cold inspection, surface isolation and child-shutdown cases remain in this wire fixture.

`tests/mcp-transport.test.mjs` uses the public MCP client and an actual HTTP server. It checks failed statuses, private error-body retention with exact prefix/truncation and header exclusion, credential rotation without action replay, redirect refusal, dropped acknowledgments, a concurrent successful SSE receipt and configuration compatibility. The actual owner fixture recovers a complete native HTTP error original with capture disabled and proves its body is absent from provider context. These credential callbacks are independently authored fixtures; they are not live OAuth or real-account evidence.

Run after `npm run build`:

```bash
node --test --test-concurrency=1 tests/mcp-transport.test.mjs tests/pi-mcp.test.mjs
```

`AUGMENTOR_PI_TEST_ROOT` selects a separate production tree for the owner and transport adapter. The test driver and authored fixtures remain in source. The final handoff checkpoint records exact revision/counts, staged byte correspondence and matching-head CI status. Normal packages retain the [qualified QuickJS engine](QUICKJS-ENGINE.md), its source/notices and five optional-extension exclusions.

This closes the reproduced SDK transport replay path. It does not prove an arbitrary server's side effects or semantic task completion from an HTTP status or receipt. Live MCP OAuth UI/refresh, real server workflows and the broader auth/drop/session/parallel lifecycle matrix remain release acceptance work. Browser-only MCP, physical audio, complete platform/installed/update/rollback/privacy acceptance and every other accepted P0/P1 migration requirement remain open. DSH is retained and this candidate remains unselected.
