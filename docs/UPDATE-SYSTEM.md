<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Shared application updates

## Implementation checkpoint — October 3, 2026

This feature is under implementation on `feat/automatic-updates`, based on
`c7f895d416e6b94ca601b66a09caf4846a64b907`, now integrated with main
`550e274d9f0c01f35c0e3b4d7d3743fed4899971` (Handy and SDK source alignment).
It has not replaced an installed
application, published a signed repository, or qualified automatic installation.
The complete intended scope includes optional automatic installation, independent
health observation and recovery across supported installation methods. The
discovery/download checkpoint below is not completion of that scope.

Desktop **Versions & updates** and Browser **Settings → Updates** use one
model-independent service. They show installed version/build, the last successful
check, an available release and transfer progress/errors. Preferences support
daily or two-day checks, stable or preview releases, and separate download and
installation consent. Automatic installation remains disabled until the installed
build has a qualified external installer adapter and a provisioned signed feed.
The UI does not silently turn that preference into permission to replace files.

Automatic checks default on for an installed application, off for a development
checkout. Downloads default off. The scheduler runs while the shared service is
running, starts after a short boot delay, adds up to fifteen minutes of jitter,
and retries failures with bounded backoff. It catches an overdue check on the
next launch; this is not an operating-system task that wakes a closed application.
Changing the schedule is shared across surfaces, not tied to a model or chat.

Notifications are claimed once per exact release across both surfaces. Users can
skip a release or postpone for one/two days. The native primary window uses its
existing tray when available, otherwise an unobtrusive tooltip on More. Browser
shows a button opening the Updates section. No modal dialog interrupts chat.
Failure retains the previous successful-check time and candidate instead of
claiming the application is current. An unknown legacy build cannot be declared
older than another build of the same product version without a bridge receipt.

## Unix coordination checkpoint

The Mac login shortcut service participates in the shared reversible reservation
protocol. Accepted activation/save work refuses preparation. A prepared service
rejects new activations/saves without changing saved bindings, cancellation
restores admission, and committed shutdown replies before normal helper cleanup.
Authenticated local sockets, actual build root and kernel peer observation keep
maintenance separate from ordinary shortcut status. Eleven focused shortcut
cases pass locally; combined shortcut discovery passes 41 with one OS skip.

`platform_adapters.peer_process.PeerProcess` retains a Linux socket-supplied
pidfd or Mac process event tied to the peer's kernel audit token. Every subsequent
connection must belong to that original live process. It validates the independently
selected executable, grants observation only, and never signals an application.
Three tests observe real inert Unix peers, exit and wrong-executable refusal on
Linux. Mac 14/26 native qualification remains required. Linux kernels lacking
SO_PEERPIDFD cannot use this adapter and must retain manual installation.
This observation primitive and shortcut admission are not a complete Unix installer;
startup exclusion, launchd ownership, graph drain, independent apply/health and
reopening remain required before automatic platform flags can be enabled.

At `d34b60d`, Windows Desktop passes native x64/ARM64 ACL checks. Full x64 reaches
actual completed-target reopening, then fails the fixture's subsequent drain
checkpoint because its public evidence folder is not private. The fixture now
writes that checkpoint in its existing private runtime folder. A fresh full run
must qualify all later stages; the failed run is not an overall passing proof.

## Unix startup and graph preparation

`posix_startup.Startup` holds a shared kernel reader until control registration
is discoverable; maintenance holds its exclusive writer through discovery,
reservations and observed drain. Desktop, shortcut, shared prompt/memory helpers,
and SDK launches participate. Without a supplied Linux login runtime, these
components retain the desktop’s private `/tmp/augmentor-linux-pi-<uid>` fallback;
they do not require a headless user to create `/run/user/<uid>`.
SDK registration leases survive Unix exec into the
actual Node server and defer preparation before any component shutdown.
The compiled Mac launcher now takes startup/lifetime leases before resolving
resources or initializing Python. Desktop readiness releases its native startup
reader; its installation lease remains until OS exit. Native compilation and
lock-export qualification are pending for this newer source.

Installed DSH and Browser native hosts expose private Unix maintenance endpoints
for their existing admission protocols. DSH uses the same accepted-agent/job
checks and normal `appExit` callback; Browser uses the existing document/native
reservation and shutdown flow. The original kernel-observed Node process is
verified before each request. Private endpoints have bounded one-shot messages;
a committed shutdown follows reply delivery or a lost connection and is never
replayed. Developer DSH/native hosts do not register installed update endpoints.
Prompt/memory maintenance replies add actual build-root/process identity while
ordinary RPC results retain their previous shape.

`posix_preparation.PosixPreparation` discovers those exact-source endpoints,
reserves shortcut activation before windows/downstream services, and records each
normal shutdown before observing that original process exit. Busy discovery
releases reservations and startup exclusion; unconfirmed replies retain exclusion
until transport cleanup actually finishes. Source checks cover five real Node
endpoint/graph cases, three kernel startup/exec cases and eleven shortcut cases.
The earlier peer-observation source `9bce979` passes hosted Mac 14/26. New combined
Linux/source checks pass 922 Python cases (40 skips), 531 Node cases (two skips),
92 Browser cases, build and type checks; newly added graph cases also pass focused
checks. These are isolated fixtures, not installed automatic-update qualification.

