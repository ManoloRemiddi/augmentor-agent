// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';import http from 'node:http';
import {DshBoundary,loopbackEndpoint,boundedJson} from '../apps/browser/shared/dsh-boundary.mjs';
test('DSH browser boundary fixes the role and cwd, hides other chats and rejects broad methods',async()=>{
 const rows=[{sessionId:'os',agentPreset:'augmentor-linux-product'},{sessionId:'web',agentPreset:'augmentor-browser-product'}];
 const b=new DshBoundary(async()=>({items:rows}),async()=>({chatCwd:'/browser'}));
 assert.deepEqual(await b.guard('session.create',{sessionId:'new',cwd:'/private',agentPreset:'default'}),{sessionId:'new',cwd:'/browser',agentPreset:'augmentor-browser-product'});
 assert.deepEqual((await b.sessions()).items,[rows[1]]);
 for(const method of ['session.prompt','session.cancel','session.branch','session.history','session.rename','augmentor/save'])await assert.rejects(b.guard(method,{sessionId:'os'}),/another Augmentor role/);
 for(const method of ['workspace.create','session.delete','host.shutdown','updates/download','augmentor/update-plugin','augmentor/update-status','trace/fence-probe'])await assert.rejects(b.guard(method,{}),/unavailable/);
 assert.deepEqual(await b.guard('session.prompt',{sessionId:'web'}),{sessionId:'web'});
 rows[1].agentPreset='default';await assert.rejects(b.guard('session.prompt',{sessionId:'web'}),/another Augmentor role/);
 await assert.rejects(b.guard('settings.describe',{}),/Only Augmentor/);
 await assert.rejects(b.guard('settings.mutate',{ns:'permission',ops:[{op:'set',path:['overrides'],value:[]}]}),/Unsupported/);
 await assert.rejects(b.guard('settings.mutate',{ns:'permission',ops:[{op:'set',path:['defaultPreset'],value:'unknown'}]}),/Unsupported/);
 assert.equal((await b.guard('settings.mutate',{ns:'permission',ops:[{op:'set',path:['defaultPreset'],value:'read-only'}]})).ns,'permission');
});
test('DSH transport only contacts numeric loopback and refuses redirects and oversized replies',async t=>{
 for(const url of ['https://127.0.0.1','http://localhost:3080','http://127.0.0.1/path','http://user@127.0.0.1','http://127.0.0.1?key=secret','http://192.168.1.1'])assert.throws(()=>loopbackEndpoint(url));
 assert.equal(loopbackEndpoint('http://[::1]:3080/'),'http://[::1]:3080');
 let redirected=0;const server=http.createServer((req,res)=>{if(req.url==='/start'){res.writeHead(302,{location:'/destination'});res.end()}else{redirected++;res.end(JSON.stringify({value:'x'.repeat(100)}))}});await new Promise(r=>server.listen(0,'127.0.0.1',r));t.after(()=>server.close());const base='http://127.0.0.1:'+server.address().port;
 await assert.rejects(boundedJson(base+'/start'));assert.equal(redirected,0);
 await assert.rejects(boundedJson(base+'/big',{},50),/size limit/);
});
