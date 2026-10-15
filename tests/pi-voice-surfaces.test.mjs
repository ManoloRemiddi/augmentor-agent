// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Actual public Host/SDK, Qt/Browser workers and framed IPC; synthetic audio only.
import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn,execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {once} from 'node:events';
import {writeFile,readFile} from 'node:fs/promises';
import {join,resolve,delimiter} from 'node:path';
import {setTimeout as delay} from 'node:timers/promises';
import {piVoiceFixture} from './fixtures/pi-voice.mjs';
import {until} from './fixtures/plans.mjs';
import {BrowserVoice} from '../apps/browser/shared/voice-client.mjs';
const artifact=resolve(process.env.AUGMENTOR_PI_TEST_ROOT??'.');
async function audioEnvironment(f){
 const site=join(f.root,'sitecustomize.py');await writeFile(site,'# Independently authored synthetic audio proof only.\nimport fake_audio\n');
 return {...f.env,AUGMENTOR_PI_NO_AUTOSTART:'1',AUGMENTOR_PI_WORKSPACE:f.workspace,AUGMENTOR_PI_BROWSER_WORKSPACE:f.workspace,AUGMENTOR_WINDOW_ID:'main',AUGMENTOR_WORKSPACE_PROFILE:'',AUGMENTOR_PYTHON:process.env.AUGMENTOR_PYTHON??'python3',PYTHONPATH:[f.root,join(artifact,'tests/fixtures/codex'),join(artifact,'apps/native')].join(delimiter),QT_QPA_PLATFORM:'offscreen',AUGMENTOR_VOICE_TEST_AUDIO_LOG:join(f.root,'audio')};
}
async function browser(t,f){
 const child=spawn(process.execPath,[join(artifact,'apps/browser/pi-bridge.mjs')],{env:await audioEnvironment(f),stdio:['pipe','pipe','pipe']});
 const done=once(child,'exit'),pending=new Map(),events=[];let buffer=Buffer.alloc(0),serial=0,stderr='';child.stderr.on('data',b=>stderr+=b);
 child.on('exit',()=>{for(const p of pending.values())p.reject(Error('Browser fixture exited: '+stderr));pending.clear();});
 child.stdout.on('data',b=>{buffer=Buffer.concat([buffer,b]);while(buffer.length>=4&&buffer.length>=buffer.readUInt32LE(0)+4){const n=buffer.readUInt32LE(0),row=JSON.parse(buffer.subarray(4,n+4));buffer=buffer.subarray(n+4);const p=pending.get(row.id);if(p){pending.delete(row.id);row.error?p.reject(Error(row.error.message)):p.resolve(row.result);}else events.push(row);}});
 const call=(method,params={})=>new Promise((resolve,reject)=>{const id='voice-proof-'+ ++serial;pending.set(id,{resolve,reject});const b=Buffer.from(JSON.stringify({id,method,params})),h=Buffer.alloc(4);h.writeUInt32LE(b.length);child.stdin.write(Buffer.concat([h,b]));});
 t.after(async()=>{if(child.exitCode===null&&child.signalCode===null){child.stdin.end();await done;}});
 return {call,events,child,done};
}
test('actual Pi Native hold/release, PCM playback and original Send preserve spoken/typed continuity', {timeout:30000},async t=>{
 const f=await piVoiceFixture(t,{jobMode:{}}),env=await audioEnvironment(f);
 const result=await promisify(execFile)(env.AUGMENTOR_PYTHON,[join(artifact,'tests/fixtures/pi-voice-native.py')],{env,timeout:20000});
 const proof=JSON.parse(result.stdout);assert.equal(proof.nativePiVoice,'passed');assert.equal(proof.typedFollowup,true);await f.settled(proof.sessionId);
 const events=(await f.call('session.history',{sessionId:proof.sessionId})).events.map(row=>row.event),users=events.filter(row=>row.type==='user/message');
 assert.deepEqual(users.map(row=>row.data.inputMode),['voice','text']);assert.match(users[0].data.source.rpcId,/^resonant-voice:/);
 assert.equal(f.requests.length,2);assert(JSON.stringify(f.requests[0].messages.filter(row=>row.role==='system')).includes('The user spoke this request.'));
 assert(JSON.stringify(f.requests[1].messages.filter(row=>row.role==='system')).includes('The user typed this request.'));
 assert.equal(f.peer.spoken.length,1);assert.equal((await f.call('host.describe')).activeVoiceBridges,0);
 assert.equal(await readFile(env.AUGMENTOR_VOICE_TEST_AUDIO_LOG,'utf8'),'synthetic PCM played');
});
test('actual Pi Browser uses the shared audio worker, explicit input mode and joined close with no scope crossover', {timeout:30000},async t=>{
 const f=await piVoiceFixture(t,{jobMode:{}});await f.create('native-only');const b=await browser(t,f);
 assert.equal((await b.call('initialize',f.selection)).serverInfo.capabilities.voice,true);
 await assert.rejects(b.call('augmentor/voice/start',{sessionId:'native-only',id:crypto.randomUUID()}),/current Pi conversation/);
 await b.call('session.create',{sessionId:'browser-voice'});
 const lease=await b.call('augmentor/voice/start',{sessionId:'browser-voice',id:crypto.randomUUID()});
 const heartbeat=setInterval(()=>{void b.call('augmentor/voice/control',{...lease,action:'heartbeat'}).catch(()=>{});},1000);t.after(()=>clearInterval(heartbeat));
 await until(()=>b.events.some(row=>row.method==='voice.event'&&row.params.canRecord),'shared browser microphone ready');
 await assert.rejects(b.call('augmentor/voice/control',{...lease,sessionId:'native-only',action:'begin'}),/another or closed conversation/);
 await b.call('augmentor/voice/control',{...lease,action:'begin'});await delay(100);await b.call('augmentor/voice/control',{...lease,action:'end'});
 await until(async()=>readFile(join(f.root,'audio')).then(()=>true,()=>false),'browser PCM playback');await f.settled('browser-voice');
 // A subsequent spoken correction uses the same active SDK turn rather than a
 // transient SDK string queue or a second owner.
 const root=await f.call('session.prompt',{sessionId:'browser-voice',requestId:'typed-hold',content:[{type:'text',text:JSON.stringify({kind:'worker-hold'})}]});
 await until(()=>f.requests.length===2,'typed active browser request');
 await b.call('augmentor/voice/control',{...lease,action:'begin'});await delay(100);await b.call('augmentor/voice/control',{...lease,action:'end'});
 await until(()=>f.peer.spoken.length===2,'spoken correction reply');await f.settled('browser-voice');
 const delivered=(await f.call('session.history',{sessionId:'browser-voice'})).events.map(row=>row.event).filter(row=>row.type==='user/message');
 assert.equal(delivered.at(-1).turnId,root.turnId);assert.deepEqual(delivered.map(row=>row.data.inputMode),['voice','text','voice']);
 await b.call('augmentor/voice/control',{...lease,action:'close'});clearInterval(heartbeat);await b.call('shutdown');await b.done;
 assert.equal((await f.call('host.describe')).activeVoiceBridges,0);assert.equal(f.peer.spoken.length,2);assert(f.peer.connections[0].closed);
 const users=(await f.call('session.history',{sessionId:'browser-voice'})).events.map(row=>row.event).filter(row=>row.type==='user/message');
 assert.equal(users.length,3);assert.equal(users[0].data.inputMode,'voice');assert.equal(users[0].data.content[0].text,'Synthetic spoken request');assert.equal(f.requests.length,3);
});
test('Browser close bypasses catalog reads during held Pi setup and EOF joins final ticket retirement', {timeout:30000},async t=>{
 let enter,release;const entered=new Promise(resolve=>enter=resolve),gate=new Promise(resolve=>release=resolve);
 const f=await piVoiceFixture(t,{peerOptions:{beforeRequest:async({path})=>{if(path==='/health'){enter();await gate;}}}}),b=await browser(t,f);
 await b.call('initialize',f.selection);await b.call('session.create',{sessionId:'browser-closing'});
 const lease=await b.call('augmentor/voice/start',{sessionId:'browser-closing',id:crypto.randomUUID()});
 try{
  await entered;await b.call('augmentor/voice/control',{...lease,action:'close'});
  await assert.rejects(b.call('augmentor/voice/start',{sessionId:'browser-closing',id:crypto.randomUUID()}),/still finishing/);
  b.child.stdin.end();let exited=false;b.done.then(()=>exited=true);await delay(40);assert.equal(exited,false);
 }finally{release();}
 await b.done;assert.equal(f.ticketCalls(),0);assert.equal((await f.call('host.describe')).activeVoiceBridges,0);assert.equal(f.requests.length,0);
});
test('a refused shared-worker opening and its scoped cleanup preserve the existing Browser speech lease', {timeout:30000},async t=>{
 const f=await piVoiceFixture(t,{jobMode:{}}),first=await browser(t,f),events=[],env=await audioEnvironment(f);
 await first.call('initialize',f.selection);await first.call('session.create',{sessionId:'shared-voice'});
 const lease=await first.call('augmentor/voice/start',{sessionId:'shared-voice',id:crypto.randomUUID()});
 await until(()=>first.events.some(row=>row.method==='voice.event'&&row.params.canRecord),'first window voice ready');
 // The Browser broker correctly has one executor per chat. Test the independent
 // shared audio actor without attempting to attach an unauthorized second one.
 const contender=new BrowserVoice({root:artifact,notify:row=>events.push(row),
   ticket:(sessionId,openId)=>f.call('voice.ticket',{sessionId,openId,surface:'browser'}),
   release:(sessionId,openId)=>f.call('voice.close',{sessionId,openId}),submit:()=>assert.fail('Refused input must not submit'),
   spawnWorker:(_python,args,options)=>spawn(env.AUGMENTOR_PYTHON,args,{...options,env})});
 await contender.start({sessionId:'shared-voice',id:crypto.randomUUID()});
 await until(()=>events.some(row=>row.params.type==='error'),'contending opening refused');await contender.settled();
 assert.equal((await f.call('host.describe')).activeVoiceBridges,1);assert.equal(f.peer.connections[0].closed,false);
 await first.call('augmentor/voice/control',{...lease,action:'close'});await first.call('shutdown');await first.done;
 assert.equal((await f.call('host.describe')).activeVoiceBridges,0);assert.equal(f.requests.length,0);assert.equal(f.ticketCalls(),1);
});
