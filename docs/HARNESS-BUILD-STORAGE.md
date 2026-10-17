<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# MX build storage and cleanup — October 17, 2026

The latest verified total is **79 unused copies removed / about 43.06 GiB recovered**,
with about **101 GiB free**. The October 18 follow-up retired one exact superseded
extra candidate after combined-artifact qualification, keeping the latest two
extras and all required apps/rollbacks. Scratch is empty. See [the current record](../release/harness-combined-client-package-20261018.json).

The October 17 checkpoint was **78 copies / 42.51 GiB**. The original cleanup below
accounts for 75 copies.
A follow-up removed three more unsealed app mirrors after checking their complete
inventories against retained, intact sealed releases. Two mirrors also contained
12 source files each; every extra byte matched the recorded Git commit before
deletion. The matching releases, Git history and small qualification records remain.
Exact live-process and persistent-launch reference checks found no use of these
three roots. Main/pilot PIDs, protected files, shared stores, menu selections and
GPU/service configuration passed before/after preservation checks.

Older unclassified application/source/runtime/output folders remain; some contain
nested test results or profile material. This is not a claim that every remaining
large folder is needed. Further deletion requires classifying those exact bytes,
preserving any unique data and identifying their current references. No historical
source checkout, project, conversation or needed backup was removed.

The owner-authorized cleanup removed **75 unused application copies**: the original
34 ordinary copies, six more ordinary copies and 35 obsolete staged releases.
Observed recovery was **40.89 GiB**. Root free space rose from about **58 GiB to
99 GiB**, and usage fell from **94% to 89%**. This session's repeated application
builds were a substantial contributor to the storage pressure.

Each removed root was checked for application-only provenance, owner-data exclusion,
live process/file/configuration references and current qualification dependencies.
Staged roots also passed manifest/source checks. The private exact-path receipts
remain operator evidence; public records contain aggregates only. Selected/running
apps, current reviews, source work, projects, histories, settings, shared stores,
model/GPU/voice services and required backups were preserved. Owner preservation
checks passed before and after both cleanup batches.

The remaining ambiguous older staged roots and source/runtime/cache directories
were retained. Their age or size alone does not establish that they are disposable.
This was targeted cleanup, not a sweep of the owner's home directory.

## Required development workflow

Run local app-copy/build qualification through:

```sh
python3 -B scripts/harness-build-workspace.py -- COMMAND ARGUMENTS
```

The command receives `AUGMENTOR_BUILD_WORKSPACE`. It must explicitly place its
throwaway app/test mirrors there. Keep only small logs, source hashes and receipts
outside that directory. The helper does not redirect arbitrary build output or
prevent another command from writing elsewhere; compliance with this workflow is
required. It takes a private Linux process lock, refuses concurrent or unreaped
work, and checks a **64 GiB reserve** before starting and during execution. Low
space stops only the process group it created and returns exit code 75.

On success, failure or handled cancellation it removes its own scratch directory.
Visible process/open-file or selected/rollback/review references cause retention
and block the next workspace. Inaccessible process metadata is not a guarantee
of universal visibility. A crash or power loss can leave work for inspection;
there is no startup blanket deletion. The helper never prunes arbitrary old roots.

Do not store owner data or select an installed release inside scratch. Publish a
sealed artifact only when actual package/installed qualification needs it. Retain
selected/running/needed rollback/registered artifacts plus at most the latest two
unselected candidates that are not otherwise required. Audit exact references
before removing older whole roots; preserve needed backup/history bytes.
Documentation-only updates need no new application copy.

## Qualification and resumed work

Nine authored Python cases pass: cleanup after success/failure, exit status/log
preservation, concurrency, unknown leftovers, path/permission refusal, reserve
refusal, live-reference retention, rollback retention and low-space process stop.
The actual default-reserve wrapper also ran the focused source validation without
creating a persistent app copy: **45 Node / 91 Python**, zero failures/skips, plus
`npm run check`. Later DSH delegation/environment changes passed their affected
**3 Node / 12 Python** cases again (overlapping those totals).

Source work resumed on explicit managed DSH launch binding. The opt-in wrapper
preserves the original command, arguments, cwd, PATH, PYTHONPATH, NODE_OPTIONS
privacy preload and custom service settings, while applying the selected shared
pair and recorded interpreters. Direct and desktop-delegated authored processes
hold the managed reader; an unmanaged idle DSH process blocks cold adoption.
Invalid commands refuse without logging private arguments or changing stores.
These are independently authored subprocess tests, not actual upstream backend
qualification. No owner service or installed bootstrap was changed.

The installed compatibility adapter's legacy `0.1.5-rc.1` response is synthesized;
it did **not** prove the loaded DSH backend version. The CLI on disk is
`0.2.0-rc.2`; the live modern `session/modelCatalog` and `pluginInventory/list`
routes succeed without a backend version field. The exact loaded backend version
remains unverified. Actual product integration **0.2.11** still refuses candidate
**0.2.13**. Subsequent current-source probes verify the catalogue/inventory/preset/settings
read contracts. Modern installer/CLI pins and preservation of custom composition/
metadata remain prerequisites before any owner cutover.
See [shared profiles](HARNESS-SHARED-PROFILES.md) and the
[aggregate record](../release/harness-build-storage-20261017.json).

The existing MX main and pilot remain available unchanged. Pilot feedback still
gates further project transfers. Voice and later platforms remain deferred.

## Resumed CI failure correction

The already-running hosted jobs were allowed to finish. Run 39035553761 ends with
2,143 root passes / one failure / 53 skips; run 39036728003 ends with 2,141 passes /
two failures / 53 skips. Both fail the actual supervised Office changed-source
case; the newer run also fails the Native inspector fixture's fixed-delay check.
Source-boundary, Home and component jobs pass. No whole workflow pass is claimed.

The supervised Office worker now rechecks the admitted source receipt if the
underlying renderer throws: concurrent truncation/replacement can make parsing
fail before the normal post-render receipt check. An unchanged source preserves
its original parser error. No output is published on either failure. The Native
inspection fixture now waits for its actual GUI callback before restoring the
session or checking the next invalid URL; the production navigation guard is
unchanged. All **11 affected Node cases** pass, including real Wasm rejection /
recovery and actual Pi/Qt inspection. This count is separate from the earlier
45-case launch/source focus. No owner inference, installation or app copy occurs.

## Follow-up verification after resumed source work

The exact-path deletion receipts were checked again: all original 34 and all 41
additional removed roots remain absent. Free space is **98.5 GiB** and the managed
scratch directory contains only its lease file. Subsequent progress/thinking and
backup-coverage source qualification created no full application mirror or sealed
release. The full Linux SDK succeeds at workflow 222ae6e9 / runtime 889ad6cb; see
[the qualification record](../release/harness-progress-cut-map-20261017.json).
Older unclassified output/release/cache trees are still retained pending exact
provenance and reference checks; this verification does not claim all remaining
large directories are needed or that all duplicate storage has been eliminated.
