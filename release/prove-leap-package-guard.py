#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Exercise Leap RPM scriptlets with synthetic payloads in the exact owned container.

No application is installed. Local RPMs are unsigned; official build dependencies
retain their normal repository signature checks. Full product acceptance is separate.
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

TARGET='opensuse-leap16.0-x86_64'
ROOT=Path('/tmp/augmentor-leap-package-proof')
APP=Path('/usr/lib/augmentor')
PENDING=Path('/var/lib/augmentor-package-maintenance/pending.json')
PYTHON='/usr/bin/python3.13'


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def run(argv,expected=0):
    result=subprocess.run(argv,text=True,capture_output=True,timeout=120,
                          env={**os.environ,'LC_ALL':'C','HOME':'/tmp/augmentor-proof'})
    print(json.dumps({'command':argv,'returncode':result.returncode}),flush=True)
    print(result.stdout,end='',flush=True);print(result.stderr,end='',file=sys.stderr,flush=True)
    if expected is not None and result.returncode!=expected:raise RuntimeError('Unexpected result; preserve the fixture and inspect before retrying.')
    return result


def snapshot():
    return {'package':run(['rpm','-q','--qf','%{NAME} %{VERSION}-%{RELEASE} %{ARCH}','augmentor-agent']).stdout,
            'files':{str(p.relative_to(APP)):digest(p) for p in sorted(APP.rglob('*')) if p.is_file()},
            'desktop':Path('/usr/share/augmentor/desktop-version').read_text()}


def finalized():
    assert not PENDING.exists()
    assert all(not Path('/run/augmentor/augmentor-'+c+'.pending').exists() for c in ('runtime','desktop'))


