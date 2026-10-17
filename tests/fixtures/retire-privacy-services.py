# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
# Only the caller's independently authored temporary privacy-test namespace.
import json,os,signal,selectors,sys,tempfile
from pathlib import Path
home=Path(sys.argv[1]);browser_closed='--browser-closed' in sys.argv;roots=[Path(value) for value in sys.argv[2:] if value!='--browser-closed']
assert home.parent.resolve()==Path(tempfile.gettempdir()).resolve() and home.name.startswith('augmentor-privacy-upgrade-')
shared=str(home/'shared-state');allowed={str(root/'services'/kind/'service.py') for root in roots for kind in ['memory','prompt-library']};selected=[]
def actors():
 for proc in Path('/proc').iterdir():
  if not proc.name.isdigit():continue
  try:
   if proc.stat().st_uid!=os.getuid() or (proc/'stat').read_text().rsplit(')',1)[1].split()[0]=='Z':continue
   args=[value.decode() for value in (proc/'cmdline').read_bytes().split(b'\0') if value];env=dict(value.decode().split('=',1) for value in (proc/'environ').read_bytes().split(b'\0') if b'=' in value)
   if env.get('HOME')==str(home) and env.get('AUGMENTOR_SHARED_STATE')==shared:yield proc,args,env
  except (OSError,UnicodeError,ValueError):continue
assert not any(Path(args[0]).name in ('node','nodejs') and any(arg.endswith('/dist/runtime/src/main.js') for arg in args) for _,args,_ in actors()),'A test Host is still running; do not stop its companions.'
try:
 for proc,args,env in actors():
  is_service=any(arg in allowed for arg in args)
  is_crashpad=browser_closed and Path(args[0]).name=='chrome_crashpad_handler' and any(arg.startswith('--database='+str(home)+'/') for arg in args)
  if not is_service and not is_crashpad:continue
  original=(proc/'stat').read_text().rsplit(')',1)[1].split()[19];fd=os.pidfd_open(int(proc.name))
  if (proc/'stat').read_text().rsplit(')',1)[1].split()[19]!=original:os.close(fd);raise RuntimeError('Test actor identity changed; preserve its state.')
  selected.append((fd,is_service))
 for fd,_ in selected:
  signal.pidfd_send_signal(fd,signal.SIGTERM)
  with selectors.DefaultSelector() as watch:watch.register(fd,selectors.EVENT_READ);assert watch.select(10),'A test companion did not terminate; preserve evidence.'
 print(json.dumps({'retiredCompanions':sum(service for _,service in selected),'retiredBrowserHelpers':sum(not service for _,service in selected)}))
finally:
 for fd,_ in selected:os.close(fd)
