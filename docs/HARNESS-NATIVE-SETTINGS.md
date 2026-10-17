<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Native settings recovery for the MX Harness transition


## Retain the existing provider during the client update — October 17

The matching Native client now carries forward the existing provider selector,
configuration/vault handling and provider-specific session implementation. This
restores behavior required by the working client; voice expansion remains deferred.
The four complete modules come from verified public
[51272530](https://github.com/ManoloRemiddi/augmentor-agent/commit/512725304a16a62a3f24acb0e3bfbdd1f8b16235)
and [c1b2279a](https://github.com/ManoloRemiddi/augmentor-agent/commit/c1b2279a2267850e6c52be72e632479ac916a031).
Their exact blobs and hashes are recorded in the qualification receipt. Selected
public Window/Controller/button hooks retain current Pi close/cancellation,
conversation, submitted-content and maintenance behavior; private installed source
is not copied. The existing Voice settings entry opens the retained provider hub,
while local voice controls stay available inside it. No additional UI redesign.

Cloud preparation keeps the chosen model and existing session and never requests
or closes a Pi local speech ticket. A pending Pi retirement still blocks opening.
Cancellation before/after ticket creation is checked. Spoken submissions keep their
provider prefix and emit one acceptance/uncertainty receipt; typed lookalike IDs
remain typed. No automatic retry is introduced. Local Pi opening identity, buffered
manual input, close joins and typed/spoken distinction retain their current tests.
Provider polling waits during maintenance; an admission race resets the polling
flag, and settings jobs keep the window busy until their callbacks settle.

The focused combined **201 Python cases pass**, zero failures/skips, including eight
new adaptation cases and selected public provider/audio/vault/settings tests.
An isolated repeat with the product's hash-locked **websocket-client 1.8.0** passes
all 201; the initial development-environment run used 1.9.0. Qt is 6.8.2.1.
Sockets, audio streams, vaults and provider replies are synthetic. The test process
has a read-only host filesystem and isolated network; no microphone, real vault,
external API, owner model or service is used. This is existing-protocol retention,
not new verification of an external API or physical speech. The Linux SDK Native
step now includes this group using its existing locked dependencies.

No installed app, launcher, saved provider, credential or GPU/service placement was
changed. Tests use one managed scratch and the actual 64 GiB reserve; no full app
copy or immutable release was created. Next bind real bootstrap/all-client adoption,
matching selection and durable finalization/reverse to one cold checkpoint, then
qualify one combined candidate and actual continuation. Pilot feedback still gates
further projects; VR-RasterStudio remains in DSH.


The replacement Native client must keep the owner's existing settings interface
before it can participate in the shared DSH/Pi transition. The feature branch
previously had an older flat modal dialog. This source restores the existing
inline Agent, Look, Voice and More panel; it does not update the installed app.

The panel retains identity/avatar and Agent Identity drafts, scoped memory,
access revision checks, named DSH agents, shortcut rollback, model entry choices,
Prompt Library, connection/setup, recorded token history, updates and support.
Current host bindings retain Handy, shared appearance publication, normal Quit
and the existing Pi Trajectory/Context inspector, Reasoning and MCP controls. Inspector availability follows
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
| `agents_settings.py`, DSH adapter/controller additions, two shortcut helpers, `desktop-entries.mjs` and registry tests | [98a961ae6cbad56358575e65f8f1b9668205fbc9](https://github.com/ManoloRemiddi/augmentor-agent/commit/98a961ae6cbad56358575e65f8f1b9668205fbc9) | Named-agent UI, label/preference/history bindings and presentation boundary; selected public test only, unrelated preset-boundary test excluded |
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

## Retained progress, thinking and current cold-cut map — October 17

The next source checkpoint retains the working clients' observed request stages
and saved thinking preference. It is source work, not an installed update. Public
[request-stage source d943ad2](https://github.com/ManoloRemiddi/augmentor-agent/commit/d943ad299883dad458f854ae7db815cf1eb06348),
[thinking preference d4ab5fd](https://github.com/ManoloRemiddi/augmentor-agent/commit/d4ab5fd739e33e7fe3c6b1c270b863ced54d84dd)
and the public 41e0441 callback dispatcher supply selected Native/Browser behavior.
Their public commit/tree identities were verified. Private installed methods were
compared in memory, not copied; request observation and thinking completion match
the known public implementations. Voice-provider expansion remains deferred.

Native labels identify actual validation/create/model/subscribe/send/accept work,
then observed turn/request/stream openings. First reasoning/text replaces the
waiting label; completion, failure, idle and the originating handled-input receipt
clear it. Old generations cannot restore a later label. These transient labels
are not conversation history, inferred queue positions or model internals.
Current branch identity, queue, cancellation, permission and submitted-content
safeguards remain. Open is the retained default while reasoning streams; the saved
per-window choice and manual controls work, and completed thinking collapses.
The existing inline Conversation control now persists that choice.

The Browser restores the same public progress presentation and primary Native
thinking preference, while keeping SDK workspace storage isolated. Acceptance is
bound to its original pending draft so a late acknowledgement cannot mark a new
conversation accepted. Handled-input receipts clear only their own wait without
inventing a user/model message. Current scoped submitted-content and unknown-outcome
behavior remains. A source regression asserting the old standalone completion
behavior was updated to assert completion collapse **and** subsequent manual reopen;
code-copy and workspace controls remain tested.

Local **161 Python / 24 focused Node / 130 Browser unit** cases pass, zero failures
or skips, plus type checks. Hosted run **39063562845** passes the Native and
transport stages, then fails Browser test imports because the SDK job omitted its
separate test dependency lockfile (`jsdom`). The workflow now uses the existing
validation recipe: `npm ci --prefix apps/browser` and `apps/browser/test`, both with
`--ignore-scripts`. That failure is retained, not a complete SDK pass.
Python comprises 121 Native/settings/shared-preference
cases, 28 Controller/readiness/remote cases and 12 cold-backup cases. The new
Browser/Native stream-opening and late-reply tests use authored data; no owner
model or microphone is used. Full [Linux SDK 39063815081](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/39063815081)
**succeeds** at workflow **222ae6e9** / runtime **889ad6cb**, including the
121-case Native group, 130 Browser units and four focused transport cases.
[Portable qualification record](../release/harness-progress-cut-map-20261017.json).

The current read-only caller map finds three original Native windows idle with no
drafts at observation, 12 known client/companion processes and 35 launcher/registration
files. One active Native Messaging origin resolves to a Chromium extension source
whose **on-disk** manifest is 0.2.11; its loaded runtime version is still unverified.
Do not spoof that manifest to pass the matched 0.2.13 host. A matching extension
adoption/reload must be part of the eventual client transition.

The proposed data coverage contains **21 logical roots / two shared pairs**, about
**7.59 GiB** across **199,279 metadata entries**, largest file 295,408,944 bytes,
with no observed special files. This reads deployment/profile metadata and file
metadata, not database/conversation bodies. It is live sizing, **not a cold cut,
backup or activation authority**. It covers Native settings/session state, both
registered review profiles and registry, shared component files, and both deployment
selectors. Existing program releases, project folders and whole browser profiles
are not duplicated by this plan. External retained modules and engine services
still require their existing preservation rules.

The archive API now accepts explicit `members` for additional roots: 1–64 unique
direct regular filenames. This captures the second deployment's JSON without its
`releases/` or unrelated profiles. It can accompany separately selected nested
profile trees regardless of ordering. Traversal, duplicates, directories and
symlink members refuse; whole recognised mixed deployment roots refuse. Existing
whole logical data trees and archive schema stay compatible. Bootstrap/registration
writes use the existing startup installer's small per-file snapshot/CAS mechanism;
do not copy whole launcher folders or weaken their directory checks just to archive
additional metadata. Exact affected bootstrap paths still need binding before use.

At this preceding checkpoint, the candidate lacked the existing alternate-provider
Window/Controller path. The provider-retention checkpoint above now restores it.
Verified public 51272530/c1b2279a compatibility source is available; carry forward
existing behavior without changing credentials, provider, services or GPU placement.
Exact owner selections remain in private operator evidence.
This preservation prerequisite does not reopen deferred voice expansion.

No owner data, settings, service, selected app or project was changed. All local
checks use the one-workspace helper and real 64 GiB reserve; no full app copy,
sealed release or owner archive was made. Next complete matching selection and
durable finalization/reverse, bind actual caller/bootstrap adoption, then qualify
one combined immutable candidate. Pilot feedback still gates further projects;
VR-RasterStudio stays in DSH. Existing voice services/placement remain, with voice
and later OS rollout deferred.

## Settings checkpoint qualification — October 17, 2026

Local **137 Python / 20 Node** cases pass, zero failures/skips, plus `npm run check`.
The Python total is 109 settings/Window/scaling/branch/shortcut/maintenance/retained
voice-control cases plus 28 Controller/readiness/remote cases. The eight host
cases include actual Qt widget interactions, dirty drafts, in-frame setup,
maintenance refusal, live inspector state, light/dark readability, zoom and retained Pi Reasoning/MCP editors.
The final 109-case group passes after restoring named label/preference/history
bindings and the retained Pi controls. The preceding zoom correction also passed
its affected 45-case Window/scaling/host group. These overlapping reruns are not
added to the distinct total. Offscreen light/dark screenshots of the actual
preview Window were inspected; they are **authored preview evidence**, not owner
backend, physical desktop or installed adoption acceptance.

All local app/test work used the one-workspace helper with the real 64 GiB reserve,
read-only host filesystem and separate network/PID namespaces. No full app mirror,
sealed artifact or owner-data copy was created. A concurrent scratch attempt was
refused as designed and rerun after the active workspace had finished. The current
CI Linux SDK installs the hash-locked same Qt 6.8.2.1 test wheels and runs the
109-case Native group; hosted terminal results belong in the qualification record.
One legacy shortcut failure test now explicitly isolates its XDG data directory.
Hosted run **39060564972** fails at Native test imports because the clean runner
lacked `libEGL.so.1`; it is not a full SDK pass. The workflow now installs
`libegl1` alongside OpenGL and locks the existing Pygments/NumPy requirements
needed by the Native imports. Full Linux SDK **39060753072 succeeds** at **c1475178eaec00dbbdaa77227f1f4c64258f412c**,
including all 109 Native cases. The [qualification record](../release/harness-native-settings-20261017.json)
separates source, preview, installed and owner acceptance.

The installed Native client and main/pilot Harness remain unchanged. This is a
source parity prerequisite, not a completed shared-backend cutover. Next: verify
remaining current-client deltas, map all real callers/data roots, couple the
qualified cold backup to matching-client selection and durable finalization/reverse,
then qualify one combined immutable artifact and owner continuation. Keep the
[storage workflow](HARNESS-BUILD-STORAGE.md); no further project transfers before
pilot feedback, and VR-RasterStudio stays in DSH. Voice and later OS rollout remain
deferred. See [integration activation prerequisites](HARNESS-DSH-INSTALLATION.md).
