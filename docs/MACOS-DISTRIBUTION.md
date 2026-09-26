<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# macOS distribution implementation

The owner authorized implementation and isolated testing on the network Macs on
25 September 2026. The shared Qt application and canonical repository remain the
product foundation. This work supersedes the old Mac packaging baseline for the
files it changes; historical acceptance records remain evidence of their own builds.

## Delivery contract and sequencing

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
