<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Shared application updates

## Current status — October 4, 2026

The shared check/notification/download service and external installation
controllers are implemented on `feat/automatic-updates` in draft PR 32. Public
feed and automatic-install eligibility remain disabled; no owner installation
has been updated. Disposable installed-app evidence below is separate from
customer distribution. Older checkpoints retain their source-specific history.

| Installation | Implemented controller | Latest qualified scope and remaining boundary |
| --- | --- | --- |
| Windows per-user Inno, x64/ARM64 | Independent retained observer, complete component graph, Inno apply, offline completion and captured reopening | `c40926b` full run 37170465430 passes all 24 stages on both CPUs. Later `07c05af` desktop run passes junction/session admission. Signed forward N-to-N+1 remains unqualified. |
| Linux managed per-user Desktop, x64/ARM64 | Immutable staging/selection, owned registrations and user services, completion and reopening | `0bc9639` complete native archive/relocation/Qt/portal/Handy proof passes both CPUs; service migration has separate native evidence. New full-observer cleanup at `b438ad8` passes host tests; fresh native bundle run 37174399503 is executing. |
| Mac per-user Desktop bundle | Whole-bundle staging/replacement, persistent startup barrier, independent health and captured reopening | Prior Mac 14/26 bundle/controller evidence passes at `69477f8`; native follow-up 37174398113 at `b438ad8` is executing. Shared/system/Companion coordination and signed forward delivery remain open. |
| Package-managed Linux, shared/system installations, custom profiles, SDK-owned hosts | Compatible discovery/manual download; installation defers where ownership cannot be coordinated | Privileged/shared-user and SDK owner lifecycle adapters require further work. A running SDK owner is preserved before any shutdown. |

Real signed metadata and inert HTTP downloads now join Python installation
authority in two passing host tests: fresh withdrawal and damaged signatures
prevent installation. Complete Unix observer cleanup also has real kernel/file
and copied-ELF exit evidence. These checks do not substitute for distinct signed
forward releases, legacy bridge delivery, recovery/stage/backup retention or
production signing/feed provisioning. See the latest detailed sections for exact
refs, artifacts, fixture limits and pending native results.

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
Public apply requires the exact transaction directory ordinary startup checks;
custom fixture directories are accepted only for explicit development inspection.
Only a successful native replacement return can establish its live `applied`
observation. The original caller seals the exact apply-acknowledged record before
closing its journal. `updates.macos_completion.complete_observed` reacquires
startup and installation writers, compares the original acknowledgement, checks
the retained recovery bundle, validates both actual build receipts and executes
the exact target's isolated offline UI health probe. It archives completion only after these checks succeed. A
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

## Managed Linux artifact retention and lifetime

The existing immutable deployment tool copies a bundled `python/` directory and
rewrites a source-relative interpreter path into the staged release. Its full
inventory covers those bytes and blocks selection if they subsequently change.
Existing external interpreters retain their explicit paths; the updater does
not change a user's Python installation or infer bundled-runtime qualification.

Managed Linux code with a reviewed `release.json` and its exact fixed-root
`desktop-release.json` uses the private per-user installation lease, plus the
persistent pending-transaction launch check. It does not query dpkg/rpm or take
system package locks. A moved managed artifact is refused before obtaining the
lease. OS package paths retain their existing package-owned admission/configuration
checks. The three isolated Linux fixtures exercise actual kernel contention,
pending-record preservation and moved-artifact refusal; eleven deployment fixtures
cover immutable interpreter retention and damaged-candidate refusal. The focused
updater set passes 155 cases (154 passed, one OS skip).

This is part of the authorized complete Linux adapter work, not its completion.
Independent signed-bundle staging/controller, complete runtime/voice ownership,
target health and reopening still require implementation/qualification. Legacy
overlays and unqualified source receipts cannot opt into automatic installation.


Native health checkpoint: `faca8b5` passes the complete package/whole-bundle
retention/same-build apply/offline target-health step on Mac 14 and Mac 26 in
[37141250126](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37141250126).
Mac 14's complete workflow job passes; remaining Mac 26 distribution checks are
running. This precedes the persistent startup barrier/completion and managed
Linux additions, which require their own newer native qualification.


The complete Mac 14/26 run at `faca8b5` now succeeds in 37141250126, including
target health and later distribution checks. Newer code checkpoint `b285823`
(persistent barrier, live Mac completion and managed Linux lifetime) awaits
[37143117713](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37143117713).
SDK contracts at `56a8f17` pass
[37142662043](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37142662043);
shared/Linux packaging remains running in
[37142662036](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37142662036).
No owner application or public automatic-install flag is changed.


## Mac retained controller checkpoint

The shared manager now has a fixed Mac bootstrap/observer adapter for a private
per-user `~/Applications/Augmentor Agent Desktop.app` installation with the
canonical profile/runtime paths and a writable destination volume. The home
must exclude other users; shared `/Applications`, custom profiles and companion
installations retain manual downloads while their installation coordination is
unfinished. This avoids treating a per-user process lock as proof that another
user has closed a shared application. No installation or home permission is
changed to make it eligible.

The source launch verifies the complete distribution bundle before starting only
its fixed bundled bootstrap. That fresh child waits for its attempt identifier
to be saved by the manager, verifies fresh TUF/consent/download authority, retains
an exact complete source copy and checks the copy/original again. It then execs
the retained interpreter outside replacement, keeping its original private
bootstrap lock through exec. The observer checks its actual kernel executable,
its imported code location and the inherited lock's actual inode. Neither saved
PIDs nor a status receipt can grant apply authority.

The retained observer validates the source/copy and independently retained
candidate. Mac automatic composition accepts exactly one bundle artifact;
additional components require an explicit plan. It copies the exact signed ZIP
bytes into a private destination-volume stage, bounds ZIP/ZIP64 directory
allocation and expanded size, rejects unsafe paths/collisions/external links and
writes through links, and verifies local headers against central names before
native extraction. It checks available space, the real signature/team, exact
packaged target and full candidate receipt. Metadata reads are bounded ordinary
files. Legitimate framework links and product resource sidecars remain supported.

`MacCoordinator` composes renewable reservation, captured instance names, normal
kernel-observed drain, fresh publisher/consent checks, one-shot atomic replacement
and exact acknowledgement. Independent offline target health then archives the
transaction. Reopening requires that original live backend, its actual captured
plan, the exact completed archive and the still-verified target. Only the fixed
native launcher and captured names are used; no saved commands or actions are
replayed. Existing launchd registrations remain untouched. Their persistent
pending guard prevents normal work before completion; removing/disabling a
registration during the update remains the user's choice. Unpacked Browser
extensions still need normal explicit reload.

Known reversible pre-drain cancellation reports deferral; uncertain drain/apply
or completion remains blocked and preserved. A reopening error retains observed
target success and asks for a normal reopen. The public entrypoints expose no
development switch. Producer/consumer release qualification and feed remain
disabled, so this checkpoint does not install a customer update.

Verification: 164 focused updater cases pass (163 passed, one OS skip); the broad
Python checkpoint passes 942 cases (902 passed, 40 explicit skips), using isolated
Qt/dictation state. Six real ZIP/path cases and three location/profile cases are
included. The native fixture now runs the actual coordinator/completion, checks
the produced ZIP, refuses unobserved reopening, then execs its disposable retained
runtime with the original lock. The production observer must refuse its explicit
development bundle before source inspection/drain/apply. This native checkpoint
is pending; it is not signed N-to-N+1, captured normal-window reopening or real
launchd acceptance. The earlier `b285823` persistent barrier/completion passes
Mac 14/26 in 37143117713; `56a8f17` shared/Linux packaging passes in 37142662036.

Remaining full-scope work includes shared-system/companion Mac coordination,
actual captured-window/background-owner acceptance, interrupted recovery/reset,
bounded observer/stage/backup retention, Linux controllers, approved signing
custody, public feed/bridge and signed forward qualification. Pending and unknown
runtime/stage evidence is retained until independently safe cleanup is available.


Mac controller qualification at `882dd23` fails the new produced-ZIP count check
on both Mac versions in 37147847618; Windows Desktop both CPUs and SDK pass that
source (37147849267, 37147853195). The end record's count differs from the parsed
directory. The corrected boundary walks actual central records before standard
parser allocation, validates each record length/volume and actual entry/byte
limits, and requires exact counts or an exact 16-bit wrap without ZIP64. It also
handles a valid exactly-65,535 entry archive without requiring a ZIP64 locator.
A real 65,536-entry fixture validates the wrapped representation and refuses a
changed counter; seven real ZIP cases and the 165-case focused set pass. The
native report now includes actual/end counts, ZIP64 and wrapping diagnostics.
Native rerun is required before claiming produced-archive compatibility or later
controller/exec acceptance. Paths/local headers/links retain their separate checks.


