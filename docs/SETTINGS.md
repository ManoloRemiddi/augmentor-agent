<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Settings organization and thinking display

## Desktop

Settings now opens on Conversation, with six named categories in a sidebar.
At widths below 620 pixels a category dropdown replaces the sidebar; the selected
page and its edits are retained. Each category scrolls independently and Done
remains outside the scrolling area.

| Category | Existing controls |
| --- | --- |
| Conversation | Thinking display; Prompt library |
| Appearance | Colours, skins, backgrounds and visual effects |
| Voice | Resonant Voice configuration |
| Connections | DSH/Pi engine selection, Connect DSH, Connect Home, Recover connection |
| Shortcuts | Existing first/second-window shortcut editors and Save actions |
| Data & support | Memory and Support report |

The original actions and dialogs remain connected to the same callbacks. Model,
voice, memory, connection and shortcut settings are not reset by reorganizing the
page. Appearance follows the current light/dark theme.

## Thinking choice

**Settings → Conversation → Thinking display → While thinking** offers:

- **Open — show live thinking** (default, including existing profiles).
- **Collapsed** (thinking is available through its existing expansion control).

The choice saves immediately and applies to active thinking and future responses.
When thinking ends it still collapses automatically. Manual expansion/collapse
remains available, and repeated chunks or unchanged preference refreshes preserve
a manual choice within the current thinking phase. Changing the preference does
not expand or close previously completed thinking boxes. Request-progress labels,
answer text, tool execution and model reasoning settings are unchanged.

Native preferences store the boolean `expand_thinking` in the existing scoped
appearance profile. A newly created named window inherits the initial primary
value, then keeps its own choice, like other window preferences. Existing settings
files default to Open; invalid stored types fall back to that default.

Browser source adds Conversation as its default Settings category, renames Colours
to Appearance and Harnesses to Connections, and exposes the same choice. The
existing surface-preferences bridge shares `expandThinking` with the primary
floating window. Colour-only updates preserve the thinking preference, and invalid
boolean writes are rejected. Browser mirrors the value to its existing preference
storage and refreshes live chat through its existing appearance notifications/poll;
named native windows keep their independent preference. Browser and desktop
installation/adoption are separate.

## Qualification and deployment

The full native workspace suite ran 509 tests successfully (two macOS-only checks
skipped). Browser DOM/transport checks passed 54 tests, plus the new Settings page
DOM test, covering restore/save through the shared preference API. Focused Qt tests
verify persistence, current/future thinking, manual controls, both navigation
layouts and retained setting actions. Screenshots were inspected at 760 and 400
pixels in dark and light themes; this caught and corrected page-background contrast.
These are real offscreen widgets and synthetic fixtures, not Mac installed tests.

Implementation `d4ab5fd` was applied to a separate candidate copied from selected
release `20260927-234746-0c414bcb` (SHA-256
`7f43ebcdbf87f24709a59563583dbb4c97726345ed9313dcd7fa275045bd3a72`).
Only the native Settings/preferences/rendering files and shared preference service
were patched; the installed Linux panel's existing platform differences were
preserved. The candidate passed 62 focused native checks and managed stage and
authenticated activation checks.

Managed release `20260928-000201-bcc8c6e5`, SHA-256
`bbb98668f777bd926705f047ed7fd8de4d0aa21303f4a16c046b6b9f148672ad`, is selected. The primary and mobile windows accepted
graceful close and were restarted, and now report that build, online/model-ready
with no session-restore error. The primary window is open. The secondary window
was running a task, so its work was preserved. A one-shot local update operation,
`augmentor-settings-secondary-adoption.service`, is actively waiting for that
window to become idle. It uses the same guarded close operation and canonical
launcher, verifies the selected build and readiness, then exits. It makes no
model request and exits without a restart if superseded by a newer selection.
Its owner-only result is under the local state directory's
`augmentor/updates/settings-secondary-adoption.json`. This is pending secondary
adoption, not a claim that its running build has already changed.
Public releases, installed Mac and the loaded Browser extension are unchanged;
Browser source and its shared preference path are tested but not deployed here.
