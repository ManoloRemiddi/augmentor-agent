# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual CI-only systemd user unit, socket pidfd, drain and managed migration.

Requires the dedicated disposable CI account. The Node service is an inert
maintenance fixture. Imports/connection and offline target health are mocked;
service ownership, kernel observations, graph and files are actual.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import unittest
from unittest.mock import Mock,patch

import test_update_linux_registration as fixtures
from updates.linux_registration import RegistrationPlan
from updates.linux_services import OwnedServicePlan,render,UNIT
from updates.linux_managed import ManagedPlan,load_deployment
from updates.linux_coordinator import LinuxCoordinator
from updates.linux_reopen import reopen_dsh_observed
from platform_adapters.private_files import atomic_json,read_json

CONTROL="""// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {unixControl} from '../../../../../services/lifecycle/unix-control.mjs';
import {fileURLToPath} from 'node:url';
import {existsSync,lstatSync} from 'node:fs';
const runtime=process.env.XDG_RUNTIME_DIR,root=fileURLToPath(new URL('../../../../../',import.meta.url));
const folder=lstatSync(runtime);
if(!folder.isDirectory()||folder.uid!==process.getuid()||(folder.mode&0o077))
 console.error(JSON.stringify({schema:'augmentor-fixture-runtime-diagnostic/1',runtime,uid:process.getuid(),
  directoryUID:folder.uid,mode:folder.mode&0o777,directory:folder.isDirectory()}));
let token=null,closing=false;
const service=await unixControl({runtime,root,component:'dsh',control:(method,params)=>{
 const action=method.replace('host.maintenance.','');
 if(action==='prepare'){if(existsSync(runtime+'/busy')||token&&token!==params.token)throw Error('Busy fixture');token=params.token}
 else if(action!=='status'){
  if(params.token!==token)throw Error('Wrong original reservation');
  if(action==='cancel')token=null;
  else if(action==='commit')closing=true;
  else if(action!=='renew')throw Error('Unsupported fixture operation');
 }
 return {protocol:'augmentor-component-maintenance/1',phase:closing?'closing':token?'prepared':'ready',
  active:existsSync(runtime+'/busy')?1:0,expiresInSeconds:token&&!closing?30:null};
},onCommitted:()=>{void service.close()}});
"""


@unittest.skipUnless(sys.platform=='linux' and os.environ.get('AUGMENTOR_SYSTEMD_QUALIFICATION')=='1',
    'Requires the dedicated disposable Linux systemd CI user.')
