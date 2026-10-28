// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {mkdtempSync,writeFileSync,existsSync,symlinkSync,rmSync} from 'node:fs';import {tmpdir} from 'node:os';import {join} from 'node:path';import {EventEmitter} from 'node:events';
import {ungroupedDirectory} from '../dist/runtime/src/ungrouped.js';import {HarnessVoice} from '../dist/runtime/src/harness-voice.js';import {DshPiController} from '../apps/harness/dsh-pi-controller.mjs';import {bindResponsiveSidebar} from '../apps/harness/responsive-sidebar.mjs';import {pcm16,HarnessAudio,voiceControl} from '../apps/harness/harness-audio.mjs';
import {dictationInsertion} from '../apps/harness/dsh-dictation.mjs';
test('quick chats have separate private files and reject directory redirection',t=>{
 const root=mkdtempSync(join(tmpdir(),'ah-ungrouped-'));t.after(()=>rmSync(root,{recursive:true,force:true}));
 const a=ungroupedDirectory(root,'chat-a'),b=ungroupedDirectory(root,'chat-b');writeFileSync(join(a,'private-note'),'ALPHA');assert(!existsSync(join(b,'private-note')));assert.equal(ungroupedDirectory(root,'chat-a'),a);
 assert.throws(()=>ungroupedDirectory(root,'../project'));
 symlinkSync(a,join(root,'ungrouped','redirect'));assert.throws(()=>ungroupedDirectory(root,'redirect'),/private/);
});
test('New chat never inherits a project and older owners fail without creating',async()=>{
 const c=new DshPiController('fixture');c.update({phase:'ready',sessionId:'project',workspace:'/project',catalog:{default:{provider:'x',model:'y'}},capabilities:{isolatedUngrouped:1}});const requests=[];c.rpc=async(m,p)=>{requests.push(p);return {sessionId:p.sessionId};};c.refresh=async()=>{};c.open=async()=>{};
 await c.create();assert.equal(requests[0].ungrouped,true);assert(!('cwd'in requests[0]));await c.create('/explicit-project');assert.equal(requests[1].cwd,'/explicit-project');assert(!('ungrouped'in requests[1]));c.update({capabilities:{}});await assert.rejects(()=>c.create(),/needs the isolated/);assert.equal(requests.length,2);
});
test('rotation changes sidebar defaults, keyboard resizing and polls preserve manual toggles',()=>{
 const calls=[],listeners={},controller={state:{phase:'ready',sessionId:'a'},subscribe(fn){this.notify=fn;return()=>{};}},view={innerWidth:1100,screen:{orientation:{type:'landscape-primary',addEventListener(n,fn){listeners.orientation=fn;},removeEventListener(){}}},addEventListener(n,fn){listeners[n]=fn;},removeEventListener(){}};
 bindResponsiveSidebar(controller,{sidebar:{actions:{setExpanded:(...x)=>calls.push(x)}}},view);controller.notify();listeners.resize();assert.deepEqual(calls,[['a',true]]);
 view.screen.orientation.type='portrait-primary';view.innerWidth=690;listeners.orientation();assert.deepEqual(calls.at(-1),['a',false]);listeners.resize();assert.equal(calls.length,2);view.innerWidth=1100;view.screen.orientation.type='landscape-primary';listeners.orientation();assert.deepEqual(calls.at(-1),['a',true]);
});
test('browser PCM conversion bounds amplitude and resamples to companion input',()=>{
 const out=new Int16Array(pcm16(new Float32Array([2,-2,.5,0]),16000).buffer);assert.deepEqual([...out],[32767,-32767,16384,0]);assert.equal(pcm16(new Float32Array(480),48000).byteLength,320);
});
test('release during slow microphone permission cannot consume the lease or start capture later',async()=>{
 let grant,opens=0,stopped=0;const c={clientId:'c',token:'t',epoch:1,state:{sessionId:'s',phase:'ready',capabilities:{browserAudio:1,browserDictationDraft:1}},subscribe(){return()=>{};},async fetcher(path){if(path.endsWith('/open'))opens++;return {ok:true,json:async()=>({events:[]})};}},view={navigator:{mediaDevices:{getUserMedia:()=>new Promise(r=>grant=r)}},AudioContext:class{resume=async()=>{};close=async()=>{};},addEventListener(){}};
 const audio=new HarnessAudio(c,view),opening=audio.press();await new Promise(r=>setImmediate(r));assert.equal(opens,0);await audio.release();grant({getTracks:()=>[{stop(){stopped++;}}]});await opening;assert.equal(opens,0);assert.equal(stopped,1);assert.equal(audio.getSnapshot().held,false);
});
test('release inserts the final transcript once into the existing draft; no conversational submission occurs',async()=>{
 const audio=new HarnessAudio({epoch:1,state:{sessionId:'fixture',phase:'ready'},subscribe(){return()=>{};}},{addEventListener(){}}),controls=[];let drain,stopped=0,text='Existing: ',revision=0;
 audio.draft=dictationInsertion({scope:()=>1,revision:()=>revision,span:()=>({start:text.length,end:text.length}),replace:(span,value)=>{text=text.slice(0,span.start)+value+text.slice(span.end);revision++;return true;}});
 const s={sessionId:'fixture',epoch:1,ready:true,transcripts:new Set(),insertion:audio.draft.captureInsertion(),chain:new Promise(r=>drain=r),media:{getTracks:()=>[{stop(){stopped++;}}]}};audio.seat=s;audio.request=async(a,p)=>controls.push([a,p]);audio.gesture={};audio.set({phase:'listening',recording:true,held:true});
 const finishing=audio.release();assert.equal(stopped,1);assert(voiceControl(audio.getSnapshot()).busy);await audio.press();await audio.event(s,{type:'transcript-partial',text:'late partial'});assert.equal(audio.getSnapshot().note,'Finishing transcription…');drain();await finishing;assert.deepEqual(controls,[['control',{type:'end'}]]);
 const transcript={type:'transcript',requestId:'authored-fixture',text:'Authorised fixture'};await audio.event(s,transcript);await audio.event(s,transcript);assert.equal(text,'Existing: Authorised fixture');assert.equal(audio.getSnapshot().phase,'ready');assert.equal(controls.length,1);assert.equal(audio.inputBusy(),false);
 // Only explicit Send changes to the response-wait state.
 assert.equal(audio.sending('fixture'),true);await audio.press();assert.equal(audio.getSnapshot().phase,'thinking');
 // Server completion can precede local playback drain. The Talk state waits.
 audio.sources.add('pending-frame');await audio.event(s,{type:'turn-complete'});await audio.event(s,{type:'speech-idle'});assert.equal(audio.getSnapshot().phase,'thinking');audio.sources.clear();audio.playbackReady(s);assert.equal(audio.getSnapshot().phase,'ready');
 let recordings=0;audio.record=async()=>recordings++;await audio.event(s,{type:'ready'});assert.equal(recordings,0);
});
test('a changed draft retains recognition for explicit insertion and a different session cannot receive it',async()=>{
 const c={epoch:1,state:{sessionId:'fixture',phase:'ready'},subscribe(fn){this.notify=fn;return()=>{};}},audio=new HarnessAudio(c,{addEventListener(){}});let text='Original ',revision=0;
 audio.draft=dictationInsertion({scope:()=>c.state.sessionId,revision:()=>revision,span:()=>({start:text.length,end:text.length}),replace:(span,value)=>{text=text.slice(0,span.start)+value+text.slice(span.end);revision++;return true;}});
 const s={sessionId:'fixture',epoch:1,transcripts:new Set(),insertion:audio.draft.captureInsertion()};audio.seat=s;text='Edited ';revision++;
 await audio.event(s,{type:'transcript',requestId:'first',text:'dictated text'});assert.equal(text,'Edited ');assert.equal(audio.getSnapshot().pendingText,'dictated text');assert.equal(audio.insertPending(),true);assert.equal(text,'Edited dictated text');assert.equal(audio.insertPending(),false);
 s.insertion=audio.draft.captureInsertion();c.state.sessionId='other';await audio.event(s,{type:'transcript',requestId:'second',text:'must not cross sessions'});assert.equal(text,'Edited dictated text');
});
test('voice relay binds identities, rejects repeated PCM and only returns draft transcripts without starting work',async()=>{
 const calls=[],ws=new EventEmitter();ws.send=()=>{};ws.terminate=()=>{};
 const relay=new HarnessVoice(async(method,p)=>{calls.push([method,p]);if(method==='voice.ticket')return {protocol:'resonant-voice/1',sessionId:p.sessionId,url:'ws://127.0.0.1:8877/voice',ticket:'a'.repeat(64)};if(method==='session.queue')return {items:[],activeTurnId:null};return {accepted:true};},()=>ws);
 const p={clientId:'client',sessionId:'chat',openId:'open'};await relay.operation('open',p);ws.emit('open');ws.emit('message',Buffer.from('{"type":"ready"}'),false);await relay.operation('control',{...p,type:'begin'});await relay.operation('audio',{...p,seq:0,data:'AAA='});await assert.rejects(()=>relay.operation('audio',{...p,seq:0,data:'AAA='}),/interrupted/);await assert.rejects(()=>relay.operation('events',{...p,clientId:'other'}),/no longer/);
 await relay.operation('control',{...p,type:'end'});assert.equal((await relay.operation('audio',{...p,seq:1,data:'AAA='})).ended,true);assert.equal((await relay.operation('control',{...p,type:'end'})).ended,true);await assert.rejects(()=>relay.operation('control',{...p,type:'begin'}),/finish/);
 const transcript=Buffer.from(JSON.stringify({type:'transcript',requestId:'12345678-1234-4234-8234-123456789abc',text:'Authored fixture'}));ws.emit('message',transcript,false);ws.emit('message',transcript,false);await new Promise(r=>setImmediate(r));assert.equal(calls.filter(x=>x[0]==='session.prompt'||x[0]==='session.queue').length,0);const events=(await relay.operation('events',p)).events.filter(x=>x.type==='transcript');assert.equal(events.length,1);assert.equal(events[0].text,'Authored fixture');await relay.close();assert(calls.some(x=>x[0]==='voice.close'));
});
