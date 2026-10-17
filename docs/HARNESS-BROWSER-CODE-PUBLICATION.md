<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Browser code in the MX client transaction

`services/dsh/browser_code_publication.py` binds the existing unpacked extension
code folder to [client publication](HARNESS-CLIENT-PUBLICATION.md) **schema 4**.
This internal Linux controller changes no UI. It does not stop Chromium, reload
an extension, move browser profile/storage, start clients or prove owner acceptance.
The installed Browser remains 0.2.11 until an actual coordinated cut and reload.
macOS and Windows adapters remain unqualified and deferred under the MX-first plan.

## Prepare before configuration fences

Use the reviewed source controller outside the application's archived release-store
parent. The immutable application supplier remains **4f83b7e8**, artifact
**535ad8e607de7fbd3f4aea707882a94a1ad8a2ba25ad7ebcd19f906137b4f1be**.
Its packaged controller predates schema 4; use the current source controller for
this operation, and the sealed supplier for application bytes and startup rendering.
Do not patch that seal or build another whole app for a controller-only change.
The [qualification record](../release/harness-browser-code-publication-20261018.json)
records the exact controller revision separately from the application revision.

After preserving accepted work and quiescing **every** actual browser/Native/review,
embedded, registered-workspace and DSH companion caller:

1. Hold `client_publication.maintenance` for every deployment, shared pair and
   registered review. Capture one fresh complete cold archive, including the
   **whole existing extension code folder**, every covered selector and all data.
2. Prepare shared-data adoption from that archive. Prepare Browser code with
   `browser_code_publication.prepare(target, incoming, artifact_sha, recovery,
   cold_backup, guard.configuration)` before configuration preparation writes fences.
3. Prepare configuration with the same archive, then call client publication's
   `prepare(..., shared_adoption={root, sha256}, browser_code={root, sha256}, ...)`.
   The Browser reference uses `browserCodeSha256` returned by its preparation.
   Registry revision/names, previous pairs and reviewed bootstrap expectations
   remain mandatory where applicable. Explicit archived Browser code below the
   primary deployment's `browser` directory cannot silently be omitted.
4. Apply and finalize through the matching client publication only. Ordinary
   reopen, loaded extension/Native-host handshake and owner continuation follow
   separately. Disk manifest/version checks alone do not prove loaded code.

Preparation leaves live code untouched. The target must be an explicit existing
canonical direct child of the primary deployment's `browser` directory; both
root and parent must be owned protected directories. The current real parent
still has mode **0775** and needs only group-write removal before actual
preparation, with its original mode recorded. That change was not made by this
checkpoint. Browser profile data must never be put in this code folder.

Recovery must be private persistent storage on the **same filesystem**, outside
source, application, profile/data and archive roots. Known disposable build scratch
is rejected for owner recovery; all synthetic fixture roots can share the managed
workspace. One small incoming code slot is staged, not a full app or a new copy of
old extension bytes. The cold archive already covers the old code. Inspect any
failed unpublished stage before retrying; never accumulate abandoned attempts.

## Bounds, identity and recovery

Preparation verifies the complete incoming application seal and current archive,
then checks MV3 version, the existing extension key and exactly unchanged required
and optional permission sets. Permission expansion needs a separately reviewed
update. Inventory permits only owned ordinary directories and single-link regular
files: no links, sockets, devices or special modes. Bounds are **2,048 entries /
32 MiB total / 8 MiB per file**, 512-byte relative paths, 255-byte names and a
64 KiB manifest. The real **64 GiB reserve** applies before and during copying.

Fingerprints bind every path, file byte and ordinary mode. Legacy group-writable
files can be preserved exactly; incoming group/other write bits are removed while
the protected original root mode is retained. The journal also binds both directory
inodes, parent identity, supplier, archive, original selector and every guarded pair.
Changes to live code or either recovery slot refuse without overwriting them.

Only the matching publication owns mutation. Apply exchanges the complete code
root and slot with Linux `renameat2(RENAME_EXCHANGE)` after configuration/data and
before bootstrap, backend/Native preflights and build selectors. Both parents are
fsynced. After a real process death, before/after directory identities determine
whether the exchange already happened; resume never blindly exchanges it again.
Before durable finalizing intent, reverse restores exact old code inode, bytes and
modes along with the shared data, registry and selectors. Browser storage stays
outside the exchange.

Durable finalizing intent releases data and Browser code **before** startup fences
are removed. Thereafter recovery finishes forward, without replaying data/code
application or reversing newly created work. Old recovery code remains retained;
it is not permission to reverse an already reopened store. A fresh reviewed cold
cut is required for any later downgrade. Prior schema-3 publication journals
require their matching historical controller; never relabel their schema.

## October 18 qualification and remaining installation

**167 Python checks pass** with zero failures/skips under the managed 64 GiB
workspace and read-only host/network isolation. The 23 new Browser cases include
real child exits after forward/reverse exchanges, release/fence gaps, exact reverse,
shared data plus registered reviews and an explicit partial third source,
foreign edit/inode/archive refusal, required Browser binding and persistent
recovery. Fixtures use authored extension code and real SQLite; backend health
replies are synthetic. Earlier 77- and 165-case runs overlap, not additional totals.
The first focused run exposed an absent ownership-marker error; it was corrected
before these passes. Hosted results for this new controller are pending.

Read-only checks against actual installed/incoming code pass inventory and unchanged
key/permissions: **55 files / 527,093 bytes** to **67 files / 618,936 bytes**, versions
0.2.11 to 0.2.13. No owner preparation, code exchange, browser reload, cold archive,
activation, migration, service stop or model request occurred. Running Native/review
PIDs/builds, 36 protected files, shared rows/engine, registry 20, selectors, menus,
shortcuts and GPU/voice/service state verify unchanged. No app copy or release was
created; scratch was removed and about 101 GiB remains free.

Remaining: coordinate Chromium exit/reload; preserve accepted work while quiescing
all callers; prepare the protected parent; capture once; bind data, Browser,
configuration, reviews and clients; apply/finalize; reopen normally and verify the
owner can continue the pilot. More transfers need pilot feedback; VR-RasterStudio
stays in DSH. Voice expansion and later operating systems remain deferred.
