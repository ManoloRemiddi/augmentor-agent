<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# macOS distribution implementation

The owner authorized implementation and isolated testing on the network Macs on
25 September 2026. The shared Qt application and canonical repository remain the
product foundation. This work supersedes the old Mac packaging baseline for the
files it changes; historical acceptance records remain evidence of their own builds.

## Delivery contract and sequencing

### September 26 publication audit

The request to publish a macOS download prompted a fresh check of release
requirements. Both network Mac minis have **zero valid code-signing identities**;
Gatekeeper rejects the current canonical development app. An Apple Developer
web login alone does not install a Developer ID certificate or authorize
notarization. No signing secrets are configured in this repository's GitHub
Actions settings. A certificate request and its private key have been prepared
privately on the 16 GB Mac; neither belongs in this repository.

The macOS 14/26 bundled-runtime CI checks for `ea7b116` passed, but the Debian
recovery proof failed because its isolated legacy profile omitted the preset
that readiness now verifies. The proof now supplies that preset and explicitly
selects it. The real local proof passes stopped-host startup, unexpected-host
recovery and legacy-history repair; production readiness checks were not weakened.

The personal Mac installation is not a fresh-user installer. Guided managed DSH
provisioning, provider setup, required plugins, release licensing, browser and
update qualification remain separate release work. Do not publish the personal
profile, credentials, development ZIP or a Gatekeeper-bypass guide as a consumer
download. The website still serves its existing Linux preview.

The intended public experience is a Developer ID signed, notarized DMG: drag the
application into Applications, open guided setup, connect a model and approve the
browser extension in its store. Required Python, Qt, Node, DSH and plugin code
travel with the desktop release. Large optional engines/models and durable user
data stay outside the signed app. An advanced external DSH connection preserves
the user's installation and has a separate update-ownership contract.

Weekly desktop updates should notify, then install and restart when the user
chooses. Browser/store updates happen independently, requiring a versioned wire
protocol and a tested transition from today's exact-version clients. One shared
manifest and lifecycle policy should serve Linux, Mac and later Windows; package
replacement and OS integration remain platform-specific. Existing Linux installed
selection and running services are unchanged by this development work.

Before broad setup/refactoring or public updater integration, close four gates:

1. Native entrypoint, stable permission attribution and a viable signed Qt layout.
2. Complete prepared runtime, with real tool paths exercised from the bundle.
3. Safe task/process shutdown and two-version updating, including recovery.
4. Store identity/policy, protocol migration and durable draft persistence.

The first implementation closes parts of gates 1 and 2. It is **not a public
release** and does not claim the other gates have passed.

## Implemented foundation

- The desktop and helper entrypoints are compiled Mach-O binaries. The launcher
  embeds the pinned Python through `PyConfig` instead of replacing the desktop
  process with a shell/interpreter. `sys.executable` still selects the bundled
  Python for independent services. Interpreter environment injection and bytecode
  writes are disabled. Library lookup is relative to the relocated bundle.
- Microphone purpose text is present in the app metadata. This is preparation for
  actual permission tests, not evidence of permission approval or persistence.
- The Mac Python manifest now includes sounddevice/PortAudio loading and CPU ONNX
  runtime dependencies. `macos-requirements.txt` pins the actual ARM64/universal
  wheels by hash. Old base-interpreter package metadata is removed during staging.
  Model provisioning, acoustic echo, hands-free and physical audio are unqualified.
- `stage-dsh.py` installs the complete locked production DSH graph during the
  build with npm lifecycle scripts disabled. It validates installed versions and
  executes only the reviewed, hash-checked helper-permission preparation. It
  emits a dependency/lock inventory and runs real native-dependency checks.
  That inventory explicitly leaves license review incomplete.
- The bundle contains DSH's capability definitions and license, the complete
  staged DSH tree, and the prepared runtime on the launcher's PATH. It does not
  silently initialize or overwrite an external DSH profile.
- Production staging now retains Pi's keyboard helper for the actual target OS.
- `package-macos.py --dmg` additionally emits a read-only development disk image
  with an Applications link. ZIPs remain available for inventory/CI checks. Artifact
  reports explicitly list outstanding release gates.
