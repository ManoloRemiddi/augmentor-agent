<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

## Shared prompt CI startup prerequisites — October 17

Hosted source **45088675** exposes two test-setup failures. Home’s final image
smoke check places shared data at `/tmp/data`. The real shared-profile guard
requires its immediate parent to be owned by the service user and protected from
other writers, so the world-writable shared temporary directory is invalid.
The test now creates its own **0700** parent as the container’s ordinary runtime
user before calling the same packaged prompt client. The service’s ownership
checks remain unchanged; existing data is not moved or re-permissioned.

The Linux SDK job’s fresh Python **3.13.5** environment also lacks the
`websocket` module imported by the actual prompt service’s optional DSH setup
binding. A new shared test-prerequisite file selects the **existing product**
`websocket-client==1.8.0` universal wheel and its existing Windows/macOS lock hash.
The SDK workflow installs it with hashes, binary-only and no dependency resolution
on all matrix platforms. The separate Windows Qt/native prerequisites remain.
No runtime dependency, DSH source, service behavior or installed application changes.

A fresh local Python 3.13.5 environment confirms the missing module before the
locked installation, then passes **10 Node cases across two files** for complete
shared-data consolidation, process ownership, cold reopen and no recapture.
**23 Python cases across three files** pass with the prepared Qt interpreter and
normal native import path. A separate actual Node prompt-client cold start passes
under a new private parent; a writable-parent control refuses before creating data.
Only its own temporary prompt service is retired; no model or owner data is used.

[Qualification](../release/harness-shared-prompt-ci-qualification-20261017.json)
records input hashes, failing hosted jobs and correction status. Full new-head
Home-container/SDK matrix results remain distinct from local source/client checks.
Both current MX review PIDs/all 36 protected paths/hashes, shared rows, registry,
menus/selections and GPU/voice states still match the preceding checkpoint.
No new app deployment, owner project transfer or NAS change follows.

# Shared prompts and memory during Harness consolidation

Harness, Native and Browser clients share one prompt/memory service when their
`AUGMENTOR_SHARED_STATE` and `AUGMENTOR_SHARED_DATA` roots match. Copying whole
review profiles creates independent libraries, generated person identities and
processing gateways instead. The October 16 read-only inventory found twelve
prompts in each of the two current reviews and nineteen captured memory records
between them. Their engine bank/cache tables were empty; their person IDs differ.
The pilot's copied gateway port conflicts with the primary owner. Raw inventories,
identities, credentials and content stay private.

## Single ownership

Prompt and memory processes now hold a shared data-root lifetime lease plus an
exclusive lease for their component. They can coexist with each other; a second
prompt or memory process using a different state/socket path cannot open the same
data. The lease belongs to the actual Python process and covers accepted request
and worker drain. The Node maintenance transaction owns the exclusive counterpart.
Existing per-state locks are retained, including compatibility with cold stores
last opened by older releases. The upgrader must stop all old callers/companions
before adopting data; older releases do not understand the new lifetime fence.

Companion startup checks an unfinished migration before opening/creating data,
including the gap between adoption renames. Generated staging/backup directories
and raw source archives cannot run as companion roots. Persistent lock files are
private and kept in place. Both clients must use the same chosen state/data pair;
there is no automatic discovery, foreign socket adoption or port reassignment.
This contract adds no second agent owner or telemetry.

## Cold consolidation

`scripts/import-shared-profile.mjs` imports into an **existing initialized target**.
It preserves the source and target engine configuration, capture and processing
preferences. Stop both Harness callers and both companion pairs first. Create a
private manifest containing only local paths and explicit choices:

```json
{
  "schema": "augmentor-shared-profile-input/1",
  "source": {"state": "/private/source/shared-state", "data": "/private/source/shared-data"},
  "target": {"state": "/private/target/shared-state", "data": "/private/target/shared-data"},
  "sourceSha256": "REPLACE_WITH_INSPECTED_SHA256",
  "mapDefaultPerson": true
}
```

