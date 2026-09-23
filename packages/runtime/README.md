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
