<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Windows implementation evidence

All `3c6d78b` Linux source/installed-package/browser jobs, macOS feasibility,
fast native Windows and Inno handoff fixtures pass. The actual full Windows
application installer integration is still running and is not yet qualified.

Update journals now support independent completion after the caller has observed
installer exit, reverified the release pair/installed selection and passed a local
health callback. Completed records are durably archived; failed health, an
unmatched artifact pair or a pre-APPLY record cannot finish the attempt. Four
new local fault/preservation tests pass (16 combined coordinator/journal checks).
The installed Windows proof now checks every payload file and a real Qt launch
before archiving. Native execution of this completion path is pending. This does
not implement recovery from an unknown installer outcome or rollback.

Full native runtime at `f950a45` passes on **both x64 and ARM64** in
[36389905723](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36389905723),
plus the shared Mac Qt candidate. This qualifies the shared voice 0.1.19 pin with
actual managed DSH/voice startup, compiled desktop Send/Enter/history, observed
graph drain, exclusive access after drain, owner/service restart and compiled
browser commit. The provider is deterministic; physical audio/input and live
model quality are not claimed. The newer actual full-payload installer and
`WindowsApply` integration at `3c6d78b` are now running; those installed-package
checks have not yet passed.

The actual installed-app qualification now composes the shared coordinator with
`WindowsApply`: an independent Inno process, private authenticated handoff and
one-shot durable APPLY. The fixture starts an installed window and background
owner, drains their observed graph, retains the extracted Setup process across
coordinator exit, waits for its completion and relaunches installed binaries.
It repairs the identical retained artifact, so it does not establish N-to-N+1,
publisher trust, health-driven recovery or rollback. New native execution is
pending. Existing Inno handoff/final-access fixtures at `b006ebb` pass both CPUs
in [36390819194](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36390819194);
that result compiles the updated helper but does not execute the new app installer.

Current source builds an unsigned installer candidate from the actual staged
shared app with `scripts/package-windows.py`. It uses one app identity, stable
`current/Augmentor.exe`, bundled runtimes and a Start-menu shortcut. Native
startup/lifetime exclusion now supports fresh installation, identical-build
repair and removal. The remover copies its exact hash-bound helper to a temporary
location, retaining both gates while deleting installed binaries. Existing
redirected/hard-linked trees are refused; persistent data stays outside the
installer tree. Manual cross-build replacement is intentionally unavailable until
the coordinated update/recovery path is connected.

Three portable build-intake checks cover wrong CPU/public metadata, incomplete
payloads and source-link refusal. New full-payload installation, native Qt preview,
live-draft maintenance refusal, repair/relaunch, path refusal and uninstall/data
preservation assertions are scheduled on both native CPUs; execution is pending.
Qualification has compiled-in disposable paths and uses Server build 26100 only
for the hosted x64 runner; the normal candidate minimum remains Windows 11 25H2
build 26200. This is not signed/public delivery or ordinary-user/physical testing.
Login integration, browser-registration removal, product N-to-N+1, recovery and
rollback remain open alongside the feature ledger.

