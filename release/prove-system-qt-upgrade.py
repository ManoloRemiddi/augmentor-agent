#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Distinct native package-release upgrade/rollback in explicit offline fixtures.

Uses real Desktop/Node leases and preserves the synthetic user's runtime receipt
and files. Product version, DSH history, graphical login and power loss are separate.
"""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode=True
APP=Path('/usr/lib/augmentor')
HOME=Path('/home/augmentor-package-proof')
MARKERS={
    'Owned Augmentor arch complete package fixture; synthetic users only; no host devices or mounts\n':
        ('arch20261001-x86_64','pacman','/usr/bin/python3'),
    'Owned Augmentor leap complete package fixture; synthetic users only; no host devices or mounts\n':
        ('opensuse-leap16.0-x86_64','rpm','/usr/bin/python3.13'),
}


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('before','after','guard','out'):parser.add_argument('--'+name,type=Path,required=True)
    for name in ('before','after'):parser.add_argument('--'+name+'-sha256',required=True)
    args=parser.parse_args()
    if os.geteuid()!=0 or not Path('/.dockerenv').exists():raise ValueError('Use the explicit disposable Docker fixture only.')
    marker=Path('/etc/augmentor-full-package-fixture').read_text()
    if marker not in MARKERS or args.out.exists() or args.out.is_symlink():raise ValueError('Unknown fixture or existing evidence.')
    target,manager,bootstrap=MARKERS[marker]
    for path,expected in [(args.before,args.before_sha256),(args.after,args.after_sha256)]:
        if path.is_symlink() or sha(path)!=expected:raise ValueError('Require both exact streaming-inspected artifacts.')
    if args.before_sha256==args.after_sha256:raise ValueError('Upgrade needs distinct artifacts.')
    if any(row.split()[1]=='00000000' for row in Path('/proc/net/route').read_text().splitlines()[1:]):
        raise ValueError('Disconnect this owned fixture before the lifecycle proof.')
    spec=importlib.util.spec_from_file_location('independent_upgrade_guard',args.guard)
    guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
    if guard.host(target)!=manager:raise ValueError('Explicit fixture target differs.')
    args.out.mkdir(mode=0o700)
    env={**os.environ,'LC_ALL':'C','PYTHONDONTWRITEBYTECODE':'1'}
    outcomes={}

    def settled():
        for path in (guard.STATE/'pending.json',guard.RUN/'augmentor-runtime.pending',guard.RUN/'augmentor-desktop.pending'):
            assert not path.exists() and not path.is_symlink(),str(path)

    def transaction(name,command,refusal=False):
        result=subprocess.run([str(value) for value in command],env=env,text=True,capture_output=True,timeout=180)
        for suffix,content in [('stdout',result.stdout),('stderr',result.stderr)]:
            (args.out/(name+'.'+suffix)).write_text(content)
        if refusal:
            assert result.returncode!=0 and 'Augmentor is still open' in result.stdout+result.stderr,name
        else:assert result.returncode==0,name+' failed; preserve and inspect logs.'
        outcomes[name]={'exitCode':result.returncode,'stdoutSha256':sha(args.out/(name+'.stdout')),
                        'stderrSha256':sha(args.out/(name+'.stderr'))}

    def native(path,rollback=False):
        if manager=='pacman':return ['pacman','-U','--noconfirm',path]
        return ['rpm','-Uvh','--replacepkgs',*(['--oldpackage'] if rollback else []),path]

    initial=guard.receipt(target,manager);settled()
    initial_receipt=(APP/'linux-package.json').read_bytes()
    initial_release=(APP/'release.json').read_bytes()
    policy=json.loads((APP/'linux-python-runtime.json').read_text())
    runtime_store=HOME/'.local/share/augmentor/python-runtimes'
    selected=next(runtime_store.glob(policy['profile']+'-*'))
    saved={path.name:path.read_bytes() for path in selected.iterdir() if path.is_file() and path.name.endswith('.json')}
    assert saved,'Synthetic immutable runtime receipt is required.'
    sentinel=HOME/'package-upgrade-sentinel.txt'
    if sentinel.exists() or sentinel.is_symlink():raise ValueError('Preserve the prior synthetic sentinel.')
    sentinel.write_text('Owned distinct package-release upgrade fixture. Preserve this file.\n');os.chown(sentinel,1002,1002)
    sentinel_sha=sha(sentinel)
    common=['runuser','-u','augmentor-package-proof','--','env','QT_QPA_PLATFORM=offscreen','PYTHONDONTWRITEBYTECODE=1']

    def preserve_user():
        assert sha(sentinel)==sentinel_sha
        assert {path.name:path.read_bytes() for path in selected.iterdir() if path.is_file() and path.name.endswith('.json')}==saved

    def busy_checks(phase,command):
        expected=guard.receipt(target,manager)
        receipt=(APP/'linux-package.json').read_bytes();release=(APP/'release.json').read_bytes()
        for component in ('runtime','desktop'):
            launch=([bootstrap,'-B',APP/'scripts/run-component.py','runtime',APP/'node/bin/node','-e','setInterval(()=>{},1000)']
                    if component=='runtime' else ['augmentor-agent','--preview'])
            with (args.out/(phase+'-'+component+'-live.stdout')).open('w') as stdout,(args.out/(phase+'-'+component+'-live.stderr')).open('w') as stderr:
                child=subprocess.Popen([str(value) for value in common+launch],env=env,stdout=stdout,stderr=stderr,start_new_session=True)
                try:
                    deadline=time.monotonic()+30
                    while True:
                        assert child.poll() is None,'Real leased component stopped.'
                        with (guard.RUN/('augmentor-'+component+'.lock')).open('r') as lock:
                            try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                            except BlockingIOError:break
                        if time.monotonic()>deadline:raise RuntimeError('Real component lease missing.')
                        time.sleep(.1)
                    transaction(phase+'-'+component+'-busy',command,True)
                    assert guard.receipt(target,manager)==expected
                    assert (APP/'linux-package.json').read_bytes()==receipt and (APP/'release.json').read_bytes()==release
                    assert child.poll() is None;settled();preserve_user()
                finally:
                    if child.poll() is None:os.killpg(child.pid,signal.SIGTERM);child.wait(timeout=15)

    audit=['pacman','-Qkk','augmentor-agent'] if manager=='pacman' else ['rpm','-V','augmentor-agent']
    busy_checks('upgrade',native(args.after))
    transaction('idle-upgrade',native(args.after))
    upgraded=guard.receipt(target,manager);settled();preserve_user()
    assert upgraded['package']!=initial['package'] and upgraded['source']!=initial['source']
    assert upgraded['version']==initial['version'],'This probe qualifies package-release changes only.'
    transaction('upgrade-native-audit',audit)
    transaction('upgrade-cold-render',common+['augmentor-agent','--preview','--screenshot',HOME/'upgrade-window.png'])
    busy_checks('rollback',native(args.before,True))
    transaction('idle-rollback',native(args.before,True))
    assert guard.receipt(target,manager)==initial
    assert (APP/'linux-package.json').read_bytes()==initial_receipt and (APP/'release.json').read_bytes()==initial_release
    settled();preserve_user()
    transaction('rollback-native-audit',audit)
    transaction('rollback-cold-render',common+['augmentor-agent','--preview','--screenshot',HOME/'rollback-window.png'])
    report={'format':'augmentor-system-qt-package-release-upgrade-proof/1','target':target,
            'before':{'package':initial['package'],'source':initial['source'],'artifactSha256':args.before_sha256},
            'after':{'package':upgraded['package'],'source':upgraded['source'],'artifactSha256':args.after_sha256},
            'proofSha256':sha(__file__),'independentGuardSha256':sha(args.guard),'outcomes':outcomes,
            'offline':True,'realNativeAndNodeLeases':True,'pendingAbsent':True,'completeAppInventoryPassed':True,
            'nativePackageAuditPassed':True,'syntheticUserSentinelPreserved':True,'immutableRuntimeReceiptsPreserved':True,
            'originalPackageRestored':True,'packageReleaseUpgradeTested':True,'packageReleaseRollbackTested':True,
            'productVersionUpgradeTested':False,'dshHistoryTested':False,'completeInstallerTested':False,
            'realDesktopSessionTested':False,'graphicalBrowserTested':False,'physicalAudioTested':False,
            'ownerStateChanged':False,'publicReleaseQualified':False}
    (args.out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'target':target,'passed':True}))


if __name__=='__main__':main()
