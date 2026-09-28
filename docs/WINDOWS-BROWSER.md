<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Windows browser companion implementation

The Windows candidate retains the shared Chromium extension, protocol and DSH/Pi
bridge. Browser selection must allow a Chromium executable chosen by the user,
including forks such as Comet. A known-browser list cannot be a prerequisite.
This guide records implementation and evidence, not a completed installation.

## Native executable

The payload now builds `AugmentorBrowserHost.exe` alongside `Augmentor.exe`, using
the same isolated embedded Python and private DLL policy. Only the application
has a desktop entry. The browser host has binary stdin/stdout, no console or modal
startup error, and writes diagnostics to the private user log. Its manifest origin
is derived from the existing extension key; it accepts that origin and the browser's
bounded parent-window argument. The browser's manifest allowlist is still the
browser-side authorization boundary; argv alone does not authenticate a process.

The host shares the desktop's verified environment and installation lease. It
ensures the per-user supervisor, then retains a Windows Job for its Node bridge
and descendants. Browser disconnection exits the bridge; a host crash also closes
the Job. Prompt/memory and DSH remain with the supervisor, not that short-lived
bridge. Neither browser startup nor a disconnect installs or updates DSH.

The new native qualification sequence launches the actual binary with disposable
browser-style stdio. It checks required/versioned handshake, Unicode/newline
prompt save/readback, selection of the actual bundled DSH, its previously generated
fixture conversation history, refusal of the legacy plugin-update route, and
preserved supervisor components after disconnect. These native checks pass on
both x64 and ARM64 at `13c6c0d` in [run 36366164798](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36366164798).
This is not evidence of registry discovery, extension loading or a real browser
window. Those are separate W5 gates.

## Remaining browser work

The source now provides per-user registration in the Chrome, Chromium and Edge
HKCU native-host lookup locations. This is a host compatibility mechanism, not
a browser-choice allowlist. The manifest retains the stable installed executable
path, outside a version-specific selection. Existing foreign registrations or
edited manifests are refused before writes/removal. Repeating an unchanged setup
does not rewrite registry values; a failed multi-key setup rolls back only values
written by that attempt. Removal preserves unrelated registry values. A private
manifest is removed only after the owned registration values are retired.

Native tests use unique disposable HKCU paths, check both registry views, simulate
an interrupted registration and validate a stable junction-based launcher path.
These tests pass on both native CPUs at `8df9049`; no actual browser lookup
location has been changed by them.

Discovery now reads HTTP/HTTPS capabilities under Windows `RegisteredApplications`
and resolves their command's executable with the Windows argument parser. It
does not run registered commands, change the default browser or inspect profiles.
A separately selected executable is accepted through the same static PE product
metadata and Chromium resource inspection, without a product-name allowlist.
Renamed resource packs and version subdirectories are supported. This is a
candidate browser check, not proof of extension/native-messaging compatibility.
Native tests use disposable registration and resource fixtures; their discovery
execution passes both native CPUs at `13c6c0d` in [run 36366164943](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36366164943).
Real installed-browser acceptance remains pending. The executable
picker must remain available when discovery finds nothing.

The chooser now shares the existing Mac Qt form and control flow. Windows uses
an `.exe` picker, opens the exact selected browser with `chrome://extensions`,
and gives Windows folder-selection instructions. Cancel/invalid selection
preserve the current browser; selecting another clears any earlier prepared
result. It does not choose a default browser or force extension installation.

Windows preparation requires the installer's HKCU
`Software\Augmentor\Installation` anchor (`AppId=com.augmentor.Agent`, `Root`
equal to the stable payload path), matching release CPU metadata and both native
executables. Source/build-tree launches do not create this anchor or expose
setup. W7 must create/remove it with the other owned registrations; that
installer integration is still pending. The anchor is ownership metadata within
the ordinary-user boundary, not publisher authentication or protection against
hostile same-user software.

