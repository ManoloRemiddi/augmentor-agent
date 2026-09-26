#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real Mac hotkey registration and native two-window activation, isolated state.

Activation invokes the service's hotkey callback; physical key injection requires
separate permission and is not claimed. Only opt-in fixture windows are controlled.
"""
import argparse
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import time


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app-root',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();root=args.app_root.resolve();args.out.mkdir(parents=True,exist_ok=True)
    if sys.platform!='darwin':raise SystemExit('Run on macOS.')
    with tempfile.TemporaryDirectory(prefix='ash-',dir='/tmp') as directory:
        state=Path(directory)
        for name in ('XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_STATE_HOME','XDG_RUNTIME_DIR','AUGMENTOR_PI_CONFIG','AUGMENTOR_PI_STATE','AUGMENTOR_SHARED_DATA','AUGMENTOR_SHARED_STATE'):
            path=state/name;path.mkdir(mode=0o700);os.environ[name]=str(path)
        os.environ['AUGMENTOR_MACOS_HOTKEY']=str(root/'native/augmentor-hotkey')
        sys.path.insert(0,str(root/'apps/native'))
        from PySide6.QtCore import QCoreApplication
        from PySide6.QtGui import QKeySequence
        from augmentor_linux.macos_shortcuts import configuration,RemoteShortcutManager
        from augmentor_linux.macos_shortcut_service import ShortcutService,request
        from augmentor_linux.shortcut_activation import DesktopActivation
        from augmentor_linux.instances import ipc_basename
        app=QCoreApplication([])
        configuration().parent.mkdir(parents=True)
        primary_sequence='Ctrl+Alt+Shift+F18';secondary_sequence='Ctrl+Alt+Shift+F19'
        configuration().write_text(json.dumps({'sequence':primary_sequence}))
        native=root.parents[1]/'MacOS/Augmentor Agent Desktop'
        command=[str(native),'--preview','--ui-test-control']
        def exchange(name,message):
            with socket.socket(socket.AF_UNIX) as peer:
                peer.settimeout(4);peer.connect(str(Path(os.environ['XDG_RUNTIME_DIR'])/(ipc_basename(name)+'.sock')))
                peer.sendall(message.encode());return json.loads(peer.makefile('rb').readline())
        def ui(name,action,**values):
            result=exchange(name,'ui-test:'+json.dumps({'action':action,**values}))
            assert result.get('ok'),result
            return result['result']
        def until(name,predicate,timeout=15):
            end=time.monotonic()+timeout
            while time.monotonic()<end:
                app.processEvents()
                try:
                    value=ui(name,'inspect')
                    if predicate(value):return value
                except (FileNotFoundError,ConnectionRefusedError):pass
                time.sleep(.04)
            raise AssertionError('Window state timed out: '+name)
        def create():
            service=ShortcutService()
            service.activations={name:DesktopActivation(command=command,instance=name) for name in ('main','secondary')}
            service.start();return service
        service=create();children=[]
        try:
            assert request({'operation':'status'})['active']
            assert not request({'operation':'status','instance':'secondary'})['active']
            primary=configuration().read_bytes()
            RemoteShortcutManager(instance='secondary').save(QKeySequence(secondary_sequence))
            assert configuration().read_bytes()==primary
            assert request({'operation':'status','instance':'secondary'})['active']
            saved=configuration('secondary').read_bytes()
            try:RemoteShortcutManager(instance='secondary').save(QKeySequence(primary_sequence))
            except RuntimeError as error:assert 'already assigned' in str(error)
            else:raise AssertionError('Conflicting shortcut was accepted')
            assert configuration('secondary').read_bytes()==saved
            states={}
            for name in ('main','secondary'):
                service.activate(name);children.append(service.activations[name].child)
                states[name]=until(name,lambda value:value['visible'])
                ui(name,'draft',expected='',text='Unsent '+name+' fixture')
            assert states['main']['pid']!=states['secondary']['pid']
            for name,other in (('secondary','main'),('main','secondary')):
                service.activate(name);until(name,lambda value:not value['visible'])
                preserved=ui(other,'inspect')
                assert preserved['visible'] and preserved['pid']==states[other]['pid']
                assert preserved['draft']=='Unsent '+other+' fixture'
                service.activate(name);restored=until(name,lambda value:value['visible'])
                assert restored['pid']==states[name]['pid'] and restored['draft']=='Unsent '+name+' fixture'
                refusal=exchange(name,'maintenance.close')
                assert refusal['draftPresent'] and not refusal['accepted']
            for name in states:
                ui(name,'capture',path=str(args.out.resolve()/(name+'.png')))
                ui(name,'draft',expected='Unsent '+name+' fixture',text='')
                assert exchange(name,'maintenance.close')['accepted']
                service.activations[name].child.wait(timeout=15)
            service.close();service=create()
            for name in states:
                assert request({'operation':'status','instance':name})['active']
                service.activate(name);children.append(service.activations[name].child)
                reopened=until(name,lambda value:value['visible'])
                assert reopened['pid']!=states[name]['pid']
                assert exchange(name,'maintenance.close')['accepted']
                service.activations[name].child.wait(timeout=15)
            report={'passed':True,'nativeCarbonRegistration':True,'bothBindingsRestoredAfterServiceRestart':True,
                    'targetedNativeHideShow':True,'coldLaunchAndReopen':True,'otherWindowDraftPreserved':True,
                    'maintenanceRefusedUnsentDraft':True,'conflictPreservedBothBindings':True,
                    'physicalKeyboardTested':False,'provider':'isolated preview fixtures','appRoot':str(root)}
            (args.out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
        finally:
            service.close()
            for child in children:
                if child and child.poll() is None:child.terminate();child.wait(timeout=10)


if __name__=='__main__':main()
