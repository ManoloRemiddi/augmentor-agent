#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Exercise real ALPM hooks using explicitly synthetic payloads in an owned container.

Requires the exact disposable container marker. This is package-mechanism
qualification, not application, desktop, Browser or public-release acceptance.
"""
import argparse
from contextlib import contextmanager
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pwd
import re
import subprocess
import sys

TARGET='arch20261001-x86_64'
MARKER='Owned Arch 20261001 Augmentor package guard synthetic qualification\n'
ROOT=Path('/tmp/augmentor-arch-package-proof')
APP=Path('/usr/lib/augmentor')
PENDING=Path('/var/lib/augmentor-package-maintenance/pending.json')
GUARD=Path('/usr/lib/augmentor-package-guard/lifecycle.py')
USER_HOME=Path('/tmp/augmentor-proof')


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def command(argv,expected=0):
    result=subprocess.run(argv,text=True,capture_output=True,timeout=120,
                          env={**os.environ,'LC_ALL':'C','HOME':str(USER_HOME)})
    print(json.dumps({'command':argv,'returncode':result.returncode}),flush=True)
    print(result.stdout,end='',flush=True);print(result.stderr,end='',file=sys.stderr,flush=True)
    if expected is not None and result.returncode!=expected:
        raise RuntimeError('Unexpected command result; preserve fixture and inspect before retrying.')
    return result


def snapshot():
    return {'package':command(['pacman','-Q','augmentor-agent']).stdout.strip(),
            'files':{str(p.relative_to(APP)):digest(p) for p in sorted(APP.rglob('*')) if p.is_file()},
            'desktop':Path('/usr/share/augmentor/desktop-version').read_text()}


def finalized():
    assert not PENDING.exists()
    assert all(not Path('/run/augmentor/augmentor-'+c+'.pending').exists() for c in ('runtime','desktop'))


def build(release,source):
    directory=ROOT/('payload-'+str(release));directory.mkdir()
    payload=directory/'payload';payload.mkdir()
    provenance={'commit':source,'dirty':False}
    (payload/'release.json').write_text(json.dumps({'version':'0.2.13','target':TARGET,'source':provenance,
          'qualificationScope':'synthetic package hooks only; not an Augmentor application artifact'})+'\n')
    (payload/'synthetic.txt').write_text('Synthetic ALPM lifecycle test payload '+str(release)+'\n')
    receipt={'format':'augmentor-linux-package-receipt/1','target':TARGET,'manager':'pacman',
             'version':'0.2.13','source':provenance,'completeInventory':True,
             'package':{'name':'augmentor-agent','versionRelease':'0.2.13-'+str(release),'architecture':'x86_64'},
             'files':{p.name:digest(p) for p in sorted(payload.iterdir())}}
    (payload/'linux-package.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (directory/'PKGBUILD').write_text("""# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
