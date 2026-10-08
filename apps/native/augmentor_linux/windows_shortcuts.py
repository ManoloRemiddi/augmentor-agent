# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Native Windows hotkeys, owned by the background Qt thread, not a window."""
import ctypes
from ctypes import wintypes
from itertools import count
import os
from pathlib import Path
import sys

from PySide6.QtCore import QAbstractNativeEventFilter, QCoreApplication, QObject, QThread, Qt, Signal
from PySide6.QtGui import QKeySequence

from .platform_runtime import private_directory
from platform_adapters.private_files import atomic_json, read_json

ROOT = Path(__file__).resolve().parents[3]
DEFAULTS = {'main': 'Ctrl+Alt+Space', 'secondary': 'Ctrl+Alt+Shift+Space'}
WM_HOTKEY, MOD_NOREPEAT = 0x0312, 0x4000
_identifiers = count(0x2000)


def binding(sequence):
    """Map an explicit Qt key combination to Windows modifiers/virtual key."""
    if isinstance(sequence, str):
        sequence = QKeySequence(sequence, QKeySequence.SequenceFormat.PortableText)
    if sequence.isEmpty() or sequence.count() != 1:
        raise ValueError('Choose one key combination.')
    combination = sequence[0]
    modifiers = combination.keyboardModifiers()
    allowed = Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.ShiftModifier
    if modifiers & ~allowed or not modifiers & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier):
        raise ValueError('Use Ctrl or Alt, optionally with Shift. Windows-key combinations are reserved by Windows.')
    key = int(combination.key())
    special = {Qt.Key.Key_Space: 0x20, Qt.Key.Key_Tab: 0x09, Qt.Key.Key_Return: 0x0d,
               Qt.Key.Key_Escape: 0x1b, Qt.Key.Key_Backspace: 0x08,
               Qt.Key.Key_Insert: 0x2d, Qt.Key.Key_Delete: 0x2e,
               Qt.Key.Key_Home: 0x24, Qt.Key.Key_End: 0x23,
               Qt.Key.Key_PageUp: 0x21, Qt.Key.Key_PageDown: 0x22,
               Qt.Key.Key_Left: 0x25, Qt.Key.Key_Up: 0x26, Qt.Key.Key_Right: 0x27, Qt.Key.Key_Down: 0x28}
    if ord('A') <= key <= ord('Z') or ord('0') <= key <= ord('9'): virtual_key = key
    elif int(Qt.Key.Key_F1) <= key <= int(Qt.Key.Key_F24) and key != int(Qt.Key.Key_F12):
        virtual_key = 0x70 + key - int(Qt.Key.Key_F1)
    elif key in special: virtual_key = special[key]
    else: raise ValueError('Choose a letter, number, Space, navigation key or function key other than F12.')
    native = ((2 if modifiers & Qt.KeyboardModifier.ControlModifier else 0) |
              (1 if modifiers & Qt.KeyboardModifier.AltModifier else 0) |
              (4 if modifiers & Qt.KeyboardModifier.ShiftModifier else 0))
    return native, virtual_key, combination.toCombined(), sequence.toString(QKeySequence.SequenceFormat.PortableText)


class NativeFilter(QAbstractNativeEventFilter):
    def __init__(self, owner): super().__init__(); self.owner = owner
    def nativeEventFilter(self, event_type, message):
        if bytes(event_type) in (b'windows_dispatcher_MSG', b'windows_generic_MSG'):
            event = wintypes.MSG.from_address(int(message))
            if event.message == WM_HOTKEY and self.owner.deliver(int(event.wParam)):
                return True, 0
        return False, 0


