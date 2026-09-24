<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Augmentor 0.2.11 security release

This Debian 13 amd64 preview updates Desktop, Browser and their shared runtime
to the security-fixed `ws 8.21.3`. It addresses
[CVE-2026-62389](https://github.com/advisories/GHSA-73jw-fp74-p77x), where incomplete
WebSocket messages can exhaust receiver memory. The Browser pnpm lock also now
matches the existing `fflate 0.8.3` ZIP64 fix. Details, Pi dependency preparation
and regression boundaries are in the [security correction](WS-SECURITY-2026-09-24.md).

## Downloads

Use the [0.2.11 complete preview release](https://github.com/ManoloRemiddi/augmentor-agent/releases/tag/v0.2.11-complete-preview.1)
in the canonical repository. Check `SHA256SUMS` before extracting the complete
archive. The release includes matching runtime/desktop Debian packages, Browser
extension, complete installer, component/source manifests and the npm plugin
tarball. [Fresh installation](COMPLETE-INSTALL.md) includes pinned DSH and the
existing Model Picker 1.1.2, Adaptive Reasoning 0.2.3 and Resonant Voice 0.1.16.
Speech/model settings and optional memory provisioning are unchanged.

The npm package is `dsh-augmentor@0.2.11`, with `ws` pinned to `8.21.3`.
The registry plugin updates only the DSH-side browser tools. It does not replace
an older native companion, desktop or extension. Use the matching complete
product upgrade for those components. The old `0.1.32` download and npm version
are historical and do not acquire fixes when a new release is published.

## Existing installations

Finish active tasks before replacing or restarting the host. Preserve profiles,
tokens, models, conversations, prompt libraries, memory and speech configuration.
The fresh installer refuses an existing setup; do not delete user data to bypass
that protection.

Package-managed Debian users follow [package lifecycle](LIFECYCLE.md) with both
0.2.11 Debian packages, then check/install the matching owned DSH integration in
Settings, restart the idle DSH service, recheck and save the connection. Reload
the matching 0.2.11 Browser extension. Edited presets require a reviewed merge;
never reset them merely to pass the ownership checks.

Managed user-local desktops follow [staged desktop deployment](DESKTOP-DEPLOYMENTS.md):
stage the verified runtime artifact, update the matching DSH integration while
idle, then activate only after authenticated identity/catalog checks pass. Close
and reopen the idle windows through their managed launchers. Confirm running
and selected builds agree; selection alone does not reload existing processes.
Retain the prior artifact and integration backups for coordinated rollback.

## Qualification and publication record

The final artifact source is
[`618012abc8a0055145a0f27b15ac13ac4726a9db`](https://github.com/ManoloRemiddi/augmentor-agent/commit/618012abc8a0055145a0f27b15ac13ac4726a9db),
merged through [PR #5](https://github.com/ManoloRemiddi/augmentor-agent/pull/5).
All three jobs passed in [release CI 35970695316](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/35970695316):
source/native/package checks, installed-package lifecycle, and packaged Chromium/companion acceptance.

Additional final-artifact checks:

- The complete archive installed as a fresh ordinary Debian user in the pinned
  Debian container: real DSH and plugins, private configuration, native Qt render,
  second-window/login entries, matching browser registration and repeated-install
  preservation. This used a fixture model endpoint; optional speech and memory
  engines were deferred.
- The exact npm tarball installed independently and passed real plugin/WebSocket
  round trips with fixture DSH services and browser responses.
- Artifact review verified versions/source identity, archive inventories, native
  binary hashes, license notices and absence of private state files.
- Anonymous GitHub download matched the published complete archive SHA256:
  `657cfaf9b6b2ba35d924db2c0e3759e6aac3bfded2c31f1dae5d0b0a263be8a9`.
- npm `latest` is `dsh-augmentor@0.2.11`, with dependency `ws: 8.21.3`.
  The registry tarball exactly matches the tested package, SHA256
  `4d79a9c83d961fe262f589b81fed13bcb5dafbea1b05e4bfd328d3055b1b4f04`.
- The public release includes `SHA256SUMS`, component `bundle.json` and the artifact
  review. Original archived release bytes remain unchanged.

The website's download links, copied installation prompt and manual now point to
0.2.11 in the canonical application repository. The legacy 0.1.32 install recipe
was retired and historical collection downloads carry an explicit warning.
Website source: `8602c0964bc6f284235f7dbbd2b934bd8da879fa`; 15 website checks passed.

## Installed workstation, September 24

Desktop and mobile selected and actually running:
`20260924-094830-104a6ce4`, version **0.2.11**, artifact inventory SHA256
`8163361aced5a1764111e97e741a8d6082b41c019315192b5b7759f09fe4a0a3`.
Both reported online, speech available, and `updatePending: false`.
The live DSH product and Browser plugin reported 0.2.11. Root/Pi, mobile and the
installed DSH Browser plugin resolve ws 8.21.3; all eight distinct local receiver
regression cases passed. No secondary window was running.

This is a user-local deployment assembled from the tested runtime, matching
mobile files and the previously installed custom Browser policy. It is not a
claim that the older system Debian package was upgraded. The extracted Debian
`release.json` was retained as `docs/source-debian-artifact.json` before staging,
so this independent user-local artifact uses the managed deployment lifecycle
rather than the system package lease/version marker. An initial candidate that
retained the Debian marker correctly refused startup against the older system
package; it was replaced with a separately staged artifact, never edited in place.

The stable mobile and native-host launchers follow `desktop.json`. Owned DSH
integration was updated while idle; existing preset prompts, capabilities and
settings were retained exactly except for remapped owned adapter paths. Models,
GPU placement, speech services, histories and memory data were preserved. The
previous 0.2.8 desktop selection and integration/configuration backups are retained
privately for coordinated rollback; restore both integration and selection when
rolling back across product versions.

The matching Chromium extension is prepared under the user data directory at
`augmentor/browser/0.2.11`, and native messaging points to the selected release.
At the recorded check, the user still needed to load that extension and open the
side panel: the plugin reported zero connected browser pipes. Chromium was not
exposed to this session's browser-control connection. This is an explicit remaining
Browser activation step, not evidence of a live 0.2.11 browser session.

No new real-model answer quality, physical microphone/speaker trial, macOS or
Fedora acceptance is claimed by these release checks.
