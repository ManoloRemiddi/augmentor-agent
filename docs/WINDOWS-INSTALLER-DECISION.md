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
