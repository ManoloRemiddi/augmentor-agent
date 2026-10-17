# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Authored data and disposable selections; no owner launcher/service changes."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


@unittest.skipUnless(sys.platform=='linux','MX/Linux selected launch adapter')
class SharedLaunchTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='authored-shared-launch-');self.addCleanup(temporary.cleanup);self.home=Path(temporary.name)
        env={'HOME':str(self.home),'XDG_DATA_HOME':str(self.home/'xdg-data'),'XDG_STATE_HOME':str(self.home/'xdg-state'),'XDG_CONFIG_HOME':str(self.home/'xdg-config'),'XDG_RUNTIME_DIR':str(self.home/'run')}
        for name in ('xdg-data','xdg-state','xdg-config','run'):(self.home/name).mkdir(mode=0o700)
        environment=patch.dict(os.environ,env);environment.start();self.addCleanup(environment.stop)
        stores=self.home/'stores';stores.mkdir(mode=0o700)
        run=subprocess.run([sys.executable,'-I','-B',str(ROOT/'tests/fixtures/shared-profile-data.py'),str(ROOT),str(stores),'target-processed'],capture_output=True,text=True,check=True)
        value=json.loads(run.stdout);self.before={key:value['source'][key] for key in ('state','data')};self.after={key:value['target'][key] for key in ('state','data')}
        os.environ.update(AUGMENTOR_SHARED_STATE=self.before['state'],AUGMENTOR_SHARED_DATA=self.before['data'])
        # These overrides are part of this fixture, never the test runner's later callers.
        self.addCleanup(lambda:os.environ.pop('AUGMENTOR_SHARED_STATE',None));self.addCleanup(lambda:os.environ.pop('AUGMENTOR_SHARED_DATA',None))
        self.shared=load('authored_shared_launch',ROOT/'scripts/shared-launch-profile.py')
        self.launch=load('authored_desktop_launch',ROOT/'scripts/desktop-launch.py')
        self.deploy=load('authored_deployment',ROOT/'scripts/desktop-deployment.py')
        self.deploy.DATA=self.home/'xdg-data/augmentor';self.deploy.DATA.mkdir(mode=0o700)
        source=self.home/'candidate';native=source/'apps/native/augmentor_linux';native.mkdir(parents=True)
        (native/'window.py').write_text('# --ensure-running\n');(native/'controller.py').write_text('# Authored component fixture\n')
        lifetime=source/'services/lifecycle/lease.py';lifetime.parent.mkdir(parents=True)
        lifetime.write_text('# Independently authored preflight fixture\ndef hold(_kind): pass\n')
        (source/'release').mkdir();(source/'release/product.json').write_text('{"version":"authored"}')
        mobile=source/'apps/mobile/start.py';mobile.parent.mkdir(parents=True);mobile.write_text('# Independently authored supervisor\n')
        manifest=source/'apps/browser/extension/manifest.json';manifest.parent.mkdir(parents=True);manifest.write_text('{"key":"YXV0aG9yZWQta2V5"}')
        server=source/'apps/browser/embed/server.mjs';server.parent.mkdir(parents=True);server.write_text('// Independently authored embedding marker\n')
        for name in ('shared-launch-profile.py','desktop-launch.py','desktop-browser-launch.py','embed-launch.py'):
            path=source/'scripts'/name;path.parent.mkdir(exist_ok=True);shutil.copy2(ROOT/'scripts'/name,path)
        (source/'scripts/app-sdk-launch.py').write_text('# Independently authored SDK adapter marker\n')
        for name in ('companion_import.py','memory/dual.py'):
            path=source/'services'/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/'services'/name,path)
        self.original={'root':str(source),'python':sys.executable,'node':shutil.which('node'),'dshService':None,'version':'authored'}
        self.deploy.atomic(self.deploy.DATA/'desktop.json',self.original)
        self.check=patch.object(self.deploy,'check');self.check.start();self.addCleanup(self.check.stop)
        self.release=self.deploy.stage(source,'independently-authored-launch-qualification')
        self.selection=self.deploy.verify(self.release)['deployment']
        self.deploy.atomic(self.deploy.DATA/'desktop.json',self.selection)

    def binding(self,previous=None,next_pair=None):
        previous=self.before if previous is None else previous;next_pair=self.after if next_pair is None else next_pair
        value={'schema':self.shared.SCHEMA,'previous':previous,'next':next_pair,'selectionSha256':hashlib.sha256((self.deploy.DATA/'desktop.json').read_bytes()).hexdigest(),'targetSha256':self.shared.component_fingerprint(next_pair)}
        path=self.home/'binding.json';path.write_text(json.dumps(value));path.chmod(0o600);return path

    def test_native_service_secondary_and_mobile_receive_the_same_selected_pair_and_preserve_speech(self):
        selected={**self.selection,'sharedProfile':self.after};self.deploy.atomic(self.deploy.DATA/'desktop.json',selected)
        # Mobile supervisor dispatch has no display/service side effect before exec.
        os.environ['RESONANT_VOICE_HOME']='/authored/unchanged-speech';self.addCleanup(lambda:os.environ.pop('RESONANT_VOICE_HOME',None))
        for args in (['--service-run'],['--instance','secondary'],['--mobile','--preview'],['--embed']):
            with self.subTest(args=args),patch.object(self.launch,'exchange',return_value=None),patch.object(self.launch.os,'execve') as execute:
                self.launch.main(args)
                argv=execute.call_args.args;env=argv[2]
                self.assertEqual(env['AUGMENTOR_SHARED_STATE'],self.after['state']);self.assertEqual(env['AUGMENTOR_SHARED_DATA'],self.after['data'])
                self.assertEqual(env['RESONANT_VOICE_HOME'],'/authored/unchanged-speech');self.assertEqual(env['AUGMENTOR_PYTHON'],sys.executable)
                self.assertEqual(env['AUGMENTOR_PI_NODE'],self.selection['node']);self.assertEqual(env['PI_TELEMETRY'],'0')

    def test_embedding_rechecks_selected_pair_and_preserves_sdk_adapter_and_clean_node_environment(self):
        selected={**self.selection,'sharedProfile':self.after};self.deploy.atomic(self.deploy.DATA/'desktop.json',selected)
        embedding=load('authored_embedding',ROOT/'scripts/embed-launch.py')
        with patch.dict(os.environ,{'NODE_OPTIONS':'--require /authored-never-load','NODE_PATH':'/authored-never-load'}),patch.object(embedding.os,'execve') as execute:
            embedding.main()
        args=execute.call_args.args;self.assertEqual(args[0],self.selection['python']);self.assertEqual(args[1][1:3],['-I','-B']);self.assertTrue(args[1][3].endswith('/scripts/app-sdk-launch.py'));self.assertEqual(args[1][4],'embed')
        self.assertEqual(args[2]['AUGMENTOR_SHARED_DATA'],self.after['data']);self.assertNotIn('NODE_OPTIONS',args[2]);self.assertNotIn('NODE_PATH',args[2])

    def test_cold_activation_preserves_database_bytes_and_reverse_manifest_restores_original_selection(self):
        before=self.shared.component_fingerprint(self.before);after=self.shared.component_fingerprint(self.after)
        selected=self.deploy.activate(self.release,self.binding());self.assertEqual(selected['sharedProfile'],self.after)
        self.assertEqual(self.deploy.read(self.deploy.DATA/'desktop.previous.json'),self.selection)
        with self.assertRaisesRegex(ValueError,'explicit cold reverse'):self.deploy.rollback()
        reverse=self.binding(self.after,self.before);restored=self.deploy.rollback(reverse)
        self.assertEqual(restored,self.selection);self.assertEqual(self.shared.component_fingerprint(self.before),before);self.assertEqual(self.shared.component_fingerprint(self.after),after)

    def test_managed_reader_or_component_lease_refuses_binding_without_changing_selection(self):
        raw=(self.deploy.DATA/'desktop.json').read_bytes();binding=self.binding()
        with self.shared.launch_lease(self.deploy.DATA):
            with self.assertRaisesRegex(ValueError,'managed client is active'):self.deploy.activate(self.release,binding)
        with self.shared.cold([self.after]):
            with self.assertRaisesRegex(ValueError,'companion owners'):self.deploy.activate(self.release,binding)
        self.assertEqual((self.deploy.DATA/'desktop.json').read_bytes(),raw)

    def test_actual_cli_inspect_activate_and_reverse_keep_cold_database_bytes(self):
        pair=self.home/'pair.json';pair.write_text(json.dumps(self.after));pair.chmod(0o600)
        before=self.shared.component_fingerprint(self.before);after=self.shared.component_fingerprint(self.after)
        inspected=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/shared-launch-profile.py'),'inspect',str(pair)],capture_output=True,text=True,check=True)
        self.assertEqual(json.loads(inspected.stdout)['sha256'],after)
        # Actual CLI and read-only schema checker; authored import/lifetime stubs
        # above isolate this transaction test from installed Qt/DSH/model services.
        def command(*args):
            return subprocess.run([sys.executable,'-B',str(ROOT/'scripts/desktop-deployment.py'),*map(str,args)],capture_output=True,text=True,check=True)
        command('activate',self.release,'--shared-profile',self.binding())
        self.assertEqual(self.deploy.read(self.deploy.DATA/'desktop.json')['sharedProfile'],self.after)
        command('rollback','--shared-profile',self.binding(self.after,self.before))
        self.assertEqual(self.deploy.read(self.deploy.DATA/'desktop.json'),self.selection)
        self.assertEqual(self.shared.component_fingerprint(self.before),before);self.assertEqual(self.shared.component_fingerprint(self.after),after)

    def test_stale_selection_changed_target_and_invalid_schema_refuse_without_promotion(self):
        raw=(self.deploy.DATA/'desktop.json').read_bytes();path=self.binding();value=json.loads(path.read_text());value['selectionSha256']='0'*64;path.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'selection changed'):self.deploy.activate(self.release,path)
        path=self.binding();Path(self.after['data'],'hindsight-installation.json').write_text('{}');Path(self.after['data'],'hindsight-installation.json').chmod(0o600)
        with self.assertRaisesRegex(ValueError,'changed since'):self.deploy.activate(self.release,path)
        Path(self.after['data'],'hindsight-installation.json').unlink()
        import sqlite3
        with sqlite3.connect(Path(self.after['data'])/'dual-memory.sqlite3') as db:db.execute('CREATE TABLE unsupported_authored_table (id TEXT)')
        with self.assertRaisesRegex(ValueError,'database validation'):self.deploy.activate(self.release,self.binding())
        self.assertEqual((self.deploy.DATA/'desktop.json').read_bytes(),raw)

    def test_unrelated_build_update_keeps_current_binding_and_rejects_selection_changes_during_preflight(self):
        self.deploy.activate(self.release,self.binding());selected=self.deploy.read(self.deploy.DATA/'desktop.json')
        next_release=self.deploy.stage(self.release,'second-authored-build')
        # A later user choice wins over an older staged launch snapshot.
        changed={**selected,'sharedProfile':self.before};self.deploy.atomic(self.deploy.DATA/'desktop.json',changed)
        updated=self.deploy.activate(next_release);self.assertEqual(updated['sharedProfile'],self.before)
        newer={**updated,'authoredConcurrentEdit':True}
        def edit_during_check(*_args,**_kwargs):self.deploy.atomic(self.deploy.DATA/'desktop.json',newer)
        with patch.object(self.deploy,'check',side_effect=edit_during_check),self.assertRaisesRegex(ValueError,'selection changed during promotion'):
            self.deploy.activate(self.release)
        self.assertEqual(self.deploy.read(self.deploy.DATA/'desktop.json'),newer)

    def test_binding_refuses_archive_alias_overlap_and_permissive_or_unknown_metadata(self):
        path=self.binding();path.chmod(0o644)
        with self.assertRaisesRegex(ValueError,'private owned'):self.deploy.activate(self.release,path)
        path.chmod(0o600);value=json.loads(path.read_text());value['unknown']='authored';path.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'Unsupported'):self.deploy.activate(self.release,path)
        archive=self.home/'shared-imports'/('a'*64)/'data';archive.mkdir(parents=True,mode=0o700)
        with self.assertRaisesRegex(ValueError,'evidence'):self.shared.profile({'state':self.after['state'],'data':str(archive)},dedicated=False)
        nested=archive/'nested-state';nested.mkdir(mode=0o700)
        with self.assertRaisesRegex(ValueError,'evidence'):self.shared.profile({'state':str(nested),'data':self.after['data']},dedicated=False)
        alias=self.home/'data-alias';alias.symlink_to(self.after['data'])
        with self.assertRaisesRegex(ValueError,'aliases'):self.shared.profile({'state':self.after['state'],'data':str(alias)})
        with self.assertRaisesRegex(ValueError,'overlap'):self.shared.profile({'state':self.after['data'],'data':self.after['data']})
        value=json.loads(self.binding().read_text());value['next']['state']=self.before['data'];path.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'overlap across'):self.deploy.activate(self.release,path)

    def test_browser_registration_is_opt_in_and_exact_hash_adoption_keeps_sealed_source_untouched(self):
        installer=load('authored_installer',ROOT/'scripts/install-desktop-startup.py')
        # The registration key is independently authored, not an owner manifest.
        seal=self.deploy.verify(self.release)
        host=self.home/'xdg-config/chromium/NativeMessagingHosts/com.augmentor.agent.json';host.parent.mkdir(parents=True);host.write_text('AUTHORED_ORIGINAL_HOST')
        original=host.read_bytes();self.selection['dshService']=None
        with self.assertRaisesRegex(ValueError,'explicit adoption'):installer.install(self.release,Path(sys.executable),Path(self.selection['node']),enable=False,register_browser=True)
        self.assertEqual(host.read_bytes(),original)
        expected={name:None for name in ('chromium','google-chrome','google-chrome-beta','BraveSoftware/Brave-Browser')};expected['chromium']=hashlib.sha256(original).hexdigest()
        with patch.object(Path,'home',return_value=self.home):installer.install(self.release,Path(sys.executable),Path(self.selection['node']),enable=False,register_browser=True,expected_hosts=expected)
        saved=json.loads(host.read_text());entry=self.home/'.local/bin/augmentor-browser-host-managed';self.assertEqual(saved['path'],str(entry));self.assertNotIn(str(self.release),entry.read_text())
        self.assertFalse((self.release/'scripts/augmentor-browser-host').exists());self.assertTrue((self.deploy.DATA/'shared-launch-profile.py').is_file())
        self.assertEqual(self.deploy.verify(self.release),seal)

    def test_late_target_edit_and_binding_selection_race_preserve_the_current_selection(self):
        original=(self.deploy.DATA/'desktop.json').read_bytes();binding=self.binding()
        def edit_target(*_args,**_kwargs):Path(self.after['data'],'hindsight.json').write_text('{"authoredConcurrentEdit":true}')
        with patch.object(self.deploy,'check',side_effect=edit_target),self.assertRaisesRegex(ValueError,'changed before'):
            self.deploy.activate(self.release,binding)
        self.assertEqual((self.deploy.DATA/'desktop.json').read_bytes(),original)
        binding=self.binding();concurrent={**self.selection,'authoredOwnerEdit':True}
        def edit_selection(*_args,**_kwargs):self.deploy.atomic(self.deploy.DATA/'desktop.json',concurrent)
        with patch.object(self.deploy,'check',side_effect=edit_selection),self.assertRaisesRegex(ValueError,'selection changed during'):
            self.deploy.activate(self.release,binding)
        self.assertEqual(self.deploy.read(self.deploy.DATA/'desktop.json'),concurrent)

    def test_existing_binding_tolerates_later_engine_backups_without_relaxing_cold_adoption(self):
        backup=Path(self.after['data'])/'hindsight-before-controlled-authored.tar';backup.write_bytes(b'AUTHORED_MEMORY_BACKUP')
        env=self.shared.environment(self.after,{'RESONANT_VOICE_HOME':'KEEP_SPEECH_CONFIG'})
        self.assertEqual(env['AUGMENTOR_SHARED_DATA'],self.after['data']);self.assertEqual(env['RESONANT_VOICE_HOME'],'KEEP_SPEECH_CONFIG')
        with self.assertRaisesRegex(ValueError,'dedicated shared data'):self.shared.profile(self.after)

    def test_interrupted_startup_write_restores_owned_bytes_and_preserves_concurrent_edits(self):
        installer=load('authored_atomic_installer',ROOT/'scripts/install-desktop-startup.py');first=self.home/'first';second=self.home/'second';first.write_bytes(b'ORIGINAL_ONE');first.chmod(0o600);second.write_bytes(b'ORIGINAL_TWO');second.chmod(0o600)
        backup=self.home/'backup';backup.mkdir();original=installer.atomic_bytes
        def fail(path,content,mode):
            if path==second:raise OSError('Authored late startup failure')
            return original(path,content,mode)
        with patch.object(installer,'atomic_bytes',side_effect=fail),self.assertRaisesRegex(OSError,'late startup'):
            installer.write_startup_files({first:'NEW_ONE',second:'NEW_TWO'},backup,self.home,{})
        self.assertEqual(first.read_bytes(),b'ORIGINAL_ONE');self.assertEqual(second.read_bytes(),b'ORIGINAL_TWO')
        def race(path,content,mode):
            if path==second:first.write_bytes(b'KEEP_CONCURRENT_EDIT');raise OSError('Authored owner edit')
            return original(path,content,mode)
        with patch.object(installer,'atomic_bytes',side_effect=race),self.assertRaisesRegex(ValueError,'concurrent edits'):
            installer.write_startup_files({first:'NEW_ONE',second:'NEW_TWO'},backup,self.home,{})
        self.assertEqual(first.read_bytes(),b'KEEP_CONCURRENT_EDIT');self.assertEqual(second.read_bytes(),b'ORIGINAL_TWO')
