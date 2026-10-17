<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Native settings recovery for the MX Harness transition

The replacement Native client must keep the owner's existing settings interface
before it can participate in the shared DSH/Pi transition. The feature branch
previously had an older flat modal dialog. This source restores the existing
inline Agent, Look, Voice and More panel; it does not update the installed app.

The panel retains identity/avatar and Agent Identity drafts, scoped memory,
access revision checks, named DSH agents, shortcut rollback, model entry choices,
Prompt Library, connection/setup, recorded token history, updates and support.
Current host bindings retain Handy, shared appearance publication, normal Quit
and the existing Pi Trajectory/Context inspector. Inspector availability follows
the current session/connection/capabilities. No new voice service or placement
is introduced. Windows/macOS adapter code is retained, not newly qualified here.

Settings opens inside the existing frame. Returning keeps the original composer,
unsent text, history and chat geometry. Unsaved identity/editor changes refuse
closing or compaction until resolved. Open settings counts as busy for maintenance;
a prepared maintenance reservation cannot open it. Zoom keeps the settings frame
within its screen/touch bounds and restores chat dimensions at the selected scale.

Named independent agents keep their DSH instructions, permissions and working
folder. Presentation ownership requires the registered preset **and** folder,
excludes subagents and does not grant personal memory ownership. Archived bindings
remain readable; active interactions require a current binding. Entry renaming
and model changes preserve session identity; role/folder changes retain the old
binding and use a new state key. A later in-chat model choice survives reopening.
The current workspace/profile checks and product-version/home checks remain.

## Public provenance

These are public **Augmentor** source selections under their existing repository
license, with copyright/SPDX retained. They are not newly copied DSH code.
The canonical public GitHub commit/content identities were verified. No private
repository baseline, owner configuration or installed generated module is copied
into public source, tests or CI. The installed module was read only for comparison.

| Selection | Public revision | Use |
| --- | --- | --- |
| `agent_settings.py`, `token_usage.py`, `services/usage/history.mjs` and their tests | [41e04412678f77e45c85f339161ba7572d6a843c](https://github.com/ManoloRemiddi/augmentor-agent/commit/41e04412678f77e45c85f339161ba7572d6a843c) | Existing settings body, layout, local token calendar/reader and regressions |
| `scripts/stage-native-agents-overlay.py` | [98a961ae6cbad56358575e65f8f1b9668205fbc9](https://github.com/ManoloRemiddi/augmentor-agent/commit/98a961ae6cbad56358575e65f8f1b9668205fbc9) | Only its nine literal panel substitutions, evaluated against the public body |
| `agent_entries.py` | [ef2d7f233d4fb4f567388d6c21c80bd20bb3fd66](https://github.com/ManoloRemiddi/augmentor-agent/commit/ef2d7f233d4fb4f567388d6c21c80bd20bb3fd66) | Registry/state retention/managed launch |
| `agents_settings.py`, DSH adapter/controller additions, two shortcut helpers, `desktop-entries.mjs` and registry tests | [98a961ae6cbad56358575e65f8f1b9668205fbc9](https://github.com/ManoloRemiddi/augmentor-agent/commit/98a961ae6cbad56358575e65f8f1b9668205fbc9) | Named-agent UI and presentation boundary; selected public test only, unrelated preset-boundary test excluded |
| `services/identity/profile.py`; `paint_energy_ring` only | [eef21cf23866a21e5bfafd36adeffd1d82465388](https://github.com/ManoloRemiddi/augmentor-agent/commit/eef21cf23866a21e5bfafd36adeffd1d82465388) | Shared identity store and existing avatar painter; current VoiceButton remains |
| Inline Window host methods | [41e04412678f77e45c85f339161ba7572d6a843c](https://github.com/ManoloRemiddi/augmentor-agent/commit/41e04412678f77e45c85f339161ba7572d6a843c) | Selected open/close settings methods, preserving current maintenance/setup/inspection and draft cancellation |

The base panel's public Git blob is
`12554f9ff5a1f9ca598f97b5ac6c915bcdedea2c`, SHA-256
`4b374a2bb7ecdfbb4abeefa887f88afab4160106bde2f9d097c84f4261e259e4`.
The public recipe blob is `1afa2218024487951033f09b5d52276cc949dc1d`.
Applying its `replace` function and nine top-level panel replacement calls produces
SHA-256 `69a793cf700473d6a622800eb78fc8e835550d6b04fe55022eb1fe93d773eb9a`.
**Do not run the recipe's complete overlay**: its unrelated baseline `copytree`
is not a public-source reconstruction. The generated public body differs from the
installed module; it is not described as an exact public installed blob.

`settings_host.py` is independently authored glue using existing current public
Window/DictationSettings/Appearance APIs. Its Quit/Handy/appearance/inspector
bindings, preview null handling, dynamic inspector state and zoom/maintenance
integration are distinguished from the historical selections above. DSH branch
scope additions intersect the current workspace gate; they do not replace it.

## Qualification and remaining work — October 17, 2026

Local **134 Python / 20 Node** cases pass, zero failures/skips, plus `npm run check`.
The Python total is 106 settings/Window/scaling/branch/shortcut/maintenance/retained
voice-control cases plus 28 Controller/readiness/remote cases. The seven host
cases include actual Qt widget interactions, dirty drafts, in-frame setup,
maintenance refusal, live inspector state, light/dark readability and zoom.
The initial 105-case group was green; after the zoom correction its affected
45-case Window/scaling/host group passes again. These overlapping reruns are not
added to the distinct total. Offscreen light/dark screenshots of the actual
preview Window were inspected; they are **authored preview evidence**, not owner
backend, physical desktop or installed adoption acceptance.

All local app/test work used the one-workspace helper with the real 64 GiB reserve,
read-only host filesystem and separate network/PID namespaces. No full app mirror,
sealed artifact or owner-data copy was created. A concurrent scratch attempt was
refused as designed and rerun after the active workspace had finished. The current
CI Linux SDK installs the hash-locked same Qt 6.8.2.1 test wheels and runs the
106-case Native group; hosted terminal results belong in the qualification record.
One legacy shortcut failure test now explicitly isolates its XDG data directory.

The installed Native client and main/pilot Harness remain unchanged. This is a
source parity prerequisite, not a completed shared-backend cutover. Next: verify
remaining current-client deltas, map all real callers/data roots, couple the
qualified cold backup to matching-client selection and durable finalization/reverse,
then qualify one combined immutable artifact and owner continuation. Keep the
[storage workflow](HARNESS-BUILD-STORAGE.md); no further project transfers before
pilot feedback, and VR-RasterStudio stays in DSH. Voice and later OS rollout remain
deferred. See [integration activation prerequisites](HARNESS-DSH-INSTALLATION.md).
