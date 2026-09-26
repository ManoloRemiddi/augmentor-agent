<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Independent second window

`augmentor-linux --instance secondary` opens a separate native process with its
own conversation metadata, appearance/placement, and local activation socket.
Repeated launches toggle that same named window. The default invocation retains
its original socket and files. Both windows share the existing harness services,
prompt library and model catalog.

## Cross-platform requirement

Two independent instances are a product feature on both Linux and macOS. The
current Mac shortcut integration exposes only main; that is an unfinished port,
not the intended product difference. The [parity audit](PLATFORM-PARITY-AUDIT.md)
traces the missing service/activation work and records the shared instance tests
passing on both OSs. No second Mac shortcut is implemented by this documentation.

## Settings

Either window's Settings → Window shortcuts has separate capture fields and Save
buttons for the first and second agents. Each field records the combination the
keyboard actually sends. Conflicting assignments are rejected; failed KDE updates
restore the previous binding and launcher files. Entries persist for later desktop
sessions. This two-window launcher integration currently targets KDE.

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
