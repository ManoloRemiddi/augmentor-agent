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
preserved supervisor components after disconnect. These native checks are pending.
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
These tests remain pending; no actual browser lookup location has been changed.
Installer/chooser wiring, registry views and fork lookup locations still need
actual-browser tests; do not infer them from browser profile directories.
Preserve the shared chooser/instruction flow and verify an actual
selected-browser native connection before calling setup complete. Consumer store
identity/review and independent extension update compatibility remain release
gates. No browser policy or extension installation is forced by this work.

References: [Chrome native messaging](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging),
[Edge host registration and lookup order](https://learn.microsoft.com/en-us/microsoft-edge/extensions/developer-guide/native-messaging),
and [Chromium Windows launcher source](https://chromium.googlesource.com/chromium/src/+/main/chrome/browser/extensions/api/messaging/launch_context_win.cc).
