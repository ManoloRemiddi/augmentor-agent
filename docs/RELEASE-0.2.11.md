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

The dependency correction passed all three jobs in
[CI 35967395357](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/35967395357):
source/native checks and packaging, installed-package lifecycle, and packaged
Chromium/companion acceptance. The final 0.2.11 release additionally requires its
own passing run, complete-archive install proof and checksum verification.
The final artifact identities and installed-machine result are recorded here
after those checks complete. No physical microphone or model-quality claim is
implied by fixture-based release checks.
