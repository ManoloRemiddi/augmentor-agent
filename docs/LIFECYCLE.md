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

The shared Resonant Voice 0.1.18 candidate exposes the same private reservation
vocabulary through its existing authenticated `/internal/maintenance` endpoint.
Read its [versioned contract](https://github.com/ManoloRemiddi/resonant-voice/blob/7a6645ea27f55bdd18acbc22c2893a09bed58004/docs/PROTOCOL.md).
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
still must preserve drafts, reserve open panels and prevent reconnect during
coordinated updates. Portable real-process tests hold a shared request over EOF
in the parent and both bridges, then require a complete final response and Node
`beforeExit`. The DSH bridge case uses a deliberately unavailable isolated
endpoint, not a real model or WebSocket session. Voice tests use controlled
workers/submissions and do not qualify a physical audio device. The new assembled
Windows browser flow still needs native execution.
