<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Linux DSH integration installation

## Cold data archive and current-cut binding — October 17

Source **a0f1f16dac3e493201867863382bdf38b2f6b5b3** adds internal
`services/dsh/cold_backup.py` for the data-backup prerequisite
before configuration preparation. This is capture/verification source, **not an
installed owner backup, activation command or automatic data restore**. Existing
review/Agent data, services, selections and bootstrap files remain untouched.

`capture(output, guard, additional)` requires the active cold maintenance guard,
unchanged selection and no pending profile/deployment marker. Coverage is explicit:
the whole DSH home, the selected/previous deployment JSON, and each guarded pair’s
three shared databases plus optional Hindsight engine/installation JSON. Mixed
Desktop data contributes named files rather than its application releases.
Additional named Native/Harness data directories must be supplied by the caller;
a data subtree inside mixed storage is allowed, the whole mixed root and program
release/checkout trees are not. This is **not** a claim that every real caller’s
data is covered without reviewing that list. SQLite journals refuse a cold cut.

A private PAX tar stores byte content, ordinary modes, UID/GID and nanosecond
mtime, directories, symlink text and original hardlink relationships within the
covered roots. Source
paths are read through directory descriptors without following symlinks. External
module targets stay external; their retained supplier artifacts still need
separate review. No artificial cross-file hardlinks are introduced for equal
content. Special permission bits, FIFOs/devices/sockets and unsupported ownership
require explicit scope review rather than being silently omitted. No code, model,
service or archived action is executed by capture/verification.

The fixed limits are 500,000 entries, two GiB per file, 16 GiB logical data,
128 MiB metadata and a 20 GiB archive. Conservative planned space is checked before
copying, followed by repeated **64 GiB free-space reserve** checks during copying
and archive validation. A caught failure publishes no success receipt and
removes only its own unchanged-inode bulk files; a replaced foreign file is kept.
Abrupt process death can leave an uncommitted private archive. Without a complete
receipt it cannot qualify activation; outer orchestration must inspect/retire that
attempt before another owner capture.
A complete or unknown completion-publication outcome is preserved for inspection.
Existing output directories are never reused or overwritten.

The archive/manifest are independently hashed and every member is checked against
the exact inventory. Source metadata, roots, selection and shared component cuts
are rechecked before the durable receipt is published. `verify` can confirm a
historical archive offline. `verify_for_guard` additionally binds it to the same
home, deployment, shared pairs and still-original covered data; a valid old archive
is refused as a *current* backup after source/selection changes. Neither result
qualifies the unreviewed caller graph or authorizes activation. There is no live
restore/extraction API; configuration reverse does not overwrite data banks or
replay actions.

Ten independently authored cases pass within **143 Python / four launcher Node**
checks. Tests cover GNU tar offline restoration, exact bytes/modes, Unicode names,
original hardlinks, symlinks without target traversal, selective mixed roots,
quota refusal, mid-copy/source/late-tree failures, foreign-output preservation,
corrupt/linked archives and current-cut refusal. Space is simulated in these tiny
fixtures to test policy independently of runner capacity; this is not a hosted
free-space claim. GNU tar uses `--same-permissions --no-same-owner` in a new private
authored directory; original numeric ownership is recorded, not privileged chown.

Separately, a real public fresh DSH integration and actual immutable candidate
adapter run on authored isolated data with the **real** reserve check. The archive
has **46 entries / 543,420 logical bytes** and restores both complete three-DB sets,
an explicit Native history/draft and all current DSH-home regular file bodies/modes
through GNU tar. DSH’s fresh setup moves its legacy settings pathname, so the proof
checks the actual inventory rather than guessing that path. Same-cut verification,
replacement-backend/Native-adapter preflight, exact config reverse and unchanged
DBs/incoming seal all pass, with zero owner profile/model use. Python **3.13.5** and
GNU tar **1.35** are tested locally. No new application mirror or immutable artifact
is created. Full Linux SDK **39057936198** is a terminal **success** at
**c3a6adae35c98d0f49095980652f8e01fa03379e** / runtime a0f1f16d, including all ten
new archive cases and the existing preservation/selection/backend checks.

The owner’s full cold backup and all required Native/Harness roots still need the
real caller/data map and quiescence. Next couple this verified data receipt to
matching-client selection and durable finalization/reverse, then qualify one
combined immutable update and actual owner continuation. Pilot feedback still
gates further project transfers; voice, later OS and public Office packaging
remain separate.

