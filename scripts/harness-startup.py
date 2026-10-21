#!/usr/bin/python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""MX login/recovery controller for an explicitly registered, immutable Harness."""
import argparse
from contextlib import redirect_stdout
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import select
import shlex
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
import types
import urllib.request
import urllib.error

SERVICE='augmentor-harness.service'
SCHEMA='augmentor-harness-startup/1'
GRAPHICS=('DISPLAY','WAYLAND_DISPLAY','XAUTHORITY','XDG_SESSION_TYPE','XDG_CURRENT_DESKTOP','DESKTOP_SESSION')


def paths():
    home=Path.home()
    return home,Path(os.environ.get('XDG_DATA_HOME',home/'.local/share'))/'augmentor-harness/startup',Path(os.environ.get('XDG_CONFIG_HOME',home/'.config'))


def private_bytes(path,limit=2*1024**2,public=False):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_nlink!=1 or info.st_size>limit or info.st_mode & (0o022 if public else 0o077):raise ValueError('An installed startup file is unsafe or was replaced. Preserve it and reinstall the controller.')
        raw=os.read(fd,limit+1)
        if len(raw)>limit:raise ValueError('Startup record exceeds its bound.')
        return raw
    finally:os.close(fd)


def atomic(path,raw,mode=0o600):
    path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.'+path.name+'-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(raw);os.fchmod(f.fileno(),mode);f.flush();os.fsync(f.fileno())
        os.replace(name,path)
        fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)
    finally:
        if os.path.exists(name):os.unlink(name)


def configuration():
    _,data,_=paths();value=json.loads(private_bytes(data/'current.json'))
    if value.get('schema')!=SCHEMA or not isinstance(value.get('review'),str) or not value['review'].isalnum():raise ValueError('The startup selection is invalid; no alternate profile was started.')
    for key in ('registry','opener'):
        p=Path(value[key])
        if not p.is_absolute() or str(p.resolve())!=str(p):raise ValueError('Startup paths must be explicit and cannot contain aliases.')
    return value


def review_tool(config):
    raw=private_bytes(Path(config['opener']))
    registry=json.loads(private_bytes(Path(config['registry'])/'reviews.json'))
    if registry.get('ownedFiles',{}).get(config['opener'])!=hashlib.sha256(raw).hexdigest():raise ValueError('The registered review opener was changed; no runtime was started.')
    tool=types.ModuleType('verified_harness_review');tool.__file__=config['opener'];exec(compile(raw,config['opener'],'exec'),tool.__dict__)
    return tool


def selection(config,tool,browser=False):
    with tool.registry_lock(Path(config['registry'])):
        value=tool.registry_read(Path(config['registry']));entry=value['entries'].get(config['review'])
        if entry is None:raise ValueError('The chosen Harness is no longer registered; no empty or alternate profile was created.')
        # This performs the existing full seal/profile/maintenance/startup checks.
        # Never emit its private login URL to stdout, the journal or a status file.
        with redirect_stdout(io.StringIO()):tool.open_review(entry,not browser)
        stamp=hashlib.sha256(private_bytes(Path(config['registry'])/'reviews.json')).hexdigest()
    return entry,stamp


def http_ready(pid,port,proc_root=Path('/proc')):
    # Match the listener to the verified IPC peer before declaring the bookmark ready.
    # Health requests carry no bearer, including when a different app owns the port.
    proc=proc_root/str(pid);address='0100007F:'+format(port,'04X')
    listeners={line.split()[9] for line in (proc/'net/tcp').read_text().splitlines()[1:] if len(line.split())>9 and line.split()[1]==address and line.split()[3]=='0A'}
    owned=set()
    for fd in (proc/'fd').iterdir():
        try:link=os.readlink(fd)
        except FileNotFoundError:continue
        if link.startswith('socket:['):owned.add(link[8:-1])
    if not listeners.intersection(owned):raise ValueError('The chosen Harness does not own its fixed browser port. No other listener was contacted.')
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open('http://127.0.0.1:'+str(port)+'/api/access',timeout=2):pass
    except urllib.error.HTTPError as error:
        if error.code==401:return
    raise ValueError('The fixed browser endpoint did not confirm its expected access boundary.')


