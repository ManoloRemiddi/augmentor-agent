<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Windows installer qualification: active-work removal

September 28, 2026. **The stock Velopack EXE is not selected for production.**
Its successful disposable install/update fixture did not test the ordinary
Windows Settings uninstall path while work was active. W1 is reopened for that
requirement; no customer installer has been published. The private runtime,
native launchers, shared application and Windows adapters do not depend on this
packaging choice.

**Implementation decision after native feasibility:** use Inno Setup 7.1.0 and
WinSparkle 0.9.4 for the Windows integration. The complete bounded alternative
probe passes both x64 and ARM64 in [run 36367881230](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36367881230),
branch head `85cfbd7`, actual GitHub merge checkout
`c8c01d3a00e2267b342f408ade15d7152cfc0a2e`. This replaces the rejected Velopack
default. It does not waive full app coordination, rollback/health, signing or
ordinary-user/interactive installer qualification. Only this selected backend
will be wired into the customer package; the Velopack fixture is historical
failure characterization.

## Observed upstream behavior

The inspected Velopack 1.2.158 source is pinned at
`3c7f52c1bf17d10ad21b794b006d5ebd1a879a3b`.
Its [EXE uninstall](https://github.com/velopack/velopack/blob/3c7f52c1bf17d10ad21b794b006d5ebd1a879a3b/src/bins/src/commands/uninstall.rs)
calls `force_stop_package` before the application hook. The
[documented hook](https://docs.velopack.io/integrating/uninstalling) cannot cancel
removal. Returning a busy error from that hook is therefore insufficient.
This violates Augmentor's requirement that normal maintenance preserve active
work and refuse/defer before terminating components.

Changing `UninstallString` inside the install hook is also insufficient: the
[install routine](https://github.com/velopack/velopack/blob/3c7f52c1bf17d10ad21b794b006d5ebd1a879a3b/src/bins/src/commands/install.rs)
writes its registry entry afterward, and updates write it again. A later registry
wrapper would still leave setup/repair and interruption cases to solve.

Velopack's MSI mode preserves its updater, but the generated
[MSI actions](https://github.com/velopack/velopack/blob/3c7f52c1bf17d10ad21b794b006d5ebd1a879a3b/src/wix-dll/src/lib.rs)
always report success after hooks, including nonzero exit and timeout.
The [template](https://github.com/velopack/velopack/blob/3c7f52c1bf17d10ad21b794b006d5ebd1a879a3b/src/vpk/Velopack.Packaging.Windows/Msi/Templates/MsiTemplate.hbs)
has no application veto before removal. Switching the output extension to MSI
does not itself meet the requirement. A custom MSI transformation/upstream fork
would introduce a separate maintenance and qualification obligation.

## Alternatives assessed against this failure

| Option | Relevant behavior | Conclusion |
| --- | --- | --- |
| Stock Velopack EXE | Stops package processes before non-vetoing uninstall hook | Fails normal busy-uninstall requirement |
| Stock Velopack MSI | Hook errors do not abort; no product admission guard supplied | Not a proven fix; would need custom packaging work |
| MSIX / App Installer | Can defer updates while in use; removal normally has force semantics, unless its caller explicitly requests deferred removal | Does not establish safe ordinary Settings removal; also requires external-browser registration and full-trust child qualification |
| Inno Setup plus WinSparkle | Native proof passes veto, lifetime admission, retry, signed-download rejection and target filtering | Selected for implementation; full product integration and release qualification pending |

Microsoft documents both [deferred updates and forced default removal](https://devblogs.microsoft.com/insidemsix/msix-servicing-while-in-use/).
The latter is why a format change alone is not the resolution.
Inno's [event functions](https://jrsoftware.org/ishelp/topic_scriptevents.htm)
allow preparation failure and uninstall refusal. WinSparkle's
[API](https://github.com/vslavik/winsparkle/blob/master/include/winsparkle.h)
allows refusing installer launch while busy, and its
[distribution](https://github.com/vslavik/winsparkle) includes ARM64.
These are research findings, not executed Augmentor integration.
The bounded native fixture result above adds execution evidence; it still does
not establish that Augmentor's actual component graph drains safely.

## Required proof before selecting a replacement

1. Pin/hash the build tools and updater binaries; preserve ordinary-user install,
   native x64/ARM64 payloads, a single app identity and the shared UI.
2. Use two disposable versions and a uniquely named fixture. Exercise normal and
   silent install, reinstall/repair, update and Windows-registered uninstall.
3. While active, refuse **before** file replacement or process termination.
   Hold an admission reservation throughout maintenance; a status snapshot is
   insufficient because new work can start after it.
4. After an idle drain, remove only owned software/registrations, preserving data.
   Test cancellation, a failed helper, stale state, installer crash, retry and
   restoration of admission without silently replaying actions.
5. Prove signed update integrity, wrong-CPU/channel rejection, retained recovery
   payload, failed-health rollback and successful next-version restart. Signature
   and clean ordinary-user proofs remain separate from hosted unsigned fixtures.

There will be one selected installer/updater backend, not two customer channels
using competing maintenance rules. The shared release manifest/coordinator still
owns product/dependency compatibility on Linux, Mac and Windows.

## Reproducible failed-requirement probe

`scripts/windows-installer-proof.py` now extends the existing two-version fixture
with a live holder and the actual stock uninstall command. It records termination,
the leftover active marker and the hook's view of that marker. The expected
upstream failure is explicit as `productionInstallerQualified: false`; a green
workflow means the characterization ran, not that the installer meets W1.
Native execution of this additional probe is pending. Previous busy-update
refusal remains valid only for the fixture's app-initiated update entrypoint.

The next independent `Windows installer feasibility` workflow pins Inno Setup
7.1.0 and WinSparkle 0.9.4 by upstream release SHA-256. Its disposable package
tests two simultaneous active processes against repair, update and the registered
uninstaller, then an injected preparation failure, retry and idle removal. The
installer owns an exclusive file-sharing handle for the complete operation;
fixture workers share that same admission file. This qualifies the mechanism,
not the full product's still-pending drain and admission integration.

The native x64/ARM64 WinSparkle DLL separately checks an ephemeral-key signed
download, an invalid signature, a busy callback and a wrong-architecture feed.
Its test callback inspects the verified bytes without executing them. The Inno
lifecycle and updater verification are deliberately separate evidence, not a
claim of a complete consumer update transaction. The compiler and installer
bootstrap are x64 tools (emulated on ARM); app, Python and updater are native.
This new workflow has not executed yet. Publisher identity and Authenticode
remain separate from the disposable EdDSA key used for test downloads.

The first native run at `762f7c6` builds both CPU fixtures and installs/opens them
successfully, then fails a test assumption: Inno shortens long AppIds in its
uninstall registry key. The fixture now uses a shorter unique ID; it still reads
the registered uninstall command rather than guessing its executable. No busy
maintenance or native updater result is claimed from that first run.

The second alternative run, `36367490603` at `e18fbb0`, passes the installer
busy repair/update/removal, two-holder preservation, failed preparation/retry and
idle lifecycle sequence on both CPUs. Native valid-download handling and invalid
signature rejection also pass. The busy updater test then times out because its
modal refusal dialog was not dismissed before the fixture called cleanup. The
fixture now closes only its own updater windows and retains callback progress
before cleanup; the complete updater result still requires rerunning.

The first stock-EXE busy-uninstall probe reaches forced holder exit and the
active-marker assertion on x64, then fails redundant cleanup: `Update.exe`
survives briefly for self-removal and a second uninstall cannot find the removed
application. Cleanup now checks the application still exists before retrying.
The rejected product requirement has not changed.

The corrected alternative run passes all four native updater cases on both
CPUs: matching signed bytes reach the handling callback; a bad signature does
not; busy work returns false and never hands off the download; a feed for the
other CPU reports no applicable update. Both reports record the same merge
checkout above. The installer refuses while either live holder is present,
releases admission after injected failure, and completes idle repair/update/
removal with persistent settings unchanged. Physical installer interaction,
full-app process coordination and failed-health rollback remain open.

## Independent Setup handoff qualification

The startup writer now has separate native sharing/inheritance evidence on both
CPUs at `e4593b1`. Current source extends the Inno fixture to the actual extracted
Setup process: it explicitly duplicates the disposable coordinator's handle in
`InitializeSetup`, then acknowledges before the coordinator exits normally or is
deliberately crashed. The test observes that exact Setup process, verifies new
startup readers and competing writers remain refused, releases the fixture to
complete repair, and checks the gate is released after normal Setup exit. An
invalid transfer must abort before changing the installed fixture version.

This qualification intentionally does not rely on the bootstrap executable
inheriting a handle into its extracted child. It follows Inno's documented
[initialization/finalization events](https://jrsoftware.org/ishelp/topic_scriptevents.htm)
and Windows [DuplicateHandle](https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-duplicatehandle).
Native execution is pending. Its raw PID/handle arguments and compiled fixture
acknowledgment paths are **not a production handoff protocol**. Customer integration
still requires authenticated coordinator/installer identity, verified artifact
binding, complete app drain, durable transaction/health recovery and rollback.
No customer installer or updater callback is enabled by this fixture.


## Independent installer process ownership

The extracted-Setup transfer fixture at `0ca8348` passes both CPUs in
[36380756992](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36380756992).
The next source step adds `windows_installer_process.py`: it holds a protected
private artifact open without write/delete sharing, compares its SHA-256 against
the caller's previously verified digest, creates it suspended and assigns an
unnamed Job before the first instruction executes. This Job has no kill-on-close
limit. The installer requests breakaway from any enclosing app Job; refusal
aborts before execution rather than silently accepting a crash-coupled updater.
Closing the observation or losing the coordinator cannot terminate the installer.

The retained Job permits same-user live descendant observations, including
Inno's extracted Setup process, while refusing unrelated PIDs. Production must
obtain the PID from authenticated IPC and the digest from release verification;
a file containing a PID and a self-computed download hash are not those trust
boundaries. The current fixture explicitly uses test-only file acknowledgments.
It now checks wrong-digest refusal, artifact write exclusion, actual Setup Job
membership, unrelated-PID refusal and exit/crash survival through the new adapter.
Native execution of this addition is pending. Authenticated handoff, signing,
complete graph commit, durable recovery and rollback remain open.

The launch ordering follows Microsoft's [suspended process creation flags](https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags),
[assignment before running a process in a Job](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-assignprocesstojobobject)
and [Job lifetime and breakaway rules](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects).

The first independent-process run at `3748282` fails before Setup readiness on
both CPUs. The pinned pywin32 312 `win32con` does not export
`CREATE_BREAKAWAY_FROM_JOB`; source now uses its documented Win32 flag value.
The fixture also reports an early coordinator error immediately instead of only
a missing readiness file. Native independent-process success remains pending;
the earlier extracted-Setup handle-transfer proof remains separately qualified.


## Authenticated handoff source

The next source adds a one-shot private pipe from the coordinating process to
Inno's actual Setup process. The coordinator verifies the kernel client PID
against the exact installer Job before duplicating the startup writer into it.
The x64 helper inside Inno verifies the pipe server's PID/current user and the
received handle's private owner, regular single-link file identity, exact runtime
path and active startup exclusion. Customer helper builds reject alternate
runtime roots; the development helper permits the explicit disposable test root.
The helper loads from Inno's embedded files, outside application replacement.

`READY` only confirms retained startup exclusion. The caller must separately
send `APPLY`, after global drain and durable recovery are established. Cancellation,
coordinator loss or timeout before `APPLY` aborts Setup without authorizing file
changes. Lost application acknowledgment is an unknown outcome, never a reason
to replay the action. The separate final installation lease is still required.
This interface is not yet wired into a customer updater or global commit.

The Inno fixture now compiles the helper and tests authenticated normal handoff,
coordinator loss after authorization, cancellation and loss before authorization.
It retains the actual Setup process before deliberately crashing the coordinator.
Native execution is pending; only syntax checks have run locally.

The `bacf148` attempt reports CreateProcess access denied on both hosted CPUs.
Source review also found that file-specific access bits had been reused for
process/thread security: the new code uses each object's GENERIC_ALL mapping
for the private current-user/SYSTEM descriptor. Hosted qualification explicitly
allows its enclosing runner Job and records kernel Job membership; it never
silently falls back after a refused independent product launch. Production still
requires breakaway and refuses if that environment prevents independence. The
new native run must distinguish these boundaries before claiming success.

The helper uses Inno's documented [embedded DLL loading and setup-only calls](https://jrsoftware.org/ishelp/topic_scriptdll.htm).

At `066320c`, the x64 helper compiles and the first independent Setup launch
reaches verified Job membership. Its artifact-write probe is correctly refused,
but the Python CRT maps the error to errno 13 rather than preserving Win32 code
32, so the test assertion fails. The probe now uses the native private-file
adapter for an exact kernel sharing result. Authenticated handoff, cancellation
and crash cases still require execution. The next fixture also explicitly checks
an unrelated pipe client and a wrong coordinator PID. These are test corrections
and additional assertions, not waived qualification.


At `261d3c4`, [the full Inno/WinSparkle fixture passes both CPUs](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36383382819).
This includes independent Setup ownership, immutable artifact binding, private
pipe authentication, wrong coordinator/unrelated client refusal, explicit APPLY,
cancel/loss before authorization and retained exclusion across exit/crash after
it. The x64 report confirms its outer hosted-runner Job was present in all four
handoff cases. Production breakaway and ordinary-user installation remain
separate acceptance; the fixture does not bypass or qualify those constraints.
Complete product commit, recovery, rollback, signing and publication remain open.

The current authenticated fixture also uses the [durable update record](LIFECYCLE.md#durable-update-record).
It records a repair of the selected fixture with the same 0.0.2 artifact, writes
apply intent before authorization, and checks retained records after normal
coordinator exit, crash and before-apply abort. Seven local journal tests pass;
actual Inno execution of this addition is pending. The record is an inspection
input and never authorization to repeat an uncertain install.

## Final installation access after coordinator exit

The embedded helper now exposes a bounded final-access operation, available only
after authenticated APPLY. It waits on the retained coordinator process handle
for actual exit, opens the existing private `installation.lock` without sharing,
validates its owner/ACL and ordinary single-link identity, and takes the exclusive
byte-zero lease. It holds that handle and the transferred startup writer through
Setup completion. Missing/foreign files, a coordinator that remains alive, or any
other application lifetime handle refuse replacement. It loads no application
Python/Qt DLL from the directory being replaced and never terminates a process.

The Inno fixture calls this before file installation. Its coordinator now retains
a real shared lifetime lease, which the controller independently observes before
exit. Authenticated cases test normal exit, crash, and an extra holder that must
make Setup refuse final access. Source/syntax checks pass; these new C/Inno cases
await native compilation/execution. Initial installation, real product data,
recovery/health/rollback, signing and ordinary-user acceptance remain separate.

At `3394145`, the helper compiles on both CPUs, then Inno compilation rejects the
combined Boolean/Windows BOOL expression. The fixture now assigns the result to
a Pascal Boolean before branching and uses an explicit Cardinal timeout. Native
execution of final access remains pending. The preceding `1872e19` Inno journal
qualification passes both CPUs in [36388207448](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36388207448).

## Actual application installer candidate

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

The shared native launcher now takes startup exclusion before its lifetime lease;
manual maintenance uses the same order with exclusive handles and byte locking.
No process is killed or adopted. The application payload is checked for source
links before compilation, and the existing installation tree is checked for
redirects/hard links before replacement/removal. These checks do not claim to
protect against a malicious process already running as the same Windows user.

The Inno template uses the documented [setup/uninstall event boundaries](https://jrsoftware.org/ishelp/topic_scriptevents.htm)
and [temporary DLL unloading](https://jrsoftware.org/ishelp/topic_isxfunc_unloaddll.htm).
Its helper is compiled for the x64 Setup/uninstaller process on both CPUs; the
application and all its runtime DLLs retain the native selected architecture.

## Shared coordinator Windows backend

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

`WindowsApply` accepts only the startup gate and caller-verified artifact digest,
uses fixed Inno flags and a fresh private log, and closes the handoff before its
process observations. Unknown apply acknowledgments cannot be replayed. The
installer remains independent after coordinator exit; a digest still does not
establish publisher trust. Its explicit outer-runner Job option is fixture-only.
The installed integration script is a development proof, not a public updater or
a production trust boundary. Product update metadata/UI/recovery remain open.

The full Windows workflow now runs the selected Inno application installer instead
of reinstalling the rejected Velopack feasibility pair on every change. The
original proof scripts and dated failure evidence remain available for reference;
removing that redundant CI step does not waive any Inno/product release gate.

Windows staging now places its temporary production dependency graph on the same
volume and moves disjoint top-level directories into the payload, avoiding a
second recursive copy of node_modules. Overlapping runtime/license directories
retain their previous merge behavior. Native output qualification remains required;
no measured speedup is claimed. Package evidence records installer byte size.

The installed proof reads the Start-menu shortcut target/arguments, observes the
real Setup exit, compares every installed payload file to the known-built fixture
and opens/closes installed Qt before completing and archiving the durable update
record. This is local health for identical-build qualification, not live provider,
Windows speech engine or production recovery evidence. Native execution is pending.

At `3c6d78b` the actual x64 full-payload installer compiles and installs, then the
qualification stops because Inno's default AppVerName adds the version to the
registered display name. The template now explicitly uses `Augmentor Agent`;
DisplayVersion continues to identify the release separately. Repair, coordinated
apply and removal still await execution after this correction.

## Actual shortcut readback correction

Full x64 `805664f` installs and verifies the shared payload and stable registration,
then fails the actual IShellLink argument comparison. The earlier compiler-command
quote escaping crossed both command-line and Inno section parsing. Current source
constructs the qualification command in a Pascal code constant after those parsing
layers. It records actual shortcut arguments on any future comparison failure.
Three portable package intake tests pass; native readback and later installed
repair/coordinator/removal stages remain pending. Normal customer launch has no
qualification arguments. No personal shortcut or public installer changed.

## Signed download integration

The [release delivery boundary](WINDOWS-UPDATE-DELIVERY.md) now authenticates signed
metadata and retained installer bytes independently of feed labels. New native
WinSparkle ZIP callback fixtures are scheduled on both CPUs. Local real-signature
and storage tests pass; native execution, product UI wiring, N-to-N+1 and recovery
remain pending. WinSparkle never receives default installer-execution authority.

## First installed preview and busy-maintenance evidence

Full x64 `594b56d` now passes actual payload integrity, stable application name,
shortcut target/arguments and native installed preview launch. Repair and removal
both refuse while its draft is present, preserving the process, draft and data.
The next assertion exposes a shared controller-free preview close timeout, before
repair or coordinated apply. It is reproduced and corrected in the shared UI;
portable real-process checks pass, and native rerun is pending. Failed installed
proofs now retain bounded logs from only their disposable preview directory.

## Owned installer registrations

The candidate now records the stable browser-setup installation anchor and offers
background login startup on fresh install. It uses a native, typed exact-value
HKCU operation under the held installation gate, preserving matching/foreign
values as appropriate and never loading application Python during replacement.
Repair/update preserve removed login startup. Removal compares before deleting
only owned values; unrelated values and StartupApproved are untouched. The
[Windows shell guide](WINDOWS-SHELL.md#installer-owned-login-and-browser-anchor)
records paths, behavior and remaining native/physical qualification. New native
Inno registry fixtures and full installed readback are scheduled, not yet passed.

## Native long paths and browser cleanup

Full x64 `ead355c` passes installed preview exit after the shared fix, then refuses
same-build repair in native tree validation. The actual initial-install log has
65,933 file entries, including 205 paths over 260 characters (maximum 283). The
native walk used unprefixed Win32 paths, independently of the app launcher's
longPathAware manifest. Current source uses explicit extended local paths for
ancestor checks, enumeration and file inspection. Attribute inspection also allows
delete sharing, so Setup's own uninstall-log handles do not cause a false refusal.
Hard-link/reparse/depth/count checks remain. New Inno qualification includes an
ordinary payload over 500 characters; full installed repair must still pass.

The actual native registry fixture at `2f17cb0` passes both CPUs. Current source
adds [browser ownership receipts and removal](WINDOWS-BROWSER.md#installed-ownership-receipt-and-removal),
plus real native held-file write/delete refusal. The full installed proof prepares
an extension using synthetic Chromium resources and isolated registration keys,
checks manifest-edit removal refusal, then checks normal pointer cleanup with
persistent data retained. New execution is pending; actual browser UI/store
acceptance and complete installed update/recovery remain open.

## Closed fixture readiness publication

At `6890375`, the [native fixture run](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36398267565)
passes completely on x64. ARM64 passes the new typed registry, long-path traversal
and private manifest pinning cases, then encounters a sharing violation in the
older observation file: `ready.json` exists while Inno still holds its writing
handle. Fixture readiness now publishes by rename after the write closes. Python
observations likewise publish complete JSON. No timeout is enlarged and no
authority/installer assertion is removed. The actual authenticated pipe remains
the handoff contract. Native rerun of this test correction is pending.

## Full installed repair and isolated removal diagnosis

At `6890375`, [full x64 qualification](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36398267417)
now passes actual initial installation/browser/login identity, live-draft refusal,
repair and normal Qt relaunch, installed graph drain and same-build coordinated
application, complete file-digest/local Qt health and journal archival. Removed
login startup stays removed. Final uninstall incorrectly refuses, even after the
fixture's edited browser manifest is restored. The existing log does not identify
which preflight refused, so current code logs admission, tree, manifest retention
and receipt failures separately. No refusal is bypassed.

`scripts/windows-application-template-proof.py` uses the exact application Inno
script and packaging definitions with small inert component markers. It does not
launch or qualify those markers as an app. It first requires repair/removal with
no browser entry, then edited-manifest refusal and exact-owned removal. This
qualifies real installer event integration separately from the full product, and
makes removal regressions diagnosable without rebuilding all app dependencies.
New native execution is pending. The preceding [67eebe3 native fixtures](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36399077539)
pass completely on both CPUs, at merge checkout `85522a92c8cad9d45bf22bd1395c5607d5bd8e46`.

The smaller exact-template test at `77731b9` reproduces the failure before any
browser is configured: default registry-value inspection returns an error. The
helper rejected a NULL value-name pointer. Pascal Script uses this representation
for an empty String; [Windows defines NULL and empty names as the default value](https://learn.microsoft.com/en-us/windows/win32/api/winreg/nf-winreg-regqueryvalueexw).
The helper now normalizes the representation without relaxing gating, type checks,
exact expected content or foreign preservation. The actual Inno registry fixture
adds default-value read/create/remove and foreign refusal. Both the small exact
application-template test and full installed removal must pass before this is
considered qualified.

At `df44e1c`, the x64 native default-value checks pass and the exact application
template successfully repairs and removes its inert payload without a browser.
Immediate reinstall then encounters the still-running copied Uninstall process: the
original EXE exits first so Inno can delete it. The next test starts before the
remover releases maintenance (the logs show a 0.5-second overlap). This refusal
is correct, not permission to weaken the maintenance gate.

Both template and full installed proofs now use the existing `OwnedProcess`
range and `wait_graceful` to observe all installer/remover descendants exiting
normally before further actions or inspection. Their existing bounds remain; no
setup/removal command is replayed. Forced cleanup is restricted to failed disposable
tests. Native rerun of the complete sequence is pending.

## Interactive completion and startup handoff

The installer offers the standard checked **Open Augmentor** option on its final
page. Inno's [postinstall run entry](https://jrsoftware.org/ishelp/topic_runsection.htm)
runs after successful installation. Its callback requires completed installation
and held maintenance, then releases the gate before the installed native executable
acquires startup/lifetime handles. Leaving the option unchecked retains normal
end-of-installer cleanup. Silent installs do not launch. Authenticated coordinated
updates suppress this option because independent health owns reopening.

The small application-template test now drives the actual visible wizard buttons
inside its own retained Windows Job. The finish action must start the real
lease-holding launcher and private Python, which write a fixture observation and
exit normally. DSH/Node/PowerShell markers remain inert and no shared desktop or
actual-browser launch is claimed. Silent maintenance must never produce that
observation. Native execution of this new addition is pending; preceding template
repair/removal and signed-update qualification [pass both CPUs at 8a3ff05](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36400951199).

At `8ecd4c0`, both native interactive tests time out before wizard advancement;
this is not a passing Finish check. The driver used GetWindowText on another
process's controls, which [Windows does not support](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getwindowtextw).
It now reads captions through bounded WM_GETTEXT, retaining the exact Job ownership
and button criteria, and writes bounded owned-window diagnostics on failure.
The 120-second overall bound and required native launch observation remain.
The full `8a3ff05` x64 installed proof separately passes normal removal and
persistent-data retention; that workflow still has a memory startup-test failure.

The `5bd0e45` native diagnostics identify the visible enabled control as
`TNewButton` with caption `&Next`; the modern wizard omits the legacy arrow.
The fixture now accepts that exact caption as well as `Next >`. No application
or installer admission behavior changes. Finish/native-launch qualification
remains pending until this corrected driver reaches and verifies it.

## Retain original installer bytes before replacement

Current source preserves the original `{srcexe}` before copying any application
files. The native maintenance helper derives `recovery/` from its already validated
private data handle, verifies the source SHA-256 with Windows CNG, streams a private
copy, flushes it and publishes it by a non-replacing rename. It then pins and hashes
the retained copy again. The filename is the installer SHA-256; its `.release`
receipt contains the compiled payload `release.json` SHA-256. Receipts are also
flushed and published without replacement. Existing matching artifacts are reused;
corrupt bytes, mismatched receipts, redirected paths or invalid permissions refuse
installation before application replacement. Disk/copy failures remove only the
call's unpublished temporary file. Earlier retained installers are preserved.

This cache is byte retention, not Authenticode/publisher verification, selection
of a known healthy build or authorization to roll back. Artifacts from a failed
installation can also be present; never choose recovery by newest filename or
mtime. The separate signed-bundle reader does not interpret these raw first-install
receipts. Initial source selection, publisher trust, independent recovery execution,
health decisions and bounded pruning/removal of software caches remain open work.
Until that retention policy is implemented, normal software removal preserves
recovery artifacts alongside persistent data. Customer publication stays disabled.

The exact-template proof now checks private source bytes/receipt, refuses a changed
installer and changed receipt without modifying the application, and verifies that
repair reuses the retained file. The full installed proof checks complete installer
retention through coordinated reapplication and removal. Native execution of this
new cache is pending; Python compile and whitespace checks pass locally.

At `59dbbf4`, [native Inno x64](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36404083419)
passes the actual interactive Finish/native startup test and all prior cases. ARM64
reaches Finish and the log records application launch and successful Setup exit,
then the driver reads the destroyed wizard handle (1400). The driver now observes
only process exit after Finish and tolerates vanished controls during inspection.
This is a fixture correction; ARM64 Finish qualification still requires a clean run.

At `ba0b68c`, [all Inno/WinSparkle cases pass both CPUs](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36404979491)
at actual merge checkout `612ce6050b6ab3a80478609a7a8514913df1b467`. Downloaded
reports confirm original-installer retention, both corrupt-cache refusals,
repair/removal, exact browser cleanup, interactive native startup and silent
no-launch. This is exact-template/bootstrap evidence; the full payload cache
integration remains under qualification.

## Exact selected-installer receipt

Current source writes `recovery/selected-installer` only after successful payload
installation and registration. Its strict ASCII record is the line
`augmentor-installer-selection/1`, the 64-character installer SHA-256 and the
64-character payload-metadata SHA-256, each followed by LF. Preflight pins and
validates any existing record before application replacement. An invalid/private-
ownership mismatch refuses without changing application files. The post-install
write flushes a new private sibling and atomically replaces only the previously
validated record. An unchanged repair performs no write. Failed/unknown publication
is reported, not retried inside the same attempt.

`services/lifecycle/installed_source.py` reads this exact record under the caller's
installation observation/admission, matches the actual identified `release.json`
bytes, validates target/schema/source identity and the immutable `.release`
receipt, then hashes and pins the selected installer. Missing or damaged records
never select another file by age or filename. The installed coordinator proof
now takes its source identity from this native receipt and executes the actual
retained installer, replacing its previous separately copied fixture source.

Selection is not a health receipt or publisher trust. Interrupted apply still
requires independent inspection and the journal's previous source; do not infer
success or rollback permission from this pointer. Six private-storage reader tests
pass locally (38 update tests total). Exact-template and full installed proofs
exercise native publication/readback, preserved selection on repair and malformed
selection refusal; native execution of this addition is pending.

At `bdba572`, [native Inno/WinSparkle](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36405973067)
passes both CPUs at merge checkout `7fb0927db3e8e75e03a8bae7d31c104649f2a992`,
including selected-source publication/readback and malformed-selection refusal.
The [complete 6c1e7cf workflow](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36403736092)
also passes both CPUs at `0053027cbeb1feee4365ebedd589381fbe431fdb`, through
installed removal and journal archival. That full run predates source caching;
[full bdba572](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36405973046)
is still executing and is the required cached-source integration proof.

## Independent repair from Windows installed-app controls

The candidate registers Inno's [AppModifyPath](https://jrsoftware.org/ishelp/topic_setup_appmodifypath.htm)
as the quoted, privately retained original installer. Windows' installed-program
Modify action can therefore invoke repair without loading the installed launcher,
Python, Qt or application scripts. There is no second Start menu application or
system-wide runtime. The retained installer contains its own maintenance helper.
Client Settings/Control Panel presentation remains a physical acceptance check.

Manual repair can restore missing or damaged `current/release.json` only when
both installed Root/AppId registrations match and the independently held selection
receipt matches this exact installer's digest and compiled payload digest. The
native helper also rehashes/pins the retained executable and checks its private
receipt. Missing/foreign registration, malformed selection or another installer
refuses before app-file replacement. A rejected attempt can retain verified source
bytes; bounded cache cleanup remains a separate unfinished requirement. Removing
the entire payload no longer turns an owned repair into a fresh install or resets
the user's login-startup choice. This is exact-build repair, not rollback.

Manual install/repair and removal refuse any `updates/active.json` under the
private Augmentor data base, regardless of its contents. An inaccessible or
redirected updates directory also refuses. The native check holds the ordinary
private directory and existing exclusive startup/lifetime gates; it never parses
a saved PID, replays an operation, clears the journal or guesses which release
survived. The installed coordinator proof now uses this same canonical `updates`
directory. Cross-version interrupted-update recovery still requires its separate
executor, compatibility/health decision and real failure qualification.

The exact-template proof reads the real ModifyPath, removes the installed native
EXE, Python runtime DLLs and version metadata, checks pending-update/foreign-source/
missing-registration refusal, then runs registered repair from the cached installer.
It verifies restored bytes, unchanged persistent data and source-cache reuse, and
also repairs damaged metadata. The full-payload proof removes the same critical
files, repairs through ModifyPath and reopens the actual installed Qt application.
New native execution is pending; local update tests and script compilation do not
establish these native repair cases passed. Publisher trust, independent rollback,
obsolete-file cleanup and bounded cache policy remain open.

The first native run at `74ec319` fails while compiling the new script, before
installation: combining the DLL's Win32 `BOOL` return directly with Pascal
`Boolean` operands is rejected. The same pinned Inno 7.1.0 compiler reproduces
the line-205 type mismatch in an isolated Wine compile-only fixture. Assigning
the DLL result to the existing Boolean variable before the condition compiles
successfully. No installer was executed under Wine; this is compiler evidence
only. Package failures now include a bounded compiler diagnostic, and CI retains
the template compiler log. Corrected native repair execution remains pending.

At `a0d2530`, both native template installs complete, then the exact ModifyPath
assertion detects that Inno stripped the directive's surrounding quotes. This
would break an executable path containing spaces. Command quoting now happens
inside the code-constant function, after directive parsing; the native assertion
is retained. The older full run at `74ec319` was cancelled because its script had
the already reproduced compile error, not because it was slow or passed.

The downloaded full baseline also exposed unnecessary launcher `.lib`/`.exp`
linker output at the installed payload root. Native builds now direct object and
import/export-library output to their disposable compiler workspace. Template
and full installed assertions require those byproducts absent; runtime libraries
inside the pinned dependencies are unchanged. Native execution is pending.

At `f61d32f`, [all native Inno/WinSparkle cases pass both CPUs](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36409313595)
at merge checkout `b05a0c9a9747d9e52cdbdb905bc1a992a8ad782c`. Downloaded reports
confirm `registered-independent-repair-and-unresolved-update-refusal`, including
missing/damaged metadata and runtime, missing whole payload, preserved disabled
startup and persistent data, wrong selected source/registration and pending-record
refusal, plus all earlier repair/removal/Finish/handoff/signature cases. This is
the exact template with native bootstrap/private Python and inert other components.
The [full f61d32f application run](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36409313612)
is still executing. Compiler-byproduct cleanup was added afterward at `6f4c291`.

Historical gap before the next change: ordinary native startup checks maintenance
leases, not the unresolved update journal. Before enabling customer auto-update,
add recovery-aware startup plus an explicitly authorized independent local-health
probe; do not let ordinary startup load a potentially partial replacement after
maintenance exits. The manual repair/removal guard does not close this separate
gap. Cross-version recovery must use the journal's recorded source and compatible
persistent-data schemas, never infer a healthy source from `selected-installer`.

## Recovery-aware startup and isolated local health

Normal desktop and browser native entrypoints now inspect the fixed private
`updates/active.json` while retaining startup and installation leases, before
loading Python or any app profile. Any existing record, including malformed JSON
or a directory, refuses with exit 74. A redirected or permissive journal directory
also refuses. Manual repair/removal reuse the same native directory check. Saved
phases, PIDs and commands never grant permission to start a partial replacement.

The desktop executable's exact `--local-health` action selects a separate fixed
script. It retains maintenance exclusion, cannot accept other desktop arguments
and is unavailable through the browser host. It creates a private random temporary
profile, clears inherited app/profile configuration, runs runtime preflight and
renders the actual shared Qt window with no controller or persistent preferences.
It checks native Windows Qt, text coverage and a nonempty render, removes only its
temporary profile, and reports the exact payload-metadata hash and identity. It
does not start the supervisor, connect a provider, register ordinary desktop IPC,
change conversations or clear a journal. This is local UI readiness, not complete
feature acceptance or publisher trust.

`services/lifecycle/windows_health.py` runs that action in an owned Windows Job
under read leases and a bounded deadline. It independently compares the report
to the caller-verified release and observes the whole process range exit. Only
that disposable probe range can be stopped on failure. The caller must separately
verify full payload bytes, schemas, artifact trust and installer exit before
requesting journal completion. Health refusal leaves the unresolved record intact.

The installed proof now requires desktop/browser refusal while apply is unresolved,
failed health with a missing helper or mismatched release, unchanged persistent
sentinels/journal, successful isolated native health and profile cleanup. Ordinary
Qt startup is tested only after verified durable archival. The fast native proof
checks pre-Python refusal, unsafe journal directories, fixed action routing and
binary stdout using an explicitly inert recording action; it is not installed UI
health evidence. Two portable real-Qt checks pass and prove no controller/process
startup or preference writes. Fresh x64/ARM64 execution remains pending.

The previous [full f61d32f run](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36409313612)
passes x64 independent registered repair and actual Qt reopening; ARM64 is still
running. [Inno 6f4c291](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36409755006)
passes both CPUs at `cbbaa57cf262d4ceb46536a0566ba126a2943381`, including the
compiler-byproduct cleanup assertion. These runs precede the new health action.
Recovery from interrupted apply, actual cross-version rollback, safe cancellation
before apply, obsolete payload removal and bounded cache retention remain required
before enabling customer updates. An unresolved journal must lead to the future
independent recovery flow, not an instruction to delete its record manually.
