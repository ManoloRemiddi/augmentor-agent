<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Shared Pi runtime host

`src/` integrates the public Pi coding-agent SDK: exact model selection, sessions,
resource loading, policy, client protocol, shared-service clients and lifecycle.
The independent prompt service owns prompt storage; the automatic-memory
companion owns its transcript journal and Hindsight delivery. This host owns
neither another memory engine nor a second conversational loop.

Build with `npm run build` from the repository root; run `npm start`. Qt is optional.
See [Pi protocol](../../docs/PROTOCOL.md), [architecture](../../docs/ARCHITECTURE.md),
[automatic memory](../../docs/DUAL-MEMORY.md) and [tests](../../tests/README.md).


The [Harness candidate](../../docs/AUGMENTOR-HARNESS.md) adds a client of this owner, opt-in effective-request/parsed-provider observations and deterministic native context-edit tool budgets. `tool_result_excerpt` reads originals only from the current branch; `session.trimTools` repairs idle loaded/cold histories without inference or action replay. Advisory checkpoints use finalized top-level tool results and public boundary drafts; they never force continuation or authorize retries. These use supported Pi 1.1.0 APIs. Managed analytics, install reporting and cache warming are explicitly off. The guide records capture limits, source/fixture evidence and remaining queue/recovery/adaptive/surface/release gates.

Standalone Native/Browser `inspection.open` uses the private owner IPC to lazily open a conversation-scoped read-only Harness. Its separate bearer permits fixed history/observation reads and scoped live polling, expires after four hours, and never owns approvals or exposes the operator token. Opening inspection sends no prompt and does not enable capture. See [the authority and qualification record](../../docs/AUGMENTOR-HARNESS.md#native-and-browser-conversation-inspection).
