// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {createServer} from 'node:http';import {mkdtempSync} from 'node:fs';import {tmpdir} from 'node:os';import {join} from 'node:path';
import {apply} from '../adapters/dsh-prompt-library/lib/index.js';import {promptCall} from '../dist/prompt-library/src/client.js';
test('DSH settings adapter and standalone clients share revisions, without another settings store',async t=>{
 const root=mkdtempSync(join(tmpdir(),'augmentor-dsh-prompts-'));process.env.AUGMENTOR_SHARED_STATE=join(root,'state');process.env.AUGMENTOR_SHARED_DATA=join(root,'data');
 const original=await promptCall('prompts.save',{name:'shared',content:'Initial [clipboard]'});const pid=(await promptCall('host.describe')).pid;t.after(()=>process.kill(pid));
 let handler;apply({effect:fn=>fn(),webServer:{register:route=>{handler=route.handler;return ()=>{}}}});
 const server=createServer((req,res)=>handler(req,res));await new Promise(r=>server.listen(0,'127.0.0.1',r));t.after(()=>server.close());
 const url='http://127.0.0.1:'+server.address().port;
 const call=async(value,origin=url)=>(await fetch(url,{method:'POST',headers:{'content-type':'application/json',origin},body:JSON.stringify(value)})).json();
 assert.deepEqual((await call({action:'list'})).library,original);
 const row=original.prompts[0];assert.equal((await call({action:'save',id:row.id,name:'renamed',content:'Changed',expectedRevision:row.revision})).ok,true);
 const current=await promptCall('prompts.list');assert.equal(current.prompts[0].id,row.id);assert.equal(current.prompts[0].name,'renamed');
 assert.equal((await call({action:'save',id:row.id,name:'shared',content:'Stale',expectedRevision:row.revision})).ok,false);
 assert.equal((await call({action:'list'},'https://foreign.example')).ok,false);
});
