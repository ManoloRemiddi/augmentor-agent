# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual owned unit/harness files; explicit simulated systemd/peer observations."""
import json
from contextlib import nullcontext
import hashlib
import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import Mock,patch

import test_update_linux_registration as fixtures
from updates.linux_services import OwnedServicePlan,render,UNIT,PROPERTIES
from updates.linux_desktop import OwnedDesktopPlan,render as desktop_unit
from updates.linux_managed import ManagedPlan,load_deployment
from updates.linux_coordinator import LinuxCoordinator
from lifecycle.posix_startup import Startup
from lifecycle.update_journal import UpdateJournal
from platform_adapters.private_files import atomic_json,read_json


@unittest.skipUnless(sys.platform=='linux','Owned Linux user-service migration.')
class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.RegistrationTests('runTest');self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups);f=self.fixture
        self.config=f.base/'config';self.state=f.base/'state'
        for path in (self.config/'systemd/user',self.config/'augmentor',self.state/'augmentor-install'):
            path.mkdir(parents=True,mode=0o700)
        for path in (self.config,self.config/'systemd',self.state):path.chmod(0o700)
        self.credentials=self.state/'augmentor-install/model.env'
        self.credentials.write_bytes(b'FIXTURE_SECRET=preserve-exactly\n');self.credentials.chmod(0o600)
        self.previous={'root':str(f.source),'node':str(f.source/'node/bin/node'),'dshService':UNIT,
            'dshHome':str(f.home),'dshEndpoint':'http://127.0.0.1:3080','version':'1.0.0'}
        self.proposed={**self.previous,'root':str(f.target),'node':str(f.target/'node/bin/node'),'version':'2.0.0'}
        self.unit=self.config/'systemd/user'/UNIT
        self.before_unit=render(self.previous['node'],f.source/'dsh/node_modules/@deepseek-ai/dsh/lib/bin.js',
            f.home,self.credentials,3080)
        self.unit.write_bytes(self.before_unit);self.unit.chmod(0o600)
        self.harnesses=self.config/'augmentor/harnesses.json'
        self.saved={'default':'dsh','pi':{'fixtureChoice':'preserve'},
            'dsh':{'endpoint':self.previous['dshEndpoint'],'home':str(f.home),'version':'1.0.0','extra':'preserve'}}
        atomic_json(self.harnesses,self.saved)
        self.report={'Id':UNIT,'LoadState':'loaded','FragmentPath':str(self.unit),'DropInPaths':'',
            'ActiveState':'active','SubState':'running','MainPID':'123','Result':'success',
            'UnitFileState':'enabled','NeedDaemonReload':'no'}
        self.env=patch.dict(os.environ,{'XDG_CONFIG_HOME':str(self.config),'XDG_STATE_HOME':str(self.state),
            'AUGMENTOR_SHARED_CONFIG':str(self.config/'augmentor')});self.env.start();self.addCleanup(self.env.stop)

    def plan(self,*,bind=True):
        registration=self.fixture.plan(bind=False)
        with patch.object(OwnedServicePlan,'query',return_value=self.report.copy()):
            service=OwnedServicePlan(registration,self.previous,self.proposed)
        if bind:registration.bind_artifacts(self.fixture.before,self.fixture.after)
        return registration,service

    def inactive(self):return {**self.report,'ActiveState':'inactive','SubState':'dead','MainPID':'0'}

    def bind_and_drain(self,service):
        process=Mock(pid=123,closed=False);process.exited.return_value=False
        preparation=SimpleNamespace(root=self.fixture.source,dsh=[SimpleNamespace(process=process)])
        with patch.object(service,'query',return_value=self.report.copy()):service.bind(preparation)
        process.exited.return_value=True
        with patch.object(service,'query',return_value=self.inactive()):service.require_drained()
        return process

    def test_original_exit_migrates_unit_and_shared_version_preserves_credentials_enablement_and_other_harnesses(self):
        registration,service=self.plan();self.bind_and_drain(service);f=self.fixture
        with UpdateJournal(f.transactions,f.before,f.after) as journal,Startup(
                f.runtime,maintenance=True,transactions=f.transactions) as gate:
            f.intent(journal);registration.apply(gate,journal)
            with patch.object(service,'query',return_value=self.inactive()),patch('updates.linux_services.subprocess.run') as run:
                service.reload(gate,journal);self.assertTrue(service.verify_applied())
                self.assertEqual(run.call_count,1)
                self.assertEqual(run.call_args.args[0],['/usr/bin/systemctl','--user','daemon-reload'])
            updated=read_json(self.harnesses)
            self.assertEqual(updated,{**self.saved,'dsh':{**self.saved['dsh'],'version':'2.0.0'}})
            self.assertEqual(self.unit.read_bytes(),render(self.proposed['node'],
                f.target/'dsh/node_modules/@deepseek-ai/dsh/lib/bin.js',f.home,self.credentials,3080))
            manifest=read_json(registration.backup/'manifest.json')
            records={row['name']:row for row in manifest['files']}
            self.assertEqual((registration.backup/records['user-service/'+UNIT]['backup']).read_bytes(),self.before_unit)
            self.assertEqual(self.credentials.read_bytes(),b'FIXTURE_SECRET=preserve-exactly\n')
        f.sentinels_preserved()

    def test_custom_unit_or_dropin_refuses_without_writes(self):
        self.unit.write_bytes(self.before_unit+b'Environment=USER_CUSTOM_CHOICE=1\n')
        with self.assertRaisesRegex(ValueError,'customized'):self.plan()
        self.unit.write_bytes(self.before_unit);self.report['DropInPaths']='/fixture/custom.conf'
        with self.assertRaisesRegex(ValueError,'drop-ins'):self.plan()
        self.assertEqual(read_json(self.harnesses),self.saved)

    def test_redirected_config_or_changed_harness_identity_refuses(self):
        other=self.fixture.base/'other-config';other.mkdir(mode=0o700)
        with patch.dict(os.environ,{'XDG_CONFIG_HOME':str(other)}):
            with self.assertRaises(FileNotFoundError):self.plan()
        atomic_json(self.harnesses,{**self.saved,'dsh':{**self.saved['dsh'],'home':'/fixture/other'}})
        with self.assertRaisesRegex(ValueError,'shared DSH'):self.plan()

    def test_live_mainpid_must_match_actual_reserved_peer(self):
        _,service=self.plan();process=Mock(pid=456,closed=False);process.exited.return_value=False
        preparation=SimpleNamespace(root=self.fixture.source,dsh=[SimpleNamespace(process=process)])
        with patch.object(service,'query',return_value=self.report.copy()):
            with self.assertRaisesRegex(ValueError,'actual original socket peer'):service.bind(preparation)
        self.assertFalse(service.bound);self.assertEqual(self.unit.read_bytes(),self.before_unit)

    def test_changed_live_service_is_refused_during_publisher_revalidation_before_drain(self):
        _,service=self.plan()
        with patch.object(service,'query',return_value={**self.report,'MainPID':'456'}):
            with self.assertRaisesRegex(ValueError,'changed after preflight'):service.validate_preparation()
        self.assertFalse(service.bound);self.assertFalse(service.drained)
        self.assertEqual(self.unit.read_bytes(),self.before_unit)

    def test_restart_failed_exit_and_changed_enablement_block_apply(self):
        for changes in ({'MainPID':'456'},{'Result':'exit-code'},{'UnitFileState':'disabled'}):
            with self.subTest(changes=changes):
                _,service=self.plan();process=Mock(pid=123,closed=False);process.exited.return_value=False
                preparation=SimpleNamespace(root=self.fixture.source,dsh=[SimpleNamespace(process=process)])
                with patch.object(service,'query',return_value=self.report.copy()):service.bind(preparation)
                process.exited.return_value=True
                with patch.object(service,'query',return_value={**self.inactive(),**changes}):
                    with self.assertRaises(ValueError):service.require_drained()
                self.assertFalse(service.drained)

    def test_failed_reload_is_not_replayed_and_leaves_pending_exact_backups(self):
        registration,service=self.plan();self.bind_and_drain(service);f=self.fixture
        with UpdateJournal(f.transactions,f.before,f.after) as journal,Startup(
                f.runtime,maintenance=True,transactions=f.transactions) as gate:
            f.intent(journal);registration.apply(gate,journal)
            with patch.object(service,'query',return_value=self.inactive()),patch(
                    'updates.linux_services.subprocess.run',side_effect=OSError('Synthetic daemon failure.')) as run:
                with self.assertRaisesRegex(OSError,'daemon failure'):service.reload(gate,journal)
                with self.assertRaisesRegex(ValueError,'original drained'):service.reload(gate,journal)
                self.assertEqual(run.call_count,1)
            with self.assertRaisesRegex(ValueError,'not acknowledged'):service.verify_applied()
            self.assertTrue(registration.verify_applied())
        self.assertTrue((f.transactions/'active.json').exists())

    def test_query_rejects_missing_duplicate_or_unknown_properties(self):
        _,service=self.plan()
        report=''.join(key+'='+self.report[key]+'\n' for key in PROPERTIES)
        for raw in (report+'Id='+UNIT+'\n',report+'Unknown=1\n',report.replace('Result=success\n','')):
            with patch('updates.linux_services.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout=raw.encode())):
                with self.assertRaises(ValueError):service.query()

    def test_unit_matches_actual_complete_installer_field_grammar(self):
        path=fixtures.ROOT/'scripts/setup-complete.py'
        spec=importlib.util.spec_from_file_location('augmentor_complete_service_fixture',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        node='/fixture space/100%/node';cli='/fixture "quoted"/bin.js'
        command=[node,cli,'web','--no-open','--host','127.0.0.1','--port','3080']
        self.assertEqual(render(node,cli,self.fixture.home,self.credentials,3080),
            module.service(command,self.fixture.home,self.credentials).encode())

    def test_service_migration_composes_with_original_managed_pointer_and_completion(self):
        self.completed_scene()

    def completed_scene(self,exercise=None,*,desktop=False):
        f=self.fixture;data=f.base/'data/augmentor';data.mkdir(parents=True,mode=0o700);data.parent.chmod(0o700)
        self.env_data=patch.dict(os.environ,{'XDG_DATA_HOME':str(data.parent)})
        self.env_data.start();self.addCleanup(self.env_data.stop)
        tool=load_deployment(data);tool.check=Mock()
        configs=[]
        for root,config,version,commit in ((f.source,self.previous,'1.0.0','a'*40),
                (f.target,self.proposed,'2.0.0','c'*40)):
            (root/'apps/native/augmentor_linux').mkdir(parents=True)
            (root/'apps/native/augmentor_linux/window.py').write_text('--ensure-running')
            (root/'release').mkdir()
            product={'version':version,'channel':'preview','protocols':{'product':'augmentor/1'},
                'dataSchema':1,'readableDataSchemas':[1]}
            (root/'release/product.json').write_text(json.dumps(product))
            (root/'release.json').write_text(json.dumps({**product,'target':'linux-x64','sourceCommit':commit,
                'component':'desktop','update':{'build':1,'automaticInstallQualified':False}}))
            if desktop:
                (root/'scripts').mkdir()
                (root/'scripts/desktop-launch.py').write_bytes((fixtures.ROOT/'scripts/desktop-launch.py').read_bytes()+
                    (b'\n# Synthetic target release.\n' if root==f.target else b''))
            files=tool.inventory(root);digest=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()
            config={**config,'python':sys.executable,'releaseId':'fixture-'+version,'sourceRef':commit,'artifactSha256':digest}
            tool.atomic(root/'desktop-release.json',{'deployment':config,'files':files,'artifactSha256':digest})
            configs.append(config)
        atomic_json(data/'desktop.json',configs[0]);registration,service=self.plan(bind=False)
        state=self.report.copy();test=self;desktop_plan=None;desktop_state=None
        if desktop:
            launcher=data/'desktop-launch.py';launcher.write_bytes((f.source/'scripts/desktop-launch.py').read_bytes());launcher.chmod(0o600)
            unit=self.config/'systemd/user/augmentor-desktop.service';unit.write_bytes(desktop_unit(launcher));unit.chmod(0o600)
            desktop_state={**state,'Id':'augmentor-desktop.service','FragmentPath':str(unit),'MainPID':'234','UnitFileState':'disabled'}
            with patch.object(OwnedDesktopPlan,'query',return_value=desktop_state.copy()):
                desktop_plan=OwnedDesktopPlan(registration,data)
        # Explicitly simulated graph/process/systemd actions; selection, barriers,
        # journal, registration backups and completion archive are actual files.
        class Graph:
            def __init__(self,root,runtime,shared,*,transactions,captured,services,desktop=None):
                self.root=root;self.runtime=runtime;self.transactions=transactions;self.captured=captured
                process=Mock(pid=123,closed=False);process.exited.return_value=False
                self.dsh=[SimpleNamespace(process=process,pid=123)]
                self.windows=[]
                if desktop is not None:
                    for name,pid in (('',234),('-secondary',235)):
                        peer=Mock(pid=pid,closed=False);peer.exited.return_value=False
                        self.windows.append(SimpleNamespace(process=peer,pid=pid,endpoint=runtime/('augmentor-linux-pi'+name+'.sock')))
                self.desktop=desktop
            def __enter__(self):
                self.gate=Startup(self.runtime,maintenance=True,transactions=self.transactions)
                service.bind(self)
                if self.desktop is not None:self.desktop.bind(self)
                self.captured(self.reopen_plan());return self
            def reopen_plan(self):
                return {'instances':['main','secondary'] if self.desktop is not None else [],'hadBrowser':False}
            def check(self):test.assertIsNotNone(self.gate.fd)
            def drain(self,*,checkpoint):
                for window in self.windows:
                    checkpoint('commit-intent',window);checkpoint('commit-acknowledged',window)
                    window.process.exited.return_value=True;checkpoint('exited',window)
                if desktop_state is not None:desktop_state.update(ActiveState='inactive',SubState='dead',MainPID='0')
                participant=self.dsh[0]
                checkpoint('commit-intent',participant);checkpoint('commit-acknowledged',participant)
                participant.process.exited.return_value=True
                state.update(test.inactive());checkpoint('exited',participant)
            def __exit__(self,*args):
                for window in self.windows:window.process.closed=True
                self.dsh[0].process.closed=True;self.gate.close()
        with patch('updates.linux_managed.load_deployment',return_value=tool),patch(
                'updates.linux_completion.verify_health',return_value=True),patch(
                'updates.linux_coordinator.CapturedPreparation',Graph),patch.object(
                service,'query',side_effect=lambda:state.copy()),(patch.object(desktop_plan,'query',side_effect=lambda:desktop_state.copy())
                    if desktop_plan is not None else nullcontext()),patch('updates.linux_services.subprocess.run') as run:
            with ManagedPlan(data,f.source,f.target,development=True,registration=registration) as plan:
                plan.services=service;plan.desktop=desktop_plan
                coordinator=LinuxCoordinator(plan,f.runtime,f.runtime/'shared',f.transactions)
                result=coordinator.run(lambda stage:True)
                self.assertTrue(result['installationComplete']);self.assertTrue(service.verify_applied())
                self.assertEqual(read_json(data/'desktop.json'),configs[1])
                self.assertEqual(read_json(data/'desktop.previous.json'),configs[0])
                self.assertEqual(read_json(Path(result['archive']))['phase'],'complete')
                self.assertFalse((f.transactions/'active.json').exists());self.assertEqual(run.call_count,1)
                if exercise is not None:exercise(coordinator,result,state,run)
                if desktop_plan is not None:
                    self.assertEqual(desktop_state['UnitFileState'],'disabled')
                    self.assertEqual(desktop_plan.launcher.read_bytes(),(f.target/'scripts/desktop-launch.py').read_bytes())
        f.sentinels_preserved();self.assertEqual(self.credentials.read_bytes(),b'FIXTURE_SECRET=preserve-exactly\n')
