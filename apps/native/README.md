<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Native desktop surface

The maintained Python surface uses **PySide6 / Qt**, not the historical PyQt6
implementation. `augmentor_linux/window.py` owns composition; `controller.py`
coordinates the selected Pi or DSH adapter. Model execution remains in that
harness. See [current architecture](../../docs/ARCHITECTURE.md) and
[feature matrix](../../docs/FEATURE-MATRIX.md) for platform/capability limits.

| Concern | Entry points and guide |
| --- | --- |
| Pi transport and startup | `pi_client.py`, `runtime_start.py`; [protocol](../../docs/PROTOCOL.md) |
| DSH sessions and interactions | `adapters/dsh*.py`; [setup](../../docs/DSH-SETUP.md) |
| Rendering, prompts and commands | `transcript.py`, `markdown.py`, `composer.py`, `prompts.py`; [commands](../../docs/SLASH-COMMANDS.md) |
| Memory controls | `memory.py`, `dual_memory.py`, `prompt_client.py`; [automatic](../../docs/DUAL-MEMORY.md), [manual](../../docs/MEMORY.md) |
| Audio | `voice.py`, `voice_button.py`, `voice_settings.py`, `voice_vad.py`, `voice_echo.py`; [hands-free](../../docs/HANDS-FREE-IMPLEMENTATION.md) |
| Appearance and windows | `skins.py`, `backgrounds.py`, `preferences.py`, `instances.py`, `shortcuts.py`; [skins](../../docs/SKINS.md), [second window](../../docs/SECOND-WINDOW.md) |
| Recovery and support | `recovery.py`, `support.py`; [recovery](../../docs/DESKTOP-OFFLINE-RECOVERY.md) |

Run native tests from the repository root with its Python/Qt environment:
`npm run test:native`. Actual pointer/clipboard, first-run, package and platform
acceptance are separate checks described in [tests](../../tests/README.md).
Hiding a window must not cancel its task; Stop must remain explicit. Do not
restart an active installed window to verify a source-only documentation change.