def verified_owner(tool,entry):
    owner=tool.Owner(entry['profile'])
    try:
        status=owner.call('host.describe',{});p=entry['profile'];pid=status.get('pid')
        if pid!=owner.peer[0] or status.get('stateDir')!=p['state'] or status.get('configDir')!=p['config'] or status.get('version')!=entry['deployment']['version']:raise ValueError('The running owner differs from the chosen Harness. It was preserved.')
        cmd=(Path('/proc')/str(pid)/'cmdline').read_bytes().split(b'\0')
        if os.fsencode(str(Path(entry['deployment']['root'])/'dist/runtime/src/main.js')) not in cmd:raise ValueError('The running build differs from registration. It was preserved.')
        http_ready(pid,p['port'])
        return pid
    finally:owner.close()


def startup_message(error):
    text=str(error).lower()
    if 'maintenance' in text or 'requires recovery' in text:return 'Waiting for managed application maintenance or its recovery. Existing work is preserved.'
    if 'fixed browser port' in text:return 'The fixed Harness browser port is unavailable. It will retry without changing the address.'
    if 'live process' in text or 'running owner' in text:return 'An existing owner is unconfirmed. It is preserved; no replacement is started.'
    if 'changed after staging' in text or 'opener was changed' in text:return 'Installed-file verification failed. Reinstall the verified application or startup controller.'
    if isinstance(error,FileNotFoundError):return 'A registered installation or project path is unavailable. Restore that path; no empty replacement is created.'
    return 'Waiting for verified Harness startup. Existing owners, work and maintenance fences are preserved.'


