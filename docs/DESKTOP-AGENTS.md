<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Named desktop agents

Settings → Agents adds desktop entries that reference independently owned DSH
presets. Entries have stable window IDs, display names, a preset ID, working
folder, optional initial model and a private conversation-state binding. The UI
reads `agentPresets.list` and the DSH model catalog separately. It never edits a
persona, skill or tool definition. No desktop window or DSH agent starts until an entry is opened.

The compatible installed settings frame exposes **More → Agents · named
windows**. The shared source settings dialog exposes the same form. Select an
entry, edit it and save; use Open / hide to recall it. Appearance applies to the
window where Settings is open: open the desired entry before changing its skin.

## State and migration

The version-1 registry is `~/.config/augmentor/agents.json`, respecting
`XDG_CONFIG_HOME` or an explicit `AUGMENTOR_AGENT_ENTRIES` override. Until its first
write, it synthesizes the existing main/secondary entries. Their original session,
model, preferences, appearance and shortcut files stay in place. Renames and model
changes retain the conversation binding. A changed preset or working folder gets
a new binding and retains the old binding in the registry. DSH conversation files
are never moved or deleted. History → All agents exposes retained conversations;
a conversation outside the current preset/folder opens as history, with sending
and branching disabled.

Removal retains the DSH definition, conversation files and former binding, and
removes only the entry and its owned OS shortcut. Remove a window from another
window after closing it. The main entry remains the startup anchor and can be
renamed or edited; other entries can be removed. Cosmetic preference files are
retained rather than deleting unrelated personal data. IDs cannot be reused after
removal. File writes are atomic, and concurrent saves require the displayed
revision. Shortcut registration occurs after revision admission, with restoration
if its accompanying registry commit fails.

Custom entries always use DSH. A missing/broken preset blocks connection and new
requests with an explicit unavailable message. No replacement preset is chosen.
An already open window whose binding changes elsewhere refuses further mutation
until reopened. Refresh preserves unsaved preset/model selections; unavailable
models remain explicit and cannot be saved as a fallback.

## Compatibility and authority

Independent entries support typed chat, system dictation, model selection,
branching, editing, saved chats and native DSH approval/question interactions.
Branching and editing retain the exact source preset and working folder.
The product bridge recognizes only active registered preset/folder pairs for
native interactions and forks; retained pairs are also recognized for saved-chat
metadata. This presentation ownership does not change `ownsProductSession`,
which continues governing Augmentor memory and normal product authority.

Augmentor conversational voice, personal identity/memory editing and prompt
improvement are unavailable for independent entries. Global Augmentor approval
settings cannot be changed from such an entry. DSH owns its agent permissions.
Dictation remains an OS input feature and supplies text to the selected agent.
Selecting a model with an agent's name does not select that agent.

Arbitrary DSH presets preserve their DSH composition. Augmentor does not silently
add a sandbox, tools or isolation to every preset. A definition previously
relying on process-wide restrictions must be composed correctly by its DSH owner
before sharing a server. Three optional, generic DSH composition helpers support
that migration without importing private agent source:

- `dsh-preset-file` registers an existing owner-authored `agent.cordis.yml` and
  `preset.yml` directory. It uses the explicitly specified DSH runtime's YAML
  parser and reloads file revisions. Missing/malformed replacements unregister
  stale definitions. The UI remains a consumer of DSH's catalog.
- `dsh-preset-boundary` masks inherited tools, publishes only an explicit grant
  list and rejects wrong preset/folder calls, ungranted tools, a widened sandbox
  or a changed approval policy. Its confined modes are workspace-write/read-only;
  it preserves a narrower existing sandbox and requires approval `ask`.
- `dsh-preset-environment` overlays shell environment in a fresh isolated shell
  provider. It does not mutate the shared server environment. Use it beside that
  preset's isolated shell, never against the root shared shell.

A scoped DSH group can isolate `skills`, `sandboxPolicy`, `approval` and `shell`,
mount fresh providers and retain its own persona, skill directory, tools and
hooks. The tool boundary supplements DSH's sandbox; it does not replace hooks or
an external gateway's owner-approval requirements. These helpers do not implement
another agent runtime or agent editor.

