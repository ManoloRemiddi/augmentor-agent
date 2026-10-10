<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Private observation store

`src/store.ts` implements `augmentor-observation/1` as diagnostic read models. It never owns Pi conversation state, resumes a request or executes a tool. See [Harness qualification](../../docs/AUGMENTOR-HARNESS.md) for lifecycle, privacy and open performance gates.

Events have stable UUIDs, ordered per-session `seq`, timestamps, kind, optional turn/request correlations, metadata and payload coverage. The counter is reserved atomically before append. Clearing or expiry preserves the counter. Forward and backward pages use exclusive sequence cursors, up to 500 records. Native session history remains untouched.

Full structured payload retention is explicit opt-in. Bodies are private JSON files with known credential fields redacted and SHA-256 over the stored UTF-8 body. Retrieval returns bounded text chunks, `units: utf8-bytes`, `nextOffset` and `hasMore`; clients concatenate text and parse only after the last chunk. A cursor inside a multi-byte character is rejected. Very small pages may advance by one complete character. Missing or expired payloads return `available: false`.

Default retention is 14 days and 512 MiB. Payloads are evicted before metadata. Individual bodies cap at 32 MiB or half the budget. Crash-tail recovery and owned temporary-file cleanup are local storage repairs. One runtime owner must hold the profile; the IPC listener is acquired before construction. Metadata paging currently scans JSONL; indexing and full-history search remain delivery gates.
