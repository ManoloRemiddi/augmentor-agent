# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Owned macOS hotkey process and persisted choice, independent of KDE."""
import json
import errno
import os
from pathlib import Path
import selectors
import subprocess
import tempfile
import threading
import sys
import time
from PySide6.QtCore import QObject,Signal,Qt
from PySide6.QtGui import QKeySequence

ROOT=Path(__file__).resolve().parents[3]
manager=None

def configuration():
    base=Path(os.environ.get('XDG_CONFIG_HOME',Path.home()/'Library/Application Support/Augmentor/config'))
    return base/'augmentor/shortcut.json'

def current_keys():
    path=configuration()
    if not path.exists():return []
    sequence=QKeySequence(json.loads(path.read_text())['sequence'],QKeySequence.SequenceFormat.PortableText)
    if sequence.isEmpty() or sequence.count()!=1:raise ValueError('The saved shortcut is invalid.')
    return [sequence[0].toCombined()]

class ShortcutManager(QObject):
    pressed=Signal()
    problem=Signal(str)
    def __init__(self,parent=None):
        super().__init__(parent);self.process=None;self.key=None;self.binding=None;self.lock=threading.RLock();self.closed=False
        self.helper=Path(os.environ.get('AUGMENTOR_MACOS_HOTKEY',str(ROOT/'native/augmentor-hotkey')))

    def command(self,sequence):
        if sequence.isEmpty() or sequence.count()!=1:raise ValueError('Choose one key combination.')
        combination=sequence[0];key=int(combination.key());modifiers=combination.keyboardModifiers()
        # Qt intentionally maps ControlModifier to Command and MetaModifier to
        # Control on macOS; use its semantics rather than the displayed names.
        mask=sum(value for flag,value in [(Qt.KeyboardModifier.ControlModifier,256),
            (Qt.KeyboardModifier.ShiftModifier,512),(Qt.KeyboardModifier.AltModifier,2048),
            (Qt.KeyboardModifier.MetaModifier,4096)] if modifiers&flag)
        if not mask or modifiers&Qt.KeyboardModifier.KeypadModifier:
            raise ValueError('Choose a modified shortcut outside the numeric keypad.')
        names=('Left','Right','Up','Down','Home','End','PageUp','PageDown','Escape','Tab','Return','Backspace','Delete')
        special={int(getattr(Qt.Key,'Key_'+name)):'@'+name for name in names}
        special.update({int(Qt.Key.Key_F1)+n:'@F'+str(n+1) for n in range(20)})
        symbol=special.get(key,chr(key) if 32<=key<0x1000000 else None)
        if symbol is None:raise ValueError('That key is not supported for macOS shortcuts.')
        result=subprocess.run([str(self.helper),'--resolve',symbol],capture_output=True,text=True,timeout=5)
        response=json.loads(result.stdout)
        if result.returncode:raise ValueError(response.get('error','Could not resolve this shortcut.'))
        return [str(self.helper),str(response['keyCode']),str(mask)]

    @staticmethod
    def stop(process):
        if process is None:return
        try:process.stdin.close()
        except (OSError,ValueError):pass
        try:process.wait(timeout=3)
        except subprocess.TimeoutExpired:process.kill();process.wait()

    def save(self,sequence,persist=True):
        with self.lock:
            if self.closed:raise RuntimeError('The shortcut owner has closed.')
            command=self.command(sequence);key=sequence[0].toCombined()
            if self.key==key and self.binding==command and self.process and self.process.poll() is None:return key
            child=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
            try:
                with selectors.DefaultSelector() as selector:
                    selector.register(child.stdout,selectors.EVENT_READ)
                    if not selector.select(5):raise RuntimeError('macOS shortcut registration timed out.')
                    ready=json.loads(child.stdout.readline())
                if ready.get('event')!='ready':raise ValueError(ready.get('error','Shortcut registration failed.'))
                if persist:
                    path=configuration();path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
                    fd,temporary=tempfile.mkstemp(prefix='.shortcut-',dir=path.parent)
                    try:
                        with os.fdopen(fd,'w') as stream:
                            json.dump({'sequence':sequence.toString(QKeySequence.SequenceFormat.PortableText)},stream)
                            stream.flush();os.fsync(stream.fileno())
                        os.replace(temporary,path)
                    finally:Path(temporary).unlink(missing_ok=True)
            except BaseException:
                self.stop(child);child.stdout.close();raise
            previous=self.process;self.process=child;self.key=key;self.binding=command
            self.stop(previous)
            threading.Thread(target=self.watch,args=(child,),daemon=True).start()
            return key

    def watch(self,child):
        for line in child.stdout:
            try:event=json.loads(line)
            except ValueError:continue
            if child is self.process and event.get('event')=='pressed':self.pressed.emit()
            if child is self.process and event.get('event')=='layoutChanged':
                try:self.save(QKeySequence(self.key),persist=False)
                except Exception as error:
                    # A stale physical binding could activate on the wrong key.
                    # Release it if the new layout cannot resolve/register it.
                    with self.lock:
                        if child is self.process:
                            self.process=None;self.binding=None;self.stop(child)
                    self.problem.emit('Keyboard layout changed; save your shortcut again: '+str(error))
        child.stdout.close()
        if child is self.process and not self.closed:self.problem.emit('The macOS shortcut stopped. Save it again in Settings.')

    def restore(self):
        keys=current_keys()
        if keys:self.save(QKeySequence(keys[0]),persist=False)

    def close(self):
        with self.lock:
            self.closed=True;child=self.process;self.process=None;self.stop(child)

    def release(self):
        with self.lock:
            child=self.process;self.process=None;self.binding=None;self.stop(child)

