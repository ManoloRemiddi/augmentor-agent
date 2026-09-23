# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Process-scoped KWin desktop following through its public scripting API.

Some KWin 6 releases allocate script IDs from the number of loaded scripts.
After unloading a non-last script this can collide with an existing DBus path.
Never run an occupied ID: reserve inert slots until a free path is allocated.
"""
import os
import sys
import re
import tempfile
import uuid
from pathlib import Path
if sys.platform == 'linux':
    from PySide6.QtDBus import QDBusConnection, QDBusInterface, QDBusMessage

_current=None

def scripting_interface():
    return QDBusInterface('org.kde.KWin','/Scripting','org.kde.kwin.Scripting',QDBusConnection.sessionBus())

def release_scripts(lease):
    if not lease:return
    scripting=scripting_interface()
    for name,file in reversed(lease):
        if scripting.isValid():scripting.call('unloadScript',name)
        Path(file).unlink(missing_ok=True)

def run_script(source,prefix='augmentor-linux-pi'):
    if sys.platform != 'linux':return None
    bus=QDBusConnection.sessionBus();scripting=scripting_interface()
    if not scripting.isValid():return None
    lease=[]
    for _ in range(32):
        inspector=QDBusInterface('org.kde.KWin','/Scripting','org.freedesktop.DBus.Introspectable',bus)
        xml=inspector.call('Introspect').arguments()[0]
        occupied={int(i) for i in re.findall(r'<node name="Script(\d+)"',xml)}
        name=f'{prefix}-{os.getpid()}-{uuid.uuid4().hex}'
        with tempfile.NamedTemporaryFile(mode='w',suffix='.js',prefix='augmentor-pin-',delete=False) as file:
            file.write(source);path=file.name
        result=scripting.call('loadScript',path,name)
        if result.type()==QDBusMessage.MessageType.ErrorMessage:
            Path(path).unlink(missing_ok=True);release_scripts(lease);return None
        script_id=result.arguments()[0]
        if not isinstance(script_id,int) or script_id<0:
            Path(path).unlink(missing_ok=True);release_scripts(lease);return None
        lease.append((name,path))
        if script_id in occupied:
            Path(path).write_text('// Inert reservation for a KWin script-ID collision.\n')
            continue
        script=QDBusInterface('org.kde.KWin',f'/Scripting/Script{script_id}','org.kde.kwin.Script',bus)
        if script.call('run').type()==QDBusMessage.MessageType.ErrorMessage:
            release_scripts(lease);return None
        return lease
    release_scripts(lease);return None

def pin_kwin(pinned):
    global _current
    if sys.platform != 'linux':return False
    scripting=scripting_interface()
    if not scripting.isValid():return False
    if _current:
        if pinned and scripting.call('isScriptLoaded',_current[-1][0]).arguments()==[True]:return True
        release_scripts(_current);_current=None
    assignment='w.onAllDesktops = true; w.keepAbove = true;' if pinned else 'w.desktops = [workspace.currentDesktop];'
    source=f'''
function apply(w) {{ if (w.pid === {os.getpid()}) {{ {assignment} }} }}
function refresh() {{ for (const w of workspace.windowList()) apply(w); }}
refresh();
'''
    if pinned:source+='workspace.windowAdded.connect(apply); workspace.currentDesktopChanged.connect(refresh);'
    lease=run_script(source)
    if pinned:_current=lease
    else:release_scripts(lease)
    return lease is not None

def release_kwin():
    global _current
    release_scripts(_current);_current=None
