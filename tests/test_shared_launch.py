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
        mobile=source/'apps/mobile/start.py';mobile.parent.mkdir(parents=True)
        mobile.write_text("# Independently authored supervisor\nimport os,json,sys,shutil\nprint(json.dumps({'argv':sys.argv[1:],'node':shutil.which('node'),'shared':os.environ.get('AUGMENTOR_SHARED_DATA'),'voice':os.environ.get('AUTHORED_VOICE_KEEP')}))\n")
        manifest=source/'apps/browser/extension/manifest.json';manifest.parent.mkdir(parents=True);manifest.write_text('{"key":"YXV0aG9yZWQta2V5"}')
        server=source/'apps/browser/embed/server.mjs';server.parent.mkdir(parents=True);server.write_text('// Independently authored embedding marker\n')
        host=source/'apps/browser/native-host.mjs'
        host.write_text("// Independently authored native peer\nconsole.log(JSON.stringify({argv:process.argv.slice(2),shared:process.env.AUGMENTOR_SHARED_DATA,state:process.env.AUGMENTOR_SHARED_STATE,telemetry:process.env.PI_TELEMETRY,options:process.env.NODE_OPTIONS??null}));\n")
        (native/'home_tray.py').write_text('# Independently authored Home entry\n')
        for name in ('shared-launch-profile.py','desktop-launch.py','desktop-browser-launch.py','desktop-dsh-launch.py','dsh-profile-gate.py','embed-launch.py','home-launch.py'):
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
                if args[0]=='--mobile':
                    self.assertEqual(env['PATH'].split(os.pathsep)[0],str(Path(self.selection['node']).parent))
                    self.assertEqual(env['PATH'].split(os.pathsep,1)[1],os.environ.get('PATH',''))

    def test_home_gate_preserves_arguments_environment_and_selected_shared_pair(self):
        selected={**self.selection,'sharedProfile':self.after};self.deploy.atomic(self.deploy.DATA/'desktop.json',selected)
        home=load('authored_managed_home',ROOT/'scripts/home-launch.py')
        with patch.dict(os.environ,{'RESONANT_VOICE_HOME':'/authored/keep-voice','AUTHORED_HOME_OPTION':'keep'}),patch.object(home.os,'execve') as execute:
            home.main(['--background'])
        command=execute.call_args.args
        self.assertEqual(command[0],selected['python']);self.assertEqual(command[1][-3:],['-m','augmentor_linux.home_tray','--background'])
        self.assertEqual(command[2]['AUGMENTOR_SHARED_STATE'],self.after['state']);self.assertEqual(command[2]['AUGMENTOR_SHARED_DATA'],self.after['data'])
        self.assertEqual(command[2]['RESONANT_VOICE_HOME'],'/authored/keep-voice');self.assertEqual(command[2]['AUTHORED_HOME_OPTION'],'keep')
        self.assertEqual(command[2]['PYTHONPATH'],str(Path(selected['root'])/'apps/native'))
        (self.deploy.DATA/'dsh-preservation.json').write_text('AUTHORED PENDING')
        with patch.object(home,'run') as run:
            with self.assertRaisesRegex(ValueError,'requires recovery'):home.main(['--background'])
        run.assert_not_called()

    def test_explicit_legacy_alias_adoption_uses_stable_gated_helpers(self):
        startup=load('authored_alias_startup',ROOT/'scripts/install-desktop-startup.py')
        binary=self.home/'.local/bin';binary.mkdir(parents=True,mode=0o700)
        aliases={}
        for name in ('augmentor-mobile','augmentor-browser-host'):
            path=binary/name;path.write_text('# AUTHORED OLD '+name+'\n');path.chmod(0o700);aliases[name]=hashlib.sha256(path.read_bytes()).hexdigest()
        before={p:p.read_bytes() for p in binary.iterdir()}
        plan=startup.startup_plan(self.release,self.selection['python'],self.selection['node'],adopt_aliases=aliases)
        self.assertEqual({p:p.read_bytes() for p in binary.iterdir()},before)
        self.assertEqual(plan['files'][binary/'augmentor-mobile'],plan['files'][binary/'augmentor-mobile-managed'])
        self.assertIn(str(self.deploy.DATA/'desktop-browser-launch.py'),plan['files'][binary/'augmentor-browser-host'])
        self.assertTrue(all(plan['expectations'][binary/n]==h for n,h in aliases.items()))
        self.assertIn(self.deploy.DATA/'home-launch.py',plan['files'])
        ordinary=startup.startup_plan(self.release,self.selection['python'],self.selection['node'])
        self.assertNotIn(binary/'augmentor-mobile',ordinary['files']);self.assertNotIn(binary/'augmentor-browser-host',ordinary['files'])

    def test_legacy_alias_hashes_refuse_foreign_edits_before_any_install(self):
        startup=load('authored_stale_alias_startup',ROOT/'scripts/install-desktop-startup.py')
        binary=self.home/'.local/bin';binary.mkdir(parents=True,mode=0o700)
        path=binary/'augmentor-mobile';path.write_text('AUTHORED CURRENT KEEP');path.chmod(0o700)
        with self.assertRaisesRegex(ValueError,'alias changed'):
            startup.startup_plan(self.release,self.selection['python'],self.selection['node'],adopt_aliases={'augmentor-mobile':'0'*64})
        self.assertEqual(path.read_text(),'AUTHORED CURRENT KEEP')
        with self.assertRaisesRegex(ValueError,'only explicitly reviewed'):
            startup.startup_plan(self.release,self.selection['python'],self.selection['node'],adopt_aliases={'augmentor-stack':None})

    def test_actual_legacy_aliases_keep_arguments_node_path_and_refuse_a_pending_cut(self):
        startup=load('authored_real_alias_startup',ROOT/'scripts/install-desktop-startup.py')
        selected={**self.selection,'sharedProfile':self.after};self.deploy.atomic(self.deploy.DATA/'desktop.json',selected)
        startup.install(self.release,selected['python'],selected['node'],enable=False,
                        adopt_aliases={'augmentor-mobile':None,'augmentor-browser-host':None})
        binary=self.home/'.local/bin'
        env={**os.environ,'AUTHORED_VOICE_KEEP':'keep','NODE_OPTIONS':'--require /authored-never-load','NODE_PATH':'/authored-never-load'}
        run=subprocess.run([str(binary/'augmentor-browser-host'),'chrome-extension://authored/','--authored'],env=env,capture_output=True,text=True,check=True)
        value=json.loads(run.stdout);self.assertEqual(value['argv'],['chrome-extension://authored/','--authored'])
        self.assertEqual(value['shared'],self.after['data']);self.assertEqual(value['state'],self.after['state']);self.assertEqual(value['telemetry'],'0');self.assertIsNone(value['options'])
        run=subprocess.run([str(binary/'augmentor-mobile'),'--origin','https://authored.invalid','--preview'],env=env,capture_output=True,text=True,check=True)
        value=json.loads(run.stdout);self.assertEqual(value['argv'],['--origin','https://authored.invalid','--preview'])
        self.assertEqual(value['node'],selected['node']);self.assertEqual(value['shared'],self.after['data']);self.assertEqual(value['voice'],'keep')
        (self.deploy.DATA/'dsh-preservation.json').write_text('AUTHORED PENDING CUT')
        for name in ('augmentor-mobile','augmentor-browser-host'):
            run=subprocess.run([str(binary/name)],env=env,capture_output=True,text=True)
            self.assertNotEqual(run.returncode,0);self.assertEqual(run.stdout,'');self.assertIn('requires recovery',run.stderr)

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

    def test_pending_preservation_fence_blocks_build_and_binding_selection_before_preflight(self):
        self.deploy.atomic(self.deploy.DATA/'desktop.json',{**self.selection,'sharedProfile':self.after})
        before=(self.deploy.DATA/'desktop.json').read_bytes()
        self.deploy.atomic(self.deploy.DATA/'desktop.previous.json',{**self.selection,'sharedProfile':self.before})
        binding=self.binding(self.after,self.before)
        fence=self.deploy.DATA/self.shared.PRESERVATION_FENCE
        fence.write_bytes(b'{"authored":"PRIVATE_UNFINISHED_UPDATE"}');fence.chmod(0o600)
        self.check.stop()
        with patch.object(self.deploy,'check') as preflight:
            installer=load('authored_fenced_installer',ROOT/'scripts/install-desktop-startup.py')
            for operation in (lambda:self.deploy.activate(self.release),lambda:self.deploy.rollback(),
                              lambda:self.deploy.activate(self.release,binding),
                              lambda:self.deploy.rollback(binding),
                              lambda:installer.install(self.release,Path(sys.executable),Path(self.selection['node']),enable=False)):
                with self.assertRaisesRegex(ValueError,'requires recovery'):operation()
            preflight.assert_not_called()
        self.check.start()
        self.assertEqual((self.deploy.DATA/'desktop.json').read_bytes(),before)
        self.assertIn(b'PRIVATE_UNFINISHED_UPDATE',fence.read_bytes())

    def test_ordinary_build_selection_shares_existing_readers_but_refuses_maintenance_writer(self):
        with self.shared.launch_lease(self.deploy.DATA):self.deploy.activate(self.release)
        raw=(self.deploy.DATA/'desktop.json').read_bytes()
        with self.shared.launch_lease(self.deploy.DATA,exclusive=True):
            with self.assertRaisesRegex(ValueError,'managed client is active'):self.deploy.activate(self.release)
            with self.assertRaisesRegex(ValueError,'managed client is active'):self.deploy.rollback()
        self.assertEqual((self.deploy.DATA/'desktop.json').read_bytes(),raw)

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

    def test_startup_plan_renders_without_backups_file_writes_or_service_commands(self):
        installer=load('authored_pure_startup_plan',ROOT/'scripts/install-desktop-startup.py')
        before={str(p):p.read_bytes() for p in self.home.rglob('*') if p.is_file()}
        with patch.object(Path,'home',return_value=self.home),patch.object(installer,'_directory',side_effect=AssertionError('directory write')),patch.object(installer.subprocess,'run',side_effect=AssertionError('service command')):
            plan=installer.startup_plan(self.release,Path(sys.executable),Path(self.selection['node']))
        self.assertEqual(plan['manifest'],self.selection)
        self.assertIn(self.deploy.DATA/'desktop-launch.py',plan['files'])
        self.assertEqual({str(p):p.read_bytes() for p in self.home.rglob('*') if p.is_file()},before)

    def test_future_startup_plan_does_not_bypass_normal_installer_selection_guard(self):
        installer=load('authored_future_startup_plan',ROOT/'scripts/install-desktop-startup.py')
        descriptor=self.deploy.DATA/'desktop.json';before=descriptor.read_bytes()
        prospective={**self.selection,'root':str(self.home/'next-candidate'),'releaseId':'authored-next'}
        native=Path(prospective['root'])/'apps/native/augmentor_linux';native.mkdir(parents=True)
        (native/'window.py').write_text('# AUTHORED --ensure-running\n')
        product=Path(prospective['root'])/'release/product.json';product.parent.mkdir();product.write_text('{"version":"authored"}')
        with patch.object(Path,'home',return_value=self.home):
            plan=installer.startup_plan(Path(prospective['root']),Path(sys.executable),Path(self.selection['node']),selection=prospective)
            self.assertEqual(plan['manifest'],prospective)
            with self.assertRaisesRegex(ValueError,'managed release is selected'):
                installer.install(Path(prospective['root']),Path(sys.executable),Path(self.selection['node']),enable=False)
        self.assertEqual(descriptor.read_bytes(),before)

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
