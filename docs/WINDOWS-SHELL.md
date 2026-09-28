<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Windows desktop and background controls

This is an implementation contract for the development candidate, not a customer
installation guide. See the [implementation evidence](WINDOWS-IMPLEMENTATION-STATUS.md)
and [W4 plan](WINDOWS-IMPLEMENTATION-PLAN.md#w4--complete-the-native-windows-desktop-experience).

The shared desktop retains its existing appearance, settings and two independent
windows. `Augmentor.exe` embeds the private Python runtime and selects the common
desktop module. Repeat app launches request Show. The shortcut activation helper
uses the same authenticated instance endpoint to request Toggle; an absent
endpoint permits a cold launch, while an uncertain delivery never gets replayed.

The embedded launcher intentionally excludes arbitrary PATH/current-directory DLL
search. Its Python entrypoint retains explicit DLL-directory handles for private
Python, PySide and Shiboken libraries and selects the bundled Qt plugin directory.
This allows separately loaded image plugins to resolve their Qt dependencies
without restoring global DLL search. [Python DLL directories](https://docs.python.org/3/library/os.html#os.add_dll_directory).

## Keyboard ownership

The existing Windows supervisor now hosts a Qt event loop and owns both native
`RegisterHotKey` registrations, independently of either desktop window. Defaults
are Ctrl+Alt+Space and Ctrl+Alt+Shift+Space. A collision leaves the affected default
unassigned; the shared Settings editor can choose an available combination. The
Windows adapter supports Ctrl/Alt with optional Shift and letters, digits, Space,
navigation keys and function keys except F12. Windows-key combinations and bare
keys are refused. Keyboard-layout and physical-input acceptance remains pending.

Only the owner thread registers, unregisters or edits shortcuts. Named-pipe
workers queue an explicit Qt slot. A settings save registers the proposed binding,
atomically writes its private user-owned record, then releases the old binding.
An OS collision or failed file write keeps the previous live choice and record.
The two agent windows cannot claim the same combination. Obsolete queued messages
cannot activate a replacement binding; identifiers are not reused. `MOD_NOREPEAT`
prevents held-key repeat notifications. Shutdown unregisters owned bindings.

The only added supervisor requests are `shortcut-status` and `shortcut-save`, with
fixed fields and one of the two supported window identities. Pipe authentication
and application-root matching remain required. A timed-out save is not replayed;
Settings must read the current value before another explicit save. Activation runs
outside the event loop, with at most one outstanding action per window.

Native tests exercise actual OS collision rejection, file-save rollback, queued
`WM_HOTKEY` delivery through Qt, release and two-window separation. A posted
message is explicitly not physical keyboard evidence. The supervisor integration
test verifies persistence and worker-to-owner dispatch through the private pipe.

## Remaining shell gates

This source does not yet complete tray Open/Quit, login registration, installed
Start menu/taskbar identity, coordinated busy-work shutdown or update ownership.
These remain required before customer distribution. A successful preview or
hotkey backend test must not be described as an installed Windows application.

References: [Microsoft RegisterHotKey](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-registerhotkey)
and [Qt native event filters](https://doc.qt.io/qt-6/qabstractnativeeventfilter.html).
