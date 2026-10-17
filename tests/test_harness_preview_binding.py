# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Authored sealed preview identity, mutable binding and startup admission."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]


@unittest.skipUnless(sys.platform=='linux','MX preview binding')
class PreviewBindingTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(dir=os.environ.get('AUGMENTOR_BUILD_WORKSPACE'));self.addCleanup(temporary.cleanup)
        self.base=Path(temporary.name)
        environment=patch.dict(os.environ,{key:str(self.base/name) for key,name in [('HOME','home'),('XDG_DATA_HOME','data'),('XDG_CONFIG_HOME','config'),('XDG_STATE_HOME','state'),('XDG_RUNTIME_DIR','run')]})
        environment.start();self.addCleanup(environment.stop)
        for path in (self.base/'data',self.base/'config',self.base/'state',self.base/'run'):path.mkdir(mode=0o700)
        self.data=self.base/'data/augmentor-harness-preview/augmentor'
        # Intermediate mkdir modes follow the caller's umask, including 0022
        # on hosted runners. Construct the actual private installed profile.
        self.data.parent.mkdir(mode=0o700);self.data.mkdir(mode=0o700)
        self.root=self.data/'releases/authored';(self.root/'node/bin').mkdir(parents=True,mode=0o700)
        (self.root/'node/bin/node').write_bytes(b'AUTHORED NODE');(self.root/'node/bin/node').chmod(0o700)
        files={'node/bin/node':hashlib.sha256(b'AUTHORED NODE').hexdigest()}
        self.selected={'root':str(self.root),'node':str(self.root/'node/bin/node'),'python':sys.executable,'version':'authored','releaseId':'authored','sourceRef':'authored','artifactSha256':hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()}
        (self.root/'desktop-release.json').write_text(json.dumps({'deployment':self.selected,'files':files,'artifactSha256':self.selected['artifactSha256']}))
        self.descriptor=self.data/'desktop.json';self.save(self.selected)
        # Exercise the protected installed layout, rather than trusting the
        # checkout's group-writable development files as installed helpers.
        self.bin=self.base/'bin';self.bin.mkdir(mode=0o700)
        for name in ('harness-preview.py','shared-launch-profile.py'):
            path=self.bin/name;shutil.copyfile(ROOT/'scripts'/name,path);path.chmod(0o700)
        spec=importlib.util.spec_from_file_location('authored_preview',self.bin/'harness-preview.py');self.preview=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.preview)
        self.pair={'state':str(self.base/'common-state'),'data':str(self.base/'common-data')}
        for name in self.pair.values():Path(name).mkdir(mode=0o700)
        for name in self.preview.shared_helper().DATABASES:
            path=Path(self.pair['data'])/name;path.write_bytes(b'AUTHORED COMPONENT');path.chmod(0o600)

    def save(self,value):self.descriptor.write_text(json.dumps(value));self.descriptor.chmod(0o600)

    def test_binding_changes_only_shared_paths_and_preserves_existing_preview_identity(self):
        before=self.preview.configuration()[1]
        self.save({**self.selected,'sharedProfile':self.pair})
        selected,after=self.preview.configuration()
        self.assertEqual(selected['sharedProfile'],self.pair)
        self.assertEqual(after['AUGMENTOR_SHARED_DATA'],self.pair['data'])
        self.assertEqual(after['AUGMENTOR_SHARED_STATE'],self.pair['state'])
        for key in ['AUGMENTOR_PI_CONFIG','AUGMENTOR_PI_STATE','AUGMENTOR_PI_SOCKET','PI_CODING_AGENT_DIR','AUGMENTOR_PI_WORKSPACE','AUGMENTOR_DICTATION_STATE','AUGMENTOR_PI_LLAMA_CPP_PROVIDERS']:
            self.assertEqual(after[key],before[key],key)
        self.assertEqual(after['PI_TELEMETRY'],'0')

    def test_another_immutable_field_or_changed_artifact_still_refuses(self):
        self.save({**self.selected,'version':'foreign','sharedProfile':self.pair})
        with self.assertRaisesRegex(ValueError,'staged identity'):self.preview.configuration()
        self.save(self.selected);(self.root/'node/bin/node').write_bytes(b'AUTHORED MODIFIED NODE')
        with self.assertRaisesRegex(ValueError,'files changed'):self.preview.configuration()

    def test_invalid_shared_store_does_not_fall_back_to_the_old_preview_store(self):
        alias=self.base/'alias';alias.symlink_to(self.pair['data'])
        self.save({**self.selected,'sharedProfile':{**self.pair,'data':str(alias)}})
        with self.assertRaisesRegex(ValueError,'aliases'):self.preview.configuration()

    def test_maintenance_fence_blocks_before_configuration_or_model_start(self):
        (self.data/'dsh-preservation.json').write_text('AUTHORED PENDING')
        with patch.object(sys,'argv',['harness-preview','--native']),patch.object(self.preview,'open_selected') as opened:
            with self.assertRaisesRegex(ValueError,'requires recovery'):self.preview.main()
        opened.assert_not_called()

    def test_active_writer_blocks_the_native_and_browser_entry_modes(self):
        with self.preview.shared_helper().launch_lease(self.data,exclusive=True):
            for args in (['--native'],[]):
                with self.subTest(args=args),patch.object(sys,'argv',['harness-preview',*args]),patch.object(self.preview,'open_selected') as opened:
                    with self.assertRaisesRegex(ValueError,'managed client'):self.preview.main()
                opened.assert_not_called()

    def test_installed_single_opener_finds_the_protected_stable_helper(self):
        helper=self.bin/'shared-launch-profile.py'
        helper.rename(self.data/'shared-launch-profile.py')
        self.assertEqual(self.preview.shared_helper().DATABASES,('prompts.sqlite3','dual-memory.sqlite3','memory.sqlite3'))

    def test_missing_linked_or_writable_helper_refuses_before_startup(self):
        helper=self.bin/'shared-launch-profile.py'
        for kind in ('writable','link','missing'):
            with self.subTest(kind=kind):
                if kind=='writable':helper.chmod(0o720)
                elif kind=='link':
                    helper.unlink();helper.symlink_to(ROOT/'scripts/shared-launch-profile.py')
                else:helper.unlink()
                with patch.object(sys,'argv',['harness-preview','--native']),patch.object(self.preview,'open_selected') as opened:
                    with self.assertRaises(ValueError):self.preview.main()
                opened.assert_not_called()
