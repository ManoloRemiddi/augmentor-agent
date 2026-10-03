# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""One private broker per desktop session; Handy has no independent tray/lifecycle."""
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
from multiprocessing.connection import Listener

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'apps/native'));sys.path.insert(0,str(ROOT))
from augmentor_linux.dictation import location
from services.dictation import portal


def process_alive(pid):
    if os.name=='nt':
        import ctypes
        from ctypes import wintypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenProcess.restype=wintypes.HANDLE
        kernel.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)]
        kernel.CloseHandle.argtypes=[wintypes.HANDLE]
        handle=kernel.OpenProcess(0x1000,False,pid)
        if not handle:return False
        try:
            code=wintypes.DWORD()
            return bool(kernel.GetExitCodeProcess(handle,ctypes.byref(code))) and code.value==259
        finally:kernel.CloseHandle(handle)
    try:
        os.kill(pid,0)
        proc=Path('/proc')/str(pid)/'stat'
        return not proc.exists() or proc.read_text().rsplit(')',1)[1].split()[0]!='Z'
    except (ProcessLookupError,FileNotFoundError):return False


class Backend:
    def __init__(self, base, session="default"):
        self.base=base; self.lock=threading.RLock(); self.child=None; self.pending={}; self.sequence=0; self.generation=0; self.owner=None;self.input_daemon=None;self.portal=None
        self.key_events=queue.Queue()
        threading.Thread(target=self.key_worker,daemon=True).start()
        self.inputdir=base/session;self.inputdir.mkdir(exist_ok=True,mode=0o700)
        self.statefile=base/'preferences.json'
        self.preferences=json.loads(self.statefile.read_text()) if self.statefile.exists() else {'enabled':False}

    def save(self):
        temporary=self.statefile.with_suffix('.tmp')
        with open(temporary,'w',encoding='utf-8') as output: json.dump(self.preferences,output)
        os.chmod(temporary,0o600); os.replace(temporary,self.statefile)

    def binary(self):
        candidate=ROOT/'components/handy/runtime/bin'/('handy.exe' if os.name=='nt' else 'handy')
        if sys.platform=='darwin':
            bundled=ROOT/'components/handy/runtime/Augmentor Dictation.app/Contents/MacOS/handy'
            if bundled.is_file():candidate=bundled
        if not candidate.is_file(): raise RuntimeError('The bundled Handy component is unavailable. Install a complete Augmentor package.')
        return candidate

    def start(self):
        if self.child and self.child.poll() is None:return
        env=os.environ.copy();env.update(AUGMENTOR_HANDY_EMBEDDED='1',HANDY_DISABLE_UPDATER='1')
        if sys.platform=='win32':
            from services.dictation.windows_runtime import environment
            env=environment(ROOT/'components/handy/runtime',env)
        if sys.platform.startswith('linux') and portal.required():
            env['AUGMENTOR_HANDY_EXTERNAL_SHORTCUT']='1'
            # GNOME has no layer-shell protocol for a bottom-edge overlay.
            # XWayland supplies window placement; the portal still owns keys
            # and our private input helper pastes into native Wayland apps.
            env['GDK_BACKEND']='x11'
        env['PATH']=str(self.binary().parent)+os.pathsep+env.get('PATH','')
        env['YDOTOOL_SOCKET']=str(self.inputdir/'input.sock')
        sys.path.insert(0,str(ROOT/'services/lifecycle'))
        from lease import hold
        hold('runtime')
        self.generation=time.monotonic_ns()
        self.child=subprocess.Popen([str(self.binary())],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env=env,**({'umask':0o077} if os.name!='nt' else {'creationflags':0x08000000}))
        threading.Thread(target=self.read,args=(self.child,),daemon=True).start()
        try:self.call('status',{})
        except Exception:
            self.stop();raise
        if 'theme' in self.preferences:self.call('theme',self.preferences['theme'])
        if self.owner:self.call('conversation.acquire',{'token':self.owner['token']})
        if self.preferences.get('enabled'):
            try:self.activate()
            except Exception:self.stop();self.preferences['enabled']=False;self.save();raise

    def key_worker(self):
        while True:
            owner,session,pressed=self.key_events.get()
            with self.lock:
                if owner is not self.portal or owner.session!=session or not self.child or self.child.poll() is not None:continue
                try:self.call('shortcut.event',{'pressed':pressed})
                except (OSError,RuntimeError,TimeoutError):pass

    def activate(self):
        self.start_input()
        if sys.platform.startswith('linux') and portal.required() and not self.portal:
            instance=portal.Portal(lambda session,pressed:self.key_events.put((instance,session,pressed)))
            try:instance.bind(self.call('status',{})['settings']['shortcut'])
            except Exception:instance.close();raise
            self.portal=instance
        self.call('enable',{'enabled':True})

    def start_input(self):
        if not sys.platform.startswith('linux') or os.environ.get('XDG_SESSION_TYPE')!='wayland':return
        if self.input_daemon and self.input_daemon.poll() is None:return
        if not os.access('/dev/uinput',os.W_OK):raise RuntimeError('Allow Augmentor keyboard input in system setup, then sign out and back in. Dictation has not started.')
        socket=self.inputdir/'input.sock';socket.unlink(missing_ok=True)
        daemon=self.binary().with_name('ydotoold')
        self.input_daemon=subprocess.Popen([str(daemon),'--socket-path='+str(socket),'--socket-perm=0600'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for _ in range(40):
            if socket.exists():return
            if self.input_daemon.poll() is not None:break
            time.sleep(.05)
        self.stop_input();raise RuntimeError('Augmentor keyboard input helper could not start.')

    def stop_input(self):
        process,self.input_daemon=self.input_daemon,None
        if process and process.poll() is None:
            process.terminate()
            try:process.wait(timeout=2)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        (self.inputdir/'input.sock').unlink(missing_ok=True)

    def read(self, child):
        try:
            while True:
                line=child.stdout.readline(1048577)
                if not line:break
                if len(line)>1048576:child.terminate();break
                try: reply=json.loads(line)
                except (ValueError,UnicodeError):continue
                entry=self.pending.get(reply.get('id'))
                if entry and entry[0] is child:entry[1].put(reply)
        finally:
            for owner,waiter in list(self.pending.values()):
                if owner is child:waiter.put({'error':'Handy stopped. Refresh system dictation settings.'})

    def call(self, method, params):
        self.sequence+=1;ident=self.sequence;waiter=queue.Queue();self.pending[ident]=(self.child,waiter)
        try:
            self.child.stdin.write((json.dumps({'id':ident,'method':method,'params':params})+'\n').encode());self.child.stdin.flush()
            reply=waiter.get(timeout=60 if method=='model.select' else 15)
            if 'error' in reply:raise RuntimeError(reply['error'])
            return reply['result']
        except queue.Empty: raise TimeoutError('Handy did not respond. Refresh system dictation settings.')
        finally:self.pending.pop(ident,None)

    def stop(self):
        instance,self.portal=self.portal,None
        if instance:instance.close()
        self.stop_input()
        child,self.child=self.child,None
        if child:
            child.stdin.close()
            try:child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.terminate()
                try:child.wait(timeout=2)
                except subprocess.TimeoutExpired:child.kill();child.wait()
        module=sys.modules.get('lease')
        if module:
            for descriptor in module._leases:os.close(descriptor)
            module._leases.clear()

    def request(self, method, params):
        with self.lock:
            if self.owner:
                if not process_alive(self.owner['pid']):
                    if self.child and self.child.poll() is None:self.call('conversation.release',{'token':self.owner['token']})
                    self.owner=None
            if method=='initialize':
                if 'theme' not in self.preferences:self.request('theme',params['theme'])
                return self.request('status',{})
            if method=='theme':
                params=params.copy();edited_at=params.pop('edited_at',time.time_ns())
                if type(edited_at) is not int or edited_at<=0:raise ValueError('Invalid appearance timestamp.')
                # Strict validation also applies when the component is disabled.
                import re
                if set(params)!={'background','foreground','accent','border','opacity','animated','mode'} or any(not re.fullmatch('#[0-9a-fA-F]{6}',str(params[k])) for k in ('background','foreground','accent','border')) or type(params['opacity']) not in (int,float) or not .35<=params['opacity']<=1 or type(params['animated']) is not bool or params['mode'] not in ('light','dark'):raise ValueError('Invalid overlay theme.')
                if edited_at<self.preferences.get('theme_updated_at',0):return {}
                if self.child and self.child.poll() is None:self.call(method,params)
                self.preferences['theme']=params;self.preferences['theme_updated_at']=edited_at;self.save();return {}
            if method=='enable':
                if type(params.get('enabled')) is not bool:raise ValueError('Invalid enabled value.')
                if params['enabled']:
                    self.start()
                    try:self.activate()
                    except Exception:
                        self.stop();self.preferences['enabled']=False;self.save();raise
                else:
                    if self.child and self.child.poll() is None:self.call('enable',params)
                    self.stop()
                self.preferences['enabled']=params['enabled'];self.save();return {}
            if method=='conversation.acquire':
                expires=params.get('expires_at')
                if expires is not None and (type(expires) is not int or expires<=time.time_ns()):raise RuntimeError('Voice input request expired; start voice again.')
                if self.owner and self.owner['token']!=params.get('token'):raise RuntimeError('Microphone is busy in another Augmentor conversation.')
                if not isinstance(params.get('token'),str) or len(params['token'])!=32 or type(params.get('pid')) is not int or params['pid']<=0:raise ValueError('Invalid microphone owner.')
                if self.child and self.child.poll() is None:self.call(method,{'token':params['token'],**({'expires_at':expires} if expires is not None else {})})
                if expires is not None and expires<=time.time_ns():
                    if self.child and self.child.poll() is None:self.call('conversation.release',{'token':params['token']})
                    raise RuntimeError('Voice input request expired; start voice again.')
                self.owner=params.copy();return {}
            if method=='conversation.release':
                if self.owner and self.owner['token']==params.get('token'):
                    if self.child and self.child.poll() is None:self.call(method,params)
                    self.owner=None
                return {}
            if method=='shutdown':
                if self.owner:raise RuntimeError('Close Augmentor voice before maintenance. Nothing was cancelled.')
                if self.child and self.child.poll() is None and self.call('status',{}).get('phase') in ('recording','transcribing'):raise RuntimeError('Finish or cancel dictation before maintenance.')
                self.stop();self.shutting_down=True;return {}
            if method=='status' and not self.preferences.get('enabled') and not self.child:
                return {'enabled':False,'phase':'disabled','tray':False,'installed':(ROOT/'components/handy/runtime/bin'/('handy.exe' if os.name=='nt' else 'handy')).is_file(),'theme':self.preferences.get('theme')}
            if method not in {'status','models','settings','devices','cancel','model.select','model.download','model.cancel'}:raise ValueError('Unsupported dictation operation.')
            if method=='model.download' and params.get('terms_reviewed') is not True:raise ValueError('Review the model publisher terms before downloading.')
            self.start()
            portal_changed=False
            if method=='settings':
                revision=params.get('revision')
                if not isinstance(revision,str) or not revision.startswith(str(self.generation)+'/'):raise RuntimeError('Dictation settings changed; refresh before saving.')
                params={**params,'revision':int(revision.split('/')[1])}
                if self.portal and 'shortcut' in params.get('values',{}):
                    current=self.call('status',{})
                    if current['revision']!=params['revision']:raise RuntimeError('Dictation settings changed; refresh before saving.')
                    if current['phase'] not in ('ready','setup-needed') or self.owner:raise RuntimeError('Finish voice input before changing the shortcut.')
                    old=current['settings']['shortcut']
                    try:self.portal.bind(params['values']['shortcut'])
                    except Exception:
                        try:self.portal.bind(old)
                        except Exception:self.stop();self.preferences['enabled']=False;self.save()
                        raise
                    portal_changed=True
            try:result=self.call(method,params)
            except Exception:
                if portal_changed:
                    # A lost reply may mean the native settings were committed.
                    # Release both owners rather than leave two different bindings.
                    self.stop();self.preferences['enabled']=False;self.save()
                raise
            if method=='status':
                result['revision']=str(self.generation)+'/'+str(result['revision'])
                result['shortcut_description']=self.portal.description if self.portal else result['settings']['shortcut']
            if method=='models':
                catalog=ROOT/'components/handy/runtime/notices/ModelCatalog.json'
                entries={m['id']:m for m in json.loads(catalog.read_text())['models']} if catalog.exists() else {}
                for row in result:
                    hf=row.get('source',{}).get('HuggingFace',{}) if isinstance(row.get('source'),dict) else {}
                    repository=hf.get('repo_id');entry=entries.get(repository,{})
                    row['license']=entry.get('license','Publisher terms; review model card')
                    row['model_card']='https://huggingface.co/'+repository+'/blob/'+hf.get('revision','main')+'/README.md' if repository else 'https://handy.computer/docs/models'
                    if entry.get('base_model'):row['base_model_card']='https://huggingface.co/'+entry['base_model']
                    if repository=='handy-computer/parakeet-unified-en-0.6b-gguf':row['license']='CC BY 4.0 conversion; original model: NVIDIA Open Model License'
            return result


def main():
    base,address,key=location()
    lock=open(base/(Path(address).name+'.lock'),'a')
    if os.name=='nt':
        import msvcrt
        try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:return
    else:
        import fcntl
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        Path(address).unlink(missing_ok=True)
    import hashlib
    backend=Backend(base,'session-'+hashlib.sha256(address.encode()).hexdigest()[:12])
    # An incomplete source checkout must not claim an enabled user's endpoint
    # and leave the installed app talking to a broker without its component.
    # Disabled private test brokers can still coordinate conversation capture.
    if backend.preferences.get('enabled'):backend.binary()
    def reap():
        while not getattr(backend,'shutting_down',False):
            time.sleep(1)
            with backend.lock:
                if not backend.owner:continue
                alive=process_alive(backend.owner['pid'])
                if not alive:
                    try:
                        if backend.child and backend.child.poll() is None:backend.call('conversation.release',{'token':backend.owner['token']})
                    except (OSError,RuntimeError,TimeoutError):pass
                    backend.owner=None
    threading.Thread(target=reap,daemon=True).start()
    with Listener(address,family='AF_PIPE' if os.name=='nt' else 'AF_UNIX',authkey=key) as listener:
        if os.name!='nt':os.chmod(address,0o600)
        def serve(connection):
            with connection:
                try:
                    value=json.loads(connection.recv_bytes(65536))
                    reply={'result':backend.request(value['method'],value.get('params',{}))}
                except Exception as error:reply={'error':str(error)}
                try:connection.send_bytes(json.dumps(reply).encode())
                except (OSError,EOFError):pass
                if getattr(backend,'shutting_down',False):os._exit(0)
        try:
            while True:
                from multiprocessing import AuthenticationError
                try:connection=listener.accept()
                except (AuthenticationError,EOFError):continue
                threading.Thread(target=serve,args=(connection,),daemon=True).start()
        finally:backend.stop()

if __name__=='__main__':main()
