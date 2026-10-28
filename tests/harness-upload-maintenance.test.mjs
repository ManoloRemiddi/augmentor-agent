// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Actual public Pi Host/HTTP carriers; authored bytes, no provider request.
import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {readFile} from 'node:fs/promises';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {setTimeout as delay} from 'node:timers/promises';
import {PiConnection} from '../dist/client/src/socket.js';
import {localConnect} from '../dist/platform/src/transport.js';
const source=fileURLToPath(new URL('../',import.meta.url));
async function until(fn,label){const end=Date.now()+12000;let last;while(Date.now()<end){try{if(await fn())return;}catch(e){last=e;}await delay(20);}throw Error(label+(last?' ('+last.message+')':''));}
test('guarded real Host shutdown refuses slow/concurrent HTTP uploads, accepts abort settlement and never replays',{skip:process.platform!=='linux',timeout:60000},async t=>{
 let fixture,owner,link,output='',stderr='';const carriers=new Set();
 t.after(async()=>{for(const req of carriers)req.destroy();owner?.close();if(fixture?.pid&&fixture.exitCode===null){const ended=once(fixture,'exit');fixture.kill('SIGTERM');await ended;}});
 const env=Object.fromEntries(Object.entries(process.env).filter(([key])=>!/^(AUGMENTOR_|DSH_|PI_)/.test(key)));for(const key of ['AUGMENTOR_PI_TEST_ROOT','AUGMENTOR_PYTHON'])if(process.env[key])env[key]=process.env[key];
 fixture=spawn(process.execPath,[join(source,'scripts/harness-ui-proof.mjs')],{cwd:source,env:{...env,AUGMENTOR_HARNESS_PROOF_RECORD_REQUESTS:'1'},stdio:['ignore','pipe','pipe']});fixture.stdout.on('data',data=>output+=data);fixture.stderr.on('data',data=>stderr+=data);
 await until(()=>{assert.equal(fixture.exitCode,null,stderr);try{link=JSON.parse(output.trim().split('\n').find(x=>x.startsWith('{"fixture"')));return !!link;}catch{return false;}},'private fixture ready');
 const url=new URL(link.url),token=new URLSearchParams(url.hash.slice(1)).get('token');const socket=localConnect(join(link.state,'runtime.sock'));await once(socket,'connect');owner=new PiConnection(socket);await owner.call('host.hello',{protocol:'augmentor-pi/1'});
 const catalog=await owner.call('models.list'),sid=crypto.randomUUID();await owner.call('session.create',{sessionId:sid,cwd:link.workspace,selection:catalog.default});const history=await owner.call('session.history',{sessionId:sid});
 const receipts=async()=>JSON.parse(await readFile(join(link.state,'attachments','v1',sid+'.json'),'utf8').catch(error=>{if(error.code==='ENOENT')return '[]';throw error;}));
 const count=async()=> (await owner.call('host.describe')).activeUploads;
 const veto=async()=>{await assert.rejects(()=>owner.call('host.shutdown'),/Finish file uploads/);assert.equal((await owner.call('host.describe')).activeTurns,0);};
 // Fresh carriers avoid reusing a socket after deliberately incomplete/oversize input.
 const start=(name,length,extra={},bearer=token)=>{
  let resolve;const promise=new Promise(r=>resolve=r);const req=http.request(url.origin+'/api/attachments/upload?'+new URLSearchParams({sessionId:sid,name,...extra}),{method:'POST',agent:false,headers:{Authorization:'Bearer '+bearer,'Content-Type':'application/octet-stream',...(length===undefined?{'Transfer-Encoding':'chunked'}:{'Content-Length':length})}},async response=>{try{let raw='';for await(const chunk of response)raw+=chunk;resolve({status:response.statusCode,...(raw?{body:JSON.parse(raw)}:{})});}catch(error){resolve({error});}});req.on('error',error=>resolve({error}));carriers.add(req);req.once('close',()=>carriers.delete(req));req.flushHeaders();return {req,promise};
 };
 // Headers plus one byte are enough to reserve the entire body-reception phase.
 const bytes=Buffer.from('Independently authored slow draft file.');const slow=start('slow.txt',bytes.length);slow.req.write(bytes.subarray(0,1));await until(async()=>await count()===1,'body reception counted');assert.equal((await receipts()).length,0);await veto();slow.req.end(bytes.subarray(1));const result=await slow.promise;assert.equal(result.status,200,JSON.stringify(result));assert.equal(result.body.file.bytes,bytes.length);await until(async()=>await count()===0,'completed upload settled');assert.equal((await receipts()).length,1);
 // Each concurrent carrier owns one lease. Finishing one cannot release another.
 const complete=start('complete.txt',4),aborted=start('aborted.txt',12);complete.req.write('a');aborted.req.write('b');await until(async()=>await count()===2,'two independent carriers counted');await veto();complete.req.end('bcd');assert.equal((await complete.promise).status,200);await until(async()=>await count()===1,'only completed carrier released');await veto();aborted.req.destroy();await aborted.promise;await until(async()=>await count()===0,'aborted input released');assert.equal((await receipts()).length,2);
 // Bad media and announced oversize have no immutable receipt or retry.
 const invalid=start('bad.png',3,{mediaType:'invalid/type'});invalid.req.end('bad');assert.equal((await invalid.promise).status,400);await until(async()=>await count()===0,'failed processing released');const oversized=start('too-large.txt',20*1024*1024+1);oversized.req.end('x');assert.equal((await oversized.promise).status,400);assert.equal(await count(),0);assert.equal((await receipts()).length,2);
 const streamed=start('chunked-too-large.txt');streamed.req.write('x');await until(async()=>await count()===1,'unannounced stream protected');await veto();streamed.req.end(Buffer.alloc(20*1024*1024));const rejected=await streamed.promise;assert(rejected.status===400||rejected.error?.code==='ECONNRESET',JSON.stringify(rejected));await until(async()=>await count()===0,'stream limit released');assert.equal((await receipts()).length,2);
 const inspection=await owner.call('inspection.open',{sessionId:sid}),inspector=new URLSearchParams(new URL(inspection.url).hash.slice(1)).get('token');const readOnly=start('inspector-refused.txt',3,{},inspector);readOnly.req.end('bad');assert.equal((await readOnly.promise).status,400);assert.equal(await count(),0);const unauthenticated=start('token-refused.txt',3,{},'invalid');unauthenticated.req.end('bad');assert.equal((await unauthenticated.promise).status,401);assert.equal(await count(),0);assert.equal((await receipts()).length,2);
 assert.deepEqual(await owner.call('session.history',{sessionId:sid}),history);assert.equal(await readFile(link.requestLog,'utf8').catch(error=>{if(error.code==='ENOENT')return '';throw error;}),'');assert.equal((await owner.call('session.list')).items.length,1);
 const closed=once(fixture,'exit');assert.deepEqual(await owner.call('host.shutdown'),{accepted:true});await closed;assert.equal(fixture.exitCode,0,stderr);
});
