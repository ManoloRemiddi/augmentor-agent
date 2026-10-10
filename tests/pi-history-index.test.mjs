// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Actual private IPC owner + public SDK-authored native/display history; no inference.
import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {mkdtemp,mkdir,readFile,writeFile,rm} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {tmpdir} from 'node:os';
import http from 'node:http';
import {createHash,randomUUID} from 'node:crypto';
import {setTimeout as delay} from 'node:timers/promises';
import {SessionManager} from '@earendil-works/pi-coding-agent';
import {PiConnection} from '../dist/client/src/socket.js';
import {localConnect} from '../dist/platform/src/transport.js';
import {historyPage} from '../dist/protocol/src/history.js';
async function until(fn,label){const deadline=Date.now()+15000;while(Date.now()<deadline){if(await fn())return;await delay(20);}throw Error('Indexed Pi history timeout: '+label);}

test('actual Pi cold/warm/restarted display and native pages use indexes without loading or changing originals',{timeout:45000},async t=>{
 const root=await mkdtemp(join(tmpdir(),'augmentor-pi-history-index-')),config=join(root,'config'),state=join(root,'state'),sessions=join(state,'sessions'),cwd=join(root,'workspace');
 for(const folder of [join(config,'agent'),sessions,cwd])await mkdir(folder,{recursive:true,mode:0o700});
 const children=[],connections=[];let requests=0;
 const provider=http.createServer((req,res)=>{requests++;res.writeHead(500).end('No inference belongs to this fixture');});provider.listen(0,'127.0.0.1');await once(provider,'listening');
 t.after(async()=>{for(const connection of connections)connection.close();for(const child of children)if(child.exitCode===null&&child.signalCode===null){const ended=once(child,'exit');child.kill('SIGTERM');await ended;}provider.closeAllConnections();await new Promise(done=>provider.close(done));await rm(root,{recursive:true,force:true,maxRetries:5,retryDelay:100});});
 await writeFile(join(config,'agent','models.json'),JSON.stringify({providers:{fixture:{baseUrl:'http://127.0.0.1:'+provider.address().port+'/v1',apiKey:'synthetic-only',api:'openai-completions',models:[{id:'history-fixture',name:'Authored history fixture',reasoning:false,input:['text'],contextWindow:131072,maxTokens:1024,cost:{input:0,output:0,cacheRead:0,cacheWrite:0}}]}}}));
 const manager=SessionManager.create(cwd,join(sessions,'native-original')),events=[];
 for(let i=0;i<2000;i++){
  const text='Authored question '+i,answer='Authored saved answer '+i,seq=i*5+1;
  manager.appendMessage({role:'user',content:[{type:'text',text}],timestamp:Date.now()});
  const message={role:'assistant',content:[{type:'text',text:answer}],api:'openai-completions',provider:'fixture',model:'history-fixture',stopReason:'stop',timestamp:Date.now(),usage:{input:0,output:0,cacheRead:0,cacheWrite:0,totalTokens:0,cost:{input:0,output:0,cacheRead:0,cacheWrite:0,total:0}}};
  manager.appendMessage(message);
  events.push({seq,type:'turn/start',data:{}},{seq:seq+1,type:'user/message',data:{source:{kind:'user'},content:[{type:'text',text}]}},{seq:seq+2,type:'assistant/chunk',data:{chunk:{type:'text-delta',text:'Authored saved '}}},{seq:seq+3,type:'assistant/message',data:{message}},{seq:seq+4,type:'turn/end',data:{}});
 }
 const native=manager.getSessionFile(),journal=join(sessions,'indexed-history.events.jsonl'),metrics=join(root,'metrics.json'),preload=join(root,'history-read-proof.mjs');
 const original=await readFile(native);await writeFile(journal,events.map(event=>JSON.stringify(event)+'\n').join(''),{mode:0o600});const display=await readFile(journal);
 await writeFile(join(sessions,'indexed-history.meta.json'),JSON.stringify({id:'indexed-history',cwd,file:native,selection:{provider:'fixture',model:'history-fixture'},title:'Authored saved history',saved:true,policy:'read-only',updatedAt:Date.now(),requests:[],running:false}));
 const observed=join(state,'observations','indexed-history');await mkdir(observed,{recursive:true,mode:0o700});const eventId=randomUUID(),payload=JSON.stringify({text:'x'.repeat(1024*1024)+' OWNER_RESTART_PAYLOAD_TERM'}),payloadFile=join(observed,eventId+'.payload.json'),payloadSha=createHash('sha256').update(payload).digest('hex');await writeFile(payloadFile,payload,{mode:0o600});const diagnostics=JSON.stringify({protocol:'augmentor-observation/1',id:eventId,seq:1,sessionId:'indexed-history',time:Date.now(),kind:'fixture/snapshot',data:{name:'Independently authored captured snapshot'},payload:{state:'retained',bytes:Buffer.byteLength(payload),sha256:payloadSha,redactions:[]}})+'\n';await writeFile(join(observed,'events.jsonl'),diagnostics,{mode:0o600});await writeFile(join(observed,'counter.json'),JSON.stringify({seq:1}),{mode:0o600});
 await writeFile(preload,`import fs from 'node:fs';import {syncBuiltinESMExports} from 'node:module';
const source=${JSON.stringify(journal)},nativeSource=${JSON.stringify(native)},payloadSource=${JSON.stringify(payloadFile)},metrics=${JSON.stringify(metrics)},open=fs.openSync,close=fs.closeSync,read=fs.readSync,readFile=fs.readFileSync,fds=new Map();let bytes=0,nativeBytes=0,payloadBytes=0;
fs.openSync=(file,...args)=>{const fd=open(file,...args);if(String(file)===source||String(file)===nativeSource||String(file)===payloadSource)fds.set(fd,String(file));return fd};
fs.closeSync=fd=>{fds.delete(fd);return close(fd)};
fs.readSync=(fd,...args)=>{const n=read(fd,...args);if(fds.has(fd)){if(fds.get(fd)===source)bytes+=n;else if(fds.get(fd)===nativeSource)nativeBytes+=n;else payloadBytes+=n;fs.writeFileSync(metrics,JSON.stringify({bytes,nativeBytes,payloadBytes}),{mode:0o600})}return n};
fs.readFileSync=(file,...args)=>{if(String(file)===source||String(file)===nativeSource||String(file)===payloadSource)throw Error('Complete display/native/payload read forbidden by authored history proof');return readFile(file,...args)};
syncBuiltinESMExports();`,{mode:0o600});
 const env=Object.fromEntries(Object.entries(process.env).filter(([key])=>!/^(AUGMENTOR_|DSH_|PI_)/.test(key)));
 Object.assign(env,{HOME:join(root,'home'),AUGMENTOR_PI_CONFIG:config,AUGMENTOR_PI_STATE:state,AUGMENTOR_SHARED_DATA:join(root,'shared-data'),AUGMENTOR_SHARED_STATE:join(root,'shared-state'),AUGMENTOR_PI_LINUX_TOOLS:'0',PI_OFFLINE:'1'});
 const start=async()=>{
  const child=spawn(process.execPath,['--import',preload,join(resolve(process.env.AUGMENTOR_PI_TEST_ROOT||'.'),'dist/runtime/src/main.js')],{env,stdio:['ignore','pipe','pipe']});children.push(child);let output='',errors='';
  child.stdout.on('data',data=>output+=data);child.stderr.on('data',data=>errors+=data);
  await until(()=>{if(child.exitCode!==null||child.signalCode!==null)throw Error(errors);return output.split('\n').some(line=>{try{return JSON.parse(line).ready===true;}catch{return false;}});},'owner ready');
  const socket=localConnect(join(state,'runtime.sock'));await once(socket,'connect');const connection=new PiConnection(socket);connections.push(connection);await connection.call('host.hello',{protocol:'augmentor-pi/1'});return {child,connection};
 };
 const first=await start(),page=await first.connection.call('session.history',{sessionId:'indexed-history',maxMessages:3});assert.deepEqual(page,historyPage(events,3));
 const initial=JSON.parse(await readFile(metrics,'utf8')).bytes,earlier=await first.connection.call('session.history',{sessionId:'indexed-history',maxMessages:3,beforeSeq:page.events[0].event.seq});assert.deepEqual(earlier,historyPage(events,3,page.events[0].event.seq));assert(JSON.parse(await readFile(metrics,'utf8')).bytes-initial<8192,'warm owner reads only selected display records');
 const nativePage=await first.connection.call('session.nativeHistory',{sessionId:'indexed-history',limit:3});assert.equal(nativePage.nativeSessionId,manager.getSessionId());assert.equal(nativePage.entries[0].role,'assistant');
 const nativeInitial=JSON.parse(await readFile(metrics,'utf8')).nativeBytes,nativeEarlier=await first.connection.call('session.nativeHistory',{sessionId:'indexed-history',limit:3,cursor:nativePage.nextCursor});assert.equal(nativeEarlier.entries.length,3);assert(JSON.parse(await readFile(metrics,'utf8')).nativeBytes-nativeInitial<=4*65536,'warm native metadata pages verify bounded source blocks');
 let offset=0,raw='';while(true){const excerpt=await first.connection.call('session.nativeRead',{sessionId:'indexed-history',entryId:nativePage.entries[0].entryId,pathHash:nativePage.entries[0].pathHash,entryHash:nativePage.entries[0].entryHash,nativeSessionId:nativePage.nativeSessionId,offset,limit:256});raw+=excerpt.text;if(!excerpt.hasMore)break;offset=excerpt.nextOffset;}
 assert.equal(JSON.parse(raw).message.content[0].text,'Authored saved answer 1999');assert(JSON.parse(await readFile(metrics,'utf8')).nativeBytes-nativeInitial<=12*65536,'metadata and excerpts verify bounded original blocks');
 const partialSearch=await first.connection.call('observation.search',{sessionId:'indexed-history',scope:'payloads',query:'OWNER_RESTART_PAYLOAD_TERM'});assert(partialSearch.hasMore&&partialSearch.coverage.partialPayload);assert.deepEqual(partialSearch.records,[]);
 const stopped=once(first.child,'exit');first.child.kill('SIGTERM');await stopped;assert.equal(first.child.exitCode,0);
 const restarted=await start();assert.deepEqual(await restarted.connection.call('session.history',{sessionId:'indexed-history',maxMessages:3,beforeSeq:5001}),historyPage(events,3,5001));assert(JSON.parse(await readFile(metrics,'utf8')).bytes<8192,'restarted owner uses its persisted index');
 assert.deepEqual(await restarted.connection.call('session.nativeHistory',{sessionId:'indexed-history',limit:3,cursor:nativePage.nextCursor}),nativeEarlier);assert(JSON.parse(await readFile(metrics,'utf8')).nativeBytes>0&&JSON.parse(await readFile(metrics,'utf8')).nativeBytes<=4*65536,'restarted native metadata pages verify bounded source blocks');
 let searchCursor=partialSearch.nextCursor,found=[];do{const beforePayload=JSON.parse(await readFile(metrics,'utf8')).payloadBytes??0,part=await restarted.connection.call('observation.search',{sessionId:'indexed-history',scope:'payloads',query:'OWNER_RESTART_PAYLOAD_TERM',cursor:searchCursor});assert.equal(part.coverage.indexBuildBytesRead,0);assert((JSON.parse(await readFile(metrics,'utf8')).payloadBytes??0)-beforePayload<=512*1024);found.push(...part.records);searchCursor=part.nextCursor;if(!part.hasMore)break;}while(true);assert.deepEqual(found.map(row=>row.id),[eventId]);const verified=await restarted.connection.call('observation.payload',{sessionId:'indexed-history',eventId,offset:0,limit:32,sha256:payloadSha});assert.equal(verified.verification,'captured snapshot source blocks');assert.equal(verified.sha256,payloadSha);assert.equal(await readFile(payloadFile,'utf8'),payload);assert.equal(await readFile(join(observed,'events.jsonl'),'utf8'),diagnostics);
 assert.deepEqual(await readFile(native),original);assert.deepEqual(await readFile(journal),display);assert.equal(requests,0);const descriptor=await restarted.connection.call('host.describe');assert.equal(descriptor.activeTurns,0);assert.equal(descriptor.capabilities.indexedDisplayHistory,true);assert.equal(descriptor.capabilities.indexedNativeHistory,true);
});
