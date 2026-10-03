<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Updating, migrating and removing the Debian preview

For the selected user-local desktop, use [desktop deployments](DESKTOP-DEPLOYMENTS.md).
Package replacement alone does not promote a different user-local desktop build.

September 27 maintenance correction: if a process exits between its identity
check and the following `/proc/PID/stat` read, preparation now treats the missing
file as successful shutdown. Permission errors are not suppressed. Installed
package CI exposed this race while removing an idle shortcut-launched desktop;
the regression and existing lifecycle tests pass. See the [qualification record](MACOS-APPEARANCE-2026-09-27.md).

The packaged application uses `augmentor-runtime` and optional
`augmentor-desktop`. Both versions come from `release/product.json`. Install the
matching pair when using the desktop. The current preview version is 0.2.10, with Linux
and DSH as the first-release target. Packages retain user data outside
`/usr/lib/augmentor`. Historical upgrade/rollback evidence below is scoped to
its exact version pair; it does not certify every downgrade.

## Upgrade

Finish or Stop running chats, disconnect Augmentor in the extension, and close
open native dialogs. In each account using Augmentor, run:

```sh
augmentor-maintenance prepare
sudo apt install --reinstall ./augmentor-runtime_0.2.10_amd64.deb ./augmentor-desktop_0.2.10_amd64.deb
```

Run the installation command from the directory containing the reviewed package
pair. The public 0.2.10 pair has a distinct version from 0.2.9; `--reinstall` also
supports reinstalling that exact pair if necessary. Public
releases must use distinct versions. It requires an administrator password when the account has no unattended
package-install permission. Do not share that password with an assistant.

Preparation refuses an active task. It closes the idle native window, runtime worker
and shared prompt and automatic-memory companions, then creates a private snapshot under
`$XDG_STATE_HOME/augmentor-release-backups/`. This includes credentials: treat it
as private user data. The command prints the exact backup directory. It does not
stop the external DSH harness or replay a prompt.

Package hooks hold an exclusive release boundary and refuse components still in
use. Launchers, workers and services hold shared lifetime leases. Incomplete
package configuration also prevents launch after reboot. Starting a new chat
after preparing may require preparing again; the package manager refuses the
operation instead of terminating that chat.

For the 0.2.0 baseline, close its UI and browser connection first. It predates the
maintenance command. The 0.2.1 installer detects remaining old workers and refuses
replacement. Keep that release's host shutdown and prompt-service stop available
until its user migration is complete; do not kill a task to force installation.

## Interrupted installation and rollback

Keep the two known-good previous `.deb` files. Finish an interrupted installation
with `sudo dpkg --configure -a`; if dependencies are incomplete, use the
distribution's package repair flow. Do not remove release locks by hand.

The following is the historical 0.2.1 → 0.2.0 rollback example, not the
current candidate rollback command:

```sh
augmentor-maintenance prepare
sudo apt install --allow-downgrades ./augmentor-runtime_0.2.0_amd64.deb ./augmentor-desktop_0.2.0_amd64.deb
```

The checked 0.2.1 → 0.2.0 rollback retains history and prompts in place. It does not
restore an older data snapshot over newer work. This proves that specific schema-1
pair; a future storage migration needs its own compatibility and restoration
checks before publishing a downgrade path.

## Move existing user entrypoints to the packages

After the packages are installed and old components have closed:

```sh
augmentor-maintenance migrate
```

This backs up recognized Augmentor launchers and native-host registrations,
moves the legacy launcher shortcut to the packaged identity, and points the
user-level browser registration at `/usr/bin/augmentor-browser-host`. It retains
the legacy application directory. An existing canonical shortcut takes priority.
Without a running KDE session, the trusted launcher retains its shortcut for the
next login. Differing or symlinked integrations stop migration before replacement.
The printed backup contains a per-file manifest for review or restoration.

## Remove

To remove both components, first run this as each affected ordinary user:

```sh
augmentor-maintenance prepare --remove
sudo apt remove augmentor-desktop augmentor-runtime
```

Preparation clears owned launcher entries and KDE shortcut bindings, removes
recognized user-level browser registrations, and backs up those integrations.
The package manager removes system launchers and native-host registrations.
Configuration, prompts, conversations, backups and user workspace files remain.
Reinstallation uses the retained data without resubmitting old prompts.

For desktop-only removal, use `prepare --component desktop --remove` and
`sudo apt remove augmentor-desktop`. The companion and its active task remain
available. This mode snapshots the removed integrations rather than copying live
runtime data. Per-user cleanup is explicit because root package scripts do not
execute user-controlled code or rewrite arbitrary home directories.

## Current memory and lifecycle evidence

