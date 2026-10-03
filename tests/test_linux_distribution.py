# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Package selection must never turn distro similarity into install authority."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]


def module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py')
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


distro=module('linux_distribution')
setup=module('setup-complete')


def manifest(target):
    version='0.2.13'
    if target==distro.ARCH:
        names=[f'augmentor-agent-{version}-1-x86_64.pkg.tar.zst']
    elif target==distro.LEAP:
        names=[f'augmentor-agent-{version}-1.leap16.x86_64.rpm']
    elif target.startswith('fedora'):
        release=target.split('-')[0].removeprefix('fedora')
        names=[f'augmentor-agent-{version}-1.fc{release}.x86_64.rpm']
    else:
        names=[f'augmentor-{kind}_{version}_amd64.deb' for kind in ('runtime','desktop')]
    value = {'format':'augmentor-complete/1','target':target,'version':version,'components':{},
            'packages':names,'sha256':{name:hashlib.sha256(b'fixture').hexdigest() for name in names}}
    if target==distro.NOBLE:
        value['pythonRuntime']={'format':'augmentor-linux-python-runtime-contract/1','target':target,
            'profile':'noble-cp312-x86_64-voice','pythonAbi':[3,12],'architecture':'x86_64',
            'policySha256':'a'*64,'lockIdentity':'b'*64}
    if target==distro.MINT:
        runtime=module('linux-python-runtime')
        policy=ROOT/'release/linuxmint22.3-python-source-qt-voice.json'
        value['pythonRuntime']=runtime.contract(runtime.policy(policy),runtime.digest(policy))
    if target in (distro.ARCH,distro.LEAP):
        value['nativePackage']={'name':'augmentor-agent','versionRelease':version+'-1'+('.leap16' if target==distro.LEAP else ''),'architecture':'x86_64'}
        runtime=module('linux-python-runtime')
        policy=ROOT/'release'/('arch20261001-python-voice.json' if target==distro.ARCH else 'opensuse-leap16.0-python-voice.json')
        value['pythonRuntime']=runtime.contract(runtime.policy(policy),runtime.digest(policy))
    if target==distro.ARCH:
        value['guardPackage']={'file':'augmentor-package-guard-0.2.13-2-any.pkg.tar.zst','name':'augmentor-package-guard','versionRelease':'0.2.13-2','architecture':'any'}
        value['sha256'][value['guardPackage']['file']]=hashlib.sha256(b'guard fixture').hexdigest()
    return value


