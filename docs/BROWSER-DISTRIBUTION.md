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

## Normal Linux sandbox qualification

Linux native-host launchers clear inherited `LD_LIBRARY_PATH`, `LD_PRELOAD` and
`LD_AUDIT` before starting their Python/Node runtime. Chromium's distro wrapper
can export its own private library directory; it must not become Augmentor's
loader path. Debian/Fedora and Arch/Leap package recipes and the source registrar
apply this boundary only to the browser host. Direct runtime/desktop verification
still rejects unreviewed loader overrides; source-Qt controls generate their own
verified Qt paths afterwards. Browser/host manifests and identities are unchanged.

Set `AUGMENTOR_PROOF_NORMAL_SANDBOX=1` for the isolated
`scripts/browser-composable-proof.py` run as an ordinary user, with
`AUGMENTOR_PROOF_HEADED=1` for a graphical session. Set
`AUGMENTOR_PROOF_BROWSER_BINARY`, `AUGMENTOR_PROOF_APP_ROOT`,
`AUGMENTOR_PROOF_EXTENSION` and `AUGMENTOR_PROOF_NATIVE_HOST` to the exact native
browser, installed application, matching unpacked extension and canonical
installed host launcher. Use a writable fixture copy of the test scripts for
their outputs; keep the installed payload unchanged.

This mode removes the test's historical `--no-sandbox` flag and refuses root.
It also checks `chrome://sandbox` and actual CDP-reported renderer processes:
seccomp filter mode2, no-new-privileges, fixture browser ancestry and distinct
PID/network namespaces. The diagnostic page describes expected renderer status;
it cannot substitute for process evidence. Missing renderers, unreadable
namespaces or inherited namespaces fail acceptance. The normal mode records
`browser-sandbox-proof.json` and attaches renderer evidence to the completed
composable Browser report. Legacy container runs retain their explicit disabled
sandbox flags and do not qualify this requirement.

For owned QEMU qualification VMs where the ordinary user cannot read renderer
namespace links, `AUGMENTOR_PROOF_SANDBOX_SUDO_PROC=1` enables a narrowly scoped
read-only collector. It verifies the VM marker, calling UID, private fixture
profile and process ancestry before accepting namespace evidence from `/proc`; it changes no browser,
kernel or desktop settings. Production installation does not invoke this test
collector. Chromium rewrites Linux process titles into one space-joined string;
the collector labels those flag tokens separately from original NUL-separated
arguments, and requires a whitespace-free fixture profile.

This proof remains separate from manual Load unpacked, branded Chrome,
Snap/Flatpak native messaging, audio and desktop consent/input acceptance.

### October 3 installed XWayland command acceptance

[The current checkpoint](../release/qualification/next-targets/20261003-installed-browser-xwayland-and-clean-artifacts.json)
records clean423 installed Leap release5 with clean368 proof scripts: normal
headed XWayland command exit0, all Pi page/clipboard/branch/edit/prompt/report
assertions and reconnect without replay, exactly8 fixture model requests,
59.00seconds under the explicit90-second VM budget. Six actual renderers retain
seccomp/no-new-privileges/distinct PID/network namespace isolation. Earlier
30-second failures and the completed-but-hung diagnostic remain historical.
The extension matches all65 archive members; no installed payload overlay is used.
DSH Browser, fresh shared onboarding and physical hardware remain separate.

Native Wayland's CDP clipboard assertion fails despite sandbox/page success.
An observed Copy button click through the owned virtual tablet writes the
correct OS clipboard; its diagnostic later misses the short confirmation tick.
This is partial evidence, not full native Wayland acceptance. The exact Chromium
[Wayland clipboard implementation](https://raw.githubusercontent.com/chromium/chromium/154.0.8037.57/ui/ozone/platform/wayland/host/wayland_clipboard.cc)
uses compositor input serials when setting a selection; whether that explains
all behavior remains under investigation. Public qualification scripts never
infer a passing clipboard result from a UI tick alone.

### Native Wayland observed input

[The real-input diagnostic](../release/qualification/next-targets/20261003-native-wayland-browser-real-input-diagnostic.json)
passes the unchanged public assertions after one observed virtual-tablet Copy
click: normal native Wayland command exit0, six sandboxed renderers, exactly8
fixture model requests and57.10-second recovery without replay. This private
pause diagnostic does not replace fresh source-bound maintained qualification.

`AUGMENTOR_PROOF_WAYLAND_INPUT_SECONDS=30` or `60` requests a bounded pause before
the first Copy action, only in headed normal-sandbox Wayland mode. The proof
writes `outputs/browser-wayland-input-ready.json` with the exact proof hash,
fixture identity, browser PID and viewport. An external observer can verify the
current UI and use ordinary input or the dedicated VM's guarded virtual tablet.
Retain that screenshot/input receipt separately; the pause itself does not
prove input occurred. All subsequent real clipboard and behavior assertions
remain unchanged. Default0 is unchanged. Never use owner hardware or assume a
stale ready file belongs to the current run: match PID, fixture and proof hash.
The explicit pause is test instrumentation, not a product permission setting.

### Explicit native Wayland qualification

`AUGMENTOR_PROOF_OZONE_PLATFORM=wayland` requires a headed ordinary-user normal
sandbox run in an observed Wayland session. The proof verifies a real socket
owned by that UID in its private session runtime directory, passes its absolute
path as `WAYLAND_DISPLAY`, and removes `DISPLAY`/`XAUTHORITY`. The fixture keeps
its own separate runtime and state paths, and uses `wl-copy`/`wl-paste` for real
clipboard checks. This follows the [Wayland client API](https://wayland.freedesktop.org/docs/html/apb.html),
which accepts an absolute compositor socket path independently of `XDG_RUNTIME_DIR`.
Successful XWayland runs do not qualify this mode; actual native Wayland Browser
acceptance remains pending. The latest installed package/reconnect limits are
recorded in [the rollout checkpoint](../release/qualification/next-targets/20261003-leap-browser-loader-upgrade.json).

The default reconnect proof waits30seconds. `AUGMENTOR_PROOF_RECONNECT_SECONDS=90`
is an explicit emulated-VM measurement mode; reports record both the budget and
elapsed time. Product timeouts are unchanged. The Leap diagnostic restored its
edited session after55.51seconds without replay, while its original30-second
failures remain. Its clipboard fixture held SSH stdout after the assertions;
clipboard providers now use detached output and exact private-state cleanup.
This diagnostic alone does not qualify full Browser acceptance or customer
recovery latency.
