<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Choose an installed Chromium browser on macOS

The earlier setup hard-coded Chrome and Chromium and could not configure Comet.
The replacement discovers browser applications in system/user Applications and
one organizational subfolder, and provides a native app chooser for other
locations. It validates HTTP/HTTPS browser handlers and Chromium framework
resources, then opens the exact chosen app's Extensions page. Users can prepare
another browser without reopening setup. Safari is not a Chromium browser.

Registration uses Chromium's `CrProductDirName` metadata when provided. Otherwise
an existing app-named data directory containing `Local State` is required, with
an explicit data-folder chooser for ambiguous cases. No profile contents are
read or modified. Paths outside Application Support, traversal and linked
directories are refused. Legacy CLI aliases remain compatible. Uninstall/restore
discovers matching Augmentor manifests for selected forks and preserves unrelated
or edited manifests. The immutable extension copy and stable extension ID remain.

This is a Mac OS adapter change; shared extension code, Linux browser setup and
desktop appearance are unchanged. Discovery establishes the engine family, not
support for every fork's extension APIs or enterprise policies. Browsers must
support unpacked Manifest V3 extensions, native messaging and the side panel.
The user still approves Load unpacked in the browser; there is no silent install.

## Qualification checkpoint

Source implementation is on `fix/macos-browser-choice`. Fourteen browser
registration/dialog tests and eleven uninstall/recovery tests pass locally.
The broader local Mac suite cannot import QtTest in the workstation's system
PySide6; the pinned Mac build environment must run the complete suite.
Comet 153.0.8010.191 on the 32 GB Mac loads the bundled extension in a disposable
profile and exposes side-panel, action and native-messaging APIs. This initial
probe does not establish a working native connection or installed replacement.
Clean candidate, end-to-end Comet chat and installed readback are still pending
at this checkpoint. Public preview 2 is unchanged.

The interface proof now accepts `AUGMENTOR_PROOF_BROWSER_APP`, uses the selected
app's metadata and registers directly into its isolated data root before launch.
It verifies side-panel API availability, native messaging, DSH chat and desktop
Send/reopen against the deterministic local provider, without personal profiles.

## Primary references

- [Chromium macOS product directory implementation](https://chromium.googlesource.com/chromium/src/+/main/chrome/common/chrome_paths_mac.mm).
- [Chrome native messaging registration](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging).
- [Comet quick start guide](https://www.perplexity.ai/comet/resources/articles/comet-quick-start-guide).