This graph alone cannot authorize replacement. The Unix external observer,
exact-source recovery retention, final package/bundle lease, launchd/systemd
registration coordination, fresh publisher authority, independent target health
and reopening still need complete installation qualification. Package-managed
Linux must use its package manager; managed Linux must preserve the immutable
`augmentor-update` selection contract. Mac Desktop/Companion coexistence and
unowned speech/runtime components need explicit installation-plan handling.
Automatic flags remain disabled on all customer/source records.

At `000fb62`, both native Mac jobs pass the Unix updater cases, real Node graph
checks and compiled Mach-O startup/lifetime/export tests. The workflows fail later
in packaged SDK native-description qualification. SDK hosts now retain their
blocking registration without joining Browser document maintenance, and fixture
errors retain bounded native diagnostics. The Linux SDK registration/native protocol
proof passes; fresh combined native Mac workflows must qualify the correction.
SDK app owners remain responsible for normal shutdown and are never automatically
committed through Browser maintenance.

## Mac retained bundle and native apply checkpoint

`macos_payload` inspects the entire bundle, including native executables, Python,
Node, DSH, framework links and signatures. Relative links must resolve inside the
bundle; external/dangling/hard links, special or privileged files, changing bytes
and oversized trees refuse inspection. Native inspection compares independently
identified release bytes and bundle identity/version, verifies signatures before
and after hashing, and requires Developer ID/team and Gatekeeper assessment for
public signed/notarized releases. Explicit development fixtures remain separate.
Two inert relocation/link-boundary tests pass on Linux.

`MacInstallerBackend` requires the live Unix startup writer, exact previously
inspected source/candidate snapshots and same-volume staging. Readiness acquires
the final exclusive installation lease; APPLY is one-shot and rechecks both
bundles. The existing native replacement keeps an exact old bundle and restores
it on a confirmed failed promotion rename. It does not edit user state, replay
native journals, complete the shared transaction or resume a launchd registration.
Fresh publisher authority, graph drain and owned registration coordination belong
to the external controller and remain required.

The new hosted `macos-update-payload-proof.py` qualifies whole development-bundle
retention, signature-damage refusal, kernel reader refusal and the actual shared
journal/graph/backend same-build replacement into a disposable retained copy.
It preserves the original artifact, source backup, pending shared record and
synthetic settings. Native execution is pending. It does not qualify signed
N-to-N+1, independent target UI health/reopen or any installed user application.
The source has 147 focused updater cases (one OS skip); production flags remain
false until the complete observer/controller and distribution gates pass.

## Mac offline target health

The fixed target `macos-local-health.py` action renders the existing shared preview
UI using offscreen Qt inside a new private temporary profile. It clears inherited
app/speech/model/profile variables, starts no controller or companion and checks
text/font/render availability. The external `macos_health` observer first verifies
the complete exact bundle/signature, launches only that target's fixed Python
script, observes successful actual exit, validates bounded metadata/render evidence,
and verifies the whole bundle again. This is offline local renderability, not
provider connectivity, Cocoa/TCC permission acceptance or ordinary app reopening.

Two typed Mac-report tests and the existing two real shared-render tests pass on
Linux. The hosted retained-copy apply proof now also probes the actual copied
target's sealed runtime. Native qualification is pending for the new action.
The shared transaction deliberately remains pending in that fixture: health alone
does not supply a live production observer's completion/publisher authority.

Full Windows qualification at `9bce979` now passes both x64 and ARM64 in
[37134219949](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37134219949),
including actual busy-draft deferral, independent target health, captured-window
reopen and the later repair/remove stages. Its other five workflows also pass.
This remains a same-build development fixture, not signed N-to-N+1. The newer Unix
source is qualified separately and has not been deployed to installed apps.

## Ownership and data

`services/updates/manager.py` belongs to the per-user shared prompt service, rather
than starting a second unowned daemon. Prompt service maintenance admission covers
the whole background discovery/download operation. Busy downloads refuse graph
maintenance; cancellation terminates only the updater's own transfer child.
An updater initialization/recovery error cannot disable conversations or prompts.

Windows transfers create new cache bytes instead of preserving public temporary
file ACLs. The Python owner verifies the file’s existing user/SYSTEM allow-list
through an opened kernel handle before setting its protected flag. Windows may
assign the OS token's default Administrators owner to elevated Node creations;
this exact token identity is normalized to the user only after validating the
private grants. Unrelated owners, public grants and linked files are refused
without changing their permissions. See Microsoft's [default object owner](https://learn.microsoft.com/en-us/windows/win32/secauthz/owner-of-a-new-object).
Hosted
Windows tests must verify this producer boundary on both CPUs.

Private data lives under `<AUGMENTOR_SHARED_DATA>/updates` (or the existing shared
data default): atomically written `state.json`, verified repository metadata,
digest-named cache files and `ready/<channel>-<target>-<version>-<build>/` downloads
with their original filenames. Status responses hide filesystem paths. An explicit
**Show downloaded files** action opens that dedicated folder without executing
the installer. Cache files have bounded sizes, verified hashes and private file
permissions; linked/hardlinked or foreign files fail validation. Conversation,
credential, model and speech directories are not replaced by downloading updates.

