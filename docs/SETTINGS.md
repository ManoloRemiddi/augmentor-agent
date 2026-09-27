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

Source and installed candidate identities and restart evidence are recorded here
after the managed update. Public releases and the loaded Browser extension are
not implicitly replaced by this source change.
