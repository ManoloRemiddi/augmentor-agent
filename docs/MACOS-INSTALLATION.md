<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# macOS development installation

**Current preview direction:** The owner approved distribution without Apple
Developer ID after enrollment failed. See [the preview release record](MACOS-PREVIEW-RELEASE.md)
and [customer guide](MACOS-PREVIEW.html). Earlier Apple gates below describe the
intended stable release and historical audits. They do not block the explicitly
approved ad-hoc preview.


The September 25 [distribution implementation](MACOS-DISTRIBUTION.md) adds native
embedded-Python entrypoints, a prepared bundled DSH runtime and development DMG
output. It records current evidence and the remaining first-run/update/signing
gates. The commands below describe the earlier development installer and remain
an advanced preview workflow, not the intended public drag-install experience.

The ARM64 app is a development candidate. Public signing, notarization and the
remaining acceptance gates are tracked in [release status](CROSS-PLATFORM-RELEASE-STATUS.md).

Extract the candidate into a separate directory. Close Augmentor Desktop and
browser connections, and stop the DSH instance using the Augmentor integration.
Run the candidate's bundled Python and installer as your ordinary user:

```sh
candidate="/absolute/path/to/Augmentor Agent Desktop.app"
"$candidate/Contents/Resources/app/python/bin/python3" -I -B \
  "$candidate/Contents/Resources/app/scripts/install-macos.py" "$candidate" \
  --development
```

New installations prefer `/Applications/Augmentor Agent Desktop.app` when the
logged-in user can write there; otherwise they use `~/Applications`. An update
keeps an existing installation in either location. If both exist, the installer
requires an explicit destination rather than choosing or creating another copy.
Use `--destination` to select another owned application directory. Moving an
existing app also requires updating its owned DSH, browser and login references;
changing the destination alone is not a migration. The installer verifies and stages the candidate,
then takes an exclusive installation lease. A running component holding a shared
lease prevents replacement; the installer does not stop or replay tasks.

An existing Augmentor bundle is retained beside the destination with a hidden
`.Augmentor Agent Desktop.before-<unique-id>.backup.noindex` name, so rollback
data is not another app icon. Staging directories also end in `.noindex`.
The JSON result gives its exact path. Older `.before-….app` transaction journals
remain recoverable, but new updates do not create that visible backup format.
To roll back, use that backup as the candidate and specify the same destination.
Rollback verifies the backup and retains the newer bundle in turn. A modified
backup that fails signature verification is retained for inspection and cannot be
installed as a candidate; use an intact previous distribution instead.

No user configuration, conversations, credentials or shared prompt data is deleted.
The application itself must remain immutable while running: the launchers and
shared component environment disable Python bytecode writes within the signed
bundle. Run diagnostic Python commands with `-I -B` for the same reason.

The `--development` flag permits ad-hoc signatures. Without it, candidates must
also pass Gatekeeper assessment. This is not a replacement for the public release's
Developer ID and notarization process. The installer journals replacement before
moving the old app; a later invocation recovers an interrupted promotion under
the exclusive installation lease. Unexpected directory identities stop recovery
for review. Power-loss and clean-user acceptance remain release gates; retain the
original downloaded bundle.

## Browser companion registration

For browser-only use, the separate development bundle is
`Augmentor Agent Browser Companion.app`. Install it with the same command above,
setting `candidate` to that bundle. The same existing-installation preference and
Applications fallback apply. It contains the browser
extension and shared runtimes without Qt, the desktop window, capture helpers or
the global shortcut service. Use the browser extension to interact with it.

Desktop and companion bundles can reside beside each other. Each browser's
native-host registration selects one installed bundle; registering the companion
for that browser replaces the previous registration with a retained backup.
It does not connect that browser to both bundles. Use the installed companion
path in the registration command below. The shared installation lease can still
prevent maintenance while another Augmentor component is running.

The companion supports manual connection to an existing memory service. Guided
memory setup currently requires Augmentor Agent Desktop. Candidate 4 has passed
installed Pi and DSH browser workflows, manual memory controls against Hindsight
0.9.2, and a disposable uninstall/restore check. These development results
do not establish public release readiness.

Run `scripts/register-macos-browser.py` with the installed `.app` path and
`--browser chromium` (the default), `chrome`, or `chrome-for-testing`. Use the
bundled Python with `-I -B`. The registrar creates the per-user native messaging
manifest outside the signed bundle and points it at `Contents/MacOS/augmentor-browser-host`.
It derives the exact allowed extension ID from the bundled extension key.
Existing manifests are backed up before replacement; identical registration is
unchanged. Symlink manifests are refused.