Saved preferences use optimistic revision checks. Dirty settings forms preserve
the draft and its original revision while another surface changes the service.
An old-channel response cannot overwrite a newer selection. Interrupted workers
become an explicit interrupted state; observing that state never replays install.

Desktop transports updates through `PromptClient`, including when the model is
offline. Browser uses a short independent native connection. A mismatched product
handshake permits status, discovery, download, cancellation and opening the
download folder to support repair; it does not permit preferences or installation.
The existing embedded application SDK administration guard still blocks this
shared surface entirely. Update actions reject caller-provided URLs, commands,
release objects and download destinations.
The SDK settings filter also hides the shared Updates section. Embedded workspace
controls cannot change the host installation's update consent or start updates.

## Publisher tooling checkpoint

[`scripts/update-repository.mjs`](../scripts/update-repository.mjs) creates a
two-of-three Ed25519 root and separate targets/snapshot/timestamp keys. Secret
material must live outside any Git checkout and outside public output. Routine
`publish` and `refresh` do not load offline root private keys. Both channel
catalogs pass the same Python schema used by installed clients; new artifact
entries require actual size/hash-verified bytes. Existing public target names
cannot be relabeled with another digest. Refresh verifies retained signed
publication history and re-signs unchanged content with a higher sequence.

A publication uses consistent versioned snapshot/targets metadata and hash-prefixed
catalog files. Timestamp expires in seven days, snapshot in thirty, targets in
ninety and the initial root in two years. The output is a new immutable local
publication directory; upload remains a separate release-owner action. Publish
versioned files/catalogs first and timestamp last, retaining prior versioned files
and root history. The installed TUF client verifies catalog-prefixed paths; GitHub
installer filenames retain their public names and pass the maintained model’s
exact target verification.

## Release-build receipts and packaging

The Debian, Mac and Windows stage builders now use
`services/updates/packaging.py`. Every newly staged payload includes
`release/updates.json`; an enabled configuration requires a bounded, self-signed,
unexpired two-of-three public root, verified with the pinned TUF model before
copying. Only that public JSON file is copied from `release/updates/`; private
signing keys are never copied. Inherited Node preload options are removed during
the build-time verification. These files enter the Mac application inventory and
signature, Windows sealed inventory, and Debian runtime package before delivery.

`release.json.update` carries schema `augmentor-update-receipt/1`, the reviewed
build sequence and a deterministic release ID covering product version, source
commit, CPU, channel and application component. The installed service rechecks
that ID against its receipt. A zero build is an explicitly unnumbered test
candidate, not a public ordered build; packagers default to zero for CI/dev use.
Public Mac/Windows previews require a positive `--update-build N`. The Windows
preview workflow is now explicitly dispatched with a reviewed build input shared
by both CPU jobs. Do not derive this number independently per CPU, use a timestamp
as ordering, or reuse a published version/build for another payload. Debian
release creation likewise supplies `--update-build N` explicitly. All current
receipts retain `automaticInstallQualified: false`; a counter or a successful
package build does not qualify installation.
Numbered staging requires a clean source checkout, and any explicitly declared
source commit must match its actual HEAD. Unnumbered candidates may record dirty
source but cannot use that to claim an ordered public build.

Mac `desktop` and `companion` receipts and signed catalog entries have distinct
identities. Catalog entries without `component` mean `desktop`, preserving the
schema's initial desktop interpretation. Only Mac supports a separate companion
entry; selection cannot change the installed component. The legacy public asset
lookup currently offers desktop bundles only and returns no companion candidate.
Development-channel bundles use valid preview preferences with scheduled checks
off, including after restart.

## Installation authority integration in progress

### Live installation controller, deferral and reopening

The native `5891eef` revision passes Mac 14/26, shared validation, SDK platform
contracts and installer feasibility. Windows Desktop fails only the new runtime
lease fixture's nonprivate temporary parent; the fixture now creates its parent
through the actual private-directory API. Full x64 installation passes busy-draft
deferral and independent completion, then refuses reopening because installed code
has ordinary Inno ownership/read grants rather than a private-data ACL. The source
correction introduces a separate read-only installed-payload descriptor: expected
user/SYSTEM/Administrators ownership and write access, ordinary read grants,
single-link/no-reparse bytes, no ACL mutation. Cache/observer state remains private.
The source bootstrap uses this same explicit installed-code boundary. A new native
ACL test accepts public read access and refuses public write access. Fresh hosted
qualification is required; the initial x64 run is a failure, not a reopening pass.

The Windows controller now connects the shared download service to the fixed
supervisor launch. It dispatches only after leaving its own maintenance work
admission, with both download/install consent, a fully downloaded authenticated
candidate and qualified source/target. The external bootstrap and coordinator
still independently recheck publisher authority and consent. Canonical per-user
installation/data locations are required; custom locations retain manual delivery.
No customer build or feed is enabled by this integration.

Each launch has a fresh identifier and a bounded private result. Results report
status only: they cannot run commands or change the cached running identity.
Confirmed pre-drain cancellation requires live reservation release, durable
cancellation archival, the original coordinator's private handoff and its actual
whole-process-range exit. Busy work then waits five minutes. Lost launch replies,
invalid results and uncertain post-shutdown failures block automatic retries and
preserve recovery records. Cancelling a download never terminates Setup. Skipping,
postponing or revoking consent remains checked before APPLY.

