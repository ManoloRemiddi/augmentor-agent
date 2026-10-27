// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';import {mkdtemp,rm,readdir} from 'node:fs/promises';import {tmpdir} from 'node:os';import {join} from 'node:path';import {setTimeout as delay} from 'node:timers/promises';
import {connectedBrowser,registerConnectedBrowserHost} from '../apps/browser/shared/connected-executor.mjs';
async function until(fn){for(let n=0;n<200;n++){if(await fn())return;await delay(20)}throw Error('Browser rendezvous timed out')}
test('real native-host rendezvous preserves split Unicode, swallows duplicate replies and drains maintenance',async t=>{
 const root=await mkdtemp(join(tmpdir(),'abc-')),prior=process.env.AUGMENTOR_BROWSER_EXECUTOR_DIR;process.env.AUGMENTOR_BROWSER_EXECUTOR_DIR=root;
 let executor,busy=false;const frames=[],text='café 日本語 😀 '.repeat(10000);
 executor=registerConnectedBrowserHost(frame=>{frames.push(frame);const result=frame.params.action==='tabs_list'?{ok:true,tabs:[{id:7,url:'https://fixture.test/'}]}:frame.params.action==='capabilities'?{ok:true,trustedKeyboard:true}:{ok:true,text};setTimeout(()=>{assert(executor.receive({id:frame.id,result}));assert(executor.receive({id:frame.id,result}));},0)},{busy:()=>busy});
 t.after(async()=>{executor.close();await until(async()=>!(await readdir(root)).some(x=>x.endsWith('.json')));await rm(root,{recursive:true,force:true});if(prior===undefined)delete process.env.AUGMENTOR_BROWSER_EXECUTOR_DIR;else process.env.AUGMENTOR_BROWSER_EXECUTOR_DIR=prior});
 await until(async()=>(await readdir(root)).some(x=>x.endsWith('.json')));
 const capabilities=await connectedBrowser('pi:authored',{action:'capabilities'});assert.equal(capabilities.tabs[0].id,7);assert.equal(capabilities.trustedKeyboard,true);
 const result=await connectedBrowser('pi:authored',{action:'document_read',tabId:7});assert.equal(result.text,text);assert.equal(executor.active,0);assert.equal(executor.receive({id:'unrelated',result:{}}),false);
 busy=true;const count=frames.length;await assert.rejects(connectedBrowser('pi:authored',{action:'insert_text',tabId:7,text:'never'}),/maintenance/);assert.equal(frames.length,count);assert.equal(executor.active,0);
});

test('compatible native host captures executor replies before its selected engine child',{skip:!process.env.AUGMENTOR_COMPAT_ROOT,timeout:45000},async t=>{
 const {spawn}=await import('node:child_process');const {once}=await import('node:events');
 const root=await mkdtemp(join(tmpdir(),'anh-')),prior=process.env.AUGMENTOR_BROWSER_EXECUTOR_DIR;process.env.AUGMENTOR_BROWSER_EXECUTOR_DIR=root;
 const app=process.env.AUGMENTOR_COMPAT_ROOT,manifest=JSON.parse(await (await import('node:fs/promises')).readFile(join(app,'apps/browser/extension/manifest.json'))),env={...process.env,AUGMENTOR_WORKSPACE_PROFILE:'',AUGMENTOR_SHARED_STATE:join(root,'s'),AUGMENTOR_SHARED_DATA:join(root,'d')};
 const child=spawn(process.execPath,[join(app,'apps/browser/native-host.mjs')],{env,stdio:['pipe','pipe','pipe']});let buffer=Buffer.alloc(0),seq=0,error='';const pending=new Map(),executed=[];
 const write=frame=>{const bytes=Buffer.from(JSON.stringify(frame)),head=Buffer.alloc(4);head.writeUInt32LE(bytes.length);child.stdin.write(Buffer.concat([head,bytes]))};
 child.stderr.on('data',b=>error+=b);child.stdout.on('data',chunk=>{buffer=Buffer.concat([buffer,chunk]);while(buffer.length>=4&&buffer.length>=buffer.readUInt32LE(0)+4){const length=buffer.readUInt32LE(0),frame=JSON.parse(buffer.subarray(4,length+4));buffer=buffer.subarray(length+4);if(frame.method==='browser/execute'){executed.push(frame);const result={ok:true,tabs:[{id:91,url:'https://authored.test/'}]};write({id:frame.id,result});write({id:frame.id,result});}else if(pending.has(frame.id)){const row=pending.get(frame.id);clearTimeout(row.timer);pending.delete(frame.id);frame.error?row.reject(Error(frame.error.message)):row.resolve(frame.result)}}});
 const call=(method,params)=>new Promise((resolve,reject)=>{const id='fixture-'+ ++seq,timer=setTimeout(()=>reject(Error('Native host timeout: '+method+' '+error)),10000);pending.set(id,{resolve,reject,timer});write({id,method,params})});
 t.after(async()=>{for(const row of pending.values())clearTimeout(row.timer);child.stdin.end();await Promise.race([once(child,'close'),delay(3000)]);if(child.exitCode===null)child.kill();await until(async()=>!(await readdir(root)).some(x=>x.endsWith('.json')));await rm(root,{recursive:true,force:true});if(prior===undefined)delete process.env.AUGMENTOR_BROWSER_EXECUTOR_DIR;else process.env.AUGMENTOR_BROWSER_EXECUTOR_DIR=prior});
 await call('augmentor/handshake',{protocol:'augmentor/1',version:manifest.version});assert.equal((await call('harness.select',{harness:'pi'})).harness,'pi');
 await until(async()=>(await readdir(root)).some(x=>x.endsWith('.json')));
 const tabs=await connectedBrowser('pi:independent-desktop',{action:'tabs_list'});assert.equal(tabs.tabs[0].id,91);assert.equal(executed.length,1);assert.match(executed[0].id,/^connected-browser-/);assert.equal(executed[0].params.owner,'pi:independent-desktop');
});
