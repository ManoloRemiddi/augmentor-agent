# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Native setup must not trust a success code or an old completed user stamp."""
from contextlib import nullcontext
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))


def module(name):
    spec=importlib.util.spec_from_file_location(name.replace('-','_'),ROOT/'scripts'/f'{name}.py')
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


setup=module('setup-complete')
builder=module('package-complete')
verifier=module('linux-package-verification')


class NativeCompleteSetup(unittest.TestCase):
    @unittest.skipUnless(sys.platform.startswith('linux'), 'Linux native installed-package adapter')
    def test_completed_native_stamp_cannot_skip_pending_or_changed_registered_package(self):
        runtime=module('linux-python-runtime')
        policy=ROOT/'release/opensuse-leap16.0-python-voice.json'
        contract=runtime.contract(runtime.policy(policy),runtime.digest(policy))
        manifest={'version':'0.2.13','sourceCommit':'a'*40,'artifactId':'fixture',
                  'target':setup.distribution.LEAP,'pythonRuntime':contract,
                  'packages':['augmentor-agent-0.2.13-1.leap16.x86_64.rpm'],
                  'sha256':{'augmentor-agent-0.2.13-1.leap16.x86_64.rpm':'b'*64},
                  'nativePackage':{'name':'augmentor-agent','versionRelease':'0.2.13-1.leap16','architecture':'x86_64'}}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);app=root/'app';app.mkdir()
            state=root/'state/augmentor-install';state.mkdir(parents=True)
            stamp=state/'installation.json';stamp.write_text(json.dumps({'bundle':'fixture','status':'installed'}))
            before=stamp.read_bytes()
            (app/'release.json').write_text(json.dumps({'version':manifest['version'],
                'source':{'commit':'a'*40,'dirty':False},'target':manifest['target'],'pythonRuntime':contract}))
            args=SimpleNamespace(bundle=root,plan=False,skip_packages=True,app_root=app)
            for failure in ('native package maintenance unresolved','registered package differs'):
                adapter=SimpleNamespace(verify_payload=unittest.mock.Mock(side_effect=ValueError(failure)))
                with self.subTest(failure=failure),patch.dict(os.environ,{'XDG_STATE_HOME':str(root/'state')}),\
                     patch.object(Path,'home',return_value=root),patch.object(setup.os,'geteuid',return_value=1002),\
                     patch.object(setup,'verify_bundle',return_value=manifest),patch.object(setup,'load',return_value=adapter),\
                     patch.object(setup,'run') as run,patch.object(setup,'write') as write:
                    with self.assertRaisesRegex(ValueError,failure):setup.install(args)
                    adapter.verify_payload.assert_called_once();run.assert_not_called();write.assert_not_called()
                self.assertEqual(stamp.read_bytes(),before)

    def test_custom_effective_hook_directory_refuses_before_file_access(self):
        manifest={'guardPackage':{'name':'augmentor-package-guard','versionRelease':'0.2.13-2','architecture':'any'}}
        fields='Name : augmentor-package-guard\nVersion : 0.2.13-2\nArchitecture : any\n'
        with patch.object(verifier,'query',side_effect=[fields,'/etc/pacman.d/hooks/\n/custom/hooks/\n']),\
             patch.object(Path,'lstat') as stat:
            with self.assertRaisesRegex(ValueError,'Custom pacman hook'):verifier.verify_guard(manifest)
            stat.assert_not_called()

    def test_guard_archive_extra_script_or_changed_control_refuses_without_execution(self):
        references={key:ROOT/('release/linux-package-guard.py' if relative=='linux-package-guard.py'
                              else 'release/arch/guard/'+Path(relative).name) for key,relative in verifier.GUARD_FILES.items()}
        references['/usr/share/licenses/augmentor-package-guard/LICENSE']=ROOT/'LICENSE'
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'augmentor-package-guard-0.2.13-2-any.pkg.tar.zst';path.write_bytes(b'synthetic archive transport')
            for defect in ('install-script','changed-control','wrong-version'):
                stream=io.BytesIO()
                with tarfile.open(fileobj=stream,mode='w') as archive:
                    entries={name.lstrip('/'):source.read_bytes() for name,source in references.items()}
                    entries['.PKGINFO']=('pkgname = augmentor-package-guard\npkgver = '+
                        ('0.2.13-1' if defect=='wrong-version' else '0.2.13-2')+'\narch = any\n').encode()
                    if defect=='install-script':entries['.INSTALL']=b'Unapproved native install hook; never execute.'
                    if defect=='changed-control':entries['usr/lib/augmentor-package-guard/lifecycle.py']+=b'\n# changed\n'
                    for name,body in entries.items():
                        info=tarfile.TarInfo(name);info.mode=0o644;info.size=len(body)
                        archive.addfile(info,io.BytesIO(body))
                stream.seek(0)
                producer=SimpleNamespace(stdout=stream,returncode=0,communicate=lambda:(b'',b''),kill=lambda:None)
                with self.subTest(defect=defect),patch.object(builder.subprocess,'Popen',return_value=nullcontext(producer)),\
                     self.assertRaises(ValueError):builder.checked_arch_guard(path)

    def test_npm_wrapper_refuses_changed_partial_install_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);data=root/'data';(data/'installer-bin').mkdir(parents=True)
            command=data/'installer-bin/npm';command.write_text('unexpected existing command')
            before=command.read_bytes()
            with patch.object(Path,'stat',return_value=SimpleNamespace(st_uid=0,st_mode=0o100644)),\
                 patch.object(Path,'is_file',return_value=True),patch.object(setup,'write') as write:
                with self.assertRaisesRegex(ValueError,'private installer npm command differs'):
                    setup.npm_environment(setup.distribution.LEAP,root/'app',data,{'PATH':'/usr/bin'})
                write.assert_not_called()
            self.assertEqual(command.read_bytes(),before)


if __name__=='__main__':unittest.main()
