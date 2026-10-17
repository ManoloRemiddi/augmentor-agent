#!/usr/bin/python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Register and reopen a sealed MX review without selecting or replacing Desktop."""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import time
import uuid
from urllib.parse import urlsplit, parse_qs

SCHEMA='augmentor-harness-reviews/1'
PATH_KEYS=('config','state','socket','sharedState','sharedData','workspace','runtimeDir','xdgConfigHome','xdgDataHome','xdgStateHome')
PROFILE_KEYS=set(PATH_KEYS)|{'port','sessionId','llamaCppProviders','linuxTools'}
MAX_FRAME=8*1024*1024

def digest(data):return hashlib.sha256(data).hexdigest()
def canonical(value):
    if not isinstance(value,str) or not value or len(value)>4096 or any(ord(c)<32 for c in value):raise ValueError('Choose canonical absolute review paths.')
    p=Path(value)
    if not p.is_absolute() or str(p)!=value or str(p)!=os.path.normpath(value) or str(p.resolve())!=str(p):raise ValueError('Review paths cannot contain aliases or symbolic links.')
    return p

def directory(path,private=True,create=False):
    path=canonical(str(path))
    if create:path.mkdir(parents=True,mode=0o700,exist_ok=True)
    s=path.lstat()
    if not stat.S_ISDIR(s.st_mode) or s.st_uid!=os.getuid() or private and s.st_mode&0o077:raise ValueError('A review directory must be owned and private.')
    return path

def read_private(path,limit=2*1024*1024):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        s=os.fstat(fd)
        if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.getuid() or s.st_mode&0o077 or s.st_nlink!=1 or s.st_size>limit:raise ValueError('Use a bounded private owned regular record.')
        with os.fdopen(os.dup(fd),'rb') as stream:raw=stream.read(limit+1)
        if len(raw)>limit:raise ValueError('Review record exceeds its bound.')
        return json.loads(raw)
    finally:os.close(fd)

