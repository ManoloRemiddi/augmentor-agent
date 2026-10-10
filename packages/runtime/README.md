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

`src/display-history.ts` adds derived byte-offset/compaction indexes for Pi `session.history`. Both loaded and cold paging use this reader. Its 64-byte entries retain sequence, original offset/length, user-group rank and links that skip completed or empty reasoning deltas; bodies are never copied into the index. Valid persisted indexes survive owner restart. Missing/stale/damaged indexes rebuild by streaming the display journal, and only owned abandoned atomic-write files are removed. Complete source corruption is preserved with an error; incomplete tails retain the existing owned repair. Invalid/reused sequences fail before append. Response budgets, original sequences, partial replies and suppression of finalized deltas before applying the cursor match the established `historyPage` contract.

`host.describe.capabilities.indexedDisplayHistory` advertises the reader. This does not index or rewrite Pi native sessions, run inference or introduce another agent loop. SDK resume/branch/edit and conversational-memory initialization still rehydrate their required native/display state; loaded display arrays remain in memory for those operations. Inspection/paging is the optimized path. Indexes are private derivatives alongside `<id>.events.jsonl`, outside diagnostic observation retention and within the display-history lifecycle. POSIX modes are 0600; physical Windows ACL and installed/platform acceptance remain separate gates. See [indexed display-history qualification](../../docs/AUGMENTOR-HARNESS.md#indexed-display-history-with-original-compaction-semantics).
