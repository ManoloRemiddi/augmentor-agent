<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Guided DSH installation on Mac

## Current correction: runtime first, visible browser access

The earlier technical form below did not solve the owner's usability problem.
On reinspection the installed desktop was still unconfigured: the DSH payload
was bundled, but the managed profile and login service did not exist. Model
validation prevented installation from starting, and Models & providers opened
a bare origin without DSH's browser authentication.

Current source opens **Agent setup** with two separate steps. **Install and
start DSH** needs no provider fields and uses the same managed installer and
ownership journal. It saves the connection only after the service and product
integration are healthy. Model configuration remains in DSH's own
**Settings → Models** interface. The setup explains the first-run DeepSeek
prompt and **Configure later** for other providers. **Check connection** reads
the saved provider/credential availability, not just the built-in catalog.
It does not claim a successful inference request from configuration alone.

The Mac chat window keeps **Agent setup** and **Open DSH** visible. Setup remains
available for a managed installation after first run. Start/Open resume the
recorded launchd owner if needed, without rewriting models or restarting a
running host. Browser opening obtains DSH's current process login token using
the existing authenticated local integration; DSH exchanges it for its own
browser cookie. Tokens are never displayed, copied to the clipboard, or stored
in a new launcher. Every opening requests a fresh token, including after restart.
External connections keep the existing connection editor, with the same corrected
browser handoff. Linux and Pi setup are unchanged.

Verification: focused setup/transport tests, 112 Mac tests and
27 native-window tests have passed on the 32 GB Mac. An isolated real launchd
profile started without a provider in 10.886 seconds. The Browser skill checked
its actual initial screen, preview notice, Models section and provider chooser
through a private SSH tunnel; this was synthetic state, not the owner's account.
A catalog-only assertion initially exposed the distinction between listed models
and configured credentials. A fixture without a key also exposed the pinned
pi-ai adapter's key requirement; the fixture now saves its synthetic credential
through DSH's own credentials API before testing chat.

The following evidence qualified the source/candidate before activation.
The real engine-first proof passed in 11.171 seconds with a credential saved
through the DSH API, completed chat, unchanged repeat setup, service restart,
restored history and fresh browser login after restart. Its temporary LaunchAgent
and shared helpers were stopped. Native Qt renders of initial setup, running DSH
without a model, and persistent chat navigation were visually inspected.
The qualification and activation record below identifies the installed artifact.
The later sections retain historical evidence for the earlier form.

## Qualified replacement and activation

Application source is `60413de`. A separate candidate overlays eleven recorded
application/document files on the earlier public `ea128d6` binary; its exact
application inventory SHA-256 is
`d0461531a8dbb80595b4374e73a39f7bee4b77c5b6ce9727b0e69cc3a1131a0f`.
The final sealed candidate passed engine-first provisioning in 11.786 seconds,
chat with a DSH-stored synthetic credential, repeated setup, restart/history,
and browser login before/after restart. Its integrity still passed after use.
The currently installed older application also retains a valid integrity seal.
The 112 Mac tests were rerun at this source and passed. The 27 native-window
and 11 transport tests passed; the setup tests are included in the Mac suite.

The [Mac 14/26 workflow at `33b58ff`](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36254590085)
and [full validation workflow at `33b58ff`](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36254590084)
both passed. That follow-up changes documentation only; application code remains
`60413de`. The earlier `60413de` runs were cancelled by the follow-up push before
completion. Native Qt screenshots verified setup before installation, running
without a model, and visible chat navigation. Browser UI checks used the Browser
skill and a temporary tunnel; the test tab and tunnel were closed. All owned
fixture jobs and shared helpers were drained. No private model key was copied
from another machine or used in these tests.

### Installed on the 32 GB Mac, September 26

After being told replacement requires closing the old version to avoid losing
unfinished input, the owner explicitly requested installation. The old window
was idle with no open dialog and accepted graceful maintenance closure. The first
installer attempt correctly refused an outstanding application read lease and
preserved the old app. Its holder was an idle Pi runtime from the exact installed
bundle, not another preview. The peer PID, executable and zero active turns were
verified, then its own `host.shutdown` maintenance API drained it. No running
conversation was stopped and other installations were not touched.

The existing installer then atomically activated the candidate at
`/Applications/Augmentor Agent Desktop.app`, retaining the previous bundle in a
hidden backup. It used the previously approved explicit ad-hoc preview mode;
strict integrity checks remained enabled. Neither Gatekeeper policy nor quarantine
attributes were changed. The installed inventory and all eleven source overlays
matched the qualified candidate. Product version remains `0.2.12`, application
source `60413de`, with the inventory hash recorded above.

Using the official launcher's environment, runtime-only setup provisioned the
owner's private DSH profile and registered `com.augmentor.Agent.DSH`. The reopened
native desktop selected DSH, reported online with no connection or restoration
error, and both DSH and shortcut login services were loaded. Installed integrity
passed again after use. The authenticated browser handoff was accepted by macOS's
default browser. This is actual installed service/connection evidence, not a claim
of visual inspection of the owner's browser window.

The owner has **zero configured models** at this checkpoint. They can choose one
in DSH's Settings → Models and then test chat; no live owner-model inference is
claimed. The new visible Agent setup/Open DSH controls are installed. The public
preview DMG remains unchanged, and PR #13 remains a draft.

