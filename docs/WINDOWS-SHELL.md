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

Before delivering a user-initiated Show/Toggle request, the launcher/shortcut owner
offers its foreground permission to the kernel-authenticated pipe server PID with
`AllowSetForegroundWindow`. Windows may still refuse focus; Augmentor does not
inject keys or attach input queues to override that policy. The shared window
then performs its normal Qt activation. Real foreground/input acceptance remains
a physical-machine check. [Windows foreground handoff](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-allowsetforegroundwindow).

The embedded launcher intentionally excludes arbitrary PATH/current-directory DLL
search. Its Python entrypoint retains explicit DLL-directory handles for private
Python, PySide and Shiboken libraries and selects the bundled Qt plugin directory.
This allows separately loaded image plugins to resolve their Qt dependencies
without restoring global DLL search. [Python DLL directories](https://docs.python.org/3/library/os.html#os.add_dll_directory).

The product build embeds the existing Augmentor vector icon at seven sizes
(16–256 pixels), the shared product version, and an ordinary-user application
manifest. Per-monitor V2 DPI awareness prevents Windows from treating the entire
window as an old bitmap-scaled application. Long-path awareness is declared;
this does not remove Windows policy or third-party path limits. The OS compatibility
GUID is the shared Windows 10/11 manifest identifier, not a Windows 10 product
support commitment. Native qualification reads these resources back from the
compiled executable. Mixed-monitor DPI and Explorer/taskbar visuals still need
physical Windows acceptance. See [Microsoft application manifests](https://learn.microsoft.com/en-us/windows/win32/sbscs/application-manifests).

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

## Login registration mechanism

`windows_startup.py` provides one owned HKCU Run value pointing to the installer's
stable `current/Augmentor.exe --background` path. It does not resolve that path
to a version directory. Repeated registration performs no write, unfamiliar values
are preserved, and removal deletes only the exact owned command. It never changes
HKLM or Windows `StartupApproved` state. The executable's background mode starts
the same per-user supervisor without opening a chat window. Source launches do
not enable login startup; installer hooks still need to call this mechanism.
Native tests use a disposable HKCU key, not the actual login key. Real Windows
startup-disable behavior and logout/login still require installed acceptance.

## Shared companion ownership

The supervisor additionally exposes fixed `start-prompts` and `start-memory`
operations. Each launches only its shipped service, with the private interpreter,
inside a separate Windows Job retained by the same supervisor. Repeated starts
reuse the live child. An already-running endpoint outside that owner is preserved
and reported as a conflict; no process is adopted or killed by filename or PID.
Status distinguishes the Job helper PID from the service PID. Logs remain in the
private supervisor directory. A supervisor crash closes its Jobs and contains
their descendants. This is fault containment, not graceful product Quit.

The native test queries both actual services, checks repeat-start identity,
refuses an empty-owner exit while they run and observes their kernel process
handles after a deliberate supervisor fault. This passes on both native CPUs at
`840127f`. Python and Node clients now request fixed startup operations through
that owner only when their service endpoint is proven absent. Node uses a bounded
private-Python helper; it never starts the service daemon itself on Windows.
Timeouts or lost responses after a connection do not replay the original request.
Already-running service endpoints retain their existing transport behavior.
The companion-client test adds real Python cold startup, Node memory startup,
prompt save/restart and continued memory-process identity. Native execution of
that client adoption remains pending. Service quiescence and accepted-request draining
remain required for ordinary shutdown and updates.

## Remaining shell gates

The shared instance handler now drains commands already queued while the window
was being constructed. A Qt event processed before `newConnection` was connected
could otherwise leave the first command waiting until another arrival. This is
a shared startup correction; native regression of the new source is pending.

This source does not yet complete tray Open/Quit, installer login hooks, installed
Start menu/taskbar identity, coordinated busy-work shutdown or update ownership.
These remain required before customer distribution. A successful preview or
hotkey backend test must not be described as an installed Windows application.

References: [Microsoft RegisterHotKey](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-registerhotkey)
and [Qt native event filters](https://doc.qt.io/qt-6/qabstractnativeeventfilter.html).