## Managed Linux live selection controller — October 3

The managed adapter now composes retained preflight, Unix reservation/drain,
one-shot immutable selection and independently observed offline completion.
`updates.linux_managed.ManagedPlan` holds the existing deployment writer before
reading the exact selected bytes. It bounds release descriptors, verifies the
original deployment inventories, and records whole-tree content/mode/directory
snapshots of both releases. Public use requires qualified receipts, bundled
interpreters and the canonical immutable release store. Downloaded descriptors
cannot change existing profile, endpoint or service ownership fields.

The candidate's authenticated DSH product/catalog check runs **before** graph
preparation, while the existing integration is available. A mismatch refuses the
plan before any shutdown. Subsequent checks surround each fresh authority refresh
and repeat offline imports/integrity. They do not waive the original exact product
version check or invent compatibility from a stopped server. Upgrades needing a
new DSH integration/preset require an explicit coordinated migration plan.

`LinuxCoordinator` uses the existing live Unix preparation/journal protocol and
captures only observed instance names. `ManagedBackend` takes the final exclusive
installation lease and requires this journal's exact live apply intent. It writes
`desktop.previous.json`, then atomically fsyncs `desktop.json`; immutable source
and target survive. A namespace flush failure after replacement stays unknown,
cannot retry, and preserves the persistent startup barrier. The original returned
apply seals the acknowledged record; completion verifies that exact record, both
selections and both immutable trees around the fixed isolated target Qt render.
Only then is the shared completed journal archived. Failed health preserves the
applied selection, source recovery and pending record; no automatic rollback or
replay occurs.

Twelve isolated Linux cases pass: the full real selection/lock/journal sequence,
live compatibility refusal, changed selection/modes, unobserved lifetime holder,
revoked pre-drain consent, failed health, publisher-owned profile refusal,
public development-receipt refusal, unknown post-replace namespace flush and an
actual target subprocess rendering the shared Qt window with a disposable
profile. A further empty-graph same-build proof stages the actual copied shared
UI/services, runs real imports, performs selection, renders target health and
archives completion without import/health mocks or service owners. Selection
failure cases use inert imports/health; the separate Qt case uses the
real copied native surface and fixed `-I -B` action. These are fixture/source
checks, not installed public N-to-N+1 acceptance. Focused updater checks pass 177
cases (176 passed, one OS skip) over `cde75ee`. The preceding full Python check passes 954 cases (914 passed,
40 skips); the subsequent added real end-to-end case passes separately.

This controller has not enabled manager eligibility. Authentic bundle staging,
retained executable handoff, existing systemd/service/preset ownership and observed
reopening remain required. Debian/RPM need package-manager authorization and
installation plans rather than this per-user selection adapter. The complete
cross-platform goal, signed forward-update qualification, interrupted recovery,
legacy bridge and production feed/signing remain open.


## Managed Linux exact bundle and retained handoff — October 3

`linux_staging` accepts one publisher-held managed Desktop ZIP with fixed top-level
`Augmentor Agent Desktop`. Shared `zip_staging` first bounds/counts the central
directory, verifies local names, and rejects collisions, traversal, privileged or
special files, external links and writes beneath links. Linux refuses Mac resource
sidecars. Exclusive ordinary-file writes precede symlink creation; there is no
`extractall` or archive-selected command. The complete archive length/hash is
checked against the retained signed row before extraction. Whole-tree inspection
then checks links, modes and bytes before any target import.

A downloaded tree cannot contain local deployment/selection records. Its exact
version/build/source/target/channel/protocol/schema receipt must match the original
publisher candidate. The retained existing `desktop-deployment.stage` constructs
configuration from the current private selection, retains bundled Python/Node,
creates a separate immutable target and leaves selection unchanged. Space checks
cover both extraction and its additional immutable copy. Changed bytes, bad
receipts, unavailable space or imports fail before selection/drain.

`linux_bootstrap` and fixed scripts now retain a whole exact source copy in a
fresh private observer directory, close original startup/lifetime/deployment
readers, and exec its copied interpreter with the original inheritable bootstrap
lock. The observer verifies the actual kernel executable, its imported code root,
exact source digests and the original lock inode before fresh TUF/consent authority.
It composes authentic stage, live managed preflight, graph/drain, pointer commit
and original offline completion. Local attempt results are status only. Production
entrypoints expose no development or arbitrary-command switch. Manager eligibility
remains disabled pending owned service/preset coordination, reopening, retention,
public producer/bridge and signed forward-update qualification.

Seven initial archive/selection cases plus additional duplicate-space refusal
pass. Two Linux handoff cases include actual copied ELF exec and inherited flock;
the production entrypoint refuses an unqualified source before any network,
drain or apply. The source, observer and private selection remain byte-identical.
These are synthetic local fixtures, not signed N-to-N+1 customer acceptance.
The source-copy and immutable-copy space checks prevent accepted work being
closed merely to discover those known disk requirements.

Fresh automatic installation verification now always uses the bundled Node rather
than an unrelated environment override; a focused authority test checks this
boundary. Ordinary developer helper selection is unchanged. Shared Unix service
discovery now matches prompt/memory's actual `AUGMENTOR_SHARED_STATE` / XDG state
location, including the installed Mac environment; it no longer guesses
`socket-runtime/shared`. Absolute-path cases qualify the correction.

At the prior native correction `cde75ee`, both complete Mac 14/26 jobs pass
[37149226481](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37149226481).
The actual ditto ZIP has 66,643 directory entries and an end counter of 1,107,
with no ZIP64: an exact 16-bit wrap. The fixed bounded parser agrees. Native proof
also passes actual retained observer exec/inherited lock and production development
refusal, same-build coordinator apply, whole backup retention, malformed/pending
startup refusal, exact offline target health and completed archival. It opens no
normal user app and proves no signed forward update or captured-window reopening.
The retried full validation at `882dd23` passes all Linux/shared packaging jobs in
[37147851279](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37147851279).

New local updater checks pass 190 cases (189 passed, one OS skip), over `cec9767`.
The earlier broad Python run passes 966 cases (926 passed, 40 skips), before the
final Node/space cases, which pass focused checks. The common ZIP extraction,
Mac discovery correction and newer controller sources need their fresh native
qualification. All public feed and automatic-install defaults remain disabled.


The managed staging allowlist now preserves the full `dsh/` runtime, including
matching speech, instead of dropping that packaged directory. Public extraction
requires DSH payload metadata and fixed CLI/speech entrypoints before imports.
One real filesystem fixture detects retained dependency damage; one public-flag
fixture refuses an incomplete bundle without importing its candidate. This does
not yet migrate existing DSH preset/host paths or restart registrations.

Fresh qualification of `3374580` is running in Mac
[37151926643](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37151926643),
Linux/shared
[37151929120](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37151929120)
and Windows Desktop
[37151931306](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37151931306).
The subsequent Linux DSH allowlist/completeness correction passes twelve focused
deployment and nine archive cases and needs its newer Linux qualification.

## Managed Linux owned registration migration

`linux_registration.RegistrationPlan` migrates only the known installer-owned DSH
Browser files, default preset aliases, literal owned host-composition entry and
bundled module links between the original inspected immutable releases. Current
file hashes, source defaults, link targets and ownership version must agree.
Edited presets, ambiguous composition entries, copied/external dependencies and
unfamiliar ownership records require an explicit migration. Other composition
entries, Browser chat configuration, model settings, tokens, conversations and
speech settings are preserved.

Managed preflight checks the original live DSH against its source version and
imports the target offline. The registration plan binds once to the complete
inspected source/target artifact pair; another journal cannot authorize writes.
Apply requires the original live startup writer and matching apply intent. It
flushes exact private before-file backups and a manifest before any registration
mutation, writes owned files/links, then switches the managed desktop selection.
Completion checks the applied registrations and retained backups before and after
the fixed offline target render. Failed writes or namespace acknowledgements keep
the pending barrier and backups; saved manifests do not grant retry or rollback.

Nine actual-file/link/journal fixtures pass, including a version-changing full
registration/selection/completion composition with mocked connected/import and
health actions. These fixtures preserve synthetic model, token, conversation and
voice settings, refuse modified ownership/defaults and unrelated release pairs,
and retain unknown post-replace outcomes. They do not restart an installed DSH or
prove target live compatibility. Focused updater checks pass 200 cases (199 passed,
one platform skip). Full Python passes 979 cases (939 passed, 40 explicit skips)
using isolated dictation/Qt state. Owned service-unit and shared harness-registration migration,
actual target DSH health, captured reopening, retention and producer/forward
qualification remain required; automatic managed Linux eligibility stays disabled.

