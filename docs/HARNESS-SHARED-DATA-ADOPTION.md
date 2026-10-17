<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Cold adoption into the existing common store

`services/dsh/shared_data_adoption.py` prepares the approved prompt/memory merge
without replacing the production folder that also holds application releases,
selectors and other settings. The existing canonical store, person/bank identity,
prompt-improvement instructions, capture/processing settings and engine configuration
remain authoritative. This is an internal Linux API, not a new GUI or an installed
owner migration. The main/pilot, loaded clients and owner projects remain unchanged.

## Explicit sources and complete backup

One operation accepts one to four dedicated source pairs and one existing canonical
target. Hold every source/target companion gate and every declared deployment
writer through `client_publication.maintenance`. The first pair is the existing
canonical target; its three databases remain mandatory. Sources must be distinct,
non-overlapping, owned and private. No automatic home-directory discovery occurs.

The real caller audit found another older Native preview store beyond the review
and production stores. It contains only automatic memory. Declare such a secondary
pair explicitly in `partial_pairs`; ordinary launch/selection and the primary
store still require all three databases. An undeclared missing database refuses.
No placeholder database is created in a partial source. Its existing components
are schema/integrity checked and imported; the receipt marks absent components.
A read-only advisory check confirms that actual legacy database's schema and
unchanged bytes. It is not a cold checkpoint or owner migration.

Cold archive **schema 2** records `partialSharedProfiles`. Named component coverage
includes existing databases and records the other names as optional; creation of
a previously absent file invalidates the original cut. Capture every dedicated
source data tree explicitly, including nested `shared-imports`, as additional
whole-tree coverage. Existing canonical import history also needs explicit backup
coverage. All other Native/Harness project, state and registration coverage still
requires the actual operator's reviewed map. The earlier two-pair map is incomplete
for this graph. Older schema-1 archives require their matching historical operator;
do not relabel them or use them to authorize this source checkpoint.

Prepare in this order under the same cold guard:

1. Capture the full reviewed cold archive.
2. Call `shared_data_adoption.prepare(sources, recovery_root, cold_backup,
   guard.configuration, map_default_person=...)`. Choose the mapping explicitly;
   processed source banks/jobs still require the existing explicit bank migration.
3. Prepare the matching configuration with the same cold archive.
4. Prepare client publication with `shared_adoption={root, sha256}`. A deployment
   changing shared pairs must have its previous source in this bound adoption.
   Legacy additional selectors without `sharedProfile` require `previous_pairs`.

Use protected, persistent recovery storage on the target filesystem for actual
owner images; never disposable build scratch. Authored test profiles use the
managed workspace. Preparation copies only the target's three databases and
optional engine JSON plus complete source archives. It uses the existing pure
`companion_import` merger, without service/model/engine objects or calls. The
actual 64 GiB reserve applies before copying and during preparation. Planned
capacity includes source archives and component growth. Metadata is bounded to
four MiB; source inventories retain the runtime's 100,000-entry/four-GiB bound.
An unsuccessful unpublished stage is retained for explicit inspection; do not
create repeated attempts without inspecting and retiring that stage.

## Component publication and recovery

The immutable journal binds the archive, original selection, all guarded pairs,
each complete source inventory, exact before/after DB bytes and modes, unchanged
engine files, merge receipts and the canonical root's device/inode. Source
inventory hashes agree with the existing runtime `stateInventory`, including
UTF-16 filename ordering, Unicode and nested history.

Client publication **schema 2** owns both configuration and data journals. The
data API refuses standalone mutations. Configuration is applied, the three
database slots are exchanged with Linux `renameat2(RENAME_EXCHANGE)`, source
archives are published without replacement, then bootstrap/preflight/selections
complete. No mixed application directory is renamed. Every intermediate state
must match the known before/after slot pair; a changed DB, source, archive,
engine file or recovery image stops without overwriting it. The verified archive
is cached only within that guard while all three archive-file identities/stamps
remain unchanged; later edits invalidate the cache.

If canonical import history is absent, its complete new parent is published in
one no-replace rename. If it already exists, only the new cut directories move.
Multiple-source publication can resume between these moves. Existing history
is preserved. Identical/already imported cuts and conflicting transcript/request
identities refuse; no old request, tool action or memory processing is replayed.
Unassigned source eligibility and activity windows remain archived, inactive.

Before finalizing intent, reverse exchanges the exact original components back,
moves only its own new archives back into recovery, and reverses bootstrap,
configuration and selectors. It does not overwrite an unknown edit. Source
profiles, their raw history and the cold archive remain intact.

Durable client finalizing intent precedes data release and removal of startup
fences. After that boundary, recovery finishes forward without reapplying old
DB images. Released verification checks the original recovery slots and retained
import history, while permitting new ordinary database work. Automatic old-cut
reverse is refused. Any later rollback needs a fresh reviewed cold cut that
preserves new work. Client publication still reports ordinary-client startup and
owner continuation separately; neither is established by a successful journal.

## Qualification and remaining adoption

The authored integration fixtures exercise real SQLite schemas and the public
offline merger, including a full review source plus a partial legacy Native source.
They cover actual child exits after all three component exchanges, archive moves
and every startup-marker removal; partial multi-source forward/reverse; exact
original restoration; immutable source/nested history; existing target history;
foreign edits; missing full-source coverage; reserve refusal; ownership gaps;
explicit partial sources; and post-reopen work preserved during finalization.
Publication backend health replies are synthetic. The separate backend-probe suite
retains its real namespace/transport tests. No owner model call or data migration
is implied by authored fixture success.

One combined immutable artifact still needs qualification against the retained
integration, followed by exact launcher/registration adoption, the complete real
three-pair cold cut, matching loaded Browser, controlled apply/finalize and actual
owner continuation. Further projects remain gated on pilot feedback;
VR-RasterStudio stays DSH. Voice expansion and later OS remain deferred.

See [client publication](HARNESS-CLIENT-PUBLICATION.md),
[build storage](HARNESS-BUILD-STORAGE.md) and
[the qualification record](../release/harness-shared-data-adoption-20261017.json).
