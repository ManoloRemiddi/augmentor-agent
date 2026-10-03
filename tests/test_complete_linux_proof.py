# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Complete proof children must use the same verified loader contract as startup."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import socket
import copy
import hashlib
from contextlib import ExitStack
from types import ModuleType
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'services'))


def load(path):
    spec=importlib.util.spec_from_file_location(path.stem.replace('-','_'),path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


proof=load(ROOT/'release/prove-complete-linux.py')
runtime=load(ROOT/'scripts/linux-python-runtime.py')
source_qt=load(ROOT/'scripts/linux-source-qt.py')


class CompleteProofEnvironment(unittest.TestCase):
    def provider(self, app, python, profile, *, refused=None):
        (app/'linux-python-runtime.json').write_text('{}')
        spec=SimpleNamespace(loader=SimpleNamespace(exec_module=Mock()))
        from contextlib import ExitStack
        stack=ExitStack()
        stack.enter_context(patch.object(proof.importlib.util,'spec_from_file_location',return_value=spec))
        stack.enter_context(patch.object(proof.importlib.util,'module_from_spec',return_value=runtime))
        verified=stack.enter_context(patch.object(runtime,'resolve',return_value=str(python),side_effect=refused))
        stack.enter_context(patch.object(runtime,'policy',return_value={'profile':profile}))
        stack.enter_context(patch.object(runtime,'source_qt',return_value=source_qt))
        return stack,verified

    @unittest.skipUnless(sys.platform.startswith('linux') and shutil.which('cc'), 'ELF loader/compiler required')
    def test_source_contract_reaches_real_child_loader_and_inherited_worker_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            app=Path(directory)/'app';app.mkdir();root=Path(directory)/'runtime'
            python=root/'bin/python3';library=root/'qt/lib/libaugmentor_proof_fixture.so';library.parent.mkdir(parents=True)
            subprocess.run([shutil.which('cc'),'-shared','-fPIC','-x','c','-','-o',str(library)],
                           input='int augmentor_proof_fixture(void) { return 73; }',text=True,check=True,capture_output=True)
            child="import ctypes,json,os;print(json.dumps({'value':ctypes.CDLL('libaugmentor_proof_fixture.so').augmentor_proof_fixture(),'python':os.environ['AUGMENTOR_PYTHON'],'plugins':os.environ.get('QT_PLUGIN_PATH'),'foreignTheme':os.environ.get('QT_QPA_PLATFORMTHEME')}))"
            base={'PATH':os.defpath,'LD_LIBRARY_PATH':'/unreviewed/old/Qt','QT_QPA_PLATFORM':'offscreen',
                  'QT_QPA_PLATFORMTHEME':'foreign','QT_QPA_GENERIC_PLUGINS':'foreign'}
            with patch.dict(os.environ,base,clear=True):
                self.assertNotEqual(subprocess.run([sys.executable,'-c',child],capture_output=True).returncode,0)
                stack,verified=self.provider(app,python,runtime.SOURCE_PROFILE)
                with stack:
                    env=proof.selected_python_environment(app,python)
                    # No explicit env: this independently checks worker inheritance.
                    result=subprocess.run([sys.executable,'-c',child],text=True,capture_output=True,check=True)
                    verified.assert_called_once_with(app,str(python))
                answer=json.loads(result.stdout)
                self.assertEqual(answer['value'],73)
                self.assertEqual(answer['python'],str(python))
                self.assertEqual(answer['plugins'],str(root/'qt/plugins'))
                self.assertIsNone(answer['foreignTheme'])
                self.assertNotIn('QT_QPA_GENERIC_PLUGINS',os.environ)
                self.assertEqual(env['LD_LIBRARY_PATH'],str(root/'qt/lib'))
                self.assertEqual(env['QT_QPA_PLATFORM'],'offscreen')

    def test_native_system_runtime_keeps_default_loader_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            app=Path(directory);python=app/'runtime/bin/python3'
            base={'PATH':os.defpath,'QT_QPA_PLATFORM':'offscreen','HOME':directory}
            with patch.dict(os.environ,base,clear=True):
                stack,verified=self.provider(app,python,'leap16-cp313-x86_64-voice')
                with stack:env=proof.selected_python_environment(app,python)
                verified.assert_called_once_with(app,str(python))
                self.assertEqual(env,{**base,'AUGMENTOR_PYTHON':str(python)})
                self.assertEqual(dict(os.environ),env)
                self.assertNotIn('LD_LIBRARY_PATH',env)
                self.assertNotIn('QT_PLUGIN_PATH',env)

    def test_undeclared_legacy_runtime_keeps_inherited_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            app=Path(directory);python=app/'python/bin/python'
            base={'PATH':os.defpath,'QT_QPA_PLATFORM':'offscreen'}
            with patch.dict(os.environ,base,clear=True),patch.object(proof.importlib.util,'spec_from_file_location') as loader:
                env=proof.selected_python_environment(app,python)
                loader.assert_not_called();self.assertEqual(env,{**base,'AUGMENTOR_PYTHON':str(python)})

    def test_inventory_refusal_does_not_fall_back_or_modify_worker_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            app=Path(directory);python=app/'runtime/bin/python3';base={'PATH':os.defpath,'AUGMENTOR_PYTHON':'previous'}
            with patch.dict(os.environ,base,clear=True):
                stack,verified=self.provider(app,python,runtime.SOURCE_PROFILE,refused=ValueError('immutable inventory changed'))
                with stack,self.assertRaisesRegex(ValueError,'immutable inventory changed'):
                    proof.selected_python_environment(app,python)
                verified.assert_called_once_with(app,str(python));self.assertEqual(dict(os.environ),base)

    def test_source_preload_refusal_preserves_previous_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            app=Path(directory);python=app/'runtime/bin/python3';base={'PATH':os.defpath,'LD_PRELOAD':'/unreviewed/injection.so'}
            with patch.dict(os.environ,base,clear=True):
                stack,_=self.provider(app,python,runtime.SOURCE_PROFILE)
                with stack,self.assertRaisesRegex(ValueError,'preload/audit'):
                    proof.selected_python_environment(app,python)
                self.assertEqual(dict(os.environ),base)

    def test_dangling_policy_link_is_refused_instead_of_legacy_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            app=Path(directory);(app/'scripts').mkdir()
            shutil.copy2(ROOT/'scripts/linux-python-runtime.py',app/'scripts/linux-python-runtime.py')
            (app/'linux-python-runtime.json').symlink_to(app/'missing-policy.json')
            before=dict(os.environ)
            with self.assertRaisesRegex(ValueError,'regular artifact file'):
                proof.selected_python_environment(app,app/'python/bin/python3')
            self.assertEqual(dict(os.environ),before)


@unittest.skipUnless(sys.platform.startswith('linux'), 'Owned Linux post-install fixture')
class CompletePostInstallProof(unittest.TestCase):
    def fixture(self, root):
        home=root/'home';home.mkdir(mode=0o700)
        state=home/'.local/state/augmentor-install';state.mkdir(parents=True,mode=0o700)
        app=root/'app';app.mkdir();(home/'.local/share/augmentor/dsh-home').mkdir(parents=True)
        expected={}
        for name in proof.POST_SETTINGS:
            path=home/name;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text('independent immutable fixture settings: '+name);path.chmod(0o600)
            expected[name]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size}
        fixture={'sourceCommit':proof.POST_SOURCE,'artifactId':'explicit-test-artifact',
                 'bundleManifestSha256':'a'*64,'settings':expected,'modelApiPort':34187,'dshPort':39603}
        desktop={'python':str(root/'runtime/bin/python3'),'dshService':'augmentor-dsh.service'}
        return home,state,app,fixture,desktop

    def execution(self, directory, *, lost=False, stalled=False, changed=False, turn_stalled=False, host_delay=0):
        home,state,app,fixture,desktop=self.fixture(Path(directory));clock=SimpleNamespace(now=0.,host_reads=0)
        processes=[];mutations=[];requests=[];start_count=0
        histories={'prior':{'header':{'id':'prior'},'events':[{'type':'kept','value':73}]}}
        def process(*args,**kwargs):
            self.assertEqual(kwargs.get('cwd'),str(home))
            p=Mock();p.poll.return_value=None;p.wait.return_value=0;processes.append(p);return p
        def call(method,payload=None):
            payload=payload or {};sid=payload.get('sessionId')
            if method=='host.describe':
                clock.host_reads+=1
                if stalled:raise ValueError('not ready')
                clock.now+=host_delay
                return {}
            if method=='session.list':return {'items':[{'sessionId':key,'running':turn_stalled and key!='prior'} for key in histories]}
            if method=='session.history':
                result=copy.deepcopy(histories[sid])
                if len(processes)>1:
                    result['header']['delegationDepth']=0
                    if changed and sid=='prior':result['events'].append({'type':'unexpected'})
                return result
            mutations.append((method,sid))
            if method=='session.create':histories[sid]={'header':{'id':sid},'events':[]}
            if method=='session.prompt':
                requests.append({'session':sid})
                if not turn_stalled:histories[sid]['events'].append({'text':'LINUX DISTRO FIXTURE VERIFIED'})
                if lost:raise OSError('response lost after dispatch')
            return {}
        adapter=SimpleNamespace(product=True,call=call)
        server=Mock()
        def model_server(values,port):
            self.assertEqual(port,34187)
            def proxy_call(method,payload=None):
                before=len(requests);result=call(method,payload)
                if len(requests)>before:values.extend(requests[before:])
                return result
            adapter.call=proxy_call;return server
        def render(command,**kwargs):
            self.assertIn('--preview',command);self.assertEqual(kwargs['env']['QT_QPA_PLATFORM'],'offscreen')
            self.assertEqual(kwargs.get('cwd'),str(home))
            Path(command[-1]).write_bytes(b'owned synthetic render fixture'*400)
        fake=ModuleType('augmentor_linux.adapters.dsh');fake.DshAdapter=lambda:adapter
        stack=ExitStack();stack.enter_context(patch.dict(os.environ,{'PATH':os.defpath},clear=True))
        stack.enter_context(patch.object(proof,'POST_HOME',home));stack.enter_context(patch.object(proof,'POST_APP',app))
        stack.enter_context(patch.object(proof,'validate_post_fixture',return_value=({'artifactId':fixture['artifactId']},desktop,{'PATH':os.defpath})))
        stack.enter_context(patch.object(proof,'fixture_model_server',side_effect=model_server))
        stack.enter_context(patch.object(proof,'run',side_effect=render))
        stack.enter_context(patch.object(proof.threading,'Thread',return_value=Mock()))
        stack.enter_context(patch.object(proof.time,'monotonic',side_effect=lambda:clock.now))
        stack.enter_context(patch.object(proof.time,'sleep',side_effect=lambda amount:setattr(clock,'now',clock.now+amount)))
        stack.enter_context(patch.dict(sys.modules,{'augmentor_linux.adapters.dsh':fake}))
        stack.enter_context(patch('platform_adapters.processes.OwnedProcess',side_effect=process))
        return stack,home,state,fixture,desktop,clock,processes,mutations,server

    def test_post_install_preserves_settings_prior_history_and_restart_without_setup(self):
        with tempfile.TemporaryDirectory() as directory:
            stack,home,state,fixture,desktop,clock,processes,mutations,server=self.execution(directory)
            with stack:report=proof.post_install_proof(Path(directory)/'bound-bundle',fixture)
            self.assertFalse(report['setupReplayed']);self.assertFalse(report['originalFreshFullProofPass'])
            self.assertEqual(report['dshService'],'augmentor-dsh.service');self.assertEqual(report['modelRequests'],2)
            self.assertTrue(report['savedSettingsPreserved']);self.assertTrue(report['preexistingHistoriesPreserved'])
            self.assertEqual(len(processes),2)
            for p in processes:p.terminate.assert_called_once();p.close.assert_called_once()
            self.assertEqual(len([m for m,s in mutations if m=='session.prompt']),2)
            record=json.loads((state/'post-install-proof/run.json').read_text());self.assertEqual(record['status'],'complete')
            self.assertIsNone(record['pendingRequest']);self.assertTrue(record['settingsPreserved'])
            server.shutdown.assert_called_once();server.server_close.assert_called_once()

    def test_unknown_prompt_outcome_is_dispatched_once_and_owned_process_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            stack,home,state,fixture,desktop,clock,processes,mutations,server=self.execution(directory,lost=True)
            with stack,self.assertRaisesRegex(OSError,'response lost'):proof.post_install_proof(Path(directory),fixture)
            self.assertEqual([m for m,s in mutations].count('session.prompt'),1);self.assertEqual(len(processes),1)
            processes[0].terminate.assert_called_once();processes[0].close.assert_called_once()
            record=json.loads((state/'post-install-proof/run.json').read_text())
            self.assertTrue(record['unknownRequestOutcome']);self.assertEqual(record['pendingRequest']['method'],'session.prompt')
            self.assertEqual(record['status'],'failed');self.assertTrue(record['settingsPreserved'])
            with self.assertRaisesRegex(ValueError,'previous post-install proof'):proof.begin_post_run(state,fixture)

    def test_public60_second_readiness_limit_cleanup_and_no_request_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            stack,home,state,fixture,desktop,clock,processes,mutations,server=self.execution(directory,stalled=True)
            with stack,self.assertRaisesRegex(RuntimeError,'within60seconds'):proof.post_install_proof(Path(directory),fixture)
            self.assertGreaterEqual(clock.now,60);self.assertLess(clock.now,60.21)
            self.assertEqual(len(processes),1);self.assertEqual(mutations,[])
            processes[0].terminate.assert_called_once();processes[0].close.assert_called_once()
            self.assertEqual(json.loads((state/'post-install-proof/run.json').read_text())['status'],'failed')

    def test_failed_start_escalates_only_owned_process_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            stack,home,state,fixture,desktop,clock,processes,mutations,server=self.execution(directory,stalled=True)
            def owned_process(*args,**kwargs):
                p=Mock();p.poll.return_value=None
                p.wait.side_effect=[subprocess.TimeoutExpired('owned-fixture',15),0]
                processes.append(p);return p
            with stack,patch('platform_adapters.processes.OwnedProcess',side_effect=owned_process),\
                 self.assertRaisesRegex(RuntimeError,'within60seconds'):
                proof.post_install_proof(Path(directory),fixture)
            self.assertEqual(len(processes),1);self.assertEqual(mutations,[])
            processes[0].terminate.assert_called_once();processes[0].kill.assert_called_once();processes[0].close.assert_called_once()

    def test_restart_history_change_cannot_claim_preservation(self):
        with tempfile.TemporaryDirectory() as directory:
            stack,home,state,fixture,desktop,clock,processes,mutations,server=self.execution(directory,changed=True)
            with stack,self.assertRaisesRegex(ValueError,'Restart changed'):proof.post_install_proof(Path(directory),fixture)
            self.assertEqual(len(processes),2)
            for p in processes:p.terminate.assert_called_once();p.close.assert_called_once()
            record=json.loads((state/'post-install-proof/run.json').read_text());self.assertFalse(record['historyPreservedVerified'])

    def test_stale_journal_is_never_adopted_even_for_same_source(self):
        with tempfile.TemporaryDirectory() as directory:
            state=Path(directory);root,record=proof.begin_post_run(state,{'artifactId':'same','sourceCommit':proof.POST_SOURCE,'bundleManifestSha256':'a'*64})
            original=(root/'run.json').read_bytes()
            with self.assertRaisesRegex(ValueError,'previous post-install proof'):
                proof.begin_post_run(state,{'artifactId':'same','sourceCommit':proof.POST_SOURCE,'bundleManifestSha256':'a'*64})
            self.assertEqual((root/'run.json').read_bytes(),original)

    def test_explicit_cwd_v2_preserves_exact_pre_request_failed_run(self):
        with tempfile.TemporaryDirectory() as directory:
            state=Path(directory);old=state/'post-install-proof';old.mkdir(mode=0o700)
            fixture={'artifactId':'same','sourceCommit':proof.POST_SOURCE,'bundleManifestSha256':'a'*64,
                     'runDirectory':'post-install-proof-cwd-v2'}
            record={'format':'augmentor-owned-post-install-run/1','run':'1b8cb2ae536d0e6d979e89d15acf5cb1',
                    'artifactId':'same','sourceCommit':proof.POST_SOURCE,'bundleManifestSha256':'a'*64,
                    'proofScriptSha256':proof.POST_PRIOR_PROOF_SHA,'status':'failed','phase':'starting',
                    'pendingRequest':None,'unknownRequestOutcome':False,'settingsPreserved':True}
            raw=json.dumps(record).encode();path=old/'run.json';path.write_bytes(raw);path.chmod(0o600)
            digest=hashlib.sha256(raw).hexdigest();fixture['priorFailure']={'sha256':digest}
            with patch.object(proof,'POST_PRIOR_FAILURE_SHA',digest):
                root,new=proof.begin_post_run(state,fixture)
                self.assertEqual(root.name,'post-install-proof-cwd-v2');self.assertEqual(path.read_bytes(),raw)
                with self.assertRaisesRegex(ValueError,'previous post-install proof'):proof.begin_post_run(state,fixture)
                self.assertEqual(path.read_bytes(),raw)
            for key,value in [('pendingRequest',{'method':'session.prompt'}),('unknownRequestOutcome',True),
                              ('status','complete'),('phase','restart'),('settingsPreserved',False)]:
                altered={**record,key:value};changed=json.dumps(altered).encode();path.write_bytes(changed)
                changed_digest=hashlib.sha256(changed).hexdigest()
                with patch.object(proof,'POST_PRIOR_FAILURE_SHA',changed_digest),self.assertRaisesRegex(ValueError,'pre-request failure'):
                    proof.post_run_name(state,{**fixture,'priorFailure':{'sha256':changed_digest}})
            path.write_bytes(raw)
            with patch.object(proof,'POST_PRIOR_FAILURE_SHA',digest),self.assertRaisesRegex(ValueError,'binding differs'):
                proof.post_run_name(state,{**fixture,'runDirectory':'arbitrary-retry'})
            path.write_bytes(raw+b' ')
            with patch.object(proof,'POST_PRIOR_FAILURE_SHA',digest),self.assertRaisesRegex(ValueError,'record differs'):
                proof.post_run_name(state,fixture)

    def test_real_owned_child_cwd_is_explicit_and_parent_cwd_preserved(self):
        from platform_adapters.processes import OwnedProcess
        with tempfile.TemporaryDirectory() as directory:
            home=Path(directory)/'fresh';home.mkdir(mode=0o700)
            parent=Path.cwd()
            process=OwnedProcess([sys.executable,'-I','-c','import os; print(os.getcwd())'],
                                 cwd=str(home),stdout=subprocess.PIPE,text=True)
            try:
                self.assertEqual(process.process.stdout.read().strip(),str(home))
                self.assertEqual(process.wait(timeout=10),0)
            finally:
                process.close();process.process.stdout.close()
            self.assertEqual(Path.cwd(),parent)

    def v3_records(self, state, fixture):
        hashes={}
        for name in proof.POST_V3_PRIOR_SHA:
            root=state/name;root.mkdir(mode=0o700)
            if name in ('post-install-proof','post-install-proof-cwd-v2'):
                record={'format':'augmentor-owned-post-install-run/1','sourceCommit':proof.POST_SOURCE,
                        'artifactId':fixture['artifactId'],'bundleManifestSha256':fixture['bundleManifestSha256'],
                        'status':'failed','phase':'starting','pendingRequest':None,'unknownRequestOutcome':False,
                        'settingsPreserved':True}
            else:
                record={'installedSource':proof.POST_SOURCE,'SDKMutations':False,'phase':'observed',
                        'modelRequests':0,'providerHttpRequests':[],
                        'status':'failed' if name=='post-install-readiness-only-180-v1' else 'full-adapter-read-observed'}
            path=root/'run.json';raw=json.dumps(record).encode();path.write_bytes(raw);path.chmod(0o600)
            hashes[name]=hashlib.sha256(raw).hexdigest()
        fixture.update(runDirectory=proof.POST_V3_RUN,startupBudgetSeconds=120,priorFailures=hashes)
        return hashes

    def test_v3_success_records_explicit_emulated_budget_and_preserves_four_journals(self):
        with tempfile.TemporaryDirectory() as directory:
            stack,home,state,fixture,desktop,clock,processes,mutations,server=self.execution(directory)
            hashes=self.v3_records(state,fixture)
            originals={name:(state/name/'run.json').read_bytes() for name in hashes}
            with stack,patch.object(proof,'POST_V3_PRIOR_SHA',hashes):
                report=proof.post_install_proof(Path(directory),fixture)
                with self.assertRaisesRegex(ValueError,'previous post-install proof'):proof.begin_post_run(state,fixture)
            self.assertEqual(report['startupBudgetSeconds'],120);self.assertEqual(report['turnBudgetSeconds'],60)
            self.assertTrue(report['emulatedStartupQualification']);self.assertFalse(report['originalFreshFullProofPass'])
            self.assertFalse(report['public60SecondStartupProofPass'])
            self.assertEqual(report['priorRecordHashes'],hashes);self.assertEqual(report['modelRequests'],2)
            self.assertEqual(len(report['startupObservations']),2)
            self.assertEqual([method for method,sid in mutations].count('session.prompt'),2)
            for name,raw in originals.items():self.assertEqual((state/name/'run.json').read_bytes(),raw)
            record=json.loads((state/proof.POST_V3_RUN/'run.json').read_bytes())
            self.assertEqual(record['startupBudgetSeconds'],120);self.assertEqual(record['modelRequests'],2)

    def test_v3_stalled_start_uses120_only_and_sends_no_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            stack,home,state,fixture,desktop,clock,processes,mutations,server=self.execution(directory,stalled=True)
            hashes=self.v3_records(state,fixture)
            with stack,patch.object(proof,'POST_V3_PRIOR_SHA',hashes),self.assertRaisesRegex(RuntimeError,'within120seconds'):
                proof.post_install_proof(Path(directory),fixture)
            self.assertGreaterEqual(clock.now,120);self.assertLess(clock.now,120.21)
            self.assertEqual(mutations,[]);self.assertEqual(len(processes),1)
            processes[0].terminate.assert_called_once();processes[0].close.assert_called_once()
            record=json.loads((state/proof.POST_V3_RUN/'run.json').read_bytes())
            self.assertFalse(record['unknownRequestOutcome']);self.assertEqual(record['modelRequests'],0)
            self.assertEqual(record['startupObservations'][0]['ready'],False)

    def test_v3_slow_successful_read_crossing120_refuses_before_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            stack,home,state,fixture,desktop,clock,processes,mutations,server=self.execution(directory,host_delay=121)
            hashes=self.v3_records(state,fixture)
            with stack,patch.object(proof,'POST_V3_PRIOR_SHA',hashes),self.assertRaisesRegex(RuntimeError,'observed after120seconds'):
                proof.post_install_proof(Path(directory),fixture)
            self.assertEqual(clock.host_reads,1);self.assertEqual(clock.now,121)
            self.assertEqual(mutations,[]);self.assertEqual(len(processes),1)
            processes[0].terminate.assert_called_once();processes[0].close.assert_called_once()
            record=json.loads((state/proof.POST_V3_RUN/'run.json').read_bytes())
            self.assertFalse(record['unknownRequestOutcome']);self.assertEqual(record['modelRequests'],0)
            self.assertFalse(record['public60SecondStartupProofPass'])
            observation=record['startupObservations'][0]
            self.assertTrue(observation['readinessObserved']);self.assertFalse(observation['ready'])
            self.assertFalse(observation['withinBudget']);self.assertEqual(observation['elapsedSeconds'],121)

    def test_default_late_read_preserves_behavior_but_cannot_label60_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            stack,home,state,fixture,desktop,clock,processes,mutations,server=self.execution(directory,host_delay=61)
            with stack:report=proof.post_install_proof(Path(directory),fixture)
            self.assertEqual(report['status'],'pass');self.assertEqual(clock.host_reads,2)
            self.assertEqual([row['elapsedSeconds'] for row in report['startupObservations']],[61,61])
            self.assertFalse(report['public60SecondStartupProofPass'])
            self.assertFalse(json.loads((state/'post-install-proof/run.json').read_bytes())['public60SecondStartupProofPass'])

    def test_v3_role_turn_budget_remains60_not120(self):
        with tempfile.TemporaryDirectory() as directory:
            stack,home,state,fixture,desktop,clock,processes,mutations,server=self.execution(directory,turn_stalled=True)
            hashes=self.v3_records(state,fixture)
            with stack,patch.object(proof,'POST_V3_PRIOR_SHA',hashes),self.assertRaisesRegex(RuntimeError,'turn did not finish within60seconds'):
                proof.post_install_proof(Path(directory),fixture)
            self.assertGreaterEqual(clock.now,60);self.assertLess(clock.now,60.21)
            self.assertEqual([method for method,sid in mutations].count('session.prompt'),1)
            self.assertEqual(len(processes),1);processes[0].terminate.assert_called_once()

    def test_v3_refuses_altered_uncertain_or_incomplete_prior_records(self):
        with tempfile.TemporaryDirectory() as directory:
            state=Path(directory);fixture={'artifactId':'same','sourceCommit':proof.POST_SOURCE,'bundleManifestSha256':'a'*64}
            hashes=self.v3_records(state,fixture)
            with patch.object(proof,'POST_V3_PRIOR_SHA',hashes):
                proof.v3_prior_guard(state,fixture)
                with self.assertRaisesRegex(ValueError,'all four exact'):proof.v3_prior_guard(state,{**fixture,'priorFailures':{}})
                path=state/'post-install-proof/run.json';raw=path.read_bytes();path.write_bytes(raw+b' ')
                with self.assertRaisesRegex(ValueError,'record changed'):proof.v3_prior_guard(state,fixture)
                path.write_bytes(raw)
            for name,key,value in [('post-install-proof','pendingRequest',{'method':'session.prompt'}),
                                   ('post-install-proof-cwd-v2','unknownRequestOutcome',True),
                                   ('post-install-readiness-only-180-v1','SDKMutations',True),
                                   ('post-install-full-adapter-readiness-v1','modelRequests',1)]:
                path=state/name/'run.json';raw=path.read_bytes();record=json.loads(raw);record[key]=value
                changed=json.dumps(record).encode();path.write_bytes(changed)
                altered={**hashes,name:hashlib.sha256(changed).hexdigest()}
                with patch.object(proof,'POST_V3_PRIOR_SHA',altered),self.assertRaisesRegex(ValueError,'uncertain outcome'):
                    proof.v3_prior_guard(state,{**fixture,'priorFailures':altered})
                path.write_bytes(raw)
            for value in (60,180,120.0,True):
                with self.assertRaisesRegex(ValueError,'explicit emulated Mint v3'):
                    proof.post_startup_budget({**fixture,'startupBudgetSeconds':value})
            with self.assertRaisesRegex(ValueError,'explicit emulated Mint v3'):
                proof.post_startup_budget({'startupBudgetSeconds':120})
            self.assertEqual(proof.post_startup_budget({}),60)

    def test_v3_unknown_prompt_outcome_has_no_retry_or_adoption(self):
        with tempfile.TemporaryDirectory() as directory:
            stack,home,state,fixture,desktop,clock,processes,mutations,server=self.execution(directory,lost=True)
            hashes=self.v3_records(state,fixture)
            with stack,patch.object(proof,'POST_V3_PRIOR_SHA',hashes):
                with self.assertRaisesRegex(OSError,'response lost'):proof.post_install_proof(Path(directory),fixture)
                with self.assertRaisesRegex(ValueError,'previous post-install proof'):proof.begin_post_run(state,fixture)
            self.assertEqual([method for method,sid in mutations].count('session.prompt'),1)
            self.assertEqual(len(processes),1);processes[0].close.assert_called_once()
            record=json.loads((state/proof.POST_V3_RUN/'run.json').read_bytes())
            self.assertTrue(record['unknownRequestOutcome']);self.assertEqual(record['pendingRequest']['method'],'session.prompt')

    def test_bound_workspace_refuses_nonempty_extra_link_or_changed_state(self):
        with tempfile.TemporaryDirectory() as directory:
            home=Path(directory);(home/'storages').mkdir();p=home/'storages/workspace.json'
            p.write_text(json.dumps({'tables':{'workspaces':{}}}));p.chmod(0o600);digest=hashlib.sha256(p.read_bytes()).hexdigest()
            proof.empty_workspace_guard(home,digest)
            with self.assertRaisesRegex(ValueError,'workspace changed'):proof.empty_workspace_guard(home,'a'*64)
            p.write_text(json.dumps({'tables':{'workspaces':{'old':{}}}}))
            with self.assertRaisesRegex(ValueError,'Prior session'):proof.empty_workspace_guard(home,hashlib.sha256(p.read_bytes()).hexdigest())
            (home/'storages/foreign.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'Unexpected prior'):proof.empty_workspace_guard(home,digest)
            (home/'storages/foreign.json').unlink();p.unlink()
            target=home/'elsewhere.json';target.write_text('{}');p.symlink_to(target)
            with self.assertRaisesRegex(ValueError,'storage identity'):proof.empty_workspace_guard(home,digest)

    def test_occupied_port_is_refused_without_stopping_its_owner(self):
        with socket.socket() as owner:
            owner.bind(('127.0.0.1',0));number=owner.getsockname()[1]
            with self.assertRaises(OSError):proof.require_ports_idle([number])
            self.assertEqual(owner.getsockname()[1],number)

    def test_other_source_target_or_account_refuses_before_installed_source_load(self):
        base={'format':'augmentor-owned-mint-post-install/1','sourceCommit':proof.POST_SOURCE,'uid':1001,
              'user':'augmentor-complete-proof','home':str(proof.POST_HOME),'target':'linuxmint22.3-amd64',
              'markerSha256':hashlib.sha256(proof.POST_MARKER_TEXT.encode()).hexdigest()}
        for key,value in [('sourceCommit','f'*40),('uid',1000),('home','/home/owner'),('target','ubuntu24.04-amd64')]:
            with self.subTest(key=key),patch.object(proof,'proof_module') as loader,                 self.assertRaisesRegex(ValueError,'explicit owned clean2035'):
                proof.validate_post_fixture(Path('/unread'),{**base,key:value})
            loader.assert_not_called()


if __name__=='__main__':unittest.main()
