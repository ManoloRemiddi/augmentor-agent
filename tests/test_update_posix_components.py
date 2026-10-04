# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real Node Unix control and kernel-bound Python participants, inert data only."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'services'))
from lifecycle.posix_components import UnixParticipant,discover_sockets
from lifecycle.reservations import Reservations
from lifecycle.posix_preparation import PosixPreparation
from platform_adapters.paths import private_directory


@unittest.skipUnless(sys.platform in ('linux','darwin') and shutil.which('node'),'requires native Unix and Node')
class UnixControlTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='ac-');self.addCleanup(temporary.cleanup)
        self.root=private_directory(Path(temporary.name).resolve()/'p')
        self.sentinel=self.root/'retained.json';self.sentinel.write_bytes(b'Preserve fixture settings.');self.sentinel.chmod(0o600)
        source="""import {unixControl} from './services/lifecycle/unix-control.mjs';
import {existsSync} from 'node:fs';
const runtime=process.argv[1],root=process.argv[2];
let token=null,closing=false;
const control=await unixControl({runtime,root,component:'dsh',control:(method,params)=>{
 const action=method.replace('host.maintenance.','');
 if(action==='prepare'){if(existsSync(runtime+'/busy')||token&&token!==params.token)throw Error('Busy fixture');token=params.token}
 else if(action!=='status'){if(params.token!==token)throw Error('Wrong reservation');if(action==='cancel')token=null;else if(action==='commit')closing=true;else if(action!=='renew')throw Error('Unsupported')}
 return {protocol:'augmentor-component-maintenance/1',phase:closing?'closing':token?'prepared':'ready',active:existsSync(runtime+'/busy')?1:0,expiresInSeconds:token&&!closing?30:null};
},onCommitted:()=>{process.stdin.destroy();void control.close()}});
console.log(JSON.stringify({endpoint:control.endpoint,pid:process.pid}));
process.stdin.resume();process.stdin.once('end',()=>{void control.close()});
"""
        self.node=Path(shutil.which('node')).resolve()
        self.child=subprocess.Popen([str(self.node),'--input-type=module','-e',source,str(self.root),str(ROOT)],
            cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        def close():
            if self.child.stdin and not self.child.stdin.closed:self.child.stdin.close()
            self.child.stdin=None
            self.child.communicate(timeout=20)
        self.addCleanup(close)
        ready=self.child.stdout.readline()
        if not ready:self.fail(self.child.stderr.read())
        self.endpoint=Path(json.loads(ready)['endpoint'])

    def participant(self,root=ROOT):
        observed=UnixParticipant(self.endpoint,root,self.node,kind='dsh')
        self.addCleanup(observed.close)
        return observed

    def test_busy_prepare_and_cancel_preserve_data_and_original_process(self):
        observed=self.participant()
        (self.root/'busy').write_bytes(b'Accepted inert work.')
        with self.assertRaises(ValueError):
            with Reservations(keepalive=False) as group:group.prepare(observed)
        self.assertIsNone(self.child.poll())
        (self.root/'busy').unlink()
        with Reservations(keepalive=False) as group:
            group.prepare(observed)
            self.assertEqual(observed.control('status')['phase'],'prepared')
        self.assertEqual(observed.control('status')['phase'],'ready')
        self.assertEqual(self.sentinel.read_bytes(),b'Preserve fixture settings.')

    def test_commit_observes_original_process_exit_after_reply(self):
        observed=self.participant();steps=[]
        with Reservations(keepalive=False) as group:
            group.prepare(observed)
            group.commit(observed,checkpoint=lambda stage,item:steps.append((stage,item.pid)))
        self.assertEqual(self.child.wait(timeout=10),0)
        self.assertEqual(steps,[(stage,self.child.pid) for stage in ('commit-intent','commit-acknowledged','exited')])
        self.assertFalse(self.endpoint.exists())
        self.assertEqual(self.sentinel.read_bytes(),b'Preserve fixture settings.')

    def test_wrong_build_is_refused_without_stopping_node_or_deleting_endpoint(self):
        with self.assertRaises(ValueError):self.participant(self.root/'another-build')
        self.assertIsNone(self.child.poll());self.assertTrue(self.endpoint.exists())
        self.assertEqual(self.sentinel.read_bytes(),b'Preserve fixture settings.')

    def test_actual_graph_discovers_reserves_and_drains_node_with_startup_exclusion(self):
        steps=[]
        with PosixPreparation(ROOT,self.root,self.root/'shared') as graph:
            self.assertEqual([item.pid for item in graph.dsh],[self.child.pid])
            self.assertEqual(graph.reopen_plan(),{'instances':[],'hadBrowser':False})
            graph.drain(checkpoint=lambda stage,item:steps.append((stage,item.pid)))
        self.assertEqual(self.child.wait(timeout=10),0)
        self.assertEqual(steps,[(stage,self.child.pid) for stage in ('commit-intent','commit-acknowledged','exited')])
        self.assertEqual(self.sentinel.read_bytes(),b'Preserve fixture settings.')

    def test_busy_actual_graph_releases_startup_without_stopping_node(self):
        from lifecycle.posix_startup import Startup
        (self.root/'busy').write_bytes(b'Keep accepted fixture work.')
        graph=PosixPreparation(ROOT,self.root,self.root/'shared')
        with self.assertRaises(ValueError):graph.__enter__()
        self.assertTrue(graph.preparation_released)
        with Startup(self.root):pass
        self.assertIsNone(self.child.poll());self.assertTrue(self.endpoint.exists())


if __name__=='__main__':unittest.main()
