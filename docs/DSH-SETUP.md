<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Optional DSH connection

Install and start the supported Node DSH CLI **0.1.5-rc.1** separately. Its `dsh`
command must be on the application's PATH. Configure your model in DSH. Augmentor
checks the CLI's first-party packages, the host API, its integration version, and
a local pairing token; it does not copy the developer's providers or credentials.
The checked CLI supplies dsh-base/dsh-tools 0.1.5-rc.1 and schemastery 3.18.2.
The bridge uses Augmentor's bundled ws 8.21.0. DSH's own dependencies remain
separately installed and owned by DSH.

In Linux Settings choose **Connect DSH**. In the browser select DSH and use the
connection icon. Enter a numeric loopback URL and your existing DSH data folder
(default `~/.dsh`). Choose **Check connection**, then **Install integration** when
needed. For a fresh unpaired DSH instance, paste the complete local URL printed
by `dsh web`, including its token, into the URL field. Only the clean origin is
saved; authentication stays local and needs no DeepSeek account. Finish current DSH tasks first. Restart DSH, check again, and choose
**Save and use DSH**. The checked endpoint/data folder are shared by both UIs.

Installation owns `augmentor-linux-product` and `augmentor-browser-product`
presets and one composition insertion. The original profile text is preserved,
with a private backup. The browser role has an execution guard against OS tools.
Both presets mount the same optional memory tool; explicit memory retention and
its data controls stay in Augmentor's shared settings.

Future integration refreshes validate recorded file and preset hashes before
replacement, keep the old integration and preset contents, and avoid duplicating
the composition entry. Edited presets or composition entries require migration;
they are not silently overwritten. Legacy/custom Augmentor integrations are
preserved and need a separate migration review. The preview's guided path is
verified on a fresh supported DSH profile, not arbitrary hand-edited profiles.

DSH holds a runtime lifetime lease while this integration is loaded. Close DSH
before package maintenance, even if its chats are idle. Reopen it afterwards and
refresh/check the integration when Augmentor requests matching versions. An
integration connection failure never resubmits a prior task.

`scripts/dsh-setup-proof.py` uses a disposable DSH home and actual Qt controls.
With `AUGMENTOR_PROOF_BROWSER=1` it also runs Chromium against that host, verifies
page contents and preserved branch/edit context, and sends forbidden native
requests directly to verify role and update boundaries. The model responses are
deterministic fixtures; this is SDK/integration evidence, not model-quality
certification.

## Current DSH 0.1.5 limitations

The native and browser transports use authenticated Typert RPC and scoped session
streams. Model Picker Augmented **1.1.2** is the compatible optional DSH plugin;
its pins and visibility are shared by both DSH surfaces. It does not curate Pi or
OpenCode catalogs.

DSH approvals/questions are completed in DSH's authenticated web UI. Edit or a
historical branch is refused before mutation if DSH's fork would inherit a queued
input beyond the requested turn. This preserves the original conversation and
avoids replaying the old input. Pi/OpenCode Edit remains available. See the
[cross-platform and public-release plan](CROSS-PLATFORM-RELEASE-PLAN.md).
