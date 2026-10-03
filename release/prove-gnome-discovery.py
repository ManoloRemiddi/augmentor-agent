#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import argparse,json,os,subprocess,time,re,shutil
import hashlib
from pathlib import Path
parser=argparse.ArgumentParser(description='Read-only compositor-interface discovery in an isolated GNOME fixture. Does not qualify login or input.')
parser.add_argument('--out',type=Path,required=True)
parser.add_argument('--exercise-custom-shortcuts',action='store_true',help='Exercise native GSD with synthetic input in this private compositor only.')
parser.add_argument('--exercise-augmentor-shortcuts',action='store_true',help='Exercise Augmentor shared Qt Save rows and native GNOME adapter in this private compositor.')
parser.add_argument('--exercise-gnome-observer',action='store_true',help='Install/read the observer only inside the private compositor fixture.')
parser.add_argument('--exercise-native-ui',choices=('wayland','xcb'),help='Exercise existing actual Augmentor windows through canonical GSD launchers in this private compositor.')
parser.add_argument('--exercise-workspace-follow',action='store_true',help='Test existing XWayland pin/unpin and independent workspace following in this private compositor.')
args=parser.parse_args()
if args.exercise_workspace_follow and args.exercise_native_ui!='xcb':parser.error('Workspace follow proof requires --exercise-native-ui xcb.')
production=args.exercise_augmentor_shortcuts
observer=args.exercise_gnome_observer or bool(args.exercise_native_ui)
exercise=args.exercise_custom_shortcuts or production or observer
if os.geteuid()==0 or not any(Path(p).exists() for p in ('/.dockerenv','/run/.containerenv')):
 raise SystemExit('Use an ordinary user in a disposable Docker/Podman container.')
if Path('/run/systemd/seats').exists():
 raise SystemExit('Use a private headless fixture with --tmpfs /run/systemd; full logind acceptance is separate.')
root=Path.home();run=Path(os.environ['XDG_RUNTIME_DIR']);run.mkdir(mode=0o700,exist_ok=True)
out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
proof=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
os.environ.update(XDG_RUNTIME_DIR=str(run),XDG_CURRENT_DESKTOP='GNOME',XDG_SESSION_TYPE='wayland',GNOME_SHELL_SESSION_MODE='user',LIBGL_ALWAYS_SOFTWARE='1',GALLIUM_DRIVER='llvmpipe',WAYLAND_DISPLAY='wayland-augmentor')
# dbus-run-session started before Python set these values. Propagate only the
# private graphical environment so early Shell/IBus activation selects GNOME.
subprocess.run(['dbus-update-activation-environment','XDG_CURRENT_DESKTOP','XDG_SESSION_TYPE',
                'GNOME_SHELL_SESSION_MODE','WAYLAND_DISPLAY','XDG_RUNTIME_DIR','DISPLAY'],check=True,timeout=5)
