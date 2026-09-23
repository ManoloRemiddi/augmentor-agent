<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Optional manual memory library

[Automatic relationship and work memory](DUAL-MEMORY.md) now maintains continuity
from conversations using Hindsight 0.10.0, with separate relationship knowledge
pages and project retrieval. See that guide for setup, migration and evidence.
The rest of this page documents the older, optional manual Hindsight library; it
is independent of the automatic banks and is not the continuity engine.

## Hindsight library

This manual-library connection is optional and disabled on a fresh installation. Linux **Settings →
Memory** and the browser's **Memory** icon open the same per-user service. A model
connection is not required to manage retained data.

Connect an independently installed Hindsight **0.9.2** instance. Use a numeric
loopback HTTP address for a local service, or HTTPS and an API key for a remote
service. Enter a user bank and, optionally, a different project bank. Check the
connection, then save and enable. Checking contacts health/version endpoints; it
sends no conversation history. Keys are private local configuration, unencrypted.
Redirects are rejected and a stored key is never forwarded to a different host.

The selected recall scope applies to **all Augmentor chats**. This preview has
one configured project bank; it does not yet infer separate projects from working
directories. Linux and browser, Pi and DSH, recall through this same boundary.
Models cannot choose bank IDs, switch scope, retain or delete data. Recalled text
is reference data, never authorization or instructions. A remote administrator
must enforce access to the chosen banks: local scope routing does not replace
Hindsight server authorization. Separate Linux users have separate private sockets,
configuration and databases; sharing a remote bank credential intentionally shares
that bank's access.

In Memories, enter the exact text to remember and press **Retain this text**.
Augmentor submits only that text and source metadata (surface, harness, chat ID).
There is no automatic transcript upload. Hindsight may call its configured model
and charge for extraction. Queued retention is shown as pending until Hindsight
reports completion. Unknown outcomes are not automatically replayed, including
after reconnect or restart. Refresh reconciles operation status without writing.

View the original retained documents, page through them, export all extracted
facts as JSON, or delete a selected document and its associated memories. Deletion
is blocked until an accepted retain has finished or failed, so a queued operation
cannot silently recreate the document. Successful deletion also purges its source
text from Augmentor's local operation journal. Previously exported files, backups,
chat messages containing recalled facts and remote service backups remain subject
to their own deletion/retention controls. Export contains extracted facts; it is
not a backup of the entire Hindsight server.

Disable stops new recall and retention. Data controls remain available, and
previously submitted operations may finish. If the service is unavailable, the
agent receives an empty unavailable result and can continue the ordinary chat.
Stop aborts the client-side recall without replaying the request.

## Verification and limits

On 2026-09-06, `scripts/memory-proof.py` drove the actual Qt form through check,
save, retention, source viewing and disable. A real Hindsight 0.9.2 instance used
the independently running local Qwen model for extraction and recall. The proof
observed asynchronous completion, separated user/project facts, exported facts,
and verified remote deletion and local source purge. With `DSH_TEST_MODULES`,
real Pi SDK and isolated DSH sessions on both surfaces called `memory_recall`;
the deterministic HTTP model's next request contained the actual recalled fact
in all four combinations. Eight model requests were observed.

The Chromium proof independently used real DOM pointer actions for connection,
retention, viewing, disabling and deletion, and checked the downloaded export's
contents. It also completed browser navigation/type/click after first-run model
setup without copying a developer configuration. These are implementation tests,
not external beta or remote multi-tenant service certification.

Test server image: `ghcr.io/vectorize-io/hindsight:0.9.2` at digest
`sha256:3b46e26ec69355422c46ceb496cd758ae226d751be4a0799b4e844251d524d46`.
Hindsight is not included in Augmentor packages. [Guided DSH setup](DSH-SETUP.md)
mounts the shared memory binding in Augmentor's two owned product presets.
Registering it globally would expose the user's memory tool to unrelated DSH
agents. Legacy/custom preset migrations remain a separate review.

See the version-bound [Hindsight API schema](https://github.com/vectorize-io/hindsight/blob/424601520456a6d06a81b2fdc709a0d023d800af/hindsight-docs/static/openapi.json)
and [retention documentation](https://hindsight.vectorize.io/developer/api/retain).
