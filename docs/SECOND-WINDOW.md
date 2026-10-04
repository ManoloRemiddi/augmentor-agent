<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Independent second window

`augmentor-linux --instance secondary` opens a separate native process with its
own conversation metadata, appearance/placement, and local activation socket.
Repeated launches toggle that same named window. The default invocation retains
its original socket and files. Both windows share the existing harness services,
prompt library and model catalog.

## Cross-platform requirement

Two independent instances are a product feature on both Linux and macOS. The Mac login service now owns both shortcuts with separate persistence and
instance-targeted activation. Main defaults to Fn+Space; secondary remains unassigned
until saved. See [implementation and qualification](MACOS-RECOVERY-2026-09-26.md).
The earlier [parity audit](PLATFORM-PARITY-AUDIT.md) records why this was required.

The Windows implementation branch connects this same instance command handler
to SID-authenticated named pipes and protected per-window owner locks. Pipe
commands cross to Qt's main thread; the shared UI still decides whether drafts
or active work block maintenance. Clicking the Windows application focuses an
existing window. Explicit toggle commands remain available for shortcuts.
Native CI adds two actual Windows-QPA preview processes, duplicate launch, draft
isolation, busy-close refusal and live zoom checks. Those checks are pending;
they do not establish installed launchers, global shortcuts or full chat parity.
See the [Windows evidence ledger](WINDOWS-IMPLEMENTATION-STATUS.md).

## Settings

Either window's Settings → Window shortcuts has separate capture fields and Save
buttons for the first and second agents. Each field records the combination the
keyboard actually sends. Conflicting assignments are rejected; failed KDE updates
restore the previous binding and launcher files. Entries persist for later desktop
sessions. Both KDE and macOS provide this two-window launcher integration.

Colours & visual effects saves to each window's own appearance file, including
custom skins, formatting colours, backgrounds and visual effects. Resonant Voice
saves the selected voice, speed and volume to that window's speech-service profile;
voice mode, pause tolerance and enablement remain in its appearance preferences.

A new named window copies the primary appearance and model selection once, but
never its conversation ID. It keeps independent placement and immediately saves
its appearance clone. When the voice service is available, first opening also
creates its independent voice profile. If voice is offline, that clone is deferred
until the first successful voice connection or Settings request. Later primary
changes do not overwrite existing secondary preferences. Existing second-window
customizations are preserved. Names are limited to 1–32 lowercase letters, digits
and hyphens, starting with a letter.

## Keyboard correction and evidence — 19 September 2026

A focused **physical keyboard** capture recorded Fn+Option/Alt+Space as
`Meta+Hangul`: Qt key 16781617, modifiers 268435456, native scan code 130, native
virtual key 65329. The earlier `Alt+Hangul` assumption was wrong. The installed
`com.augmentor.Agent.secondary.desktop` now binds `Meta+Hangul` to the voice preview
launcher with `--instance secondary`. The primary `Hangul` binding is unchanged.

Verification:

- 11 shortcut tests, 3 instance-isolation tests, 24 window tests, 46 native voice
  tests and 7 skin tests passed. Voice settings tests are included in the 46.
- All 33 speech-service tests passed, including clone-once/restart persistence and
  real HTTP/WebSocket profile routing with fake synthesis (no GPU inference).
- Exercised the **installed** Settings capture field and Save button against real
  KDE; read back both bindings and confirmed the primary was unchanged.
- Injected Linux Meta+Hangul and Hangul through the desktop input system. Each
  combination hid and reopened only its own running window, retaining the same
  process IDs. This is desktop integration evidence; the final replay was synthetic,
  using the event measured from the physical keyboard.
- Exercised the installed Resonant Voice dialog against the running service:
  changed secondary speed/volume, reopened and read them back, checked the primary
  was unchanged, then restored the secondary's original values. No microphone or
  model prompt was used.
- Rendered and inspected Settings; fixed the scroll area's background contrast.

Local proof files are under ignored `outputs/`: `shortcut-key-probe.json`,
`installed-shortcut-proof.json`, and `installed-two-window-settings.png`.
The targeted source changes are installed in the Resonant Voice preview and in the
running voice companion. Backups are under
`~/.local/state/augmentor-repair-backups/two-window-settings-20260919-131032/`.
