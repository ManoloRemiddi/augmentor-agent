<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Windows desktop and background controls

This is an implementation contract for the development candidate, not a customer
installation guide. See the [implementation evidence](WINDOWS-IMPLEMENTATION-STATUS.md)
and [W4 plan](WINDOWS-IMPLEMENTATION-PLAN.md#w4--complete-the-native-windows-desktop-experience).

The shared desktop retains its existing appearance, settings and two independent
windows. `Augmentor.exe` embeds the private Python runtime and selects the common
desktop module. Repeat app launches request Show. The shortcut activation helper
uses the same authenticated instance endpoint to request Toggle; an absent
endpoint permits a cold launch, while an uncertain delivery never gets replayed.

Before delivering a user-initiated Show/Toggle request, the launcher/shortcut owner
offers its foreground permission to the kernel-authenticated pipe server PID with
`AllowSetForegroundWindow`. Windows may still refuse focus; Augmentor does not
inject keys or attach input queues to override that policy. The shared window
then performs its normal Qt activation. Real foreground/input acceptance remains
a physical-machine check. [Windows foreground handoff](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-allowsetforegroundwindow).

The embedded launcher intentionally excludes arbitrary PATH/current-directory DLL
search. Its Python entrypoint retains explicit DLL-directory handles for private
Python, PySide and Shiboken libraries and selects the bundled Qt plugin directory.
This allows separately loaded image plugins to resolve their Qt dependencies
without restoring global DLL search. [Python DLL directories](https://docs.python.org/3/library/os.html#os.add_dll_directory).

The product build embeds the existing Augmentor vector icon at seven sizes
(16–256 pixels), the shared product version, and an ordinary-user application
manifest. Per-monitor V2 DPI awareness prevents Windows from treating the entire
window as an old bitmap-scaled application. Long-path awareness is declared;
this does not remove Windows policy or third-party path limits. The OS compatibility
GUID is the shared Windows 10/11 manifest identifier, not a Windows 10 product
support commitment. Native qualification reads these resources back from the
compiled executable. Mixed-monitor DPI and Explorer/taskbar visuals still need
physical Windows acceptance. See [Microsoft application manifests](https://learn.microsoft.com/en-us/windows/win32/sbscs/application-manifests).

## Keyboard ownership

The existing Windows supervisor now hosts a Qt event loop and owns both native
`RegisterHotKey` registrations, independently of either desktop window. Defaults
are Ctrl+Alt+Space and Ctrl+Alt+Shift+Space. A collision leaves the affected default
unassigned; the shared Settings editor can choose an available combination. The
Windows adapter supports Ctrl/Alt with optional Shift and letters, digits, Space,
navigation keys and function keys except F12. Windows-key combinations and bare
keys are refused. Keyboard-layout and physical-input acceptance remains pending.

Only the owner thread registers, unregisters or edits shortcuts. Named-pipe
workers queue an explicit Qt slot. A settings save registers the proposed binding,
atomically writes its private user-owned record, then releases the old binding.
An OS collision or failed file write keeps the previous live choice and record.
The two agent windows cannot claim the same combination. Obsolete queued messages
cannot activate a replacement binding; identifiers are not reused. `MOD_NOREPEAT`
prevents held-key repeat notifications. Shutdown unregisters owned bindings.

The only added supervisor requests are `shortcut-status` and `shortcut-save`, with
fixed fields and one of the two supported window identities. Pipe authentication
and application-root matching remain required. A timed-out save is not replayed;
Settings must read the current value before another explicit save. Activation runs
outside the event loop, with at most one outstanding action per window.

Native tests exercise actual OS collision rejection, file-save rollback, queued
`WM_HOTKEY` delivery through Qt, release and two-window separation. A posted
message is explicitly not physical keyboard evidence. The supervisor integration
test verifies persistence and worker-to-owner dispatch through the private pipe.

## Login registration mechanism

`windows_startup.py` provides one owned HKCU Run value pointing to the installer's
stable `current/Augmentor.exe --background` path. It does not resolve that path
to a version directory. Repeated registration performs no write, unfamiliar values
are preserved, and removal deletes only the exact owned command. It never changes
HKLM or Windows `StartupApproved` state. The executable's background mode starts
the same per-user supervisor without opening a chat window. Source launches do
not enable login startup; installer hooks still need to call this mechanism.
Native tests use a disposable HKCU key, not the actual login key. Real Windows
startup-disable behavior and logout/login still require installed acceptance.

## Shared companion ownership

The supervisor additionally exposes fixed `start-prompts` and `start-memory`
operations. Each launches only its shipped service, with the private interpreter,
inside a separate Windows Job retained by the same supervisor. Repeated starts
reuse the live child. An already-running endpoint outside that owner is preserved
and reported as a conflict; no process is adopted or killed by filename or PID.
Status distinguishes the Job helper PID from the service PID. Logs remain in the
private supervisor directory. A supervisor crash closes its Jobs and contains
their descendants. This is fault containment, not graceful product Quit.

The native test queries both actual services, checks repeat-start identity,
refuses an empty-owner exit while they run and observes their kernel process
handles after a deliberate supervisor fault. This passes on both native CPUs at
`840127f`. Python and Node clients now request fixed startup operations through
that owner only when their service endpoint is proven absent. Node uses a bounded
private-Python helper; it never starts the service daemon itself on Windows.
Timeouts or lost responses after a connection do not replay the original request.
Already-running service endpoints retain their existing transport behavior.
The companion-client test adds real Python cold startup, Node memory startup,
prompt save/restart and continued memory-process identity. Native execution of
that client adoption remains pending. Service quiescence and accepted-request draining
remain required for ordinary shutdown and updates.

## Remaining shell gates

The shared instance handler now drains commands already queued while the window
was being constructed. A Qt event processed before `newConnection` was connected
could otherwise leave the first command waiting until another arrival. This is
a shared startup correction; native regression of the new source is pending.

This source does not yet complete tray Open/Quit, installer login hooks, installed
Start menu/taskbar identity, coordinated busy-work shutdown or update ownership.
These remain required before customer distribution. A successful preview or
hotkey backend test must not be described as an installed Windows application.

The shared window now exposes [reversible component admission](LIFECYCLE.md#desktop-admission)
to the future coordinator. Local two-window proof checks draft preservation,
cancelled preparation and normal committed close. New source counts accepted
controller work and pauses reconnect during preparation; Windows execution is
pending. This does not yet add a global Quit or installer action.

## Background-owner reservation

The private supervisor pipe accepts `action: maintenance` with the shared exact
`method`/`params` component contract. Preparing this owner closes admission to
new component starts, failed-setup stops, shortcut saves and shortcut activations.
It does **not** stop or declare idle the children already running. Their status
and shortcut settings remain readable. Cancel/expiry restores startup admission.
Commit refuses until every owned child has exited; it acknowledges before the
Qt loop exits normally. The legacy empty-owner exit cannot bypass a reservation.

The shell and supervisor share one admission counter. A shortcut activation is
counted before executor submission and stays counted until completion/cancellation.
An accepted queued Qt settings operation stays counted through its actual
execution even if the pipe caller times out. A proven unstarted cancelled item
releases its reservation without applying the setting. These rules prevent a
shortcut or reconnect from opening a new component between global preparation
and final installation-file exclusion.

Portable owner/Qt tests pass, including a lost reply while the accepted Qt
operation is still executing. Native owner tests now reserve/cancel, refuse a
settings write and commit an empty owner to exit zero; execution is pending.
The whole-product coordinator still needs window/browser/harness/voice discovery,
component reservations and exclusive installation access. This source adds no
customer-facing Quit or installer transaction by itself.

Normal owner status now checks the Windows Job's actual active-process count
after its leader exits. A surviving descendant keeps the component owned and
blocks commit/replacement startup; status never closes its Job to make it appear
stopped. `wait_graceful` times out while preserving a live Job. The explicit
fault/bootstrap `wait`/termination behavior remains separate. A new native test
lets a parent exit, proves its detached descendant survives a graceful timeout,
then lets the descendant exit itself and observes the fully drained Job. Native
execution is pending; the portable supervisor regression passes. This Windows
process-range check makes no new descendant-tracking claim for Unix adapters.

References: [Microsoft RegisterHotKey](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-registerhotkey)
and [Qt native event filters](https://doc.qt.io/qt-6/qabstractnativeeventfilter.html).

## Window discovery for maintenance

`services/lifecycle/windows_components.py` observes held private instance locks
and authenticates each corresponding pipe peer with the Windows kernel. It
retains an actual process handle, checks the executable and selected build root,
and requires the window's advertised reservation protocol before sending control
requests. Every later connection must still belong to that same live process.
An unknown build or old protocol refuses discovery; it is not closed or adopted.
Stale files remain untouched. Observation handles grant no termination rights.

This is a snapshot, not complete installation exclusion. A coordinator still
must prevent new startup, reserve every participating component, observe normal
exit and obtain exclusive installation access before replacing application files.
The native two-window proof now exercises discovery, another build's refusal,
prepare/cancel and observation after normal exit. Its portable path passes;
the new native discovery assertions await execution.

Earlier pending component entries above are superseded by full runtime
`e7228e5` passing both native CPUs in [run 36372119531](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36372119531).
Owner reservation and full Job drain additionally pass both CPUs at `303a619`
in [desktop run 36372703256](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36372703256).
These remain hosted component tests, not a finished customer installer or
physical keyboard/browser acceptance.

## Native startup lifetime lease

The application and browser executables now acquire the existing installation
lease before loading private Python or Qt. The native helper reads the current
Windows token and OS Local AppData path, creates protected current-user/SYSTEM
objects, and validates existing ownership, ACLs, reparse points and hard links
without repairing unfamiliar data. Owned directory and file handles stay open
through Python finalization and process exit. Its shared byte-zero lock excludes
Python maintenance; its shared file handle also excludes Inno's no-sharing gate.
No new persistent maintenance marker can remain after a crash.

Only builds explicitly marked as development candidates compile support for the
existing `--qualification-root` switch. They require an existing private root,
and return early-refusal code 73 without a modal dialog for disposable launches.
Customer builds use OS-owned paths. The historical installer fixture executable
retains its separate fixture gate; it is not the application launcher.

The new compiled probe tests both executables without a runtime beside their
copies, proving refusal precedes Python loading. It covers byte/no-sharing
exclusion, hard links, unchanged broad ACLs and junction targets. Positive
embedded-Python fixtures hold the lease through their work and release it on
normal exit. The full compiled window proof additionally checks the real app's
lease while both windows run. Native execution of these additions is pending.

This closes early native-entrypoint loading, not all update coordination: direct
companion interpreters remain covered by their owning process ranges and Python
leases. Global startup reservation, browser participation, independent apply,
recovery and production installer integration remain required. Implementation
follows [Microsoft's file-lock contract](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-lockfileex)
and [handle-based security inspection](https://learn.microsoft.com/en-us/windows/win32/api/aclapi/nf-aclapi-getsecurityinfo).

At `bfde231`, [desktop run 36373865190](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36373865190)
passes both CPUs, including all new compiled early-lease cases and normal release.
The initial `653adac` probe used a file flag from the wrong pywin32 module;
that test-only correction is included. Full assembled early-lease integration
remains a separate pending run. Full runtime `303a619` now passes both native
CPUs in [run 36372703204](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36372703204),
including complete Job drain and owner reservation, before the new early lease.

## Short-lived startup exclusion

The native desktop and browser launchers additionally open a private
`run/startup.lock` reader before loading Python. The file has the same strict
current-user/SYSTEM descriptor, no-reparse and single-link requirements as the
lifetime lease. Readers request read access and share only read access. A
maintenance writer requests read/write access and also shares only reads: any
unregistered startup prevents its acquisition; once acquired it refuses new
startup readers and competing maintenance writers. No file content signals busy
state, and a crash releases the kernel-owned handles.

`AugmentorStartupReady` releases only the native startup handle. The desktop calls
it after constructing its window and private command handler; browser readiness
requires its Job/executable-verified bridge registration. Windows source previews
and independently starting supervisors use the same Python reader. A preview
without discoverable controls keeps the reader until normal exit. Existing
supervisor status stays readable while maintenance prevents creation of a new
owner. The process lifetime lease remains held through finalization and exit.

The separate startup file allows an independent applier to inherit a duplicate
of the writer handle while the final no-sharing `installation.lock` gate waits
for all running application code to exit. This avoids a close/reopen gap. The
new kernel proof exercises explicit handle-list inheritance, normal coordinator
exit and deliberate coordinator crash, then verifies continued startup refusal,
independent installation exclusion and release after the recipient exits. This
is a transfer primitive, not a production installer transaction; the authenticated
handoff, complete component coordinator, renewal, rollback and recovery remain
required before applying updates.

Native execution of these startup additions is pending. Portable browser
registration and supervisor policy tests pass. The compiled launcher probe now
tests pre-Python startup-writer/hard-link refusal and an explicit readiness signal
without releasing the lifetime lease. Full window/browser probes check readiness
against the actual assembled applications. Sharing and transfer follow
[Microsoft CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)
and [DuplicateHandle](https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-duplicatehandle).

At `e4593b1`, [both native desktop jobs](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36378514808)
pass startup-reader/writer sharing, inherited-handle retention across parent exit
and crash, compiled early refusal and readiness release with the lifetime lease
still held. Full assembled application execution remains a separate gate.

## Background owner and component observations

Current source publishes the owner's PID, build root and maintenance capability
through its authenticated pipe. `discover_owner` reads the held private owner
registration, retains the kernel process handle and verifies its executable and
build without starting a background process. Its maintenance client refuses a
replacement pipe/process and validates the shared component protocol.

After reserving the owner, `observe-child` can confirm that an already observed
PID belongs to the exact live Job for DSH, prompts or memory and uses the expected
private executable. It exposes no launch, termination or arbitrary-command RPC.
The eventual component client must retain its own process observation and bind
it to the transport before using this check. A reported PID alone is insufficient.
New native tests cover valid prompt/memory peers and reject an unrelated process,
another component's Job and unknown component names; execution is pending.

The companion maintenance client now binds prompt/memory RPCs to those exact
kernel pipe peers and Jobs before sending a request. It verifies correlation,
protocol, idle acknowledgments and finite reservation lifetime. Discovery refuses
an unowned listener or incomplete owner inventory. Native supervisor qualification
now prepares, renews and cancels each actual companion while retaining the owner
reservation. Execution of these new assertions is pending.

## Observed local HTTP

Source now provides a Windows loopback transport for the owned DSH/voice
maintenance clients. After connecting to explicit `127.0.0.1`, it finds the
server side of that exact established TCP connection in the kernel ownership
table, retains the process, verifies its Windows user and executable, and calls
the reserved owner's Job verification before sending HTTP headers or tokens.
Later requests must still reach the same live process. A new listener on a reused
port is refused before credentials are sent. The transport does not follow
redirects, discover proxies or reconnect/replay requests.

The native test launches disposable actual HTTP processes and verifies correct
PID observation, refusal before HTTP bytes for wrong ownership/executable, and
refusal after a replacement binds the same port. Execution is pending. This is
the transport primitive; DSH/voice profile integration and global coordination
still need their own qualification. The table layout and connection ownership
follow [GetExtendedTcpTable](https://learn.microsoft.com/en-us/windows/win32/api/iphlpapi/nf-iphlpapi-getextendedtcptable)
and [MIB_TCPROW_OWNER_PID](https://learn.microsoft.com/en-us/windows/win32/api/tcpmib/ns-tcpmib-mib_tcprow_owner_pid).

`windows_dsh.py` now uses that transport for the supervisor-owned DSH profile.
It checks the private managed record and service anchor, product version,
maintenance protocol and token-derived home identity. Every maintenance request
must reach the retained Node peer in the owner's exact DSH Job. The assembled
managed-runtime proof now exercises prepare/cancel, refused model input, normal
commit, complete Job drain, retained-process exit and history after restart
through this client. Native execution is pending. Existing external/manual DSH
connections are not adopted or stopped. Owned voice startup remains an explicit
feature gap; this change does not imply that the Windows speech engine is ready.


## Reversible component preparation

`windows_preparation.py` binds the startup writer and retained component clients
to one reversible context. It reserves the live owner first, then surfaces,
managed DSH and companions; every confirmed reservation has its own heartbeat.
Closing the context cancels in reverse order before releasing observations and
startup exclusion. Discovery/identity failures take the same cleanup path as
busy responses. A transport exceeding cleanup bounds keeps those resources in
a deferred cleanup worker until its in-flight request returns.

The actual prompt/memory native proof now verifies group renewal, launch and
second-writer exclusion, cancellation and continued process life. The assembled
proof includes compiled desktop plus DSH and companions, unchanged restored
history, and busy DSH refusal without cancelling its active model turn. These
new native assertions await execution. Six portable reservation and two graph
failure tests pass, along with existing admission/owner policy checks. This
context intentionally exposes no commit/apply operation. See the shared
[lifecycle contract](LIFECYCLE.md#coordinated-reversible-preparation).


Installer processes use a separate [independent process adapter](WINDOWS-INSTALLER-DECISION.md#independent-installer-process-ownership).
The ordinary service `OwnedProcess` remains kill-on-close for fault containment.
Its semantics must not be reused for an installer that must outlive Augmentor.
New installer Job/byte-binding native qualification is pending.
