<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Mac preview 3: installed browser choice

[Release v0.2.12-macos-preview.3](https://github.com/ManoloRemiddi/augmentor-agent/releases/tag/v0.2.12-macos-preview.3)
was published on September 27, 2026 at 15:37:17 UTC. It adds installed Chromium
browser discovery and an app chooser, handles Comet's native-host compatibility
location, and keeps setup instructions readable. The shared extension and the
accepted flare/live-size behavior are unchanged.

## Source and artifact

- Clean binary source: `3627daebbfe88a3f9adc92f2566575b343655b7e`.
- [PR #17](https://github.com/ManoloRemiddi/augmentor-agent/pull/17) merged as
  `9451682c49f9b9e75e17e50a80afa58eedd85b5e`.
- Reviewed head `114a879415ee7cbb4ac7a7e3f8f5db1440d53b5c` adds documentation and
  a Linux test-cleanup correction after the binary source. Runtime paths match.
- Product 0.2.12; Apple silicon; minimum macOS 14; ad-hoc signature; no notarization.

| Item | Bytes | SHA-256 |
| --- | ---: | --- |
| Public DMG | 528,906,168 | `d31488baf9e07329d5f07f62f3f51052bc990d6e3f638dfa33856aa62d0ec694` |
| Build ZIP | 339,781,018 | `a77f6158fa3e7691a3e546895eb6fd4b265376bf1d714e610f6d28e6e72d96cb` |
| Application inventory | 592 entries | `9474ee18fa69b9b1ede2e8f555164c3db82d4a56ec6f0b3646266cf5f4fb98df` |

The release has seven assets: DMG, artifacts, build/test evidence, dependency
source links, original source inventory, customer guide and checksums. GitHub's
server-side size/SHA-256 values match all seven prepared files. Qt 6.8.2,
PySide 6.8.2.1, Python 3.12.13, Node 24.19.0 and DSH 0.1.5-rc.1 remain pinned.
Dependency source archives are reused at their immutable preview-1 URLs, with
checksums in `DEPENDENCY-SOURCES.json`. Original source provenance is preserved.
The signed application was not patched during packaging or verification.

## Qualification

Read [browser choice](MACOS-BROWSER-CHOICE.md) for implementation and diagnostics.
The final artifact passes all 130 Mac tests, real Comet 153 and Chrome 153
native-host/DSH conversations against isolated deterministic providers, desktop
Send/Enter across reopening, saved conversation restoration, plugin setup and
service restart. Comet's Extensions manager accepts `chrome://extensions/`.
The Cocoa dialog discovers Comet and Brave; the app chooser is visible and text
fits. These checks do not claim manual browser folder-chooser approval.

The final DMG passes checksum, read-only mount/copy, LaunchServices opening at a
path with spaces/Unicode, native runtime and DSH integration, followed by strict
signature verification. [Mac 14/26 at the binary source](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36328849465)
passed. At the reviewed head, [Mac 14/26](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36329419461)
and [Linux/Home/Browser/installed lifecycle](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36329419458)
all passed. The Linux cleanup fix addresses helper writes racing profile removal;
it changes no Linux production behavior.

## Public delivery and installed scope

The complete anonymous download was verified at 15:47:43 UTC: all 528,906,168
bytes match the published SHA-256 and checksums file. The website was promoted
at commit `b6de0ac`, with download-card wording corrected at `9f27f9b` to show
529 MB and installed Chromium browsers including Comet. Live homepage, Mac guide
and Desktop page HTML matched the deployed source at 15:56:57 UTC. The in-app browser
also opened the Mac guide and exercised the installation-prompt copy button;
it reported successful copying. All 15 website source tests pass. The existing
Linux download and copied install prompt are preserved.

The owner's existing `b8dac9d` app remains online/model-ready. An open dialog
blocks safe maintenance; macOS denies remote Accessibility control, so closure
of that dialog is required before activation. The tested replacement is staged
separately. Temporary qualification app registrations were removed, older test
bundles were deleted, and existing personal models/settings were preserved.
Do not describe the owner installation as upgraded until activation/readback pass.

This remains the owner-authorized unnotarized preview. Apple Open Anyway,
manual extension loading, coordinated updates, complete removal and the other
previously documented release/permission limits remain. No personal credentials,
browser profile or model subscription is included. The builder's stable-release
gates stay visible in `artifacts.json`; they are not a claim that preview tests failed.