```sh
node scripts/import-shared-profile.mjs inspect /private/manifest.json
node scripts/import-shared-profile.mjs import /private/manifest.json
```

Inspection supplies the exact cold checksum. State and data must be private owned
real directories; target adoption currently requires a private owned parent and
is qualified only on MX Linux. Do not place the manifest or command output in a
public repository. The tool holds both original companion state locks and source
data ownership through the complete operation. The target uses the same flushed,
copy-on-write transaction, full target backup, external startup fence and explicit
verified finish/rollback as [native profile transfer](HARNESS-DSH-MIGRATION-PILOT.md#relocation-between-cold-harness-profiles--october-16).
For an interrupted operation, use `import-dsh-projects.mjs inspect`, `finish` or
`rollback` with the original **target data root**, not a native session state.

The exact source tree is hash-verified before and after the offline database
merge under `shared-imports/<source-sha256>/data`. The receipt and
`memory-sequences.json` sit beside it. No service, HTTP client, inference window
or model call is constructed by the merger. Target configuration and installer
ownership files stay byte-identical. This command neither migrates an external
Hindsight volume nor claims ownership of another installed engine. It does not
repoint launchers, restart apps, enable capture, resume processing or change ports.
Those are separate cutover actions after all callers stop and backups verify.

### Prompts

Identical shortcut names/text deduplicate to the target identity. Different text
with the same name is retained under the existing `-imported-N` convention. Unique
source IDs are preserved; an ID collision gets a deterministic replacement and a
receipt alias. Target prompt identities, improvement instructions and edits win.
Different source improvement instructions remain in the exact archived database
and are reported in the receipt; no alternative is silently selected.

Import ledgers retain deleted-source tombstones. Committed source request IDs
are retired in the shared service: a retry is refused with an explicit refresh
message, rather than replaying the old mutation or returning a source-only
snapshot as the current library. Target request receipts remain. Clients reopen
and reload after cutover. A clean selected Harness preview now updates on explicit
Refresh after a Native peer edit; unsaved/in-progress edits still retain their
local version and conflict guard. The original settings layout is preserved.

### Memory

Raw transcript event identity, text, role, modality, status, timestamps and digests
are preserved. Duplicate IDs must have identical content and bindings. Global
journal sequence numbers are translated in the private receipt; scope membership,
legacy projection/revision sources and local cursors follow that translation.
Skipped-capture tombstones cannot be overwritten by imported captured text.
Divergent bindings, unsupported schema/columns, incomplete SQLite journals,
nonmonotonic cursors and unknown data components refuse the entire unpublished
candidate. Existing target settings and engine ownership are not overwritten.

By default, source person identities and project partitions remain distinct.
`mapDefaultPerson: true` explicitly maps only the source default person to the
target default; other people remain separate. It is suitable for newly generated
review identities with no processed banks/jobs, as observed in the current reviews.
Processed identities require a separate bank migration before mapping. Processed
banks can be preserved under their original identity only with the same engine
destination/authentication and no conflicting scope/cache. This is not an
implementation of arbitrary cross-engine or merged-person memory migration.

Cached Hindsight facts/pages and original remote document IDs remain intact.
Processing job IDs, payloads, phases and budget charges retain their original
engine-facing identities, including original embedded transcript sequences.
Imported unfinished jobs become stopped receipts and require explicit review;
charges are never reset. Activity windows and unassigned source processing
eligibility are archived, not activated. Raw history remains available for the
existing explicit historical-interval processing action. Copying memory does not
start a backlog. Native chat histories themselves are not rewritten or resubmitted.

The transaction retains the four-GiB/100,000-entry snapshot bounds. Each database
is integrity checked and each table is limited to 100,000 rows, including the
combined result. Existing library limits stay at 1,000 prompts/500,000 text bytes.

## Qualification and adoption

Fixtures are independently authored. They use actual Python services, public Pi
SDK owners, Node/Native prompt clients and the original Chromium GUI. They cover
backups and exact source archives, conflicting/deleted shortcuts, retired writes,
raw memory/scopes/cursors, cached banks, charges/stopped jobs, changed/unknown
inputs, foreign engines and actual interrupted-adoption startup fencing.
Two Pi owners reopen on one shared service without old-history recapture and
continue only the explicitly submitted conversation. GUI/Native peer edits make
no model requests; existing dirty-editor conflict tests remain.

A controlled preceding sealed release admits two same-data owners through two
socket roots for **each** companion. Corrected source admits one, and each second
process exits before opening the database/socket. This is separate from live
Hindsight/Qwen acceptance or installed platform qualification.

Source and packaged results and any real review cutover are recorded below.
The original installed Agent/DSH stores, selected application, engine volumes,
model/GPU/audio settings and broader project migration remain separate.

Source build and **270/270 Node cases** across **54 files/16 actual Chromium
files** pass with two workers, no skips and unchanged deadlines. Python checks
pass **82/83**, with the existing actual-Windows-owner case explicitly skipped on
Linux. This includes common lease, prompt peers, memory/cache/budget, service
idle/startup and licence/private-source/notice contracts. The initial fixture
parent-permission refusal and disabled-capture source-read assertion remain in
private logs; they were corrected without relaxing the private-path/authorization
guards. The first GUI peer test reproduced the clean-preview Refresh bug, fixed
in the existing authored editor. Packaged-target and running-review evidence follows.

Private unselected MX **20261016-193501-a9131856**, application **0a1b7005**,
passes the same **270/270** cases against exact packaged modules and **82 Python
passes/one actual-Windows-owner skip** without site packages. The source and seal
also pass six focused runtime cases each, including one additional explicit
previously-admitted-queue carryover contract. All **24,602 sealed /
1,096 compiled** inputs verify after actual review GUI QA.
Production Node/dependencies/components and supplier sources/licences stay exact.
[Portable evidence](../release/harness-shared-profile-review-20261016.json).

### Running MX reviews

Both idle review owners now run this candidate at their existing profiles/ports,
using one shared companion pair. Guarded idle shutdown, confirmed companion
retirement and **389 verified regular backup files** precede consolidation.
All **four original conversations**, **32 cold/post-GUI protected inputs**,
target improvement instructions, capture/processing preferences and engine
configuration/installer identity verify. The unused original pilot data's **five
files** remain exact. Its complete checked archive and original target backup are
retained privately. The twelve prompt copies deduplicate into **12 shared prompts**;
all **19 captured records** retain their text, timestamps and event identities.
No additional DSH project or native conversation profile was transferred.

The generated pilot default person is explicitly mapped to the primary default;
no processed banks/jobs existed. After verifying the exact old eligibility and
sequence map, the operator explicitly carries **16 already-admitted source records**
through the existing `memory.dual.import` interval action. Together with the one
primary pending record there are **17 pending records**. Raw captured text is
unchanged; no activity window, processing job or inference request is created.
Only the verified previously-admitted subset is selected, not arbitrary historical
text. Unknown imported job outcomes remain stopped. This preserves the existing
queue's intent without inventing a new live processing window.

For an analogous reviewed carryover, select only source `memory_eligible` rows
whose job is null, verify their mapped target event digests/session bindings,
and submit exact per-session `memory.dual.import` intervals (at most 100 records
per call). Read back target eligibility after any uncertain response before further
calls. Never renew old activity owners or reset job budgets as part of migration.

Actual original-GUI checks open both libraries and memory pages, show twelve
prompts and nineteen records with processing enabled and no gateway conflict,
and report zero console/HTTP errors. They change no flags and send no model/audio
work. Initial private QA omitted the prompt modal's normal Escape/reopen route;
the corrected driver uses the existing controls without changing the UI.
The installed selection, original DSH/Agent data, GPU/model/audio configuration
and canonical local changes remain intact. Shared Native **client** parity is
qualified; installed Agent adoption/physical Qt use and broader project/OS rollout
remain separate. The engine's availability is still reported from actual runtime
state; this change does not claim a new live inference proof.
