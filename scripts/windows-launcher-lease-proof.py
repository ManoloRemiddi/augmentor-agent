#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Test compiled pre-Python startup exclusion in explicitly disposable data."""
import os
from pathlib import Path
import shutil
import subprocess
import sys


def prove(root, work):
    import win32con
    import win32file
    import win32security
    from platform_adapters import locks
    from platform_adapters.windows_identity import private_directory, private_lock_descriptor
    from lifecycle.windows_startup import Startup

    base = private_directory(work/'native-startup')
    private_directory(base/'run')
    lock = base/'run/installation.lock'
    # A separate copy deliberately has no runtime. If exclusion happens after
    # loading Python it cannot produce the specific early-refusal exit code.
    copies = private_directory(work/'no-runtime')
    applications = []
    for name in ('Augmentor.exe', 'AugmentorBrowserHost.exe'):
        shutil.copy2(root/name, copies/name)
        applications.append(copies/name)

    def refused(directory):
        for application in applications:
            result = subprocess.run([str(application), '--qualification-root', str(directory), '--preview'],
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
            assert result.returncode == 73, (application.name, result.returncode, result.stderr)

    fd = private_lock_descriptor(lock)
    try:
        os.write(fd, b'preserved')
        locks.flock(fd, locks.LOCK_EX|locks.LOCK_NB)
        refused(base)
    finally: os.close(fd)
    assert lock.read_bytes() == b'preserved'
    assert not (base/'config').exists(), 'A blocked launch reached Python configuration.'

    # The installer's no-sharing gate and Python byte lock both exclude native
    # startup. Release is kernel-owned; neither failure leaves a pending marker.
    gate = win32file.CreateFile(str(lock), win32con.GENERIC_READ|win32con.GENERIC_WRITE,
        0, None, win32con.OPEN_EXISTING, win32file.FILE_FLAG_OPEN_REPARSE_POINT, None)
    try: refused(base)
    finally: gate.Close()

    with Startup(base/'run', maintenance=True): refused(base)
    startup = base/'run/startup.lock'
    os.link(startup, base/'startup-second-link')
    try: refused(base)
    finally: (base/'startup-second-link').unlink()

    os.link(lock, base/'second-link')
    try: refused(base)
    finally: (base/'second-link').unlink()
    broad = private_directory(work/'broad-startup')
    descriptor = win32security.ConvertStringSecurityDescriptorToSecurityDescriptor(
        'D:P(A;OICI;FA;;;WD)', win32security.SDDL_REVISION_1)
    win32security.SetFileSecurity(str(broad), win32security.DACL_SECURITY_INFORMATION, descriptor)
    before = win32security.GetFileSecurity(str(broad), win32security.DACL_SECURITY_INFORMATION)
    refused(broad)
    after = win32security.GetFileSecurity(str(broad), win32security.DACL_SECURITY_INFORMATION)
    stringify = lambda sd:win32security.ConvertSecurityDescriptorToStringSecurityDescriptor(
        sd, win32security.SDDL_REVISION_1, win32security.DACL_SECURITY_INFORMATION)
    assert stringify(before) == stringify(after)
    assert not (broad/'run').exists(), 'Startup changed a rejected private directory.'

    import _winapi
    target = private_directory(work/'junction-target')
    link = work/'junction-startup'
    _winapi.CreateJunction(str(target), str(link))
    try:
        refused(link)
        assert not (target/'run').exists(), 'Rejected junction startup changed its target.'
    finally: os.rmdir(link)

    return {'beforePythonLoad':True, 'exclusiveByteLock':True, 'installerNoSharingGate':True,
        'hardLinkRefused':True, 'broadAclPreserved':True, 'junctionRefused':True, 'desktopAndBrowser':True,
        'startupWriterBeforePythonLoad':True, 'startupHardLinkRefused':True}


def assert_held(runtime):
    """Called while the actual desktop is ready, not against a fixture process."""
    import pywintypes
    import win32con
    import win32file
    from platform_adapters import locks
    from platform_adapters.windows_identity import private_lock_descriptor
    path = Path(runtime)/'installation.lock'
    fd = private_lock_descriptor(path)
    try:
        try: locks.flock(fd, locks.LOCK_EX|locks.LOCK_NB)
        except BlockingIOError: pass
        else: raise AssertionError('The running native application released its lifetime lease.')
    finally: os.close(fd)
    try:
        handle = win32file.CreateFile(str(path), win32con.GENERIC_READ|win32con.GENERIC_WRITE,
            0, None, win32con.OPEN_EXISTING, 0, None)
    except pywintypes.error as error:
        assert error.winerror == 32, error
    else:
        handle.Close()
        raise AssertionError('Installer file sharing did not exclude a running native application.')


def assert_startup_ready(runtime):
    """A discovered native component must no longer retain a startup reader."""
    import time
    from lifecycle.windows_startup import Startup
    deadline = time.monotonic()+5
    while True:
        try:
            with Startup(runtime, maintenance=True): return
        except OSError as error:
            if error.winerror != 32 or time.monotonic() >= deadline: raise
            time.sleep(.02)


def main():
    """Fast compiled qualification with disposable embedded-Python entrypoints."""
    import argparse
    import importlib.util
    import json
    import tempfile
    import time
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--arch', choices=('x64','arm64'), required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != 'win32': parser.error('Native Windows is required.')
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root/'services'))
    from platform_adapters.windows_identity import private_directory
    runtime = args.runtime.resolve()
    if (runtime/'release.json').exists() or (runtime/'scripts').exists():
        parser.error('Use a fresh disposable bootstrap runtime, never an assembled application.')
    work = private_directory(Path(tempfile.mkdtemp(prefix='augmentor-early-lease-')).resolve()/'private')
    args.out.mkdir(parents=True, exist_ok=True)
    (runtime/'release.json').write_text(json.dumps({'version':'0.0.0',
        'customerDistribution':False, 'qualificationStatus':'development-candidate'}), encoding='utf-8')
    (runtime/'scripts').mkdir()
    fixture = """import pathlib,sys,time
sys.path.insert(0, REPLACE_SERVICES)
from lifecycle.windows_startup import native_ready
root=pathlib.Path(sys.argv[2])
(root/'ready').write_text('ready')
while not (root/'publish').exists(): time.sleep(.02)
assert native_ready()
assert native_ready()  # Repeated readiness cannot touch the lifetime lease.
(root/'published').write_text('ready')
while not (root/'release').exists(): time.sleep(.02)
""".replace('REPLACE_SERVICES', repr(str(root/'services')))
    for script in ('launch-windows.py','launch-windows-browser.py'):
        (runtime/'scripts'/script).write_text(fixture, encoding='utf-8')
    spec = importlib.util.spec_from_file_location('native_launcher_builder', root/'scripts/build-windows-launcher.py')
    builder = importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)
    for name in ('Augmentor.exe','AugmentorBrowserHost.exe'):builder.build_launcher(runtime,args.arch,name=name)
    report = prove(runtime, work)
    for name in ('Augmentor.exe','AugmentorBrowserHost.exe'):
        state = private_directory(work/name)
        child = subprocess.Popen([str(runtime/name),'--qualification-root',str(state)],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            deadline = time.monotonic()+10
            while not (state/'ready').exists() and child.poll() is None and time.monotonic()<deadline:time.sleep(.05)
            assert (state/'ready').exists(), (name,child.poll())
            assert_held(state/'run')
            from lifecycle.windows_startup import Startup
            try:
                with Startup(state/'run', maintenance=True): pass
            except OSError as error: assert error.winerror == 32, error
            else: raise AssertionError('Native startup was released before publishing controls.')
            (state/'publish').write_text('publish', encoding='utf-8')
            while not (state/'published').exists() and child.poll() is None and time.monotonic()<deadline:time.sleep(.02)
            assert (state/'published').exists(), (name,child.poll())
            assert_startup_ready(state/'run')
            assert_held(state/'run')
            (state/'release').write_text('release', encoding='utf-8')
            assert child.wait(timeout=10)==0
            from platform_adapters import locks
            from platform_adapters.windows_identity import private_lock_descriptor
            fd=private_lock_descriptor(state/'run/installation.lock')
            try:locks.flock(fd,locks.LOCK_EX|locks.LOCK_NB)
            finally:os.close(fd)
        finally:
            if child.poll() is None:child.kill()
            child.communicate(timeout=10)
    report.update(arch=args.arch,compiled=True,normalExitReleasesLease=True,
        nativeReadinessReleasesOnlyStartup=True,
        scope='Actual native launcher and private Python with disposable entrypoints; not complete desktop or installer evidence.')
    (args.out/'native-startup-lease.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':main()