class Hotkeys(QObject):
    pressed = Signal(str)
    def __init__(self, parent=None):
        if sys.platform != 'win32': raise RuntimeError('Windows hotkeys require Windows.')
        super().__init__(parent)
        self.app = QCoreApplication.instance()
        if self.app is None: raise RuntimeError('Windows shortcuts need the background event loop.')
        self.user = ctypes.WinDLL('user32', use_last_error=True)
        self.user.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
        self.user.RegisterHotKey.restype = wintypes.BOOL
        self.user.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
        self.user.UnregisterHotKey.restype = wintypes.BOOL
        self.active = {}; self.identifiers = set(); self.closed = False
        self.filter = NativeFilter(self); self.app.installNativeEventFilter(self.filter)

    def require_thread(self):
        if QThread.currentThread() != self.thread(): raise RuntimeError('Shortcut changes require their owner thread.')
        if self.closed: raise RuntimeError('The shortcut owner is closed.')

    def assign(self, instance, sequence, persist=lambda _text: None):
        self.require_thread()
        from .instances import validate_name
        validate_name(instance)
        parsed = binding(sequence)
        old = self.active.get(instance)
        if any(name != instance and item[1][:2] == parsed[:2] for name, item in self.active.items()):
            raise ValueError('That shortcut is already assigned to the other agent.')
        if old and old[1][:2] == parsed[:2]:
            persist(parsed[3]); return parsed[2]
        identifier = next(_identifiers)
        if identifier > 0xbfff: raise RuntimeError('Restart Augmentor before changing more shortcuts.')
        if not self.user.RegisterHotKey(None, identifier, parsed[0] | MOD_NOREPEAT, parsed[1]):
            raise ValueError('Windows could not assign that shortcut. It may be used by another app; choose another combination.')
        self.identifiers.add(identifier)
        try: persist(parsed[3])
        except BaseException:
            self.release(identifier); raise
        self.active[instance] = identifier, parsed
        if old: self.release(old[0])
        return parsed[2]

    def release(self, identifier):
        if self.user.UnregisterHotKey(None, identifier): self.identifiers.discard(identifier)
        # Retain a failed unregister for close(), but never dispatch an obsolete
        # binding or reuse its identifier while an old message may be queued.

    def deliver(self, identifier):
        for instance, (current, _parsed) in self.active.items():
            if current == identifier: self.pressed.emit(instance); return True
        return identifier in self.identifiers

    def close(self):
        if self.closed: return
        self.require_thread()
        self.active.clear()
        for identifier in list(self.identifiers): self.release(identifier)
        self.app.removeNativeEventFilter(self.filter); self.closed = True


class ShortcutOwner:
    def __init__(self):
        self.hotkeys = Hotkeys()
        self.errors = {name: None for name in DEFAULTS}
        self.directory = private_directory(Path(os.environ['XDG_CONFIG_HOME'])/'augmentor')

    def path(self, instance):
        from .instances import validate_name
        validate_name(instance)
        return self.directory/('shortcut.windows.'+instance+'.json')

    def restore(self):
        from .agent_entries import entries
        for entry in entries():
            instance=entry['id'];default=DEFAULTS.get(instance)
            if default is None and not self.path(instance).exists():continue
            try:
                try:
                    record = read_json(self.path(instance))
                    if set(record) != {'sequence'} or not isinstance(record['sequence'], str): raise ValueError('Invalid saved shortcut.')
                    sequence = record['sequence']
                except FileNotFoundError: sequence = default
                self.hotkeys.assign(instance, sequence)
            except Exception as error: self.errors[instance] = str(error)

    def dispatch(self, message):
        instance = message.get('instance')
        path = self.path(instance)
        if message.get('action') == 'shortcut-save' and set(message) == {'action', 'instance', 'sequence'}:
            sequence = message['sequence']
            if not isinstance(sequence, str) or len(sequence) > 256: raise ValueError('Invalid shortcut sequence.')
            self.hotkeys.assign(instance, sequence, lambda text: atomic_json(path, {'sequence': text}))
            self.errors[instance] = None
        elif message.get('action')=='shortcut-remove' and set(message)=={'action','instance'}:
            path.unlink(missing_ok=True)
            old=self.hotkeys.active.pop(instance,None)
            if old:self.hotkeys.release(old[0])
        elif message.get('action') != 'shortcut-status' or set(message) != {'action', 'instance'}:
            raise ValueError('Unsupported shortcut operation.')
        active = self.hotkeys.active.get(instance)
        return {'instance': instance, 'active': active is not None, 'key': active[1][2] if active else None,
                'error': self.errors.get(instance)}

    def close(self): self.hotkeys.close()


def current_keys(instance='main'):
    from windows_supervisor import request
    status = request('shortcut-status', root=ROOT, instance=instance)
    return [status['key']] if status['active'] else []


def save_shortcut(sequence, instance='main'):
    from windows_supervisor import request
    parsed = binding(sequence)
    return request('shortcut-save', root=ROOT, instance=instance, sequence=parsed[3])['key']