@contextmanager
def shared(component,uid):
    code="import fcntl,os,sys; os.setgid(int(sys.argv[2])); os.setuid(int(sys.argv[2])); f=open('/run/augmentor/augmentor-'+sys.argv[1]+'.lock','rb'); fcntl.flock(f,fcntl.LOCK_SH); print('READY',flush=True); sys.stdin.read()"
    child=subprocess.Popen([PYTHON,'-I','-c',code,component,str(uid)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
    try:
        assert child.stdout.readline().strip()=='READY'
        assert Path('/proc',str(child.pid),'status').read_text().split('Uid:')[1].splitlines()[0].split()==[str(uid)]*4
        yield
    finally:child.communicate('',timeout=10);assert child.returncode==0


def build(release,source,guard,fail=None):
    directory=ROOT/('payload-'+str(release)+('-'+fail if fail else ''));directory.mkdir()
    for name in ('SPECS','BUILD','BUILDROOT','RPMS','SOURCES','SRPMS'):(directory/name).mkdir()
    payload=directory/'payload';payload.mkdir()
    provenance={'commit':source,'dirty':False};version_release='0.2.13-'+str(release)+'.leap16'
    (payload/'release.json').write_text(json.dumps({'version':'0.2.13','target':TARGET,'source':provenance,
        'qualificationScope':'synthetic RPM scriptlets only; not an Augmentor application artifact'})+'\n')
    (payload/'synthetic.txt').write_text('Synthetic RPM lifecycle test payload '+str(release)+'\n')
    package={'name':'augmentor-agent','versionRelease':version_release,'architecture':'x86_64'}
    (payload/'linux-package.json').write_text(json.dumps({'format':'augmentor-linux-package-receipt/1',
        'target':TARGET,'manager':'rpm','version':'0.2.13','source':provenance,'package':package,
        'completeInventory':True,'files':{p.name:digest(p) for p in sorted(payload.iterdir())}},indent=2)+'\n')
    # Embed trusted standalone source in each phase; final removal needs no app files.
    # RPM expands spec macros inside scriptlets too. Preserve the guard's
    # literal %{NAME}/%{VERSION}/%{RELEASE}/%{ARCH} query format at runtime.
    body=guard.read_text().rsplit("\nif __name__=='__main__':",1)[0].replace('%','%%')+'\n'
    pre=body+"print(json.dumps(begin("+repr(TARGET)+",'upgrade',"+repr(package)+")))\n"
    if fail=='pre':pre+="raise RuntimeError('Deliberate synthetic failure after durable preflight')\n"
    post=body+("(APP/'synthetic-extra').touch()\n" if fail=='post' else '')+"print(json.dumps(complete("+repr(TARGET)+")))\n"
    remove=body+"if sys.argv[1]=='0': print(json.dumps(begin("+repr(TARGET)+",'remove')))\n"
    after=body+"if sys.argv[1]=='0': print(json.dumps(complete("+repr(TARGET)+")))\n"
    # sys is needed only to inspect RPM's ordinary final-removal argument.
    remove='import sys\n'+remove;after='import sys\n'+after
    spec=directory/'SPECS/augmentor-agent.spec'
    spec.write_text('''# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
%global debug_package %{nil}
%global __os_install_post %{nil}
Name: augmentor-agent
Version: 0.2.13
Release: '''+str(release)+'''.leap16
Summary: Explicitly synthetic Augmentor RPM transaction proof
License: LicenseRef-Augmentor-MIT-Resale-1.0
BuildArch: x86_64
AutoReqProv: no
Requires: /usr/bin/python3.13
Requires(pre): /usr/bin/python3.13
Requires(preun): /usr/bin/python3.13
Requires(posttrans): /usr/bin/python3.13
Requires(postuntrans): /usr/bin/python3.13
%description
Synthetic receipts and text only. No application or public release.
%prep
%build
%install
mkdir -p %{buildroot}/usr/lib/augmentor %{buildroot}/usr/share/augmentor
cp -a '''+str(payload)+'''/. %{buildroot}/usr/lib/augmentor/
printf '%s\\n' '0.2.13' > %{buildroot}/usr/share/augmentor/desktop-version
%pre -p /usr/bin/python3.13
'''+pre+'''%posttrans -p /usr/bin/python3.13
'''+post+'''%preun -p /usr/bin/python3.13
'''+remove+'''%postuntrans -p /usr/bin/python3.13
'''+after+'''%files
/usr/lib/augmentor
/usr/share/augmentor/desktop-version
''')
    for p in [directory,*directory.rglob('*')]:os.chown(p,1000,1000)
    run(['runuser','-u','proof','--','rpmbuild','-bb','--define','_topdir '+str(directory),str(spec)])
    archive=directory/'RPMS/x86_64'/('augmentor-agent-'+version_release+'.x86_64.rpm')
    assert archive.is_file();return archive


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-ref',required=True)
    parser.add_argument('--guard-source',type=Path,required=True)
    parser.add_argument('--guard-sha256',required=True)
    parser.add_argument('--lease-source',type=Path,required=True)
    args=parser.parse_args()
    assert os.geteuid()==0 and Path('/.dockerenv').is_file()
    assert Path('/etc/augmentor-package-test-container').read_text()=='Owned Leap 16 Augmentor RPM synthetic qualification\n'
    fields=dict(row.split('=',1) for row in Path('/etc/os-release').read_text().splitlines() if '=' in row)
    assert fields['ID'].strip('"')=='opensuse-leap' and fields['VERSION_ID'].strip('"')=='16.0'
    assert os.uname().nodename=='e71c50cb883e' and pwd.getpwnam('proof').pw_uid==1000
    assert re.fullmatch('[a-f0-9]{40}',args.source_ref)
    assert not ROOT.exists() and not APP.exists() and not PENDING.exists()
    assert args.guard_source.resolve().is_relative_to(Path('/tmp')) and digest(args.guard_source)==args.guard_sha256
    assert args.lease_source.resolve().is_relative_to(Path('/tmp')) and len(args.lease_source.resolve().parents)>=3
    ROOT.mkdir(mode=0o755)
    guard=ROOT/'guard.py';guard.write_bytes(args.guard_source.read_bytes())
    a=build(1,args.source_ref,guard);b=build(2,args.source_ref,guard)
    pre=build(2,args.source_ref,guard,'pre');post=build(3,args.source_ref,guard,'post')
    run(['rpm','-Uvh',str(a)]);finalized();first=snapshot()
    run(['rpm','-Uvh','--replacepkgs',str(a)]);finalized();assert snapshot()==first
    refusals=[]
    for component,uid in [('runtime',1000),('desktop',1001)]:
        for operation in ('upgrade','remove'):
            with shared(component,uid):
                result=run(['rpm','-Uvh',str(b)] if operation=='upgrade' else ['rpm','-e','augmentor-agent'],None)
                assert result.returncode!=0 and 'Augmentor is still open' in result.stdout+result.stderr
                finalized();assert snapshot()==first
                refusals.append({'component':component,'uid':uid,'operation':operation,'refused':True,'payloadUnchanged':True})
    with shared('runtime',1000),shared('desktop',1001):
        result=run(['rpm','-Uvh',str(b)],None);assert result.returncode!=0;finalized();assert snapshot()==first
    result=run(['rpm','-Uvh',str(pre)],None)
    assert result.returncode!=0 and PENDING.exists() and snapshot()==first
    record=json.loads(PENDING.read_text());assert record['oldReceiptSha256']==digest(APP/'linux-package.json')
    for c in ('runtime','desktop'):Path('/run/augmentor/augmentor-'+c+'.pending').unlink()
    module=importlib.util.spec_from_file_location('actual_leap_lease',args.lease_source)
    lease=importlib.util.module_from_spec(module);module.loader.exec_module(lease);lease.ROOT=APP
    try:lease.hold('runtime')
    except RuntimeError:pass
    else:raise AssertionError('Persistent intent did not fence startup.')
    run([PYTHON,'-I',str(guard),'recover-unchanged','--target',TARGET]);finalized()
    run(['rpm','-Uvh',str(b)]);finalized();second=snapshot();assert second!=first
    run(['rpm','-Uvh','--oldpackage',str(a)]);finalized();assert snapshot()==first
    result=run(['zypper','--non-interactive','--no-refresh','install','--no-recommends','--allow-unsigned-rpm',str(post)],None)
    assert PENDING.exists() and (APP/'synthetic-extra').exists()
    assert '0.2.13-3.leap16' in snapshot()['package']
    zypper_code=result.returncode
    result=run([PYTHON,'-I',str(guard),'complete','--target',TARGET],None)
    assert result.returncode!=0 and 'complete receipt inventory' in result.stderr
    result=run([PYTHON,'-I',str(guard),'recover-unchanged','--target',TARGET],None);assert result.returncode!=0
    assert (APP/'synthetic-extra').is_file() and (APP/'synthetic-extra').stat().st_size==0
    (APP/'synthetic-extra').unlink()
    run([PYTHON,'-I',str(guard),'complete','--target',TARGET]);finalized()
    run(['rpm','-e','augmentor-agent']);finalized();assert not APP.exists()
    report={'format':'augmentor-leap-real-rpm-synthetic-payload-proof/1','target':TARGET,
        'source':{'commit':args.source_ref,'dirty':False},'proofSha256':digest(Path(__file__)),
        'guardSha256':digest(guard),'syntheticPayloadArchives':{str(p.relative_to(ROOT)):digest(p) for p in (a,b,pre,post)},
        'packageManagerVersions':run(['rpm','-q','rpm','zypper']).stdout.splitlines(),
        'firstInstallTested':True,'reinstallTested':True,'activeLeaseRefusals':refusals,
        'jointMultiuserLeaseRefusalTested':True,'preScriptFailureRetainedDurableIntent':True,
        'lostVolatileMirrorsSimulationStartupRefused':True,'verifiedUnchangedOldRecoveryTested':True,
        'upgradeTested':True,'downgradeTested':True,'posttransInventoryFailureRetainedDurableIntent':True,
        'zypperPosttransFailureExitCode':zypper_code,'unverifiedNewStateRefused':True,
        'verifiedSyntheticInjectionRemovalAndCompletionTested':True,'finalRemovalPostuntransTested':True,
        'locallyBuiltPackagesUnsigned':True,'payloadScope':'synthetic receipts and text only; no application',
        'fullApplicationPayloadTested':False,'realMultiuserApplicationTested':False,'realInterruptedRebootTested':False,
        'realDesktopTested':False,'browserTested':False,'physicalAudioTested':False,'publicReleaseQualified':False,
        'ownerStateChanged':False}
    (ROOT/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