## Shortcuts and platforms

Linux uses the existing KDE KGlobalAccel owned desktop entries. macOS's background
shortcut service and Windows's hotkey owner now accept registered stable IDs
rather than only main/secondary. Their platform adapters still validate supported
keys and reject conflicts. Physical Mac/Windows acceptance is separate from the
passing shared/adapter tests.

Capture the actual OS event. Fn is keyboard-dependent. On the tested MX Keys
Mini, brief Fn+O and plain O produced the same Qt key 79, scan code 32, virtual key
111 and no modifiers; Fn alone produced no event. Solaar also reported Fn as
non-divertable. Fn+O cannot be registered separately through the current shortcut
interface. Do not label plain O as Fn+O or silently assign a substitute. This
entry's shortcut remains unassigned pending an owner choice or a supported
keyboard-level mechanism.

## Qualification — October 8, 2026

The feature branch starts from public main `79784a5`. The owner's dirty canonical
checkout and unrelated worktrees are preserved. The installed Linux baseline is
compatible product 0.2.11, selected release `20261005-095559-8aa03c9b`, artifact
SHA-256 `d0f0386d4b37cc41dbcf53d3ecf49be33e1b583b13afe15bf57d46fc73b002a8`.
It contains the approved settings frame and specialist-workspace infrastructure
that cannot be replaced wholesale by the current source 0.2.13 artifact.

Source qualification: type/build checks pass; Node suite has 513 passes and two
existing skips; native suite has 875 cases with 36 skips. Independently authored
fixtures cover migration, retained bindings, stale revisions, shortcut conflicts,
failed-commit restoration, strict preset/folder ownership and missing presets.
The optional real-DSH test uses the installed 0.2.0-rc.2 runtime with an invented
loopback model, proves separate effective personas/tools/permissions, rejects an
inherited tool from the independent agent and successfully executes it from the
sibling. No private Olares definition or real-system data appears in that test.

Reproduce that runtime proof by setting `DSH_INSTALL_ROOT` to the installed DSH
package directory and running `node --test tests/dsh-independent-presets.test.mjs`.
Without the explicit runtime it is an opt-in skip, not runtime acceptance.

The installed overlay recipe is `scripts/stage-native-agents-overlay.py`: copy an
immutable compatible artifact to a fresh candidate, apply the feature and keep
its product version/dependencies/approved UI. The candidate passes the seven new
native cases and its Agents form has been visually inspected in the existing
settings frame. Follow [managed deployments](DESKTOP-DEPLOYMENTS.md) for stage,
activation and selected-versus-running evidence. This source qualification does
not itself select a release or prove a live owner-model request.

Olares-specific isolation verification and its integration on port 3080 remain
pending. Two isolated fixture startup failures involved missing services and a
duplicate filesystem provider, before any live Olares request. Its repository's
`IMPLEMENT.md` requires asking after two failures, so that fixture remains paused
for the owner's answer. No live Olares configuration, gateway safeguards or
model-server settings have been changed. The existing dedicated launcher remains
separate. Only a read-only status request is needed for eventual live acceptance.

The first live Linux adoption exposed a public-launcher name mismatch in the new
Open action. It is corrected to the installer-owned `augmentor-agent` entrypoint
and covered by an installer-contract test. Primary startup also required waiting
for the old systemd unit to finish exiting after guarded close; a successful
`start` issued while that unit was still active had not launched a replacement.
The old window closed cleanly and its saved conversation/model were preserved.

Live read-only KDE inspection also found that the compatible developer artifact
had its real main/secondary bindings under `com.augmentor.Agent.desktop`, while
the old settings helper looked under the development namespace because it
recognized only `release.json`. Managed `desktop-release.json` artifacts now
resolve the installed namespace, preserving the existing Fn+Space bindings.
The six KDE adapter cases pass, including managed namespace resolution and
failed registry-commit restoration. No existing shortcut was reassigned.
