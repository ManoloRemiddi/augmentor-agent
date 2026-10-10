<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Browser private-preview distribution

The extension requires the matching Augmentor companion on the same Linux user
account. Pi is bundled; DSH is an optional connection. Install `augmentor-runtime`
from the same artifact set as the extension ZIP. Desktop Qt packages are optional
for browser use. Model credentials belong to the person testing the product.

For a private preview, extract `augmentor-browser-<version>.zip` into a permanent
folder, open `chrome://extensions`, enable Developer mode, and choose **Load
unpacked** with that folder. Open Augmentor, select Pi and complete **Connect
model**. The extension ID must be `dgfpmlnbofacjafljfohgmfacobgfjbh`. Keep the ZIP's
manifest key: native messaging restricts access to that identity.

When upgrading, finish or stop tasks, disconnect Augmentor, prepare the companion
using the [lifecycle procedure](LIFECYCLE.md), and install the matching package.
Extract the new extension into its permanent folder and reload it in the browser.
A mismatched version is refused before requests can change data. Keep a backup of
the old extension directory for the documented package rollback. A reconnect does
not resubmit a previous prompt.

`scripts/package-browser.py` builds the ZIP and `artifacts.json`, including source
commit, dirty status, identity, version, file inventory and SHA-256. Packaging
verifies every ZIP member and the pinned Marked license. The root CI browser job
installs the downloaded runtime package and loads the downloaded ZIP as an ordinary
user in Chromium, with a deterministic local model and no developer configuration.
Its result must pass for the candidate being handed to testers.

### October 10 Pi Harness source qualification

The [loaded Pi Chromium follow-up](AUGMENTOR-HARNESS.md#loaded-pi-chromium-extension) drives the actual MV3 extension, product native host and Pi 1.1.0 against an independently authored synthetic page/provider. It verifies snapshot/type/click/screenshot, identified template-expanded steering, original Chat text, Remove, reload restoration, Stop/paused FIFO resume and exact Branch/Edit without changing the parent. Streaming now preserves the negotiated queue Send button instead of disabling it during each rendered delta. Layout and control placement are unchanged.

Trusted development/companion configuration may set `AUGMENTOR_PI_BROWSER_WORKSPACE` to an explicit Pi Browser working directory. The default remains `~/Augmentor Browser Pi`. This permits isolated profiles without changing the account home; it does not grant new tools or change surface authorization. The candidate's source and staged-tree tests are Linux evidence; a staged tree is not a complete installed package. Mac/Windows Browser, other Chromium distributions, live providers and installed acceptance remain separate qualification.

The [Branch/Edit follow-up](AUGMENTOR-HARNESS.md#harness-branchedit-controls-and-steering-history) scopes Pi inherited delivery IDs to their originating conversation in queue and optimistic prompt reconciliation. Historical parent messages still render. Existing Branch/Edit buttons now reflect connected/idle/submitting and negotiated capability guards; queue Send remains available during supported active turns. This corrects an apparent-enabled action that previously returned without branching/editing. The loaded Codex/Pi fixtures wait for the actual action state instead of using Send as an idle signal. Layout and control placement are unchanged. Exact failed-run, source/staged checks and remaining platform acceptance are in the owning qualification record.

The preview has actual Chromium 152 evidence. Google Chrome, Brave, other operating
systems, and Snap/Flatpak browser isolation remain uncertified until their own
installation and native-messaging tests pass. Do not advertise those combinations
on the strength of registration files alone.

Public distribution requires the publisher's Chrome Web Store account, listing,
privacy disclosures, review instructions and approval. A ZIP is the upload artifact;
this repository does not imply store publication. See Google's
[publishing process](https://developer.chrome.com/docs/webstore/publish) and
[native messaging registration](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging).
Confirm the final store identity and companion allowlist together before release.
