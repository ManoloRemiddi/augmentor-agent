<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Managed Mac first run

This is source implementation and isolated fixture qualification, not a public
release or a change to the owner's working Mac. It addresses the basic
runtime/model bootstrap gap found in the [publication audit](MACOS-DISTRIBUTION.md#september-26-publication-audit).

## User flow

A fresh bundled Mac desktop with no saved DSH connection offers **Set up
Augmentor**. The user supplies an OpenAI-compatible API address, model name,
API key and context window. **Connect** sends a short model test, creates a
private runtime profile, installs the checked product integration, starts a
login service and reconnects the desktop. This path needs no separate DSH,
Python or Node install, terminal command or manual DSH restart.

The app must first be copied into `/Applications` or the user's `Applications`
directory. **Use existing DSH** retains the external connection form. A saved
connection keeps using that form; managed setup refuses to adopt or replace it.
The initial form supports OpenAI-compatible chat APIs. Other protocols, OAuth,
provider editing and required extra-plugin provisioning remain separate work.

Opening an app from a disk image or temporary build folder must not register a
login shortcut pointing at that temporary path. Automatic shortcut bootstrap now
requires an Applications location before creating a new login registration;
an already-running shortcut owner remains available. The focused regression
verifies refusal before the registrar can run. Signed mounted-image user-flow
acceptance is still required.

The form blocks duplicate submissions and dismissal during setup, refuses an
active conversation action, preserves fields on failure and clears the key on
success. The desktop reconnects only after the service and product presets pass
their checks. The GUI sends configuration through private subprocess stdin;
an unknown worker result is not automatically replayed.

## Ownership and lifecycle

`scripts/setup-macos.py` reuses the complete installer's model settings and
checked integration bootstrap. That bootstrap gained `save=False`, allowing
the Mac to prepare integration without selecting a stopped temporary host.
Linux keeps its existing default behavior.

Default data lives under
`~/Library/Application Support/Augmentor/data/augmentor/managed-dsh`:

- `home/`: DSH settings, profile, presets and conversations;
- `runtime.json`: private API key and runtime environment;
- `setup.json`: owner, endpoint, phase and connection fingerprint;
- `setup.lock`: cross-process setup exclusion;
- private bootstrap/runtime diagnostic logs.

The profile links the app's prepared DSH dependencies. First run neither invokes
npm nor downloads a second runtime or changes the signed app. It is independent
of `~/.dsh`. Ownership and links are checked. The API key is stored **without
encryption** in a mode-0600 file inside a mode-0700 directory, consistent with
the existing private configuration contract; this is not Keychain storage.
Secrets are absent from the LaunchAgent plist, process arguments and public
reports. Provider error bodies are not copied into the GUI.

The per-user `com.augmentor.Agent.DSH` LaunchAgent uses the bundled interpreter
and Node, starts at login and restarts after failure. Its helper restores the
private provider environment and holds the application lifetime lease. Recovery
recognizes the saved `managed` owner and restarts that job instead of spawning a
detached runtime without credentials. Advanced reconnection to the same profile
retains the ownership descriptor.

The host uses launchd's **Interactive** process type because it handles chat and
tools that the user is waiting for. Apple's [launchd policy documentation](https://github.com/apple-oss-distributions/launchd/blob/main/man/launchd.plist.5)
applies restrictive resource limits to Background jobs. The earlier source
descriptor used Background; this correction does not modify the owner's separate
development service. A private `startup-check.json` records elapsed time, attempts,
integration readiness and the last redacted check error on success or failure.

Bootstrap starts a temporary owned host, installs product integration, restarts
to validate it, then stops that host. The persistent service must become healthy
before shared connection settings are saved. Failed setup stops only its own
unpublished service and retains private state for retry. Existing jobs/profiles
and concurrent connection edits are preserved. Interrupted acknowledgements can
finish a matching running configuration without rewriting it or starting another
runtime. An incorrect provider key can be corrected and retried.

`launchctl bootout` can acknowledge removal before its job finishes exiting.
Cleanup now waits for disappearance before replacement or file removal. This
does not establish containment of arbitrary detached user tools or close the
coordinated updater/drain gate. Update, uninstall of this runtime owner and
whole-bundle migration still require qualification.

## Evidence

Local Linux regression passed **475 tests, two Mac-only skips**, before the final
three focused recovery/provider-error tests were added. The final managed backend
suite has twelve cases; the actual Qt form has three. Fourteen of those passed
on the 16 GB ARM64 Mac before the last provider-error test was added.

The subsequent timeout/retry test brings the backend suite to **thirteen**, all
passing on Linux and the 16 GB ARM64 Mac. It verifies that readiness failure
does not select a broken connection, stops the unpublished job, redacts the key
from private diagnostics and permits a successful retry. The Interactive-service
proof completed provisioning in 10.62 seconds, including 3.394 seconds of
persistent-service readiness checks, then passed chat, restart and restoration.

The real Mac proof used an isolated profile, prepared bundled DSH/Node/Python,
a uniquely named real LaunchAgent and a deterministic HTTP model. It verified
model availability, a completed DSH chat, repeat setup without another bootstrap,
service stop/start and restored conversation. Three fixture requests occurred.
The temporary login job was removed and fixture prompt/memory socket peers were
stopped through kernel-authenticated same-user identity. No owner's model,
conversation or login service was used.

```sh
QT_QPA_PLATFORM=offscreen PYTHONPATH=apps/native python3 -m unittest discover \
  -s tests -p 'test_macos*setup*.py' -v
python3 scripts/macos-managed-setup-proof.py \
  --app-root '/path/to/candidate/Contents/Resources/app' \
  --out '/path/to/new-proof-output'
```

The proof calls the provisioning library in private source/runtime staging;
the production entrypoint still requires an installed Applications location.
Qt tests exercise real widgets with a fixture worker. This does not establish
an end-user click-through from a quarantined, signed DMG. The Mac CI matrix now
runs the real managed-service proof against each newly built bundle and verifies
its signature afterward; pending CI must not be described as passed.

At source `4fdd8a4`, [both Mac runners](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36234652550)
and [full validation](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36234652564)
passed. The preceding `7f03e17` run passed macOS 14 but timed out waiting for the
managed service on macOS 26. Its logs did not establish the cause. A later pass
does not prove that intermittent failure resolved. Failure excerpts now contain
only synthetic fixture logs, and CI retains the report even when a step fails.
The scheduling correction is independently appropriate; do not attribute the
earlier timeout to it without supporting evidence. These runs precede that
correction and are not its qualification.

The correction at `81f3726` subsequently passed its own
[macOS 14/26 matrix](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36235276970).
Provisioning took 25.899 seconds on macOS 14 and 28.897 seconds on macOS 26;
persistent readiness took 8.036 and 9.577 seconds respectively. Both completed
chat, repeat setup, service restart and conversation restoration, removed the
temporary services and passed the post-use signature check. The additional
pre-correction [repeat matrix](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36235021154)
also passed, so the original isolated timeout remains an unresolved reliability
observation, not a demonstrated scheduling diagnosis.

The same `81f3726` source passed
[full validation](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36235276975),
including the Linux, installed-package lifecycle, Browser and Home jobs.

The owner's canonical app remains the earlier development artifact. See the
[release guide](MACOS-RELEASE.md) for Developer ID/notarization, signed installed
acceptance, extra plugins, browser, voice/memory, licensing and update gates.

## Preview plugin and browser follow-up

The managed profile now enables the locked Model Picker, Adaptive Reasoning and
Resonant Voice packages alongside DSH’s web bundles. Voice initialization creates
only missing private configuration; speech models are separate. The browser setup
menu prepares a stable external extension folder and native-host registration,
then leaves final Load unpacked approval to Chrome/Chromium. See the
[preview release record](MACOS-PREVIEW-RELEASE.md) for distribution scope.