class DistributionPlans(unittest.TestCase):
    def test_parse_quoted_release_fields_without_executing_them(self):
        result=distro.os_release('ID=ubuntu\nVERSION_ID="26.04"\nID_LIKE="debian"\nPRETTY_NAME="Ubuntu 26.04 LTS"\n# comment\n')
        self.assertEqual(distro.host_target(result,'x86_64'),'ubuntu26.04-amd64')
        self.assertEqual(distro.os_release('ID="$(touch /tmp/forbidden)"')['ID'],'$(touch /tmp/forbidden)')

    def test_supported_hosts_select_their_own_package_format(self):
        for target,(name,version,manager,_) in distro.TARGETS.items():
            value=distro.install_plan(manifest(target),'/bundle with spaces',info={'ID':name,'VERSION_ID':version},machine='x86_64')
            self.assertEqual(value['target'],target)
            if manager=='pacman':
                self.assertEqual(value['command'][:4],['sudo','pacman','-U','--noconfirm'])
                self.assertEqual(len(value['commands']),3)
                self.assertTrue(value['guardVerificationBeforeApplication'])
            elif manager=='zypper':
                self.assertEqual(value['command'][:5],['sudo','zypper','--non-interactive','install','--no-recommends'])
                self.assertEqual(value['bootstrapPython'],'/usr/bin/python3.13')
            else:self.assertEqual(value['command'][:4],['sudo',manager,'install','-y'])
            self.assertEqual(len(value['packages']),2 if manager=='apt' else 1)
            for name in value['packages']:self.assertIn('/bundle with spaces/'+name,value['command'])

    def test_derivatives_older_releases_and_other_architectures_fail_closed(self):
        for info in ({'ID':'linuxmint','VERSION_ID':'22.2','ID_LIKE':'ubuntu debian'},
                     {'ID':'ubuntu','VERSION_ID':'22.04'},{'ID':'debian','VERSION_ID':'12'},
                     {'ID':'unknown','VERSION_ID':'44','ID_LIKE':'fedora'}):
            with self.subTest(info=info),self.assertRaises(ValueError):distro.host_target(info,'x86_64')
        with self.assertRaisesRegex(ValueError,'separately qualified'):distro.host_target({'ID':'fedora','VERSION_ID':'44'},'aarch64')

    def test_wrong_bundle_target_is_refused_even_for_debian_related_hosts(self):
        with self.assertRaisesRegex(ValueError,'matching bundle'):
            distro.install_plan(manifest('debian13-amd64'),'/bundle',info={'ID':'ubuntu','VERSION_ID':'26.04'},machine='x86_64')

    def test_noble_contract_is_required_and_cannot_cross_targets(self):
        value=manifest(distro.NOBLE)
        for key,replacement in [('profile','noble-cp312-x86_64'),('target','ubuntu26.04-amd64'),
                                ('pythonAbi',[3,13]),('policySha256','unverified'),('architecture','aarch64')]:
            with self.subTest(key=key):
                broken={**value,'pythonRuntime':{**value['pythonRuntime'],key:replacement}}
                with self.assertRaises(ValueError):distro.python_runtime_contract(broken,distro.NOBLE)
        with self.assertRaises(ValueError):distro.python_runtime_contract({},distro.NOBLE)
        with self.assertRaises(ValueError):distro.python_runtime_contract(value,'debian13-amd64')

    def test_arch_and_leap_contract_cannot_borrow_another_abi_stack_or_license_claim(self):
        for target in (distro.ARCH,distro.LEAP):
            value=manifest(target)
            for key,replacement in [('target',distro.NOBLE),('profile','noble-cp312-x86_64-voice'),
                                    ('pythonAbi',[3,12]),('licenseReviewComplete',True),
                                    ('embeddedSourceCoverageComplete',True)]:
                broken={**value,'pythonRuntime':{**value['pythonRuntime'],key:replacement}}
                with self.subTest(target=target,key=key),self.assertRaises(ValueError):
                    distro.python_runtime_contract(broken,target)
            broken={**value,'pythonRuntime':{**value['pythonRuntime'],'systemQtStack':
                     {**value['pythonRuntime']['systemQtStack'],'qtVersion':'unqualified'}}}
            with self.assertRaises(ValueError):distro.python_runtime_contract(broken,target)

    def test_native_package_or_independent_guard_identity_cannot_be_omitted_or_mixed(self):
        for target in (distro.ARCH,distro.LEAP):
            value=manifest(target)
            for package in (None,{**value['nativePackage'],'architecture':'aarch64'},
                            {**value['nativePackage'],'versionRelease':'0.2.12-1'}):
                with self.subTest(target=target,package=package),self.assertRaises(ValueError):
                    distro.native_package_contract({**value,'nativePackage':package},target)
        value=manifest(distro.ARCH)
        for guard in (None,{**value['guardPackage'],'architecture':'x86_64'},
                      {**value['guardPackage'],'versionRelease':'0.2.13-1'}):
            with self.subTest(guard=guard),self.assertRaises(ValueError):
                distro.arch_guard_package({**value,'guardPackage':guard})
        broken={**value,'sha256':{name:sha for name,sha in value['sha256'].items() if name!=value['guardPackage']['file']}}
        with self.assertRaises(ValueError):distro.arch_guard_package(broken)

    def test_legacy_debian_bundle_without_explicit_package_list_is_supported(self):
        value=manifest('debian13-amd64');value.pop('packages')
        self.assertEqual(len(distro.package_files(value,'debian13-amd64')),2)

    def test_missing_mixed_unchecked_or_wrong_version_packages_are_refused(self):
        cases=[['../augmentor-runtime_0.2.13_amd64.deb'],
               ['augmentor-runtime_0.2.13_amd64.deb']*2,
               ['augmentor-runtime_0.2.13_amd64.deb','augmentor-desktop_0.2.12_amd64.deb'],
               ['augmentor-runtime_0.2.13_amd64.deb',{}]]
        for names in cases:
            value=manifest('debian13-amd64');value['packages']=names
            with self.subTest(names=names),self.assertRaises(ValueError):distro.package_files(value,value['target'])
        value=manifest('fedora43-x86_64')
        with self.assertRaises(ValueError):distro.package_files(value,'fedora44-x86_64')

    def test_voice_gpu_and_memory_dependencies_follow_explicit_choices(self):
        self.assertIn('nodejs-npm', distro.dependency_packages('fedora43-x86_64'))
        self.assertIn('nodejs24-npm', distro.dependency_packages('fedora44-x86_64'))
        for target in ('debian13-amd64','ubuntu26.04-amd64','fedora44-x86_64'):
            plain=distro.dependency_packages(target)
            full=distro.dependency_packages(target,voice=True,gpu=True,memory=True)
            self.assertNotIn('cmake',plain);self.assertIn('cmake',full)
            self.assertNotIn('docker.io',plain);self.assertNotIn('moby-engine',plain)
            self.assertIn('moby-engine' if target.startswith('fedora') else 'docker.io',full)
            existing=distro.dependency_packages(target,memory=True,memory_engine_present=True)
            self.assertNotIn('docker.io',existing);self.assertNotIn('moby-engine',existing)
        with self.assertRaises(ValueError):
            distro.install_plan(manifest('fedora44-x86_64'),'/bundle',info={'ID':'fedora','VERSION_ID':'44'},machine='x86_64',gpu=True)

    def test_plan_reads_verified_bundle_without_prompting_or_writing_state(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory);value=manifest('fedora44-x86_64')
            for name in value['packages']:(bundle/name).write_bytes(b'fixture')
            (bundle/'bundle.json').write_text(json.dumps(value))
            before={path.name:path.read_bytes() for path in bundle.iterdir()}
            args=SimpleNamespace(bundle=bundle,skip_packages=False,plan=True,voice=False,gpu=None,memory=False)
            with patch.object(setup.distribution,'host_target',return_value=value['target']),patch.object(setup,'run') as run,patch.object(setup,'write') as write,patch('builtins.input') as prompt:
                result=setup.install(args)
            self.assertEqual(result['system']['packageManager'],'dnf')
            run.assert_not_called();write.assert_not_called();prompt.assert_not_called()
            self.assertEqual(before,{path.name:path.read_bytes() for path in bundle.iterdir()})


if __name__=='__main__':unittest.main()