pkgname=augmentor-agent
pkgver=0.2.13
pkgrel="""+str(release)+"""
pkgdesc='Explicitly synthetic Augmentor ALPM transaction test; no application'
arch=('x86_64')
license=('custom:test-fixture')
depends=('augmentor-package-guard')
options=('!strip')
package() {
  install -d "$pkgdir/usr/lib/augmentor" "$pkgdir/usr/share/augmentor"
  install -m644 "$startdir/payload/"* "$pkgdir/usr/lib/augmentor/"
  printf '%s\\n' '0.2.13' > "$pkgdir/usr/share/augmentor/desktop-version"
}
""")
    for p in [directory,payload,*directory.rglob('*')]:os.chown(p,1000,1000)
    command(['runuser','-u','proof','--','sh','-c','cd '+str(directory)+' && makepkg --cleanbuild --noconfirm'])
    archive=directory/('augmentor-agent-0.2.13-'+str(release)+'-x86_64.pkg.tar.zst')
    assert archive.is_file();return archive


@contextmanager
def shared_lease(component,uid):
    code="import fcntl,os,sys; os.setgid(int(sys.argv[2])); os.setuid(int(sys.argv[2])); f=open('/run/augmentor/augmentor-'+sys.argv[1]+'.lock','rb'); fcntl.flock(f,fcntl.LOCK_SH); print('READY',flush=True); sys.stdin.read()"
    child=subprocess.Popen(['/usr/bin/python3','-I','-c',code,component,str(uid)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
    try:
        assert child.stdout.readline().strip()=='READY'
        assert Path('/proc',str(child.pid),'status').read_text().split('Uid:')[1].splitlines()[0].split()==[str(uid)]*4
        yield child.pid
    finally:
        child.communicate('',timeout=10);assert child.returncode==0


def hook(name,when,execute,abort=False):
    path=Path('/etc/pacman.d/hooks')/name;path.parent.mkdir(parents=True,exist_ok=True)
    assert not path.exists()
    path.write_text('[Trigger]\nOperation = Upgrade\nType = Package\nTarget = augmentor-agent\n\n[Action]\nWhen = '+when+'\nExec = '+execute+'\n'+('AbortOnFail\n' if abort else ''))
    return path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--guard-package',type=Path,required=True)
    parser.add_argument('--guard-sha256',required=True)
    parser.add_argument('--source-ref',required=True)
    parser.add_argument('--lease-source',type=Path,required=True)
    args=parser.parse_args()
    assert os.geteuid()==0 and Path('/.dockerenv').is_file()
    assert Path('/etc/augmentor-package-test-container').read_text()==MARKER
    assert 'ID=arch' in Path('/etc/os-release').read_text()
    assert os.uname().nodename=='5ea9e6eb7b6e'
    assert pwd.getpwnam('proof').pw_uid==1000 and USER_HOME.is_dir()
    assert re.fullmatch('[a-f0-9]{40}',args.source_ref)
    assert not APP.exists() and not PENDING.exists() and not ROOT.exists()
    assert args.guard_package.resolve().is_relative_to(Path('/tmp/arch-package-guard-build-v2'))
    assert args.lease_source.resolve().is_relative_to(Path('/tmp'))
    assert len(args.lease_source.resolve().parents)>=3
    ROOT.mkdir(mode=0o755)
    command(['pacman','-U','--noconfirm',str(args.guard_package)])
    assert digest(GUARD)==args.guard_sha256
    guard_identity=command(['pacman','-Q','augmentor-package-guard']).stdout.strip()
    a=build(1,args.source_ref);b=build(2,args.source_ref)
    command(['pacman','-U','--noconfirm',str(a)]);finalized();first=snapshot()
    command(['pacman','-U','--noconfirm',str(a)]);finalized();assert snapshot()==first
    refusals=[]
    for component,uid in [('runtime',1000),('desktop',1001)]:
        for operation in ('upgrade','remove'):
            with shared_lease(component,uid):
                result=command(['pacman','-U','--noconfirm',str(b)] if operation=='upgrade' else ['pacman','-R','--noconfirm','augmentor-agent'],expected=None)
                assert result.returncode!=0 and 'Augmentor is still open' in result.stdout+result.stderr
                finalized();assert snapshot()==first
                refusals.append({'component':component,'uid':uid,'operation':operation,'refused':True,'payloadUnchanged':True})
    with shared_lease('runtime',1000),shared_lease('desktop',1001):
        result=command(['pacman','-U','--noconfirm',str(b)],expected=None)
        assert result.returncode!=0;finalized();assert snapshot()==first
    result=command(['pacman','-Rdd','--noconfirm','augmentor-package-guard'],expected=None)
    assert result.returncode!=0 and 'own completed transaction' in result.stdout+result.stderr
    assert command(['pacman','-Q','augmentor-package-guard']).stdout.strip()==guard_identity
    later=hook('zz-augmentor-fixture-abort.hook','PreTransaction','/usr/bin/false',True)
    result=command(['pacman','-U','--noconfirm',str(b)],expected=None)
    assert result.returncode!=0 and PENDING.exists() and snapshot()==first
    old_intent=json.loads(PENDING.read_text())
    assert old_intent['oldReceiptSha256']==digest(APP/'linux-package.json')
    # Simulate loss of volatile mirrors, explicitly not a real container reboot.
    for c in ('runtime','desktop'):Path('/run/augmentor/augmentor-'+c+'.pending').unlink()
    spec=importlib.util.spec_from_file_location('actual_lease',args.lease_source)
    lease=importlib.util.module_from_spec(spec);spec.loader.exec_module(lease);lease.ROOT=APP
    try:lease.hold('runtime')
    except RuntimeError:pass
    else:raise AssertionError('Durable record did not fence startup after lost mirrors.')
    command(['/usr/bin/python3','-I',str(GUARD),'recover-unchanged','--target',TARGET]);finalized()
    later.unlink()
    command(['pacman','-U','--noconfirm',str(b)]);finalized();second=snapshot()
    assert second['package']=='augmentor-agent 0.2.13-2' and second!=first
    command(['pacman','-U','--noconfirm',str(a)]);finalized();assert snapshot()==first
    # Controlled synthetic inventory corruption before the real finalizer.
    failure=hook('aa-augmentor-fixture-inventory.hook','PostTransaction','/usr/bin/touch /usr/lib/augmentor/synthetic-extra')
    result=command(['pacman','-U','--noconfirm',str(b)],expected=None)
    assert command(['pacman','-Q','augmentor-agent']).stdout.strip()=='augmentor-agent 0.2.13-2'
    assert PENDING.exists() and (APP/'synthetic-extra').exists()
    refused=command(['/usr/bin/python3','-I',str(GUARD),'complete','--target',TARGET],expected=None)
    assert refused.returncode!=0 and 'complete receipt inventory' in refused.stderr
    old_refused=command(['/usr/bin/python3','-I',str(GUARD),'recover-unchanged','--target',TARGET],expected=None)
    assert old_refused.returncode!=0 and PENDING.exists()
    # Remove only the exact empty synthetic injected file. No selected product
    # release is installed or edited by this fixture.
    assert (APP/'synthetic-extra').is_file() and (APP/'synthetic-extra').stat().st_size==0
    (APP/'synthetic-extra').unlink();failure.unlink()
    command(['/usr/bin/python3','-I',str(GUARD),'complete','--target',TARGET]);finalized();assert snapshot()==second
    command(['pacman','-R','--noconfirm','augmentor-agent']);finalized();assert not APP.exists()
    assert GUARD.is_file()
    command(['pacman','-R','--noconfirm','augmentor-package-guard']);assert not GUARD.exists()
    report={'format':'augmentor-arch-real-alpm-synthetic-payload-proof/1','target':TARGET,
        'source':{'commit':args.source_ref,'dirty':False},'proofSha256':digest(Path(__file__)),
        'guardSha256':args.guard_sha256,'guardPackageSha256':digest(args.guard_package),'guardIdentity':guard_identity,
        'syntheticPayloadArchives':{p.name:digest(p) for p in (a,b)},
        'separateGuardBootstrapTested':True,'firstInstallTested':True,'reinstallTested':True,
        'activeLeaseRefusals':refusals,'jointMultiuserLeaseRefusalTested':True,
        'guardRemovalRefusedWhileAppRegistered':True,'laterPreHookAbortRetainedDurableIntent':True,
        'lostVolatileMirrorsSimulationStartupRefused':True,'verifiedUnchangedOldRecoveryTested':True,
        'upgradeTested':True,'downgradeTested':True,'inventoryFailureRetainedDurableIntent':True,
        'inventoryFailurePacmanExitCode':result.returncode,'unverifiedNewStateRefused':True,
        'verifiedSyntheticInjectionRemovalAndCompletionTested':True,'applicationRemovalTested':True,
        'separateGuardRemovalTested':True,'realPackageManagerUsed':'pacman/libalpm',
        'locallyBuiltPackagesUnsigned':True,'payloadScope':'synthetic receipts and text only; no application',
        'fullApplicationPayloadTested':False,'realMultiuserApplicationTested':False,'realInterruptedRebootTested':False,
        'realDesktopTested':False,'browserTested':False,'physicalAudioTested':False,'publicReleaseQualified':False,
        'ownerStateChanged':False}
    (ROOT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