## Earlier form and deployment (superseded UX)

The 32 GB Mac had the public 0.2.12 preview from `ea128d6`, including DSH,
Node and Python, but no saved DSH connection. The running desktop was offline
with “Use Connect DSH to save the matching local connection before automatic
startup.” No DSH managed profile existed. This was a first-run UX failure, not
an absent runtime binary. The older form said Connect and did not explain DSH
installation. Dismissing it left the ordinary recovery loop reporting an error.

## Behavior

For a Mac without a saved connection or conversation, the native window now
opens **Install DSH** before starting connection monitoring. The same action
remains in Settings if the user chooses Later. The form explains that the
runtime is included and installed automatically, with no Terminal or separate
download. The only required input is the user's model connection; DSH does not
include model weights or a provider account. Context size is an advanced field.

The existing managed installer remains the only installation engine. Its fixed
phase IDs stream through private subprocess stdout to the UI: check model,
prepare runtime, add Augmentor capabilities, start login service, verify ready.
Credentials remain on stdin and in private configuration, never process arguments
or progress text. Duplicate submissions and dismissal during provisioning are
blocked. Failure keeps entered settings and offers Retry setup. An incomplete
acknowledgment does not claim success or automatically replay installation.
The existing ownership journal checks or finishes the same installation on retry.

A saved external or managed connection retains normal recovery and configuration.
An incomplete app copy receives a specific diagnosis and download action rather
than an external DSH form. The install helper also refuses incomplete candidate
payloads before replacement, while permitting an old incomplete destination to
be replaced. Its manifest includes the CLI link used by provisioning.

## Verification and deployment

The 32 GB Apple-silicon Mac (macOS 26.6.2) passed all 109 Mac tests and 27 native
window tests. The installation form was rendered and visually inspected using
the bundled Qt runtime. These tests exercise the actual Qt widgets, missing payloads, preserved external
connections, progress, failure/retry, private credentials and managed-service
ownership. A deterministic model fixture is not live provider evidence.

A separate candidate was staged from the sealed `ea128d6` public preview with
only the ten implementation/document files recorded in its `release.json`
changed. Its application inventory was regenerated and the candidate resealed
with an ad-hoc integrity signature. Application code is from `2fb9a5b`; later
commit `3e88750` changes test cleanup only. This is a scoped candidate based on
the published binary, not a claim of a new clean-build public release.

On that candidate, the real managed-service proof passed in 11.879 seconds,
including all three required plugins, a completed chat, repeated setup without
another installation, service restart and restored conversation. Its temporary
LaunchAgent and prompt/memory services were removed. The real native Window
in an isolated Qt profile opened Install DSH automatically, did not start
recovery, and allowed Later followed by reopening setup. These checks did not
use the owner's credentials, conversation or model service.

The first Mac CI attempt passed its assertions but crashed during interpreter
shutdown with retained test widgets. The test-only follow-up explicitly drains
deferred Qt destruction and uses the canonical module import. This follows
[Qt's event-loop lifetime contract](https://doc.qt.io/qt-6.8/qobject.html#deleteLater).
The [macOS 14/26 workflow at `3e88750`](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36247499831)
then passed completely, including clean packaging, bundled DSH/Qt contracts,
managed chat/restart/history and post-use signature checks. Run bundled Python
diagnostics with `-B` and `PYTHONDONTWRITEBYTECODE=1` (including subprocesses) so
test imports cannot add bytecode caches to sealed apps.
The original app's integrity was restored and checked after archiving such
test-generated caches; no source file or user data was removed.

The broader Linux workflow initially stopped in an unchanged Chromium fixture:
its temporary profile cleanup raised `ENOTEMPTY`. The Mac workflow is independent
and passed. The Linux workflow was retried; that intermittent browser cleanup
failure is not claimed fixed by the Mac setup changes.

At documentation ref `6bead5a`, both the
[full validation workflow](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36247948239)
and [Mac 14/26 workflow](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36247948301)
passed, including Debian, Browser, installed-package lifecycle and Home checks.

## Installed on the 32 GB Mac

After the owner confirmed closing the desktop, the qualified candidate was
installed at `/Applications/Augmentor Agent Desktop.app`. The earlier desktop
does not report or preserve an unsent draft, so its idle flag alone was not
used to close it. An authenticated, same-user prompt-library helper belonging
to that exact installed application was stopped with its graceful shutdown
handler. The installer paused and restored the owned shortcut service and kept
the previous application in a hidden backup. Other preview runtimes were not
stopped.

The candidate uses the previously approved Apple-independent preview policy.
The installer's explicit development mode was required for its ad-hoc signature;
strict code integrity checks remained enabled. No Gatekeeper setting or
quarantine attribute was changed.

Installation and post-install integrity checks passed. All ten changed files
matched the application inventory, whose SHA-256 is
`f36b1ef73e00054adf19982bf515b72c2c1b50b25d0f600be512f21c1af2db76`.
LaunchServices opened the installed native process, the owned shortcut service
was running, and the desktop maintenance endpoint responded with an empty
connection error. The installed application code remains `2fb9a5b` as described
above. The model connection is still unconfigured; live chat on the owner's
account is not claimed. The public `v0.2.12-macos-preview.1` DMG is unchanged.