A live **metadata-only** pass of the real DSH home also fits current limits:
198,115 inventory entries including its root, 8,030,948,652 logical bytes including
hardlinks and 77,500,142 conservatively estimated metadata bytes. No unsupported
special mode, foreign owner or over-two-GiB file is observed. This reads no data
bodies and is not a cold checkpoint or proof of every additional profile root.
A separate Native provenance follow-up verifies two exact historical dependency
blobs through the canonical public GitHub repository. The missing settings UI
baseline is not supplied by its public overlay script; no private baseline is
copied or declared public. This narrows the next client-parity review.

[Portable qualification record](../release/harness-cold-backup-20261017.json).

## Managed-client maintenance fence — October 17

The controlled backend work exposed a remaining interruption gap: the persistent
DSH-home fence blocked the managed DSH server, while a released deployment writer
could let Native, Browser, embedding or mobile launchers reopen before the
configuration transaction had been recovered. The new source closes that gap
before any installed activation is attempted.

Source **e58a72b90aea23cbbc758da1680bf608e8ef58c3** changes the journal to
**`augmentor-dsh-configuration-transaction/2`**.
It publishes a private deployment `dsh-preservation.json` first, followed by the
existing profile marker, after durable recovery copies. Both markers bind the
same transaction and digest. The common `launch_lease` refuses the deployment
marker after acquiring its reader/writer lock, before any managed entrypoint
can execute its app/service path. Recovery is the sole explicit bypass and
requires the exclusive cold writer; presence of a record does not authorize
replay. This covers source-managed Native/service/secondary/login/recovery,
Browser Native Messaging, embedding, mobile and direct/delegated DSH launchers.
Older fixed-path/custom callers still require explicit adoption; this is not a
universal process or filesystem sandbox.

Ordinary Desktop activation/reverse now take a **reader** through validation and
selection, so they remain compatible with running readers but refuse a cold
maintenance writer or unresolved marker. Shared-store selection still owns its
exclusive writer and also checks the controller's current marker contract even
when an older candidate supplies the binding helper. Normal startup installation inherits the same exclusive gate. No generic
updater can release the maintenance markers.

Apply requires both owned markers. Reverse may recover an interrupted partial
marker publication, verifies all existing marker identities and exact config
bytes/modes, and completes protection under the cold writer before restoring.
After durable original configuration/reversed status, it removes the profile
marker first and deployment marker last. Death at either publication/removal
boundary is recoverable; foreign markers, dangling links and changed config are
preserved. Version 1 journals are deliberately refused by this new controller;
use their original retained controller for inspection/reverse rather than
relabeling an old record as version 2. No owner version-1 transaction is pending.

Local source checks pass **133 Python / four managed-launch Node** cases, including
**16 transaction** cases and **14 shared-launch / 12 deployment** cases. Eleven
actual managed launcher commands refuse both prepared and applied authored
transactions after the writer exits. Separate subprocesses die after each marker
publication/removal; reverse completes with exact original config and no open
marker. Selection fencing and reader compatibility are tested. These seven new
Python cases overlap the 133, not extra totals. The actual upstream DSH and sealed
candidate Native-adapter preflight/reverse also pass again on authored isolated
data; that is separate from the authored launcher regression evidence. Linux SDK
now explicitly runs the shared-launch and deployment files as well as the
32 preservation-discovery and nine backend cases. Full Linux SDK
**39055975304** is a terminal **success** at **beaa1b2f17d0b306e7d09ec804f3f416d83fccf0**,
with runtime e58a72b9 unchanged by that qualification-record head.

No installed app/bootstrap/service/selection changes, owner profile execution,
model requests, project transfers or new app copy occur. Both reviews/all 36
protected sets, registry 18, stores/settings, menus and GPU/voice state reverify.
Full cold backups, all real profile/client adoption, matching selection and durable
finalization/reverse orchestration, one combined immutable qualification and owner
continuation remain. Pilot feedback gates further project transfers; voice and
later OS remain deferred.

Additional read-only preparation inspects metadata for all 78 installed Native
Python files: 33 match current public bytes and ten lack an exact fetched Git
object. One of those, the settings module, has no current public counterpart.
This expands the earlier spot check; it does not prove a private/public origin
or authorize copying. Only hashes/AST symbol metadata are retained privately.
Live DSH-home sizing inspects 198,114 entries without reading data bodies,
following links, copying data or deleting dependency/backup trees. This advisory
is not a cold checkpoint and cannot authorize activation. These findings scope
the next backup/client-adoption work while preserving the working owner UI.

[Portable qualification record](../release/harness-dsh-managed-fence-20261017.json).

## Controlled replacement-backend and Native-adapter preflight — October 17

