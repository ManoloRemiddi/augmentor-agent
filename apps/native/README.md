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

The existing two shortcut rows select KDE KGlobalAccel, macOS or the native GNOME
50 settings adapter. GNOME requires GTK 4 GI in the selected interpreter and a
live Shell/MediaKeys graphical session; failures stay explicit in those rows.
See [distro qualification and limits](../../docs/LINUX-DISTRO-ROLLOUT.md#october-2-native-gnome-save-adapter):
the private daemon proof covers Save/conflicts. Separate actual Augmentor preview
window proofs pass canonical shortcut hide/restore, compositor focus and composer
typing for XWayland/native Wayland. Separate full Fedora VM proofs cover canonical
closed launch, duplicate autostarts, lock recovery, idle crash and reboot for the
earlier clean `f7d7585` installed package. A later full-session managed proof
starts clean `8244c9c` through the canonical xcb launcher and verifies actual early
portal registration and focused/rendered onboarding. Its updater uses a separately
recorded staging correction; clean combined artifacts, full native-Wayland startup,
connected tasks and physical keys remain open. The GNOME XWayland workspace proof also passes independent pin/unpin/follow
through the existing controls. Native packages declare `wmctrl`; GNOME unpin
uses its own window's sticky-removal request without needing an initially absent
root-desktop hint. Native Wayland following remains a separate adapter gap.

The desktop identity is supplied before constructing `QApplication`, because Qt's
Unix platform services can call the portal during construction. A full-session
standalone Qt 6.11.2 fixture reproduces late registration's cached-identity D-Bus
error and verifies successful early registration on both xcb and Wayland. Working
source at the identity stage passes 643 native cases (two Mac-only skips) and the separate private
shortcut/focus/typing/workspace checks. This does not qualify the separate control
helper's consent identity or portal restart registration; see the
[identity report and limits](../../docs/LINUX-DISTRO-ROLLOUT.md#early-qt-desktop-identity).

The canonical Linux launcher exports the selected Python interpreter to child
helpers. DSH's Linux support uses the same shared executable/environment
adapter. The Ubuntu 24.04 managed-runtime foundation and its explicit system
GI bridge are tracked in [the distro rollout](../../docs/LINUX-DISTRO-ROLLOUT.md);
its import/render fixture does not yet qualify a Noble installation.