class RemoteShortcutManager(QObject):
    """Settings client; closing a desktop window must not stop the service."""
    pressed=Signal()
    problem=Signal(str)

    def save(self,sequence):
        from .macos_shortcut_service import request
        return request({'operation':'save','sequence':sequence.toString(QKeySequence.SequenceFormat.PortableText)})['key']

    def restore(self):
        from .macos_shortcut_service import request
        status=request({'operation':'status'})
        if status.get('error'):self.problem.emit(status['error'])

    def close(self):
        pass


class ManagedShortcutManager(RemoteShortcutManager):
    """Enable login ownership when a packaged app saves its shortcut."""
    def __init__(self,parent=None):
        super().__init__(parent)
        self.local=ShortcutManager(self)
        self.local.pressed.connect(self.pressed)
        self.local.problem.connect(self.problem)
        self.lock=threading.RLock()

    def ensure_service(self):
        from .macos_shortcut_service import request
        try:
            status=request({'operation':'status'})
        except OSError as error:
            if error.errno not in (errno.ENOENT,errno.ECONNREFUSED):raise
        else:
            if status.get('protocol')!=1:raise RuntimeError('Unsupported shortcut service version.')
            return
        application=ROOT.parents[2]
        result=subprocess.run([sys.executable,'-I','-B',str(ROOT/'scripts/register-macos-shortcut.py'),
                               str(application),'install'],capture_output=True,text=True,timeout=45)
        if result.returncode:
            raise RuntimeError('Could not start the login shortcut service: '+(result.stderr.strip() or result.stdout.strip()))
        deadline=time.monotonic()+15
        while True:
            try:
                status=request({'operation':'status'})
                if status.get('protocol')!=1:raise RuntimeError('Unsupported shortcut service version.')
                return
            except OSError as error:
                if error.errno not in (errno.ENOENT,errno.ECONNREFUSED):raise
                if time.monotonic()>=deadline:raise RuntimeError('The login shortcut service did not become ready. Try saving again.') from error
                time.sleep(0.1)

    def save(self,sequence):
        with self.lock:
            # Reject unsupported combinations before releasing an existing key.
            self.local.command(sequence)
            self.local.release()
            self.ensure_service()
            # One save attempt only. An uncertain acknowledgement never causes
            # local re-registration or replay of the settings operation.
            return super().save(sequence)

    def restore(self):
        with self.lock:
            registration=Path.home()/'Library/LaunchAgents/com.augmentor.Agent.shortcut.plist'
            if registration.exists() or registration.is_symlink():
                return super().restore()
            # Preserve existing in-app shortcuts until the user saves settings.
            # Removing login registration must not silently re-enable it.
            self.local.restore()

    def close(self):
        with self.lock:self.local.close()


def select_manager(parent=None):
    if (ROOT/'release.json').is_file():return ManagedShortcutManager(parent)
    from .macos_shortcut_service import request
    try:
        status=request({'operation':'status'})
    except OSError as error:
        if error.errno not in (errno.ENOENT,errno.ECONNREFUSED):raise
        registration=Path.home()/'Library/LaunchAgents/com.augmentor.Agent.shortcut.plist'
        if registration.exists() or registration.is_symlink():
            raise RuntimeError('The login shortcut service is not ready. Start it before saving a shortcut.')
        return ShortcutManager(parent)
    if status.get('protocol')!=1:raise RuntimeError('Unsupported shortcut service version.')
    return RemoteShortcutManager(parent)


def initialize(window):
    global manager
    try:manager=select_manager(window)
    except Exception as error:
        window.set_status('Could not connect to the shortcut service: '+str(error))
        return
    manager.pressed.connect(window.toggle_visibility)
    manager.problem.connect(window.set_status)
    from PySide6.QtWidgets import QApplication
    QApplication.instance().aboutToQuit.connect(manager.close)
    def restore():
        try:manager.restore()
        except Exception as error:manager.problem.emit(str(error))
    threading.Thread(target=restore,daemon=True).start()

def save_shortcut(sequence):
    if manager is None:raise RuntimeError('Open the desktop app before saving its shortcut.')
    return manager.save(sequence)