Source **517b71dbb0293aa78f306b127ae444e51ce09b95** adds the internal
`services/dsh/backend_probe.py` next step after the configuration journal. It can
start a temporary replacement while the cold maintenance guard and durable DSH
startup fence remain active. No installed apply/finalize command or automatic
owner upgrade is exposed. No new full app copy or immutable release is created;
the existing a4dc0eb2 candidate supplies immutable incoming bytes but does not
contain this new controller.

Only an applied, reviewed four-file configuration qualifies. The stage now also
binds the exact installed CLI entry and the incoming `desktop-release.json` when
present. Launch metadata is excluded from the artifact file-inventory hash, so
that extra binding is necessary before executing its recorded Python. A changed
manifest cannot redirect the adapter check to another interpreter, even when the
file inventory alone still verifies. Old stages missing those bindings cannot
start this probe; prepare a fresh immutable-input stage. The actual owner's
read-only stage now binds **48 inputs / 10 edits**, retaining 20 literal module
paths. No owner profile execution or write occurs in that staging check.

The temporary web command uses the incoming bundled Node, the bound CLI entry,
its existing working directory and supplied service environment, with the checked
home/shared pair and telemetry opt-outs. It listens on a temporary numeric
loopback port with `--no-open`. The normal managed launch gate remains exclusive.
Bubblewrap supplies a separate user/PID namespace with the backend as PID 1,
parent-death handling, fresh proc/basic devices and a retained launch descriptor.
Detached children remain in that PID namespace. The controller uses pidfds for
identity/signals and waits for normal teardown before config operations resume.
Private backend output stays in a **512 KiB memory buffer**, not unbounded disk
logs. Readiness failure or an exception closes the temporary tree; the durable
configuration fence remains for recovery.

This is process-lifetime containment, **not a filesystem/network permission
sandbox**. Full cold-store backups and review/quiescence of the real retained
profile graph and every legacy caller remain outer prerequisites. The requested
probe operations only read product identity, catalogue and presets; those reads
do not prove arbitrary plugin startup side effects safe. The real owner full
profile is not executed or adopted by this checkpoint.

The product check enforces the actual protocol, candidate version, home-token
identity, required personal roles and catalogue shape. The actual incoming Native
adapter then imports and calls `host.describe` in its own temporary PID namespace,
using a private connection registry. A stale inherited `DSH_AUGMENTOR_URL` is
overridden **only for this check** to reach the temporary backend; real settings
are not rewritten and product-version guards are not bypassed. That temporary
registry is removed. A successful check leaves startup fenced; matching loaded
clients, selection publication and fence finalization remain separate work.

### Qualification

**124 source Python / four source launcher Node cases pass**, zero failures or
skips. Seven new probe cases cover cold/applied admission, held launch gates,
configuration-write refusal while probing, normal cleanup of detached children,
controller death with both namespace actors stopped, missing tools/changed CLI,
changed launch metadata, bounded private logs/readiness failure and wrong product
identity. The metadata negative control confirms that inventory verification
alone still succeeds while the new exact metadata check refuses execution.

A separate isolated operator test uses the **actual installed DSH 0.2.0-rc.2**,
a fresh public integration and the existing **a4dc0eb2** immutable incoming build.
The real replacement reports product 0.2.13, matching home identity and both valid
personal roles; the **actual candidate Native adapter** connects successfully,
including with a deliberately stale inherited server address. Configuration
mutation is refused while the probe runs. Both backend/client namespaces retire,
startup remains fenced after success, exact original config bytes/modes are
restored through the journal (including mixed 0600/0644 original modes), both
authored shared DB sets stay exact and the
incoming seal re-verifies. Zero owner profiles/models are used. This is not
physical GUI, real owner-bank, or live task acceptance.

The experiment exposed two concrete setup/probe defects before acceptance:
source `copy2` permissions could leave newly installed files group-writable, and
a namespace without basic `/dev` caused the real runtime-lease spawn to fail with
EACCES. Fresh setup now protects only its new copied integration assets; existing
owner permissions remain untouched. The probe mounts basic devices, and its
actor tests open `/dev/null`. Product/version failures are still refused.

