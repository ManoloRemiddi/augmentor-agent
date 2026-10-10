// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import net from 'node:net';
import {mkdtempSync,mkdirSync,writeFileSync,readFileSync,existsSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';

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