Current shared dependency is **Resonant Voice 0.1.19**, exact source
`7d0fd6d677ea4bbbca0183a6bb3a3d3f24a8147a`. Its native x64/ARM64 configuration and
maintenance checks pass in [36389214161](https://github.com/ManoloRemiddi/resonant-voice/actions/runs/36389214161),
and the packed archive passes disposable DSH install/compose/remove. This fixes
Windows ownership during automatic profile cloning/preferences. The shared lock
and complete package select this same archive on all OSs. Assembled native graph
drain/restart remains to be qualified with it; physical audio remains open.

At `9cc54b1`, [Inno final-access qualification](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36389318640)
and [fast Windows desktop](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36389318570)
pass both CPUs. Actual extracted Setup retains startup exclusion through
coordinator exit/crash, acquires final installation access and refuses an
additional lifetime holder. The fast run includes all 12 journal/coordinator
tests. These are controlled fixtures, not an installed customer update. Continue
product installer/backend wiring, independent recovery and the full feature ledger.
No Windows customer release or personal deployment is made.

The pending statuses below are historical checkpoints, superseded only by the
specific results recorded above.

Current source adds shared update decision orchestration: five local tests with
real journal writes/admission pass (12 combined journal/coordinator checks).
`2b1680d` full x64 confirms managed DSH and owned voice startup, then refuses a
voice config whose Windows owner changed during automatic profile cloning.
Resonant 0.1.19 candidate `7d0fd6d` corrects that separate package; native checks
must pass before Augmentor repins it. The `3394145` native helper compiles on both
CPUs; Inno's Boolean/BOOL type mismatch is corrected in source and awaits execution.
Earlier [Inno journal qualification](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36388207448)
passes both CPUs. Full graph drain, installed update and recovery remain open.

Fast native [`1872e19`](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36388207564)
passes both CPUs, including all seven private-journal crash/write tests. Current
source adds final Setup access after actual coordinator exit and refusal while an
additional lifetime holder remains. New helper compilation/Inno execution is
pending; full owned-voice/graph drain and the earlier Inno journal additions are
still being qualified. See [final access contract](WINDOWS-INSTALLER-DECISION.md#final-installation-access-after-coordinator-exit).

The shared [durable update record](LIFECYCLE.md#durable-update-record) now has seven
passing local tests, including actual process crash and exclusive writer claims.
New native fast tests and authenticated Inno before/after-APPLY journal assertions
await execution. This does not implement automatic recovery/rollback or installed
N-to-N+1 application. The port correction at `2b1680d` passes fast x64; ARM64 and
the actual owned-service/drain integration are still being qualified.

Current correction: both native CPUs reproduce the free-loopback-port timeout in
[`c1070b2` desktop qualification](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36387350489).
The voice startup probe now uses exclusive wildcard binding without listening;
it cannot mistake a short connect timeout for an unavailable port or contact an
external service. Six local tests pass, including occupied wildcard and
bound-but-not-listening sockets. Native corrected startup/drain remains pending.

September 27, 2026. The owner authorized autonomous implementation and will
connect a Windows machine for joint physical testing afterward. Follow the full
[implementation plan](WINDOWS-IMPLEMENTATION-PLAN.md); this ledger does not narrow
its outcome. No Windows customer release or installed-product claim exists yet.

Latest source, September 28: explicit graph drain requires durable caller
checkpoints and observed exits, renews remaining participants, and checks complete
Jobs before owner shutdown. Twelve local reservation and three graph tests pass.
The assembled window/DSH/voice/companion drain, exclusive-lease and restart proof
awaits native execution; installer application and recovery remain unfinished.
Linux [`2bd7b67`](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36385346967)
passes all 647 native assertions but exits 139 during Qt interpreter shutdown.
The actual Chromium commit/reconnect step passed before that failure. Local
isolation and GDB traced the shutdown failure to the shell's temporary Qt thread
wrappers. The corrected creating-thread dispatch passes all 645 local assertions
and exits zero; hosted qualification is pending. See [thread dispatch evidence](WINDOWS-SHELL.md#keyboard-ownership).
The failed workflow is not waived. The new free-loopback-port startup test also
passes locally (six voice ownership checks total).

Full `2bd7b67` x64 fails inside managed service startup, before voice integration
qualification. The fixture now writes its previously discarded supervisor output
to a private log and includes bounded diagnostics on failure. The earlier
`1bf1b78` compiled browser commit passes x64; ARM64 stops earlier at a native
transcript snapshot comparison. The updated fixture compares the snapshot taken
inside the prepared admission fence and includes expected/actual values on
failure. Both corrections require new native execution.

Source `2bd7b67`, September 28: managed DSH now starts its bundled Resonant loopback
bridge through the existing owner, with one retained Job, private profile and
occupied-port refusal. Kernel-bound voice maintenance joins graph preparation.
Five local profile/ownership refusal tests, two graph failure tests, six portable
owner tests and five launcher tests pass (two native owner tests skip on Linux).
Assembled real-service graph/ticket/commit/restart assertions are added; native
execution is pending. This does not qualify Windows ASR/TTS engines or audio.
Full runtime at [`e63312b`](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36383783733)
now passes both CPUs, including corrected graph and capture assertions.

Latest browser checkpoint, September 28: idle browser commit rechecks context inventory
and page state, replies through its private owner, then drains the native host
naturally. Actual local Chromium verifies retained-process exit, same-page
reconnection, a post-commit draft and selected conversation preservation. All
265 Node/Browser and seven private-transport tests pass. New compiled Windows
commit assertions await execution; this is not an installed-version upgrade.
At `e63312b`, [fast desktop](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36383783782)
and [authenticated installer fixture](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36383783743)
pass both CPUs. Its [full graph qualification](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36383783733)
also passes both CPUs. Global commit/apply, owned voice, remaining platform features,
recovery/rollback, physical hardware and customer release gates remain open.

The following checkpoints are chronological history, not the latest capability
status; subsequent evidence supersedes pending/disabled statements only within
its stated scope.

Earlier checkpoint: full runtime passes both CPUs at `f079931`, including the
corrected bootstrap token, actual compiled desktop/DSH maintenance, background
owner reservation, complete Windows Job drain, kernel-verified window discovery
and the pre-Python native lifetime lease.
The separate voice 0.1.18 candidate passes native configuration and maintenance
on both CPUs.
Browser source drains accepted parent and DSH/Pi bridge operations and reserves
all open extension documents. Linux/Mac and all hosted Windows workflows pass at
`f079931`. New source adds the actual private native browser owner, correlated
admission and kernel-based Windows discovery. Local real Chromium, transport and
regression checks pass; compiled native execution is pending. Commit remains
disabled. The lifetime lease is not the short-lived global startup fence.
Installer backend is **Inno Setup/WinSparkle**; earlier Velopack
candidate entries below are historical. Global coordination and full app release
are not complete.

The native browser-owner change at `df52b47` passes compiled x64 qualification,
both fast Windows desktop jobs, installer feasibility, Linux (including actual
Chromium through product private control), and macOS. Full ARM64 qualification
is still running in [36377424868](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36377424868).
Current source adds [short-lived startup exclusion](WINDOWS-SHELL.md#short-lived-startup-exclusion)
before Python loads, releases it only after discoverable controls are ready, and
adds real-Windows duplicated-handle transfer tests. Portable browser registration,
supervisor policy and launcher policy checks pass. These new kernel/compiled
assertions await native execution. No installer apply or browser commit is enabled.

Subsequently, all workflows pass at `df52b47`, including full x64/ARM64 in
[36377424868](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36377424868).
The new startup fence at `e4593b1` passes [both fast Windows jobs](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36378514808),
including actual compiled launchers and inherited-gate preservation across exit
and crash. Full runtime execution is still running. Its Linux Chromium proof
exposed a qualification-owner race: initial DSH and replacement Pi native hosts
shared one test endpoint. Current qualification uses a separate actual private
owner per native host, matching Windows, and adds simultaneous-host registration
and normal-exit evidence. The product's Windows owner was already per process.
Current source also adds retained background-owner discovery and read-only
component Job verification; its new native assertions await execution. Global
coordination, component transports and installer apply remain unfinished.

Full native runtime `e4593b1` subsequently passes both CPUs in
[36378514796](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36378514796),
including actual assembled desktop/browser startup readiness. `3a379a2` contains
the corrected per-host Chromium qualification and background-owner observation;
its hosted jobs are running. Current source additionally binds prompt/memory
maintenance to their retained pipe peers and owner Jobs, validates idle/expiry
acknowledgments, and extends native companion reservation tests. Portable policy
checks pass; new native companion execution remains pending.

Both fast Windows jobs at `3a379a2` pass retained background-owner discovery and
exact prompt/memory Job observations in
[36379432569](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36379432569).
The companion participant client is pushed at `6531e2d` and awaits native execution.
Current source adds established-connection TCP ownership checks before local
HTTP credentials, retained process identity and replacement-port refusal. Syntax
checks pass; new real-Windows HTTP assertions are pending. DSH/voice profile
adapters, the complete coordinator and installer application remain open.

The actual prompt/memory participant assertions at `6531e2d` now pass both fast
Windows jobs in [36379716570](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36379716570).
Current source connects the observed HTTP transport to the private managed DSH
profile, verifying the service anchor, product version and home identity. The
full DSH maintenance/restart proof now uses this client and checks its retained
process exits with the complete Job. These new HTTP/DSH assertions await native
execution; owned voice startup/provisioning and global coordination remain open.

At `f08c4f0`, both [fast Windows jobs](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36380441839)
pass the actual TCP-peer/credential-refusal/reused-port tests. Its full owned-DSH
integration is running. Full runtime `3a379a2` now passes both CPUs in
[36379432589](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36379432589).
Linux and Mac regressions pass at `6531e2d`, including the corrected Chromium
proof. Current installer qualification adds gate transfer into Inno's actual
extracted Setup process and checks retention across coordinator exit/crash.
Native execution of this new Inno case is pending; production handoff identity,
coordinated apply, health and rollback remain open.

At `0ca8348`, the actual extracted Inno Setup gate-transfer proof passes both
CPUs in [36380756992](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36380756992),
including normal coordinator exit/crash and invalid-transfer refusal before
version change. Both fast Windows jobs and Linux/Mac workflows also pass. At
`f08c4f0`, full x64 managed DSH integration passes; ARM64 is still running.

Current source adds [coordinated reversible preparation](LIFECYCLE.md#coordinated-reversible-preparation)
with independent renewals, conservative expiry, single cancellation after lost
acknowledgments, and startup exclusion retained through cleanup. Six reservation,
two graph failure and four admission checks pass locally; six portable owner
checks pass with two Windows-only cases skipped. Actual companion group and
assembled desktop/DSH graph assertions are added and await hosted execution.
This is preparation/cancellation only: no product commit, installer apply,
voice provisioning, rollback or release gate is waived.

At `f08c4f0`, [full native runtime](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36380441902)
now passes both CPUs, including managed DSH's observed HTTP participant and
normal shutdown/history restart. At `2ce8d32`, [both fast Windows jobs](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36381768755)
pass real prompt/memory group preparation, renewal, startup exclusion and
cancellation. The assembled desktop/DSH graph additions await the full run.

Current source adds a non-killing installer observation Job, suspended assignment
and read-only artifact binding to the verified digest. The real Inno handoff
fixture now launches through this adapter and verifies extracted-Setup ownership,
wrong digest/unrelated PID refusal and retained gate across normal exit/crash.
Syntax checks pass; native execution is pending. This is not yet authenticated
installer IPC or a complete update transaction.

## Baseline and environments (W0)

Implementation branch `feat/windows` starts from reviewed `main` `b8e36a4` plus
the planning commit `8565172`. Product 0.2.12, DSH 0.1.5-rc.1, Pi 0.85.1,
schema 1 and the current protocol versions remain unchanged. Unrelated open
source work and existing Linux/Mac installations are preserved. Reconcile new
reviewed changes before release; do not copy unreviewed local overlays.

The unchanged baseline passes TypeScript check/build, 182 Node tests and 538
native tests (three skips) in isolated Python 3.12.13 / PySide 6.8.2.1.
The initial system-Python attempt lacked QtTest; that was an environment failure,
not waived tests or a product regression.

| Environment | Availability/evidence | Boundary |
| --- | --- | --- |
| Linux x64 development | Available; baseline suites pass | Existing personal processes untouched |
| macOS ARM64 | Existing Mac 14/26 CI and authorized network Macs | Candidate dependency upgrade still needs testing |
| Windows x64 | `windows-2025` runtime, installer fixture and kernel probes executed | Server runner is build/runtime evidence, not Windows 11 client acceptance |
| Windows ARM64 | Native `windows-11-arm` runtime, installer fixture and kernel probes executed | Native-process readback passes; no RTX hardware claim |
| Physical Windows | Owner will connect a machine later | DPI, graphics, input, microphone and client installer tests remain pending |
| RTX Spark N1X | No accessible hardware verified | Hardware qualification remains required |
| Signing/publisher | No repository signing secrets or self-hosted runners found | Certificate/identity and browser-store publication remain external gates |

No account credential values were read or copied. Hosted qualification runs have
read-only repository permission and receive no signing or personal-model secrets.

## Runtime candidates (W1)

`release/windows/runtime.json` and architecture-specific hashed requirements lock
the candidates. They are explicitly **unqualified until execution passes**.
Python 3.13.15 is selected for both Windows targets because the inspected standalone
Python 3.12.13 distribution lacks Windows ARM64. Qt/PySide 6.11.2, sounddevice
0.5.6 and PyYAML 6.0.3 supply native ARM wheels missing from the previous pins.
Keep the other pinned native/voice dependencies unless a concrete failure requires
a change. No current Linux/Mac runtime pin is silently upgraded.

The staging tool downloads and verifies exact Python, Node 24.19.0 and PowerShell
7.6.6 archives, installs only hashed binary Python packages and checks dependencies.
The runtime probe requires native execution, imports actual Qt/NumPy/ONNX/PortAudio,
renders a Qt widget, launches private Node/PowerShell and inspects Python PE machine
types. DSH staging uses its existing lock and reviewed preparation script, with
real FFI, search, shell, termination and terminal tests. This does not prove an
installed Augmentor conversation or physical device behavior.

Velopack 1.2.158 was the initial, subsequently rejected candidate. The native launcher embeds
private Python without PATH-based DLL resolution. Compilation, two-version
installation/update/removal, busy-work coordination, independent recovery and
publisher trust still require their own proofs; runtime imports cannot select
the installer on their behalf.

## Feature and gate ledger

Each row retains the shared product requirements. Fixture evidence, actual
providers, installed artifacts and physical hardware must remain distinguishable.

| Work | Current state | Required next evidence |
| --- | --- | --- |
| W0 baseline | Shared baseline and native hosted evidence recorded | Current-main reconciliation and client/hardware environments |
| W1 native runtime and installer | Native runtimes pass; Inno/WinSparkle selected after both-CPU replacement feasibility | Full product coordination/rollback, clean-client install and publisher trust; [decision](WINDOWS-INSTALLER-DECISION.md) |
| W2 paths, ownership, IPC, locks | Both CPUs pass kernel adapters, cross-user ACL denial and Python/Node prompt transport | Complete component ownership and lifecycle integration |
| W3 managed DSH/model setup | Both CPUs pass assembled setup, compiled composer Send/Enter and history restart against deterministic DSH/model | Full first-run UI, ordinary-user/live-provider acceptance |
| W4 desktop, two windows, shortcuts, tray | Both CPUs pass compiled preview zoom/drafts, native resources and source hotkey persistence | Installer startup hooks, tray/quit and physical interaction |
| W5 chosen Chromium/Comet companion | Native registration/discovery/preparation/chooser and compiled host protocol fixtures pass both CPUs | Installer anchor and real selected-browser conversation |
| W6 computer control | Pending | Consented capture/input, Stop and Windows privilege boundaries |
| W6 voice/memory/Home/Pi | Pending | Existing feature contracts and configured-engine connectivity |
| W6 RTX inference | Pending hardware | Native compatible backend, measured shared-memory behavior |
| W7 signed install/repair/removal | Pending | Clean ordinary user, one identity, preserved persistent data |
| W8 coordinated weekly updates | Pending | Real N→N+1, busy/draft/settings protection, recovery across OS backends |
| W9 full artifact qualification | Pending | Exact candidate plus physical Windows and separately RTX evidence |
| W10 publication and guides | Pending | Signed public artifacts, anonymous website download, installed update |

G1–G5 remain open. Continue work while physical hardware is unavailable; do not
mark the overall implementation complete based on build or fixture success.

## First native execution, September 28

GitHub run `36353583238` at `f3f6de6` executed native x64 and ARM64, loaded the
actual Qt/NumPy/ONNX/PortAudio/Velopack modules, rendered the widget and launched
private Node and PowerShell. Both correctly failed the subsequent strict PE
inventory: sounddevice includes unused x86 audio DLLs in its x64 wheel, and
PySide6's ARM64 wheel includes an unused ARM32 `vccorlib140.dll`. The staging
policy now excludes only reviewed, individually hashed foreign DLLs and retains
the strict inventory check. The corrected run remains pending. Earlier successful
imports alone do not establish that the complete candidate passed.

Separately, candidate Qt/PySide 6.11.2 passes the same 538 Linux native tests
(three skips), preserving existing behavior under this library upgrade. Mac
candidate GUI checks and native two-version installer fixtures are added to CI.

At `89ae133`, the complete x64 runtime probe passes. ARM64 also needs the
individually hashed Shiboken copy of the unused ARM32 runtime excluded. The
shared Windows build exposed CRLF conversion breaking shader provenance hashes;
`.gitattributes` now preserves source bytes across checkouts. Installer compilation
exposed `cmd.exe` quoting in the build harness, corrected without changing client
execution. Mac candidate UI checks passed, but the job ended on a nonexistent
test filename; that test selection is corrected, not treated as a passing job.

The first W2 primitive is a shared/exclusive process lease adapter. Three real
separate-process Linux tests prove shared readers, exclusive maintenance and
kernel release on abnormal process exit. Windows runs the same tests next.
It is not yet wired into product services and does not claim compatibility with
DSH's separate file-lock protocol. Secure paths and transport remain pending.

The next isolated W2 adapter uses pinned pywin32 312 native wheels for Windows
token identity and ACLs. It creates persistent folders under the OS Local AppData
known folder with a protected current-user/SYSTEM allow-list, refuses permissive
existing directories without changing their permissions, and rejects junctions
and other reparse ancestors. Windows tests exercise owner/ACL readback, reopen,
permissive-path refusal and junction redirection. It is not yet adopted by the
application launcher; execution evidence is pending. This adds no global Python
installation and makes no changes to the owner's machine.

At `523fe9a`, run `36354229667` proves the native runtime on both architectures,
the selected Mac Qt behavior tests, and x64 process leases. The **x64 disposable
installer lifecycle passes**: native embedded launch from a Unicode/space path,
install hooks, local feed download, reopen with auto-apply disabled, refusal while
a fixture process is busy, update/reopen, retention of the previous package,
uninstall hooks/native-host registry cleanup and preserved settings. This remains
an unsigned installer-mechanism proof, not full-app or authenticated rollback
qualification. Reports are retained as the run's `windows-evidence-x64` artifact.

The same run finds a Windows ANSI decoding failure while inspecting a DSH npm
manifest. Package metadata now explicitly uses UTF-8; generated design assets
use UTF-8/LF on every OS. Windows build Python runs in explicit UTF-8 mode, and
the native launcher sets isolated Python preconfiguration to UTF-8 before startup
and supplies that mode to ordinary child services. The installer fixture checks
the actual interpreter flag. ARM64 DSH/installer work from this run is still in
progress; a new source revision must not erase the outstanding evidence boundary.

W2 import refactoring now routes Augmentor-owned branch journals, Home pairing,
Pi startup and lifecycle leases through the shared lock adapter. POSIX behavior
still delegates directly to `flock`; no third-party DSH history lock has been
substituted. The complete Linux native suite passes after these import changes
(544 tests, six platform/environment skips). Windows now runs the shared live
zoom, activity and window interaction tests as well as its platform probes;
actual Windows rendering/interaction results remain pending for that source.

The ARM64 installer proof at `523fe9a` also completes successfully, including
all lifecycle assertions above. Both native architectures therefore have evidence
for the selected installer mechanism; G1 still requires the complete DSH payload
and remaining clean-machine/trust checks. The first private-path probe at
`52964ae` finds that pywin32 token handles do not implement Python context
managers; token ownership now uses explicit `finally: Close()` and tests actual
process-token identity. The fixture does not mask failed ACL checks. Independent
DSH and UI probes now continue after an unrelated probe failure to collect useful
evidence; the overall job still fails if any required probe fails.

The isolated Python named-pipe adapter is now implemented for W2 qualification.
It preserves byte-stream framing, restricts the server ACL to user/SYSTEM,
rejects remote clients and pre-created names, and checks both peers through
kernel pipe process IDs and process-token SIDs. Overlapped operations have
timeouts/cancellation; the listening name stays owned between accepts. Tests
exercise repeated connections, clients disappearing before a request, large
Unicode responses, occupied-name refusal, reuse after close and read cancellation.
The adapter is not yet wired into application services. Native execution,
different-user rejection and authenticated Node interoperability remain pending;
do not infer these from the source or from Linux-skipped tests.

At `d13f504`, actual Windows x64 shared zoom/flare/window interaction tests and
desktop preview rendering pass. Native pipe probes expose three incorrect API
binding assumptions: file access constants belong to `ntsecuritycon`, the pipe
identification flag belongs to `win32file`, and pywin32 312 does not export
`CancelIoEx`. The correction uses the published bindings and an explicit kernel
binding for cross-thread cancellation, waiting for pending reads/writes before
freeing their handles. Separate-process framing and close-during-read tests are
added; their native execution remains pending.

DSH staging reaches its license inventory and correctly rejects missing Windows
entries. The four locked x64/ARM64 Sharp/Koffi npm archives were fetched and
verified against lockfile integrity. Exact Windows Koffi 3.2.1 binaries use the
existing matching MIT notice. Sharp 0.35.4 declares **Apache-2.0 AND
LGPL-3.0-or-later**; the inventory now retains that combined expression, the
Apache text, the LGPL supplement and the upstream native-library attribution
table. It does not select away LGPL obligations or mark the distribution review
complete. Corresponding source/replacement evidence remains a W7 release gate.
Six license-inventory tests pass, including missing supplemental-notice refusal.

At `74c7db5`, both real Windows architectures pass the private-directory and
named-pipe kernel probes, including a separate-process peer, large Unicode
responses, read timeout recovery and close waking a blocked reader. DSH payload
qualification still fails on x64 and is being investigated; no full green Windows
job or working installed application is claimed.

Shared prompt/memory servers and native clients now use the OS transport adapter.
Unix retains sockets; Windows uses the authenticated named pipe. Node clients
use the same Python pipe implementation through private inherited binary stdio,
avoiding undocumented Node handle access or an unauthenticated network listener.
Only a connection failure proven to precede sending may trigger service startup;
later failures never replay an action. Windows installed components also gain
private per-user lifetime leases and known-folder runtime paths. Pi's Node server
and the full Windows supervisor remain pending.

The real shared prompt integration test starts two competing daemon processes,
proves one owner, saves Unicode from native Python and Node, checks idempotent
acknowledgments, and verifies persistence after restart. It passes on Linux;
native Windows execution of these adopted services is queued next. Shared
TypeScript checks/build and all 182 Node tests pass. The preceding complete
Linux native suite passes 550 tests (11 platform/environment skips); later new
private-lease and integrated-service tests retain their own execution boundary.

The adopted transport revision `4c8717e` passes all 182 Node and 552 native Linux
tests (12 platform/environment skips), including real Python/Node service saves
and restart. Native Windows service execution remains pending.

The `74c7db5` x64 DSH log narrows its failure: FFI, ripgrep, PowerShell pipeline,
ordinary process termination and ConPTY round-trip all finish, but Node does not
exit after disposal and the outer 90-second deadline expires. The probe now
requires natural shutdown and reports remaining resource types on failure.
Upstream node-pty issues [887](https://github.com/microsoft/node-pty/issues/887),
[947](https://github.com/microsoft/node-pty/issues/947) and
[965](https://github.com/microsoft/node-pty/issues/965) describe relevant worker,
pipe and pseudoconsole leaks; the locked 1.2.0-beta.15 source is being inspected.
Do not paper over this with a successful forced process exit.

Visual inspection of the hosted offscreen screenshot also finds missing-font
boxes despite passing widget interaction assertions. That screenshot is not
visual acceptance. A separate probe now uses the actual Windows Qt platform
plugin, verifies font/glyph availability and captures the shared preview. Real
Windows-QPA output and physical display/DPI acceptance remain distinct gates.

The in-progress `d9e4c3a` x64 job passes private installation-lease tests, the real
Python/Node shared prompt test and the actual Windows Qt font/render probe.
ARM64 shared-service execution is still pending its build. The earlier offscreen
boxes are not observed by the Windows-QPA font assertions; retain and inspect
the native screenshot before claiming visual acceptance.

The next DSH candidate applies two Windows-only, exact-source-hash preparations:
the supported node-pty `useConptyDll` option selects its already locked Microsoft
ConPTY DLL; when terminal output closes, its paired input socket and output worker
are disposed. The bundled DLL uses Microsoft's release protocol rather than the
inbox path identified by upstream issue 965. Originals and prepared hashes are
recorded in `payload.json`, original MIT attribution is retained, and any upstream
drift fails before either source file changes. No Mac/Linux dependency source is
patched. Four sequential terminal dialogues now check native resource counts,
absence of child console hosts and natural process exit. This remains a candidate
fix until those native tests pass; public packaging and full source/license
review remain open.

The retained `d9e4c3a` x64 screenshot was visually inspected: actual Windows QPA
renders readable labels and controls using the platform's Tahoma fallback. Its
font report and screenshot are in `windows-evidence-x64`; offscreen output is
not substituted for that evidence. The uncorrected terminal's shutdown report
shows an extra `MessagePort` and pipe after disposal, consistent with the source
worker/input lifecycle defect. The prepared correction still awaits execution.

An isolated W2 process-owner adapter now creates an unnamed Windows Job with
kill-on-close semantics. A small isolated Python worker enters that Job before
starting any workload; only the supervisor retains its handle. This prevents a
fast target from escaping containment before assignment, and supports cleanup
after a supervisor crash. The native fixture starts a detached grandchild,
captures its actual process handle, crashes only its disposable owner and checks
kernel-signaled exit of both descendants. Execution and adoption into managed
DSH remain pending. This mechanism never replaces busy-work checks before normal
updates or user-directed shutdown.

Both architectures complete the `d9e4c3a` shared-service, private-path and actual
Windows-QPA rendering probes. The unpatched terminal leak is identical on ARM64;
the complete job fails for that reason. Keep the ongoing prepared-terminal run's
separate outcome authoritative. The first supervisor-crash fixture at `d3071c1`
fails and needs diagnosis before process containment can be considered qualified;
the fixture now retains bounded helper error output instead of only a missing
PID-file assertion.

First-run preparation now adds shared DSH discovery that understands Windows npm
shims without executing them, Windows owner checks, native PowerShell tool
selection, and explicit private-runtime paths. Dependency links use ordinary
Unix symlinks or Windows junctions without an administrator/Developer Mode
requirement; cleanup and conflicting-target tests preserve the dependency itself.
The common temporary-DSH bootstrap uses the owned-process adapter, retaining its
Unix session behavior and enabling Windows containment once that adapter passes.
These pieces do not constitute a completed Windows setup wizard/supervisor. The
29 existing/new setup tests and two actual directory-link tests pass on Linux;
native link and complete Mac bootstrap regressions are still required.

The complete Linux native suite with first-run preparations passes 558 tests
(13 platform/environment skips). At `d3071c1`, x64 performs all four terminal
dialogues and releases its worker, but the resource-count assertion reports two
pipes. The probe initialized its stdout/stderr after taking the baseline, so
those diagnostic streams were incorrectly counted as new terminal resources.
The probe now initializes both streams before comparison; it still requires
natural Node exit and independently checks for surviving console hosts. Native
rerun is required, and the supervisor failure still awaits its retained traceback.

The Mac first-run transaction now lives in `services/dsh/managed.py`, with service
ownership supplied by the OS entrypoint. Mac preserves LaunchAgent registration
and its external entrypoint/test seams; Windows will supply the per-user supervisor.
Both use one model-validation, readiness, retry and connection-save sequence.
Private JSON records validate opened regular/single-link files; Windows creates
protected current-user/SYSTEM ACLs, while Unix retains private modes. Atomic
replacement preserves an existing record if serialization fails.

The extraction passes all 565 local native tests (13 platform/environment skips),
including all 17 existing managed-Mac regressions and new common private-file and
setup fixtures. Native Windows and complete Mac artifact checks remain required.
At `635d0a9`, x64's prepared DSH payload now passes all four terminal dialogues,
resource release, absence of console hosts, and natural shutdown. The same run
finds separate directory-link, process-owner and DSH-setup test failures; these
are not treated as a green Windows job or working installed application.

Retained `635d0a9` x64 diagnostics identify those failures precisely: directory
linking and CLI discovery work, but two assertions compare a resolved long path
with Windows' short `RUNNER~1` temporary path. Their expected paths now resolve
through the filesystem as well. The process-owner failure is a real binding
problem: pywin32 312 rejects `None` as the Job name. The adapter now uses typed
`CreateJobObjectW` with a null name for a genuinely unnamed Job, retaining the
kernel handle directly and closing it explicitly. Containment still requires
the subsequent native crash test; a source correction alone does not prove it.

At `89e8a84`, the real supervisor-crash/descendant containment probe passes on
both x64 and ARM64. A new private-file probe still fails and is being diagnosed;
do not treat the full Windows job as green.

The Windows managed owner now uses one exclusive per-user supervisor and the
authenticated local transport. Its fixed component commands can start the
bundled DSH, report state and clean up an unpublished failed setup. They cannot
execute an arbitrary command, stop a selected profile through failed-setup
cleanup, or exit while a component is running. The process owner reaps completed
Jobs and retains the installation lease. This is initial DSH ownership: normal
Quit, shared update coordination, startup registration and bounded log rotation
remain separate unfinished work.

`setup-windows.py` uses the shared first-run transaction with this owner. New
native CI assembles a development application payload from shared sources and
locked production dependencies, then provisions actual DSH against an isolated
deterministic model, sends a conversation and checks history after an owned
supervisor crash/restart. The proof also rejects failed-setup cleanup once the
profile is selected. These are newly added checks awaiting execution, not a
working installed-app claim; real-provider, browser and physical UI tests remain.

The `89e8a84` private-file failures are exception-contract mismatches, not failed
ACL/content preservation: pywin32 emits its own non-`OSError` type for missing
and existing files. The adapter now maps kernel errors into Python's standard
filesystem exception family. The same x64 run passes shared managed-setup
fixtures, terminal cleanup and the installer mechanism; ARM64 is still running.

A full local rerun also exposed an existing browser-voice shutdown race: its
daemon stdin reader could emit a second Qt close signal during interpreter
teardown and abort the process. The shared reader now exits on the explicit
close frame, avoids Python buffered input locks and stops emitting once Qt quits.
A real-process regression repeats Close while the parent keeps stdin open;
all five focused browser-voice tests pass. This fix serves all three OSs and
does not change audio placement or the voice UI.

The resulting local regression run passes all 570 native tests (14 explicit
platform/environment skips). Supervisor, staged application and managed-chat
native probes still await the next Windows run. The existing Mac/Linux installed
applications remain untouched.

The pinned DSH JSONL backend uses `Local\\dsh-session-lock-<SHA256>` count-one
semaphores on Windows, derived from its lexically resolved lower-case lock path;
it does not use a Windows file lock. The reviewed published module hash is
`7d0640c9fc4be6c703b77605fdee6af519c542fae28a6cd4489353309812f062`.
The separate `dsh/session_lease.py` adapter matches that protocol and retains
Unix `flock`; application lifetime locks remain separate. Recovery imports and
private startup records are portable, and managed Windows restart routes to the
credential-preserving supervisor. External Windows DSH remains externally owned;
automatic spawning of that external service is not implemented.

The staged native conversation proof now adds an actual pending model turn,
requires our repair lease to be refused while DSH owns the history, tests Stop,
and checks lease release before restoring the conversation after owner exit.
This check is newly added and pending native execution. Local common tests pass
572 cases (14 platform/environment skips), including existing repair/backup
regressions and a separate-process lease/crash test. Mac CI now explicitly adds
these shared setup, private-file, voice and recovery suites. Both complete Mac
14/26 artifact workflows pass at the preceding `ae17cc3`; current additions still
require their own native runs.

At `ae17cc3`, x64 passes all native primitives, real supervisor arbitration,
private records, common setup fixtures, browser-voice shutdown and terminal
checks. Production dependencies assemble successfully, but actual DSH web
bootstrap exits and its log is empty. The process helper forwarded inheritable
handles without explicitly selecting its child's standard streams. It now
passes stdin/stdout/stderr explicitly (the Windows STARTF_USESTDHANDLES contract)
and gains a binary/Unicode round-trip test. The managed proof also checks the
actual DSH CLI version through that owned helper, and bootstrap failures include
the numeric exit code. This is a diagnosed logging gap and candidate startup
correction, not a claim that the full DSH bootstrap now works.

The generated candidate records its actual checked-out commit; PR jobs may use
GitHub's synthetic merge commit (x64 `ae17cc3` run records `6afaefc...`) rather than
the branch head. These are CI development payloads, not promoted release sources.
Both complete Mac artifact workflows and Linux/Home/Browser/installed-package
validation pass for `ae17cc3`; subsequent recovery/stdio changes need their own
results. The source remains on draft PR #20 and no installed user app changed.

Windows window activation now uses the existing Qt instance-command handler
through a small authenticated-pipe adapter. Its owner lock is a protected
Windows file lease, and commands are delivered to Qt's main thread. Other OSs
retain their current Qt transport. Repeat Windows application launches request
Show, and independent named windows retain separate endpoints. Shutdown closes
the listener and owner lease; update busy/draft decisions remain shared.

The new native probes test thread affinity, binary framing/Unicode, immediate
client close, exclusive ownership, two actual Windows-QPA preview windows,
duplicate launch, per-window drafts, busy maintenance refusal and live zoom.
They are awaiting execution and do not claim normal product Quit, installed
launchers, global shortcuts, hardware rendering or live chat. Local regressions
pass 574 tests (16 explicit platform/environment skips). ARM64 completes the
preceding `ae17cc3` primitive/terminal/supervisor checks, but its real DSH setup
fails with the same empty startup log as x64; the stdio correction has its own
ongoing run.

## Shared first-run UI and Windows voice configuration (September 28)

At `6475a9f`, both native Windows jobs pass explicit binary stdio forwarding and
DSH CLI version readback. The actual DSH startup log now identifies the blocker:
Resonant Voice 0.1.16 tests Unix permission bits on Windows and rejects its token.
No permission check is bypassed. The separately maintained voice candidate
0.1.17 (`aae6a51`, [dependency PR #2](https://github.com/ManoloRemiddi/resonant-voice/pull/2))
adds native protected user/SYSTEM ACL creation and opened-file validation. Its
four native configuration checks pass on x64 and ARM64 at code ref `22fd869`
([run 36360561703](https://github.com/ManoloRemiddi/resonant-voice/actions/runs/36360561703));
36 Node tests pass on Linux, with two Windows-only skips. The common DSH lock and
complete Linux assembly now select that same versioned archive. Application DSH
setup/conversation qualification is still pending; this is not audio/GPU proof.

The approved first-run interface is now `managed_setup.py`, shared by Windows and
Mac. Payload diagnosis and the setup-worker/service-owner selection are platform
adapters. Windows presents the existing two-step runtime/model flow, preserves
external DSH ownership, and sends credentials over UTF-8 stdin without a console.
No additional UI layout is introduced. Linux's existing external-runtime path is
unchanged. The local native suite passes 576 tests (16 Windows/environment skips).

The first Windows recovery suite exposed administrator-owned test files on the
hosted runner. Synthetic histories now explicitly use the per-user security
descriptor; production owner checks remain strict. Reparse refusal is translated
into the common recovery error instead of leaking an adapter exception. All 24
recovery tests pass locally; native recovery rerun remains required. Existing
Linux/Mac apps, personal speech/model configuration and downloads are unchanged.

Recovery backups, their manifests and temporary replacement histories now receive
private ACLs and explicit ownership at creation. `copy2` plus `chmod` was
insufficient on Windows, especially under an elevated test runner. A temporary
private directory on the history volume preserves atomic replacement across
separate configuration/data volumes. The 24 recovery tests pass after this
change; native tests remain the gate for the Windows filesystem behavior.

At `ae982ce`, the new two-window Windows preview probe times out awaiting its
first instance response; direct pipe/Qt dispatch unit tests and simple native
font/rendering still pass. Linux and Mac full artifact CI also pass at that ref.
The proof now preserves the actual command error and child exit codes instead
of collapsing all failures into a timeout. Its shared command sequence passes a
separate local Linux run (two processes, draft maintenance refusal, duplicate
launch and live 120% zoom). That is not Windows evidence. Windows desktop checks
now have their own native x64/ARM64 workflow so UI diagnostics do not wait for
DSH dependency assembly and installer qualification to finish.

The independent desktop check at `166fd2c` confirms both preview processes stay
alive and authenticated pipe connection succeeds, but response reading times
out. It is not an exited child or a missing endpoint. The next fixture launch
records bounded thread stacks for this stalled command path; normal product
launches do not enable that diagnostic timer.

The stalled UI thread capture at `e9467ff` shows the main Qt event loop running
while the pipe worker waits for GUI completion. The adapter now crosses threads
through an explicit queued QObject slot, then emits the common handler callback
on the GUI thread. The focused test uses a real `app.exec()` loop rather than
manual event pumping. Native execution remains required to confirm the fix.
Owned-process construction also closes its Job if limit/handle configuration
fails; a native failure-injection test checks that repeated failures leak no
kernel handles and launch no workload.

## Native desktop control and first assembled DSH success

At `79d9efc`, [Windows desktop run 36361445729](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36361445729)
passes on x64 and ARM64. The actual Windows-QPA preview test verifies separate
window PIDs/drafts, repeat-launch ownership, busy-draft maintenance refusal,
and immediate 120% zoom (font 13→16 pixels, send button 24→29). The x64 captured
image was inspected and its text/icons are readable. This is source-preview
control evidence, not an installed binary, physical input or GPU acceptance.

The x64 job of [runtime run 36361250959](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36361250959)
passes at branch head `e9467ff`. Its assembled payload records actual GitHub merge
checkout `6f0f975477622c836bd97aa3d24f637a357a28bc`. Actual bundled DSH starts with
the 0.1.17 voice candidate, completes first-run setup and answers the deterministic
model. The real harness writer excludes recovery via its Windows semaphore;
Stop cancels an active turn; an owned supervisor crash/restart preserves history;
failed-setup cleanup refuses to stop a selected runtime. Four fixture provider
requests were used, no personal provider secret. All 24 recovery checks and the
remaining x64 runtime/installer probes pass. ARM64 full-runtime execution is
still in progress. Startup diagnostics now distinguish a recovered transient
check failure from a current error.

The next source adds the actual embedded `Augmentor.exe` desktop entrypoint:
private bundled runtimes, architecture/payload preflight, stable AppUserModelID,
per-window private diagnostic logs and the shared native UI. The shared C build
routine also continues to build the disposable installer fixture. Assembly now
compiles the product executable, and the two-window probe can invoke it directly
while checking that the GUI remains in that executable's process. Disposable-data
redirection is allowed only by a development-candidate manifest. These binary
launch checks are not yet executed. Full installer hooks, login registration,
tray/hotkeys, safe Quit/update coordination, browser setup and hardware tests
remain subsequent gates; the new entrypoint is not a customer release.

The source suite after the launcher additions passes 580 tests (17 platform skips).
Three launcher checks cover wrong architecture, missing payload, refusal of
customer data-path overrides and selection of private bundled tools.

The kernel privacy suite now also includes a real different-user token probe,
opted in only on the disposable hosted Windows runners. It creates a temporary
ordinary local identity, authenticates it with a non-cached network logon token,
impersonates that token for file/pipe open attempts, requires access-denied, then
reverts and deletes the account. Normal developer/customer test runs skip this
account-creation fixture. This probes actual ACL denial, not a separately logged
in desktop process; the latter remains a broader multi-user acceptance check.
Native results are pending. References:
[LogonUserW](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-logonuserw)
and [NetUserAdd](https://learn.microsoft.com/en-us/windows/win32/api/lmaccess/nf-lmaccess-netuseradd).

## Windows shortcut owner and compiled-desktop qualification

The complete `e9467ff` [runtime run 36361250959](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36361250959)
now passes on **both** native CPUs, superseding the ARM64-pending entry above.
At `6cac5e5`, [run 36362155338](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36362155338)
passes x64 native compilation, DSH conversation/restart, cross-user file/pipe
denial and installer fixtures. The compiled `Augmentor.exe` starts both preview
windows, but its zoom assertion fails; the older proof discarded the actual
response. The next proof retains initial state and the complete zoom result.
This is an unresolved packaged-desktop gate, not a successful binary launch proof.
The independent source desktop, Mac artifact and Linux/shared validation workflows
pass at `6cac5e5`; ARM64 full-runtime execution remains ongoing at this checkpoint.

The next source adds the [Windows shortcut owner](WINDOWS-SHELL.md). Two native
registrations live in the existing supervisor's Qt thread, and the shared Settings
surface routes Windows reads/saves to that owner. Registration and private-file
save rollback preserve the old choice on failure. The common activation helper
uses Windows authenticated pipes/native cold launch and retains Linux/Mac behavior.
The source preview proof also verifies independent hide/show activation. Local
mapping, Qt dispatch and all 14 shared shortcut checks pass; native hotkey and
supervisor integration runs remain pending. No installed personal app, Windows
customer package or public download changed.

The complete local Python suite after this addition passes 584 tests with 19
explicit platform/environment skips. Windows registration itself remains a native
CI gate; the skipped cases are not counted as Windows behavior evidence.

At `5c1ad26`, [desktop run 36363088603](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36363088603)
passes on both x64 and ARM64, including real `RegisterHotKey` collision rejection,
failed-save preservation, posted-message Qt dispatch, authenticated supervisor
settings changes and source two-window hide/show. Physical key presses, login,
tray and compiled-app rendering are still separate gates. The preceding
`6cac5e5` runtime run also completes ARM64 with the same compiled zoom failure;
all other runtime checks, including cross-user ACL denial, pass on both CPUs.

Inspection of the exact pinned PySide 6.11.2 wheel confirms it relies on PATH for
the SVG plugin's Qt DLL dependencies, while the native executable intentionally
excludes PATH from DLL search. The next launcher explicitly registers only its
bundled Python/Qt library directories and restricts Qt plugins to that payload.
This addresses an identified packaging gap; the native zoom rerun must still
confirm the original failure and the correction. The supervisor proof additionally
restarts the owner and checks restoration of both saved shortcuts.

At `475a3a2`, [desktop run 36363357087](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36363357087)
passes on both CPUs, including closing/restarting the actual background owner
and restoring both persisted bindings. The next product build adds native icon,
version and manifest resources without changing the approved artwork. All seven
generated PNG icon frames locally decode at their exact sizes with alpha;
native resource compilation/readback and physical shell/DPI appearance remain
pending. The disposable W1 installer fixture retains its separate identity.

Windows focus handoff now gives the existing desktop process the launch/hotkey
owner's foreground permission before Show/Toggle. It uses the server PID obtained
from the authenticated pipe, never a PID in application JSON. Windows may deny
the handoff; normal visibility control is retained without input injection.
Preview inspection records active-window state, but native API execution and
physical foreground behavior remain distinct qualification gates.

At `5c1ad26`, x64 compiled diagnostics confirm the Appearance failure is
`The Qt SVG image plugin is unavailable`, matching the explicit-library-path
correction already queued in `475a3a2` and later source. At `41ef486`, the fast
source desktop/shortcut checks pass on both CPUs including foreground-handoff
API execution; real foreground permission after physical input remains pending.

The next source adds an idempotent per-user login registration mechanism and
`Augmentor.exe --background`. The stable installer path is retained without
resolving it into a version folder; existing foreign entries and Windows startup
approval/disable records are preserved. No login registration is enabled by source
launches. Tests exercise a disposable HKCU key, not the real startup key; native
execution, installer wiring and actual login acceptance remain pending. Cold
Windows shortcut launch also names the target window explicitly so an inherited
secondary-window environment cannot change the first shortcut's destination.

The local Python regression suite through `0a1d086` passes 587 tests with 20
platform/environment skips. The next native runtime fixture launches compiled
`Augmentor.exe` against its already-provisioned isolated DSH/model, types through
Send, closes/reopens the same named window, submits with Enter and checks rendered
history and duplicate prevention. It verifies the GUI's process image and test
Job membership, retains captures and adds private desktop logs to failure reports.
The Job is fixture cleanup for that GUI and its children; it does not qualify
normal product-wide Quit. This new native chat sequence is not yet executed.

At `0a1d086`, the x64 job in [runtime run 36364000645](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36364000645)
now passes, including compiled preview zoom with the corrected private Qt DLL
directories and readback of the embedded icon/version/manifest. ARM64 remains
in progress. At `ade5be0`, both fast native desktop jobs and macOS feasibility
pass; the compiled real-DSH native chat proof remains queued.

The next source extends the existing supervisor with fixed prompt/memory companion
Jobs, repeat-start reuse and refusal to replace an externally owned endpoint.
Its new native test queries the actual services and verifies containment after
deliberately killing only its disposable supervisor. Client startup adoption and
native execution of this addition are pending; graceful Quit/update admission
control is explicitly not implemented by a Job kill.

At `840127f`, [desktop run 36364832529](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36364832529)
passes on both CPUs, including real prompt/memory identity, repeat startup and
kernel-observed process exit after an isolated owner fault. The next source adopts
that backend in both Python and Node prompt/memory clients. Unix startup behavior
is retained. Local TypeScript check/build and the real Unix shared-service and
sealed-bundle startup tests pass; native client-owned save/crash/restart execution
remains pending. Linux/shared and macOS workflows also pass at `ade5be0`.

The complete `0a1d086` [runtime run 36364000645](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36364000645)
now passes on both native CPUs, including the compiled Qt plugin correction,
two preview windows, zoom/drafts, embedded resources, DSH setup/history/Stop,
cross-user kernel probes and the disposable installer lifecycle. The later
compiled actual-composer proof is still executing; these results do not subsume it.

W5 source begins with a dedicated [Windows native browser executable](WINDOWS-BROWSER.md),
private diagnostics and binary framing through the shared Node bridge. A new
qualification sequence checks the real executable's handshake, Unicode prompt
storage, actual DSH history and disconnect ownership. Native execution, browser
registration, chosen-browser UI and installation are pending. Five local launcher
checks pass, including origin/argument refusal; syntax checks are not native
binary evidence. This work does not publish an extension or change any browser
profile. Client-adoption source `6c2a492` passes both fast Windows desktop jobs;
its full native Node/Python ownership test is still queued.

At `840127f`, x64 in [run 36364832602](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36364832602)
now passes the compiled native desktop's actual Send/Enter/reopen/history sequence
against bundled DSH and the deterministic fixture model. ARM64 is still running.
This adds actual controller/widget evidence, not physical input or a live provider.

The next W5 backend registers the native host in the ordinary user's standard
Chromium-compatible HKCU lookup locations. It retains a stable launcher path,
refuses foreign entries/changed manifests and rolls back partially written values.
Native tests isolate every write beneath unique fixture registry roots; execution
of the view/idempotence/conflict/rollback/removal tests is pending. Installer and
chosen-browser setup integration remain future steps, not implied by this API.

At `8df9049`, [desktop run 36365706210](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36365706210)
passes on both CPUs, including actual disposable-HKCU view/readback, idempotence,
foreign-value preservation, partial-write rollback and stable-junction tests.
The next backend adds read-only registered-browser discovery plus static inspection
of any user-selected Chromium executable. It uses Windows command parsing and
product metadata, permits renamed/versioned resources and executes no discovered
command. Native discovery fixtures and actual-browser acceptance are pending.

The first discovery run (`36366023065`) reaches real Windows argument parsing and
PE/resource inspection on both CPUs, then fails a fixture expectation comparing
the runner's short `RUNNER~1` temp path with its resolved long spelling. The
expectation now compares resolved paths; product normalization is retained.
The registration safety tests still pass. Full discovery execution must rerun.

At `13c6c0d`, [desktop run 36366164943](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36366164943)
passes both CPUs including the corrected real Windows discovery fixture. At
`840127f`, the full [runtime run 36364832602](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36364832602)
now passes both CPUs, including actual compiled desktop Send/Enter/reopen/history
against the bundled DSH and deterministic model. At `13c6c0d`, x64 in
[runtime run 36366164798](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36366164798)
also passes the new actual native-browser-host binary/protocol sequence and
Python/Node companion ownership/restart checks. ARM64 is still running. macOS
feasibility passes at this ref; the shared Linux installed checks remain in progress.

A separate pinned-source review finds the stock Velopack EXE terminates active
package processes before its non-vetoing uninstall hook. W1 is reopened for this
failed requirement; see the [installer decision](WINDOWS-INSTALLER-DECISION.md).
An additional isolated native probe now characterizes busy uninstall explicitly;
its execution is pending. No customer package, browser profile or website changed.

The complete `13c6c0d` runtime run now passes on both x64 and ARM64, including
actual compiled browser host framing/handshake/prompts/DSH-history/disconnect
and real Python/Node client adoption of the owned prompt/memory services. Shared
Linux validation and macOS feasibility also finish successfully at that ref.
Actual browser UI/store installation and physical hardware remain pending.

A separate native installer-candidate workflow now exercises pinned Inno 7.1.0
and native WinSparkle 0.9.4. It covers repair/update/removal admission with two
live fixture processes, failed preparation/retry and signed-download refusal
cases. Source syntax and diff checks pass; native execution is pending. The
product packaging backend has not switched based on source alone.

W5 now shares the approved Mac chooser/instruction form with a Windows adapter.
Windows preparation requires an installer-owned stable HKCU anchor, keeps the
extension in content-addressed private data and refuses source registrations or
edited prepared files. Installer anchor writing and actual-browser tests remain
pending. All five local chooser tests, 16 Mac browser checks and 28 common window
checks pass. The new real-Windows preparation fixture is queued for native CI.

At `742bfb0`, both native desktop jobs pass the private extension staging fix and
complete preparation fixture. The alternative installer run at `85cfbd7` also
passes both CPUs, actual merge checkout `c8c01d3a00e2267b342f408ade15d7152cfc0a2e`.
Inno/WinSparkle are now the selected implementation backend, with full product,
signing/rollback and client-machine gates retained in the installer decision.

The shared prompt companion now has reversible maintenance admission and normal
acknowledged shutdown. Accepted requests refuse preparation; prepared components
reject new requests before execution. Four concurrency/expiry tests, a real
Linux prompt-service long-poll/refusal/cancel/shutdown/restart proof and 19 shared
prompt checks pass. Native RPC execution is pending. This does not yet coordinate
memory processing, DSH, voice, browser, desktops or their automatic restarts;
those remain required before any global Quit/update can use it.

The automatic-memory companion now adopts that same admission protocol for its
RPC requests, background step and memory gateway. Existing inference/settlement
refuses maintenance, preparation blocks new inference, and cancellation preserves
the user's saved processing-pause preference. Local real-service shutdown/restart
preserves journal data and that preference; all eight budget/gateway checks pass.
The test waits for durable gateway cleanup after its HTTP response, rather than
mistaking received bytes for completed work. New native memory/gateway checks are
added to the fast desktop workflow; full global coordination remains pending.

At `4f2f763`, [full runtime run 36368605593](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36368605593)
passes both native CPUs and the shared Mac Qt candidate. This includes the new
prompt/memory maintenance RPCs and the browser staging ACL correction. Fast
desktop and installer feasibility also pass at that ref. The preceding `85cfbd7`
run had the already-fixed staging ACL error, a Mac test that assumed fixed
animation timing, and one Windows startup-inspection timeout. The animation
test now waits for actual completion with a bound. The shared window handler
also drains requests queued during construction before its callback connected;
this addresses a concrete startup notification race. Latest full runtime success
predates that source correction and the following DSH changes.

DSH now implements [reversible admission and normal shutdown](LIFECYCLE.md#dsh-admission-and-normal-shutdown)
over its authenticated product endpoint. Five real SDK tests and actual local
DSH HTTP/CLI execution pass, including Node `beforeExit`, so forced exit is not
misreported as natural shutdown. The work also fixes shared plugin cleanup to
use the actual Cordis effect lifecycle. Native SDK, busy-model refusal and
natural-exit/restart checks are added to Windows qualification and remain pending.
Voice/browser/desktop participation and the global coordinator are still required.

At `795a72b`, shared Linux validation, macOS feasibility, both fast Windows
desktop jobs and both Inno/WinSparkle candidate jobs pass. Full Windows runtime
[run 36370115270](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36370115270)
passes the actual pinned SDK admission tests but fails the new managed DSH proof
on both CPUs: the product token was created with the elevated token's group
owner, which the strict file validator correctly refuses. Source now creates
and reads the token through explicit private kernel descriptors, preserving an
external home's ACL and refusing replacement/links. New native execution remains
pending. Fixture cleanup also retains the replacement supervisor's exact process
handle and preserves the primary failure if its still-live companions refuse exit.

Shared desktop source now implements reversible maintenance reservation, blocks
input and reconnection while prepared, counts queued/background work and closes
normally after commit. Four new Qt tests, affected controller/queue/window/voice
regressions and a real two-process Linux preview proof pass. The latter verifies
the other window's draft survives, cancelled input works again and a committed
preview exits zero. The compiled Windows chat proof now requests the same
prepare/commit path; native execution is pending. Voice/browser participation,
global coordination and full installer integration remain required.

At `187bee6`, fast desktop, installer feasibility, Linux and macOS workflows all
pass. The native x64 full run reaches a second token creator in the complete
bootstrap path before the checked installer; it still used ordinary file output.
Source now routes both creators through the same protected-token helper. A new
bootstrap retry test verifies the real resulting token's descriptor and unchanged
identity after failed startup, and runs in fast Windows qualification. The actual
compiled DSH setup/admission/exit path must pass again before this fix is qualified.

The shared dependency graph now selects Resonant Voice **0.1.18**, exact source
`7a6645e`, retaining one speech package across all OSs. Both native CPUs pass its
private configuration and five real HTTP/WebSocket/CLI maintenance tests in
[run 36371851225](https://github.com/ManoloRemiddi/resonant-voice/actions/runs/36371851225).
The separate companion now reserves admission, refuses open voice/issued tickets,
waits for accepted synthesis and actual ASR process closure, and commits an idle
natural exit observed through `beforeExit`. Local DSH SDK cleanup, eight Python
ASR fixture checks and the actual complete installer compose/restart proof pass.
No real provider, microphone, audio device, global coordinator or managed Windows
speech deployment is implied. External speech/model services are never adopted
for shutdown merely because they speak the same protocol.

The Windows owner now reserves startup, shortcut settings and activations using
the shared component protocol, without stopping live children. Commit refuses
until it is empty and acknowledges before normal exit. Portable owner/Qt tests
pass, including queued activations and work still executing after a lost settings
reply. Native supervisor handshake tests are added and pending. This is the
startup fence needed by global coordination; it is not global Quit or an update.

A further owner review finds that polling an exited leader previously closed its
Job, which could terminate surviving descendants before global idle checks.
The Windows owner now retains that range until its kernel active-process count
is zero. New starts reuse/preserve it, and committed shutdown remains refused.
The compiled desktop proof now waits for that whole range to drain naturally.
Portable supervisor tests pass; a real detached-child timeout/natural-exit test
is added to both native qualification paths and awaits execution.

At `e7228e5`, [full runtime run 36372119531](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36372119531)
passes native x64 and ARM64 plus the shared Mac Qt candidate. Both token creation
paths, the actual compiled desktop, real DSH admission/natural exit/restart and
the voice 0.1.18 bundle now pass that integration run. The hosted fixture uses
a deterministic model; it does not qualify an external provider or audio device.
At `303a619`, [fast desktop run 36372703256](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36372703256)
passes both CPUs, including the real native owner reservation and detached-child
graceful timeout/natural-exit regression. Full runtime for that ref is pending.

Current source adds [kernel-verified window discovery](WINDOWS-SHELL.md#window-discovery-for-maintenance).
The two-process portable proof passes; native source and compiled assertions are
added and await execution. The client preserves stale files, refuses unknown
builds/protocols and retains exact process observations without termination
rights. Global discovery still needs the browser and owned companions, and a
snapshot is not the startup fence or final exclusive installation lease.

At `dc41a56`, [fast desktop run 36373391019](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36373391019)
passes both native CPUs, including kernel-verified source-window discovery.
Its full compiled run remains pending. A startup audit also identified private
Python loading before the Python-level lifetime lock. New source moves native
application/browser exclusion ahead of that load and retains it through process
exit. New compiled probes cover actual exclusion, private path rejection and
normal release; their native execution is pending. This does not complete the
installer transaction or browser/companion coordination.

The `653adac` native launchers compile on x64 and pass the pre-Python byte-lock
refusal checks. Its new probe then fails because the test uses a pywin32 flag
from the wrong module. The probe now uses `win32file.FILE_FLAG_OPEN_REPARSE_POINT`,
matching the existing product adapter. Remaining native assertions must pass
before this startup work is qualified; this is not a waived integration failure.

Shared browser source now drains accepted parent-side operations on EOF and
observes its bridge's close without force-exiting the parent. Browser voice
retains actual worker and accepted ticket/submission activity after its UI closes;
the two-second force-kill timer is removed. Thirteen focused local Node/DOM
checks pass, including two real-process EOF/`beforeExit` cases and independent
voice worker/submission drain. Native compiled integration remains pending.
DSH/Pi bridge admission, extension panel/reconnect reservation and global
coordination still require implementation; these corrections do not complete
browser maintenance or speech engine qualification.

Full runtime `303a619` passes both native CPUs in
[run 36372703204](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36372703204).
At `bfde231`, [fast desktop run 36373865190](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36373865190)
passes both CPUs, including the compiled native early-startup lease tests. These
supersede their earlier pending entries while preserving the distinct full-app
early-lease integration gate.

Further browser source adds accepted-work draining to both DSH/Pi bridges,
disables DSH reconnect after EOF, waits for retiring voice workers and releases
the interaction presenter without deciding pending approvals. The Windows host
now waits for its complete Job to exit naturally. Four portable process cases
pass with explicit `beforeExit` observations; the new DSH bridge case is offline,
and real compiled Windows DSH/browser integration remains pending.

The combined local Node and Browser suite passes all **237** tests with the
actual pinned DSH SDK available and isolated user paths. This includes the new
bridge drain checks and existing auth, approvals, shared prompts, voice control,
browser actions and UI regressions. Windows wrapper qualification still depends
on the native compiled run; no installed browser was restarted.

At `6d245a7`, [full runtime run 36374006218](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36374006218)
passes both native CPUs and the shared Mac Qt candidate. This qualifies the
compiled early lifetime lease, window discovery and the included parent/voice
drain source, superseding those earlier pending entries. The subsequent
`264227a` DSH/Pi bridge drain passes both fast desktop and installer-candidate
jobs, plus Linux and Mac workflows; its full x64 job passes, ARM64 is pending.

The next source checkpoint adds reversible browser-worker/page reservation on
all OSs. Actual isolated Chromium, the real Pi bridge and native messaging
frames prove two chat documents plus Settings, draft/API-key refusal, cancel,
renew, new/closed-page invalidation and actual 30-second lost-reservation expiry.
The qualification-only framing proxy is separate from the product host.
TypeScript check/build and all 248 combined Node/Browser checks pass before the
additional silent-page, hello-timeout and early voice-gesture cases; those three
focused additions also pass. Native Windows browser discovery/control and commit
are not implemented by this checkpoint. The component refuses commit, so these
results do not enable an installer or claim end-to-end weekly updates.

At `f079931`, [full Windows qualification](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36375929935)
passes both CPUs and the Mac Qt candidate. Fast Windows desktop, installer
feasibility, [Linux validation](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36375929882)
and Mac feasibility also pass. This includes the DSH/Pi bridge drain and the
first real Chromium page-reservation proof, superseding earlier pending entries.

The following native browser source adds private wrapper registration, exact
relay Job/executable verification, held-lock discovery with retained process
observations and a separate control connection into the actual Node host. Native
request/action correlations veto preparation; worker/page cancellation releases
the matching native fence. Local actual Chromium now uses this product control
path, replacing the earlier framing proxy. All 257 combined Node/Browser tests,
four private-transport Python tests and five launcher policy tests pass. The
expanded compiled native-host proof awaits x64/ARM64 execution. Commit explicitly
refuses until global startup fencing and independent installer handoff exist.

The first independent-process run at `3748282` fails before Setup readiness on
both CPUs. The pinned pywin32 312 `win32con` does not export
`CREATE_BREAKAWAY_FROM_JOB`; source now uses its documented Win32 flag value.
The fixture also reports an early coordinator error immediately instead of only
a missing readiness file. Native independent-process success remains pending;
the earlier extracted-Setup handle-transfer proof remains separately qualified.


The follow-up `bacf148` independent-installer fixture fails CreateProcess with
access denied on both CPUs. Current source corrects process/thread security to
use generic object rights and adds explicit hosted-runner containment scope;
no automatic production fallback is added. It also implements authenticated
pipe transfer into an embedded Inno helper, separate READY/APPLY decisions,
normal/crash retention after authorization and refusal before authorization.
Python syntax checks pass. All new native helper/independent launch execution
remains pending; customer distribution, global commit and rollback remain open.

At `066320c`, the x64 helper compiles and the first independent Setup launch
reaches verified Job membership. Its artifact-write probe is correctly refused,
but the Python CRT maps the error to errno 13 rather than preserving Win32 code
32, so the test assertion fails. The probe now uses the native private-file
adapter for an exact kernel sharing result. Authenticated handoff, cancellation
and crash cases still require execution. The next fixture also explicitly checks
an unrelated pipe client and a wrong coordinator PID. These are test corrections
and additional assertions, not waived qualification.


At `261d3c4`, [installer qualification passes both CPUs](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36383382819),
including all authenticated handoff/peer refusal/cancel/crash cases. This supersedes
the earlier independent-helper pending/failure statuses within its disposable,
outer-runner-Job scope. No public installer or complete updater is qualified.

The full x64 run at `3748282` fails a graph-fixture assumption: an ordinary model
turn does not necessarily start both lazy companions. The graph correctly reports
only the running components. Current fixture explicitly starts prompts/memory
through its own supervisor and observes their RPC readiness before asserting a
five-component graph. The same run times out exporting a Qt screenshot after
three seconds; capture alone now has a 15-second bounded wait, records elapsed
time and requires a successful PNG result. Ordinary control deadlines remain
three seconds and no request is replayed. The portable two-window proof passes
with an 11 ms export; new native graph/render execution is pending.
Full `0ca8348` native runtime previously passed both CPUs.
