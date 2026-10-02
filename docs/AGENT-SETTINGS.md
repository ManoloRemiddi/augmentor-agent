<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Desktop agent settings

Clicking the Desktop’s three dots opens Agent settings in one click, replacing
the chat content inside the existing frameless window. It uses the same native
window and frame; no menu, separate settings window or modal loop is created.
Back to chat (or Escape) restores the exact latest chat geometry, including user
resizes before entry. The temporary settings size is not saved as chat placement.
Drafts, conversation widgets, streaming state and the visible Stop action survive.
Hiding/reopening retains the settings page while restart placement retains the
chat size. Source accessibility scaling also scales the saved chat dimensions.

Agent, Look, Voice and More remain the main navigation. Agent contains an editable
name, image picker and the existing voice energy ring, vertically stacked rectangular
Soul/Memory cards, and access for new chats. Look and Voice immediately open their
complete existing forms inside the frame, with no intermediate landing page.
More opens All settings with direct links for every old menu action: Appearance
(colours/skins), Prompt library, model/agent setup, DSH browser access or model
providers, Approval mode, Versions/updates, About/licenses and Quit. Mac browser
extension setup is retained when available. Conversation, Connections/Home and
Advanced keep the additional controls. There is no duplicate bottom Settings entry.
Approval mode takes the user directly to the Agent access control.

Settings forms are embedded child widgets, with their existing save/cancel and
worker cleanup preserved. Busy operations that already refused dismissal still
refuse navigation. An open settings page makes guarded maintenance unavailable.
An unsaved Soul offers inline Save & return, Discard & return and Keep editing;
conflicts leave the draft open. Normal file/image selectors retain their native
chooser behavior. First-run setup retains its existing flow; subsequent setup
from Settings stays in this frame.

This change implements the Desktop direction approved on 2 October 2026.
The spacious Browser redesign is a later presentation step; Browser conversations
use the same backend Soul snapshots. Existing setup and conversation state remain.
The Agent page is available after setup through Settings; there is no extra blocking
personalization wizard.

## Identity and Soul

Identity lives in `identity/` under `AUGMENTOR_PI_CONFIG`, otherwise
`$XDG_CONFIG_HOME/augmentor-pi` (default `~/.config/augmentor-pi`).
`AUGMENTOR_IDENTITY_DIR` overrides that directory for isolated tests.
`profile.json` stores the name and a copied PNG avatar. Images are decoded locally,
bounded to 10 MB and 8192 pixels per dimension, and resized to at most 256 pixels.
The image remains available after its source file is removed. Identity images
are not sent as model input. Reset image restores the voice energy ring; its
animation runs while visible and enabled by Appearance and stops when hidden.
Appearance and voice preferences retain their existing per-window ownership.

`soul.md` is authoritative personal Markdown. Before the first save, it inherits
`config/agent-persona.md`. Soul writes use an atomic, durable private file replacement,
a file lock and optimistic content revisions. Empty, NUL-containing and over-32-KiB
instructions are rejected. Conflicting edits retain the draft and the other writer.
Reset Soul loads the packaged default into the editor. Save applies it; Cancel
retains the saved version. Leaving an unsaved draft shows inline save/discard/keep-editing choices.
Reset affects no other identity, access or memory data.

Pi captures Soul in new conversation metadata; forks inherit the source snapshot.
Legacy Pi chats without Soul metadata retain their earlier system instructions.
Codex captures it in its existing immutable developer-instruction snapshot and
preserves its base instructions and capability guidance. DSH uses a scoped prompt
registry section and per-conversation `identity/dsh-sessions/<hashed-id>.md` snapshots:
its preset mount is shared, but conversation instructions are not. Historical DSH
chats without a snapshot inherit the original packaged persona, and branches inherit
the parent's snapshot. Updating an existing installation requires upgrading its
owned DSH presets to the new identity adapter and restarting the idle host.
No new journal event type or extra user message is introduced.

## Memory and access

Memory reads `memory.dual.recall` for the current harness-qualified conversation.
About you and Your project show the existing relationship/work projections,
including cached pages and pending-update state. They are derived stored knowledge,
not an editable `memory.md` file and not a claim of a complete or freshly processed
record. An unbound conversation, paused recall or unavailable service is shown
honestly. Memory setup still provides separate capture/recall and processing controls
and the existing manual-library controls; viewing knowledge does not resume processing.

Fresh Pi/Codex permission settings default to Full access. The Desktop DSH adapter
initializes an inherited permission default to Full access only when the public
settings descriptor has no explicit user `defaultPreset`; explicit saved choices
are preserved. All writes use the harness's optimistic revision. Changes affect
new chats; existing chats and historical branches keep their policy.

Codex Full access uses native `never` approval plus `danger-full-access`.
Ask before actions uses `on-request` approval with a read-only filesystem sandbox,
requiring escalation for native writes, and an explicit one-time approval for
changing Augmentor browser/desktop/Home tools. Read only uses `never` plus
`read-only` and blocks changing custom tools before dispatch. Observations,
memory reads and cancellation remain available. OS desktop sharing and paired
Home permissions still apply. Existing Codex chats without new policy metadata
retain their previous native policy and custom-tool behavior.

## Initial identity qualification — 2 October 2026 (historical)

