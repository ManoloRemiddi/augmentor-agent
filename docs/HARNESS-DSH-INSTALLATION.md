<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Linux DSH integration installation

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
hosted qualification is pending; prior SDK 39047120454 success covers earlier code.
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