Preparation copies the bundled extension to a content-addressed private data
directory, outside replaceable application files, and registers the native host.
It checks source links, bounds file sizes, applies user ACLs, refuses edited
prepared files and keeps previous copies. The native test uses only disposable
anchors/host keys and a PE/resource browser fixture. Its execution is pending;
local tests pass all five chooser flows, 16 Mac browser tests and 28 common window
tests. Actual-browser and clean-installer acceptance remain distinct.

The first native preparation run reaches a real ACL rejection: Windows' default
temporary-directory owner can be the Administrators group under the hosted token.
Preparation now creates its random staging directory with the explicit private
directory adapter instead. It does not weaken ownership checks or rewrite an
existing directory's ACL. Native preparation must rerun after this correction.

At `742bfb0`, [desktop run 36367999216](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36367999216)
passes both native CPUs, including installed-anchor checks, private staging,
repeated preparation, edited-extension preservation and the Windows chooser.
Installer-created anchors and an actual browser connection remain open gates.

Installer anchor wiring, registry views and fork lookup locations still need
actual-browser tests; do not infer them from browser profile directories.
Preserve the shared chooser/instruction flow and verify an actual
selected-browser native connection before calling setup complete. Consumer store
identity/review and independent extension update compatibility remain release
gates. No browser policy or extension installation is forced by this work.

References: [Chrome native messaging](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging),
[Edge host registration and lookup order](https://learn.microsoft.com/en-us/microsoft-edge/extensions/developer-guide/native-messaging),
and [Chromium Windows launcher source](https://chromium.googlesource.com/chromium/src/+/main/chrome/browser/extensions/api/messaging/launch_context_win.cc).
Browser inventory follows [Windows application capabilities](https://learn.microsoft.com/en-us/windows/win32/shell/default-programs);
it does not use the deprecated Start menu Internet default as the user's current
browser selection.

September 28 lifecycle source now [drains accepted bridge operations](LIFECYCLE.md#browser-transport-drain)
instead of calling `process.exit` during ordinary disconnect. The Windows wrapper
waits for the complete owned Job, preserving any surviving child rather than
closing its Job after only the leader exits. DSH/prompt/memory ownership remains
with the background owner. Portable real-process drain checks pass; actual
compiled integration of this new shutdown path is pending. This adds neither
completed global Quit. The subsequent shared
[browser page reservation](LIFECYCLE.md#browser-page-reservation) now inventories
every open extension document, refuses drafts/unsaved settings, pauses input and
reconnect, and restores admission on cancel or expiry. Its native-frame and real
Chromium proof runs in an isolated Linux profile. Windows host discovery/control
is now implemented through the [native browser participant](LIFECYCLE.md#native-browser-participant)
and awaits compiled execution. The native startup fence and committed browser
exit remain pending; the component explicitly refuses commit until that handoff
is implemented. Source registration/control is not a completed updater.

## Installed ownership receipt and removal

The actual Inno candidate now creates the Root/AppId anchor required by browser
setup. During `prepare_extension`, after validating or creating its private host
manifest and before publishing any new browser registry pointers, the adapter
records the exact manifest SHA-256 under that same installed anchor. Receipt
failure cannot publish new pointers; a new unused manifest is removed on failure.
The root is rechecked against the actual selected installation before recording.

The native uninstaller checks its own installation identity, discovers only its
known exact HKCU pointers and pins the private single-link manifest without write
or delete sharing. Inno hashes that retained file and compares the typed receipt.
Changed/missing/unverifiable owned manifests refuse removal before application or
login changes. Foreign registry pointers remain untouched. When removal actually
starts, only matching browser pointer values and the matching receipt are removed;
browser profiles, prepared extension copies and all persistent user data remain.
Cancellation before removal changes no pointers. No application Python is loaded
from a directory being removed. This receipt proves retained byte ownership, not
publisher authenticity, browser compatibility or extension store delivery.

New native tests cover receipt-before-registration ordering, failure preservation,
read/delete refusal while the native manifest handle is held, and full installed
preparation/removal through synthetic Chromium resources and private fixture keys.
These new cases are scheduled, not yet qualified. Actual selected-browser/store
and physical Windows tests remain open.