The newer shared/native checkpoint `3374580` passes both complete Mac 14/26 jobs
in [37151926643](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37151926643),
all Linux/shared packaging jobs in
[37151929120](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37151929120)
and Windows Desktop both CPUs in
[37151931306](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37151931306).
It qualifies the shared ZIP/discovery/authority changes preceding the newer Linux
dependency-retention and owned-registration work, which require fresh validation.

## Managed Linux owned user-service migration

Public managed preflight now attaches `OwnedServicePlan` to its fresh registration
plan. Only the exact complete-installer `augmentor-dsh.service`, using the source's
bundled Node/DSH, unchanged loopback endpoint and private model credential path,
is accepted. Canonical user configuration directories, the loaded fragment path,
absence of drop-ins and the user's enabled/disabled state are checked. Customized
units, external runtimes, stale loaded definitions and unfamiliar shared DSH
registrations require explicit migration. The credential file is validated without
reading or changing its contents.

The original startup writer reserves the actual DSH socket peer. Its retained
kernel observation must match the service's original live MainPID; a numeric PID
report alone grants no shutdown or migration authority. Ownership is rechecked
around publisher refreshes. Apply requires normal original process exit and an
inactive, successful service with no replacement PID. The known unit's bundled
runtime paths and the matching shared DSH version are included in the same exact
before-file backups as the presets. Other harness fields and selections survive.
After selection, a one-shot daemon reload must acknowledge the changed files while
the startup/pending barriers remain held. Offline completion checks the migrated
files, backups, loaded definition and continued inactive service before and after
the target render. A reload failure preserves the unresolved transaction and
cannot be retried from its saved phase. No stop, enable or start command is issued.

Ten isolated service cases use actual unit/shared configuration/backups/journal/
selection/archive files and explicitly simulated systemd and peer observations.
They cover complete-installer field grammar, customized units/drop-ins, mismatched
runtime/home/service PID, changed enablement, unsuccessful/restarted exits, malformed
reports, changed live service during revalidation and failed daemon reload without
replay. The combined version-changing controller case mocks graph shutdown,
imports/connection and target health. Actual user-systemd/managed artifact and target
live health/reopening qualification remain required. Public eligibility stays off.
Focused updater checks pass 210 cases (209 passed, one OS skip); full Python passes
989 cases (949 passed, 40 explicit skips) with isolated dictation/Qt state. The
final external file-mode guard also passes the ten focused service cases.
The preceding `f89b6fc` registration checkpoint passes all Linux/shared validation
jobs in [37153955607](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37153955607).
Fresh service-source checkpoint `8bc5bfb` is running in
[37154936597](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37154936597);
its results are pending. Neither workflow constitutes actual user-systemd or
signed forward qualification of this service controller.

### Native user-service qualification

The reusable [Linux user-service workflow](../.github/workflows/linux-update-service.yml)
is also called by validation. It creates a dedicated disposable `augupdatefixture`
account on a hosted Ubuntu runner, starts its actual user manager, runs the test
under that account and removes only that created account afterward. The test
requires both the explicit qualification flag and dedicated CI identity; ordinary
local/shared test discovery skips it and never writes a real user service.

`test_update_linux_service_native.py` runs the exact owned unit with an actual
copied Node executable and the shipped Unix control server. Its independently
authored inert maintenance component refuses a busy prepare, then accepts normal
reserve/drain and closes its socket to exit normally. The updater uses actual
systemd reports, socket peer pidfd, startup exclusion, graph reservations,
version-changing file/selection migration, daemon reload and completion archive.
It checks unchanged credential bytes, other harness settings and disabled service
enablement. Connected/import checks and offline UI health remain explicitly
mocked. This is a native OS/service composition fixture, not a real DSH/provider,
signed published forward update, normal GUI or reopening proof. Native execution
is pending; the local case skips because its disposable CI account is absent.

The first hosted native job at `76462aa` fails before test import because the
runner's checkout is inaccessible to the disposable user (111297907075 in
37155477755). The workflow now copies a `git archive` of the privacy-checked tracked
tree and the pinned Node executable into the account's private home, then runs
there. It copies no Git metadata or credentials. New native qualification is
required. The separate `8bc5bfb` broad validation 37154936597 fails an unchanged
dual-memory prompt-service startup after its simulated restart, before Python
updater checks; that failure remains unqualified pending a fresh complete run.

### Observed DSH reopening

`linux_reopen.reopen_dsh_observed` is called by the retained Linux driver after
independent completion. It requires the original live successful backend and
closed journal, exact completed archive/steps/revision, current managed selection,
both retained artifact inventories and snapshots, original registration backups
and inactive successfully migrated/reloaded service. Startup and installation
readers exclude another maintenance writer; any new pending attempt blocks reopening.
The fixed migrated unit receives one normal start, preserving user enablement.
A fresh target socket peer must match its live service MainPID and actual bundled
executable/root. Connected target health and immutable files are rechecked before
success. Observations are released without stopping target work. A failed or
uncertain start never grants a retry, saved archive or PID never reconstructs
authority, and an installed update remains installed when reopening fails.

Six portable cases use actual original backend, managed selection, registration
backups and completion archive with explicitly simulated graph/systemd/peer and
connected/offline health actions. They cover changed archive/target, another pending
attempt, failed start without retry, wrong target peer and changed target during
connected health. Focused updater checks before the final pending case pass 216
(214 passed, two OS/CI skips); full Python passes 995 (954 passed, 41 skips). The
final added case passes separately. Service queries explicitly include empty
properties using `show --all` with the fixed property filter.

The native fixture is extended to actual target-service reopening and fresh target
peer observation, plus wrong-completion/changed-target refusal before start. Its
provider/import/UI health remain mocked, and native execution is pending the
corrected isolated-source run. It does not reopen desktop windows or their
background owner. Those steps, real DSH/target health, signed forward producer,
retention/recovery and public feed/bridge qualification remain required. Linux
automatic eligibility remains disabled. Status observation of the remaining
37155477755 jobs timed out; a timeout is not a terminal result or restart authority.

At corrected source `bc8b256`, native job 111302228170 in 37156960807 reaches the
actual Node unit but refuses its runtime directory ownership/mode before socket
registration. The fixture adds bounded synthetic path/UID/mode diagnostics on
that failure; the shipped control server's private-directory guard is retained.
Actual migration/reopening remains unqualified pending a diagnosed native rerun.

Validation has an explicit `native_service_only` manual input for fast isolated
OS-service qualification. Its default is false: ordinary validation still runs
all existing checks. The focused mode runs privacy and the native service job;
skipped build/package jobs do not qualify broad release validation.
Focused mode uses a separate concurrency group so it does not cancel a live broad
validation of the same branch.

Focused `dc0c634` qualification 37157951783 identifies the native refusal: process
UID 1002 inherited `/run/user/1001` (directory UID 1001, mode 0700). The workflow
imports the fresh account's explicit runtime into its own user manager, and the
fixture verifies and uses `/run/user/<its UID>` for actual graph observation. No
control-server ownership guard is relaxed. New native execution is required.

At `0ed4a1b`, focused native qualification passes
[37158631483](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37158631483).
Actual test time: 10.061 seconds. Its report confirms busy deferral, original
socket process binding and normal exit, owned unit/registration migration,
daemon reload, selection completion, preserved credentials/enablement and target
service reopening. Wrong completion and changed target refuse before start;
one-shot replay refuses afterward. Actual systemd, Node executable, socket pidfd,
graph, files, journal and archive are exercised. The inert Node participant is
not a real DSH/provider; connected/import/UI health remain mocked. No normal
desktop window or background owner is reopened. Broader jobs are explicitly
skipped in focused mode and receive no qualification claim from this result.
The runtime-isolation correction is qualified for this fixture; production managed
Linux eligibility, signed forward and full release qualification remain pending.

The complete broader jobs at `bc8b256` pass in
[37156960807](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37156960807):
Debian source/build/tests, installed packages, Browser package, Home, all Handy
platforms and privacy. That workflow's overall failure is the older native runtime
fixture, separately corrected/passed at `0ed4a1b` above. The `76462aa` broader jobs
also all pass in 37155477755 except its native checkout-access fixture. These
newer source checks supersede the earlier transient dual-memory startup failure;
memory code was not altered. Different refs/scopes remain explicit.


### Owned desktop migration and observed reopening — October 4

`linux_desktop.OwnedDesktopPlan` checks the canonical installed data directory,
exact source launcher and fixed `augmentor-desktop.service` unit before binding
the registration pair. Both files join the original private backup/migration.
The target launcher comes from the inspected immutable target; customized files,
service drop-ins, stale loaded definitions and changed enablement refuse before
writes. The actual reserved main-window socket peer must match the original live
service MainPID. An inactive owner cannot adopt an externally owned main window.
Only original observed normal exit permits migration. Completion checks the
unchanged inactive owner before and after offline target health.