Implementation: `eef21cf` plus legacy Pi compatibility `fa5d3cf` on `feat/desktop-agent-settings`, based on `d91c520`. Implementation has not
been merged and awaits the owner's local acceptance.

- Build and TypeScript checks pass.
- Node suite: 484 tests, 482 passed, two explicit platform/fixture skips.
- Native suite: 610 tests, 608 passed, two explicit skips, with PySide6 6.8.2.1.
- Ten new Qt checks cover navigation, scoped Memory, name/avatar persistence,
  animation lifecycle, reset/cancel/save and optimistic Soul conflicts.
- Real pinned Codex with a synthetic Responses server proves developer snapshots,
  native approvals, custom-tool denial in Read only/Ask, and existing full-access
  Browser and Home behavior. DSH prompt hooks are separately synthetic contract checks.
- Dark/light and 320-pixel narrow native renders were inspected on Linux.
- The compatible candidate copied installed product 0.2.11 artifact
  `3e89dedc3d701fe66a41bfd0b7ff2558d0aaeb70b76750a9409eac7b0fbf30be`, overlaid
  reviewed modules, and passed its ten Qt tests plus four Node/real-Codex checks and 27 real-Pi fixture checks.
  Its product manifest, installed dependencies, speech contract and unrelated
  native behavior remain from that artifact. Source product 0.2.13 is not claimed
  as a new installed 0.2.13 release.

Linux and macOS share the UI, file persistence and harness adapters. Both use
POSIX file locks and atomic writes; no new OS adapter is required. No installed
Mac app or real Mac desktop interaction was tested in this turn. Packaging and
native dependency qualification on macOS remain acceptance work.

## Initial installed Linux identity candidate (historical)

Selected and running release: `20261002-111240-1618d51b`, compatible product
0.2.11, artifact `7419f27525a67101b03d35f1a6d11471c7d7491567d855d75d5acc0b08276b77`.
`augmentor-update stage` and `activate` passed the installed identity/import checks.
Main Desktop and mobile were idle, with no drafts, and closed through their guarded
maintenance calls before restarting their supervisors. Both now report this
build, online with voice available and no pending update. Pi/Codex were not running;
the next startup uses the selected artifact. No model request, GPU/model setting,
voice placement or private conversation was changed as deployment evidence.

The existing DSH global composition contains earlier customizations, so the full
installer refused replacement before writing files. A narrow migration checked the
ownership checksum of each personal `agent.cordis.yml`, backed up both files and
`ownership.json` under the private DSH profile, replaced only its `persona` row
with the first immutable settings candidate's identity adapter (the same identity code in the final candidate), and updated those two ownership hashes.
Other rows, the Browser plugin and global composition were preserved. The idle
`dsh-web.service` was restarted, and both product presets remain available. The
full installer still requires a separately reviewed migration of the already edited
global composition; this feature does not silently normalize it.

That initial candidate used menu → Settings; the frame-overlay revision below supersedes that navigation.
Identity and Soul are shared by the two personal surfaces; access choices affect
future chats. Live-provider responses to a customized Soul remain the owner's
acceptance test. No merge has been performed.

Rollback: `augmentor-update rollback` returns to the first settings candidate.
To undo the whole feature, activate original release `20261002-004606-8f44c801`,
restore the
backed-up personal preset files and ownership metadata, and restart idle DSH and
Desktop supervisors. New identity files remain private user data; rolling back the
UI does not delete them. Keep the local test candidate and preset backups until
acceptance is complete.

Review: [draft PR #29](https://github.com/ManoloRemiddi/augmentor-agent/pull/29), awaiting the owner’s green light.

## Frame overlay revision — 2 October 2026

The owner requested direct three-dot entry, all former menu actions in the new UI,
and resizing/restoration of the same agent frame. Shared source qualification:
623 native tests, 621 passed and two Mac-only skips, using PySide6 6.8.2.1.
Thirteen new real-window Qt checks cover same-window entry, latest geometry and
chat draft preservation, hide/reopen placement, direct Look/Voice forms and voice
cleanup, old menu coverage, inline Soul decisions/conflicts, busy-form refusal,
Stop and hidden-chat shortcut protection, compact mode, 320-pixel/light navigation,
both ordinary and non-default startup app scales, and safe dismissal before a
late worker result. Destroyed forms cannot receive worker UI updates. An existing butterfly fixture
now waits for an actual animation tick within a bounded interval instead of
assuming it has occurred after a fixed 60 ms. Dark/light/narrow renders were inspected.
The unchanged runtime’s Node/build evidence above remains historical; this follow-up
changes native presentation/lifecycle only.

The separate compatible candidate copies initial installed artifact `7419f27525a67101b03d35f1a6d11471c7d7491567d855d75d5acc0b08276b77`,
replaces the reviewed settings component and applies only the authored window and
touch patches. Its 23 focused cases pass (21 passed, two source app-sizing checks
explicitly skipped because the retained installed Appearance has no live-scale
slider). Product 0.2.11, speech dependencies, DSH/Pi/Codex runtimes and other deployed
native improvements are preserved. No DSH preset migration or host restart is
required for this UI follow-up. Shared Mac source/setup-choice tests pass on Linux;
installed Mac GUI acceptance remains unverified. Installed release identity follows
in the deployment record after staging.
