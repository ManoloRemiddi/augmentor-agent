<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

## October 4 coherent rollback and published save compatibility

[The current fixture checkpoint](../release/qualification/next-targets/20261004-native-upgrade-desktop-ending-checkpoint.json)
records successful native and ordinary 0.2.12→0.2.13 upgrade and native rollback.
The first ordinary rollback installed matching 0.2.12 integration, then refused
before entering `Setup.save`: published 0.2.12 accepts a token alone. The failed
record remains unchanged. A separately reviewed continuation used one fresh
checked token, one token-only save and normal `augmentor-update rollback`, with
no repeated integration install, staging or native transaction. Independent
ending checks pass native/integration/settings/selected 0.2.12 and previous
0.2.13, complete managed inventories, all three histories and foreign aliases.
Zero model requests occurred. The historical SDK restart changed only the
measured composition-file modification time; continuation checks preserved its
bytes and stable identity, and every other integration field.

The maintained fresh-HOME proof now selects the hash-qualified save arguments
before allocating its worker journal, starting the SDK or installing integration:
0.2.12 receives only the token; 0.2.13 receives the managed keyword. A 0.2.12
connection containing any `managed` key, including null, refuses because that
published save method would drop it. Unknown versions and connection fields also
refuse. There is no TypeError fallback or retry. Future immutable authority and
journals use scope195, preserving sealed184. All27 fresh and27 unchanged
historical coordinator tests pass. Scope195 itself has not run; the current
fixture round trip includes the separately recorded continuation.

## October 4 earlier native upgrade and executable cache correction

The fresh ext4 HOME fixture completed one normal native 0.2.12→0.2.13
transaction in 32.03 seconds: exactly two Augmentor packages and the nine
authenticated dependencies, with no removals or unrelated updates. Native and
managed inventories, settings, histories and all 255 foreign alias rows passed
the independent ending audit. Ordinary integration then passed in15.83seconds:
matching013 installation and selection, preserved histories/settings/cache aliases
and zero model requests. Complete rollback remains open.

