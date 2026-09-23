#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Exercise installed companion recovery on a disposable signed bundle copy."""
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import select
import struct
import time
import sys
import tempfile

if sys.platform!='darwin':raise SystemExit('Run on macOS.')
original=Path(sys.argv[1]).resolve(strict=True)
tools=original/'Contents/Resources/app/scripts'
spec=importlib.util.spec_from_file_location('uninstaller',tools/'uninstall-macos.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
assert module.installer.validate(original,development=True)['component']=='companion'
fixture=Path(tempfile.mkdtemp(prefix='augmentor-companion-lifecycle-',dir='/tmp'))
app=fixture/'Disposable Companion.app'
subprocess.run(['ditto',str(original),str(app)],check=True)
os.environ['XDG_RUNTIME_DIR']=str(fixture/'runtime')
support=fixture/'support'
sentinel=fixture/'user-data.json';sentinel.write_text('retained companion fixture data')
login=Path.home()/'Library/LaunchAgents/com.augmentor.Agent.shortcut.plist'
before=login.read_bytes() if login.exists() else None
host=support/'Chromium/NativeMessagingHosts'
module.browser.register(module.browser.manifest(app),host)
# Verify both the lock invariant and, optionally, the packaged launcher/exec path.
real_host=os.environ.get('AUGMENTOR_PROOF_REAL_HOST_LEASE')=='1'
process=None;descriptor=None
if real_host:
    process=subprocess.Popen([str(app/'Contents/MacOS/augmentor-browser-host')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    def read_exact(length):
        data=b'';deadline=time.monotonic()+10
        while len(data)<length:
            remaining=deadline-time.monotonic()
            if remaining<=0 or not select.select([process.stdout],[],[],remaining)[0]:
                raise AssertionError('Packaged host reply timed out')
            chunk=os.read(process.stdout.fileno(),length-len(data))
            if not chunk:raise AssertionError('Packaged host closed before replying')
            data+=chunk
        return data
    version=module.installer.validate(app,development=True)['version']
    def handshake(identity):
        data=json.dumps({'id':identity,'method':'augmentor/handshake','params':{'protocol':'augmentor/1','version':version}}).encode()
        process.stdin.write(struct.pack('<I',len(data))+data);process.stdin.flush()
        length=struct.unpack('<I',read_exact(4))[0];assert length<1024*1024
        reply=json.loads(read_exact(length));assert reply['id']==identity and reply['result']['version']==version,reply
else:
    descriptor=module.installer.installation_lock()
    fcntl.flock(descriptor,fcntl.LOCK_SH)
try:
    if real_host:handshake('before-removal')
    try:module.uninstall(app,support=support)
    except BlockingIOError:pass
    else:raise AssertionError('Active component did not prevent removal')
    assert app.exists() and (host/'com.augmentor.agent.json').exists()
    if real_host:
        assert process.poll() is None
        handshake('after-refused-removal')
finally:
    if descriptor is not None:os.close(descriptor)
    if process:
        process.stdin.close()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=5)
        process.stdout.close();process.stderr.close()
removed=module.uninstall(app,support=support)
assert not app.exists() and not (host/'com.augmentor.agent.json').exists()
receipt=Path(removed['receipt'])
assert not json.loads(receipt.read_text())['shortcutWasRunning']
interrupted=os.environ.get('AUGMENTOR_PROOF_INTERRUPT_RESTORE')=='1'
if interrupted:
    code="""import importlib.util,os,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('uninstaller',sys.argv[1])
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
app=Path(sys.argv[4]);rename=Path.rename
def cut_off(self,destination):
    result=rename(self,destination)
    if destination==app:os._exit(19)
    return result
Path.rename=cut_off
m.restore(Path(sys.argv[2]),support=Path(sys.argv[3]))
"""
    child=subprocess.run([sys.executable,'-I','-B','-c',code,str(module.__file__),str(receipt),str(support),str(app)])
    assert child.returncode==19,child.returncode
    assert app.exists() and not (host/'com.augmentor.agent.json').exists()
module.restore(receipt,support=support)
module.restore(receipt,support=support)
module.installer.validate(app,development=True)
assert json.loads((host/'com.augmentor.agent.json').read_text())==module.browser.manifest(app)
assert sentinel.read_text()=='retained companion fixture data'
assert (login.read_bytes() if login.exists() else None)==before
final=module.uninstall(app,support=support)
assert original.exists() and not app.exists()
result={'installedTools':str(tools),'activeLeaseRefusedRemoval':True,'packagedHostLease':real_host,
        'signedCompanionRestored':True,'repeatRestore':True,'interruptedAfterAppRestore':interrupted,
        'registrationRestored':True,'desktopShortcutUnchanged':True,
        'userDataPreserved':True,'originalPreserved':True,
        'fixture':str(fixture),'retainedReceipt':final['receipt']}
print(json.dumps(result))
