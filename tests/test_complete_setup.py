# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import hashlib
import argparse
import importlib.util
import json
import os
import socket
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('complete_setup',ROOT/'scripts/setup-complete.py')
setup=importlib.util.module_from_spec(spec);spec.loader.exec_module(setup)

class CompleteSetupTests(unittest.TestCase):
    def test_local_and_secure_remote_model_settings(self):
        for url in ('http://127.0.0.1:8080/v1','https://example.test/v1'):
            value=setup.model_settings(url,'chosen-model',32768)
            self.assertEqual(value['agent-default-model'],{'provider':'augmentor-model','model':'chosen-model'})
            provider=value['llm-pi-ai']['providers']['augmentor-model']
            self.assertEqual(provider['apiKeyEnv'],'AUGMENTOR_MODEL_API_KEY')
            self.assertNotIn('apiKey',provider)
            self.assertEqual(provider['models'][0]['contextWindow'],32768)

    def test_unsafe_or_credential_bearing_model_urls_refused(self):
        for url in ('http://remote.test/v1','https://name:secret@example.test/v1','https://example.test/v1?key=secret','file:///tmp/model'):
            with self.subTest(url=url),self.assertRaises(ValueError):setup.model_settings(url,'model',32768)

    def test_environment_cannot_inject_a_second_setting(self):
        with self.assertRaises(ValueError):setup.environment_value('key\nOTHER=secret')
        self.assertEqual(setup.environment_value('value"with\\escape'),'"value\\"with\\\\escape"')

    def test_bundle_checks_actual_payload_and_refuses_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'app.deb').write_bytes(b'fixture')
            manifest={'format':'augmentor-complete/1','sha256':{'app.deb':hashlib.sha256(b'fixture').hexdigest()}}
            (root/'bundle.json').write_text(json.dumps(manifest));setup.verify_bundle(root)
            (root/'app.deb').write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError,'checksum failed'):setup.verify_bundle(root)
            manifest['sha256']={'../outside':'ignored'};(root/'bundle.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'Unsafe'):setup.verify_bundle(root)

    def test_service_keeps_credentials_out_of_command_and_restarts(self):
        text=setup.service(['/path with spaces/node','/runtime/dsh','web'],'/private dsh/home','/private/model.env','/private runtime/bin/python3')
        self.assertIn('Restart=on-failure',text)
        self.assertIn('EnvironmentFile="/private/model.env"',text)
        self.assertIn('"/path with spaces/node"',text)
        self.assertNotIn('apiKey',text)
        self.assertIn('UMask=0077',text)
        self.assertIn('Environment="AUGMENTOR_PYTHON=/private runtime/bin/python3"',text)

    def test_noble_without_declared_runtime_cannot_use_legacy_pip_fallback(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(setup,'run') as run:
            app=Path(directory)
            with self.assertRaisesRegex(ValueError,'required Python runtime policy'):
                setup.prepare_python(app,app/'data','ubuntu24.04-amd64')
            run.assert_not_called()

    def test_declared_runtime_must_match_bundle_before_preparation(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(setup,'run') as run:
            app=Path(directory);(app/'scripts').mkdir()
            (app/'linux-python-runtime.json').write_bytes((ROOT/'release/ubuntu24.04-python.json').read_bytes())
            (app/'scripts/linux-python-runtime.py').write_bytes((ROOT/'scripts/linux-python-runtime.py').read_bytes())
            with self.assertRaisesRegex(ValueError,'differs from the bundle target'):
                setup.prepare_python(app,app/'data','fedora44-x86_64')
            run.assert_not_called()

    def test_noble_policy_hash_mismatch_cannot_prepare_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            app=Path(directory);marker=app/'linux-python-runtime.json'
            marker.write_bytes((ROOT/'release/ubuntu24.04-python-voice.json').read_bytes())
            runtime=setup.load(ROOT/'scripts/linux-python-runtime.py')
            contract=runtime.contract(runtime.policy(marker),runtime.digest(marker))
            contract['policySha256']='a'*64
            with patch.object(setup,'load',return_value=runtime),patch.object(runtime,'prepare') as prepare:
                with self.assertRaisesRegex(ValueError,'differs from the complete bundle contract'):
                    setup.prepare_python(app,app/'data',setup.distribution.NOBLE,contract)
                prepare.assert_not_called()
            self.assertFalse((app/'data').exists())

    def test_noble_installed_receipt_still_verifies_runtime_without_repair(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);app=root/'app';app.mkdir();state=root/'state/augmentor-install';state.mkdir(parents=True)
            marker=app/'linux-python-runtime.json'
            marker.write_bytes((ROOT/'release/ubuntu24.04-python-voice.json').read_bytes())
            runtime=setup.load(ROOT/'scripts/linux-python-runtime.py')
            contract=runtime.contract(runtime.policy(marker),runtime.digest(marker))
            manifest={'version':'0.2.13','sourceCommit':'a'*40,'artifactId':'fixture',
                      'target':setup.distribution.NOBLE,'pythonRuntime':contract}
            (app/'release.json').write_text(json.dumps({'version':'0.2.13','source':{'commit':'a'*40,'dirty':False},
                                                       'target':manifest['target'],'pythonRuntime':contract}))
            stamp=state/'installation.json';stamp.write_text(json.dumps({'bundle':'fixture','status':'installed'}))
            before=stamp.read_bytes()
            args=SimpleNamespace(bundle=root,plan=False,skip_packages=True,app_root=app)
            with patch.dict(os.environ,{'XDG_STATE_HOME':str(root/'state')}),patch.object(Path,'home',return_value=root),\
                    patch.object(setup.os,'geteuid',return_value=1000),patch.object(setup,'verify_bundle',return_value=manifest),\
                    patch.object(setup,'load',return_value=runtime),patch.object(runtime,'resolve',side_effect=ValueError('runtime corrupted')),\
                    patch.object(runtime,'prepare') as prepare,patch.object(setup,'run') as run:
                with self.assertRaisesRegex(ValueError,'runtime corrupted'):setup.install(args)
                prepare.assert_not_called();run.assert_not_called()
            self.assertEqual(stamp.read_bytes(),before)

    def test_same_version_old_or_dirty_payload_cannot_configure_new_bundle(self):
        manifest={'version':'0.2.13','sourceCommit':'a'*40}
        with tempfile.TemporaryDirectory() as directory:
            app=Path(directory);identity=app/'release.json'
            for source,version in (({'commit':'b'*40,'dirty':False},'0.2.13'),
                                   ({'commit':'a'*40,'dirty':True},'0.2.13'),
                                   ({'commit':'a'*40,'dirty':False},'0.2.12')):
                identity.write_text(json.dumps({'version':version,'source':source}))
                with self.subTest(source=source,version=version),self.assertRaisesRegex(ValueError,'does not match'):
                    setup.verify_installed_payload(app,manifest)
            identity.write_text(json.dumps({'version':'0.2.13','source':{'commit':'a'*40,'dirty':False}}))
            setup.verify_installed_payload(app,manifest)
            for contents in ('bad JSON','null'):
                identity.write_text(contents)
                with self.assertRaises(ValueError):setup.verify_installed_payload(app,manifest)
            identity.unlink()
            with self.assertRaisesRegex(ValueError,'identity is missing'):setup.verify_installed_payload(app,manifest)

    def test_skip_packages_mismatch_stops_before_private_runtime_and_secrets(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);app=root/'app';app.mkdir()
            manifest={'version':'0.2.13','sourceCommit':'a'*40,'artifactId':'fixture'}
            (app/'release.json').write_text(json.dumps({'version':'0.2.13','source':{'commit':'b'*40,'dirty':False}}))
            with socket.socket() as listener:
                listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
            args=argparse.Namespace(bundle=root,plan=False,skip_packages=True,app_root=app,
                model_url='http://127.0.0.1:8080/v1',model='fixture',context=32768,
                non_interactive=True,memory=False,voice=False,gpu=None,api_key_env='FIXTURE_MODEL_KEY',port=port)
            environment={'XDG_DATA_HOME':str(root/'data'),'XDG_CONFIG_HOME':str(root/'config'),
                         'XDG_STATE_HOME':str(root/'state'),'FIXTURE_MODEL_KEY':'synthetic'}
            with patch.dict(os.environ,environment),patch.object(Path,'home',return_value=root),\
                 patch.object(setup.os,'geteuid',return_value=1000),\
                 patch.object(setup,'verify_bundle',return_value=manifest),patch.object(setup,'run') as command:
                with self.assertRaisesRegex(ValueError,'does not match'):setup.install(args)
                command.assert_not_called()
            self.assertFalse((root/'data').exists())
            self.assertFalse((root/'config').exists())
            record=json.loads((root/'state/augmentor-install/installation.json').read_text())
            self.assertEqual(record,{'bundle':'fixture','status':'preparing'})
