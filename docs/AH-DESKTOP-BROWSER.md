<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Select Augmentor Harness in Desktop and Browser

Desktop **Settings → More → Connections & Home → Agent engine** and Browser
**Settings → Harnesses → Browser harness** offer **Augmentor Harness** (`ah`),
**DSH**, the retained **Pi (legacy profile)** and Codex development integration.
AH is the default when there is no saved engine choice. Explicit saved choices
(including DSH and named DSH entries) remain available. A busy or
mutating conversation cannot switch owners. Workspace-embedded Browser profiles
keep their registered engine and do not acquire standalone harness switching.

AH is the installed Augmentor Harness, not a renamed legacy Pi installation.
On MX, the connection follows the existing login controller's explicit review
selection and verified launcher. It uses that entry's socket, model catalog,
working folder and shared prompt/memory stores. On macOS, the adapter reads the
installed `com.augmentor.Harness` LaunchAgent's explicit environment and current
release selection. That adapter has authored metadata-fixture coverage; physical
Mac Desktop/Browser adoption is not qualified by the MX proof. Windows discovery
and installed adoption remain a separate platform gap.

Before any action, the client performs the Pi protocol handshake and compares
the owner's reported profile directories and product version with the selected
AH. Native reconnects revalidate selection; Browser pins its selection for the
connection. Missing/changed installations and mismatched owners fail visibly.
Only a connection failure during health/startup can invoke the existing AH
launcher. No conversation operation is retried, no bearer is copied into browser
storage, and an unavailable AH never creates an empty legacy Pi profile.

Desktop stores its current AH conversation under that AH state's
`clients/desktop/session.json`, with existing per-window scoping. Browser uses
separate `-ah` session/model keys; old DSH, Pi and Codex keys are retained.
Switching engines does not migrate or replay a conversation. The Pi SDK remains
the one execution owner; the surface adapter does not introduce a second loop.
Existing AH surface presets retain their supported `augmentor-*-pi` identities.
Library and memory clients use AH's shared stores; memory provenance continues
to use the owner's `pi:` conversation identity. Plugins still execute under AH's
capabilities and surface policy; adding a backend does not expose every plugin
GUI inside the floating app or Browser sidebar.

The explicit `AUGMENTOR_AH_CONNECTION` operator adapter accepts a private owned
`augmentor-ah-connection/1` JSON record containing `root`, `version` and `profile`
(`config`, `state`, `socket`, `workspace`, `sharedState`, `sharedData`). It contains
no credentials and cannot specify an arbitrary startup command. Such profiles
must already be started by their owning installer. It is used for authored
integration fixtures, not as a substitute for normal installation discovery.

## Qualification on October 20, 2026

Source checks include strict TypeScript validation, private IPC wrong-owner and
changed-selection refusal, missing/offline-profile no-fallback, preference/chat
restoration and separate Browser engine keys. An actual Qt composer and Browser
native-messaging bridge both obtain replies through the supported Pi SDK and an
authored local provider, then restore without another request. Both use the same
owner PID. These are real SDK/transport tests with synthetic model responses,
not claims about physical voice or arbitrary provider compatibility.

The actual registered MX AH additionally passed metadata-only profile, catalog,
history and prompt-library reads without generating an owner conversation.
Installed activation is recorded separately below; source changes alone do not
change the working Desktop, loaded Browser extension or selected AH artifact.

## Preserve the current MX application contract

The working Desktop is product **0.2.11**, with a retained direct Handy overlay,
whereas the Harness source branch is **0.2.13**. Replacing the whole application
would break its matching DSH integration contract. The bounded
`scripts/ah-surfaces-compat.py` recipe instead accepts exactly the recorded
`90bc1347…c9d9669f` base and ports the selectable AH client paths. It preserves
the old release/extension versions, DSH integration, legacy runtime, voice/Handy
dependencies and all unrelated application bytes. The recipe requires the
managed scratch workspace and must pass exact-candidate checks before normal
immutable deployment staging/activation. It is not a general version bypass.

## Installed MX adoption — October 20

