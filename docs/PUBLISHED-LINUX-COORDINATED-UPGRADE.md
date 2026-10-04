<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Published Linux product upgrade and rollback qualification

The [actual baseline160 checkpoint](../release/qualification/next-targets/20261004-published-managed-baseline-acceptance.json)
records normal published 0.2.12 staging and activation into a managed release.
The worker exited successfully in 11.186 seconds. The independent ending audit
passed native package checks, idle exclusive leases, process/socket absence,
all three histories and their compressed byte/metadata snapshots, and the four
unrelated settings. No model requests ran. This preserves a managed 0.2.12
predecessor before a native package upgrade replaces `/usr/lib/augmentor`.
It does not qualify a product upgrade or rollback.

`release/prove-published-linux-coordinated-version.py upgrade|rollback` is a
source-only candidate. Neither mode has executed. It uses the reviewed cold
Page, baseline lifecycle and published legacy-companion helpers. It does not
run package operations, reinstall the DSH runtime, create chats or send prompts.
The historical published 0.2.12 and 0.2.13 payloads remain unchanged.

The root coordinator must finish and audit each native transaction while no
ordinary worker, DSH or companion holds a shared native lease. The candidate
then acquires both native shared leases for its entire lifetime, rechecks the
registered versions and package bytes, and requires the exact published native
source and Setup hashes. An ending root audit is required after the worker exits;
a successful ordinary worker alone does not qualify the coordinated transaction.

For upgrade, the reviewed root APT plan is two Augmentor 0.2.12→0.2.13 upgrades
plus nine declared new Qt/PySide/QML packages, with no removals or unrelated
updates. The ordinary worker stages native 0.2.13 through the normal updater,
calls normal `Setup.check` and **explicitly calls `Setup.install` once**, restarts
only its own DSH process, checks and saves the matching product connection, then
normally activates the verified managed candidate. Published 0.2.13's check can
report installed for stale copied 0.2.12 ownership; it cannot justify skipping
installation. The maintained check correction is separate from these historical
payloads.

For rollback, root first performs the reviewed normal two-package downgrade
after the upgrade worker and its owned children exit. The new ordinary 0.2.12
worker normally installs 0.2.12 integration into the same DSH home, restarts its
own DSH process, checks and saves matching 0.2.12, and only then invokes the normal
updater rollback to the exact managed predecessor. The nine added OS dependencies
stay separately recorded; this proof does not run autoremove or roll back other
OS packages. Pointer rollback alone is not a coherent product rollback.

Each mode requires a new immutable root-owned binding at
`/opt/augmentor-version-proof150/coordinated161/{mode}-binding.json`, with immutable
root-owned ancestors. Its format is `augmentor-published-coordinated-binding/1`.
It binds mode, exact worker SHA, creation time (at most 300 seconds old), the
actual baseline160 run SHA and successful ending-audit SHA, native-audit receipt
SHA, expected incoming five setting hashes, and the separate native transaction's
known version/source and idle lease/process/socket/port status. Rollback also
binds the exact successful upgrade run SHA. Root must derive those fields from
actual retained receipts after the guarded native transaction. A binding is not
permission to replay a pending action or adopt another run.

The binding's `nativeAudit` object uses `status: "pass"`, the exact native
`version` and public `source`, `pending: null`, `unknownOutcome: false`, and
`leasesIdle`, `processesAbsent`, `socketAbsent` and `portsIdle` all true. Its
`packageTransaction` object requires `phase: "pass"`, `exitCode: 0`,
`pending: null`, `unknownOutcome: false`, `receiptSha256` identifying the actual
normal APT result receipt, and `versions` mapping both `augmentor-runtime` and
`augmentor-desktop` to the target version. `removedPackages` is empty and
`unrelatedPackageChanges` is false. Upgrade `addedDependencies` contains exactly
`libqt6quickwidgets6`, `python3-pyside6.qtopengl`, `python3-pyside6.qtqml`,
`python3-pyside6.qtquick`, `python3-pyside6.qtquickwidgets`, `qml6-module-qtqml`,
`qml6-module-qtqml-models`, `qml6-module-qtqml-workerscript` and
`qml6-module-qtquick`. Rollback adds no dependencies. Root retains the signed
metadata, reviewed dry-run, exact package hashes, actual native result and
complete OS version comparison in the receipt referenced by that binding.

The fixed fresh journals are `published-product-coordinated-upgrade161` and
`published-product-coordinated-rollback161` under the synthetic user's state
directory. Existing directories refuse. Install/save and updater dispatch have
durable one-shot pending intents. An exception keeps an unknown action pending;
the first failure is terminal, with no retry or automatic rollback. The reviewed
60-second authenticated startup bound remains unchanged.

Acceptance requires Page-only equality for the three known dense histories,
unchanged compressed session files and metadata, zero model POSTs, preserved
historical journals, and normal owned DSH/companion cleanup. Only desktop selection
and the saved DSH version can migrate. Provider YAML, installer receipt, model
environment, endpoint/home, managed service description, product token and all
unrelated saved keys remain exact. Unknown connection fields that historical save
would discard refuse before installation. Existing foreign profile files,
foreign presets and composition text remain unchanged. The normal integration
backups must contain the old owned target, presets and patch; unexpected backup
members or edited owned content refuse. No private installed overlay or settings
normalization is allowed.

Before either actual mode, review and publish the candidate, derive its exact
root binding, repeat host/container identity and storage floors, and retain the
normal signed APT dry-run and transaction receipts. After each mode, independently
audit native versions/bytes, idle exclusive leases, no owned descendants/socket/
listeners, exact current and previous managed inventories, profile backup and
foreign-content preservation, settings and all histories. This container proof
is separate from graphical, audio, hardware and broad distribution acceptance.
