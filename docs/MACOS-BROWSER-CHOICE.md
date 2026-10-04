<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Choose an installed Chromium browser on macOS

The earlier setup hard-coded Chrome and Chromium and could not configure Comet.
The replacement discovers browser applications in system/user Applications and
one organizational subfolder, and provides a native app chooser for other
locations. It validates HTTP/HTTPS browser handlers and Chromium framework
resources, then opens the exact chosen app's Extensions page. Users can prepare
another browser without reopening setup. Safari is not a Chromium browser.

Comet 153 uses Chrome's `Google/Chrome/NativeMessagingHosts` compatibility location
even though its browser data is in `Comet`; an actual native-message exchange
verified this exception. Registration for other apps uses Chromium's
`CrProductDirName` metadata when provided. Otherwise
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

## Qualification and artifact

The release candidate is a clean archive of source
`3627daebbfe88a3f9adc92f2566575b343655b7e` (product 0.2.12). It contains no personal
profiles or credentials. The pinned Python/Qt environment passed all 130 Mac
tests, including the installed-app chooser, malformed apps, metadata/path
validation, Comet compatibility registration, preservation, uninstall and restore.
The [Mac 14/26 workflow](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36328849465)
also passed at that exact source.

| Artifact | SHA-256 |
| --- | --- |
| DMG, 528,906,168 bytes | `d31488baf9e07329d5f07f62f3f51052bc990d6e3f638dfa33856aa62d0ec694` |
| Build ZIP, 339,781,018 bytes | `a77f6158fa3e7691a3e546895eb6fd4b265376bf1d714e610f6d28e6e72d96cb` |
| Application inventory, 592 entries | `9474ee18fa69b9b1ede2e8f555164c3db82d4a56ec6f0b3646266cf5f4fb98df` |

Actual Comet 153.0.8010.191 on the 32 GB Mac and Chrome 153.0.8010.53 on the
16 GB Mac both pass the packaged native-host/DSH conversation test against an
isolated deterministic provider. Each proof also passes native desktop Send,
Enter after reopening, conversation restoration, required-plugin setup, DSH
restart and strict bundle verification after use. This is not a live personal
provider test or manual browser installation approval. A separate Comet check
confirms `chrome://extensions/` renders its Extensions manager. The Cocoa setup
dialog discovers installed Comet and Brave applications; layout inspection
caught clipped instructions, now corrected with a larger minimum text layout.

The DMG passes checksum, read-only mount/copy, launch through LaunchServices at
a path with spaces/Unicode, native runtime, DSH integration and post-use seal
checks. Developer ID/notarization, Apple Open Anyway approval and the manual
browser folder chooser remain outside this qualification. Preview limitations
from the earlier release still apply.

### Corrections exposed by qualification

The interface proof accepts `AUGMENTOR_PROOF_BROWSER_APP` and isolates both the
browser home and Cocoa's `CFFIXED_USER_HOME`. Comet's native-host lookup does not
follow `--user-data-dir`; the first profile-only fixture reported "Specified
native messaging host not found". A direct native-message probe and then full
Comet chat established the compatibility location above. Temporary probe
registrations were removed. Disposable browser shutdown now uses `Browser.close`
and a bounded fallback for the owned test process; this avoids reporting a
successful chat as a failure when browser termination takes longer than 15 seconds.

An early operator inventory command omitted Python's `-B` flag and added four
standard-library cache files to its test copy. That copy was not promoted.
Fresh archive extractions and all final proofs pass strict signature checks.

The Linux workflow at the binary source encountered an unrelated `ENOTEMPTY`
race while removing the observation fixture's Chromium profile. The test now
retries transient directory removal after the parent exits; three local real
Chromium runs pass. The full Linux/Home/Browser/installed lifecycle and Mac 14/26
workflows passed at reviewed head `114a879` before merge.
No Linux production behavior changed.

## Deployment checkpoint

[PR #17](https://github.com/ManoloRemiddi/augmentor-agent/pull/17) is merged as
`9451682`. [Preview 3](MACOS-PREVIEW-3-RELEASE.md) is published, its complete
anonymous DMG download matches its checksum, and the website serves the new
installer and browser-choice guide. The owner's installed app is still `b8dac9d`:
its open dialog makes maintenance busy, and
macOS refuses remote Accessibility control. A request to close that dialog is
pending. Do not force-quit or claim the installed update is complete. The sealed
replacement is staged separately, with test application registrations removed
from LaunchServices. Activation must preserve saved appearance, models and
conversations, then verify one canonical app, one Dock tile and its running build.

## Primary references

- [Chromium macOS product directory implementation](https://chromium.googlesource.com/chromium/src/+/main/chrome/common/chrome_paths_mac.mm).
- [Chrome native messaging registration](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging).
- [Comet quick start guide](https://www.perplexity.ai/comet/resources/articles/comet-quick-start-guide).