def atomic_bytes(path,data,mode=0o600):
    fd,temp=tempfile.mkstemp(prefix='.'+path.name+'-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:stream.write(data);stream.flush();os.fchmod(stream.fileno(),mode);os.fsync(stream.fileno())
        os.replace(temp,path)
        parent=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(parent)
        finally:os.close(parent)
    finally:
        if os.path.exists(temp):os.unlink(temp)

def sealed_release(path):
    root=directory(canonical(str(path)))
    manifest=read_private(root/'desktop-release.json',16*1024*1024)
    selected=manifest.get('deployment',{})
    if selected.get('root')!=str(root) or not re.fullmatch(r'[a-f0-9]{64}',selected.get('artifactSha256','')) or manifest.get('artifactSha256')!=selected['artifactSha256']:raise ValueError('The review release identity is invalid.')
    actual={}
    for p in sorted(root.rglob('*')):
        relative=p.relative_to(root)
        if '__pycache__' in relative.parts or p.suffix=='.pyc' or str(relative)=='desktop-release.json':continue
        if p.is_symlink():
            if not p.resolve(strict=True).is_relative_to(root):raise ValueError('A sealed release cannot link outside itself.')
            actual[str(relative)]='link:'+os.readlink(p)
        elif p.is_file():actual[str(relative)]=digest(p.read_bytes())
    if actual!=manifest.get('files') or digest(json.dumps(actual,sort_keys=True).encode())!=selected['artifactSha256']:raise ValueError('Review files changed after staging. Stage a new release.')
    if selected.get('node')!=str(root/'node/bin/node') or not os.access(selected['node'],os.X_OK):raise ValueError('Use the sealed bundled Node interpreter.')
    python=Path(selected.get('python',''))
    if not python.is_absolute() or not python.is_file() or not os.access(python,os.X_OK):raise ValueError('The recorded Python interpreter is unavailable.')
    product=json.loads((root/'release/product.json').read_text())
    if selected.get('version')!=product.get('version'):raise ValueError('The recorded product version does not match.')
    selected={key:selected[key] for key in ('root','python','node','version','releaseId','sourceRef','artifactSha256')}
    return selected,actual

def profile_record(value):
    if not isinstance(value,dict) or set(value)-PROFILE_KEYS or not set(PATH_KEYS)<=value.keys():raise ValueError('Use an explicit review profile; URLs, bearers and credentials do not belong in registration.')
    p=dict(value)
    for key in PATH_KEYS:canonical(p[key])
    for key in ('config','state'):directory(p[key])
    directory(p['workspace'],private=False)
    if Path(p['socket']).parent not in (Path(p['state']),Path(p['runtimeDir'])) or len(os.fsencode(p['socket']))>103:raise ValueError('The private review socket is outside its state/runtime directory or too long.')
    for key in ('runtimeDir','sharedState','sharedData','xdgConfigHome','xdgDataHome','xdgStateHome'):
        if Path(p[key]).exists():directory(p[key])
    port=p.setdefault('port',0)
    if type(port) is not int or not 0<=port<=65535:raise ValueError('Choose a loopback review port.')
    if 'sessionId' in p and (not isinstance(p['sessionId'],str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}',p['sessionId'])):raise ValueError('Choose an exact saved conversation identity.')
    route=p.setdefault('llamaCppProviders','')
    if not isinstance(route,str) or len(route)>4096 or any(ord(c)<32 for c in route):raise ValueError('Invalid local provider route selection.')
    if type(p.setdefault('linuxTools',True)) is not bool:raise ValueError('Choose explicit Linux tool availability.')
    return p

@contextmanager
def registry_lock(root):
    directory(root,create=True);fd=os.open(root/'reviews.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    try:
        s=os.fstat(fd)
        if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.getuid() or s.st_mode&0o077 or s.st_nlink!=1:raise ValueError('Invalid private review registration lock.')
        end=time.monotonic()+10
        while True:
            try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);break
            except BlockingIOError:
                if time.monotonic()>=end:raise ValueError('Review registration is busy. No owner was restarted.')
                time.sleep(.05)
        yield
    finally:os.close(fd)

def registry_read(root):
    path=root/'reviews.json'
    try:value=read_private(path)
    except FileNotFoundError:return {'schema':SCHEMA,'revision':0,'entries':{},'ownedFiles':{}}
    if value.get('schema')!=SCHEMA or type(value.get('revision')) is not int or value['revision']<0 or not isinstance(value.get('entries'),dict) or len(value['entries'])>16 or not isinstance(value.get('ownedFiles'),dict):raise ValueError('Unsupported review registry. Preserve its backup.')
    return value


def registry_plan(root,selected,shared_pair,names,expected_revision,opener,launch_data):
    """Pure cold-publication renderer; no owner, registration or file mutation.

    The controller supplies its verified immutable deployment and opener bytes,
    holds this registry lock, and binds every previous shared pair to adoption.
    Configuration/state/socket/workspace, model routes, titles and menus remain.
    """
    root=directory(root);old=registry_read(root)
    if type(expected_revision) is not int or old['revision']!=expected_revision:
        raise ValueError('Review registration changed; preserve it and prepare its current revision.')
    if (not isinstance(names,(list,tuple)) or not names or len(names)>16 or
            any(not isinstance(n,str) or n not in old['entries'] for n in names) or len(set(names))!=len(names)):
        raise ValueError('Choose explicit existing reviews for common-store adoption.')
    if not isinstance(selected,dict) or not isinstance(selected.get('root'),str):
        raise ValueError('Supply the verified immutable review deployment.')
    if not isinstance(shared_pair,dict) or set(shared_pair)!={'state','data'}:
        raise ValueError('Use the canonical shared state/data pair.')
    for path in shared_pair.values():directory(path)
    launch_data=directory(launch_data)
    if not isinstance(opener,bytes) or not opener or len(opener)>2*1024**2:
        raise ValueError('Use bounded opener bytes from the verified artifact.')
    binary=canonical(str(Path.home()/'.local/bin/augmentor-harness-review'));directory(binary.parent,private=False)
    # The existing opener must still be the registered owned file. The ordinary
    # installer is the pre-adoption path; this renderer never steals an alias.
    fd=os.open(binary,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        info=os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_nlink!=1 or
                info.st_mode&0o7022 or info.st_size>2*1024**2):
            raise ValueError('The existing review opener is not a protected owned regular file.')
        raw=os.read(fd,2*1024**2+1)
        after=os.fstat(fd)
        current=binary.lstat()
        stamp=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_mode)
        if len(raw)!=info.st_size or stamp(info)!=stamp(after) or stamp(info)!=stamp(current):
            raise ValueError('The existing review opener changed during planning.')
    finally:os.close(fd)
    if old['ownedFiles'].get(str(binary))!=digest(raw):raise ValueError('The review opener was edited or is unowned; preserve it.')
    new=json.loads(json.dumps(old));new['revision']+=1;previous={}
    for name in names:
        original=old['entries'][name]['profile'];profile_record(original)
        previous[name]={'state':original['sharedState'],'data':original['sharedData']}
        profile=dict(original,sharedState=shared_pair['state'],sharedData=shared_pair['data']);profile_record(profile)
        new['entries'][name].update(deployment=dict(selected),profile=profile,launchData=str(launch_data))
    new['ownedFiles'][str(binary)]=digest(opener)
    return {'files':[(root/'reviews.json',(json.dumps(new,indent=2)+'\n').encode(),0o600),(binary,opener,0o700)],
            'previousPairs':previous,'revisionBefore':old['revision'],'revisionAfter':new['revision'],
            'openerBeforeSha256':digest(raw),'openerBeforeMode':stat.S_IMODE(info.st_mode)}

def live_profile(profile):
    found=[]
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():continue
        try:
            cmd=(proc/'cmdline').read_bytes().split(b'\0')
            if not any(arg.endswith(b'/dist/runtime/src/main.js') for arg in cmd):continue
            env=dict(part.decode().split('=',1) for part in (proc/'environ').read_bytes().split(b'\0') if b'=' in part)
            if env.get('AUGMENTOR_PI_STATE')==profile['state']:found.append(int(proc.name))
        except (OSError,UnicodeError,ValueError):continue
    return found

class Owner:
    def __init__(self,profile):
        path=Path(profile['socket']);info=path.lstat()
        if not stat.S_ISSOCK(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077:raise ValueError('The review IPC endpoint is not a private owned socket.')
        directory(path.parent);self.socket=socket.socket(socket.AF_UNIX);self.socket.settimeout(8)
        try:
            self.socket.connect(str(path));self.peer=struct.unpack('3i',self.socket.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
            if self.peer[1]!=os.getuid():raise ValueError('The review endpoint belongs to another user.')
            self.buffer=b'';self.call('host.hello',{'protocol':'augmentor-pi/1'})
        except BaseException:self.close();raise
    def close(self):self.socket.close()
    def call(self,method,params):
        identity=str(uuid.uuid4());self.socket.sendall((json.dumps({'id':identity,'method':method,'params':params})+'\n').encode())
        while True:
            while b'\n' not in self.buffer:
                part=self.socket.recv(65536)
                if not part:raise ValueError('The review disconnected before confirmation. Nothing was replayed.')
                self.buffer+=part
                if len(self.buffer)>MAX_FRAME:raise ValueError('The review response exceeds its bound.')
            line,self.buffer=self.buffer.split(b'\n',1);frame=json.loads(line)
            if frame.get('id')!=identity:continue
            if frame.get('error'):raise ValueError('The review refused the request. Its work was preserved.')
            return frame['result']
    def verify(self,entry,files):
        status=self.call('host.describe',{});p=entry['profile'];selected=entry['deployment'];pid=status.get('pid')
        if pid!=self.peer[0] or status.get('protocol')!='augmentor-pi/1' or status.get('version')!=selected['version'] or status.get('stateDir')!=p['state'] or status.get('configDir')!=p['config']:raise ValueError('The running review does not match its registered profile.')
        proc=Path('/proc')/str(pid);cmd=(proc/'cmdline').read_bytes().split(b'\0');env=dict(part.decode().split('=',1) for part in (proc/'environ').read_bytes().split(b'\0') if b'=' in part)
        if os.fsencode(str(Path(selected['root'])/'dist/runtime/src/main.js')) not in cmd or digest((proc/'exe').read_bytes())!=files['node/bin/node']:raise ValueError('A different build owns this review. Refresh registration after a guarded update; no owner was replaced.')
        expected={'AUGMENTOR_PI_CONFIG':p['config'],'AUGMENTOR_PI_STATE':p['state'],'AUGMENTOR_SHARED_STATE':p['sharedState'],'AUGMENTOR_SHARED_DATA':p['sharedData']}
        if any(env.get(k)!=v for k,v in expected.items()) or env.get('AUGMENTOR_PI_SOCKET',str(Path(p['state'])/'runtime.sock'))!=p['socket'] or env.get('AUGMENTOR_PI_WORKSPACE',str((proc/'cwd').resolve()))!=p['workspace'] or env.get('AUGMENTOR_PI_LLAMA_CPP_PROVIDERS','')!=p['llamaCppProviders'] or (env.get('AUGMENTOR_PI_LINUX_TOOLS')!='0')!=p['linuxTools']:raise ValueError('The running review environment differs from registration. No settings were changed.')
        return status

def runtime_environment(profile,selected):
    base=('HOME','USER','LOGNAME','SHELL','PATH','LANG','LANGUAGE','TZ','TMPDIR','DISPLAY','WAYLAND_DISPLAY','XAUTHORITY','DBUS_SESSION_BUS_ADDRESS','XDG_SESSION_TYPE','XDG_CURRENT_DESKTOP','DESKTOP_SESSION','SSL_CERT_FILE','SSL_CERT_DIR','HTTP_PROXY','HTTPS_PROXY','NO_PROXY','http_proxy','https_proxy','no_proxy')
    env={k:v for k,v in os.environ.items() if k in base or k.startswith('LC_')}
    env.update({'XDG_CONFIG_HOME':profile['xdgConfigHome'],'XDG_DATA_HOME':profile['xdgDataHome'],'XDG_STATE_HOME':profile['xdgStateHome'],'XDG_RUNTIME_DIR':profile['runtimeDir'],'AUGMENTOR_PI_CONFIG':profile['config'],'AUGMENTOR_PI_STATE':profile['state'],'AUGMENTOR_PI_SOCKET':profile['socket'],'AUGMENTOR_SHARED_STATE':profile['sharedState'],'AUGMENTOR_SHARED_DATA':profile['sharedData'],'AUGMENTOR_PI_WORKSPACE':profile['workspace'],'AUGMENTOR_PI_LLAMA_CPP_PROVIDERS':profile['llamaCppProviders'],'AUGMENTOR_PI_LINUX_TOOLS':'1' if profile['linuxTools'] else '0','AUGMENTOR_PI_NODE':selected['node'],'AUGMENTOR_PYTHON':selected['python'],'AUGMENTOR_HARNESS':'1','AUGMENTOR_HARNESS_PORT':str(profile['port']),'AUGMENTOR_DESKTOP_NO_AUTOSTART':'1','PI_TELEMETRY':'0','PI_SKIP_VERSION_CHECK':'1','PYTHONDONTWRITEBYTECODE':'1'})
    return env

def private_link(value,profile):
    try:
        if not isinstance(value,dict) or not isinstance(value.get('url'),str):raise ValueError()
        url=urlsplit(value['url']);fragment=parse_qs(url.fragment,strict_parsing=True)
        if url.scheme!='http' or url.hostname!='127.0.0.1' or url.username or url.password or url.path!='/' or url.query or not url.port or profile['port'] and url.port!=profile['port'] or set(fragment)-{'token','session'} or len(fragment.get('token',[]))!=1 or not re.fullmatch(r'[a-f0-9]{64}',fragment['token'][0]) or fragment.get('session',[])!=([profile['sessionId']] if profile.get('sessionId') else []):raise ValueError()
        return value['url']
    except (ValueError,TypeError):raise ValueError('The review returned an unexpected private link scope.') from None

@contextmanager
def managed_launch(entry):
    """Guard managed review opening, including legacy registered release roots.

    Running Pi/shared owners keep their existing data leases. This reader covers
    the opener/startup gap and honors the persistent deployment fence after an
    interrupted controller. Standalone non-deployment reviews remain standalone.
    """
    root=canonical(entry['deployment']['root'])
    configured=entry.get('launchData')
    data=canonical(configured) if configured is not None else root.parent.parent if root.parent.name=='releases' else None
    if data is None:
        yield;return
    directory(data)
    lock=data/'shared-launch.lock';fd=os.open(lock,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    try:
        a,b=os.fstat(fd),lock.lstat()
        if not stat.S_ISREG(a.st_mode) or a.st_uid!=os.getuid() or a.st_nlink!=1 or a.st_mode&0o077 or (a.st_dev,a.st_ino)!=(b.st_dev,b.st_ino):
            raise ValueError('The managed review launch gate must be private and owned.')
        try:fcntl.flock(fd,fcntl.LOCK_SH|fcntl.LOCK_NB)
        except BlockingIOError as error:raise ValueError('Managed review maintenance is in progress. No review was opened.') from error
        fence=data/'dsh-preservation.json'
        if fence.exists() or fence.is_symlink():raise ValueError('Unfinished DSH configuration maintenance requires recovery before opening this review.')
        yield
    finally:os.close(fd)


def open_review(entry,print_url=False):
    with managed_launch(entry):return _open_review(entry,print_url)


def _open_review(entry,print_url=False):
    profile=profile_record(entry['profile']);selected,files=sealed_release(entry['deployment']['root'])
    if selected!=entry['deployment']:raise ValueError('Review selection changed. Register its verified release again.')
    try:owner=Owner(profile)
    except (FileNotFoundError,ConnectionRefusedError):
        if live_profile(profile):raise ValueError('This review still has a live process but its IPC is unavailable. No replacement was started.')
        for key in ('runtimeDir','sharedState','sharedData','xdgConfigHome','xdgDataHome','xdgStateHome'):directory(profile[key],create=True)
        try:subprocess.run([selected['python'],'-B',str(Path(selected['root'])/'scripts/ensure-runtime.py'),'--harness','pi'],env=runtime_environment(profile,selected),check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=75)
        except subprocess.SubprocessError:raise ValueError('Review startup is unconfirmed. Check its private runtime.log; no additional start was attempted.') from None
        owner=Owner(profile)
    try:
        owner.verify(entry,files);link=private_link(owner.call('harness.open',{'sessionId':profile['sessionId']} if profile.get('sessionId') else {}),profile)
    finally:owner.close()
    if print_url:print(link)
    else:
        try:subprocess.run(['xdg-open',link],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15)
        except subprocess.SubprocessError:raise ValueError('The browser did not confirm opening. Use open REVIEW --print-url for its current private link.') from None

def desktop_field(value):return '"'+str(value).replace('\\','\\\\').replace('"','\\"').replace('$','\\$').replace('`','\\`').replace('%','%%')+'"'
def installed_paths(root,identity,title,icon):
    home=Path.home();data=Path(os.environ.get('XDG_DATA_HOME',home/'.local/share'));binary=home/'.local/bin/augmentor-harness-review';desktop=data/'applications'/('com.augmentor.HarnessReview.'+identity+'.desktop');image=data/'icons/hicolor/scalable/apps/com.augmentor.HarnessReview.svg'
    text='# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0\n[Desktop Entry]\nType=Application\nName='+title+'\nComment=Open the registered MX Harness review with a fresh private link\nExec='+desktop_field(binary)+' --registry '+desktop_field(root)+' open '+identity+'\nIcon=com.augmentor.HarnessReview\nTerminal=false\nCategories=Utility;\n'
    return {binary:(Path(__file__).read_bytes(),0o700),desktop:(text.encode(),0o644),image:(icon,0o644)}

def change_registry(root,identity,expected,entry=None,install=False):
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,31}',identity):raise ValueError('Choose a short lowercase review name.')
    with registry_lock(root):
        old=registry_read(root)
        if expected!=old['revision']:raise ValueError('Review registration changed. Read status before updating it.')
        if entry is None and identity not in old['entries']:raise ValueError('Review registration was not found.')
        new=json.loads(json.dumps(old));new['revision']+=1;files={}
        if entry is None:
            prior=new['entries'].pop(identity)
            for path in prior.get('menuFiles',[]):files[Path(path)]=(None,None)
        else:
            if len(new['entries'])>=16 and identity not in new['entries']:raise ValueError('The review registry is full.')
            if install:
                tool_root=Path(__file__).resolve().parents[1];_,tool_files=sealed_release(tool_root)
                if tool_files.get('scripts/harness-review.py')!=digest(Path(__file__).read_bytes()):raise ValueError('Install the opener from its sealed tool artifact.')
                icon=(tool_root/'apps/harness/vendor/augmentor-brand/favicon.svg').read_bytes();files=installed_paths(root,identity,entry['title'],icon);entry['menuFiles']=[str(p) for p in files if p.suffix=='.desktop']
            elif identity in new['entries'] and new['entries'][identity].get('menuFiles'):raise ValueError('Use --install when updating an installed menu registration.')
            new['entries'][identity]=entry
        # Preflight every intended write before replacing any owned artifact.
        saved={}
        for path in files:
            if path.exists() or path.is_symlink():
                s=path.lstat()
                if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.getuid() or s.st_nlink!=1 or old['ownedFiles'].get(str(path))!=digest(path.read_bytes()):raise ValueError('A menu/opener file is unowned or was edited. It was preserved.')
                saved[path]=(path.read_bytes(),stat.S_IMODE(s.st_mode))
            else:saved[path]=None
            directory(path.parent,private=False,create=True)
        backup=root/'backups'/str(uuid.uuid4());backup.mkdir(parents=True,mode=0o700);atomic_bytes(backup/'registry.json',json.dumps(old,indent=2).encode()+b'\n')
        for i,(path,value) in enumerate(saved.items()):
            if value:atomic_bytes(backup/(str(i)+'.original'),value[0])
        written=[]
        try:
            for path,(data,mode) in files.items():
                if data is None:path.unlink();new['ownedFiles'].pop(str(path),None)
                else:atomic_bytes(path,data,mode);new['ownedFiles'][str(path)]=digest(data)
                written.append(path)
                if path.suffix=='.desktop' and data is not None:subprocess.run(['desktop-file-validate',str(path)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5)
            atomic_bytes(root/'reviews.json',json.dumps(new,indent=2).encode()+b'\n')
        except BaseException:
            for path in reversed(written):
                if saved[path] is None:path.unlink(missing_ok=True)
                else:atomic_bytes(path,*saved[path])
            raise
        return new

class Arguments(argparse.ArgumentParser):
    def error(self,message):self.exit(2,'Use status, register, open or remove; see --help. Argument values were not logged.\n')

def main():
    if sys.platform!='linux':raise ValueError('Review launch/recovery currently targets MX Linux; other OS adapters remain unqualified.')
    parser=Arguments(description=__doc__);parser.add_argument('--registry',type=Path,default=Path(os.environ.get('XDG_CONFIG_HOME',Path.home()/'.config'))/'augmentor-harness/reviews');commands=parser.add_subparsers(dest='command',required=True)
    register=commands.add_parser('register');register.add_argument('review');register.add_argument('--release',type=Path,required=True);register.add_argument('--profile',type=Path,required=True);register.add_argument('--title',required=True);register.add_argument('--expected-revision',type=int,required=True);register.add_argument('--install',action='store_true')
    remove=commands.add_parser('remove');remove.add_argument('review');remove.add_argument('--expected-revision',type=int,required=True)
    opened=commands.add_parser('open');opened.add_argument('review');opened.add_argument('--print-url',action='store_true');commands.add_parser('status');args=parser.parse_args();root=canonical(str(args.registry))
    if args.command=='register':
        if not args.title.strip() or len(args.title)>120 or any(ord(c)<32 for c in args.title):raise ValueError('Choose a short one-line menu title.')
        selected,files=sealed_release(args.release);profile=profile_record(read_private(args.profile));entry={'title':args.title,'deployment':selected,'profile':profile}
        try:owner=Owner(profile)
        except (FileNotFoundError,ConnectionRefusedError):
            if live_profile(profile):raise ValueError('The review has a live unconfirmed owner. Registration was preserved.')
        else:
            try:owner.verify(entry,files)
            finally:owner.close()
        value=change_registry(root,args.review,args.expected_revision,entry,args.install);print(json.dumps({'revision':value['revision'],'review':args.review,'releaseId':selected['releaseId'],'menuInstalled':args.install}));return
    if args.command=='remove':print(json.dumps({'revision':change_registry(root,args.review,args.expected_revision)['revision']}));return
    with registry_lock(root):
        value=registry_read(root)
        if args.command=='status':print(json.dumps({'revision':value['revision'],'reviews':[{'review':key,'title':entry['title'],'releaseId':entry['deployment']['releaseId'],'version':entry['deployment']['version']} for key,entry in value['entries'].items()]}));return
        entry=value['entries'].get(args.review)
        if not entry:raise ValueError('This review is not registered. No empty profile was created.')
        open_review(entry,args.print_url)

if __name__=='__main__':
    try:main()
    except (Exception,KeyboardInterrupt) as error:
        # Subprocess command strings can contain the bearer. Never print them.
        message='The review operation was not confirmed; inspect its private logs.' if isinstance(error,subprocess.SubprocessError) else str(error)
        print('Augmentor Harness: '+message,file=sys.stderr);raise SystemExit(1)