Previous Linux SDK **39049376766** is now a terminal success at e018c8c9 / runtime
b78996eb. New-source Linux SDK **39053669426** at b6bfaa2a / runtime 517b71db
failed before application checks: distribution bubblewrap 0.9.0 reports
`setting up uid map: Permission denied` in the namespace smoke test. No backend
probe cases ran. The corrected workflow grants `userns` to a runner-local copy
of the distribution executable using the exact-path AppArmor profile approach
in [Ubuntu’s release notes](https://documentation.ubuntu.com/release-notes/24.04/#unprivileged-user-namespace-restrictions).
This affects only the ephemeral CI runner when its restriction is enabled;
it preserves the host-wide restriction and distribution profile. The follow-up
below records its terminal result and portable-Python correction. The full owner main/
pilot, 36 protected file sets/PIDs, registry 18, shared rows/configuration, menus
and model/GPU/voice services remain unchanged; scratch is empty and root stays
about 99 GiB free. Next finish full cold-backup/entrypoint evidence and matching
client selection/finalization/reverse orchestration, then qualify one combined
immutable update and real owner continuation. Pilot feedback still gates more
project transfers. Voice/later OS and the public Office distribution gate remain
separate. [Record](../release/harness-dsh-backend-preflight-20261017.json).

### Portable Python process handles — October 17 follow-up

The executable-specific CI profile passes the namespace smoke on Linux SDK
39054331001 (0acb8beb). Setup and the 27 preservation cases also pass. Its seven
backend cases then fail five times because the standalone CPython 3.13.5 build
omits `os.pidfd_open`; this is a terminal failed run, not a skipped qualification.
The MX system interpreter exposes that function, explaining the earlier local
success.

The follow-up retains process-descriptor identity and signalling. It uses Python’s
wrappers when available, otherwise the host libc’s named `pidfd_open` and
`pidfd_send_signal` functions through ctypes. No numeric-PID signal fallback or
architecture-specific syscall numbers are introduced. Both required operations
are checked against the controller itself **before any actor starts**; absent
facilities refuse with the startup fence retained. Two additional authored
regressions force the libc path against the real namespace/detached child and
verify refusal without spawning when both implementations are absent. There are
now nine backend cases. Final MX source checks pass **126 Python / four Node**,
including all nine, and the real upstream/candidate-adapter preflight passes again.
The feature remains Linux-only; this CI change does not
qualify Ubuntu distribution support or modify the owner’s MX system.

Final Linux SDK **39054592182** is a terminal **success** at runtime
**39a717c18bda79fa102af1f632d1b1741acfd788**. Distribution bubblewrap 0.9.0,
the exact-executable CI profile, standalone CPython 3.13.5, all nine backend cases,
27 preservation cases and four managed-launch Node cases pass with the remaining
SDK steps. This supersedes both failed attempts above without relabelling them.

A new read-only client audit observes 12 known processes, 35 launcher/registration
files and three Native instances, idle with no draft and model-ready at observation.
Four installed Native file hashes lack an exact object in fetched public history;
this does not by itself classify them as private source. The installed Browser
remote has a public history object. The active Browser extension entry is reported
by inventory without a semantic version, so its loaded version remains unverified.
No source is copied or client restarted. Owner preservation again verifies both
review PIDs/all 36 protected sets, registry 18, stores/settings, menus/selections
and GPU/voice service state. Scratch is empty; no new app mirror or artifact exists.

## Cold configuration journal and managed startup fence — October 17

Source **b78996ebc0e06b1f0bb27e27231ee36cc3006196** adds the internal
`services/dsh/preservation_transaction.py` kernel and the standalone Linux
`scripts/dsh-profile-gate.py` lifetime gate. This is configuration transaction
source, **not a complete installed activation command**. The existing `stage` /
`verify` CLI still cannot apply an owner upgrade. The previous immutable
20261017-180443-c8315564 candidate does **not** contain this change; no new full
app mirror or sealed release is created for this checkpoint.

The internal `maintenance` context owns the selected deployment's exclusive
managed-launch gate, specified shared-pair companion locks and the DSH home's
exclusive profile gate. Selection bytes and the selected pair are checked.
Known unmanaged DSH hosts using that home also veto maintenance, including custom
profiles whose shared-store environment differs. Arbitrary old custom callers
cannot all be discovered; outer cutover must inventory/stop or adopt them. New
managed DSH launchers hold an inherited shared profile lock through `exec`.
Bootstrap installs the separate small gate beside the generated wrapper; existing
owner bootstraps are not changed by a source commit.

`prepare` requires a reviewed stage, verified immutable incoming artifact, the
same cold guard and absent private transaction storage outside the profile,
application, deployment, stage and source checkout. It writes durable before/after
copies and original modes for exactly four destinations: owned Browser code,
package metadata, ownership metadata and the profile patch. The transaction plan
binds the stage, incoming artifact, home and original desktop selection. Backup
files/directories are flushed before an exclusive, atomic no-replace startup
fence is published. No full profile serializer or JavaScript expression runs.
These four-file backups are **not full conversation/shared-store backups**.

`commit` applies or resumes only those reviewed config bytes. It rechecks stage
inputs/package aliases, the incoming seal, current selection and every destination.
A death after a rename is recovered by actual before/after bytes, not a progress
counter. Unexpected destination edits/mode changes, damaged backups, foreign
fences, stale selections/inputs or unknown phases refuse replacement. Completed
configuration remains **startup-fenced**: applying four files does not prove that
matching clients and services have been adopted. No fence-finalization API or
installed apply command is exposed yet. Do not remove that fence manually to
turn this component into a cutover.

`rollback` restores exact original bytes/modes without touching databases,
replaying writes or discarding unrelated edits. It does not require an undamaged
incoming artifact, but requires valid recovery copies and the original deployment
binding. A reversed status interrupted before fence removal can finish safely;
an exact successful reverse removes and flushes its own fence. Backups stay for
operator review. A later deployment-selection change needs the outer reverse
orchestrator; this kernel will not guess which client selection to overwrite.

### Qualification and limits

**117 source Python cases / four source Node launcher cases pass**, zero failures
or skips. Eleven new transaction cases include real process exits after each of
the four apply replacements and each reverse replacement, interrupted final fence
removal, idempotent recovery, input/alias changes, corrupted recovery data, owner
edits and cold-gate contention. The new launcher case proves profile-lock lifetime
after actual `exec` and pending-fence refusal with no private diagnostic content.
The exact SDK discovery pattern passes **27 overlapping cases** (16 staging plus
11 transaction). New public fixtures are independently authored.

The actual installed upstream DSH **0.2.0-rc.2** is separately executed **in place**
with an empty authored profile, read-only host files and isolated network/PID
namespaces. Catalogue/inventory reads pass. The real idle server retains the
profile reader, vetoes maintenance, and releases the cold gate when stopped.
The generated wrapper refuses a pending fence before starting that backend.
Both authored shared database sets stay exact; zero owner profiles/models used.
Namespace/scratch processes and fixture data are retired. This is not actual
owner-profile execution, a full integration upgrade or matching-GUI acceptance.

The owner main/pilot, all 36 protected file sets/PIDs, registry revision 18, shared
rows/configuration, menus and model/GPU/voice services remain exact. New-runtime
[Linux SDK 39049376766](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/39049376766)
has passed its setup, preservation transaction and managed profile-gate steps; the
overall run remains in progress. Prior SDK 39047120454 covers earlier code.
Next integrate full cold-backup evidence, explicit entrypoint adoption, controlled
backend startup/preflight and matching-client selection/fence finalization into
one guarded operation, then qualify full installed activation/reverse and owner
continuation. Pilot feedback still gates more transfers. Voice/later OS remain
deferred; the separate public Office rebuild/distribution gate remains open.
[Record](../release/harness-dsh-configuration-transaction-20261017.json).

## Immutable preserved-integration candidate — October 17

The existing source is now qualified as one private **unselected** MX candidate:
application **73675d62d1f3db98ebc6490e5cc73c4e2629ddb8** (runtime e07e5db6),
release **20261017-180443-c8315564**, artifact
**a4dc0eb2edda6c245bd7e6dd23d32309c3e79215db6bf78ca802ad479896ef93**.
Its seal verifies **24,773 inputs / 1,143 compiled files**. The previous immutable
candidate supplies checked dependencies/components/notices; changed public sources
and freshly compiled runtime output supply this candidate. No private repository
source or owner data is copied into it. It is not a public distribution approval.

Ordinary and exact-sealed qualification each pass **42 Node / 90 Python** cases.
The recorded Python interpreter repeats all 90 Python cases (overlapping coverage).
An additional **11 exact-sealed Office process/Native inspection cases** pass,
including the actual changed-source Wasm recovery regression. All final suites
have zero failures/skips. The first operator attempts exposed excessive socket
path length and a missing test-only Native import path; those fixture environments
were corrected. Short `/tmp` bind mounts are backed by the same managed workspace,
with read-only host files and isolated process/network namespaces. No app changes
or additional sealed candidates were needed to correct those fixture failures.

The actual owner's configuration stages and verifies against this exact immutable
incoming build: **46 bound inputs / 10 module edits**, preserved peer settings,
legacy frontend and current shared-library backend. Its 20 remaining literal paths
remain retained and protected; the original full profile is neither executed nor
activated. Separately, the original nine personal modules run **in place** against
the exact sealed incoming services/adapters on authored data. Both saved roles
cold-reopen and continue, identity reaches model input, the current sealed memory
service owns cold startup, templates/instructions work, and Improve uses shared
instructions without submitting a chat turn. Three controlled local model calls;
zero owner/external model calls. Cached banks/settings and stale-source bytes stay
exact. This is narrower than real owner historical/tool/model/UI acceptance.

[Linux SDK run 39047120454](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/39047120454)
is a terminal success at the same source head. This supersedes the earlier pending
SDK observation below; it does not waive the separate public Office source/rebuild
packaging gate or prove later-platform parity.

The one ordinary app mirror and all test/data fixtures are removed. The now
superseded, unselected 20261017-151405-6c6b7080 candidate passed fresh seal and
process/selection/launcher/profile-reference checks and was retired (0.548 GiB);
its small manifest/provenance receipt remains. The new candidate and preceding
embedding candidate remain; ambiguous older artifacts are still protected.
The 64 GiB reserve and one-workspace policy remain mandatory.

The actual main/pilot app, protected stores, launchers, registry and model/GPU/voice
services remain unchanged. **No owner cutover is claimed.** Next implement and
qualify the durable cold-backed-up custom integration activation/reverse operation,
then match clients and qualify real owner continuation/busy/restart/reverse behavior.
Pilot feedback still gates further project transfers. Voice/later OS stay deferred.
[Aggregate evidence](../release/harness-dsh-preserved-package-20261017.json).

## Retained roles, cold ownership and Prompt Library bridge — October 17

Source **e07e5db623d2b777eeb4e25ece5646da858b8b90** closes two concrete preservation gaps. The retained 0.2.0 Prompt
Library backend reads/saves templates but rejects `improvement.save`, despite its
retained frontend exposing that setting. A preserved frontend bundle alone was
therefore insufficient. The stage now keeps the bundle/client unchanged, disables
only its legacy backend entry, and inserts the standard `augmentor-product-prompts`
backend from the incoming public build. The old library version/patch structure,
package alias and backend/client bytes are bound; unknown versions, custom
conflicting overrides or alias changes refuse. Reviewed repeats update the owned
replacement without duplicating it. Root-owned suppliers are accepted only as
explicit bound, non-group/world-writable supplier files; owner inputs stay guarded.

This uses DSH's actual include-patch contract: `name` in a non-insert patch is an
identity guard, not a module replacement. A name-only override would be skipped.
The supported disable-plus-insert form was verified against the real upstream
runtime, including disabled legacy and active replacement inventory entries.
It leaves frontend metadata and controls unchanged; final owner rendering remains
separate acceptance, rather than being inferred from a backend response.

Mixed releases also load identical public entry modules from different old roots.
Within the two owned personal roles, an entry whose bytes exactly equal its public
incoming counterpart can now move to that counterpart. Its relative imports then
use current clients/services instead of potentially cold-spawning an old helper.
Changed/private entries are left at their existing paths. Module edits record that
reason and bind both inputs; this copies no private adapter code. The actual stage
now binds **46 inputs**, proposes **10 module-name changes** (eight identical-public
role references plus two original integration references), and adds the library
backend bridge. Peer edits/settings remain exact. **20 literal module paths** still
remain elsewhere/unchanged; their original roots are retained.

### Runtime evidence

The two actual personal-role definitions were extracted as configuration only.
Their retained modules were executed **in place**, with the host filesystem mounted
read-only, user runtime sockets hidden and a distinct network/PID namespace. Only
a disposable fixture workspace was writable. No private module was copied into
source, test archives or CI; no original full profile or owner bank was run.

Nine original personal modules register/create both roles and preserve authored
identity snapshots and cold history events against prestarted current services.
The old Prompt Library's selected-target reads pass, while instruction-save is a
negative control. With the staged public-entry rebindings/library bridge applied
only to the fixture, **all shared services are stopped before cold startup**.
Both saved roles then continue through a controlled local OpenAI-compatible model,
with authored identity visible in their actual model input and the current source
memory service owning the cold-started store. Shared instruction save/readback and
template save/delete pass. A third controlled call improves a draft using those
shared instructions without adding a conversation turn. **Three authored model
requests / zero owner or external model requests**; no live Qwen/tool/speech
acceptance is inferred. Existing cached bank rows, person/disabled settings and all
stale-source database bytes remain exact. Namespace processes and scratch retire.

Source focus **90 Python cases** passes, including **16 preservation cases**.
Five additions cover frontend/backend bridge, alias/custom-override/version refusal,
repeat update and identical-public versus private entry handling. Previous Linux
SDK **39043965407** is now a terminal success at b3cbb4e7 / runtime 3777cc92;
new source hosted qualification remains separate. [Record](../release/harness-dsh-retained-graph-20261017.json).

The actual owner's profile was separately re-staged read-only; it was not activated
or executed in that test. Its main/pilot data, launchers, registry, model/GPU/voice
services and prior immutable releases remain unchanged. Next qualify an immutable
incoming build and a cold-backed-up activation/reverse transaction with matching
clients. Real owner banks/history/budgets/busy work/live continuation, other retained
project/plugin paths and final UI/pilot feedback remain. No further project transfer,
DSH retirement, voice work or later-platform rollout is claimed.

## Preserved custom integration stage — October 17

Source **3777cc92961fc3d21c84cf3a1390970fcea851cb** adds `scripts/stage-dsh-preservation.py stage` and `verify`.
They prepare and verify a private review directory; they do **not** install,
execute a profile, start/stop DSH, update launchers or modify an owner file.
Activation is deliberately absent from this command. It still requires an
immutable qualified incoming artifact, full cold backups, matching clients and
transaction/reverse acceptance; this preparation is not a replacement for them.

The stage binds the exact modern CLI/SDK metadata, original package provenance,
owned/active Browser code, peer edits, owned preset files, profile/settings/token
inputs and incoming integration bytes. An active compatibility Browser copy must
match the recorded owned code. Original package metadata must match the recorded
supplier hash; existing edits must be confined to peer dependencies explicitly
supporting the tested modern SDK. Those peer values are retained in the candidate
package while incoming public package metadata/version/code supplies the upgrade.
Unrecognized code, metadata or preset edits refuse rather than being discarded.

Custom YAML is parsed as bounded nodes only: no `!!js` construction/evaluation,
no YAML 1.1 value conversion and no full-document serializer. Only identified
owned module-name scalar spans are replaced. Comments, Unicode, prompts, custom
settings, `off`, expressions, Browser overrides and other plugins remain exact.
Aliased/duplicate/ambiguous structures refuse. Both existing declarative role IDs
must remain present. New preserved ownership records the deliberate migration,
not a forged historical insertion or reset of an edited-file checksum. Normal
setup refuses overwriting that ownership and requires another reviewed migration.

The output contains a candidate patch, small plugin files and a private plan with
concrete module edits, input/output hashes and retained module references. It must
be an absent directory outside the application/profile; output files are private.
`verify --sha256` checks the reviewed plan hash, staged assets and current inputs.
A changed profile, supplier, staged asset or newly created optional configuration
refuses. Partial output is removed only from the newly allocated owned stage;
existing output and all input bytes are preserved. Use the disposable build
workspace for rehearsal; do not retain another full application per checkpoint.

### Actual profile evidence and remaining graph qualification

The actual profile currently loads Browser code from a separate compatibility
folder. Its code matches the owned expected hash, and its package matches the
owned edited package; the original supplier package satisfies the recorded hash.
The actual preservation stage succeeds against **28 bound inputs**, proposes
**two module-reference changes**, and keeps peer settings exact. No real profile
is executed or owner file changed. The temporary stage is removed afterward;
small private plan/receipt evidence is retained outside GitHub.

The existing role definitions also reference **21 retained literal module paths**
across older/other adapter roots. They are preserved, not silently rebased to
unqualified replacements. Those dependencies and any dynamic expressions need
separate runtime/companion qualification before activation. The stage's input
checks are not whole-graph, model/tool, old-bank or historical acceptance. Existing
roots must remain available; no DSH retirement or original-project transfer occurs.

Focused **85 Python tests** pass: 11 preservation cases plus nine modern setup
cases and the existing setup/readiness/leases/deployment checks. Preservation
covers exact edits/peers/private output, actual CLI staging/verification, untracked
active code, non-peer edits, provenance/preset changes, aliases/duplicates, mixed
SDK/ranges, stale input/new credentials, tampering, links/overlap and late change
cleanup. New tests use independently authored profiles/code only. The Linux SDK
workflow now installs a hash-pinned PyYAML inspection wheel and runs these cases;
no new production dependency or binary publication is implied.
[Portable evidence](../release/harness-dsh-preservation-20261017.json).

Earlier Linux SDK **39042645605** succeeds at 0ca81395 / runtime 6a82cf82.
Earlier full validations **39041187997** (f640ce8c) and **39041724378** (14e3c523 /
runtime c6653b75) finish their application checks and fail at the retained **Office
public source/exact-engine-rebuild packaging gate**. Source-boundary/Home/component
jobs pass. Those are terminal results, superseding earlier live observations;
neither is restarted, and no whole-workflow/package approval is claimed. New
preservation source still needs its own hosted qualification.

## Modern setup qualification — October 17, 2026

Source **6a82cf8209a7e6783efba41b15d0d8c4282043b0** supports explicit existing DSH **0.2.0-rc.2** on Linux, alongside
the existing **0.1.5-rc.1** path. The complete-runtime download/install lock still
ships the legacy family; this change does not upgrade that lock or an owner service.
The CLI manifest selects the exact SDK family. Modern setup requires CLI/base/tools/
preset/preset-registry 0.2.0-rc.2, Cordis 4.0.4 and Schemastery 3.18.4. A missing or
mixed family refuses. The dependencies are rechecked between connection inspection
and installation. Modern setup is refused on macOS/Windows until qualified there.

The modern profile receives two declarative agent-preset registrations, preserving
the existing Linux/Browser role IDs and their common personal-agent composition.
Only the modern composition changes workflow-worker-thread to workflow-ptc; tools,
persona, compaction, memory, desktop/browser controls and enabled Ralph remain.
Legacy preset files remain owned/snapshotted, and legacy installation emits its
original composition. Package/model/provider/voice settings are not rewritten.

Existing profile text is retained byte for byte around the owned insertion. Setup
never evaluates custom YAML expressions or rewrites a reasoning key named `off`.
The owned insertion is replaced only if its exact ownership checks still pass.
Edited package metadata, preset bytes or owned composition are refused and left
intact. Existing external prompt-library integration is retained without adding
a second one. Interrupted owned updates restore the previous plugin and presets;
the integration token remains stable. These checks do not automatically migrate
the actual owner's hand-edited integration.

## Evidence

Focused **73 Python cases** pass; **18 overlapping setup cases** also pass with the
exact new Linux SDK workflow command after the final locator assertion. Eight
independently authored modern cases cover fresh install/reinstall, exact custom
text/token preservation, legacy-to-modern owned upgrade, changed/missing SDKs,
edited package/composition refusal, existing Prompt Library, rollback and platform
refusal. The SDK workflow now runs setup qualification on Linux before later Office
checks; this does not waive the public Office packaging gate. Manual SDK dispatch can use `platform=linux` for the
current MX scope; default/pull-request dispatch still tests the full platform matrix.
This Linux result cannot establish macOS/Windows readiness. Earlier f640ce8c SDK
run 39041187982 passes Linux, fails macOS on the existing unsupported import/export
path, and cancels Windows; those platform gaps are retained rather than waived.

A separate actual installed upstream **0.2.0-rc.2** CLI/base/tools/web-app test uses
current public source against a new authored profile. It installs, restarts,
registers both non-broken presets, creates both real owned roles, matches the
0.2.13 product handshake, and reads the selected authored shared prompt library.
After another cold restart both saved role histories retain every original event.
The only header difference is DSH's documented persistence default
`delegationDepth: 0` when that field was previously absent. The upstream persistence
writer explicitly uses that default; no history event is dropped or replayed.

All three traced process trees make **zero INET connect calls** during the bounded
proof with telemetry disabled, and no model request occurs. This proves fresh
role creation/blank-history cold read, not full historical sessions, tool execution,
model continuation or complete DSH feature parity. The owner's instance and profile
are never copied into the fixture. Only the small plugin install and authored data
live in the managed scratch workspace. Its two scoped test companion processes are
stopped at the end and scratch is removed. The guard correctly retained the first
attempt's scratch until those verified fixture-only processes were reaped.

The first real comparison exposed an incorrect test-library marker, then the
upstream header default. Both were investigated using authored evidence; the
source installer and history were not weakened to conceal them.
[Portable qualification](../release/harness-dsh-modern-setup-20261017.json).

## Existing owner installation

The actual installation has edited package peer metadata and custom modern
composition, so normal install must still refuse its automatic replacement.
Next prepare a deliberate backed-up migration retaining those edits, all current
role definitions, model/provider routing, plugins and settings; qualify matching
product/Browser clients and immutable artifacts before selecting anything.
Shared-store adoption then requires fresh full cold backups, the busy-work veto,
existing-bank/history/budget preservation, restart and reverse acceptance.

Both installed MX reviews remain unchanged; pilot feedback still gates additional
project transfers. Voice and other platforms remain deferred. See
[shared-profile adoption](HARNESS-SHARED-PROFILES.md),
[desktop deployment](DESKTOP-DEPLOYMENTS.md) and
[storage retention](HARNESS-BUILD-STORAGE.md).