[CI at 29231fd](https://github.com/ManoloRemiddi/augmentor-agent-history/actions/runs/35441917540)
passes installed 0.2.9 maintenance, upgrade/rollback, interrupted configuration and
removal. The installed checks assert the automatic-memory socket closes and its
SQLite journal is included in the backup. This does not back up Hindsight's
external Docker volume; see [memory operations](MEMORY-OPERATIONS.md).

## Historical evidence

Candidate 13 is a clean build from `da2c4b3de69901cf51c4b2256ee1df406f418bc4`.
Its application code matches candidate 12; its package hashes, native binary
notices and exclusion of private state pass the artifact review. Candidate 12
passes installed DSH/Qt checks and Debian 13/KDE Wayland capture/input/Stop.
Candidate 8 supplies clean package lifecycle evidence, and candidate 4 supplies
0.2.7 → 0.2.8 upgrade/rollback and VM reboot evidence. See the
[release status](CROSS-PLATFORM-RELEASE-STATUS.md) for exact scope and remaining
requirements. None of these checks alone makes the candidate public-ready.

The following records the earlier baseline evidence:

`release/lifecycle-proof.py` exercises installed 0.2.0 → 0.2.1 → 0.2.0 packages in
an expendable Debian environment as a separate user. It checks active-update
refusal, desktop-only removal during a task, interruption between unpack and
configure, rollback, migration, unrelated-file preservation, removal and
reinstallation. It compares actual persisted prompts and history and counts
provider requests to reject replay. `scripts/shortcut-launch-proof.py` additionally
checks real key activation and removal across a KDE shortcut-service restart.

Historical private CI rebuilt the baseline from frozen commit
`295dbc0f270344c4eab38ce5ade908622a0cd8af`; local upgrade evidence also uses that
commit's checksum-verified CI packages. These deterministic checks use a local
model fixture. They do not establish live-provider, native Wayland computer-use,
or independent-tester acceptance.


### Public CI baseline after repository consolidation

The current public workflow uses the original, checksum-verified **0.2.9** Debian
packages from the archived `v0.2.9-complete-preview.1` public download. It tests
upgrade to the current candidate, rollback, refusal while active, interrupted
configuration, removal and data preservation. It no longer fetches a private
commit or rebuilds private history. The older 0.2.0 evidence above remains historical.

[`scripts/stage-lifecycle-baseline.py`](../scripts/stage-lifecycle-baseline.py)
pins the complete archive SHA-256 and each Debian package hash, reads only the
expected regular-file members, and writes the manifest consumed by the existing
lifecycle proof. It preserves the original package bytes and source identity.
Run it before `bash scripts/lifecycle-proof.sh`; `--archive` accepts a local copy
only if it matches the same pinned checksum. Do not replace this baseline with
the candidate itself or give public CI credentials for private history.

## User-local supervised desktop

The [September 20 startup deployment](RESTART-RELIABILITY-2026-09-20.md) registers
one user-local build and a managed DSH service. Stop desktop/mobile surfaces
before intentionally stopping DSH for maintenance, because automatic reconnect
starts its registered runtime. `install-desktop-startup.py` backs up launchers and
records the selected deployment; do not independently edit login and menu paths.

## Shared component admission — Windows implementation work

`services/lifecycle/admission.py` provides a reversible, process-local preparation
gate. The prompt companion now adopts it on all OSs. It serializes the decision
to accept a request with maintenance preparation: an existing request makes
preparation refuse; a successful preparation blocks new requests before their
execution. This replaces neither installation leases nor the global coordinator.

The private authenticated prompt endpoint accepts `host.maintenance.status`,
`prepare`, `renew`, `cancel` and `commit` using the existing prompt envelope.
Replies identify `augmentor-component-maintenance/1`. Status takes no fields;
the other methods require a caller-generated 32–64-character lowercase hex
`token`. It is an operation reservation within the same-user boundary, not a new
authentication system. Another token cannot cancel or commit a reservation.

Preparation lasts 30 seconds; repeated prepare does not extend it. Explicit
renewal extends it, cancellation restores admission, and an abandoned preparation
expires. Commit keeps admission closed permanently in that process, acknowledges
the request and requests normal server shutdown. The non-daemon request handlers
finish and the process exits without `TerminateProcess`. Already committed data
remains; refused work is not replayed.

Tests cover real concurrent admission/preparation, expiry/renewal, a lost owner,
wrong tokens and actual prompt RPC. A live long-poll request prevents preparation;
a prepared service rejects a new save, cancellation reopens it, and committed
shutdown exits normally before an explicit restart restores prior data. Local
Linux execution passes. Native execution of the new RPC proof is pending.

The memory companion now adopts the same control protocol on its own private
endpoint, including request handlers, its background processing step and the
memory-only HTTP gateway. An in-flight model request or durable budget settlement
keeps it busy; preparation cannot terminate it. During preparation the worker
waits and the gateway makes no new model request. Cancel/expiry leave the saved
processing-pause preference unchanged. Normal committed shutdown stops the
worker and listener; a real restart test checks both the journal and preference.
Gateway HTTP tests verify refusal before the upstream connection and continued
Stop cancellation. These new memory tests pass on Linux; native execution is
pending. External Hindsight/model processes are never owned or stopped here.

At `4f2f763`, the native x64 and ARM64 desktop jobs and full runtime
[run 36368605593](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36368605593)
pass the prompt and memory tests, including actual acknowledged exits and restart.

### DSH admission and normal shutdown

The next DSH product adapter adds the same private control vocabulary through
`POST /api/augmentor-product`, with `action: maintenance`, `method` and `params`.
It requires the existing product token and loopback/origin validation; the public
descriptor advertises `maintenanceAdmission: 1`. Unknown fields are refused.
Preparation reserves every idle agent using public `runMaintenance`, refuses
pending inbox content, active remote invocations, live jobs and model streams,
and expires or cancels without stopping work. The public `llm/stream` waterfall
also fences auxiliary calls and capabilities prepared before the reservation.

DSH rc.1 has no single reversible process-wide input-admission API. This pinned
adapter therefore guards the **public** gateway `invoke`, job `start`, agent
`send` and inbox `splice` methods and vetoes new agent publication. It preserves
Cordis's caller-specific method receiver, verifies its descriptors before
preparation/commit and restores only its own methods on ordinary plugin unload.
It does not edit private loop state, initiator state, messages or history. This
is an explicit DSH-version compatibility obligation: the real SDK and gateway
tests must pass before changing the harness pin; arbitrary third-party plugins
that bypass those APIs are outside this qualification.

Commit leaves admission closed and asks the launcher's public `appExit` to
dispose the normal runtime after its HTTP acknowledgment. It does not send
`TerminateProcess` or an OS signal. The launcher itself has a bounded fallback,
so exit code zero alone is insufficient evidence. The disposable proof installs
a fixture observer for Node `beforeExit`, which forced `process.exit` skips.
It verifies refused input never reached history, cancellation preserves history,
then committed shutdown reaches `beforeExit` and exits zero. Local actual DSH
execution passes; the native Windows proof is newly added and pending.

This work exposed older shared cleanup handlers using `ctx.on('dispose')`, which
the pinned Cordis runtime does not dispatch. The runtime lease helper kept DSH
alive after its root disposed. Product, memory, execution, steering and desktop
cleanup now use `ctx.effect(() => cleanup)`; the lease cleanup waits for its
helper to exit normally. This shared correction applies to all three OSs.

The browser still requires its own participation. The global
owner must stop automatic restarts, reserve
all components, cancel reservations on preparation failure, and acquire the
exclusive installation lease after they drain. No installer may infer that the
whole app is idle from this one component's response or terminate active Jobs.

### Desktop admission

The shared native window accepts the same component protocol through its private
instance socket, as `maintenance:` followed by an exact JSON `method`/`params`
object. Responses include the process and build identity. Preparation refuses
drafts, open dialogs, voice panels, navigation, recovery and accepted background
work. Controller admission counts queued work before its thread starts; each
monitor pass is counted, while the sleeping monitor holds no work reservation.
Prepared windows suspend health/reconnect attempts and disable input. Cancellation
or expiry restores their prior enabled state. Other windows retain their drafts.

Commit acknowledges first, then closes the idle window normally. A reservation
does not call Stop, clear drafts, replay prompts or silently switch harnesses.
The old maintenance status/close commands cannot bypass a reservation. Local Qt
tests and a real two-process Linux preview proof pass; compiled Windows execution
of this new desktop behavior is pending. These are component-level checks, not
proof of global Quit or an installation transaction.

### Voice companion admission

The shared Resonant Voice 0.1.19 candidate exposes the same private reservation
vocabulary through its existing authenticated `/internal/maintenance` endpoint.
Read its [versioned contract](https://github.com/ManoloRemiddi/resonant-voice/blob/7d0fd6d677ea4bbbca0183a6bb3a3d3f24a8147a/docs/PROTOCOL.md).
Open/authenticating connections, unexpired connection tickets, accepted requests,
speech synthesis and workers still exiting keep it busy. New work is rejected
while prepared; expiry/cancel restores admission. Idle commit closes listeners
normally, without stopping an external Breeze/model process. Both native Windows
CPUs pass the dependency's actual HTTP/WebSocket and CLI natural-exit proof.

This contract does not grant Augmentor ownership of an externally configured
voice service. The global coordinator must use it only for a verified owned
companion, and must drain browser/native voice clients first. Managed Windows
voice startup and product-wide coordination remain pending.

### Windows owner reservation

The [Windows background owner](WINDOWS-SHELL.md#background-owner-reservation)
reserves component startup and shortcuts before the future coordinator reserves
the components themselves. Preparation alone says nothing about child idleness.
Commit requires the owner to be empty and acknowledges before normal Qt exit.
Accepted shortcut work remains counted after a lost caller response until the
actual operation finishes. These additions pass portable tests; native execution
of the owner handshake is pending.

## Browser transport drain

The shared native-messaging parent now drains already accepted shared operations
when browser input closes. It sends EOF to its selected bridge, waits for the
child's actual close event and flushes complete response frames before natural
exit. A child's output ending cannot truncate an outstanding parent-side prompt
operation. The parent no longer kills its bridge or calls `process.exit` for an
ordinary disconnect. A fatal protocol/transport failure retains a nonzero exit
code while accepted shared work settles; it is not replayed.

Browser voice separately retains busy state until its worker's actual close
event and accepted ticket/submission operations settle. Closing the voice UI
does not imply worker exit, and ordinary close no longer kills a worker after
two seconds. A second voice session waits for the retiring work. This is shared
behavior across OSs and adds no new audio engine or settings changes.

The DSH and Pi bridges now also close admission on EOF and drain accepted
requests through response delivery before releasing their connections. DSH
disables reconnect, drains closing voice workers and releases its interaction
presenter; closing a connection never answers an approval. The Windows wrapper
waits for its whole Job to exit naturally before releasing its lifetime lease.
Its explicit crash/fault containment remains separate.

These are component prerequisites, not global browser maintenance. The extension
reservation below now protects pages; native control/discovery is implemented
below and awaits compiled qualification. Startup exclusion and the final browser
shutdown handoff remain pending. Portable real-process tests hold a shared request over EOF
in the parent and both bridges, then require a complete final response and Node
`beforeExit`. The DSH bridge case uses a deliberately unavailable isolated
endpoint, not a real model or WebSocket session. Voice tests use controlled
workers/submissions and do not qualify a physical audio device. The new assembled
Windows browser flow still needs native execution.

### Browser page reservation

The shared Chromium worker now receives `augmentor/maintenance` over its native
port, carrying the exact `host.maintenance.*` method and params of the component
protocol. It counts accepted panel requests through their response, counts
browser actions through completion, and refuses preparation while chat, pending
requests, interactions or connection setup are active. Preparation fences new
panel/native work and reconnect attempts. A delayed harness reset is retained
and performed on cancellation rather than discarded. A new running-turn or
interaction notification cancels preparation without answering or stopping it.

Every sidebar and Settings document registers an extension-local long-lived
port identified by Chrome's `sender.documentId`. The worker inventories all
extension documents using `runtime.getContexts` before and after reservation;
an unregistered page, unsupported inventory API or changed inventory refuses.
Opening or losing a registered page cancels the reservation. This uses browser
capabilities rather than a browser-name allow-list. Chrome documents
[`getContexts` from version 114 and document identity on ports](https://developer.chrome.com/docs/extensions/reference/api/runtime).

Pages refuse drafts, message/title edits, active voice gestures, pending draft
restoration, modal dialogs, accepted page requests and unsaved inline Settings.
Prompt instructions, Pi/DSH setup, manual memory, Home pairing and Voice changes
are checked locally. Form values and secrets never enter maintenance replies.
An idle page keeps its DOM and values and temporarily becomes inert; prior input
state and focus are restored after cancellation. The worker and pages each
expire reservations after 30 seconds using monotonic clocks. Repeated prepare
does not renew; explicit renewal rechecks all pages. Missing hello, disconnected
worker or lost coordinator cannot leave the page indefinitely locked.

`commit` now repeats context inventory and page renewal, including late draft
and accepted-work checks. Only an unchanged idle group returns `closing`; this
authorizes its native connection to drain, not the browser or its pages to close.
The worker/pages retain a bounded 30-second fence, then resume input and the
existing reconnect path. New/lost pages still invalidate the reservation.
Neither page reservation nor a commit reply authorizes file replacement: the
coordinator must retain startup exclusion, observe every owned host exit and
acquire the exclusive installation lease.
Extension-version compatibility/store delivery remains a separate update gate.

Local proof now uses actual unpacked Chromium, actual page ports/context inventory
and the private owner/native control around the real Pi bridge. Its extended
proof now observes the committed wrapper's natural exit using a retained Linux
pidfd, then verifies the same document/input node, a post-commit draft and the
selected conversation survive automatic same-build reconnection. This is not
an installed N-to-N+1 extension update. The earlier
`f079931` proof used a disposable framing proxy; that helper has been replaced
by the actual product transport. Two chat documents and Settings prove draft/API-key refusal,
three-page reservation, cancellation, renewal, new/closed-page invalidation and
real 30-second expiry. The documents are opened as extension tabs; this is not a
Windows side-panel/Comet GUI or consumer installation claim. Deterministic DOM
tests additionally cover form dirtiness, accepted work, wrong tokens, missing
inventory and cancellation races. See [verification](../tests/README.md).

### Native browser participant

The Windows wrapper now holds a private per-process registration lease and hosts
an authenticated named-pipe control endpoint. Its Node parent registers over the
existing Python pipe relay, using a per-launch capability. The wrapper verifies
the relay's kernel PID, executable and membership in the exact owned Windows
Job, retaining its process handle through registration. The capability is not
passed to the DSH/Pi harness. Controllers may request identity or the bounded
maintenance vocabulary; this endpoint has no arbitrary command or termination
operation. Same-user private access is not publisher authentication.

Windows discovery enumerates held registrations, verifies the wrapper's kernel
PID/executable/build root and retains its actual process handle. It preserves
stale files and refuses an inconsistent registration. Later control cannot
silently adopt a different process. This remains a snapshot: global startup
exclusion and the final exclusive installation lease are still required.

The Node parent parses complete native frames even after harness selection,
correlating accepted requests and browser actions in both directions. Those
operations and parent-side shared work veto preparation. An idle native host
then reserves the worker/pages through native messaging and fences new work.
Its deadline conservatively includes the whole response round trip. A page
invalidation releases the matching native reservation; stale notifications and
late replies do not enter the harness. Lost control never replays a request or
terminates active model/browser work. Normal EOF still drains before natural exit.

After the worker confirms idle commit, native admission stays closed permanently
for that host. The private owner forwards `closing` to the coordinator and sends
a receipt bound to that exact RPC id. Only then does the host use its ordinary
EOF/drain path; missing delivery receipt or owner loss triggers the same drain
once, within eight seconds. An unknown worker commit outcome never claims native
shutdown and is not replayed; it gets one cancellation and bounded page expiry.
The coordinator must reconcile an unknown outcome through its retained process
observation rather than issue another commit. Browser/window closure, reload,
forced process termination and automatic model/tool replay are not involved.

Local evidence after commit integration: all 265 Node/Browser tests, seven real
private-transport Python tests and actual Chromium using the product private
owner/native host pass. The portable owner verifies the Linux peer/executable;
it does not claim Windows Job membership. The compiled Windows proof now checks
real discovery, relay ownership, reservation/refusal/cancel and committed natural
exit under startup exclusion with fixture renderer replies; execution of the new
commit assertions is pending on both CPUs. Real
Chromium document behavior and compiled transport behavior remain separate
evidence. Global commit/update, Windows Chromium/Comet GUI and customer release
are still incomplete.


### Coordinated reversible preparation

`services/lifecycle/reservations.py` shares preparation/renewal/cancellation
across already authenticated participants. It retains an attempted preparation
before sending it, so even a lost reply gets one token-specific cancellation.
Its default cleanup never commits shutdown or replays work. Explicit observed
drain is described below. Each
participant renews independently; the conservative deadline starts before the
request, and any lost/expired acknowledgment invalidates the entire group.
Cleanup stops renewals before cancelling leaves, then their background owner.
A lost cancellation reply permits only a read-only confirmation of ready state.
If a renewal exceeds the cleanup bound, its observations stay retained until
that request actually ends; no installer or shutdown is authorized.

The Windows context additionally holds the startup writer while discovering
and reserving its existing owner, desktop windows, native browser hosts, managed
DSH, its owned Resonant bridge and prompt/memory companions. Unknown ownership or any busy participant
unwinds the attempt, preserving accepted work. It currently requires a running
owned supervisor and excludes external services. Global commit,
integration with the independently qualified authenticated installer handoff and
final exclusive installation access remain prerequisites for a complete update.
Default context exit cancels reservations; only explicit `drain()` requests
component shutdown. This context cannot apply files.

Local failure/expiry/renewal tests pass. Native tests now cover actual companion
group renewal/cancellation and assembled desktop/DSH preparation with preserved
history, plus refusal during an actual deterministic-model turn. Execution of
these new graph assertions is pending; separate component tests already pass.

### Windows owned voice bridge

The first integrated native attempt (`2bd7b67`) failed startup on both CPUs.
The free-port test at `c1070b2` reproduces the cause: the one-second TCP connect
probe times out on a closed Windows loopback port instead of reporting refusal.
Startup now probes exclusive wildcard binding without listening, then launches
the owned loopback service normally. This conservatively refuses occupied ports
including wildcard or bound-but-not-listening sockets; it never connects to an
external listener. Kernel Job/HTTP-peer identity is still required after launch.
Six local ownership tests pass; corrected native integration is pending.
See [Microsoft socket binding semantics](https://learn.microsoft.com/en-us/windows/win32/winsock/using-so-reuseaddr-and-so-exclusiveaddruse).

The Windows launcher fixes `RESONANT_VOICE_HOME` inside its verified per-user
configuration directory, including disposable qualification roots. The existing
Resonant initializer retains configuration and creates private credentials.
Before starting managed DSH, the supervisor starts the fixed bundled Resonant
`serve` program in its own Job and passes that exact voice profile to DSH. It
refuses an occupied loopback port without adopting or stopping the listener.
One live Job is retained even if its leader exits before its descendants.
Normal owner shutdown refuses until the voice Job drains; forced Job teardown
remains a separately labelled supervisor-fault boundary.

Voice discovery validates the private home/port/token, established TCP kernel
peer, bundled Node executable, current user and reserved owner's exact voice Job
before credentials. It checks the Resonant protocol and maintenance capability,
then uses its existing prepare/renew/cancel/commit API. Windows graph preparation
now includes this service after DSH and before durable companions. ASR/TTS engines
outside that owned Job are not adopted or stopped.

Five local profile/ownership boundary tests pass, along with existing preparation,
supervisor-policy and launcher checks. New assembled x64/ARM64 assertions start
the actual bundled service, reserve/cancel it with the full graph, reject shutdown
while a real connection ticket is pending, then observe natural commit exit and
restart. Native execution is pending. This qualifies the service lifecycle only;
Windows ASR/TTS provisioning, device capture/playback and acoustic behavior remain
open. The owner's existing Qwen/Breeze placement and settings are unchanged.

### Observed dependency-order drain

`Reservations.commit()` now requires a caller-provided durable checkpoint
callback. It stops and joins only that component's renewal, validates all live
reservations again, records intent, then sends commit once. Other components
continue renewing independently. It records acknowledgment or unknown outcome
and waits on the retained process observation; an unknown reply is never retried.
A failed checkpoint, expired reservation or process that does not exit prevents
further commit and all installer authorization. Cleanup cancels the remaining
reversible reservations; already acknowledged shutdown is never cancelled.

`WindowsPreparation.drain()` orders desktop windows, browser hosts, DSH, its
owned voice bridge, durable companions and the background owner. Before committing
the owner, read-only inventory must confirm every complete child Job has drained,
including descendants outliving a leader. Startup exclusion and all observations
remain held until the caller closes the preparation context.

Twelve local reservation tests and three graph boundary tests pass, covering
checkpoint failure/expiry, renewal races, unknown replies, missing exit and
dependency order. The assembled native fixture is extended to drain an actual
compiled window with DSH, voice, companions and owner, write atomic private
checkpoints, prove exclusive lifetime access and restart with retained history.
These native additions await execution. Its driver deliberately has no product
lease; it performs no file replacement. Production still needs a transaction
journal/recovery implementation and independent installer integration that exits
the installed coordinator before applying files. No Update/Quit UI is connected
to this unfinished global transaction.


### Durable update record

`services/lifecycle/update_journal.py` records one update attempt in a private
directory outside the replaceable application. A kernel writer lock excludes
other coordinators. Every transition uses the shared flushed atomic-file adapter;
a write error makes that writer unusable, including an error after replacement.
The existing record is preserved and requires explicit recovery/archival before
another attempt can claim it. No exception silently resets the phase.

The record binds source/recovery and proposed artifact identities, CPU/OS,
channel and data compatibility. Current support requires mutual schema
readability; incompatible migrations need their own explicit recovery policy.
These fields document already verified artifacts and do not establish publisher
trust. No credentials, conversations, commands or arbitrary executable paths
are recorded. Saved component PIDs are diagnostic hints, never process authority.

Component intent precedes a single commit; acknowledgment/unknown outcome then
observed exit must appear in order. Installer readiness, durable `apply-intent`,
acknowledgment, independently observed installation, local health and completion
are distinct phases. A restart only classifies what to inspect. In particular,
an apply intent without a result is an unknown outcome and never triggers an
automatic retry, relaunch or rollback. Health and installation evidence remain
the coordinator/backend's responsibility, not a claim made by a JSON phase.

Seven local tests pass: actual child-process crash and writer exclusion, failed
flush after replacement, unknown acknowledgment, phase ordering, incompatible
recovery and corrupt-record preservation. Native x64/ARM64 execution is added to
the fast workflow. Authenticated Inno repair fixtures now record intent before
APPLY and check durable state after coordinator exit/crash and before-apply abort;
these new native cases await execution. This is repair of the disposable 0.0.2
fixture with identical bytes, not full application N-to-N+1 or automatic recovery.
Installer result recording, recovery/archival, health, rollback and product UI
integration remain required.

`services/lifecycle/update.py` now composes these contracts for an already
verified/pinned release: durable preparation, observed dependency-order drain,
independent installer readiness, durable apply intent, one authorization and
recorded acknowledgment. Readiness starts after drain so a large component graph
does not consume the installer's preparation timeout. The platform startup
writer stays held until backend observation cleanup; the installer retains its
transferred copy. Success explicitly requires the coordinator process to exit
and does not declare installation complete. Five local fault-ordering tests use
real journal writes and component admission; they cover busy work, failed drain,
missing readiness and lost APPLY replies without replay. Native checks are added
to the fast workflow. Product backend/UI wiring and independent recovery still
need implementation and full installed-artifact qualification.

### Windows installer handoff

The [private installer handshake](WINDOWS-INSTALLER-DECISION.md#authenticated-handoff-source)
transfers the startup writer only to the verified installer's actual process
range. Readiness retains exclusion without authorizing replacement; APPLY is an
explicit subsequent decision. Cancel/loss before that decision aborts. A lost
apply acknowledgment cannot be retried. This source requires native qualification
and integration with global component drain, final exclusive installation access,
transaction recovery and health rollback before a customer update can use it.

The helper's [final installation-access operation](WINDOWS-INSTALLER-DECISION.md#final-installation-access-after-coordinator-exit)
now waits for the actual coordinator exit and takes the private exclusive
lifetime lease before file replacement. The disposable Inno fixture verifies a
held coordinator lease and an additional-holder refusal case. Native execution
of this addition is pending; it does not complete product apply or recovery.

### Windows apply backend

The [Windows adapter and installed integration proof](WINDOWS-INSTALLER-DECISION.md#shared-coordinator-windows-backend)
connect shared durable decisions to independent Inno ownership. No download,
publisher verification or recovery is inferred from this adapter; callers retain
both verified artifacts before admission. Current native integration is pending.

The assembled managed DSH/voice graph at `f950a45` passes on both native CPUs in
[36389905723](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36389905723),
including observed global drain, exclusive installation access and retained
conversation restart. The actual product-installer application added afterward
remains in qualification; these results do not establish public N-to-N+1 updates.

### Independently verified completion

Current customer-updater integration adds explicit authority revalidation to
`authorize_update`: before preparation, before any shutdown, and after installer
readiness before APPLY intent. A false or failed customer authority check cannot
grant apply. Existing fixed-artifact qualification callers omit the optional
hook; that does not authenticate downloaded releases. Post-drain failure preserves
the journal for independent inspection without command replay. See
[shared updater integration](UPDATE-SYSTEM.md#installation-authority-integration-in-progress)
for implementation scope. Its live `AutomaticInstallAuthority` guard now refreshes
publisher verification, rereads current consent/source and retains/rechecks exact
downloads. Production OS entrypoints and independent target completion still need
to compose that guard with the existing preparation/apply adapters; no current
installed receipt qualifies automatic installation.

Independent Windows inspection now separates recorded source and recorded target.
The exact retained target installer accepts read-only `/augmentorinspect=target`
and `target-health` actions. Its extracted metadata/worker/runtime operate outside
the replaceable app, under native maintenance admission, a live journal writer
and a pinned private active record. Target assessment binds version, source,
OS/CPU, channel, data compatibility and installer digest to the exact proposed
target, and requires an apply-authorized phase. Target health additionally checks
the complete embedded inventory and runs only the isolated native health action
under read admission. It preserves the journal and cannot grant apply, become
source-recovery authority or complete a transaction by itself. The external
observer still must observe actual Setup exit and verify selected target before
archival. The portable assessment suite passes eight cases; native template checks
pass both CPUs at `1882338` in
[37115087292](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37115087292).
Full-application target-health checks remain pending and separate from N-to-N+1
or physical-device acceptance.

The external observer can now stage its exact source Python/services/scripts through
`observer_runtime.py`, under caller-held source read admission, into a fresh private
directory outside the replacement tree. Independently supplied metadata binds the
whole source inventory and the exact staged subset. Verification after source
displacement, partial-write refusal and tampered-runtime refusal pass five inert
tests; native template relocation/identity-import checks pass both CPUs at
`536e875` (run 37118685817), while full-runtime checks remain pending. No copied code
is executed by staging, and neither a staging receipt nor saved process identifiers
authorize apply or completion. Live observer IPC is now composed below; completion
and product launch integration remain pending.

`InstallerProcess.transfer_observation` now duplicates query/synchronize-only
process/Job handles and the retained read-only artifact into a caller-bound live
same-user observer. The numbers belong to that other process and must be delivered
once over its authenticated live IPC; they are never journal fields or a saved-PID
recovery instruction. `InstallerObservation` checks private artifact identity/hash,
the actual primary image's kernel file identity, same-user process membership and
the non-killing Job, then observes full Job exit without a terminate/authorize API.
Closing either observation scope preserves Setup. Native template qualification
at `536e875` passes same-process adoption/sender-close on both CPUs. The subsequent
`windows_update_observer.py` uses a live private pipe, fresh launch nonce and exact
kernel primary-process/Job binding to transfer observations to the separate parent.
The child requires confirmed retention and parent liveness before native APPLY;
no saved PID/handle/nonce authorizes any operation. The observer awaits complete
coordinator and Setup Job exit, preserving either on timeout. Native exact-template
and full-application fixtures now exercise this separate-process channel; those
newer checks remain pending and the full fixture still applies identical artifacts.

The fixed external `windows-update-coordinator.py` now composes the qualified
current source, complete payload integrity, exact retained recovery selection,
fresh TUF/consent authority and shared durable coordinator with graph preparation
and `ObservedWindowsApply`. Only fixed OS-derived production paths are accepted;
the production entrypoint has no fixture/trust fallback or arbitrary command.
Source startup read admission ends before requesting the graph writer; installation
read admission stays until this actual coordinator exits. External coordinator Jobs
explicitly permit the independently observed Setup's breakaway without enabling
kill-on-close. Five portable refusal/unknown-acknowledgment wrapper cases pass.
The owning service/supervisor launch, target-health completion, restart and signed
cross-version qualification remain pending; no qualified automatic flag is set.

An actual ARM64 full-application recovery at `97837de` crossed its former five-minute
Setup observation deadline; its inner log records successful installation afterward.
The observer preserves the recovery and never restarts that Setup. It now observes
the same Job for at most ten minutes; native outer observation allows twenty minutes
including independent inventory/health. Fresh native recovery evidence is required.

Update journals now support independent completion after the caller has observed
installer exit, reverified the release pair/installed selection and passed a local
health callback. Completed records are durably archived; failed health, an
unmatched artifact pair or a pre-APPLY record cannot finish the attempt. Four
new local fault/preservation tests pass (16 combined coordinator/journal checks).
The installed Windows proof now checks every payload file and a real Qt launch
before archiving. Native execution of this completion path is pending. This does
not implement recovery from an unknown installer outcome or rollback.

`UpdateJournal.complete_verified` takes a fresh exclusive journal claim and
independently revalidated source/target identities. It calls the health observer
with a copy of the record, advances only the final installed/healthy/complete
states, then durably renames the record to `completed-<id>.json` in the same
private directory. A subsequent update can claim a new active record. An archive
failure retains either the active completed record or its archive; this method
never retries an uncertain write or infers installer completion from a saved PID.
A record alone remains insufficient authority to launch, replay or roll back.

Windows native startup now enforces that distinction before Python loads:
ordinary desktop/browser launches refuse any active update record under the fixed
private base. The dedicated [local-health action](WINDOWS-INSTALLER-DECISION.md#recovery-aware-startup-and-isolated-local-health)
retains startup/installation read leases but uses a disposable profile and no
controller, IPC registration or service connections. Its bounded Job observer
verifies the independently identified release; failed or missing health leaves
the journal unresolved. Compiled guard/routing and source UI health pass both
Windows CPUs; full installed health qualification is pending. The independent
interrupted-update executor remains required; ordinary startup must not bypass
the record to work around that gap.

### Confirmed cancellation before shutdown

The shared coordinator now archives an unsuccessful reversible preparation only
when the same live platform context confirms release of every reservation and
its startup fence, and the journal has no shutdown checkpoint. Windows exposes
this observation only after cleanup returns confirmed, with no commit started.
Busy work remains running. A generic exception, missing observer, lost release
reply, in-flight cleanup or uncertain journal write cannot establish cancellation.

The original journal writer accepts only `verified`, `preparing` or `prepared`
with no steps. It records terminal `cancelled`, durably renames the record to
`cancelled-<id>.json`, and releases the writer. The original refusal still reaches
the caller, while the active record no longer blocks a later ordinary launch or
fresh attempt. A checkpoint, installer readiness, APPLY intent or closed writer
refuses this method. It does not resume saved commands or reopen stopped services.
Crash/failed flush/archive preserves the active record and requires independent
inspection; even an active `cancelled` phase is not permission to delete it.

Independent installed-state verification now has a shared [payload inspector](WINDOWS-UPDATE-DELIVERY.md#exact-installed-payload-inspection).
The caller supplies trusted release/inventory bytes and retains admission; a
complete match includes absence of obsolete files, followed separately by local
UI health. The report alone cannot select a recovery source, delete differences,
replay an installer or archive the journal. Native integration is pending.

Five new journal fault tests and two platform/coordinator cleanup tests pass
locally (43 update tests plus five preparation tests). The actual DSH Windows
proof now attempts an update during a held model turn, requires native component
release and cancellation archival, and asserts the turn remains running with no
installer requested. That proof uses synthetic artifact identity and cannot apply
software. Native execution is pending. Recovery after shutdown or installer
preparation still needs the separate independent recovery flow.

## Controller-free preview maintenance close

Full installed Windows x64 qualification at `594b56d` found that legacy idle
`maintenance.close` acknowledged and closed a preview widget while leaving its
process alive. Preview has no controller, and the shared app intentionally keeps
its event loop alive when the last window is hidden. The explicit maintenance
finish callback now rechecks local work and quits only after an accepted window
close, after replying/disconnecting. The token-based commit path shares this
callback. Shortcut hiding retains its existing behavior; drafts and reservations
still refuse legacy maintenance.

An actual two-preview-process portable test reproduces the old exit timeout and
passes after the fix, observing normal exits from both token commit and legacy
idle close. Four desktop maintenance tests also pass. Both native Windows and
the complete installed repair/apply/removal sequence need new execution.


## Independent recovery source observation

`lifecycle/recovery_source.py` checks an independently identified installer/release
against a validated interrupted journal's exact source. The Windows installer
holds live exclusive maintenance and journal-writer locks, pins the private record,
and snapshots it outside the installed app. A matching result records only source,
metadata and journal hashes plus the remaining observation category; it never
replays recorded PIDs or authorizes apply. See [the native boundary and evidence](WINDOWS-INSTALLER-DECISION.md#independent-recorded-source-assessment).

Recovery source lookup now uses the validated active record's exact source digest,
even if the installed selection already names the target or is missing/damaged.
It never falls back to the newest cached version. The caller holds live maintenance
and writer admission; the helper pins actual source bytes, retains record identity
and requires later independent embedded-metadata comparison. Lookup neither changes
the journal nor executes a saved action. Local tests pass; native changed-selection
lookup and the complete restoration executor remain separately required. See the
[lookup contract](WINDOWS-INSTALLER-DECISION.md#locate-the-recorded-source-after-selection-changes).
Malformed, foreign and incompatible sources refuse. Six source-assessment tests
and all 43 existing update cases pass locally; native integration is pending.

The independent inspector now has a source-health mode. It keeps the live writer
and original record pinned while changing to native read admission, verifies the
entire exact source payload, then starts only the isolated fixed health action.
The active record continues blocking ordinary startup; read admission blocks
replacement/removal. The owned probe's complete exit and shared strict report
validation are required. No record or selection changes, file restoration or
reopening follow merely from successful health. See the [contract and separate
synthetic/full native evidence](WINDOWS-INSTALLER-DECISION.md#independent-source-health-before-restoration-completion).

## Distinct source-restoration completion

`SourceRestoration` records a fresh recovery attempt separately from the original
update. It binds exact original/source metadata, persists apply intent, requires
fresh installer-exit observation, then verifies source selection/registrations,
full inventory and isolated health under held read admission. Only then does it
write a distinct `source-restored` receipt and archive the original bytes unchanged.
The failed update's target and shutdown history never become a fabricated forward
completion. Unknown writes stop the live attempt; no saved command or PID is replayed.

Thirteen portable fault/storage tests pass, including real child crash and live
writer exclusion; all 62 update cases pass locally (one Windows-only skip).
Native full application qualification now composes this shared journal with the
actual source installer and real UI health. Its execution and the product outer
observer remain pending. See the [contract and boundaries](WINDOWS-INSTALLER-DECISION.md#distinct-durable-restoration-outcome).

The retained installer now extracts an [independent recovery observer](WINDOWS-INSTALLER-DECISION.md#independent-recovery-observer)
that composes the shared attempt, independent source installer, observed exit and
complete source verification. Its native parent releases initial admission only
after preparing the bounded worker; the worker revalidates the exact original
under fresh admission before intent. Installer lifetime uses explicit Job breakaway;
source health retains read admission and a pinned active record. Native observer
and crash qualification remain pending; customer recovery routing is not enabled.
