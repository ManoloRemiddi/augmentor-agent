#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real Linux capture/overlay/paste proof using an isolated X server and virtual mic.

Run: QT_QPA_PLATFORM=xcb dbus-run-session -- xvfb-run -a bash -c
  'kwin_x11 --replace & wm=$!; trap "kill $wm" EXIT; python3 scripts/proof-handy.py'
Requires the selected Parakeet model already cached, espeak-ng, ffmpeg,
PulseAudio/PipeWire, xdotool, and the staged component. Captures no physical mic.
"""
import json
import os
from pathlib import Path
import select
import sys
import subprocess
import tempfile
import time
from PySide6.QtWidgets import QApplication,QTextEdit

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/handy-proof'

def command(args):return subprocess.check_output(args,text=True).strip()

def main():
    broker_mode='--broker' in sys.argv
    sys.path.insert(0,str(ROOT/'apps/native'))
    from augmentor_linux import dictation
    OUT.mkdir(parents=True,exist_ok=True)
    app=QApplication([]);target=QTextEdit();target.setWindowTitle('External application · Dictation proof');target.resize(620,180);target.show();target.setFocus()
    time.sleep(.2);app.processEvents()
    target_id=int(target.winId());command(['xdotool','windowfocus',str(target_id)])
    sink='augmentor_dictation_proof_'+str(os.getpid())
    module=command(['pactl','load-module','module-null-sink','sink_name='+sink])
    child=None
    with tempfile.TemporaryDirectory(prefix='augmentor-handy-proof-') as temporary:
        workspace=Path(temporary)
        (workspace/'alsa.conf').write_text('pcm.!default { type pulse device "'+sink+'.monitor" }\nctl.!default { type pulse }\n')
        env={**os.environ,'AUGMENTOR_HANDY_EMBEDDED':'1','HANDY_DISABLE_UPDATER':'1','XDG_DATA_HOME':str(workspace/'data'),'XDG_CONFIG_HOME':str(workspace/'config'),
             'ALSA_CONFIG_PATH':str(workspace/'alsa.conf'),'WEBKIT_DISABLE_COMPOSITING_MODE':'1','GDK_BACKEND':'x11','XDG_SESSION_TYPE':'x11','PULSE_SOURCE':sink+'.monitor','WEBKIT_DISABLE_DMABUF_RENDERER':'1'}
        env.pop('WAYLAND_DISPLAY',None);env['LANG']='C.UTF-8';env['LC_ALL']='C.UTF-8'
        env['AUGMENTOR_DICTATION_STATE']=str(workspace/'broker')
        sequence=0
        def pause(seconds):
            end=time.monotonic()+seconds
            while time.monotonic()<end:app.processEvents();time.sleep(.01)
        def call(method,params=None):
            nonlocal sequence
            if broker_mode:return dictation.request(method,params or {},start=False,timeout=35)
            sequence+=1;ident=sequence
            child.stdin.write((json.dumps({'id':ident,'method':method,'params':params or {}})+'\n').encode());child.stdin.flush()
            deadline=time.monotonic()+30
            while time.monotonic()<deadline:
                app.processEvents()
                if select.select([child.stdout],[],[],.02)[0]:
                    reply=json.loads(child.stdout.readline())
                    if reply.get('id')!=ident:continue
                    if 'error' in reply:raise RuntimeError(reply['error'])
                    return reply['result']
                if child.poll() is not None:raise RuntimeError('Component exited: '+str(child.returncode))
            raise TimeoutError(method+' did not respond')
        def capture_overlay(window,name):
            # Inspect successive native frames: a partial repaint regression
            # leaves only the orb/waveform and loses the static pill/cancel.
            for _ in range(3):
                pause(.12)
                capture=app.primaryScreen().grabWindow(window)
                image=capture.toImage()
                painted=[(x,y) for y in range(image.height()) for x in range(image.width())
                         if image.pixelColor(x,y).alpha()>0 and max(image.pixelColor(x,y).getRgb()[:3])>20]
                assert painted,'Recording overlay is blank'
                width=max(x for x,y in painted)-min(x for x,y in painted)+1
                height=max(y for x,y in painted)-min(y for x,y in painted)+1
                capture.save(str(OUT/name))
                assert width>=160 and height>=36,repr({'lostStaticOverlay':True,'width':width,'height':height})
        def ready(phase):
            for _ in range(150):
                state=call('status')
                if state['phase']==phase:return state
                pause(.05)
            raise RuntimeError('Expected '+phase+', got '+str(state))
        try:
            with open(OUT/'component.log','w') as log:
                if broker_mode:
                    os.environ.clear();os.environ.update(env)
                    child=subprocess.Popen([sys.executable,'-B',str(ROOT/'services/dictation/server.py')],stderr=log,env=env)
                    for _ in range(100):
                        try:call('status');break
                        except RuntimeError:pause(.05)
                else:child=subprocess.Popen([str(ROOT/'components/handy/runtime/bin/handy')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,env=env)
                state=call('status');assert state['enabled'] is False and state['tray'] is False
                call('enable',{'enabled':True});ready('ready')
                subprocess.run(['espeak-ng','-w',str(workspace/'speech.wav'),'Voice dictation works inside this separate application.'],check=True)
                subprocess.run(['ffmpeg','-loglevel','error','-y','-i',str(workspace/'speech.wav'),'-ar','16000','-ac','1',str(workspace/'input.wav')],check=True)
                command(['xdotool','windowfocus',str(target_id)]);pause(2)
                command(['xdotool','keydown','ctrl+space']);ready('recording');pause(.7)
                sources=json.loads(command(['pactl','--format=json','list','sources']))
                index=next(source['index'] for source in sources if source['name']==sink+'.monitor')
                captures=json.loads(command(['pactl','--format=json','list','source-outputs']))
                native_pid=command(['cat','/proc/'+str(child.pid)+'/task/'+str(child.pid)+'/children']).split()[0] if broker_mode else str(child.pid)
                ours=[source for source in captures if source.get('properties',{}).get('application.process.id')==native_pid]
                assert ours and all(str(source['source'])==str(index) for source in ours),repr({'expected':index,'captures':[{'source':v.get('source'),'pid':v.get('properties',{}).get('application.process.id')} for v in captures]})
                audio=subprocess.Popen(['paplay','--device='+sink,str(workspace/'input.wav')])
                pause(.5)
                overlay=int(command(['xdotool','search','--onlyvisible','--name','^Recording$']).splitlines()[-1])
                capture_overlay(overlay,'recording-dark.png')
                light={'background':'#e8edf2','foreground':'#152b2c','accent':'#ac5335','border':'#ac5335','opacity':.9,'animated':True,'mode':'light'}
                call('theme',light);assert call('status')['theme']==light
                pause(.4);capture_overlay(overlay,'recording-light.png')
                call('theme',{**light,'animated':False});pause(.4);capture_overlay(overlay,'recording-animation-off.png')
                call('theme',light)
                assert int(command(['xdotool','getwindowfocus']))==target_id,'Overlay stole input focus'
                while audio.poll() is None:pause(.05)
                pause(.3);command(['xdotool','keyup','space','shift','ctrl']);ready('ready');pause(.8)
                text=target.toPlainText();assert 'voice dictation works' in text.lower(),repr(text)
                assert int(command(['xdotool','getwindowfocus']))==target_id,'Paste went to another window'
                original=text
                state=call('status');call('settings',{'revision':state['revision'],'values':{'shortcut':'ctrl+shift+space'}})
                command(['xdotool','keydown','ctrl+shift+space']);ready('recording');pause(.5)
                geometry=command(['xdotool','getwindowgeometry','--shell',str(overlay)])
                bounds=dict(line.split('=',1) for line in geometry.splitlines() if '=' in line)
                command(['xdotool','mousemove','--window',str(overlay),str(int(bounds['WIDTH'])//2+66),str(int(bounds['HEIGHT'])-20),'click','1'])
                ready('ready');command(['xdotool','keyup','space','shift','ctrl']);pause(.3)
                assert target.toPlainText()==original,'Cancelled recording inserted text'
                token='a'*32
                call('conversation.acquire',{'token':token,'pid':os.getpid()});command(['xdotool','keydown','ctrl+shift+space']);pause(.2)
                assert call('status')['phase']!='recording','Two microphone owners admitted'
                command(['xdotool','keyup','space','shift','ctrl']);call('conversation.release',{'token':token})
                call('enable',{'enabled':False});state=call('status');assert state['enabled'] is False and state['phase']=='disabled'
                if broker_mode:call('shutdown')
                else:child.stdin.close()
                child.wait(timeout=5);assert child.returncode==0
                result={'schema':'augmentor-handy-proof/1','transcript':text,'virtualMicrophone':True,'physicalMicrophoneUsed':False,
                        'defaultCtrlSpace':True,'shortcutCustomisation':True,'liveThemeChanged':True,'staticOverlayPreservedAcrossFrames':True,'animationOffOverlayPreserved':True,'focusPreserved':True,'closeButtonCancelled':True,'cancelPreservedText':True,'microphoneOwnership':True,'disabled':True,'parentExit':True,'tray':False,'authenticatedBroker':broker_mode}
                (OUT/('broker-result.json' if broker_mode else 'result.json')).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
        finally:
            if child and child.poll() is None:
                child.terminate()
                try:child.wait(timeout=5)
                except subprocess.TimeoutExpired:child.kill();child.wait()
            import shutil
            logs=workspace/'data/com.augmentor.agent.dictation/logs'
            if logs.exists():shutil.copytree(logs,OUT/'debug-logs',dirs_exist_ok=True)
            subprocess.run(['pactl','unload-module',module],check=True)
            target.close()

if __name__=='__main__':main()
