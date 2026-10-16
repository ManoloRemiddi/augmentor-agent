// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import net from 'node:net';
import {mkdtempSync,mkdirSync,writeFileSync,readFileSync,existsSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {PiConnection} from '../dist/client/src/socket.js';

test('simultaneous fresh Pi launches admit one owner before opening profile journals',{timeout:20000},async t=>{
 const root=mkdtempSync(join(tmpdir(),'augmentor-pi-owner-')),config=join(root,'config'),state=join(root,'state');
 mkdirSync(join(config,'agent'),{recursive:true});mkdirSync(join(state,'observations','fixture'),{recursive:true});
 const journal=join(state,'observations','fixture','events.jsonl');
 writeFileSync(journal,JSON.stringify({protocol:'augmentor-observation/1',id:'synthetic',seq:1,time:Date.now(),kind:'fixture',sessionId:'fixture',data:{}})+'\n',{mode:0o600});
 const before=readFileSync(journal,'utf8'),children=[],ready=[];
 const env={...process.env,AUGMENTOR_PI_CONFIG:config,AUGMENTOR_PI_STATE:state,AUGMENTOR_SHARED_STATE:join(root,'shared-state'),AUGMENTOR_SHARED_DATA:join(root,'shared-data'),AUGMENTOR_PI_LINUX_TOOLS:'0',PI_OFFLINE:'1'};
 t.after(async()=>{for(const child of children)if(child.exitCode===null&&child.signalCode===null){const ended=once(child,'exit');child.kill('SIGTERM');await ended;}rmSync(root,{recursive:true,force:true});});
 const start=()=>{
  const child=spawn(process.execPath,[join(resolve(process.env.AUGMENTOR_PI_TEST_ROOT||'.'),'dist/runtime/src/main.js')],{env,stdio:['ignore','pipe','pipe']});children.push(child);let output='';
  child.stdout.on('data',data=>{output+=data;for(const line of output.split('\n').filter(Boolean))if(line.startsWith('{')){const item=JSON.parse(line);if(item.ready&&!ready.some(p=>p.pid===child.pid))ready.push({pid:child.pid,...item});}});
  child.fixtureErrors='';child.stderr.on('data',data=>child.fixtureErrors+=data);return child;
 };
 start();start();
 const deadline=Date.now()+10000;
 while(!(ready.length===1&&children.some(c=>c.exitCode!==null||c.signalCode!==null))){if(children.every(c=>c.exitCode!==null||c.signalCode!==null)||Date.now()>deadline)throw Error('One owned runtime did not settle: '+JSON.stringify(children.map(c=>({code:c.exitCode,signal:c.signalCode,errors:c.fixtureErrors}))));await new Promise(r=>setTimeout(r,20));}
 assert.equal(ready.length,1);assert.equal(readFileSync(journal,'utf8'),before);
 const follower=start();await once(follower,'exit');assert.equal(follower.exitCode,0);assert.equal(ready.length,1);
 assert(existsSync(join(state,'runtime.sock')));
 const socket=net.createConnection(join(state,'runtime.sock'));await once(socket,'connect');socket.setEncoding('utf8');let raw='';
 socket.on('data',data=>{raw+=data;});socket.write(JSON.stringify({id:'hello',method:'host.hello',params:{protocol:'augmentor-pi/1'}})+'\n');
 const replyDeadline=Date.now()+5000;
 while(!raw.includes('\n')){if(Date.now()>replyDeadline){socket.destroy();throw Error('Owner handshake timed out');}await new Promise(r=>setTimeout(r,5));}
 socket.destroy();assert(JSON.parse(raw.split('\n')[0]).result);
});

test('a bind loser cannot remove the winning Unix listener', {skip:process.platform==='win32',timeout:20000},async t=>{
 const root=mkdtempSync(join(tmpdir(),'augmentor-bind-loser-')),state=join(root,'state'),config=join(root,'config');mkdirSync(state);mkdirSync(join(config,'agent'),{recursive:true});
 const path=join(state,'runtime.sock'),preload=join(root,'not-yet-observed.mjs');
 // Reproduce a winner binding immediately after the loser's existence check.
 // Only this owned fixture path's first public fs check is held unobserved.
 writeFileSync(preload,'import fs from "node:fs";import {syncBuiltinESMExports} from "node:module";const exists=fs.existsSync;let first=true;fs.existsSync=function(p){if(first&&p===process.env.AUGMENTOR_COLLISION_SOCKET){first=false;return false;}return exists(p);};syncBuiltinESMExports();\n');
 const winner=net.createServer(socket=>socket.end());winner.listen(path);await once(winner,'listening');let child;
 t.after(async()=>{if(child?.exitCode===null&&child.signalCode===null){const ended=once(child,'exit');child.kill('SIGTERM');await ended;}await new Promise(done=>winner.close(done));rmSync(root,{recursive:true,force:true});});
 const env={...process.env,HOME:root,AUGMENTOR_PI_CONFIG:config,AUGMENTOR_PI_STATE:state,AUGMENTOR_SHARED_STATE:join(root,'shared'),AUGMENTOR_SHARED_DATA:join(root,'data'),AUGMENTOR_PI_LINUX_TOOLS:'0',AUGMENTOR_COLLISION_SOCKET:path,PI_OFFLINE:'1'};
 child=spawn(process.execPath,['--import',preload,join(resolve(process.env.AUGMENTOR_PI_TEST_ROOT||'.'),'dist/runtime/src/main.js')],{env,stdio:['ignore','ignore','pipe']});let stderr='';child.stderr.on('data',data=>stderr+=data);await once(child,'exit');assert.notEqual(child.exitCode,0);assert.match(stderr,/EADDRINUSE/);assert(winner.listening);
 assert(existsSync(path),'a losing runtime must preserve the winning listener path');const probe=net.createConnection(path);await once(probe,'connect');probe.destroy();
});

test('a draining SDK owner keeps its socket until session shutdown finishes',{skip:process.platform==='win32',timeout:20000},async t=>{
 const root=mkdtempSync(join(tmpdir(),'augmentor-draining-owner-')),config=join(root,'config'),state=join(root,'state'),cwd=join(root,'work'),marker=join(root,'draining'),release=join(root,'release'),extension=join(root,'shutdown.mjs');for(const dir of [join(config,'agent'),state,cwd])mkdirSync(dir,{recursive:true});
 writeFileSync(extension,'import {writeFileSync,existsSync} from "node:fs";export default pi=>pi.on("session_shutdown",async()=>{writeFileSync('+JSON.stringify(marker)+',"waiting");while(!existsSync('+JSON.stringify(release)+'))await new Promise(resolve=>setTimeout(resolve,10));});\n');
 writeFileSync(join(config,'resources.json'),JSON.stringify({sources:[extension],skills:[]}));writeFileSync(join(config,'agent','models.json'),JSON.stringify({providers:{fixture:{api:'openai-completions',apiKey:'synthetic-only',baseUrl:'http://127.0.0.1:1/v1',models:[{id:'owner-only',name:'No inference fixture',input:['text'],reasoning:false,contextWindow:32768,maxTokens:1024}]}}}));
 const env={...process.env,HOME:root,AUGMENTOR_PI_CONFIG:config,AUGMENTOR_PI_STATE:state,AUGMENTOR_SHARED_STATE:join(root,'shared'),AUGMENTOR_SHARED_DATA:join(root,'data'),AUGMENTOR_PI_LINUX_TOOLS:'0',PI_OFFLINE:'1'},children=[],ready=new Set();let client;
 const start=()=>{const child=spawn(process.execPath,[join(resolve(process.env.AUGMENTOR_PI_TEST_ROOT||'.'),'dist/runtime/src/main.js')],{env,cwd,stdio:['ignore','pipe','pipe']});children.push(child);let output='';child.stdout.on('data',data=>{output+=data;for(const line of output.split('\n'))try{if(JSON.parse(line).ready)ready.add(child.pid);}catch{}});child.stderr.on('data',()=>{});return child;};
 const until=async(fn,label)=>{const end=Date.now()+10000;while(!fn()){if(Date.now()>end)throw Error(label);await new Promise(resolve=>setTimeout(resolve,10));}};
 t.after(async()=>{writeFileSync(release,'release');client?.close();for(const child of children)if(child.exitCode===null&&child.signalCode===null){const ended=once(child,'exit');child.kill('SIGTERM');await ended;}rmSync(root,{recursive:true,force:true});});
 const owner=start();await until(()=>ready.has(owner.pid),'initial owner ready');const socket=net.createConnection(join(state,'runtime.sock'));await once(socket,'connect');client=new PiConnection(socket);await client.call('host.hello',{protocol:'augmentor-pi/1'});await client.call('session.create',{sessionId:'drain',cwd,selection:{provider:'fixture',model:'owner-only'}});
 owner.kill('SIGTERM');await until(()=>existsSync(marker),'actual SDK shutdown hook held');assert.equal(owner.exitCode,null);assert(existsSync(join(state,'runtime.sock')),'a closing owner must retain its listener while the SDK drains');const follower=start();await until(()=>follower.exitCode!==null||follower.signalCode!==null||ready.has(follower.pid),'follower settles');assert.equal(ready.has(follower.pid),false,'no replacement owner may start before old SDK shutdown');assert.equal(follower.exitCode,0);
 const ended=once(owner,'exit');writeFileSync(release,'release');await ended;assert(!existsSync(join(state,'runtime.sock')));
});

test('one profile cannot be reopened through a different custom socket while its real owner is alive',{skip:process.platform==='win32',timeout:20000},async t=>{
 const root=mkdtempSync(join(tmpdir(),'augmentor-profile-sockets-')),state=join(root,'state'),config=join(root,'config');mkdirSync(state,{mode:0o700});mkdirSync(join(config,'agent'),{recursive:true});const file=join(state,'saved.txt');writeFileSync(file,'Saved profile bytes',{mode:0o600});const children=[],ready=new Set();
 const env={...process.env,HOME:root,AUGMENTOR_PI_CONFIG:config,AUGMENTOR_PI_STATE:state,AUGMENTOR_SHARED_STATE:join(root,'shared'),AUGMENTOR_SHARED_DATA:join(root,'data'),AUGMENTOR_PI_LINUX_TOOLS:'0',PI_OFFLINE:'1'};
 const start=socket=>{const child=spawn(process.execPath,[join(resolve(process.env.AUGMENTOR_PI_TEST_ROOT||'.'),'dist/runtime/src/main.js')],{env:{...env,AUGMENTOR_PI_SOCKET:socket},stdio:['ignore','pipe','pipe']});children.push(child);let output='';child.stdout.on('data',b=>{output+=b;for(const line of output.split('\n'))try{if(JSON.parse(line).ready)ready.add(child.pid);}catch{}});child.fixtureErrors='';child.stderr.on('data',b=>child.fixtureErrors+=b);return child;};
 t.after(async()=>{for(const child of children)if(child.exitCode===null&&child.signalCode===null){const ended=once(child,'exit');child.kill('SIGTERM');await ended;}rmSync(root,{recursive:true,force:true});});
 const owner=start(join(root,'first.sock')),deadline=Date.now()+10000;while(!ready.has(owner.pid)){assert.equal(owner.exitCode,null,owner.fixtureErrors);if(Date.now()>deadline)throw Error('Custom socket owner did not start');await new Promise(r=>setTimeout(r,20));}
 const follower=start(join(root,'second.sock'));await once(follower,'exit');assert.equal(follower.exitCode,0);assert.equal(ready.has(follower.pid),false);assert(!existsSync(join(root,'second.sock')));assert.equal(readFileSync(file,'utf8'),'Saved profile bytes');assert.equal(owner.exitCode,null);
});
