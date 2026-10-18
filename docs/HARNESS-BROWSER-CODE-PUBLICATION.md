<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Browser code in the MX client transaction

`services/dsh/browser_code_publication.py` binds the existing unpacked extension
code folder to [client publication](HARNESS-CLIENT-PUBLICATION.md) **schema 4**.
Runtime/controller **5d67a8bfe45dd2d632a716b7854fd9860e08dd0b**. This internal Linux controller changes no UI. It does not stop Chromium, reload
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
root and parent must be owned protected directories. The initial real parent
had mode **0775**; the later prerequisite preparation below removed only group
write, recording the original mode before changing it to **0755**. Browser profile
data must never be put in this code folder.

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
all callers; capture once; bind data, Browser,
configuration, reviews and clients; apply/finalize; reopen normally and verify the
owner can continue the pilot. More transfers need pilot feedback; VR-RasterStudio
stays in DSH. Voice expansion and later operating systems remain deferred.

## Current owner readiness — October 18

[Read-only preparation](../release/harness-mx-current-cut-preparation-20261018.json)
revalidates the existing **48-input / ten-edit** configuration stage and renders
**32 startup/registration images**. Only the review registry content changes,
prospectively **20 to 21**; the installed helpers already match. Every exact
before-hash, prospective selector and renderer must be recomputed/compared under
the actual cold guard. This advisory plan is not permission to skip that guard.

Three ordinary Native windows and both registered reviews are currently idle;
the read-only DSH list explicitly reports no running sessions, and the registered
workspace has no queued/running/dispatching jobs. The older Native
`harness-preview` instance has an **unsent draft** and refuses safe shutdown. It
was left untouched; the owner has been asked to save/finish it and close that
window. Chromium exit/reload coordination also remains. Other older live reviews
use separate stores outside this cut; their data and processes were preserved.

[SDK run 39079128742](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/39079128742)
at source **16ba7d09** has passed the affected Linux publication/recovery step;
the full Linux job is still running at this snapshot. Mac failed the shared-memory
fixture step (cause unqualified), Windows is still running; no whole-matrix pass
is claimed. No owner file, selector, data, model, maintenance reservation, stop,
restart, archive or application copy was created by this live preparation.

## Protected parent and full Linux results — October 18

The [follow-up record](../release/harness-mx-current-cut-preparation-20261018.json)
records the actual Browser parent prerequisite: **0775→0755**, only group write
removed. Original device/inode/mode/ownership were durably recorded first; owner
access and group read/execute remain. No other local group account or access/default
ACL was observed. The initial secondary evidence-copy write refused before any
mode change; recovery resumed from its protected receipt without creating another
recovery root. Browser code inventory, registry and selection bytes remain exact.
Full Native/review PIDs/builds, 36 protected files, shared rows/engine, menus,
shortcuts and GPU/voice/services reverify unchanged. No stop, model call, data
migration, full app copy or release artifact was created.

Full Linux SDK succeeds at both source **16ba7d09**
([39079128742](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/39079128742/job/117532312384))
and documentation follow-up **c74ab11a**
([39079523341](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/39079523341/job/117533451291)).
Controller **5d67a8bf** hashes remain exact; application **4f83b7e8** remains the
unchanged supplier. Mac shared-memory fixture failure remains unqualified; this
is no whole-matrix or later-OS approval. A controlled isolated Linux probe
reproduces unavailable memory status with a 112-byte socket and success with a
56-byte socket, but the historical failing Mac root length was not observed.

The older `harness-preview` still reports an unsent draft and refuses safe shutdown.
The owner save/finish/close question remains unanswered; Chromium coordination
also remains. Do not close it forcibly, overwrite or extract its in-memory draft,
or prepare repeated owner snapshots while waiting. All remaining installation
work needs this client quiesced, a fresh complete cold cut, ordinary reopening and
owner continuation. No completion is claimed. More project transfers, voice
expansion and later operating systems remain deferred.

## Owner resumes swap and requests normal browser opening

The owner explicitly authorized closing the old preview despite its draft and
proceeding with the swap. That historical blocker is resolved. The new
[browser opening correction](HARNESS-BROWSER-OPENING.md) changes runtime/GUI bytes
and needs one newly qualified immutable candidate; the previous 4f83 supplier is
retained as recovery until that candidate qualifies. Recompute the actual cold
plan with the new artifact rather than reusing the earlier supplier receipt.