- A separate `macos-feasibility.yml` workflow builds/tests on ARM64 macOS 14 and 26.
  It uses pinned actions/tooling, hashed wheels, real native launcher tests,
  bundle inventory validation and actual DSH/Qt with a local model fixture.
  The workflow is development qualification, with no distribution credentials.
  It retains JSON reports only; binaries stay out of public CI downloads while
  the distribution/license gates remain open.

The launcher uses [CPython's isolated initialization API](https://docs.python.org/3.12/c-api/init_config.html).
Apple's [permission-attribution guidance](https://developer.apple.com/forums/thread/678819)
motivates the native entrypoint. Native embedding alone does not establish how
browser-launched voice or other helper processes receive TCC permissions.

## Reproduce on an ARM64 Mac

Use an isolated source checkout, writable output directory and build environment.
Apple Command Line Tools are a developer prerequisite; end users must not need them.
The current standalone Python comes from pinned uv 0.11.16's managed interpreter
catalog. Pin the interpreter archive itself before claiming full reproducible
release provenance. Node is independently checksum-verified by the app builder.

```sh
uv python install 3.12.13
uv venv --python 3.12.13 .macos-build-env
uv pip install --python .macos-build-env/bin/python3 --require-hashes \
  --only-binary :all: --no-deps -r release/macos-requirements.txt
# Run npm with Node 24.19.0, matching release/macos.json.
npm ci --ignore-scripts --no-audit --no-fund
npm run build
.macos-build-env/bin/python3 scripts/package-macos.py --dmg --out outputs/macos
.macos-build-env/bin/python3 scripts/verify-macos-application-inventory.py outputs/macos
.macos-build-env/bin/python3 scripts/macos-bundle-proof.py \
  --artifacts outputs/macos --out outputs/macos-installed-proof
```

The output directory must be new/empty. Do not patch or rebuild a selected app
in place. Changing the Python dependencies requires updating both the manifest
and the wheel lock, followed by actual Mac qualification. Build scripts currently
produce **ad-hoc development signatures**; their success is not Gatekeeper,
Developer ID, Hardened Runtime or notarization acceptance. Do not disable Gatekeeper
to turn an internal test result into a consumer-installation claim.

The bundle proof uses a graphical Mac login, a fresh mounted-image copy in a path
with spaces/Unicode, LaunchServices, native tools and the real DSH/Qt integration.
It retains the isolated copy and evidence on success or failure. Final signature
verification is required after using the app; launch success alone is insufficient.
It does not register login/browser integrations or connect to a live model.

## September 25 test evidence

Source baseline: `43acb1dd5ffe303d5224ac69b38fd6003402fdd8`, with changes on
`feat/macos-distribution`. Tests used an isolated directory on an ARM64 Mac mini
running macOS 26.5.1, plus the existing Linux test host. No installed Linux release,
live model settings, speech placement or existing Mac login/browser registrations
were changed. Model fixtures use disposable profiles and loopback endpoints.

- Real compiled launcher test passed on Mac: process identity, relocation with
  spaces/Unicode, hostile Python environment isolation, literal argument delivery,
  exit status, independent child interpreter and no bytecode writes.
- Mac-specific regression suite passed on both platforms (56 cases at the initial
  checkpoint; the native-only case skips on Linux). The added wheel-lock check
  increases the current suite to 57. Three staging rejection tests cover changed
  preparation code, dependency drift and a mixed DSH suite.
- Staged DSH proof passed on Mac and Linux: native FFI, ripgrep, shell pipeline,
  ordinary child-group termination, and PTY input/output. These are actual local
  processes, not mocked calls. Arbitrary detached-child containment remains open.
- Candidate 3's full DSH/Qt fixture passed from bundled code/interpreters using
  Cocoa: profile-preserving setup, owned integration refresh, refusal to overwrite
  edited presets, saved chats, approvals/rejection/cancellation, user questions,
  shared personal-agent/browser flows, exact historical fork and no replay after
  lost acknowledgement. It made 16 local deterministic model requests.
- The native app opened and produced its own window screenshot. Its seal passed
  after ordinary preview launch. The subsequent full DSH fixture invalidated the
  seal: directly started prompt/memory child services wrote bytecode. `PromptClient`
  now passes `-B` explicitly rather than depending on the app launcher's environment.
  A real subprocess regression test verifies this with bytecode enabled in the
  ambient environment. The affected candidates are not accepted artifacts.

Candidate 3 ZIP SHA-256:
`9bdb57c7b7572206f53261f5e9e705c731782bf43f9a307f1cf85610b8adc825`
(397,883,495 bytes). Application inventory SHA-256:
`c1fd6876e408ebb6e5ba3573660cd5e89de0108c75e4a3d089c35ea941531180`.
It predates the final wheel-lock/DMG metadata additions; retain its evidence as
that intermediate checkpoint. A later artifact is qualified separately.

### Accepted development checkpoint: candidate 5

After the child-interpreter correction, `macos-bundle-proof.py` passed against a
fresh DMG copy: image/ZIP inventory verification, LaunchServices window capture,
spaces/Unicode relocation, native FFI/search/shell/PTY, full DSH/Qt fixture and
strict signature verification **after all use**. This establishes development
bundle integrity and functional fixture behavior, not production signing or TCC.

| Identity | Value |
| --- | --- |
| DMG SHA-256 | `3847884a2dd653186f6be85921d50dc13a84cc655d48dead5c35e9124dfd17b0` |
| DMG bytes | 593,483,965 |
| ZIP SHA-256 | `d41c2f6d65281f005bad71c5ea4737de52daaef5685b7d550f86b6731ed7b261` |
| ZIP bytes | 397,891,719 |
| Application inventory SHA-256 | `1019bdb77bc0fd86f297f3f3d4883a4fe4134f084579408b71fdd344afb2a002` |
| DSH lock SHA-256 | `6c125583876657a5eaf97b95acaff9a820ff9e0214e06cba219b2154a274ea10` |

The DSH fixture cleanup now terminates both of its private socket services using
kernel-authenticated peer identity, without process-name searches or accidentally
starting services during cleanup. The retained candidate is unchanged by that
external test-driver correction. Repeat mounted-image qualification passed with
the corrected cleanup, and no task-owned fixture services remained running.

Final local Linux native regression: **442 tests, one environment skip, passing**.
The system Python lacked QtTest, so this run used an isolated test environment
with matching PySide6 Essentials/shiboken 6.8.2.1; the installed application and
system packages were not modified. Mac-focused regression: **57 tests passing**,
plus three staging rejection cases and the real child-bytecode regression.
The full DSH/Qt fixture also passed on Linux with the corrected service cleanup.
GitHub's new OS matrix is an additional pending check, not evidence already claimed
by these local results. This checkpoint is still product version 0.2.12 development,
not a new published product release or a consumer-ready installation.

## September 26 clean installation and default shortcut

The owner reported multiple Finder application entries and unreliable opening.
The audit found development candidates, installed qualification copies and a
backup still registered as applications. The Mac also had no assigned default
shortcut; the native helper did not accept Fn. The previous chat-only checkpoint
therefore did not establish a clean, usable installation.

Implementation `6ecda87` changes the following:

- New installs prefer writable `/Applications`; updates retain an existing app
  in `/Applications` or `~/Applications` and refuse an ambiguous default when
  both exist. Moving an app still requires migrating its integration references.
- Update staging and rollback directories are hidden and end in `.noindex`.
  New backups have a `.backup.noindex` suffix rather than `.app`; interrupted
  transactions using the older naming convention remain recoverable.
- The shared SVG supplies a complete native `.icns` and `CFBundleIconFile`.
  Finder/Dock activation shows the window; repeated native launches also show it.
  Explicit shortcut activation toggles visibility without creating another UI.
- A fresh packaged launch automatically registers the per-user login service
  with Fn+Space. Carbon registers Space (49) with `kEventKeyModifierFnMask`
  (131072); it does not require an Accessibility event tap. Settings exposes
  one Mac shortcut and a dedicated button to restore Fn+Space. Existing custom
  choices and deliberate removal of a saved choice's login registration remain
  respected. Cold shortcut activation uses the installed native executable.

On the 16 GB ARM64 Mac mini, the only installed application is now
`/Applications/Augmentor Agent Desktop.app`. Thirteen redundant application
bundles and their stale registrations were removed during consolidation. The
desktop app symlink was removed, and the existing Dock tile was repaired to
point to the canonical app with its product icon. DSH's owned LaunchAgent,
profile dependency link, presets and product plugins were migrated through
the ownership-checking setup path. Personal model configuration, credentials,
conversations and unrelated applications/services were preserved. Private data
backups and a compressed recovery application remain outside the installed app.
Time Machine backups were not altered.

Installed acceptance uses actual native processes and real DeepSeek requests:

- Icon activation while visible, while hidden, and from Finder raised the same
  primary process. The shortcut activation path hid and showed it without
  changing its conversation or composer. No test prompt was sent in the owner's
  existing primary conversation.
- A separate named native test window passed Send, restart/restoration, and Enter.
  After the final bundle update it restored that same test conversation and
  produced another real model response through its installed proof driver.
- A real in-place update chose the existing canonical destination, retained a
  hidden rollback bundle, and resumed the previously running Fn+Space service.
  Explicit service stop/start also restored the binding.
- Cold launch through the shortcut activation code reopened the native app,
  connected to its saved model and displayed one window. AppKit identified the
  canonical bundle. Normal launch rejected UI test control. Strict recursive
  signature verification passed after use.
- Finder's Spotlight query returned one app, and Dock preferences contained one
  Augmentor tile. No browser native-host manifest or loaded unpacked extension
  referenced the removed development directory.
- Linux native regression ran 451 tests with one environment skip, followed by
  20 passing focused installer/settings tests covering the final destination
  selection and Mac Fn settings. All 61 Mac contract tests passed on the Mac.
  Shipped native/services/scripts/adapters file
  hashes match the committed implementation.

Final development ZIP SHA-256:
`edd55f4548702c428d8f8ac8714d62436ffc2d931460ab7745ca4ef832bdc0dc`.
Application inventory SHA-256:
`c3444a7cc3df3c5dcaa19665b3ff26f80c2f5dcbd59d154f9009239608032751`.
The final app is left running normally, with test control disabled. The simple
desktop instruction file identifies the sole app and Fn+Space.
The completed development workspace and expanded update backup were removed
after preserving private recovery data and the compressed prior application.
Do not recreate loose qualification `.app` copies in indexed user folders;
build into `.noindex` staging, qualify the canonical installation, unregister
temporary app records and remove task-owned scratch files after acceptance.

**Evidence boundary:** macOS accepted the real global Fn+Space registration and
the activation/cold-launch paths passed, but no physical Fn+Space keypress or
logout/login was performed remotely. Accessibility and screen-recording grants
remain absent; they were not bypassed. This is a corrected personal development
installation, not acceptance of a mass-market release. Developer ID/notarization,
guided fresh-user setup, coordinated weekly updates, browser/voice qualification
and the other release gates remain open.

## September 26 follow-up: corrected primary Mac app activated — historical location

The owner requested autonomous completion. The corrected app is now installed in
`~/Applications/Augmentor Agent Desktop.app`, with a desktop shortcut to that
exact copy. DSH was checked for active sessions, stopped through its owned
LaunchAgent during replacement, then restarted. Its private profile, model
credentials, default selection, catalog and conversations were preserved.

The old qualification process had intercepted launches because it held the
primary instance socket. To preserve any unsent draft without requiring the owner
to dismiss its dialog, its own IPC hid the window; the idle process was then
paused and its socket/lock moved aside. Configuration and DSH data were backed up
privately. This obsolete process retains its draft **only in memory until reboot**;
its private recovery checkpoint records how to restore the old socket/lock after
closing the replacement. Do not resume it while the replacement primary is active.
This is a one-time development recovery, not the production update design.

The native launcher now supports an explicit `--ui-test-control` qualification
flag. Its existing owner-only Unix socket can inspect that window, capture only
its pixels, and type/click Send or press Enter through Qt. Submission refuses
existing drafts, active work, hidden windows and open dialogs. Normal launches
reject these test commands. It cannot run arbitrary code or control other apps.
The [live proof driver](../scripts/macos-live-chat-proof.py) accepts
`--native-socket` to use this mode and checks the running application's root to
detect an older process intercepting the launch. It never retries a submission
whose acknowledgment was lost.

Actual installed primary-window evidence, not a separately imported Qt window:

- The native executable opened the installed copy through LaunchServices.
- Typing and clicking Send displayed the real DeepSeek reply
  `The installed Mac app works.` with no setup dialog.
- Closing and reopening the native app, without an explicit harness argument,
  restored the same conversation. Enter submission displayed
  `The reopened Mac app works.` in that same session.
- A subsequent **normal launch without test control** reconnected, restored the
  same session and reported online/model-ready with no connection/restore error
  or blocking dialog. A test-control request was explicitly rejected.
- A named native-window check also exercised the checked-in socket proof driver.
- Strict recursive signature verification passed after actual use. Native
  regression passed 448 tests with one environment skip.

Activated development ZIP SHA-256:
`0e76a1240a1f921b45ffe754d6745819a6e2705d05e37485adca9db5c45b5686`.
Application inventory SHA-256:
`8619a3db827adbe01d2b70c6015848fa17c3fb8fe7f64493024d703e40fad000`.
The primary app is left open under its normal launch mode. Apple notarization,
voice/browser setup, other provider inference and physical reboot acceptance are
still separate gates; this evidence establishes installed Mac desktop chat with
the configured DeepSeek provider. The earlier activation-pending checkpoint below
is historical and superseded by this entry.

## September 26 correction: verify chat readiness and the actual composer

The initial personal-connection checks below were insufficient. A successful
backend request and `online`/`modelReady` flags did **not** prove that the already
open desktop could send. The owner reported failure, and it was reproduced with
the packaged Qt window: a controller created before setup retained the legacy
`augmentor-linux` preset after external setup installed only
`augmentor-linux-product`. The window displayed Ready and a model, but Send
returned `agent-presets: preset "augmentor-linux" not found`. Its Connect DSH
dialog also remained open. A fresh controller used the correct product binding.

Desktop host readiness now checks that its selected agent preset exists and is
not broken before reporting online. Missing presets direct the user to Connect
DSH and Save and use DSH, which reconstructs the controller. The check does not
silently switch an existing conversation's role or replay a failed prompt. The
setup fixture uses raw host availability before installation and checks full
desktop readiness afterwards; these are distinct contracts.

The opt-in [live Mac chat proof](../scripts/macos-live-chat-proof.py) drives the
packaged production Qt window through the composer and Send button or Enter,
using a named test window and a real configured provider. It checks that no dialog
blocks the composer, verifies the product binding, waits for the rendered reply,
and captures only that window. It can require the earlier reply after reopening.
This is a separate widget-driver process using bundled application code; it does
not automate a different, already-running window or certify OS input permissions.
Use `--live` only when a real provider request is intended.

Candidate qualification (product 0.2.12 development):

- Linux native regression: 445 tests, one environment skip; missing/broken preset
  and supported legacy preset cases are covered.
- Mac live Send-button proof displayed `Mac desktop button verified`.
- Reopening the same named window restored that conversation; Enter submission
  displayed `Mac desktop Enter verified` in the same session.
- Full packaged DSH/Qt fixture passed 16 deterministic requests, including setup,
  approvals, exact forks and unknown-acknowledgment non-replay.
- Strict recursive development-signature verification passed after use.
- Candidate ZIP SHA-256:
  `bbe4f5f7d8f14046ed4858ad05da1c289bdcb64c6b9866137234350aad079288`.

At this checkpoint the corrected candidate is staged and tested, **not activated
in the owner's already-open window**. That older process still has a dialog open.
Remote Accessibility and screen capture are not authorized on this Mac; the owner
was asked to close the old window while preserving any unsent draft. Do not claim
the user's open window is repaired until the corrected app is actually activated
and its conversation path checked. This supersedes the earlier chat-readiness
claim, not the verified provider catalog and backend-response evidence below.

## September 26 personal Mac model connection

The owner requested that the test Mac use the same model access as their MX
workstation. This is a private development deployment of source `c03c32e`, not a
new binary release or implementation of the public first-run wizard.

A verified copy of the existing development app is in the Mac user's
`~/Applications`. A separate, private `~/.dsh` profile uses that app's bundled
Node/DSH runtime. Supported setup installed and checked the matching Augmentor
integration and saved the connection in the Mac's Application Support directory.
Per-user development LaunchAgents start DSH on numeric loopback and maintain a
dedicated SSH tunnel to the workstation's two model ports. The tunnel has its own
key, destination restrictions and a pinned workstation host key. Existing
workstation DSH services and unrelated Mac tunnels were left running.

Only provider settings, required model credentials, the default selection and
model-picker preferences were transferred. Source conversations, browser login
credentials and machine-specific plugin composition were not copied. Model Picker
Augmented 1.1.2 and its JavaScript dependencies were installed outside the sealed
app. Credentials use DSH's existing owner-only local file storage; this does not
qualify the planned Keychain integration. Private settings, secrets and machine
addresses are intentionally absent from this repository and public artifacts.

Observed acceptance:

- Exact provider/model identifier comparison: **365 models across seven providers**,
  identical to the workstation, with matching default selection and no catalog
  failures. Catalog membership is not a successful inference test of every model.
- A fresh Mac DSH conversation using the Augmentor preset and DeepSeek Flash
  returned `Mac DSH connection works.` from a real provider request.
- The existing desktop reported `online: true`, `modelReady: true`, no connection
  error and no restored-session error. Its open process remains on its prior
  qualification copy; the staged user Applications copy is for subsequent launches.
- The Mac tunnel reaches the active workstation Qwen model endpoint. The secondary
  GPU endpoint refused connections on the workstation itself; its catalog remains
  available but inference there requires that workstation service to be started.
- The staged app still passes strict recursive signature verification. This is
  its original ad-hoc development signature, not Developer ID qualification.

A short start guide was placed on the Mac desktop. DSH and tunnel startup were
verified through launchd; a physical reboot/login acceptance test remains open.
Voice, browser extension installation and the other public release gates below
are not established by this model-connection check.

## Remaining gates and next work

The accessible build Mac has no valid code-signing identity. Developer ID
Application credentials and notarization access must be provisioned through the
owner's Apple developer account before production identity/upgrade tests. Never
commit certificates, private keys or account secrets to this repository.

Work still required before public release:

- Resolve signed code layout, entitlements, Qt corresponding-source/replacement
  delivery and the complete DSH/native-library license inventory.
- Test permission identity from Finder, login and browser-first operation across
  two signed versions, including denied/revoked permissions and Keychain.
- Build the managed first-run wizard, runtime/profile ownership and supervision;
  bundle/qualify Model Picker, Adaptive Reasoning and Resonant Voice integration.
  Existing external-DSH setup is not the finished no-terminal setup flow.
- Introduce durable drafts and acknowledged-send state in both surfaces, a
  compatibility protocol, legacy migration and final store extension identity.
- Prove process quiescence and update admission/drain before integrating Sparkle.
  The pinned DSH Mac provider cannot guarantee cleanup of arbitrary escaped
  descendants. An idle native connection is not active work; a stopped parent
  is not proof that all children stopped. Silent install-on-quit stays disabled.
- Qualify optional Mac voice/memory, Docker networking, model downloads and minimum
  hardware resources; preserve existing Linux provider/model placement.
- Complete signed DMG/notarization, clean-user/oldest-OS acceptance, real browser
  installation, failure recovery, manual replacement and external beta.

The build and runtime proofs reduce uncertainty without changing those release
requirements. A screenshot or an ad-hoc signed ZIP is not a completed installer.
