# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Manage only Augmentor's KDE launcher shortcut and matching desktop entries."""
from .instances import desktop_component, current_name, validate_name
import os
import sys
import re
import subprocess
import tempfile
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence

PACKAGED=(Path(__file__).resolve().parents[3]/'release.json').is_file()
COMPONENT=desktop_component('com.augmentor.Agent.desktop' if PACKAGED else 'com.augmentor.LinuxPi.desktop')
ACTION=f"['{COMPONENT}','_launch','Augmentor Agent','Show or hide Augmentor Agent']"
SYSTEM_DESKTOP=Path('/usr/share/applications')/COMPONENT
# KDE SetPresent (2) | NoAutoloading (4): saving keys alone leaves the
# launcher inactive, even though shortcut() and invokeShortcut() succeed.
SHORTCUT_FLAGS='6'


def call(method,*args):
    result=subprocess.run(['gdbus','call','--session','--dest','org.kde.kglobalaccel','--object-path','/kglobalaccel','--method','org.kde.KGlobalAccel.'+method,*args],capture_output=True,text=True,timeout=5)
    if result.returncode:raise RuntimeError('KDE shortcut service is unavailable.')
    return result.stdout.strip()


def target(instance=None):
    if instance is None:return COMPONENT,ACTION
    instance=validate_name(instance)
    base=COMPONENT.removesuffix('.desktop')
    if current_name()!='main':base=base.removesuffix('.'+current_name())
    component=base+('' if instance=='main' else '.'+instance)+'.desktop'
    return component,str([component,'_launch','Augmentor Agent','Show or hide Augmentor Agent'])


def current_keys(instance=None):
    if sys.platform=='darwin':
        from .macos_shortcuts import current_keys as read
        if instance not in (None,'main'):raise RuntimeError('Second-window shortcuts are currently supported on KDE.')
        return read()
    return [int(value) for value in re.findall(r'-?\d+',call('shortcut',target(instance)[1])) if int(value)>0]


def display_key(key):
    # Verified by a focused key test on this machine's MX Keys Mini.
    return 'Fn+Space' if key=='Fn+Space' or key==int(Qt.Key.Key_Hangul) else QKeySequence(key).toString(QKeySequence.SequenceFormat.NativeText)


def shortcut_key(sequence):
    if sequence.isEmpty() or sequence.count()!=1:raise ValueError('Choose one key combination.')
    combination=sequence[0]
    if combination.keyboardModifiers()==Qt.KeyboardModifier.NoModifier and int(combination.key())<0x1000000:
        raise ValueError('Use Ctrl, Alt or Super with a letter or Space.')
    return combination.toCombined()


def write_atomic(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w',dir=path.parent,delete=False) as file:
        file.write(text);temporary=file.name
    mode=path.stat().st_mode & 0o777 if path.exists() else 0o644
    # KDE requires user-owned launcher files to be executable before trusting
    # their Exec entry when restoring shortcuts in a later desktop session.
    if PACKAGED:mode|=0o100
    os.chmod(temporary,mode)
    os.replace(temporary,path)


def save_shortcut(sequence,instance=None):
    if sys.platform=='darwin':
        from .macos_shortcuts import save_shortcut as save
        if instance not in (None,'main'):raise RuntimeError('Second-window shortcuts are currently supported on KDE.')
        return save(sequence)
    component,action=target(instance)
    key=shortcut_key(sequence);previous=current_keys(instance)
    if key not in previous and 'true' not in call('isGlobalShortcutAvailable',str(key),component):
        raise ValueError('That shortcut is already assigned. Choose another combination.')
    data=Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local/share'))
    paths=[data/'applications'/component,data/'kglobalaccel'/component]
    backups={path:path.read_text() if path.exists() else None for path in paths}
    modes={path:path.stat().st_mode & 0o777 for path in paths if path.exists()}
    system=SYSTEM_DESKTOP if component==COMPONENT else SYSTEM_DESKTOP.with_name(component)
    template=next((text for text in backups.values() if text is not None),None)
    if template is None and PACKAGED and system.exists():template=system.read_text()
    if template is None and instance is not None:
        primary,_=target('main')
        for candidate in (data/'applications'/primary,Path('/usr/share/applications')/primary):
            if candidate.exists():
                template=candidate.read_text()
                if instance!='main':
                    template=re.sub(r'(?m)^(Exec=.*)$',lambda match:re.sub(r' --instance [a-z0-9-]+','',match[1])+' --instance '+instance,template)
                break
    portable=sequence.toString(QKeySequence.SequenceFormat.PortableText)
    try:
        # KGlobalAccel needs a launcher it can activate, including after login.
        # Prepare the owned user entries before registering the live shortcut.
        for path,original in backups.items():
            text=original if original is not None else template
            if text is None:continue
            lines=[line for line in text.splitlines() if not line.startswith('X-KDE-Shortcuts=')]
            write_atomic(path,'\n'.join(lines)+'\nX-KDE-Shortcuts='+portable+'\n')
        call('doRegister',action)
        result=call('setShortcut',action,f'[{key}]',SHORTCUT_FLAGS)
        assigned=[int(value) for value in re.findall(r'-?\d+',result)]
        if assigned!=[key]:raise RuntimeError('KDE could not assign that shortcut. The previous shortcut was kept.')
    except (OSError,RuntimeError):
        try:call('setShortcut',action,str(previous),SHORTCUT_FLAGS)
        finally:
            for path,text in backups.items():
                if text is None:path.unlink(missing_ok=True)
                else:
                    write_atomic(path,text);os.chmod(path,modes[path])
        raise
    return key
