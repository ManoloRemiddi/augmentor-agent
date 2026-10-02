#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Exercise the actual packaged component without a microphone or model download."""
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time

ROOT=Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory(prefix='augmentor-component-proof-') as temporary:
        base=Path(temporary);runtime=base/'runtime'
        shutil.copytree(ROOT/'components/handy/runtime',runtime)
        binary=runtime/'bin'/('handy.exe' if os.name=='nt' else 'handy')
        (binary.parent/'portable').write_text('Handy Portable Mode\n')
        environment={**os.environ,'AUGMENTOR_HANDY_EMBEDDED':'1','HANDY_DISABLE_UPDATER':'1','WEBKIT_DISABLE_DMABUF_RENDERER':'1','WEBKIT_DISABLE_COMPOSITING_MODE':'1','RUST_BACKTRACE':'1'}
        if sys.platform.startswith('linux'):
            environment.update(GDK_BACKEND='x11',LIBGL_ALWAYS_SOFTWARE='1',NO_AT_BRIDGE='1')
            environment.pop('WAYLAND_DISPLAY',None)
        child=subprocess.Popen([str(binary)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=environment)
        replies=queue.Queue();errors=[]
        def read():
            for line in child.stdout:
                try:replies.put(json.loads(line))
                except (ValueError,UnicodeError):pass
        def logs():
            for line in child.stderr:errors.append(line.decode(errors='replace'))
        threading.Thread(target=read,daemon=True).start();threading.Thread(target=logs,daemon=True).start()
        ident=0
        def call(method,params=None):
            nonlocal ident
            ident+=1;child.stdin.write((json.dumps({'id':ident,'method':method,'params':params or {}})+'\n').encode());child.stdin.flush()
            deadline=time.monotonic()+90
            while True:
                try:reply=replies.get(timeout=.5);break
                except queue.Empty:
                    if child.poll() is not None or time.monotonic()>deadline:
                        raise RuntimeError('No component reply; exit='+str(child.poll())+'; startup log: '+''.join(errors[-200:]))
            assert reply['id']==ident,reply
            return reply
        try:
            state=call('status')['result'];assert state['protocol']=='augmentor-handy/1'
            assert state['enabled'] is False and state['tray'] is False
            assert state['settings']['shortcut']=='ctrl+space'
            assert state['settings']['activation']=='push_to_talk'
            revision=state['revision']
            result=call('settings',{'revision':revision,'values':{'shortcut':'ctrl+shift+space'}});assert 'error' not in result,result
            assert 'error' in call('settings',{'revision':revision,'values':{'shortcut':'ctrl+space'}})
            palette={'background':'#e8edf2','foreground':'#152b2c','accent':'#ac5335','border':'#ac5335','opacity':.9,'animated':False,'mode':'light'}
            assert 'error' not in call('theme',palette)
            assert call('status')['result']['theme']==palette
            assert 'error' in call('theme',{**palette,'accent':'arbitrary'})
            assert 'error' not in call('conversation.acquire',{'token':'a'*32})
            assert 'error' in call('conversation.acquire',{'token':'b'*32})
            assert 'error' not in call('conversation.release',{'token':'a'*32})
            assert 'error' not in call('enable',{'enabled':False})
            child.stdin.close();child.wait(timeout=10);assert child.returncode==0,child.returncode
            print(json.dumps({'protocol':True,'tray':False,'modelDownload':False,'microphoneCapture':False,'theme':True,'staleSettingsRejected':True,'ownerExclusion':True,'parentExit':True}))
        finally:
            if child.poll() is None:child.terminate();child.wait(timeout=10)

if __name__=='__main__':main()
