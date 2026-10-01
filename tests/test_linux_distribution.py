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
    if target.startswith('fedora'):
        release=target.split('-')[0].removeprefix('fedora')
        names=[f'augmentor-agent-{version}-1.fc{release}.x86_64.rpm']
    else:
        names=[f'augmentor-{kind}_{version}_amd64.deb' for kind in ('runtime','desktop')]
    return {'format':'augmentor-complete/1','target':target,'version':version,'components':{},
            'packages':names,'sha256':{name:hashlib.sha256(b'fixture').hexdigest() for name in names}}


class DistributionPlans(unittest.TestCase):
    def test_parse_quoted_release_fields_without_executing_them(self):
        result=distro.os_release('ID=ubuntu\nVERSION_ID="26.04"\nID_LIKE="debian"\nPRETTY_NAME="Ubuntu 26.04 LTS"\n# comment\n')
        self.assertEqual(distro.host_target(result,'x86_64'),'ubuntu26.04-amd64')
        self.assertEqual(distro.os_release('ID="$(touch /tmp/forbidden)"')['ID'],'$(touch /tmp/forbidden)')

    def test_supported_hosts_select_their_own_package_format(self):
        for target,(name,version,manager,_) in distro.TARGETS.items():
            value=distro.install_plan(manifest(target),'/bundle with spaces',info={'ID':name,'VERSION_ID':version},machine='x86_64')
            self.assertEqual(value['target'],target)
            self.assertEqual(value['command'][:4],['sudo',manager,'install','-y'])
            self.assertEqual(len(value['packages']),1 if manager=='dnf' else 2)
            for name in value['packages']:self.assertIn('/bundle with spaces/'+name,value['command'])

    def test_derivatives_older_releases_and_other_architectures_fail_closed(self):
        for info in ({'ID':'linuxmint','VERSION_ID':'22.3','ID_LIKE':'ubuntu debian'},
                     {'ID':'ubuntu','VERSION_ID':'24.04'},{'ID':'debian','VERSION_ID':'12'},
                     {'ID':'unknown','VERSION_ID':'44','ID_LIKE':'fedora'}):
            with self.subTest(info=info),self.assertRaises(ValueError):distro.host_target(info,'x86_64')
        with self.assertRaisesRegex(ValueError,'separately qualified'):distro.host_target({'ID':'fedora','VERSION_ID':'44'},'aarch64')

    def test_wrong_bundle_target_is_refused_even_for_debian_related_hosts(self):
        with self.assertRaisesRegex(ValueError,'matching bundle'):
            distro.install_plan(manifest('debian13-amd64'),'/bundle',info={'ID':'ubuntu','VERSION_ID':'26.04'},machine='x86_64')

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