The original observer receives instance names from the actual reserved graph.
After exact target completion, it rechecks current inventory/identity and launches
only the fixed installed executable for those instances and the background owner.
Browser pages keep their normal native reconnection/reload path. Reopening failure
does not erase successful installation or authorize rerunning Setup. Local cleanup
failures likewise cannot reclassify an observed completion as failed installation.

Windows SDK launchers register a kernel lease while embedded servers run.
Preparation checks this lease before closing any desktop component and defers
until those servers close normally. This preserves work but does not yet implement
automatic graceful maintenance/reopening of SDK servers. Temporary observer code
has a separate lease retained until actual process exit. The next bootstrap cleans
only marked, completed/deferred public-code runtimes after obtaining their exclusive
lease; unknown attempts and linked trees remain preserved.

The focused portable suite passes 134 cases (133 passed, one OS skip), including
live child-process lease/cleanup tests and the real reservation cancellation
witness. Controller launch tests use an inert adapter and prove scheduling/status
boundaries, not publisher or native installation acceptance. The full Windows
fixture now exercises actual busy-draft deferral and actual completed-target
reopening; fresh native x64/ARM64 results are required for this revision.
Broader isolated source checks pass 908 Python/Qt cases (869 passed, 39 skips),
529 Node cases (527 passed, two skips), all 92 Browser cases and type checks.
These runs use locked DSH dependencies and separate dictation fixture state;
they do not touch the owner's display, tasks or installed application.

Earlier source `4327ffd6f2cc24a5ae0f7c07f704fb1f1af27078` passes
[full Windows qualification](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37126091855),
[installer feasibility](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37126091832),
[Windows Desktop](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37126091824),
[Mac 14/26](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37126091975),
[shared validation](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37126092000)
and [SDK platform contracts](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37126091829).
This confirms the prior log-reader correction and actual bootstrap-exit fence,
including nonzero refusal. Full installation remains an unpublished same-build
fixture; these passes do not qualify signed N-to-N+1 or the newer controller.

Linux/Mac automatic installation adapters, signed N-to-N+1 health/recovery,
signing-key custody/online-key migration and public feed provisioning remain open.
Same-build source restoration also needs a verified controller recovery/reset
path; a saved receipt alone must never restart installation. The subsequent
subsections retain earlier implementation checkpoints and pending evidence as
history; this subsection is the current controller status.

### Offline root replacement

