// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {mkdtemp,mkdir,writeFile,rm} from 'node:fs/promises';import {tmpdir} from 'node:os';import {join,resolve} from 'node:path';import {pathToFileURL} from 'node:url';
import {createServer} from 'node:net';import {spawn} from 'node:child_process';import {once,EventEmitter} from 'node:events';
const applicationRoot=resolve(process.env.AUGMENTOR_SURFACES_TEST_ROOT??'.');
const {RELEASE}=await import(pathToFileURL(join(applicationRoot,'dist/contracts/src/release.js')));

async function fixture(t,wrong=false){
 const root=await mkdtemp(join(tmpdir(),'ag-ah-browser-'));t.after(()=>rm(root,{recursive:true,force:true}));
 const profile={};for(const key of ['config','state','workspace','sharedState','sharedData']){profile[key]=join(root,key);await mkdir(profile[key],{mode:0o700})}
 profile.socket=join(root,'host.sock');const calls=[],sockets=new Set();
 const server=createServer(s=>{sockets.add(s);s.on('close',()=>sockets.delete(s));let buffer='';s.on('data',chunk=>{
  buffer+=chunk;let i;while((i=buffer.indexOf('\n'))>=0){const r=JSON.parse(buffer.slice(0,i));buffer=buffer.slice(i+1);calls.push(r);
   const result=r.method==='host.hello'?{protocol:'augmentor-pi/1'}:r.method==='host.describe'?{protocol:'augmentor-pi/1',version:'fixture',stateDir:wrong?'different-profile':profile.state,configDir:profile.config,capabilities:{queue:true,reasoning:true}}:
    r.method==='models.list'?{groups:[{provider:'fixture',models:[{model:'authored'}]}],default:{provider:'fixture',model:'authored'}}:
    r.method==='chats.saved'?{saved:[]}:r.method==='session.list'?{items:[{sessionId:'browser-fixture',agentPreset:'augmentor-browser-pi'}]}:{accepted:true};
   s.write(JSON.stringify({id:r.id,result})+'\n');
   if(r.method==='session.prompt')s.write(JSON.stringify({event:{method:'session/event',payload:{sessionId:'browser-fixture',event:{type:'assistant/message',message:{role:'assistant',content:[{type:'text',text:'Authored backend reply'}]}}}}})+'\n');
  }
 })});await new Promise(resolve=>server.listen(profile.socket,resolve));t.after(async()=>{for(const s of sockets)s.destroy();await new Promise(resolve=>server.close(resolve))});
 const record=join(root,'connection.json');await writeFile(record,JSON.stringify({schema:'augmentor-ah-connection/1',profile,root,version:'fixture'}),{mode:0o600});
 const child=spawn(process.execPath,['apps/browser/native-host.mjs'],{cwd:applicationRoot,env:{...process.env,AUGMENTOR_AH_CONNECTION:record,AUGMENTOR_SHARED_STATE:join(root,'wrong-shared'),AUGMENTOR_SHARED_DATA:join(root,'wrong-data')},stdio:['pipe','pipe','pipe']});
 t.after(async()=>{if(child.exitCode===null){child.stdin.end();await once(child,'close')}});
 let data=Buffer.alloc(0),id=0;const pending=new Map(),events=[],notifications=new EventEmitter();
 child.stdout.on('data',chunk=>{data=Buffer.concat([data,chunk]);while(data.length>=4&&data.length>=data.readUInt32LE(0)+4){const n=data.readUInt32LE(0),r=JSON.parse(data.subarray(4,n+4));data=data.subarray(n+4);if(r.id&&pending.has(r.id)){pending.get(r.id)(r);pending.delete(r.id)}else {events.push(r);notifications.emit('frame',r)}}});
 function call(method,params={}){return new Promise((resolve,reject)=>{const key=String(++id),b=Buffer.from(JSON.stringify({id:key,method,params})),h=Buffer.alloc(4);h.writeUInt32LE(b.length);const timer=setTimeout(()=>reject(Error('Native reply timed out')),10000);pending.set(key,r=>{clearTimeout(timer);resolve(r)});child.stdin.write(Buffer.concat([h,b]))})}
 assert.equal((await call('augmentor/handshake',{protocol:'augmentor/1',version:RELEASE.version})).result.version,RELEASE.version);
 assert.equal((await call('harness.select',{harness:'ah'})).result.harness,'ah');return {call,calls,events,profile,notifications};
}

test('Browser native host really selects AH, routes model/session/prompt RPC and streams its reply',async t=>{
 const f=await fixture(t);assert.equal((await f.call('augmentor/models')).result.default.model,'authored');
 const init=await f.call('initialize',{provider:'fixture',model:'authored'});assert.equal(init.result.serverInfo.harness,'ah');assert.equal(init.result.serverInfo.augmentor.chatCwd,f.profile.workspace);
 await f.call('session.create',{sessionId:'browser-fixture'});
 const streamed=new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Missing backend stream')),5000);f.notifications.on('frame',r=>{if(r.method==='session.event'){clearTimeout(timer);resolve(r)}})});
 const result=await f.call('session.prompt',{sessionId:'browser-fixture',requestId:'once',content:[{type:'text',text:'authored request'}]});assert.equal(result.result.accepted,true);
 assert.equal(f.calls.filter(r=>r.method==='session.prompt').length,1);
 const created=f.calls.find(r=>r.method==='session.create');assert.equal(created.params.surface,'browser');assert.equal(created.params.cwd,f.profile.workspace);
 const event=await streamed;assert.equal(event.params.event.message.content[0].text,'Authored backend reply');
});
test('Browser refuses an unrelated owner before model discovery or prompt dispatch',async t=>{
 const f=await fixture(t,true);const r=await f.call('augmentor/models');assert.match(r.error.message,/does not match/);assert(!f.calls.some(r=>['models.list','session.prompt'].includes(r.method)));
});
test('AH, DSH and legacy Pi retain distinct Browser conversation and model keys',async()=>{
 const saved={};globalThis.chrome={storage:{local:{get:(keys,cb)=>cb(saved),set:(value,cb)=>{Object.assign(saved,value);cb?.()} }},runtime:{}};
 const s=await import(pathToFileURL(join(process.env.AUGMENTOR_BROWSER_EXTENSION_ROOT??join(applicationRoot,'apps/browser/extension'),'state.mjs')));
 for(const harness of ['dsh','pi','ah']){s.state.harness=harness;s.saveSessionId(harness+'-chat');s.saveSelection({provider:harness,model:'fixture'})}
 for(const harness of ['ah','dsh','pi']){s.state.harness=harness;assert.equal(await s.loadStoredSessionId(),harness+'-chat');assert.equal((await s.loadStoredSelection()).provider,harness);assert.equal(s.storedHarness({'augmentor-harness':harness}),harness)}
 delete globalThis.chrome;
});