The retained coordinator stores the bounded captured instance names on the live
backend. Linux and Mac share only their name validator; their launch mechanisms
remain separate. After verified DSH reopening, `reopen_desktop_observed` holds
startup/installation readers and verifies the exact original completed archive,
selection, both artifacts and registration backups. It starts the fixed desktop
unit once for a captured main window and launches captured secondary names through
the migrated fixed launcher. Fresh actual target socket peers must match the live
service MainPID or original newly launched child. Target windows must report
connection and successful conversation restoration; immutable files and kernel
observations are rechecked. No saved command/PID reconstructs authority, no new
instance is invented, and a failed or uncertain launch cannot replay. The target
stays installed when reopening fails; the driver reports manual reopening.
Enablement, model choices, credentials and conversations remain user-owned.

Local evidence on this checkpoint: ten new desktop cases and the sixteen existing
service/reopening cases pass using real registration, selection, journal and
backup files, with explicit graph/systemd/process/health mocks. Focused updater
checks pass 228 total (225 passed, three OS/CI skips). These cover original peer
binding and normal exit, inactive/external owner refusal, service changes,
customized launcher, changed capture, missing DSH completion, uncertain start,
wrong target window peer and failed conversation restoration. Source/target
launcher bytes differ in the migration fixture. Full Python/native results must
be recorded at their exact tested revision.

The isolated native Linux job adds a second inert fixture using the actual
installed launcher, copied Python executable, user desktop service, named
secondary process, shipped startup/lifetime/admission primitives, control sockets,
pidfds and real managed coordinator. It exercises normal original window exits,
launcher migration, completion and fresh target main/secondary reopening. The
fixture remains independent public synthetic source: it runs no Qt window,
provider or real conversation, and connected/import/offline UI health are mocked.
Native execution is pending. Public Linux eligibility stays disabled; normal GUI,
real DSH, signed forward releases and remaining platform/package paths still need
qualification.


At source `10fdece`, full local Python passes 1007 total (965 passed, 42 skips)
in 65.802 seconds; focused updater passes 228 (225 passed, three skips).
Broad validation 37160189535 and Mac 14/26 37160188044 are running at that source.
Focused native 37160143263 was canceled by the reusable native workflow's
ref-only concurrency group when broad validation started. Its canceled job is
not a qualification result. The reusable group now includes run ID, allowing
separate focused/full parent runs on independently isolated runners to coexist.
No live broad run was manually canceled; native/broad outcomes remain pending.


Native job 111311878502 at `10fdece` in broad 37160189535 passes the existing DSH
proof, then fails the added desktop fixture before preparation: the fresh actual
persistent `state/augmentor/updates` directory is absent. The fixture now creates
it privately before use. Its normal startup/lease and coordinator use the same
persistent directory. No shipped guard is weakened. New native qualification is
required; broad/Mac jobs still running are preserved.


Focused native `134d561` run 37160387066 passes DSH and reaches actual desktop
completion; its assertion wrongly assumes main-before-secondary discovery.
Socket sorting legitimately returns secondary first. The fixture now checks
membership without replacing the original captured order. Reopening was not yet
executed. The normal installed launcher now invokes Python with `-B` and explicit
`PYTHONDONTWRITEBYTECODE=1`, including subsequent child environments. This keeps
normal imports from mutating a verified immutable release after environment
sanitization; the startup regression checks both. Native reopening and updated
local checks remain to be recorded at their exact source.


At `d1ec492`, focused Linux native qualification passes
[37160517109](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37160517109),
job 111312847964. Both tests pass in 25.028 seconds. The existing original DSH
proof remains green. The new proof confirms actual original desktop service/socket
process binding, normal main and secondary exits, migrated target launcher,
completed selection/archive and fresh target main-service plus named-window
reopening. Actual copied Python, installed launcher, user systemd, shipped startup,
lifetime/admission and socket pidfds are exercised. Enablement and credential
bytes remain unchanged; replay refuses and both immutable artifacts remain exact.
The proof's windows are inert participants, with no real Qt/provider/conversation;
connected/import and offline UI health are still mocked. Focused updater 228
(225 passed, three skips) and 31 startup/service/desktop cases also pass locally
at that source. This qualifies only the observed OS lifecycle composition,
not a signed forward update, normal desktop acceptance or full release. Broad
and Mac jobs at older `10fdece` are separate scoped evidence. Public eligibility
and feed remain disabled pending full producer/platform/recovery qualification.


### Complete managed Linux candidate producer — October 4

`scripts/package-linux-managed.py` adds the missing native x64/ARM64 producer for
the exact bundle consumed by the updater. It requires a clean reviewed checkout,
preserves the private-source boundary, stages the locked production JavaScript,
matching native Handy component and complete prepared DSH/speech graph, and
bundles hash-pinned standalone CPython 3.12.13 and Node 24.19.0. Linux Python wheels
are version/hash locked for both CPUs, including Linux Secret Service dependencies.
The installed graph must match exactly, satisfy dependency checks and import its
required GUI/audio/runtime modules. Python/npm notices remain inside the bundle.
Source/license review is still an explicit open release gate.

The producer runs the actual fixed offline Qt health action against that complete
bundle, requires unchanged immutable bytes, then exports a deterministic ZIP with
file modes and relative links. The actual download parser verifies the resulting
archive. Machine-specific selection files cannot enter the export. Every receipt
and artifact report keeps `automaticInstallQualified=false`,
`distributionsQualified=false` and `publicReleaseReady=false`; a preview build
number in CI is test evidence, not a published monotonic release. There is no
consumer-machine package install and no selected/running deployment change.

