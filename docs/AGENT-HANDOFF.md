<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Start here: agent handoff

## September 26 desktop readiness correction — activation pending

The owner reported that the Mac still could not chat. The failure was reproduced:
an already-open pre-setup controller retained the missing legacy preset while
reporting online. The desktop adapter now verifies its preset before readiness.
The corrected packaged Qt window passed actual composer/Send and Enter tests
against DeepSeek, including same-conversation restoration after reopening;
445 native tests (one skip) and the full packaged DSH/Qt fixture passed.
See [the correction and activation boundary](MACOS-DISTRIBUTION.md#september-26-correction-verify-chat-readiness-and-the-actual-composer).
The corrected candidate is staged. The owner's old window still has a dialog
open; preserve its draft and finish activation after it closes. Do not repeat
the earlier claim that an online status alone proves desktop chat works.

## September 26 personal Mac model access

The owner requested their MX model access on the test Mac. The existing
`c03c32e` development bundle now has a private per-user DSH profile, matching
Augmentor integration, Model Picker 1.1.2 and launchd-managed runtime/model tunnel.
Exact catalog comparison passed (365 models, seven providers), a real DeepSeek
Flash reply succeeded, and the open desktop reported online/model-ready. The
secondary GPU endpoint is offline on the workstation too; no GPU settings changed.
See [Mac connection evidence](MACOS-DISTRIBUTION.md#september-26-personal-mac-model-connection)
for deployment boundaries. Keep personal credentials/configuration out of GitHub.
This does not complete the public installer, signing, voice or browser rollout.

## September 25 macOS distribution implementation

The owner authorized implementation and isolated network-Mac testing. See
[macOS distribution](MACOS-DISTRIBUTION.md) for the native launcher, complete
prepared DSH payload, hashed Python wheels, build/test workflow and exact evidence.
Native launcher and real packaged DSH/Qt proofs pass on ARM64 macOS 26.5.1.
This is development qualification; managed first-run, required plugin provisioning,
store migration, coordinated updating, production signing and permission acceptance
remain open. The build Mac has no valid Developer ID signing identity.
Linux installed selections, live model/speech settings and Mac registrations were
not changed. Do not present this source branch as a published Mac release.

## September 25 source integration

The user requested merging the composer correction and other ready changes.
The integration combines Home/tray PR #6, shared Desktop/Browser/voice PR #7,
and composer PR #9, preserving their original commits. The host idle-baseline
reservation and Browser prompt-improvement send guard both survive conflict
resolution. The full sidebar entrypoint now verifies immediate transfer, duplicate
Enter suppression and preservation of a newer draft.

Combined source checks pass: TypeScript check/build, 194 Node, 44 Browser,
29 Home and 427 native tests (one native environment skip). GitHub package checks
remain the final merge gate. Installed selections and running windows are unchanged
by source integration; public download bytes require a separate release. Home's
remaining qualification work stays documented in [Home](HOME.md).

## September 25 composer submission correction

[Immediate composer feedback](COMPOSER-SEND-FEEDBACK.md) records the Desktop
idle-baseline race and Browser acknowledgment delay. Send failures now own draft
restoration; status notifications do not. Consult that guide for tests and installed
adoption rather than assuming a source update has reloaded open windows.

## September 24 Home tray launcher

The owner confirmed the installed launcher works and requested click-to-open,
click-again-to-close. The KDE adapter now resolves the actual Chromium dashboard
window on each click; explicit Open raises it. Release `20260924-205229-78c3c113`
is selected and its tray is running. Actual tray activation passed open/close/open
with one Home window and unrelated window IDs preserved. See the launcher guide
for platform limits and evidence. This supersedes the initial selection below.

[Home launcher](HOME-LAUNCHER.md) implements a lightweight Qt tray process for
opening an existing NAS dashboard through the installed browser. It remembers
only the dashboard address, requires no copied API key and starts no model/agent.
A stable entrypoint follows desktop.json; install after managed artifact promotion.
Native tests and a two-process singleton check pass. Managed release
`20260924-202032-d5e07a94` is selected; its Home tray is installed and running,
with live KDE registration and dashboard app-window evidence. Main/mobile and
secondary retain their earlier running builds; their drafts/work were preserved.
See [installation evidence](HOME-LAUNCHER.md#installed-linux-evidence--24-september-2026).

## September 24 sidebar animation and product name

The Browser prompt-improvement preview now rolls letters and settles before
committing, with cancellation and late-response guards. Chromium display metadata
uses **Augmentor Agent**. See the [latest shared-surface entry](SHARED-SURFACES-2026-09-24.md#restore-sidebar-improvement-animation-and-product-name)
for validation and installed adoption; the prepared extension requires Reload.

## September 24 sidebar presentation refinement

The user confirmed the corrected sidebar is working and requested a simpler
Browser presentation: always follow tabs, remove Follow and circular activity
controls/functionality, remove the outer border and brand label, and keep the
empty composer one line tall. Conversation title and shared control order remain.
See [shared surfaces qualification](SHARED-SURFACES-2026-09-24.md#sidebar-refinement-after-user-acceptance)
for source checks and local adoption. Chromium needs Reload after updating the
prepared extension folder; do not remove/reinstall it or interrupt native drafts.

## September 24 shared personal agent and voice

The user requests one personal agent in the floating window and browser sidebar.
[Shared surfaces](SHARED-SURFACES-2026-09-24.md) owns the new shared preset, host
voice engine, approval bridge and stopped-task status correction. Earlier
browser-only tool-policy statements are superseded for DSH personal sessions.
Read its deployment evidence before assuming a running extension has reloaded.
Combined Home/shared source `d24e2ff` runs in the secondary
window. Primary/mobile adoption and Chromium reload remain pending; preserve the
primary draft. This is a compatible development artifact, not a public release.

## September 24 Home runtime preview

[Home](HOME.md) now has a headless DSH host in `apps/home` and a constrained
Assist MCP policy in `adapters/dsh-home`. Canonical application code stays here;
private household deployment and operational records belong in the Home companion.
The user clarified that Home must be a lightweight NAS-owned capability available
inside existing Augmentor clients, with independent household hardware/models/API
configuration. A shared client adapter, pairing/settings and lightweight NAS page are implemented.
NAS runtime source e5e5764 is promoted with direct On/Off device cards and an
owner-only discovery snapshot, building on selected-device policy, model settings,
cancellation propagation and clean shutdown. The KP303 uses HA’s existing TP-Link
integration; its three lighting outlets and the Elgato light have controls enabled.
Four unlinked Tapo devices remain listed with setup status. See Home for evidence.
Earlier Desktop deployment was coordinated with the shared-surfaces task: combined
source d24e2ff / release 20260924-125950-12694ac7 was selected and secondary adopted it.
At that checkpoint main/mobile retained the preceding Home-enabled release to
preserve a draft. The later flare selection below supersedes that selected identity;
consult current installed status before any changes. Preserve drafts and active work.
The prepared Browser extension combines Home and Voice; reload/adoption is separate.
Home PR #6 remains unmerged. Source synchronization with public main does not
redeploy Desktop or alter the separately coordinated shared-surfaces PR #7.
Full resource/release qualification is pending. A finite NAS availability pilot is
running; it is not a completed seven-day workload/physical-device qualification.
New configuration defaults to owner-selected registered entities; the earlier
Assist MCP mode remains an explicit compatibility preview. Read the guide for
exact fixture/live evidence and limits before expanding device access.

exact fixture/live evidence and limits before expanding device
access. This preview does not change the installed Desktop or Browser release.

## September 24 desktop flare ownership

The [0.2.12 release record](RELEASE-0.2.12.md) tracks the managed transient
activity canvas correction, workspace/stacking proof and public download status.
PR #8 is merged and 0.2.12 is published. Website downloads select the new bundle.
Home/shared-surface previews remain separate; this release is based on public main.
The compatible local flare patch is selected in `20260924-140435-fa4c42f4`;
open windows still need reopening. Preserve unsent drafts and active work.

## September 24 WebSocket security release

See [the ws security correction](WS-SECURITY-2026-09-24.md) for the `ws 8.21.3`
pins, Pi shrinkwrap/bundled-CLI exclusions, regression evidence and publication
boundary. The build/test/start preparation step is required after installing
with lifecycle scripts disabled. The [0.2.11 release record](RELEASE-0.2.11.md) tracks final qualification,
publication and installed selection separately from the original source candidate.
PR #5 is merged; 0.2.11 is live on GitHub and npm. Desktop and mobile are running
the recorded user-local artifact, online with voice available. Chromium extension
loading remains a separate user action; see the release record before claiming
Browser activation.

## September 23 canonical repository and license

Current development is [ManoloRemiddi/augmentor-agent](https://github.com/ManoloRemiddi/augmentor-agent),
branch `main`, for both Desktop and Browser. The clean public repository was
renamed from `augmentor-agent-source`; its public history is retained.
The old private repository is now `augmentor-agent-history` and is an archive.
Read [repository roles and preserved work](REPOSITORIES.md) before resuming old tasks.

Augmentor-authored code carries [MIT with Augmentor Resale Restriction](../LICENSE).
Personal/business use and modification remain free; resale needs Manolo Remiddi's
written permission. See [publication scope](PUBLIC-SOURCE.md).
Earlier binary releases retain their shipped licenses. Source or documentation
publication does not redeploy the installed application.

## September 22 native opening-notice visibility

Source `ee5d8f1` hides only the exact successful minimal-to-xhigh request-policy
notice from native live/history transcripts. Other DSH messages and underlying
events remain intact. See [visibility contract](BOUNDED-EXECUTION-RECOVERY.md#settings-and-progress)
and [selected versus running deployment](DESKTOP-DEPLOYMENTS.md#september-22-hide-the-routine-opening-reasoning-notice).
The tested compatible artifact is selected; existing windows still need reopening.

## 0.2.10 action-aware recovery and complete distribution

Recovery now consumes structured tool outcomes and blocks exact duplicate changes,
tracks existing jobs, permits inspection and respects concluding handoffs even after
truncation. See [contract and limits](BOUNDED-EXECUTION-RECOVERY.md#action-aware-recovery--0210-preview)
and [complete installation](COMPLETE-INSTALL.md). This is generic lifecycle policy;
it does not certify answer correctness or add a cross-session transaction ledger.
The complete bundle includes the adapter and all required plugins. Public download
and candidate-specific acceptance are recorded in the [qualification ledger](RELEASE-QUALIFICATION-0.2.10.md). Product artifact source is `ad4bc7d`; subsequent test-driver/documentation changes do not alter that immutable artifact.

## September 21 general response validity

The execution adapter now handles reasoning-only/blank terminal responses using
the same bounded budget as truncation. It emits a durable incomplete outcome on
exhaustion, preserves valid answers/tool handoffs and does not certify task success.
Read [the contract, qualification and remaining scope](BOUNDED-EXECUTION-RECOVERY.md#general-response-validity-correction--september-21).
No task-specific rules, memory replacement or generic artifact verifier were added.

## September 21 bounded execution recovery

Read [bounded recovery](BOUNDED-EXECUTION-RECOVERY.md) for same-turn truncation
recovery, limits, effective-setting visibility and real-DSH regression coverage.
It is DSH-only and does not automatically certify task completion. Consult its
deployment and retest evidence before assuming installed behavior.


## September 21 controlled memory correction

The previous unattended-memory lifecycle is superseded. Read
[controlled memory](CONTROLLED-MEMORY.md), [dual memory](DUAL-MEMORY.md) and
[operations](MEMORY-OPERATIONS.md) before touching its worker or queue. Capture,
context selection and inference admission are separate. The original model and
speech placement/settings remain unchanged. Source qualification includes real
DSH/Pi fixtures, native regression, real-model memory completion, streaming
cancellation and failed-page preservation. Source `edf7d76` is installed in compatible release
`20260921-011742-0b89b31a`; all three native windows have loaded it.
Installed selection is tracked in
[desktop deployments](DESKTOP-DEPLOYMENTS.md); source tests alone do not establish
which running window has adopted an update.

## September 20 voice latency update

The native voice path now uses a bounded startup/recovery playback reserve and
exposes stage timings without logging audio or text. Resonant Voice 0.1.16 adds
incremental CPU ASR during capture; complete-install component pins are updated.
See [native voice behavior and evidence](VOICE-SINGLE-BUTTON.md#incremental-recognition-and-buffered-playback--20-september-2026)
and [deployment selection](DESKTOP-DEPLOYMENTS.md). Full native regression: 395
passing tests. Recognition and playback fixes do not remove model prompt-processing
or reasoning time; no GPU/context/reasoning policy was reduced. The 0.2.8-compatible
native artifact is now running in the desktop, secondary and mobile windows
after the user-requested graceful restart. All three are online, with their
previous conversation/model preserved and `updatePending: false`. The 0.1.16
speech companion remains running.

## Complete installation and public distribution

See the [September 20 distribution audit](DISTRIBUTION-AUDIT-2026-09-20.md) and
[complete installer](COMPLETE-INSTALL.md) for current source/installed differences,
public-bundle contents, fresh-user setup and the next macOS phase.

## September 20 consistent desktop updates

The user subsequently performed a physical reboot and reported that everything
worked. Future desktop changes must use [desktop deployments](DESKTOP-DEPLOYMENTS.md).
Login, menu, shortcuts, recovery and mobile share `desktop.json`; `augmentor-update`
stages separate artifacts, validates promotion, records identity and retains the
previous selection. Do not revive the old preview-folder deployment workflow.

## September 20 startup correction

Startup/recovery implementation: `2dca65f`; Adaptive Reasoning correction:
`15d9981` / package 0.2.2. Read [restart reliability](RESTART-RELIABILITY-2026-09-20.md) before changing
launchers or investigating another offline desktop. It records two independent
root causes, the corrected adaptive plugin, the installed service/deployment
contract, preserved histories and actual cold-start/crash/recovery evidence.
Do not restore the old hard-coded login launcher or move diagnostic events back
into conversation logs. The September 19 qualification below remains historical.

## Source of truth and retrieval

GitHub is the durable source of truth for source, decisions, run instructions,
contracts and evidence summaries. Local conversations, ignored `outputs/` and
an individual machine's installed state are not a substitute for this record.
Never publish private transcripts, credentials, tokens, model weights or user
configuration to satisfy documentation completeness.

### Historical September 19 qualification (superseded repository location)

The following records the old private development state, not today’s checkout instructions:

- Historical private repository: [augmentor-agent-history](https://github.com/ManoloRemiddi/augmentor-agent-history).
- Historical development: branch `productization/shared-memory-and-desktop`,
  [draft PR #3](https://github.com/ManoloRemiddi/augmentor-agent-history/pull/3).
  Its source was exported into the clean public repository; use public `main` now.
- Last fully qualified implementation: commit
  [`29231fdf367fdade2aee74530785d29af2bee95e`](https://github.com/ManoloRemiddi/augmentor-agent-history/commit/29231fdf367fdade2aee74530785d29af2bee95e).
  Subsequent documentation commits do not expand its runtime evidence.
- Subsequent native voice correction: [buffered activation, echo guard and drag feedback](HANDS-FREE-IMPLEMENTATION.md#buffered-activation-and-playback-echo-protection--19-september-2026),
  based on `cc8845c`. Its own validation/deployment scope is recorded separately
  from the fully qualified product snapshot above.
- Speech repository: [resonant-voice](https://github.com/ManoloRemiddi/resonant-voice),
  `main`, package 0.1.14. Both repositories require the appropriate GitHub access.
- Product manifest: [`release/product.json`](../release/product.json), 0.2.9 preview.
  A version alone is insufficient to identify a development artifact: record its
  commit and artifact hash too.

Read in order: repository [AGENTS.md](../AGENTS.md), [current architecture](ARCHITECTURE.md),
[feature matrix](FEATURE-MATRIX.md), the [documentation index](README.md), then the
subsystem guide for your task. Dated evidence applies only to its stated build.
Historical plans do not override current source/contracts and maintained guides.
If these disagree, inspect the code, report the discrepancy and update the guide
alongside the fix instead of silently treating a plan as implemented behavior.

For a fresh clone:

```sh
git clone https://github.com/ManoloRemiddi/augmentor-agent.git
cd augmentor-agent
git status --short
git log -1 --oneline
```

For an existing working copy, inspect its origin, branch and changes first. Old
private-history checkouts stay pointed at the private archive. Preserve local
changes and port only selected, reviewed changes to a fresh canonical branch;
never merge private history or repoint an old checkout at the public origin.

## Reproduce development checks

Use tested Node 24.19.0. Install Python/Qt dependencies from
[`requirements-dev.txt`](../requirements-dev.txt), using a dedicated environment
or the matching system Qt packages. [`validate.yml`](../.github/workflows/validate.yml)
is the exact clean Debian dependency and test recipe; QtTest is needed for UI tests.

```sh
npm ci --ignore-scripts
python3 scripts/sync-version.py --check
npm run check
npm run build
npm test
npm run test:native
node --test apps/browser/test/*.test.mjs
```

Use the configured Python environment for `npm run test:native`. For locked DSH
qualification, follow `release/dsh/README.md` and the workflow's DSH environment
variables; a missing DSH installation is not a passing integration test.
[Tests](../tests/README.md) maps focused checks to subsystems. Physical desktop,
provider, audio and installed-package checks have separate prerequisites and
must not be confused with fixtures.

## Verified state

[CI run 35441917540](https://github.com/ManoloRemiddi/augmentor-agent-history/actions/runs/35441917540)
passed all three jobs for `29231fd`: Debian/source/native checks; installed
packages; packaged browser. It covered first run, actual pointer/clipboard,
DSH approvals/questions/exact forks, memory lifecycle fixtures, installation,
active-task refusal, interrupted configuration, upgrade, rollback and removal.

A separate real Hindsight 0.10.0 + local Qwen proof generated four synthetic
knowledge pages, recalled relationship preferences and project state after a
bridge restart, and checked person/project isolation. It used voice-labelled
text, not a physical microphone trial. The reproducible entrypoint is
`scripts/hindsight-proof.py`; results and limits are summarized in
[the September ledger](DESKTOP-UPDATE-2026-09-19.md).

Resonant Voice 0.1.14 passed 33 Node and 3 Python ASR tests plus real DSH lifecycle
and tarball install/remove checks with fixture LLM/TTS. Speech licensing and
human listening acceptance remain separate from code/test success.

## Historical September 19 installed preview

The worker/automatic migration described here is superseded by the September 21
controlled implementation above. Do not recreate its unattended queue processing.

The recorded local preview has Hindsight on loopback 8889, a persistent Docker
volume, CPU embeddings/reranking and one background worker. Memory inference uses
the existing local Qwen endpoint without changing the chat model or GPU settings.
The automatic memory adapter was activated from published source after DSH and
voice became idle. Journal migration continues asynchronously.

This is a dated observation, not a guarantee about a future machine. Read
`~/.local/share/augmentor-memory/active.json` locally to locate its actual release
and rollback backup. Use [memory operations](MEMORY-OPERATIONS.md) for checks and
[voice deployment](https://github.com/ManoloRemiddi/resonant-voice/blob/main/docs/DEPLOYMENT.md)
for speech state. Do not copy private local configuration into documentation.
Do not restart active DSH tasks or voice connections to load a change.

## Remaining work and evidence gaps

- Human two-session voice continuity and relationship quality; microphone,
  speaker echo/double-talk, interruption and latency acceptance.
- Longer memory quality/contradiction evaluation. Automatic memory currently has
  no supported per-person/project erase UI or multi-speaker identity recognition.
- Browser source controls require deployment/reload in the target profile;
  source/isolated acceptance is not proof of that profile's installed version.
- Fedora real desktop/browser acceptance, current macOS parity, public release
  and other [distribution gates](CROSS-PLATFORM-RELEASE-STATUS.md).

## Keep GitHub sufficient for the next agent

Every meaningful change should update its owning guide and any affected
architecture, feature matrix, data disclosure, setup, migration or test recipe.
Record what is implemented, what is installed, the exact tested ref, fixture vs
real-service evidence, and remaining work. Link new guides from the index.
Preserve dated evidence rather than relabelling old tests as new qualification.
Publish a reviewed commit and update the PR with scope and validation. A local-only
note or an unpublished branch is not a completed handoff. Merge/release status
must remain explicit; documentation publication does not itself merge a draft PR.
