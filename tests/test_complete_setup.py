# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import hashlib
import argparse
import importlib.util
import json
import os
import socket
import shutil
import subprocess
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
import sys

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('complete_setup',ROOT/'scripts/setup-complete.py')
setup=importlib.util.module_from_spec(spec);spec.loader.exec_module(setup)

class CompleteSetupTests(unittest.TestCase):
    def test_initial_settings_indent_sequences_without_changing_safe_dump_values(self):
        import yaml
        settings=setup.model_settings('http://127.0.0.1:34187/v1','fixture',8192)
        before=yaml.safe_dump(settings);after=setup.settings_yaml(settings)
        self.assertEqual(yaml.safe_load(after),yaml.safe_load(before))
        self.assertIn('      models:\n        - contextWindow: 8192\n',after)
        self.assertIn('          input:\n            - text\n',after)
        # Scalar, key-order and trailing-newline defaults stay unchanged.
        self.assertEqual(setup.settings_yaml({'z':False,'a':'café','n':None}),
                         yaml.safe_dump({'z':False,'a':'café','n':None}))

    @unittest.skipUnless(shutil.which('node'), 'Real Node YAML serializer required')
    def test_initial_settings_survive_exact_pinned_node_yaml_document_reserialization(self):
        module=Path(os.environ.get('AUGMENTOR_TEST_YAML_MODULE',ROOT/'node_modules/yaml')).resolve()
        metadata=module/'package.json'
        if not metadata.exists() or json.loads(metadata.read_text()).get('version')!='2.9.1':
            self.skipTest('Provide the locked yaml2.9.1 package with AUGMENTOR_TEST_YAML_MODULE.')
        probe="""const fs=require('node:fs');const root=process.argv[1];
const version=require(root+'/package.json').version;if(version!=='2.9.1')throw Error('Unpinned YAML');
const {parseDocument}=require(root);const input=fs.readFileSync(0,'utf8');
const document=parseDocument(input);if(document.errors.length)throw document.errors[0];
// DSH replaces the unchanged default-model namespace through a leaf diff,
// then calls Document.toString() even when no leaf value changed.
process.stdout.write(document.toString());"""
        settings=setup.model_settings('http://127.0.0.1:34187/v1','fixture',8192)
        before=setup.settings_yaml(settings)
        result=subprocess.run([shutil.which('node'),'-e',probe,str(module)],input=before,
                              text=True,capture_output=True,check=True,timeout=10)
        self.assertEqual(result.stdout,before)
        # A real regression: the former indentless output changes on first Save.
        import yaml
        old=yaml.safe_dump(settings)
        old_roundtrip=subprocess.run([shutil.which('node'),'-e',probe,str(module)],input=old,
                                    text=True,capture_output=True,check=True,timeout=10)
        self.assertNotEqual(old_roundtrip.stdout,old)
        self.assertEqual(old_roundtrip.stdout,before)

    def startup_fixture(self, directory, *, ready_at=None, exit_code=None):
        sys.path.insert(0,str(ROOT/'services'))
        from platform_adapters.paths import private_directory
        home=private_directory(Path(directory)/'home');state=private_directory(Path(directory)/'state')
        clock=SimpleNamespace(now=0.)
        def sleep(seconds):clock.now+=seconds
        process=SimpleNamespace(terminate=Mock(),kill=Mock(),wait=Mock(return_value=0),close=Mock())
        def poll():
            if ready_at is not None and clock.now>=ready_at:
                (state/'setup-dsh.log').write_text('Listening: http://127.0.0.1:3080/?token=fixture-native-token\n')
            return exit_code
        process.poll=Mock(side_effect=poll)
        integration=Mock();integration.check.return_value={'installed':True,'token':'checked-integration'}
        remote=Mock()
        return home,state,clock,sleep,process,integration,remote

    def test_bounded_start_accepts_verified_late_readiness_and_closes_its_owned_range(self):
        with tempfile.TemporaryDirectory() as directory:
            home,state,clock,sleep,process,integration,remote=self.startup_fixture(directory,ready_at=85)
            with patch('platform_adapters.processes.OwnedProcess',return_value=process) as launch,\
                 patch('dsh.setup.Setup',return_value=integration),patch('dsh.remote.client',return_value=remote),\
                 patch.object(setup.time,'monotonic',side_effect=lambda:clock.now),\
                 patch.object(setup.time,'sleep',side_effect=sleep):
                setup.configure_product(ROOT,ROOT/'fixture-cli',home,'http://127.0.0.1:3080',{},state)
            self.assertGreater(clock.now,60);self.assertLess(clock.now,120)
            remote.call.assert_called_once_with('host.describe')
            integration.check.assert_called_once_with({'endpoint':'http://127.0.0.1:3080/?token=fixture-native-token','home':str(home)})
            integration.install.assert_not_called();integration.save.assert_called_once_with('checked-integration')
            launch.assert_called_once();process.terminate.assert_called_once();process.wait.assert_called_once_with(timeout=15);process.close.assert_called_once()

    def test_startup_deadline_stops_the_owned_range_without_retry_or_integration_save(self):
        with tempfile.TemporaryDirectory() as directory:
            home,state,clock,sleep,process,integration,remote=self.startup_fixture(directory)
            with patch('platform_adapters.processes.OwnedProcess',return_value=process) as launch,\
                 patch('dsh.setup.Setup',return_value=integration),patch('dsh.remote.client',return_value=remote),\
                 patch.object(setup.time,'monotonic',side_effect=lambda:clock.now),\
                 patch.object(setup.time,'sleep',side_effect=sleep):
                with self.assertRaisesRegex(RuntimeError,'did not become ready'):
                    setup.configure_product(ROOT,ROOT/'fixture-cli',home,'http://127.0.0.1:3080',{},state)
            self.assertEqual(clock.now,120);launch.assert_called_once();remote.call.assert_not_called()
            integration.check.assert_not_called();integration.install.assert_not_called();integration.save.assert_not_called()
            process.terminate.assert_called_once();process.wait.assert_called_once_with(timeout=15);process.close.assert_called_once()

    def test_integration_restart_accepts_late_readiness_without_replaying_install(self):
        with tempfile.TemporaryDirectory() as directory:
            home,state,clock,sleep,first,integration,remote=self.startup_fixture(directory,ready_at=0)
            second=SimpleNamespace(terminate=Mock(),kill=Mock(),wait=Mock(return_value=0),close=Mock())
            def poll():
                if clock.now>=85:(state/'setup-dsh.log').write_text('Ready: ?token=second-native-token\n')
                return None
            second.poll=Mock(side_effect=poll)
            integration.check.side_effect=[{'installed':False,'token':'first-checked'},
                                           {'installed':True,'token':'second-checked'}]
            with patch('platform_adapters.processes.OwnedProcess',side_effect=[first,second]) as launch,\
                 patch('dsh.setup.Setup',return_value=integration),patch('dsh.remote.client',return_value=remote),\
                 patch.object(setup.time,'monotonic',side_effect=lambda:clock.now),\
                 patch.object(setup.time,'sleep',side_effect=sleep):
                setup.configure_product(ROOT,ROOT/'fixture-cli',home,'http://127.0.0.1:3080',{},state)
            self.assertEqual(clock.now,85);self.assertEqual(launch.call_count,2)
            self.assertEqual(remote.call.call_count,2)
            integration.install.assert_called_once_with('first-checked')
            integration.save.assert_called_once_with('second-checked')
            for process in (first,second):
                process.terminate.assert_called_once();process.wait.assert_called_once_with(timeout=15);process.close.assert_called_once()

    def test_startup_process_exit_refuses_immediately_and_never_saves_integration(self):
        with tempfile.TemporaryDirectory() as directory:
            home,state,clock,sleep,process,integration,remote=self.startup_fixture(directory,exit_code=17)
            with patch('platform_adapters.processes.OwnedProcess',return_value=process),\
                 patch('dsh.setup.Setup',return_value=integration),patch('dsh.remote.client',return_value=remote),\
                 patch.object(setup.time,'monotonic',side_effect=lambda:clock.now),\
                 patch.object(setup.time,'sleep',side_effect=sleep):
                with self.assertRaisesRegex(RuntimeError,'stopped \\(exit 17\\)'):
                    setup.configure_product(ROOT,ROOT/'fixture-cli',home,'http://127.0.0.1:3080',{},state)
            self.assertEqual(clock.now,0);process.terminate.assert_not_called();process.close.assert_called_once()
            remote.call.assert_not_called();integration.check.assert_not_called();integration.save.assert_not_called()

    def test_bootstrap_token_is_private_and_reused_after_failed_start(self):
        sys.path.insert(0,str(ROOT/'services'))
        from dsh.setup import product_token
        from platform_adapters.paths import private_directory
        with tempfile.TemporaryDirectory() as directory:
            home=private_directory(Path(directory)/'home');state=private_directory(Path(directory)/'state')
            with patch('platform_adapters.processes.OwnedProcess',side_effect=RuntimeError('fixture startup failure')):
                with self.assertRaisesRegex(RuntimeError,'fixture startup failure'):
                    setup.configure_product(ROOT,ROOT/'fixture-cli',home,'http://127.0.0.1:3080',{},state)
                token=product_token(home/'augmentor-product-token')
                with self.assertRaisesRegex(RuntimeError,'fixture startup failure'):
                    setup.configure_product(ROOT,ROOT/'fixture-cli',home,'http://127.0.0.1:3080',{},state)
                self.assertEqual(product_token(home/'augmentor-product-token'),token)

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

    @unittest.skipUnless(sys.platform.startswith('linux'), 'Linux installed-runtime adapter')
    def test_declared_runtime_must_match_bundle_before_preparation(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(setup,'run') as run:
            app=Path(directory);(app/'scripts').mkdir()
            (app/'linux-python-runtime.json').write_bytes((ROOT/'release/ubuntu24.04-python.json').read_bytes())
            (app/'scripts/linux-python-runtime.py').write_bytes((ROOT/'scripts/linux-python-runtime.py').read_bytes())
            with self.assertRaisesRegex(ValueError,'differs from the bundle target'):
                setup.prepare_python(app,app/'data','fedora44-x86_64')
            run.assert_not_called()

    @unittest.skipUnless(sys.platform.startswith('linux'), 'Linux installed-runtime adapter')
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

    @unittest.skipUnless(sys.platform.startswith('linux'), 'Linux installed-runtime adapter')
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

    @unittest.skipUnless(sys.platform.startswith('linux'), 'Linux installed-package setup entrypoint')
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