The pinned PySide6 ARM64 wheel requires glibc 2.39; its x64 counterpart requires
2.28. The provisional test targets are Ubuntu 24.04 and Debian 13, not a claim for
older Raspberry Pi OS or all Linux distributions. These boundaries come from the
[pinned wheel filenames](https://pypi.org/project/PySide6-Essentials/6.8.2.1/#files).
Standalone Python includes its interpreter/stdlib but still has declared C-runtime
requirements ([upstream distribution format](https://gregoryszorc.com/docs/python-build-standalone/main/distributions.html)).
Host desktop/audio libraries, normal GUI, real DSH, full sources/notices and
signed forward installation remain release qualification work.

Eight local boundary cases pass: actual safe interpreter-link extraction, unsafe
paths/types/duplicates/external-link refusal, exact ZIP roundtrip through the real
Linux consumer, repeatable bytes, rejected local selection/external product links
and locked graph/CPU qualification invariants. These are small synthetic trees;
they do not prove a complete runtime build. The new reusable native workflow builds
both CPUs, using matching Handy artifacts, then runs the real full ZIP consumer,
relocated interpreters and fixed offline Qt health in a temporary private profile.
Only scoped JSON reports are uploaded; no bundle is publicly released.
`managed_linux_only` dispatches this scope through `validate.yml`; native-service,
managed-bundle and full scopes have separate parent concurrency groups. Full
validation includes both native bundles. Native producer execution is pending.


At `10fdece`, both full Mac 14/26 jobs pass in
[37160188044](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37160188044).
All non-native broad jobs pass in
[37160189535](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37160189535):
Debian source/build/tests, installed packages, Browser package, Home, Handy all
three existing platforms and privacy. Overall failure is only the older native
fixture's missing persistent directory; corrected native source `d1ec492` passes
separately. This establishes the shared captured-name validator on both Macs,
with the existing signed-forward/normal-GUI limitations unchanged.

At `2bd7759`, actual Linux x64 runtime input preparation downloads/verifies the
pinned Python archive and installs exactly 22 locked packages in an isolated
staging directory. Dependency checks, required imports and notice inventory pass.
The actual fixed offline Qt health action renders the shared preview at 424 × 484
with fonts and immutable files verified. No model/provider or normal desktop
controller runs; DSH/Node/Handy are absent from this input-only fixture. This does
not qualify the full bundle. Native managed run 37161745635 remains live: x64
Handy passes, while ARM64 Handy is building before the full bundle jobs can start.
The source copier excludes local dotenv files, outputs and traces as well as
bytecode and dependency/test trees; these are never candidate inputs.


Candidate application sources are now exported from the exact tracked Git commit
before copying; ignored local files with arbitrary names cannot enter that source
snapshot. Generated JavaScript and verified native/dependency artifacts remain
separate build inputs. The checkout/ref is checked again before final export.
A ninth boundary case uses a real synthetic Git repository to prove an ignored
private-state file and Git metadata are excluded while tracked code is preserved.
These checks do not establish complete clean-build or upstream-binary provenance;
those review gates remain explicit.


Managed run 37161745635 at `2bd7759` finishes both Handy CPU jobs successfully:
x64 111316467327 and ARM64 111316467332, including actual component lifecycle
proofs. Bundle jobs 111319334939/111319334927 fail before assembly on an invalid
`apps/browser` npm build command. That package has no build script; its plugin
`dist/index.js` is tracked, as in the established packagers. The invalid step is
removed. Complete native bundle qualification remains pending a corrected run;
the successful component results do not establish bundle/update qualification.

Managed run [37163111736](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37163111736)
at `2799ef3` passes both Handy lifecycle jobs. Complete bundle jobs on ARM64
(111320650528) and x64 (111320650556) assemble the locked runtimes, application,
Handy and DSH/speech, then pass immutable offline Qt health. Both fail at the
final ZIP path expression before export; local x64 reproduces the same failure.
The path construction is corrected. Archive staging/relocation remains pending;
these assembly results do not qualify installation, signed updates or a public
release. All automatic/public/distribution flags remain false.

The local complete ZIP at `0663a6f` exports but its parser rejects bundled Python
terminfo names that legitimately differ by case (`A/a`, `Eterm/eterm`). The Linux
bundle now uses case-sensitive normalized path identity; fixed Mac `.app` bundles
retain case-folded collision rejection. Duplicate paths, link-ancestor writes,
unsafe paths and bounds remain rejected; Linux extraction uses exclusive file
creation. Actual local ZIP inspection passes 72,403 entries / 1,491,988,463 expanded
bytes with ZIP64 after this correction, but its producer run did not complete a
manifest and no staging/installation qualification is claimed. Eleven Linux
producer cases and seven existing Mac archive cases pass. The corrected full
producer/consumer qualification remains pending.

At `42e2e05`, complete local Linux x64 production assembly/export and the real
`stage_download` consumer pass. The ZIP is 648,425,856 bytes, expands to
1,491,989,961 bytes, and has SHA256
`d4ae8da4ed0b64379d5b2f75a9bca804f91f5ae9f70635cc8cdf21ac60071628`.
Bundled Python/Node paths relocate; fixed offscreen Qt renders at 424 × 484 with
fonts; original/final payloads remain immutable; the isolated existing selection
is unchanged. No installed controller, live provider, normal GUI, or signed
forward update is exercised. Native both-CPU run 37163782548 remains pending.
Eleven Linux producer and seven Mac archive cases pass. Host core updater checks
pass 237 total/234 passed/three OS skips in 7.114 seconds; the two Qt settings
cases pass separately on pinned bundled Python/Qt. Host full discovery initially
fails because system PySide lacks QtTest; bundled-Python full discovery instead
fails the host-only copied-ELF fixture, which copies an interpreter without its
standalone libraries. These environment-specific runs are not recorded as full
suite passes. Final core/settings checks use their appropriate interpreters.

A concrete remaining real-desktop gate is the persistent dictation broker:
`services/dictation/server.py` holds the Unix runtime installation lease after
starting Handy. `PosixPreparation` discovers windows, shortcuts, Browser, DSH and
companions, but not this authenticated broker. Window maintenance closes directly
without the interactive Quit path's broker shutdown. Real broker reservation,
active dictation/model-work deferral, observed normal exit, startup exclusion and
safe reopening need qualification before automatic eligibility. Preserve the
owner's active broker; inert window/service fixtures do not cover this gap.

Native complete managed Linux producer/consumer qualification **passes on both
CPUs** at `42e2e05` in
[37163782548](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37163782548):
x64 job 111322629852 and ARM64 job 111322629828. Both real pinned application,
Python/Qt/Node, Handy and DSH/speech assemblies pass fixed offline UI health;
complete exported ZIPs pass the bounded parser and actual archive consumer.
Bundled runtimes relocate, original selection stays unchanged, and original/final
payloads stay immutable. Downloaded CI reports independently match exact artifact
hashes and source revision, with all public/automatic eligibility flags false.
This supersedes the export failures/pending statements above for this producer
and staging scope only. It does not exercise live providers, normal windows,
an installed update, signing trust, N-to-N+1, other distributions or older Pi OS.
Only JSON reports are retained publicly; no product archive is released.

CI x64 archive: 648,682,096 bytes, SHA256 `1c9e7084f0dd0a7dec4f8c9fb430a2dfa6436977335901f140084aa5b1b4778a`.
CI ARM64 archive: 614,281,445 bytes, SHA256 `0290f4712b394f4d06019155905cdac1c87f0da81cb907f78509ebd6d1492750`.
Local and CI artifact bytes differ; deterministic export is asserted only for
identical input trees, not complete reproducible upstream builds. The native
producer receipts retain distribution/source-license/production/feed/bridge
and installed acceptance gates. Continue dictation-broker coordination and real
DSH/desktop/signed-forward qualification, plus the remaining cross-platform work;
the complete updater goal remains active.

## Dictation participation in automatic updates — October 4, in progress

The persistent broker now exposes a private same-user Unix maintenance endpoint
bound to its actual interpreter/PID, installation root and current login/state
scope. Startup exclusion covers publication of both control endpoints. Its
installation lease lasts for the broker process, including disabled Handy.
Unix preparation captures/reserves it after surface admission closes and drains
it before downstream services. Another session/state/root is refused, preserving
its work. Original captured broker presence is an optional boolean reopening
field; no saved command, environment, path or PID can grant restart authority.

Broker admission fences ordinary requests and external shortcut callbacks. Idle
preparation acquires Handy's existing atomic microphone CAS without changing
enablement, shortcut, model or palette. A live voice owner, recording,
transcription, model operation/download or unknown model outcome defers. Download
admission is tracked across the native asynchronous reply gap. Cancellation/expiry
releases only the matching native token before restoring normal admission.
An unknown native acquire/release retains closed admission and original evidence;
late acquire requests carry a two-second native admission deadline. Commit is
one-shot; owned native stdin closes only after idle reservation, child exit is
observed without termination/kill escalation. A child shutdown timeout keeps the
broker alive/closing and prevents apply.

Linux/Mac reopening within the original verified completion starts only the fixed
target broker once, checks the new actual socket process/readiness and unchanged
target, then allows normal captured-window startup. This also restores an
original broker without reopening an uncaptured window. A failed start is not
retried or stopped; the installed target remains selected for manual reopening.
Windows shares broker admission but still needs its broker discovery/startup/
lifetime/reopening adapter before full parity. Old uncoordinated broker builds
require manual bridge delivery; public automatic eligibility/feed remain false.

Local evidence: ten broker cases pass, including an actual disabled broker,
authenticated voice owner, kernel socket pidfd, busy cancellation, complete real
graph drain and one-shot target process reopening in isolated state. Native
recording/download/unknown cases use declared backend mocks. Existing fourteen
dictation cases pass; combined host updater/dictation checks pass 261 total,
258 passed/three OS skips in 8.044 seconds. Settings Qt cases are outside this
host run. An actual copied Handy executable separately proves native-owner
exclusion, CAS reservation, broker fencing, reversible cancellation, settings
preservation and ordinary native child exit without audio capture/model download.
Native CI and shipped-bundle/signed-forward acceptance remain pending; this is
not qualification of an installed customer update.

Source `d0fad01` is committed/pushed for this broker checkpoint. Local actual
Handy maintenance passes with isolated display/D-Bus/state and no microphone/model
work; the final real-broker case also proves other-session refusal, startup-writer
exclusion and immutable source bytes across reopening. Full shared/Linux CI is
running in [37165335018](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37165335018),
including x64/ARM64 Handy, actual native broker admission and complete bundles.
Mac 14/26 qualification is running in
[37165336524](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37165336524).
Handy Mac/Windows also run the actual native CAS/broker proof. Preserve those live
runs; no CI success or installed/signed-forward update is claimed yet.

Native run `d0fad01` passes actual Handy maintenance on Linux x64
(job 111326987805), Linux ARM64 (111326987814) and Windows (111326987824), plus
Linux owned-service and ten broker cases (111326987941) in 37165335018. Its Mac
job 111326987806 and separate Mac dependency 111326969946 in 37165336524 fail
on the first broker-to-Handy status request: cold native startup exceeds the
ordinary 15-second RPC deadline. The existing component proof passes with its
90-second startup allowance. Backend startup now uses that same bounded
90-second allowance only for its first status; subsequent RPC limits/replay
policy are unchanged. Both runs are terminal. Native Mac proof and skipped
broader bundle jobs need qualification at corrected source.

Corrected native source `69477f8` passes Handy lifecycle plus actual broker/CAS
maintenance on Mac 14 (111327429133), Windows (111327429134), Linux ARM64
(111327429137) and Linux x64 (111327429183), and actual owned Linux service plus
broker graph checks (111327429178), in
[37165487146](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37165487146).
Separate Mac Handy job 111327415330 also passes in
[37165488998](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37165488998).
This supersedes the cold-handshake failure for native broker/CAS proof only.
Debian/shared tests and complete Linux x64/ARM64 bundles remain live, as do full
Mac 14/26 jobs 111327575462/111327575502. Do not restart or cancel those handles.
Public flags/feed stay disabled and the complete cross-platform goal stays active.

Real Linux desktop acceptance also needs the Wayland portal dependency closure:
`services/dictation/portal.py` imports `gi`/Gio/GLib, while the actual `42e2e05`
pinned standalone runtime reports `giAvailable: false`. The unchanged Linux
wheel lock does not include PyGObject. Native CAS/offline Qt/X11 proofs do not
cover GNOME portal operation; keep distribution eligibility false and resolve/
qualify this before a normal Wayland target is offered. Separately audit broker
spawn bytecode: `dictation.request` currently launches `sys.executable` without
explicit no-bytecode flags; the installed desktop launcher propagates its guard,
but Browser/other caller paths still need direct immutable-artifact evidence.
Preserve live broad 37165487146 and Mac 37165488998 while progressing these gates.

## Linux portal dependency closure — October 4, candidate

This follow-up to `62c15cd` adds PyGObject **3.52.4** and Pycairo **1.28.0**
to the exact standalone Python 3.12.13 runtime graph (24 packages). Official
source archives and six isolated build tools are pinned by SHA-256. Native
wheels are built outside the product runtime; their source/wheel identities,
build-tool versions, build-lock digest and native library versions are retained
in `licenses/linux-portal-build.json`. Build tools do not enter runtime inventory.
The existing portal protocol is retained. Both CPU candidates now declare glibc
2.39 and GLib/GIRepository 2.80; Ubuntu 24.04 and Debian 13 remain candidates,
with distribution qualification and automatic installation explicitly false.

The fixed offline health action emits schema `/2` only for receipts declaring
portal requirements. It imports the bundled bindings and checks their pinned
version/GLib floor. The retained consumer requires those exact fields, a real
boolean and integer version components, and agreement with bundled pins. Legacy
receipts retain their exact `/1` report. New targets run this private-profile
health action before maintenance and during immutable preflight, so unavailable
libraries refuse before stopping the current app. Ordinary dictation-client
startup now explicitly passes `-B`; an actual copied-interpreter/broker test
removes inherited bytecode guards and verifies unchanged release bytes.

Actual local native compilation/installation passed in isolated Ubuntu image
`ubuntu@sha256:008173c23f95b170204355c12626cb5a965d779a7e1283b09e9cffbb1bf33ca3`.
The staged interpreter imported PyGObject 3.52.4 with GLib 2.80.0. Its real
isolated D-Bus fixture passed both cases, exercising early Response, shortcut
press/release and denied rebinding without compositor consent or audio capture.
This local build preceded the added interpreter/provenance assertions; final
producer qualification is assigned to native x64/ARM64 CI. The complete archive
proof now runs that same two-case fixture through the relocated bundled Python,
requiring no skips and checking source/target immutability afterwards.
Original source notices are inventoried; the build proof deliberately retains
`sourceLicenseReviewComplete: false`. No distribution, physical compositor,
production signing/feed or signed forward installation is qualified here.

The preceding source `69477f8` has now completed the entire broad/shared/Linux
workflow successfully in
[37165487146](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37165487146),
including complete x64/ARM64 bundles and installed packages. Those artifacts
precede this portal closure. Full Mac 14 job 111327575462 succeeds in
[37165488998](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37165488998);
Mac 26 job 111327575502 remains live at the latest observation. These results
supersede the earlier live statuses without implying final cross-platform
qualification. The original Mac run is retained; no customer install changed.

Local follow-up checks pass: 15 managed-selection/health cases (including dependency refusal before maintenance), 11 producer/archive cases, 11 broker-maintenance cases and 14 existing dictation cases. The two-case actual bundled-interpreter D-Bus fixture also passes. These are source/private fixture checks, with the native complete two-CPU build still pending.

### Fresh-host Qt and native component requirements

The actual `/2` health consumer at `799f7f7` passed against the newly built
standalone runtime in the minimal pinned Ubuntu container after installing
`libgssapi-krb5-2`. Its first minimal-host attempt failed at the actual QtNetwork
import because that library was absent; hosted build runners had masked this
host dependency. The successful isolated check rendered 424×484 with font coverage,
verified portal bindings and retained identical payload bytes. No app/service or
provider was started. This is an actual consumer check with a synthetic receipt,
not a complete produced archive or an installed customer update.

The follow-up records `requiredSystemPackages` in the build configuration and
receipt, including Qt networking and the existing Handy GTK/WebKit/ASR dependencies.
Native bundle CI installs that same declared list, with build/fixture tools kept
separate. The relocated archive proof additionally starts the exact staged Handy
component through the bundled Python broker in a disposable copy/profile/display
and bus, exercising microphone reservation, busy-owner preservation, cancellation,
settings preservation and ordinary child exit without capture or model download.
The source/target snapshots still must remain unchanged afterwards. Native
qualification of this newer follow-up remains pending; preserve the original
`799f7f7` run 37166969159 rather than cancelling it. Distribution eligibility stays
false, and this user-local updater does not run a privileged package installer.

The declared-package follow-up also passes actual native Handy/broker maintenance
inside the same minimal Ubuntu container through the staged Python 3.12.13:
native owner preservation, CAS reservation, admission fencing, cancellation,
settings preservation and ordinary child exit all pass. The component is the
locally validated public Linux x64 build copied into this isolated fixture.
This verifies the declared host dependencies and real native protocol, but does
not stand in for the exact newer CI-produced archive or physical input acceptance.
The isolated container installs only declared runtime packages plus Xvfb/xauth
fixture tools; no owner host packages, application/profile or model are changed.

### Complete portal bundles at 799f7f7 and retained Mac results

[Native Linux run 37166969159](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37166969159)
is entirely successful at `799f7f718b91409292c0f9f8534331e995b85039`:
x64 job 111331994133 and ARM64 job 111331994069 each build the complete
24-package runtime and exercise the actual ZIP consumer, interpreter relocation,
`/2` Qt/font/portal health, real private D-Bus fixture, unchanged selection and
immutable payload. Both report PyGObject 3.52.4 and GLib 2.80.0. Hosted x64
build provenance confirms all six pinned tools, build-lock SHA-256
`fd809128ba91e5ee22ec074b6cdce2b0ea7903e1c2fc671b2c8686db63a11dba`,
GLib/GIRepository 2.80.0 and Cairo 1.18.0. Native wheel hashes differ from the
local build; pinned source/tool inputs and each output's recorded inventory do
not imply bit-identical native compilation across builders.

| Target | ZIP bytes | ZIP SHA-256 |
| --- | ---: | --- |
| linux-x64 | 649138497 | `7e9c7250370f2d22da7fce13999ceab510a36b9a8ed9e231b307057f68be7c91` |
| linux-arm64 | 614736381 | `82508fd753bfbcc8b30b280d67088099983b066f782330751604496dd91851a4` |

These artifacts precede the declared full host-package/native-Handy follow-up
`a285350762b2ebdf181b67b737eb597411df77cb`, now qualifying in
[37167426017](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37167426017).
Preserve that run; no passing exact newer archive is inferred from the older one.
The original [Mac run 37165488998](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37165488998)
also finished entirely successfully at `69477f8`, including full Mac 14 and 26
jobs 111327575462/111327575502. It supersedes the earlier live Mac statuses and
qualifies that earlier source only. None of these runs are physical compositor,
real customer DSH/provider, signed forward installation or production feed proof.
The full cross-platform goal remains active and public eligibility stays false.

### Linux service wiring and native report correction

The shared manager now discovers/launches the existing managed Linux bootstrap
only for the exact selected canonical release, matching update profile, bundled
interpreter paths, writable release store and fixed shipped entrypoints. Its
installation results come from the persistent state directory; an old manager
can still collect its original attempt after selection changes. Debian/Fedora,
source/custom profiles and missing/changed selections remain manual. Existing
signed-feed, qualified-source/target, automatic-download/install consent and
fresh independent authority gates remain enforced. This fixes the service-wiring
gap: previously Linux could never reach its existing external controller.

Follow-up host manager/Linux/authority/Mac-location checks pass **103 cases**
(101 passed, two explicit native-service skips). Actual private files/profile
selection are used; the dispatch call is deliberately mocked and no installer,
network, graph shutdown or owner application is started by these tests.

At `a285350`, [37167426017](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37167426017)
is terminal: complete x64 archive/staging/Qt/portal plus staged native maintenance
passes (111333376400); ARM64 (111333376398) builds and passes Qt/portal and its
native helper exits zero, but parsing the captured native-wrapper stdout fails
with `JSONDecodeError`. This is not an overall ARM64 pass. The helper now writes
a dedicated exclusive UTF-8 report file in the private proof directory; the
consumer bounds it to 4096 bytes and verifies every declared native proof flag.
Stdout is no longer installation/test evidence. Ordinary helper CLI stdout is
preserved. Native nonzero exits expose bounded private-fixture diagnostics.
The corrected actual local report-file proof passes in the isolated Ubuntu fixture
with unchanged target bytes, native owner/CAS/admission/cancellation/settings checks
and ordinary native exit. Fresh native two-CPU qualification remains required;
no gates are waived.

### Corrected full native Linux follow-up at 0bc9639

[Focused native run 37168003800](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37168003800)
is entirely successful at `0bc96393f1d95723a0475ee167ea91fa725bd536`.
Complete x64 job 111335079309 and ARM64 job 111335079276 each produce the actual
24-package, host-dependency-declared archive, then pass ZIP staging, relocated
bundled `/2` Qt/font/portal health, real private D-Bus and actual staged Handy/broker
maintenance through the bundled Python. The dedicated bounded UTF-8 native report
passes all owner/CAS/admission/cancellation/settings/ordinary-exit flags on both
CPUs. Exact source/target payloads and selection stay unchanged. No microphone,
model download, provider, physical compositor or actual installation is exercised.
This supersedes the ARM stdout-parser failure for this fixture only.

| Target | ZIP bytes | ZIP SHA-256 |
| --- | ---: | --- |
| linux-x64 | 649144736 | `ba333a9b2fa72804482b1ced8cba95c777d9849d6f293bca46cb50c9402810d9` |
| linux-arm64 | 614742619 | `615ac8a9d6da2ba5892e075f0764c54a1f1c6c899dc30a54128e381895eacd1f` |

The focused workflow deliberately skips Debian/broad suites, installed packages,
Browser package, Home and owned-service jobs; their earlier results do not become
new source qualification. Host related manager/Linux/authority/Mac-location checks
pass 103 cases (two explicit native-service skips). Current broad/Mac evidence
remains source `69477f8`; Windows native full acceptance retains its own earlier
record. Every public automatic-install/distribution/feed flag remains false.

Historical next work at this Linux checkpoint remains Windows persistent-broker discovery/startup/lifetime/
reopening (the current actual Handy/CAS Windows proof calls Backend directly),
normal desktop/DSH and signed forward acceptance, privileged package-managed Linux,
shared/system/companion Mac coordination, SDK owner teardown, verified interrupted
recovery and safe retention, legacy first bridge delivery, and owner-provisioned
production signing/feed. In particular, `server.main` currently registers broker
maintenance only on Linux/Mac, and `WindowsPreparation` has no dictation discovery.
Do not infer Windows broker participation from its passing native component proof.
No owner install, account/profile, live model or GPU settings changed. The complete
cross-platform goal remains active; this passing checkpoint is not completion.

## Windows persistent dictation coordination — October 4, candidate

The persistent broker now takes the Windows startup reader through publication of
both authenticated ordinary RPC and maintenance readiness, and holds the shared
installation lease until normal process exit, including when capture is disabled.
Normal installed Python Windows admission refuses any entry at the private persistent
`updates/active.json` before ordinary admission; malformed/empty entries remain
untouched. Maintenance writers may still observe recovery. The old runtime
maintenance marker remains a separate refusal.

The kernel startup reader itself only supplies exclusion; fixed read-only health
actions can retain it while inspecting a pending update. Normal installed
components check persistent refusal when acquiring their lifetime lease under
startup admission. This avoids a general pending-update bypass option and keeps
offline target-health/recovery inspection possible.

Windows session names now use the process's actual login/RDS session through
[Microsoft's ProcessIdToSessionId](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-processidtosessionid).
An update observes held broker registrations without starting one, verifies the
named pipe's current-user PID, retains a read-only process handle, and requires
the fixed `python/python.exe`, selected build root, actual session and state hash.
Another state/login/build or an unsupported response defers without adopting it.
The Windows maintenance protocol is `augmentor-dictation-maintenance/1`; the
existing Unix wire protocol and Unix state/session naming remain unchanged.

An installed GUI/native-host client now starts the fixed shipped interpreter with
isolated imports and bytecode disabled, rather than treating its native launcher
as Python. The state directory and 32-byte authentication file are protected
current-user/SYSTEM objects. An existing broad/inherited directory or key is
refused without changing its grants or rotating the key. This requires manual
bridge/migration treatment for legacy Windows state with incompatible permissions;
it is not a transparent legacy migration. The existing default dictation-state
location and preferences remain in place.

Preparation reserves surfaces, then dictation, before downstream DSH/voice/shared
services. Capture or model-work refusal preserves work and cancels prior reversible
reservations. Idle drain records normal broker commit and actual process exit
before downstream shutdown. The live observer's reopen plan carries only optional
`hadDictation: true`, with strict Boolean validation and no command/path/environment.
Verified completed-target reopening launches fixed `python/python.exe` and
`services/dictation/server.py` once in an independently observed Job, requires the
actual new peer PID and normal admission, and rechecks the immutable whole payload.
Unknown or failed launch is not replayed or force-terminated. Only a broker observed
before preparation is reopened; user preferences and login registration are not
rewritten. The caller's original exited coordinator/Setup observations, exact
completion archive, independent health and qualification/publisher gates still apply.

Portable preparation checks pass seven cases (including busy capture and drain
ordering), observer checks pass eleven including old-plan compatibility. Linux
broker/update checks pass eleven, retaining actual Unix process/graph coverage.
New native `test_update_windows_dictation.py` runs on both Windows desktop CPUs:
it copies the standalone runtime and public broker into a disposable explicitly
unqualified installation, and exercises actual pipes/processes/ACLs, disabled
lifetime exclusion, busy owner preservation, cancel, startup-writer exclusion,
empty pending-record refusal, normal exit, fixed GUI-client spawn, immutable
payload and one-shot reopening. The alternate-scope refusal uses a synthetic
scope against a real retained peer; it does not launch a second Windows login.
No microphone, model download, actual Handy component or signed forward N→N+1
installation is exercised by these new cases. Native results are pending here.

The broader local updater suite passes 258 cases (six explicit platform skips),
existing dictation passes fourteen and Windows preparation passes seven. The
first invocation used system Qt without QtTest and failed that import; rerunning
in the isolated environment with the repository-pinned complete Qt essentials
passes. No system Python or operating-system package was changed.

The full actual Inno fixture now also keeps an installed disabled broker alive,
proves an accepted microphone owner defers the real coordinator without clearing
the owner, records actual dictation drain/exit before replacement, verifies that
the installed target broker refuses the retained pending transaction, then
requires a new ready broker after live independent completion and unchanged saved
dictation preferences. Its final graph drain includes that reopened broker. This
remains same-build repair with a synthetic unsigned catalog, not signed forward
acceptance. The two-CPU full installation run is pending for this extension.

### Native Windows broker results at eddaf37

[Windows desktop run 37169461358](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37169461358)
is entirely successful at `eddaf37cdc8fe94e31570b2f3ffd8a7334f0a017`: x64 job
111339262443 and ARM64 job 111339262532. Both execute the three new actual private
installed-broker cases successfully, including retained pipe/session/executable
identity, disabled installation exclusion, occupied owner refusal/cancel,
startup-writer exclusion, normal broker exit, fixed one-shot reopen, private key
and GUI-client interpreter choice, unchanged payload/preferences and empty pending
record refusal. Their updater suite passes 258 cases (158 passed, 100 explicit
Linux/Mac/other-context skips). The rest of the native desktop workflow, including
Qt rendering, native ownership and compiled startup/lifetime launcher proofs,
passes on both CPUs. These are disposable kernel/process proofs without capture,
model download or real Handy startup.

The extended full Inno fixture at `c8b73e3` is running separately in
[37169658310](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37169658310).
Only that completed result can qualify its real installer interaction; the desktop
run does not qualify replacement, completed-target health, signed forward updates
or user-profile deployments. No production flag or owner installation changed.

### Full Windows health-boundary correction after c8b73e3

The extended full x64 fixture in run 37169658310 reaches actual installed broker
observation, busy microphone-owner deferral, graph drain/normal exit, replacement
and target-broker pending refusal. It then fails because the new blanket check in
`windows_startup.Startup` also refuses the existing read-only pending-target health
observer. This is an implementation regression, not production qualification.
The correction keeps persistent refusal in normal installed lifetime admission,
and restores the startup primitive's exclusion-only contract. The native broker
test now explicitly confirms read-only admission can observe pending bytes while
normal installed broker startup remains blocked. A new full two-CPU run must
qualify all completion/reopening/recovery stages after this correction. ARM64 is
still running at this record; do not infer its result from x64.

At correction `c40926b`, the complete native Windows desktop run
[37170463612](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37170463612)
passes both x64 (111342219515) and ARM64 (111342219640). The actual pending-broker
case still refuses installed normal startup and preserves pending bytes, while
the startup reader permits read-only inspection. The original capture/cancel,
lease, fixed-client spawn, private authentication, normal exit, immutable payload
and one-shot restart cases also pass. The corrected full installer run
[37170465430](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37170465430)
is queued behind the earlier ARM64 job, which remains live; no obsolete job was
cancelled and no later completion/reopen result is inferred. Public eligibility
and feed remain disabled.

The older run 37169658310 is now terminal failure on both CPUs. ARM64 job
111339839655 reproduces the same read-only health refusal at the exact negative
mismatched-health boundary as x64; this supports the diagnosis without qualifying
later stages. Corrected full run 37170465430 is now executing both native jobs
(x64 111344879337, ARM64 111344879344), after successful shared Qt preparation.

Read-only release-configuration audit on October 4: the canonical GitHub
repository returns no repository-level Actions secrets, variables or environments.
No credential contents were requested or read. `release/updates.json` remains
disabled. This confirms that a GitHub-based signing/deployment path has not been
provisioned in those locations; it does not establish whether the owner has keys,
certificates or service access elsewhere. The earlier online-custody and platform
signing questions remain unanswered and are not replaced by this audit. No key,
certificate, account, environment, secret or public feed was created or changed.

All public signing/feed/automatic-install/distribution flags remain false. The
remaining package/global-user, shared Mac/Companion, SDK owner teardown,
interrupted recovery/retention, actual desktop/DSH, signed forward and legacy bridge
gates remain. No owner installation, private profile, model or GPU was changed.

### Generic Windows login-session admission

Generic Windows participants now also compare the pipe peer's actual process login
session with the coordinator's session before sending any request. A different
session of the same SID defers, including idle windows/background components;
captured windows are never silently closed in one login and reopened in another.
The native retained-broker case simulates a different kernel session result,
requires prepare to refuse, then checks the real broker stayed ready without a
reservation. This tests the pre-send boundary with an actual process/pipe, not a
second real RDS login. A fresh native/full run must qualify this follow-up; the
currently running `c40926b` installer run predates this added guard. Production
flags and owner installations remain unchanged.

### Windows dictation reparse admission

Windows state validation now checks the originally supplied hierarchy before any
resolution can hide a junction. The maintenance scope performs the same read-only
reparse check before hashing the selected path; it creates no state or key.
The native fixed-client case creates an actual private fixture junction, requires
both authentication access and maintenance scope to refuse it, and verifies the
original 32-byte key is unchanged. Normal existing private paths keep the same
identity; Unix resolution/identity behavior stays unchanged. Fresh qualification
must include this follow-up before any public eligibility is enabled.

### Latest native Windows admission qualification

At `40af948`, complete desktop run
[37172409931](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37172409931)
passes both CPUs (x64 111347893591, ARM64 111347893695), including the real retained
peer with synthetic alternate-login pre-send refusal and unchanged ready admission.
At `07c05af`, complete desktop run
[37172698677](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37172698677)
passes both CPUs (x64 111348760292, ARM64 111348760163), including the actual junction
rejection for key access and maintenance scope, unchanged original key, normal
fixed GUI-client spawn, broker/lease/owner preservation and one-shot reopening.
All eleven Linux broker cases pass after the scope/path follow-up, including actual
copied-client immutability and observed Linux graph drain/reopen. No Unix identity
or wire behavior was changed.

The corrected full x64 job 111344879337 at `c40926b` in run 37170465430 now passes
all 24 installed fixture stages: actual broker capture deferral, graph drain and
normal exit, whole Inno apply/observed Setup exit, pending target-broker refusal,
independent target payload/health completion, new ready broker/settings preservation,
captured window/background reopening, source restoration, repair/removal and
persistent-data retention. The downloaded installed-application report has
`passed: true`. This remains same-build repair with a synthetic unsigned catalog,
no model/physical input/signed forward or data-rollback claim. ARM64 111344879344
remains live at this record. Full follow-up 37172411318 at `40af948` is queued; it
must qualify generic login-guard integration separately. The junction fix is
covered by the later actual desktop broker cases, not inferred from the earlier
full installer source. All production eligibility/feed flags remain false.

### Completed Windows broker installer qualification and signed authority bridge

Corrected full run
[37170465430](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37170465430)
at `c40926b` is terminal success, including x64 job 111344879337 and ARM64 job
111344879344. Both downloaded `installed-application.json` reports have `passed:
true` and all 24 stages. ARM64 independently reaches actual broker capture
deferral/drain, pending target refusal, complete target health/completion, observed
reopening, source restoration, repair/removal and persistent data retention.
The same-build synthetic unsigned catalog and no-model/physical-input/signed-
forward/data-rollback limits still apply. Full login-guard run 37172411318 at
`40af948` is now executing; the later junction fix is qualified by the actual
desktop run at `07c05af`, not inferred from this earlier full source.

`tests/test_update_signed_authority.py` and its private Node fixture additionally
join the shipped TUF repository library to `AutomaticInstallAuthority`: generate
temporary in-memory Ed25519 role keys, serve real signed metadata and an inert
payload on an explicit loopback-only fixture, verify/download through the actual
client, then reverify fresh signed metadata at live authorization boundaries.
Two host cases pass: a higher-sequence signed withdrawal refuses installation at
`installer-ready`, and a damaged publisher timestamp signature refuses at
`prepared` despite a valid cached selection. The requested artifact is downloaded
once; fresh timestamp requests are observed. No pending application journal is
created and the inert installer is never executed. Only the machine/source
identity and qualification flags are synthetic, using the existing private
installation fixture. The Windows full workflow invokes this test after locked
dependencies are installed; desktop-only workflows explicitly skip it when those
dependencies are absent. This does not grant production HTTPS exceptions, create
publisher keys/configuration or qualify an actual OS N-to-N+1 installation.

Public feed and eligibility remain false. Native signed-forward, full desktop/DSH,
package/shared-user, Mac shared/Companion, SDK owner teardown, legacy bridge,
interrupted recovery/retention and production signing gates remain open. Owner
installation/profile/model/GPU settings have not changed.

### Full Unix observer retention

Linux and Mac previously retained a complete isolated source runtime/bundle on
every attempt without retiring those copies. Daily updates could therefore
accumulate gigabytes of temporary code. `posix_observer_retention` now retains a
separate shared kernel lease for each exact private `linux-<attempt>/Observer` or
`mac-<attempt>/Observer.app` directory. The original observer acquires it during
inherited bootstrap exclusion and keeps its descriptor through Python teardown
until OS process exit. After independently validating its complete source payload,
only a confirmed deferred attempt or actual completed installation can publish a
cleanup hint containing the original verified payload digest. Unknown post-drain
outcomes remain unmarked. A reopening failure after durable completion can retire
the observer without changing the successful installation result.

A later bootstrap collects under the existing exclusive bootstrap lock, after
unfinished-transaction refusal and before creating a new observer. Collection
requires the original lease file to exist and an exclusive kernel acquisition,
an exact sidecar schema/name/outcome, a private unredirected hierarchy with exactly
one expected child, unchanged complete payload identity, and the platform's
descriptor-based symlink-safe recursive deletion. Legitimate internal Mac
framework links are checked without following them during removal. Changed code,
hard links, external/invalid links, extra files, malformed hints, old directories
without lease files and live holders all survive. Small reusable lock files remain
to prevent namespace races. These hints grant no install, recovery or replay
authority. Selected artifacts, downloaded candidates, stages, recovery backups,
settings and conversations are never collection targets; their retention gates
remain separate required work. Cleanup failure does not alter an install outcome.

Four host Unix cases use actual private files and, for lifetime admission, an
actual normally exiting inert subprocess. The copied Linux ELF observer case also
executes the production observer, verifies its unqualified-source refusal before
network/drain/apply, then collects only its completed temporary copy after exit;
the original selected artifact and manifest remain unchanged. The fixture's cache
directory now matches production private permissions. Broad host updater tests
pass 264 cases with six explicit platform/context skips. A Mac-shaped internal
framework-link tree is exercised on Linux; native Mac locks/bundle integration
still require fresh hosted qualification. This does not qualify signed forward
installation, actual active user profiles or public automatic eligibility. No
owner installation/profile/model/GPU or signing/feed configuration changed.

Mac follow-up 37174398113 at `b438ad8` is terminal failure on both Mac 14/26. The
new retention fixture passes a factory-created `/var/...` temporary path to the
strict unredirected-hierarchy guard; macOS aliases that ancestor to `/private/var`,
so all four retention cases refuse before exercising their intended boundary.
The fixture factory now resolves its own temporary root before constructing the
private tree, matching the ordinary production `~/Library` hierarchy. Production
collector inputs are still validated as supplied. A fifth actual-file case passes
a redirected parent and requires refusal with unchanged code. Both real TUF/signed
authority bridge tests already pass on each Mac in the failed run; that is limited
evidence and does not turn the overall run green. Fresh full Mac qualification is
required after the fixture correction. No release/feed/eligibility changed.