processes=[]
try:
 if exercise:
  # The fresh private user would otherwise receive a modal welcome tour,
  # which correctly prevents ordinary launcher shortcut delivery.
  subprocess.run(['gsettings','set','org.gnome.shell','welcome-dialog-last-shown-version','50.5'],check=True,timeout=5)
 if observer:
  uuid='observer@augmentoragent.com'
  source=Path(__file__).resolve().parents[1]/'services/desktop/gnome-extension'/uuid
  destination=root/'.local/share/gnome-shell/extensions'/uuid
  shutil.copytree(source,destination)
  subprocess.run(['gsettings','set','org.gnome.shell','enabled-extensions',"['"+uuid+"']"],check=True,timeout=5)
 for name,command in [('pipewire',['pipewire']),('wireplumber',['wireplumber']),('shell',['gnome-shell','--headless','--wayland','--virtual-monitor','1280x800','--wayland-display','wayland-augmentor'])]:
  log=(out/(name+'.log')).open('w');processes.append((subprocess.Popen(command,stdout=log,stderr=log),log))
 deadline=time.monotonic()+45
 while time.monotonic()<deadline:
  if processes[-1][0].poll() is not None:raise RuntimeError('GNOME shell exited before readiness')
  query=subprocess.run(['gdbus','call','--session','--dest','org.freedesktop.DBus','--object-path','/org/freedesktop/DBus','--method','org.freedesktop.DBus.NameHasOwner','org.gnome.Shell'],capture_output=True,text=True,timeout=2)
  if '(true,)' in query.stdout and (run/'wayland-augmentor').exists():break
  time.sleep(.2)
 else:raise RuntimeError('GNOME session did not become ready')
 time.sleep(2)
 owner=subprocess.check_output(['gdbus','call','--session','--dest','org.freedesktop.DBus','--object-path','/org/freedesktop/DBus','--method','org.freedesktop.DBus.GetConnectionUnixProcessID','org.gnome.Shell'],text=True,timeout=2)
 pid=re.search(r'uint32 (\d+)',owner)
 if not pid or int(pid[1])!=processes[-1][0].pid:raise RuntimeError('The session bus is not owned by this fixture compositor')
 for name,path,label in [('org.gnome.Shell','/org/gnome/Shell','shell'),('org.gnome.Mutter.DisplayConfig','/org/gnome/Mutter/DisplayConfig','display'),('org.gnome.Mutter.RemoteDesktop','/org/gnome/Mutter/RemoteDesktop','input'),('org.freedesktop.portal.Desktop','/org/freedesktop/portal/desktop','portal')]:
  query=subprocess.run(['gdbus','introspect','--session','--dest',name,'--object-path',path],capture_output=True,text=True,timeout=4)
  (out/(label+'-interfaces.txt')).write_text(query.stdout)
  if query.returncode:raise RuntimeError('Failed interface discovery for '+label)
 version=subprocess.check_output(['gnome-shell','--version'],text=True).strip()
 portal=(out/'portal-interfaces.txt').read_text()
 portal_versions={}
 for interface,body in re.findall(r'interface (org\.freedesktop\.portal\.\w+)\s*\{(.*?)\n\s*\};',portal,re.S):
  version_property=re.search(r'\bversion\s*=\s*(\d+)',body)
  if version_property:portal_versions[interface.rsplit('.',1)[-1]]=int(version_property[1])
 for interface,minimum in {'RemoteDesktop':2,'ScreenCast':5,'GlobalShortcuts':1}.items():
  if portal_versions.get(interface,0)<minimum:raise RuntimeError('GNOME portal interface unavailable: '+interface)
 report={'portalVersions':portal_versions,'proofScriptSha256':proof,'shell':version,'virtualMonitor':'1280x800','waylandSocket':True,'privateBus':True,'compositorOwnerMatchesChild':True,'softwareRendering':True,'loginManager':'GNOME built-in dummy (headless fixture)','interfaces':{label:hashlib.sha256((out/(label+'-interfaces.txt')).read_bytes()).hexdigest() for label in ('shell','display','input','portal')},'actualInputTested':False,'portalConsentTested':False,'actualLoginRebootTested':False}
 (out/'session.json').write_text(json.dumps(report,indent=2)+'\n')
 print('ISOLATED GNOME SESSION READY')
 if args.exercise_custom_shortcuts or production:
  subprocess.run(['python3',str(Path(__file__).with_name('prove-gnome-custom-shortcuts.py')),
                  '--compositor-pid',str(processes[-1][0].pid),'--out',str(out),
                  *(['--production-adapter'] if production else [])],check=True,timeout=90)
 if args.exercise_gnome_observer:
  subprocess.run(['python3',str(Path(__file__).with_name('prove-gnome-observer.py')),
                  '--compositor-pid',str(processes[-1][0].pid),'--out',str(out)],check=True,timeout=90)
 if args.exercise_native_ui:
  subprocess.run(['python3',str(Path(__file__).with_name('prove-gnome-native-ui.py')),
                  '--compositor-pid',str(processes[-1][0].pid),'--out',str(out),
                  '--platform',args.exercise_native_ui,
                  *(['--workspace-follow'] if args.exercise_workspace_follow else [])],check=True,timeout=120)
finally:
 for process,log in reversed(processes):
  if process.poll() is None:
   process.terminate()
   try:process.wait(timeout=5)
   except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
  log.close()
