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
