<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Consistent installed desktop releases

## September 22: hide the routine opening reasoning notice

Source `ee5d8f1` adds an exact native transcript filter for the successful
minimal-to-xhigh request-policy notice; see [scope](BOUNDED-EXECUTION-RECOVERY.md#settings-and-progress).
DSH events, reasoning policy, recovery messages and errors are unchanged.
Source checks passed 11 reply/history tests and 12 prompt/command tests. The
separate compatible 0.2.8 candidate passed the same 11 reply/history tests before
staging; no real model request or user conversation was changed for testing.

The candidate copies selected artifact `76c10abd7e98ab6f4bf83ad0a489198d956d9dc6ea9c28a300d94a2aede6db6a`
and applies only the reviewed native window patch. `augmentor-update` staged and
activated release `20260922-145600-eda70a59`, artifact
`16b587ec4cb4cc833a84f9a878782c7efe3ead36c49f755f7ca1e1f5b870fa62`.
Promotion passed installed identity/dependency checks. Desktop, secondary and
mobile still run `20260921-011742-0b89b31a` and report `updatePending: true`.
The main desktop reported active work, so no windows or backend services were
restarted. Close/reopen after work completes, or log in again, to adopt the
selected build. This is tested/selected behavior, not a claim of live-window
adoption. Rollback remains available through `augmentor-update rollback`.

“Latest” means the latest tested artifact explicitly activated for this user.
Saving source files, checking out a branch or building an experiment does not
change the installed app. Startup must not guess by modification time, version
number or whichever preview directory happens to exist.

## One selection

`~/.local/share/augmentor/desktop.json` (under `XDG_DATA_HOME` when set) is the
selection for login, the systemd desktop supervisor, the menu, shortcuts, the
secondary window, recovery and the mobile desktop. The old voice-preview and
login commands are aliases of the canonical launcher. Mobile reads the same
root, Python and Node paths; `--desktop-root` is an explicit development override.
A missing selected build is reported rather than silently choosing an older one.

`scripts/install-desktop-startup.py` bootstraps/refreshes these entrypoints and
installs `augmentor-update`. Once a managed release is selected, the installer
refuses to replace it with another root or interpreter: use the update command.
Installer and updater share a kernel lock so simultaneous promotions cannot race.

## Required development and update workflow

1. Implement and test the change in source. Build a complete runnable candidate
   separate from the selected release. For an incremental preview patch, first
   copy the current artifact to a separate candidate and apply the reviewed
   files there; never copy files into the selected release. Record the original
   artifact identity and the patch commits for such a mixed candidate.
2. Run the subsystem tests and the necessary integration checks. Keep the product
   manifest, installed DSH integration, native dependencies and speech contract
   compatible. In particular, a 0.2.9 source checkout cannot replace the installed
   0.2.8 UI against a 0.2.8 product integration just by changing the launcher.
3. Stage the candidate using the installed command:

   ```sh
   augmentor-update stage /absolute/path/to/tested-candidate --source-ref TESTED_COMMIT_OR_MIXED_ARTIFACT_DESCRIPTION
   ```

   Optional `--python` and `--node` explicitly select new interpreters; otherwise
   staging preserves the selected paths, including the Python venv symlink.
   The command prints a unique release directory.
4. Select the returned release directory:

   ```sh
   augmentor-update activate /absolute/path/printed/by/stage
   augmentor-update status
   ```

5. Report the source reference, artifact hash, selected/running roots and evidence.
   At the next login, all managed surfaces load the selected release. A window
   already open retains its running code until closed/reopened or logout; status
   reports `updatePending` for each such window. Recovery continues to work on
   that window while selection is pending. Do not interrupt active work just to
   make the running and selected roots match sooner.

The stage operation copies the native surface, services, adapters, built runtime,
configuration defaults, licenses, scripts and dependencies into a unique release
folder. It does not copy an entire checkout or user conversations/configuration.
It imports the actual Qt window/controller and checks the Node executable. Its
inventory hashes every regular artifact file and records internal symlinks;
external symlinks are refused because they could silently change a release.
Python bytecode caches are excluded. Python and an external Node runtime remain
explicit external dependencies and must be upgraded deliberately with validation.

Promotion verifies the complete staged inventory, repeats import checks and,
for this registered DSH installation, verifies the candidate's authenticated
product identity and model catalog against the running integration. It makes no
model request, changes no saved chat and restarts no backend. The runtime must be
reachable for this preflight; an offline or incompatible candidate cannot replace
the current selection. The checks complement feature tests; imports/catalog
access do not prove every feature or microphone/speaker behavior.

The only selection commit is an atomic, fsynced replacement of `desktop.json`.
A failed stage, failed preflight or interruption before that replacement leaves
the old selection intact. Both artifact directories survive promotion. Treat
selected release files as immutable; hash verification rejects changed artifacts
on subsequent promotion. Runtime startup does not continually hash dependencies.

## Inspect and undo without AI

```sh
augmentor-update status
augmentor-update rollback
augmentor-recover
```

Status reports the selected version, source reference and artifact identity,
plus the actual running roots and connection/audio-control state of desktop,
mobile and secondary windows. An absent window is reported as absent.

Rollback validates and selects `desktop.previous.json`; as with promotion, open
windows retain their code until their next start. The previous artifact is not
deleted. Before a coordinated DSH/speech upgrade, plan its own compatible rollback;
this command changes only the native desktop selection, not backend state, data,
plugins, model settings or external speech dependencies. There is no automatic
fallback that silently launches an obsolete version after a runtime error.

Historical scripts such as `deploy-dual-memory-preview.py` are not the desktop
update path. They refuse activation against a managed release. Package/browser
publishing and source commits remain separate operations; updating any of those
alone must not be described as deploying this installed desktop.

## September 20 validation

The implementation is published with this guide on the current development
branch/PR #3. The installed baseline is a separately staged copy of the user's
reboot-confirmed 0.2.8 audio-enabled preview with the `2dca65f` startup/recovery
patches. Its descriptor records this mixed provenance and the exact artifact
hash; it is not represented as an unmodified 0.2.9 build.

The full native suite passed **383 tests**; the **15 focused deployment/startup
tests** also passed after the final artifact-copy correction. Qualification covers interrupted promotion, failed imports/connection checks,
changed artifacts, external symlinks, internal links, preserved interpreter paths,
selection/rollback, mobile selection and manual recovery with a pending update.
Live qualification imports the staged artifact, checks the actual DSH integration
and renders its native window in a separate offscreen preview without changing
the user's open conversations. A real 0.2.9 source candidate was refused against
the active 0.2.8 DSH integration, preserving the working selection. Live rollback
of the selection also passed without restarting any window.

The selected baseline artifact SHA-256 is
`52f4ef2a146cf727627db0df66f70b80f5c59d9957f704479e4f9d45a913df53`.
All three existing windows remained connected with audio controls while their
selection was pending; they adopt the copied release at their next start.
This does not claim another physical reboot
of the newly staged release path; the user reported the preceding repair's reboot.

## September 20 voice update selection

Source patch `8f9903d` adds native playback buffering and incremental-ASR progress.
The two modified pre-existing native modules were byte-compared with the selected
baseline before patching a separate copy. No 0.2.9 product/runtime replacement was
attempted against the user's 0.2.8 DSH integration.

Selected release: `20260920-150518-3d939dd3`, product 0.2.8, artifact SHA-256
`b34bccb926558435f06216d1aa06aefcd5cc2102ef71ec52446b922856e29a7a`.
Its descriptor retains the previous baseline artifact hash and source patch.
Stage/import/inventory and authenticated activation preflight passed. The separate
speech companion was updated to Resonant Voice 0.1.16 (`fbb7cd3`) while it had no
active owner; its installed streaming path was verified with synthetic audio.

Desktop, secondary and mobile windows were still running the previous preview
with working connections/audio controls at activation. A later guarded reload
attempt found the desktop and secondary executing tasks (`busy`/`running` true)
and correctly stopped before closing anything. Their playback-buffer update is
pending until close/reopen or login. No active task, draft, DSH process, memory
service or GPU workload was stopped. The companion's incremental recognition is
already available to these older compatible clients when they connect to voice.

All 395 native tests passed, followed by the five installer tests after the voice
package pin update. Voice fixtures/real CPU tests and remaining acoustic/model
latency limitations are recorded in [the native voice guide](VOICE-SINGLE-BUTTON.md#incremental-recognition-and-buffered-playback--20-september-2026).
The canonical launcher, recovery tool, secondary shortcut and login all retain
the new selection. No physical reboot of this artifact has been claimed.

## September 20 completed voice-update restart

The user subsequently requested the restart. Desktop, secondary and mobile
maintenance endpoints confirmed no active work; accessibility checks confirmed
empty message drafts before each close. Each window closed through its guarded
maintenance protocol and reopened through its managed launcher/service.

All three now report running root `20260920-150518-3d939dd3`, `online: true`,
`voiceAvailable: true` and `updatePending: false`. Saved conversation IDs and model
selections were compared privately before and after and stayed unchanged. The
secondary window's hidden state was restored. DSH, memory and speech/model
services were not restarted. The same native playback fix now applies when
resuming existing conversations and when creating new ones; chats require no
migration. Actual first-word listening with this loaded build remains the user's
next acceptance check. The earlier deferred-reload entries are historical.

## September 21 controlled memory activation

Implementation `78b64ee`, followed by scoped-consolidation correction `edf7d76`,
was qualified against the pinned engine and unchanged local Qwen model.
[Controlled memory](CONTROLLED-MEMORY.md) records behavior, limits and evidence.

A separate copy of the selected 0.2.8 artifact `b34bccb9…` received the memory
companion, gateway/budget/controller, context assembler, DSH memory adapter, native
processing controls and required prompt-client routing. The Pi host received
matching memory integration; unrelated 0.2.9 browser-recovery additions were
excluded. The existing installed browser policy/metrics were copied into the
artifact, preserving their behavior and adding only `memory_source` to the
read-only allowance. Product identity and speech dependencies stayed compatible.

The candidate itself passed real DSH/Pi lifecycle integration with fixture model
and engine. `augmentor-update stage` imported and inventoried it; activation
verified the live 0.2.8 product contract. Selected release
`20260921-011742-0b89b31a` has artifact SHA-256
`c995e9f93bed937af4d3d5bad658da734e66b0370cbd5757497cb2369b5503f9`.

Before cutover, all DSH tasks and voice were idle. Native maintenance status and
accessibility inspection confirmed idle windows and empty message drafts. Each
window closed through its guarded protocol; presets and SQLite were backed up.
Stopping DSH also closed its child memory companion, so cutover resumed with it
already stopped. No task or unknown action was replayed.

The Hindsight installer backed up the stopped volume and retained the previous
container with restart disabled. The replacement uses that same persistent
volume, pinned image and existing model endpoint, with autonomous processing off.
The controlled companion started before DSH/window restoration. All three windows
now run the selected release, online with voice controls and `updatePending:false`.
The primary conversation/model state file was byte-compared before and after;
named windows reopened from their own stored state. The secondary window's
hidden state was restored. Model and speech settings were preserved.

Idle admission was verified with historical data present: no eligible imports,
processing jobs or model budgets appeared. Both GPUs sampled at 0% utilization.
An additional idle companion restart preserved its journal and granted no
processing window. This does not claim a physical reboot or human microphone
trial of the new artifact.

Private rollback records live under the user's `augmentor-controlled-deployment`
state directory; Hindsight's stopped-volume backup is in its private data folder.
Desktop rollback alone does not restore preset/engine configuration. Keep memory
inference paused during coordinated rollback, and never revive the old autonomous
worker just to clear a pending status. Preserve newer journal records and all
engine data. No private conversations, credentials or local bank IDs are published.

## September 21 general terminal-response guard

Source `1c8c1b7` adds a domain-independent response-validity check to the existing
DSH execution adapter. It shares recovery limits with truncation and reports
incomplete outcomes when a reasoning-only/blank answer cannot be recovered.
No weather/domain checks or mandatory task format were introduced.

Compatible0.2.8 selection:`20260921-132038-7fd1a0ae`, SHA256
`76c10abd7e98ab6f4bf83ad0a489198d956d9dc6ea9c28a300d94a2aede6db6a`.
Its base is the prior708d66c9… artifact; only the adapter and its guide were patched
in a separate candidate.142 Node/410 native tests passed in source;24 focused
adapter checks also passed on the final immutable artifact. Activation preflight
and healthy Linux/browser preset resolution passed without a model request.

The two owned presets reference the new adapter, preserving configuration and
backing up checksummed originals. Existing windows were not restarted and still
run20260921-011742-0b89b31a. Fresh visible tasks load the new preset adapter; no
claim is made about old instantiated agents reloading it. See
[contract, evidence, limitations and rollback](BOUNDED-EXECUTION-RECOVERY.md#installed-selection-for-response-validity).
