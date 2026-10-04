<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# macOS release operator guide

**Current preview direction:** The owner approved distribution without Apple
Developer ID after enrollment failed. See [the preview release record](MACOS-PREVIEW-RELEASE.md)
and [customer guide](MACOS-PREVIEW.html). Earlier Apple gates below describe the
intended stable release and historical audits. They do not block the explicitly
approved ad-hoc preview.


**Status: candidate tooling, not a published Mac download.** The personal test
Mac works with its privately configured DSH/model profile. The public product
must work without that profile or any of its credentials. See the
[publication audit](MACOS-DISTRIBUTION.md#september-26-publication-audit) before
using the existing development artifact.

## Apple account prerequisite

An Apple account and a free developer login are insufficient for this release
path. The Account Holder needs an active Apple Developer Program membership to
create a **Developer ID Application** certificate. A Developer ID Installer
certificate is for signed installer packages; this release uses an app in a DMG.
See Apple's [Developer ID certificate instructions](https://developer.apple.com/help/account/certificates/create-developer-id-certificates/).

The September 26 authenticated account check showed “Join the Apple Developer
Program” and “Enroll today”, with no certificate-management access. Enrollment
or another existing member account is required. Do not imply that the earlier
successful web login supplied a distribution identity.

Keep the signing private key on the release Mac or in protected signing storage.
Upload only its certificate signing request to Apple, import the issued
certificate into the same keychain as the matching key, and confirm it appears
as a valid Developer ID Application identity. Never commit the key, certificate
export password, API key or notarization credentials.

Notarization needs separately authenticated credentials. Store them with
`xcrun notarytool store-credentials` using its interactive flow or a securely
provisioned App Store Connect API key. The signing command takes only a Keychain
profile name. A browser login is not a substitute for notarization credentials.
See Apple's [custom notarization workflow](https://developer.apple.com/documentation/security/customizing-the-notarization-workflow).

## Prepare a candidate

Build from the reviewed source using the
[Mac build recipe](MACOS-DISTRIBUTION.md#reproduce-on-an-arm64-mac).
Use a private cache ending in `.noindex` for staged apps, never the Applications
folder, Desktop or an ordinary Finder-indexed source directory. Keep the user's
working app separate. Record source commit, clean working-tree status, build
configuration and application inventory with the candidate.

First inspect the complete native-code plan without changing anything:

```sh
python3 scripts/macos-signing.py \
  '/path/to/build/Augmentor Agent Desktop.app' --plan
```

Then prepare a **new** signed candidate directory on the release Mac. Substitute
the actual certificate SHA-1, Apple Team ID and existing Keychain profile:

```sh
python3 scripts/macos-signing.py \
  '/path/to/build/Augmentor Agent Desktop.app' \
  --out '/path/to/private-cache/release-candidate.noindex' \
  --identity '<Developer-ID-certificate-SHA1>' \
  --team-id '<Apple-Team-ID>' \
  --notary-profile '<Keychain-profile-name>'
```

Omitting `--notary-profile` produces only a signed candidate, with
`notarized: false`. The command refuses an existing output directory, an output
inside the source app, unexpected app identities, escaping/broken symlinks,
unsupported native binaries and a missing or wrong-team signing identity.

The command copies the app and restores the standard framework links omitted
by Python wheel archives. It discards duplicated framework resources only when
their contents match exactly. The original application stays unchanged.

It signs native code individually from the deepest item outward, then signs the
outer app. The Node runtime alone receives the JIT entitlement; frameworks do
not receive executable entitlements. Hardened Runtime and secure timestamps are
required. There is no blanket library-validation or debugging exception.
This follows Apple's [distribution-signing guidance](https://developer.apple.com/documentation/xcode/creating-distribution-signed-code-for-the-mac/).
Actual Developer ID runtime testing may expose additional requirements; do not
broaden entitlements without a reproduced need and a documented test.

Every native file is verified explicitly, including binaries under Resources
that recursive bundle verification may miss. The candidate app is submitted to
Apple, its submission ID is recorded before waiting, and the returned log must
be accepted without outstanding issues. The app is stapled and assessed by
Gatekeeper before the DMG is made. The DMG is then signed, notarized, stapled and
assessed separately. Its reported checksum is calculated **after** stapling.

An interrupted notarization retains its submission record. Check that submission
with `notarytool info`, `wait` and `log`; do not repeatedly upload copies while
the first submission is still in progress. Incomplete candidates retain
`notarized: false` and must not become download links.

`candidate.json` always reports `publicReleaseReady: false`. Signing is one
qualification stage; this tool does not implement installation, release
approval, GitHub upload or website publication.

## Public-release acceptance still required

1. **Clean first run:** a fresh ordinary account with no DSH, Node, Python or
   copied owner configuration must install, configure its own model, send a
   real request, close/reopen and recover its conversation. Basic
   [managed runtime/model setup](MACOS-MANAGED-SETUP.md) now exists in source and
   passes an isolated Mac fixture; signed installed acceptance and required
   extra-plugin provisioning remain open. Keep advanced
   existing-DSH setup separate and preserve its data.
2. **Signed runtime:** repeat the packaged DSH/Qt/native-tool proofs with the
   actual Developer ID build. Test a quarantined browser download on macOS 14
   and 26, including after copying off the DMG and with the network unavailable
   for ticket validation. Verify the seal after use. A fixture or ad-hoc test
   does not satisfy this gate.
3. **Desktop/browser/permissions:** one installed icon; click-to-open;
   physical Fn+Space and login restoration; actual consented screen/input/audio
   paths; the final browser extension identity and matching native host. Voice,
   memory and browser acceptance must match the features the website promises.
4. **Updates and recovery:** user-chosen update/restart with drafts and active
   tasks preserved, coordinated DSH/plugin replacement, failed-update recovery
   and rollback. Weekly release notification and one-click update remain open.
5. **Redistribution:** complete native/DSH/plugin notices and dependency review,
   corresponding Qt sources and a tested permitted library-replacement route.
   The current inventories explicitly do not claim this review is complete.

These are known gaps, not tasks delegated to the end user. Account enrollment is
the owner action; implementation, packaging and testing remain release work.

### Required plugin artifact provenance

The September 26 registry check found that the exact Model Picker 1.1.2,
Adaptive Reasoning 0.2.3 and Resonant Voice 0.1.16 packages are not all available
from npm. A customer setup based on installing those names would fail. The
[published Linux complete release](https://github.com/ManoloRemiddi/augmentor-agent/releases/tag/v0.2.12-complete-preview.1)
already carries reviewed tarballs and a checksum manifest. Their checksums match
the locally retained release artifacts:

| Package | SHA-256 |
| --- | --- |
| `dsh-model-picker-augmented-1.1.2.tgz` | `9a2c2e17c128da3565520b5f39cb85606823440ee0e1e4c2316f806fc58914fc` |
| `dsh-adaptive-reasoning-0.2.3.tgz` | `5c142213e4f7935cf7e8f0ba839e17d274451c689c04637001dd1d89b6da967e` |
| `dsh-resonant-voice-0.1.16.tgz` | `31b1d088cc66ed8eb19f235445407f17d037cc7de938b9cea5049899c5b79cf5` |

The Mac build must incorporate a locked graph for those exact artifacts, retaining
their notices and source provenance, before signing. Model Picker also needs
React and the unscoped `schemastery` package, which are absent from the current
base DSH graph. Do not copy plugin files alone, resolve new dependencies on the
customer's Mac, or ship the older collection's unrelated vulnerable packages.
The current managed profile enables only the prepared first-party web bundles
and shared product integration; it does not yet provision these three extras.
Voice plugin availability does not establish a working speech engine or consented
microphone path. Keep those acceptance checks separate.

## Website cutover

Only after those gates pass:

1. Publish an immutable versioned DMG, SHA-256 file, release notes and required
   source/license artifacts in the canonical app repository. Keep personal
   configuration and test logs out of uploaded artifacts.
2. Download the public URL into a fresh location and check the final checksum,
   Gatekeeper acceptance and actual clean install from those public bytes.
3. Update `augmentoragent.com` in its separate canonical website repository.
   Add a clearly labelled **Apple silicon · macOS 14 or later** download and a
   short guide. Intel Macs are not qualified. Preserve the Linux download.
4. Update all installation prompts that select platform-specific artifacts,
   run the website's link tests, deploy and verify the live page/button and
   final redirected download. Do not use a mutable development ZIP URL.

The intended end-user guide is: download the Mac DMG, drag Augmentor to
Applications, open it, connect your own model in guided setup, then add the
Chromium extension through its approved distribution path. Click the app icon
to open it; Fn+Space shows/hides it. Publish these instructions only when the
release actually provides and passes that flow.

## September 26 tool evidence

The signing inventory read the installed development app and found 253 native
code files. Nine signing-policy tests pass on the 16 GB ARM64 Mac, including an
actual compiled framework normalization/ad-hoc signature check; eight pass on
Linux with that Mac-only case skipped. Tests cover universal binaries, escaping
links, modified duplicate resources, unexpected framework versions, wrong
certificate type/team, source/output isolation and notarization warnings.
All 64 actual bundled Qt frameworks were also copied into a disposable private
cache, normalized, ad-hoc signed and recursively verified successfully. The
copies were removed after the proof; no new app was installed or registered.

The recovery-fixture correction is commit `a4317cd`; its
[Mac matrix](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36231852870)
and [full validation](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36231852874)
both passed. These precede the candidate-signing tooling commit and do not
establish Developer ID, fresh-user setup or public release acceptance.