class NativeServiceTests(unittest.TestCase):
    def systemctl(self,*arguments):
        return subprocess.run(['/usr/bin/systemctl','--user',*arguments],stdin=subprocess.DEVNULL,
            capture_output=True,check=True,timeout=20)

    def setUp(self):
        import pwd
        if os.environ.get('CI')!='true' or pwd.getpwuid(os.getuid()).pw_name!='augupdatefixture':
            self.fail('Native service qualification requires its dedicated disposable CI account.')
        f=fixtures.RegistrationTests('runTest');f.setUp();self.f=f;self.addCleanup(f.doCleanups)
        f.runtime=Path(os.environ['XDG_RUNTIME_DIR'])
        runtime=f.runtime.lstat()
        if (f.runtime!=Path('/run/user/'+str(os.getuid())) or f.runtime.resolve()!=f.runtime
                or runtime.st_uid!=os.getuid() or runtime.st_mode&0o077):
            self.fail('Use only this disposable account\'s actual private systemd runtime.')
        config=Path.home()/'.config';state=Path.home()/'.local/state'
        for path in (config/'systemd/user',config/'augmentor',state/'augmentor-install'):
            path.mkdir(parents=True,mode=0o700,exist_ok=True)
        for path in (config,config/'systemd',state):path.chmod(0o700)
        environment=patch.dict(os.environ,{'XDG_CONFIG_HOME':str(config),'XDG_STATE_HOME':str(state),
            'AUGMENTOR_SHARED_CONFIG':str(config/'augmentor')})
        environment.start();self.addCleanup(environment.stop)
        self.credentials=state/'augmentor-install/model.env'
        self.secret=b'FIXTURE_SECRET=preserve-exactly\n'+('XDG_RUNTIME_DIR="'+str(f.runtime)+'"\n').encode()
        self.credentials.write_bytes(self.secret);self.credentials.chmod(0o600)
        self.data=f.base/'data';self.data.mkdir(mode=0o700)
        self.tool=load_deployment(self.data);self.tool.check=Mock()
        node=Path(os.environ['AUGMENTOR_QUALIFICATION_NODE']).resolve()
        if not node.is_file():self.fail('The pinned qualification Node executable is absent.')
        self.configs=[]
        for root,version,commit in ((f.source,'1.0.0','a'*40),(f.target,'2.0.0','c'*40)):
            (root/'node/bin').mkdir(parents=True);shutil.copy2(node,root/'node/bin/node')
            cli=root/'dsh/node_modules/@deepseek-ai/dsh/lib/bin.js';cli.parent.mkdir(parents=True)
            cli.write_text(CONTROL)
            (cli.parent.parent/'package.json').write_text('{"type":"module"}\n')
            (root/'services/lifecycle').mkdir()
            shutil.copy2(fixtures.ROOT/'services/lifecycle/unix-control.mjs',root/'services/lifecycle/unix-control.mjs')
            (root/'apps/native/augmentor_linux').mkdir(parents=True)
            (root/'apps/native/augmentor_linux/window.py').write_text('--ensure-running')
            (root/'release').mkdir()
            product={'version':version,'channel':'preview','protocols':{'product':'augmentor/1'},
                'dataSchema':1,'readableDataSchemas':[1]}
            (root/'release/product.json').write_text(json.dumps(product))
            (root/'release.json').write_text(json.dumps({**product,'target':'linux-x64','sourceCommit':commit,
                'component':'desktop','update':{'build':1,'automaticInstallQualified':False}}))
            files=self.tool.inventory(root);digest=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()
            selected={'root':str(root),'node':str(root/'node/bin/node'),'python':sys.executable,'dshService':UNIT,
                'dshHome':str(f.home),'dshEndpoint':'http://127.0.0.1:3080','version':version,
                'releaseId':'fixture-'+version,'sourceRef':commit,'artifactSha256':digest}
            self.tool.atomic(root/'desktop-release.json',{'deployment':selected,'files':files,'artifactSha256':digest})
            self.configs.append(selected)
        atomic_json(self.data/'desktop.json',self.configs[0])
        self.harnesses=config/'augmentor/harnesses.json'
        self.saved={'default':'dsh','pi':{'fixtureChoice':'preserve'},'dsh':{
            'endpoint':self.configs[0]['dshEndpoint'],'home':str(f.home),'version':'1.0.0'}}
        atomic_json(self.harnesses,self.saved)
        self.unit=config/'systemd/user'/UNIT
        if self.unit.exists() or self.unit.is_symlink():self.fail('Never overwrite an existing service during qualification.')
        self.before_unit=render(self.configs[0]['node'],f.source/'dsh/node_modules/@deepseek-ai/dsh/lib/bin.js',
            f.home,self.credentials,3080)
        self.unit.write_bytes(self.before_unit);self.unit.chmod(0o600)
        def close_service():
            self.systemctl('stop',UNIT)
            self.unit.unlink();self.systemctl('daemon-reload')
        self.addCleanup(close_service)
        self.systemctl('daemon-reload');self.systemctl('start',UNIT)
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            if list(f.runtime.glob('augmentor-dsh-*.sock')):break
            time.sleep(.05)
        else:
            # Logs contain only this independently authored inert fixture.
            report=subprocess.run(['/usr/bin/journalctl','--user','-u',UNIT,'--no-pager','-n','30'],
                capture_output=True,text=True,timeout=10)
            self.fail('The actual fixture service did not register its socket. '+report.stdout)

    def plan(self):
        f=self.f;registration=RegistrationPlan(f.home,f.source,f.target,'1.0.0','2.0.0')
        service=OwnedServicePlan(registration,*self.configs)
        context=ManagedPlan(self.data,f.source,f.target,development=True,registration=registration)
        plan=context.__enter__();plan.services=service
        return plan,service

    def test_actual_busy_deferral_original_exit_unit_migration_and_completion(self):
        f=self.f;original_pid=None
        with patch('updates.linux_managed.load_deployment',return_value=self.tool),patch(
                'updates.linux_completion.verify_health',return_value=True):
            (f.runtime/'busy').write_bytes(b'Accepted inert fixture work.')
            plan,service=self.plan();original_pid=service.original['MainPID']
            try:
                with self.assertRaises(Exception) as refused:
                    LinuxCoordinator(plan,f.runtime,f.runtime/'shared',f.transactions).run(lambda stage:True)
                self.assertIsNotNone(getattr(refused.exception,'augmentor_preparation_cancelled',None))
                self.assertEqual(service.query()['MainPID'],original_pid)
                self.assertEqual(self.unit.read_bytes(),self.before_unit)
                self.assertEqual(read_json(self.data/'desktop.json'),self.configs[0])
                self.assertFalse((f.transactions/'active.json').exists())
            finally:plan.close()
            (f.runtime/'busy').unlink()
            plan,service=self.plan()
            try:
                coordinator=LinuxCoordinator(plan,f.runtime,f.runtime/'shared',f.transactions)
                result=coordinator.run(lambda stage:True)
                self.assertTrue(result['installationComplete']);self.assertTrue(service.bound)
                self.assertEqual(service.process.pid,int(original_pid))
                self.assertTrue(service.drained);self.assertTrue(service.verify_applied())
                state=service.query()
                self.assertEqual((state['ActiveState'],state['MainPID'],state['NeedDaemonReload']),('inactive','0','no'))
                self.assertEqual(state['UnitFileState'],'disabled')
                self.assertEqual(read_json(self.data/'desktop.json'),self.configs[1])
                self.assertEqual(read_json(self.data/'desktop.previous.json'),self.configs[0])
                self.assertEqual(read_json(self.harnesses),{**self.saved,'dsh':{**self.saved['dsh'],'version':'2.0.0'}})
                self.assertEqual(self.credentials.read_bytes(),self.secret)
                self.assertEqual(read_json(Path(result['archive']))['phase'],'complete')
                self.assertFalse((f.transactions/'active.json').exists());f.sentinels_preserved()
                with self.assertRaisesRegex(ValueError,'one-shot reopening'):
                    reopen_dsh_observed(coordinator.backend,{**result,'transactionId':'f'*48})
                before=plan.target/'apps/browser/plugin/dist/index.js';payload=before.read_bytes()
                before.write_bytes(b'Changed target before reopening.')
                with self.assertRaisesRegex(ValueError,'artifacts changed'):
                    reopen_dsh_observed(coordinator.backend,result)
                self.assertFalse(getattr(coordinator.backend,'service_reopening_started',False));before.write_bytes(payload)
                self.assertTrue(reopen_dsh_observed(coordinator.backend,result))
                current=service.query();service.verify_state(current,running=True)
                self.assertEqual(current['ActiveState'],'active')
                self.assertEqual(current['UnitFileState'],'disabled')
                with self.assertRaisesRegex(ValueError,'one-shot reopening'):reopen_dsh_observed(coordinator.backend,result)
                self.assertEqual(self.credentials.read_bytes(),self.secret);f.sentinels_preserved()
                print(json.dumps({'schema':'augmentor-native-linux-service-proof/1','busyDeferred':True,
                    'originalPeerBound':True,'normalExit':True,'unitMigrated':True,'daemonReloaded':True,
                    'selectionCompleted':True,'credentialsPreserved':True,'enablementPreserved':True,
                    'providerAndUiMocked':True,'serviceReopened':True,'windowsReopened':False}))
            finally:plan.close()


if __name__=='__main__':unittest.main()