def supervise(stop=None,interval=5):
    stop=stop or threading.Event();_,data,_=paths();data.mkdir(parents=True,mode=0o700,exist_ok=True)
    fd=os.open(data/'supervisor.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_nlink!=1 or info.st_mode&0o077:raise ValueError('The supervisor lock is unsafe.')
        try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        entry=None;pid=None;stamp=None;last=None;pidfd=None
        atomic(data/'status.json',(json.dumps({'schema':SCHEMA,'state':'starting'})+'\n').encode())
        while not stop.is_set():
            try:
                config=configuration();tool=review_tool(config)
                current=hashlib.sha256(private_bytes(Path(config['registry'])/'reviews.json')).hexdigest()
                exited=pidfd is not None and bool(select.select([pidfd],[],[],0)[0])
                if entry is None or current!=stamp or exited:
                    entry,stamp=selection(config,tool);pid=verified_owner(tool,entry)
                    if pidfd is not None:os.close(pidfd)
                    pidfd=os.pidfd_open(pid)
                else:
                    # Probe only known ownership, never terminate a slow/unresponsive owner.
                    if verified_owner(tool,entry)!=pid:entry=None;raise ValueError('Owner changed; checking registration before adopting it.')
                state='ready';message='Augmentor Harness is ready.';detail={'schema':SCHEMA,'state':state,'pid':pid,'review':config['review'],'port':entry['profile']['port'],'artifactSha256':entry['deployment']['artifactSha256']}
                atomic(data/'status.json',(json.dumps(detail)+'\n').encode())
            except Exception as error:
                entry=None;state='waiting';message=startup_message(error);atomic(data/'status.json',(json.dumps({'schema':SCHEMA,'state':state,'message':message})+'\n').encode())
            if message!=last:print(message,flush=True);last=message
            stop.wait(interval)
        if pidfd is not None:os.close(pidfd)
    finally:os.close(fd)


def start_service():
    envnames=[key for key in GRAPHICS if os.environ.get(key)]
    if envnames:subprocess.run(['systemctl','--user','import-environment',*envnames],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10,check=True)
    subprocess.run(['systemctl','--user','start',SERVICE],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15)


def open_app():
    # The explicit launcher remains useful if the session service manager is unavailable.
    try:start_service()
    except (OSError,subprocess.SubprocessError):pass
    config=configuration();tool=review_tool(config);deadline=time.monotonic()+90
    while True:
        try:selection(config,tool,browser=True);return
        except ValueError as error:
            if 'registration is busy' not in str(error) or time.monotonic()>=deadline:raise
            time.sleep(1)


def install(registry,review):
    home,data,config=paths()
    if any(p.resolve()!=p for p in (home,data,config)):raise ValueError('Startup locations cannot use path aliases.')
    registry=registry.resolve(strict=True);opener=home/'.local/bin/augmentor-harness-review'
    selected={'schema':SCHEMA,'registry':str(registry),'review':review,'opener':str(opener)}
    tool=review_tool(selected)
    with tool.registry_lock(registry):
        entry=tool.registry_read(registry)['entries'].get(review)
        if not entry:raise ValueError('Choose an existing registered Harness.')
        tool.profile_record(entry['profile']);deployment,_=tool.sealed_release(entry['deployment']['root'])
        if deployment!=entry['deployment']:raise ValueError('The registered build changed.')
    if not entry['profile']['port']:raise ValueError('Register a fixed local port before enabling bookmark startup.')
    raw=Path(__file__).read_bytes();digest=hashlib.sha256(raw).hexdigest();controller=data/'controllers'/digest/'startup.py';selected.update(controller=str(controller),sha256=digest)
    bootstrap='''#!/usr/bin/python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import hashlib,json,os,stat,sys
from pathlib import Path
root=Path(__file__).parent
try:
 def read(p):
  fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
  try:
   s=os.fstat(fd)
   if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.getuid() or s.st_nlink!=1 or s.st_mode&0o077 or s.st_size>2097152:raise ValueError()
   return os.read(fd,2097153)
  finally:os.close(fd)
 c=json.loads(read(root/'current.json'));p=root/'controllers'/c['sha256']/'startup.py'
 if str(p)!=c['controller'] or p.resolve()!=p:raise ValueError()
 raw=read(p)
 if hashlib.sha256(raw).hexdigest()!=c['sha256']:raise ValueError()
 globals()['__file__']=str(p);exec(compile(raw,str(p),'exec'))
except Exception:
 print('Augmentor Harness startup is unavailable. Reinstall its verified startup controller.',file=sys.stderr);sys.exit(1)
'''.encode()
    wrapper=('#!/bin/sh\nexec /usr/bin/python3 -B '+shlex.quote(str(data/'launch.py'))+' "$@"\n').encode();binary=home/'.local/bin/augmentor-harness';field=tool.desktop_field
    def unit_field(value):return '"'+str(value).replace('\\','\\\\').replace('"','\\"').replace('%','%%').replace('$','$$')+'"'
    desktop=('# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0\n[Desktop Entry]\nType=Application\nName=Augmentor Harness\nComment=Start and open your saved Augmentor Harness\nExec='+field(binary)+'\nIcon=com.augmentor.HarnessReview\nTerminal=false\nCategories=Utility;\n').encode()
    login=desktop.replace(b'Name=Augmentor Harness\n',b'Name=Augmentor Harness startup\n').replace(('Exec='+field(binary)+'\n').encode(),('Exec='+field(binary)+' --login\n').encode())+b'X-GNOME-Autostart-enabled=true\n'
    unit=('[Unit]\nDescription=Augmentor Harness startup and recovery\nPartOf=graphical-session.target\nAfter=graphical-session.target\nStartLimitIntervalSec=0\n\n[Service]\nType=exec\nExecStart='+unit_field(binary)+' --service\nRestart=always\nRestartSec=5\nKillMode=process\nTimeoutStopSec=12\nUMask=0077\n\n[Install]\nWantedBy=graphical-session.target\n').encode()
    files={controller:(raw,0o600),data/'launch.py':(bootstrap,0o600),binary:(wrapper,0o700),config/'systemd/user'/SERVICE:(unit,0o600),config/'autostart/com.augmentor.Harness.desktop':(login,0o600),Path(os.environ.get('XDG_DATA_HOME',home/'.local/share'))/'applications/com.augmentor.Harness.desktop':(desktop,0o644)}
    data.mkdir(parents=True,mode=0o700,exist_ok=True)
    previous_raw=private_bytes(data/'owned.json') if (data/'owned.json').exists() else None
    previous=json.loads(previous_raw) if previous_raw is not None else {}
    previous_selection=private_bytes(data/'current.json') if (data/'current.json').exists() else None
    if previous_selection is not None and not previous:raise ValueError('An unowned startup selection was preserved.')
    for path,(body,mode) in files.items():
        if path.exists() or path.is_symlink():
            old=private_bytes(path,public=mode==0o644)
            if previous.get(str(path))!=hashlib.sha256(old).hexdigest():raise ValueError('An unowned or edited startup file was preserved; review it before installation.')
    # Save small control-file recovery only; no application/profile copy.
    backup=Path(tempfile.mkdtemp(prefix='before-',dir=data));old_selection=data/'current.json'
    if old_selection.exists():atomic(backup/'current.json',private_bytes(old_selection))
    if previous:atomic(backup/'owned.json',json.dumps(previous).encode())
    written=[]
    try:
        for index,(path,(body,mode)) in enumerate(files.items()):
            old=private_bytes(path,public=mode==0o644) if path.exists() else None
            if old is not None:atomic(backup/(str(index)+'.original'),old)
            written.append((path,old,mode));atomic(path,body,mode)
        for path in files:
            if path.suffix=='.desktop':subprocess.run(['desktop-file-validate',str(path)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        subprocess.run(['systemd-analyze','--user','verify',str(config/'systemd/user'/SERVICE)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        atomic(data/'owned.json',json.dumps({str(p):hashlib.sha256(b).hexdigest() for p,(b,_) in files.items()},indent=2).encode())
        atomic(old_selection,(json.dumps(selected,indent=2)+'\n').encode())
    except BaseException:
        for record,old in ((data/'owned.json',previous_raw),(old_selection,previous_selection)):
            if old is None:record.unlink(missing_ok=True)
            else:atomic(record,old)
        for path,old,mode in reversed(written):
            if old is None:path.unlink(missing_ok=True)
            else:atomic(path,old,mode)
        raise
    print(json.dumps({'installed':True,'controllerSha256':digest,'review':review,'port':entry['profile']['port'],'backup':str(backup)}))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--install',action='store_true');parser.add_argument('--registry',type=Path);parser.add_argument('--review');parser.add_argument('--service',action='store_true');parser.add_argument('--login',action='store_true');parser.add_argument('--status',action='store_true');args=parser.parse_args()
    if sys.platform!='linux':raise ValueError('This startup controller is qualified only for MX Linux.')
    if args.install:
        if not args.registry or not args.review:raise ValueError('Choose an explicit registry and review.')
        install(args.registry,args.review)
    elif args.service:
        stop=threading.Event()
        for sig in (signal.SIGINT,signal.SIGTERM):signal.signal(sig,lambda *_:stop.set())
        supervise(stop)
    elif args.login:start_service()
    elif args.status:
        config=configuration();tool=review_tool(config);entry=tool.registry_read(Path(config['registry']))['entries'][config['review']];pid=verified_owner(tool,entry);print(json.dumps({'state':'ready','review':config['review'],'port':entry['profile']['port'],'pid':pid,'artifactSha256':entry['deployment']['artifactSha256']}))
    else:open_app()


if __name__=='__main__':
    try:main()
    except (Exception,KeyboardInterrupt):
        message='Augmentor Harness could not confirm startup. Your saved projects are preserved. Try the Augmentor Harness launcher again, or check journalctl --user -u augmentor-harness.service.'
        print(message,file=sys.stderr)
        if not any(arg in sys.argv for arg in ('--install','--service','--login','--status')):
            try:subprocess.run(['zenity','--error','--title=Augmentor Harness','--text='+message],timeout=30,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            except (OSError,subprocess.SubprocessError):pass
        raise SystemExit(1)