Paths follow Chrome's [native messaging documentation](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging).
Registration alone does not install a browser or prove its extension tools work.
Load the matching extension and complete browser acceptance before advertising
that browser as qualified. The Linux `install-browser-host.py` refuses macOS to
avoid creating launchers inside the signed bundle.

The source registrar also accepts `--remove` with the same installed app and
browser selection. It removes only a semantically matching native-host manifest,
retaining the original file as a uniquely named `.removed-…` backup beside it.
Changed, linked or other-installation manifests are preserved and reported.
This operation does not remove the extension, app, conversations or settings.
The removal option is included in candidate 9.

## Login shortcut service

On a fresh packaged launch, **Fn+Space** is assigned and the per-user login
service is registered automatically. Clicking the application icon opens or
raises its window; the shortcut opens or hides it. A closed app starts through
the same native executable, preserving its icon and application identity.
Settings displays one Mac shortcut and offers **Use Fn+Space** to restore the
default, since Qt's key editor cannot represent the Fn modifier itself.
Saving a custom shortcut transfers ownership to the service, which keeps it
registered after the app quits. An existing
in-app shortcut stays available until saving; reopening the app after removing
login registration does not silently recreate that registration.

For manual registration, close the desktop first and use its bundled Python:

```sh
installed="/Applications/Augmentor Agent Desktop.app"
"$installed/Contents/Resources/app/python/bin/python3" -I -B \
  "$installed/Contents/Resources/app/scripts/register-macos-shortcut.py" \
  "$installed" install
```

This creates `~/Library/LaunchAgents/com.augmentor.Agent.shortcut.plist` and
starts a per-user shortcut service in the graphical login session. Settings in
the desktop then use that service. Its registration persists after the desktop
quits. The service follows Apple's documented
[LaunchAgent lifecycle](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html).
Current evidence and its physical-keyboard/logout boundaries are recorded in
[the clean installation checkpoint](MACOS-DISTRIBUTION.md#september-26-clean-installation-and-default-shortcut).
Candidate 6 predates this service and cannot be registered with this command.

The installer temporarily stops a running, owned shortcut service before taking
the installation lease, and restarts it after releasing that lease. This also
applies when an update fails or an active conversation refuses replacement. A
service already stopped before installation remains stopped. A separate lock
serializes this entire sequence across installers. Rollback to a candidate that
predates shortcut-service support requires removing the registration first.
The candidate 8 installer writes a private recovery record before stopping
the service. After an interrupted run, retrying installation recovers the bundle
and resumes the service even if launchd now reports it stopped. The record is
removed only after resumption succeeds. A changed or removed registration, or an
unresolved bundle journal, prevents automatic resumption and retains the record
for review. Forced process-exit tests pass; actual power-loss recovery remains
an acceptance gate.
Use `remove` to stop the service and remove only its login registration; saved
shortcut settings and other user data remain. Removal also works when the app
has been moved, provided the original app path and registration environment are
supplied to a copy of the registrar. A different or linked registration is
refused. If bootstrap fails, the registrar retains the plist and reports how to
retry or remove it.

## Uninstall

Candidate 9 includes `scripts/uninstall-macos.py`. Run it from a separate
downloaded candidate, using that candidate's
bundled Python with `-I -B`, and pass the installed `.app` path.

The uninstaller verifies the app, stops its owned login service and takes the
exclusive installation lease. An active conversation refuses removal and restores
the previously running shortcut service. The app and matching browser/login
registrations are moved into an `Augmentor-uninstall-…` directory in your Trash.
A JSON receipt records their original and retained locations. Changed or unrelated
registrations stay in place and are listed in the result. Conversations, credentials,
configuration, browser extensions and previous app backups remain untouched.

A failed move rolls back completed moves when their identities still match.
Unexpected replacements stop rollback for review, retaining the receipt and files.
Do not empty that Trash directory until you are satisfied with the removal.
The Mac Mini test removed a disposable signed app with a real login service and
verified its retained signature and settings. Candidate 9 also passed the
packaged uninstall/restore cycle with real launchd. Interrupted-uninstall recovery
with real launchd and power loss still require acceptance testing.

The uninstaller accepts `--restore /absolute/path/to/receipt.json` to
restore retained files. It checks every recorded target before the first move,
refuses new or changed files at the original locations, and verifies the app's
signature before restoring it. A retry accepts files already restored by an
interrupted recovery. Once restoration releases the installation lease, it
resumes the shortcut service if that service was running before uninstall.
The receipt is persisted before stopping the service. Forced process-exit tests
pass on Linux and macOS; candidate 9 also verifies real launchd restoration from
a completed uninstall using the packaged uninstaller.