The ordinary integration attempt then refused a legitimate pnpm executable
cache alias before allocating its worker journal or starting the SDK. Its
original conservative unknown outcome remains retained; the independent ending
audit passed. [pnpm's upstream path implementation](https://github.com/pnpm/pnpm/blob/bac8077715ac5af3857b1df970a014875d89b86c/pnpm11/store/cafs/src/getFilePathInCafs.ts)
adds `-exec` when a file has executable permission. The new entry accepts only
that optional exact suffix and requires executable permission, while preserving
every pinned byte, timestamp and closed hardlink-group check. A new immutable
root authority and new journals use scope184; old174 inputs and failed receipts
remain untouched. Disposable real-hardlink tests cover valid executable aliases,
nonexecutable suffix rejection and invalid suffix rejection.

## October 4 staged integration filesystem failure

[The fresh integration-only run](../release/qualification/next-targets/20261004-published-staged-integration-filesystem-failure.json)
found the exact installed DSH command and reverified the existing staged013
inventory, then failed during normal integration installation in 9.43 seconds.
Renaming the existing profile to its sibling backup raised EXDEV; restoration
then attempted the nonexistent backup and raised FileNotFoundError. The install
intent remains pending/unknown. Save and managed activation did not run; no
package operation, staging replay, model request or retry occurred. Normal owned
cleanup and an independent native/idle audit passed. Settings, histories, prior
journals, managed inventories, selectors, native maps and token match their
before-state. Profile content remains preserved, but a temporary stage persists
and the composition file modification time changed. Full integration and rollback
remain open; investigate the maintained installer's filesystem/error handling
before a fresh qualification scope. Historical published payloads remain unchanged.

# Published Linux product upgrade and rollback qualification

The [actual baseline160 checkpoint](../release/qualification/next-targets/20261004-published-managed-baseline-acceptance.json)
records normal published 0.2.12 staging and activation into a managed release.
The worker exited successfully in 11.186 seconds. The independent ending audit
passed native package checks, idle exclusive leases, process/socket absence,
all three histories and their compressed byte/metadata snapshots, and the four
unrelated settings. No model requests ran. This preserves a managed 0.2.12
predecessor before a native package upgrade replaces `/usr/lib/augmentor`.
It does not qualify a product upgrade or rollback.

The [actual native-upgrade checkpoint](../release/qualification/next-targets/20261004-published-native-upgrade-integration-failure.json)
records one successful normal native 0.2.12→0.2.13 transaction in 24.42 seconds:
the two Augmentor packages and exactly nine declared dependencies changed. Signed
metadata and ordinary-user state remain unchanged. A verification omission of
Debian’s valid `Multi-Arch: no` value stopped the coordinator after that known
transaction; it was corrected without repeating APT.

The ordinary upgrade worker then staged and verified 0.2.13, but `Setup.check`
refused because its restricted PATH omitted the installed DSH command. Installation,
connection save and managed activation did not run. The worker exited in 11.06
seconds with all four pending fields null, `unknownOutcome: false`, unchanged
settings, preserved histories and historical journals, and normal owned cleanup.
The independent ending audit passed native013, idle leases, process/socket/port
absence and state preservation. The root coordinator’s conservative unknown flag
remains in its original failure receipt; the actual worker establishes this known
pre-installation failure separately. No rollback has run. The failed namespace
must not be replayed: continuing requires a fresh integration-only scope bound to
the existing verified stage and exact installed command.

`release/prove-published-linux-coordinated-version.py upgrade|rollback` uses the
reviewed cold Page, baseline lifecycle and published legacy-companion helpers. It does not
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

The first root read-only admission refused existing foreign `node_modules`
hardlinks before source staging, packages or worker execution. A separate
metadata-only inspection found 128 regular files: 126 with two links and two
with three links, all UID/GID 1000, with mode 0600 except one mode 0755 program.
They belong to seven foreign dependency roots: `ws`, `schemastery`, `cosmokit`,
`@standard-schema/spec`, `dsh-resonant-voice`, `dsh-adaptive-reasoning` and
`dsh-model-picker-augmented`. That refusal remains retained. The separately
reviewed exact hardlink admission preceded the actual native transaction and failed ordinary upgrade above.

The candidate can read hardlinks only under those exact foreign dependency
prefixes, with the observed owner, group, link-count and mode constraints. It
records `sha256`, `bytes`, `uid`, `gid`, `mode`, `mtimeNs`, `device`, `inode` and
`nlink`. An immutable binding's `foreignHardlinks` map must equal every observed
hardlink row before journalling and in subsequent integration snapshots. Root
must derive that map from a fresh successful read-only profile audit and retain
its equality across pre/post-native and ending audits. Descriptor identity and
path identity must remain stable during each bounded read. No aliases, caches,
ownership or permissions are changed. Generic owned integration, preset and
historical-journal snapshots continue to refuse hardlinks. These are read-time
and checkpoint comparisons; they do not enumerate every external alias or
promise continuous monitoring between checkpoints.

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

Before any new actual scope, review and publish the candidate, derive its exact
root binding, repeat host/container identity and storage floors, and retain the
normal signed APT dry-run and transaction receipts. After each mode, independently
audit native versions/bytes, idle exclusive leases, no owned descendants/socket/
listeners, exact current and previous managed inventories, profile backup and
foreign-content preservation, settings and all histories. This container proof
is separate from graphical, audio, hardware and broad distribution acceptance.

## Fresh integration163 worker and actual failure

The maintained coordinator now admits only the existing checked npm DSH shim
under the synthetic account's `dsh-runtime/node_modules/.bin`, then adds that
directory to its clean PATH ahead of native Node and the system commands. The
observed `.local/bin/dsh` is absent. The exact npm link, executable target and
supported package content are checked through bounded stable reads; caller paths,
different link text, foreign owners, hardlinks and changed contents refuse. No
command or runtime is installed to correct the proof's PATH omission.

`release/prove-published-linux-staged-integration.py` is the separately reviewed
fresh integration worker executed in the failed checkpoint above. It pins the
reviewed coordinator and selects a finite
integration-only branch. It requires a new immutable root binding at
`/opt/augmentor-version-proof150/integration163/binding.json` and exclusively
creates `published-product-staged-integration163`; failed161 is never resumed.
No APT or updater-stage dispatch occurs in this branch. The pinned normal verifier
must return the complete retained staged013 deployment, file inventory and
artifact identity before any owned process starts, and again before installation.
The retained manifest is4,232,400bytes. Only that exact historical file receives
a stable8MiB read allowance with its fixed size/hash; generic profile and owned
proof members retain their4MiB limit. The new journal writes a compact reuse
receipt pointing to the preserved manifest, rather than duplicating its inventory.

The format is `augmentor-published-staged-integration-binding/1`, mode
`upgrade-after-known-stage`. Alongside the unchanged baseline/native/settings/
foreign-hardlink fields, root binds `proofSha256`, `coordinatorSha256`, a unique
64-hex `runToken`, `createdAt` within300seconds, `priorFailedRunSha256`,
`priorRootBindingSha256`, `stageVerifiedSha256`, `readOnly162bSha256`,
`originalHostFailureSha256`, `priorIndependentEndingAuditSha256`,
`stagedDeployment`, `expectedCurrentSelectorSha256`,
`expectedPreviousSelectorSha256` and `dshCli`. The last object contains exact
`shim`, `target` and `package` rows from `verified_dsh_path`: path, owner/group,
mode, device/inode, link count, size, modification/change times, target/package
hashes and the shim's literal link text. The package transaction identifies the
original known successful APT result; a fresh full root native/ordinary-state
audit is required, without repeating that transaction.

Admission separately checks the exact guest failed161 receipt: only successful
stage occurred, all four pending fields are null, no integration action completed,
settings/history are unchanged, requests are zero and both owned children exited
normally. The conservative original host unknown flag remains preserved; it is
not rewritten or treated as the guest's known pending state. The first read-only
inventory's metadata comparison refusal also remains separate from the successful
second bounded read-only inventory.

The new branch uses normal `Setup.check`, one explicit `Setup.install`, normal
owned restart, check/save, and activation of the existing stage. Durable pending
intents, no unknown-action replay,60-second authenticated starts, Page-only dense
history equality, provider/token/foreign-content preservation and normal cleanup
remain unchanged. Historical161 files are included in ending preservation checks.
An independent full root ending audit remains mandatory. The actual run failed at installation
and does not qualify upgrade or rollback; a later rollback needs its own
reviewed binding to an actually successful new integration outcome.

## October 4 fresh ext4 baseline and separate source candidate

A separate ordinary home on an owned ext4 volume now has an actual successful
published 0.2.12 managed adoption: the unchanged managed worker exited successfully
in 10.16 seconds, with zero model requests and all three Page histories and their
compressed snapshots preserved. The initial ending scanner refused its old
40,000-member limit; that refusal remains retained. A separate bounded read-only
ending audit checked the actual 63,620-member home, full native and managed
inventories, idle processes/sockets/ports/leases, the retained journals and all
127 closed foreign hardlink groups. Its reviewed aggregate receipt identifies
actual run `d8819753…`, managed artifact `9cda9c48…` and ending receipt
`cc83cccd…`. This qualifies the fresh baseline, not an upgrade or rollback.

The current entrypoint is
[`release/prove-published-linux-freshhome-coordinated.py`](../release/prove-published-linux-freshhome-coordinated.py),
with explicit `upgrade` and `rollback` modes. It leaves the executed historical
coordinator byte-identical and imports only its hash-pinned preservation and
normal action helpers. It never calls the historical default or staged-failure
entrypoints, substitutes their constants, or adopts the old container's pending
integration. The native transaction described above passed independently;
integration passed as described above; complete rollback remains open.

Root authority is separate under `/opt/augmentor-freshhome-coordinated184/`:
`admission.json`, the exact genuine `baseline-ending.json`, and a fresh
`upgrade-binding.json` or `rollback-binding.json`. Every file and ancestor must
be root-owned, nonlinked and unwritable by the ordinary user. Input reads are
bounded and descriptor/path identity checked before and after reading. Reviewed
helper bytes are checked before import; the worker holds both normal native
shared leases before package audits through normal child cleanup and exit.

Admission format `augmentor-published-freshhome-admission/1` identifies the actual
fresh container/image, named ext4 home volume, fresh root marker, seed/export
receipts, baseline run, complete selected012 object and exact current/original
selector hashes, reviewed whole-home delta and genuine aggregate ending receipt.
`foreignHomeAliasGroups` binds the actual 127 groups/255 paths by a fixed topology
hash. `foreignHomeAliasRows` binds each path's SHA, bytes, UID/GID, mode, device,
inode, link count, modification time and actual change time. Only the seven existing foreign profile
dependency prefixes and their exact closed pnpm cache aliases can be read; no
cache scan or modification occurs. All 255 paths are reread at entry and ending
with stable descriptor/path identity, including change time during each read.
`historicalJournals` binds the exact snapshots of the three retained history
journals and the genuinely new managed baseline journal.

Phase binding format `augmentor-published-freshhome-coordinated-binding/1` adds
`admissionSha256`, `coordinatorSha256`, the new `proofSha256` and unique 64-hex
`runToken`. It retains the same 300-second age, native audit and separately known
APT transaction predicates, exact five `settingsBefore` hashes, profile
`foreignHardlinks` rows and `dshCli` topology. Rollback additionally binds an
actually successful upgrade run produced by this same new entry and admission,
with a different token. The two new journals are
`published-product-freshhome-coordinated-{upgrade,rollback}184`; preexisting
folders refuse. Normal stage/install/restart/check/save/activate or rollback is
still once-only and durably journalled; an unknown outcome is terminal.

Normal SDK startup in the actual fresh baseline changed only the timestamps of
`profiles/web/cordis.yml`. The explicit fresh-only predicate permits that known
mtime/ctime movement while stable SHA/bytes/UID/GID/mode/device/inode/link count
remain exact. All other foreign profile rows, owned backups, preset content,
provider/token/settings preservation, Page histories and no-replay rules retain
the historical strict checks. A compact new stage receipt records the full
normal verifier result's hash and deployment identity; it avoids duplicating a
large inventory inside the new journal. Full managed inventory verification
still uses the unchanged normal verifier.

The 20 current source/disposable-file tests and 27 existing coordinator tests pass.
They cover foreign/stale/unknown authority, separate native cohorts, actual
namespace/mount predicates, exact closed alias reads, immutable source topology,
rollback admission, compact inventory receipts and refusal of every material
`cordis.yml` change. They do not qualify a native transaction, SDK integration,
model use or actual upgrade/rollback. Root must stage genuine immutable authority
and perform independent ending audits after separately reviewed transactions;
a source draft or component-only ending receipt cannot satisfy admission.