The publisher now supports `prepare-root` and `activate-root`. Preparation runs
with two distinct existing offline keys, generates three replacement offline
keys outside Git/public output, and cross-signs the immediate next root with both
old and new thresholds. It does not touch the online publisher or issue releases.
Activation needs the exact current root hash, an unexpired next root, both verified
thresholds and no pending publication. Existing online role keys are retained;
online key replacement requires its separate migration/recovery implementation.
This follows [TUF root update verification](https://theupdateframework.github.io/specification/v1.0.36/),
including sequential versions and both authorities.

Private root bytes are immutable numbered files. The publisher state selects the
new file through one atomic commit, preserving the old selection if that commit
fails. A retry can reuse only the identical prepared bytes. Every later publication
contains the entire versioned root chain. Historical abandonment audits remain
valid only against that retained verified history; signing sequences and immutable
asset identities survive rotation. Neither a root update nor its local preparation
uploads metadata or enables client installation.
Keep exactly one prepared candidate for each next root version. Publish root
files only from a publication produced after successful activation; standalone
preparation output is for review. Recover an interrupted activation with the same
candidate bytes, rather than generating another authority for that version.

Twenty-three real Node producer/client tests pass. The new proof moves an actual
HTTP TUF client from root 1 through roots 2 and 3 and downloads unchanged inert
artifact bytes. It also covers distinct-key refusal, missing signatures, skipped
versions, stale root pins, interrupted activation, pending-publication refusal,
abandoned sequences and edited root history. Only temporary fixture authorities
are generated. Production root custody, online-key migration, CI provisioning and
public root/feed publication remain open.

The shared coordinator now accepts an explicit `revalidate(stage)` guard before
preparation, before any reserved peer drains, and after independent installer
readiness immediately before the durable apply intent. Only literal `True`
permits progress; changed consent/selection, withdrawal, unavailable fresh
authority or an exception cannot send APPLY. Before shutdown, live reservation
cleanup preserves work. After shutdown, the original drained record remains for
independent source inspection/recovery and cannot be replayed. Fixed-artifact
legacy qualification callers can omit this hook; omission does not establish
publisher authority for a downloaded artifact.

`AutomaticInstallAuthority` is now the independent coordinator's live guard.
It requires a qualified installed receipt, current download/install consent,
the exact selected release and complete verified downloads. Each apply boundary
refreshes the authenticated catalog through the installed bundled Node runtime
with a 30-second deadline, sharing the service's retained TUF cache/rollback floor.
It rereads consent and installed identity after the refresh. Removed, withdrawn,
changed or unavailable publisher authority refuses apply. Artifact descriptors
remain held: Windows denies writers/deletion; POSIX additionally rehashes the exact
signed length at each boundary because file timestamps alone cannot prove unchanged
bytes. A closed guard cannot be replayed.

The service and guard share `services/updates/client.py`: fixed helper location,
bounded request/reply/progress and deadline (including blocked request writes),
removed Node preload environment and cancellation of only the owned child.
The installation guard ignores runtime environment overrides. External installer
entrypoints still need to compose this guard with independently verified source,
admission/drain, actual apply and independent health/recovery. No current receipt
enables automatic installation. Synthetic catalog-reader tests establish guard
ordering/refusal, not public-feed or installed upgrade acceptance; the separate
Node suite exercises real publisher/client cryptography and transfers.

Windows independent inspection now also identifies the proposed target, using
metadata and inventory extracted from that exact installer outside the replaced
payload. `target-health` requires a matching apply-authorized journal, retained
native writer/record pins, complete inventory and fixed isolated native health.
It cannot turn target metadata into previous-source recovery authority or archive
the journal. Actual installer-exit observation, installed selection verification
and external completion remain required. Eight portable source/target assessment
tests pass; native template target-health checks pass both CPUs at `1882338` in
[37115087292](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37115087292).
Downloaded reports include the target/source-separation stage. Full-application
target-health checks remain pending. The template uses a different synthetic previous-source identity for
read-only binding, and does not establish an actual cross-version application.

`services/lifecycle/observer_runtime.py` now stages a private external Windows
observer runtime. The caller first identifies source metadata/inventory and holds
startup/installation read admission. The entire source payload must match that
inventory; selected Python, service and fixed Python-script files are copied and
hashed against it into a fresh private directory outside the app. No user-data
tree is copied. A final receipt binds both source metadata digests, and verification
requires the exact copied subset without missing or extra entries. Partial attempts
remain private and cannot be launched through verification. Five inert portable
tests include actual source-directory displacement, corruption and partial writes.
Native template relocation and identity-import checks pass both CPUs at `536e875`
([run 37118685817](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37118685817));
the full-runtime checks remain in progress at that head. Staging itself executes no
code and grants no install authority. The macOS temporary fixture now resolves its
test-owned `/var` alias before exercising the unchanged no-link production boundary;
the corrected native Mac checks are still required.

The Windows installer now exposes read-only live observation transfer to a bound
same-user external process. The receiver validates the actual primary image and
Job relationship, exact private retained artifact and non-killing Job before
observing exit. It cannot forward the transfer or authorize/terminate Setup.
Native template qualification at `536e875` passes the same-process adoption and
sender-close case on both CPUs. The newer `windows_update_observer.py` connects a
separately launched coordinator to its actual parent over a fresh private pipe.
The parent binds the exact live primary process/Job and launch nonce; it adopts
read-only Setup capabilities against its independently verified target digest and
length. No raw handles/nonce or Setup PID is saved to authorize recovery. The
coordinator requires confirmed retention and a live parent again at APPLY. Loss
of a transfer or acknowledgment causes refusal/unknown outcome, never replay.
The parent observes actual coordinator and complete Setup Job exit; observation
alone neither completes the journal nor verifies installed target health.

`updates/windows_coordinator.py` now composes actual source integrity/selection,
fresh TUF/consent authority, journal, Windows graph preparation and observed native
APPLY. Its fixed external `windows-update-coordinator.py` entrypoint accepts no
arbitrary installer/command and uses the compiled per-user installation. Source
startup readers are released before acquiring the graph writer; the lifetime
reader stays until coordinator exit. External worker Jobs explicitly allow the
separately observed Setup to break away, without kill-on-close. The fixed launch
wrapper verifies the entire staged source subset before starting that worker.

Both exact-template and full-application native fixtures now use separate-process
observation and whole Job exit instead of polling a saved Setup PID. These newer
fixtures and the fixed production coordinator require fresh native qualification;
the full fixture remains same-build, uses disposable data and omits publisher
authorization. Five portable wrapper fault cases pass (unready Setup, missing
observer, departed parent and lost native/parent acknowledgments). The focused
updater set now passes 109 cases (108 passed, one OS skip). Supervisor/service
launch integration, independent target completion and actual signed N-to-N+1
qualification remain open; no build's automatic-install flag is enabled.

The separate-process exact-template cases now pass both CPUs at PR head `5d9c0ef`
([run 37119738791](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37119738791)),
with sixteen recorded template stages. This uses native private Python/bootstrap
and inert application components, not full application or cross-version evidence.
That workflow still fails overall on x64: a separate WinSparkle negative-metadata
case correctly recorded `callbackFailed`/no handled download, then hung joining its
modal error UI. The disposable fixture now dismisses only its own windows throughout
bounded native cleanup; fresh qualification is required. macOS 14/26 and Windows
Desktop x64/ARM64 both pass the same head (37119738882 and 37119738796).

The newer `windows_completion.py` now observes the same trusted target installer's
read-only target-health mode after actual coordinator/Setup Jobs exit. Native reports
include the independently extracted inventory digest as well as the release digest.
The parent requires exact original candidate build/protocol/component identity,
retained installer selection, all inventory bytes and local Qt health. It reacquires
startup/installation read admission and the journal writer before completing.
The live coordinator also sends its exact acknowledged transaction ID and record
digest before exit; neither a later same-pair journal nor a changed snapshot can
complete this original attempt. The journal pin closes before durable archival,
while writer/read admission stays held. Failed/unknown inspections preserve the
active record and cannot launch normal application work or restore/replay.

Four portable report-binding cases and three live-writer snapshot cases pass;
the focused updater total is now 116 (115 passed, one OS skip). The full native
same-build fixture now calls this completion path using a numbered **unpublished
development fixture** (sequence 1, customer distribution/automatic qualification
false). It needs fresh native qualification and is never a public build sequence
or signed feed input. Full forward signed N-to-N+1, supervisor launch and appropriate
instance reopen remain unfinished; the manager still cannot offer installation.

### Source launch handoff and completion-log correction

The next source checkpoint adds a fixed `start-update` supervisor action. It
accepts no installer, URL, command or PID. Short source startup admission checks
the shipped bootstrap script and private Python against the complete inventory;
the external bootstrap then checks the whole payload and live automatic authority
before staging exact code outside the installation. Source readers end before the
external parent starts. The supervisor drops its source-Python file observation
after launch, so it cannot accidentally prevent replacement while being drained.

`windows-update-observer.py` authenticates its actual source bootstrap through a
fresh private pipe/nonce, retains a read-only kernel process handle, and requires
that process to exit successfully before inspecting source or launching the
coordinator. A release message or recorded PID alone is insufficient. The
external parent holds a kernel lock through signed selection, coordinator/Setup
exit and exact target completion; closing a Job observation never kills an
installer. The new native inert proof delays the real launcher's exit and checks
both successful exit and nonzero refusal. It exercises this kernel fence only,
with no installation/publisher authority; native results are pending.

Signed target catalog entries now accept the strict optional boolean
`automaticInstallQualified`. Automatic authority requires exactly `true` for the
selected target as well as qualification of the source. Missing/false entries
remain valid manual downloads. Neither a numbered build nor a signed manual
download inherits automatic-install permission. Existing public catalog/tooling
uses the same schema; no current build/feed is enabled by this addition.

At `2ac4f16`, Windows Desktop, Windows installer feasibility, macOS 14/26 and shared
validation pass (37122108435, 37122108457, 37122108698, 37122108647). Full Windows
qualification 37122108472 fails x64 at the new completion reader's 1 MiB log limit:
Inno extraction diagnostics for the full bundle exceed that size before the small
health JSON is read. The new reader streams diagnostics with a separate 128 MiB
total/128 KiB line bound, retaining the original 64 KiB typed report and exact
identity checks. Duplicate, missing and oversized reports still refuse; three
portable tests cover large diagnostics and those bounds. The full fixture now
preserves its independent inspector logs on failure. Fresh native completion
qualification is required; no passing health is inferred from installer exit.

This source checkpoint passes 120 focused updater cases (119 passed, one OS skip),
seven portable supervisor cases (two native skips), and all 19 real Node
publisher/client cases. Automatic scheduling of installation, result/deferred
reporting, appropriate instance reopen, cache retention, signed N-to-N+1 and the
other installation adapters remain unfinished. The manager still offers manual
downloads only. The complete authorized implementation goal remains active.

The branch now merges public main `550e274`, retaining paired SDK alignment,
workspace settings isolation and native SDK package qualification. The settings
merge adds Updates to the SDK administration exclusion; standalone update controls
are retained. Combined source build/type/privacy checks, 529 Node cases (527
passed, two skips), all 92 Browser cases, and 894 Python/Qt cases (855 passed,
39 explicit OS/integration skips) pass. Tests use locked DSH and isolated
offscreen Qt/dictation state. The first broad Node invocation omitted those test
dependencies and was stopped after fixture failures; it is not counted as a pass.
Native package qualification must rerun on the combined merge.

Shared repository-helper operations now hold one private kernel cache-writer lock
across the entire child operation. This prevents service/coordinator concurrency
from overwriting a newer observed TUF rollback floor with older metadata. Waiting
for that same lock counts against the operation's deadline and supports cancellation;
a cancelled/timed-out waiter launches no helper and never stops the current owner.
The focused updater set passes 104 Python cases (103 passed, one OS skip), including
actual competing child requests and preservation of the original live helper.

Full Windows qualification at `97837de` passes x64 but ARM64 recovery reaches its
old five-minute observer deadline in
[37112769947](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37112769947).
Downloaded inner Setup logs show successful installation just beyond that limit;
the observer correctly preserves the active recovery and does not replay Setup.
The actual-Setup observation limit is now ten minutes, with a twenty-minute native
outer-observer limit to leave time for inventory/health. The fixture's outer bounds
and CI allowance are increased separately. Fresh native recovery qualification is
required; a completed Setup log alone does not prove health or journal completion.

A private exclusive publisher lock and durable pending claim prevent simultaneous
or uncertain publication from reusing a role version. A permanent private artifact
ledger retains identities even after withdrawal or an abandoned attempt.
`recover --keys <private-folder> --out <exact-pending-output> --sequence <N>
--decision finalize` rechecks all role signatures, snapshot/timestamp references,
both catalog schemas, the exact root and permanent artifact identities before
advancing the private checkpoint. `--decision abandon` preserves the partial
directory and consumes that version forever; the next publication uses N+1 and
retains the last confirmed catalogs. Either decision leaves a private immutable
audit record. An uncertain audit/checkpoint write cannot be replaced with a
different recovery decision.

Recovery never evicts a publisher lock automatically. After a killed process, the
release owner must first verify that every signing process using that key folder
has stopped and explicitly quarantine its stale lock. A surviving or possibly
live writer blocks recovery. A lost/corrupted private checkpoint or ledger is not
recreated from unauthenticated public metadata. Interrupted initial key generation
still requires offline owner recovery; root rotation and portable CI provisioning
remain in progress. No real publisher
keys have been generated or public feed uploaded by this checkpoint. Synthetic
publisher tests exercise the complete producer → HTTP → installed TUF-client
path, independent root custody, online-only refresh, immutable asset refusal,
tampered history, private permissions, concurrent-writer exclusion, interrupted
checkpoint/output writes, exact recovery, skipped versions and withdrawn URLs.

## Discovery and signed delivery

The installed [`release/updates.json`](../release/updates.json) currently has
`enabled: false`. The fallback discovers public releases through the canonical
GitHub API, including prereleases for the preview channel, and selects exact known
asset names for the host CPU. It filters drafts and the other channel. GitHub
asset SHA-256 plus exact length detect corrupt manual downloads. This is HTTPS
public discovery, **not publisher-signed installation authority**. Unsupported
targets return no candidate; no x64 installer is offered to an ARM64 user.

`services/updates/repository.mjs` integrates pinned `tuf-js` 6.0.0 and
`@tufjs/models` 5.0.0. The maintained TUF client verifies root, timestamp, snapshot,
targets, expiry, version rollback and artifact identity. The adapter adds bounded
HTTPS transfers, cancellation, atomic private cache writes and exact official
artifact paths. Production cannot enable the test-only loopback transport through
a request or configuration. Enabled repository configuration must use the fixed
official artifact host and the `augmentoragent.com/updates/` metadata/catalog
namespace with a bundled initial public trust root.

An enabled signed feed fails closed: unavailable, expired or invalid metadata
does not fall back to an unsigned installer. The catalog schema
`augmentor-update-catalog/1` identifies version **and build sequence**, exact source
commit, release channel, OS/CPU, installation method, minimum OS/updater, protocols,
readable data schemas and required component hashes/sizes. Debian requires runtime,
desktop and Browser as a set; Mac and managed Linux need a bundle; Windows needs
its installer. Withdrawn, incompatible, partial, ambiguous or unsafe entries are
rejected. A signed selected digest must still agree with TUF targets when downloaded.

The catalog does not itself establish runtime health or authorize data migration.
Protocol/data compatibility changes require an explicit migration route. Linux
catalog entries require an explicit map of supported Debian/Ubuntu/Fedora version
floors; the kernel minimum is checked separately. Unknown distributions fail
closed for signed selection. Those declarations still require actual installed
distribution qualification before automatic installation can be enabled.

## Verification and remaining integration

Code checkpoint: `dc814c224c8d37e740d2806372bfb9ee61fb49b0` on
`feat/automatic-updates`. Linux source verification passed build/type checks,
version synchronization and the private-source boundary. Full Node suite: 513
cases, 511 passed and 2 explicit skips. Full offscreen Python/Qt suite: 839 cases,
803 passed and 36 explicit platform/integration skips. Browser suite: 87 passed.
The update-focused Python set passed 77 cases (one existing OS-specific skip);
real TUF/transfer set passed 11. Production dependency staging collected original
notices for 236 package instances including the new TUF dependencies. The host
QtTest binding was extracted from Debian’s matching 6.8.2.1-4 package into a
temporary test fixture; system/application installations were not changed to
provide that dependency. Native control layout was checked in a 480×500 offscreen
render without clipping. These are Linux/synthetic source checks, not installed
Mac/Windows or cross-version package acceptance.

Native Windows download/owner sealing and shared Desktop regression checks pass
both x64 and ARM64 at head `632c2f394b0b0ccd21be202873d37208f6353a31` in
[37110601272](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37110601272).
[Shared validation](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37110601416)
also passes that head, including Debian staging/proofs. The existing Windows
full-application/installer fixture workflow passes at earlier head `ae8595f` in
[37108901638](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37108901638);
its same-build installer exercise does not qualify N-to-N+1 or physical devices.
Downloaded x64/ARM64 package reports identify their actual merge checkout as
`91dfb15abb3b5898438666b5182387452fe4e5f7`.
These runs predate the receipt/producer-recovery changes above; those packaging
changes need fresh native qualification and do not inherit an earlier artifact's
seal or result.
Fresh Windows Desktop checks also pass both CPUs at `8d7f500` in
[37112146918](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37112146918).
Mac updater/publisher tests pass that head, but its bundle staging caught a
source-record variable overwritten by an existing archive stream. Both Mac and
Windows stage builders now use a distinct receipt-source name; native packaging
is being rerun. No successful bundle is inferred from the passing source tests.
The corrected builders at `97837de` pass both macOS 14/26 bundled-runtime jobs in
[37112770195](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37112770195)
and both native Windows Desktop CPU jobs in
[37112769924](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37112769924).
[Shared validation](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37112770204)
also passes that head. These results precede the independent client/guard additions;
fresh native checks remain required for those additions.
The client/guard source checkpoint passes 98 focused Python cases (97 passed,
one OS skip), full Python/Qt 863 cases (824 passed, 39 explicit OS/integration
skips), full JavaScript 521 cases (519 passed, two explicit skips), and build/type
checks. Tests use explicitly isolated dictation state. The 19 real Node
publisher/client cases are included in the full JavaScript result. Native checks
for this new source checkpoint remain pending.
The later Linux source verification snapshot passes 521 JavaScript cases
(519 passed, two explicit skips) and 850 Python/Qt cases (811 passed, 39 explicit
OS/integration skips), plus source build/type checks. Subsequent isolated packaging
tests additionally verify clean source binding and real native Node root signatures
without creating private signing-key files. The focused updater suites are the
current smaller regression set; native package workflows now run them explicitly.

Focused tests use temporary private state and independently authored inert payloads.
Repository tests use real Ed25519 metadata and local HTTP transfer through the
maintained client: valid catalog/payload, corrupt cache, altered catalog/payload,
relabeled artifact, expired/replayed timestamp, untrusted signature, dual-authority
root key rotation, root-cache replacement, trusted bridge advancement, linked
cache refusal and transfer cancellation. Manager
tests cover notification deduplication, skip/postpone, failure age/backoff, settings
revision/channel races, admission, cancellation, explicit opt-in, unsafe commands,
manual file naming and recovery refusal. Qt and Browser controls are exercised
without a model connection; Browser connection tests cover mismatched handshake
and disconnect without replay.

Run source build/type checks, `node --test tests/updates-repository.test.mjs`,
the `test_update*.py` tests with `PYTHONPATH=apps/native QT_QPA_PLATFORM=offscreen`,
and `node --test apps/browser/test/update*.test.mjs`. The full suites and separate
native OS/package qualification remain required for release. A local offscreen
Qt or synthetic provider result does not establish physical OS, microphone,
signed package or cross-version installed acceptance.

Required remaining work, retained in the authorized full implementation scope:

- Provision a publisher-controlled trust root, separated signing roles, monotonic
  publication tooling and expiry refresh; publish/monitor the signed repository.
- Qualify the new build receipt/trust inputs in native packages and ship a manual
  bridge release for legacy installations; distinguish source, selected and
  running identities.
- Compose each installation adapter with the existing admission/drain coordinator,
  an external installer, durable one-shot journal and independent health/recovery.
  Recheck freshness, consent and revocation immediately before authorizing apply.
- Preserve matching Browser/DSH/voice components and immutable Linux deployment
  selection. Unpacked Chromium extensions require explicit reload.
- Qualify N-to-N+1 upgrades, refusal during accepted work, power/process interruption,
  full recovery and native CPU execution across supported distribution/OS methods.
- Document/verify automatic consent and user postponement through actual installation,
  and disclose hosting requests/disk retention in the installed user guides.

Existing mechanisms: [immutable Linux selection](DESKTOP-DEPLOYMENTS.md),
[Windows signed delivery](WINDOWS-UPDATE-DELIVERY.md),
[Windows installer decision](WINDOWS-INSTALLER-DECISION.md), and
[platform parity](PLATFORM-PARITY-AUDIT.md). These are reusable mechanisms with
their own evidence limits, not proof that the new customer update flow is complete.


## Unix persistent barrier and Mac completion

Unix startup readers check the persistent `XDG_STATE_HOME/augmentor/updates`
transaction directory under startup admission. The defaults are
`~/Library/Application Support/Augmentor/state` on Mac and `~/.local/state` on
Linux. Any `active.json` entry blocks normal startup, including malformed or
linked entries; no saved record authorizes commands or automatic deletion. This
check survives loss of the temporary socket directory. Maintenance writers can
inspect a pending installation without permitting normal app work. The native
Mac launcher checks the same directory before initializing Python; bundled
Python launch paths also check it. Legacy builds lacking the barrier remain
ineligible for automatic installation. Linux entrypoint completeness and the
package/managed-deployment controller remain qualification requirements.

`MacInstallerBackend` requires its original live journal at this persistent
location before applying, and runs from code outside both replaceable bundles.
Only a successful native replacement return can establish its live `applied`
observation. The original caller seals the exact apply-acknowledged record before
closing its journal. `updates.macos_completion.complete_observed` reacquires
startup and installation writers, compares the original acknowledgement, checks
the retained recovery bundle and executes the exact target's isolated offline
UI health probe. It archives completion only after these checks succeed. A
changed target, unknown apply, missing live backend, failed health or changed
journal stays pending; completion cannot replay replacement or infer success
from saved PIDs. Reopening and interrupted-attempt recovery require separate
verified coordination.

The hosted disposable same-build proof additionally checks normal launch refusal
while pending, preserves the pending record after wrong-target completion, then
runs real native health and archives the attempt. A second completion is refused.
It preserves the original artifact and synthetic user state. This development
fixture is not signed forward qualification, publisher authorization, an owned
launchd/reopen controller or an installed customer update. Public automatic flags
remain false until those release gates are met.