Client implementation **c3a5f24f** is installed on the preserved 0.2.11 contract
in release **20261020-115207-13c2cdc3**, artifact
`0bae0f1bfe3758ff06527c65564fe62fb29fc3bcd6e7d8fb344249836be4142b`.
The exact inventory has 29,033 inputs, with 30 application paths changed or
added from the recorded compatible base. The current Handy source and binaries,
DSH integration, product/extension versions and unrelated files are retained.
The first disposable check found missing platform transport modules; explicit
source/dependency closure corrected the recipe before sealing or activation.
Failed scratch mirrors were removed by the managed workspace helper; one sealed
candidate was retained and selected. Required old rollback and live Mobile remain.

The normal installed updater verified the seal and matching authenticated DSH
integration before activation. Primary Desktop was idle with no draft, accepted
its existing guarded close and reopened normally on this artifact. It reports
online/model-ready, voice available, no restore error and no pending update.
Its previous DSH choice remains selected until the user chooses AH. The live
Mobile window remains on the compatible previous build with an update pending;
it was not interrupted for this Desktop/Browser request.

An isolated presentation window using the exact installed Desktop and **actual
registered AH** reached online/model-ready and exposed AH plus DSH through the
normal Settings panel. It made no conversation or prompt request. The installed
managed Browser launcher likewise completed the actual AH handshake, catalog
and initialization without creating a conversation or sending a prompt. AH's
runtime, startup selection, existing model settings and histories were retained;
normal owner activity may continue changing their state during observations.

The already installed Chromium extension contains custom code beyond the base
release. Only five files (`state`, `port`, `settings`, `panel-api`, `voice`) were
patched for the AH paths; all 50 other files and the manifest/key/version remain
byte-exact. A private original-folder backup is retained alongside the previous
desktop selection. The actual patched Settings page passes a DOM selection and
status test; its real state module passes separate AH/DSH/Pi restoration checks
against the installed companion. The older two-engine variant initially missed
the AH status label; that targeted UI test caught it before folder adoption.

**Reload Augmentor once in `chrome://extensions` if Chromium was already open**,
then open Browser Settings → Harnesses and select Augmentor Harness. The loaded
owner extension's reload/visible sidebar has not been observed. A fresh native
companion process is verified; this does not claim that a running service worker
has already loaded new code. No Chrome profile, extension ID, saved chat/model
key, owner tab or draft was replaced. DSH remains selectable.

Qualified checks: source eight Python adapter cases, twelve Controller cases,
ten actual Qt settings cases, one prompt-companion startup case, 34 shared
Browser composer/queue/settings cases, the new Settings DOM case, three private
Browser backend cases, the existing native-host compatibility case, and the
actual Qt/Browser SDK reply-and-restoration integration. The compatible ordinary
candidate passes eight Python/four Node cases against the exact existing sealed
AH runtime on an authored provider; the final installed candidate repeats the
stronger normal-Settings SDK proof. No real provider inference, physical voice,
Mac/Windows deployment or whole hosted-CI pass is inferred from these checks.

[Portable deployment evidence](../release/ah-desktop-browser-20261020.json).

## Settings navigation and selected browser opening — October 20 follow-up

The installed Settings trap was reproduced from its service traceback and with
an exact-artifact Qt regression: `HomeDialog.connect` and `.disconnect` buttons
shadowed QObject methods. Connecting the embedded dialog's `finished` signal
raised a TypeError, leaving the settings editor attached and every exit failing.
The buttons now use distinct names. Editor attachment happens after its signal
connection succeeds, avoiding that partial lifecycle state.

**More → Open harness in browser** follows the current controller. AH and legacy
Pi request `harness.open` from their attested owner and validate the returned
loopback credential link; DSH retains its registered browser-opening route.
An asynchronous result from a previously selected controller cannot open the
wrong backend. Models & providers remains separately available for AH/Pi.
The engine picker resets to the actual selection when switching is refused and
refreshes backend-dependent menu/access settings after a switch.

Common Qt tests cover Home → More and Home → Back. The real SDK/Qt fixture now
uses the actual engine picker to switch an authored initial DSH client to the
real AH adapter, opens Home and leaves via More/Back, requests a real runtime
browser link, reopens Settings, sends a composer prompt, and restores the AH
conversation. The initial DSH client and provider response are synthetic; the
Qt widgets, AH owner, SDK, IPC and browser URL issuance are real. Browser tests
also verify AH as the no-saved-choice default while retaining explicit DSH.
These fixes share the native UI across OSes; installed MX qualification is
recorded below, with physical macOS/Windows adoption still outside this rollout.
