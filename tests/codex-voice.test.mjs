// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {once} from 'node:events';
import {createServer} from 'node:http';
import {mkdtempSync, rmSync, mkdirSync, writeFileSync, existsSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join, resolve} from 'node:path';
import {spawn, execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {CodexIpcServer} from '../dist/codex-runtime/src/ipc.js';
import {setTimeout as delay} from 'node:timers/promises';
import {WebSocket} from 'ws';
import {createVoiceService} from '@augmentor-tests/resonant-voice/src/service.js';
import {CodexVoice} from '../dist/codex-runtime/src/voice.js';
import {CodexHost} from '../dist/codex-runtime/src/host.js';

async function until(fn) {for (let i=0;i<400;i++) {const value=fn();if(value)return value;await delay(10);}throw Error('Voice fixture timed out');}
async function fixture(t) {
  const spoken=[],workers=[],config={port:0,token:'a'.repeat(64),asr:{},maxUtteranceSeconds:600};
  // Synthetic devices exercise the separately pinned service, not installed models or audio.
  const service=createVoiceService(config,{tts:{health:async()=>({}),async *speak(text){spoken.push(text);yield Buffer.from([1,0,2,0]);}},workerFactory:(_,emit)=>{
    const worker={ready:true,send(event){if(event.type==='end')queueMicrotask(()=>emit({type:'final',utterance:event.utterance,text:'Synthetic spoken request'}));},close(){this.closed=true;}};
    workers.push(worker);queueMicrotask(()=>emit({type:'ready'}));return worker;
  }});
  await service.listen();config.port=service.server.address().port;
  const connection={base:`http://127.0.0.1:${config.port}`,token:config.token};
  t.after(()=>service.close());
  const connect=async ticket=>{
    assert.deepEqual(Object.keys(ticket).sort(),['protocol','sessionId','ticket','url']);
    const ws=new WebSocket(ticket.url),messages=[];ws.on('message',(data,binary)=>messages.push(binary?{type:'pcm'}:JSON.parse(data)));
    await once(ws,'open');ws.send(JSON.stringify({type:'auth',ticket:ticket.ticket,textSource:'plugin'}));
    await until(()=>messages.find(m=>m.type==='ready'));return {ws,messages};
  };
  return {service,connection,connect,spoken,workers};
}
function events(voice,session='chat') {
  const emit=(method,params)=>voice.observe(session,{method,params:{threadId:'native',turnId:'turn',...params}},id=>id==='request');
  return {
    user:()=>emit('item/completed',{item:{type:'userMessage',id:'user',clientId:'request'}}),
    start:()=>emit('item/started',{item:{type:'agentMessage',id:'answer',text:''}}),
    delta:text=>emit('item/agentMessage/delta',{itemId:'answer',delta:text}),
    end:text=>emit('item/completed',{item:{type:'agentMessage',id:'answer',text}}),emit,
  };
}
test('scoped voice streams public native text once and excludes reasoning, tools, replay and stale turns',async t=>{
  const f=await fixture(t),warnings=[],voice=new CodexVoice(()=>f.connection,(_,message)=>warnings.push(message));t.after(()=>voice.close());
  const socket=await f.connect(await voice.ticket('chat','linux')),e=events(voice);
  e.start();e.delta('Unconfirmed input must not speak.');
  e.user();e.start();e.emit('item/reasoning/summaryTextDelta',{delta:'Private reasoning.'});
  e.emit('item/completed',{item:{type:'commandExecution',id:'tool',aggregatedOutput:'Tool output must not speak.'}});
  e.delta('Public streamed ');e.delta('answer.');e.end('Public streamed answer.');e.end('Public streamed answer.');
  e.emit('turn/completed',{turn:{id:'turn',status:'completed'}});
  e.delta('Late output.');await voice.flush();await until(()=>f.spoken.length);
  assert.deepEqual(f.spoken,['Public streamed answer.']);
  assert.equal(socket.messages.find(m=>m.type==='turn-complete').requestId,'request');
  assert.deepEqual(warnings,[]);
  await voice.release('chat');await until(()=>f.workers[0].closed);assert.equal(voice.active,false);
});

test('Stop overtakes delayed text and keeps the same voice connection available without replay',async t=>{
  const f=await fixture(t),gate=Promise.withResolvers(),entered=Promise.withResolvers();
  const proxy=createServer(async(req,res)=>{
    let raw='';for await(const chunk of req)raw+=chunk;
    const body=raw?JSON.parse(raw):undefined;
    if(body?.type==='text'){entered.resolve();await gate.promise;}
    const response=await fetch(f.connection.base+req.url,{method:req.method,headers:body?{'content-type':'application/json','x-resonant-token':f.connection.token}:{},...(body?{body:raw}:{})});
    const value=await response.json();
    if(req.url==='/internal/ticket')value.url=`ws://127.0.0.1:${proxy.address().port}/voice`;
    res.writeHead(response.status,{'content-type':'application/json'});res.end(JSON.stringify(value));
  });
  await new Promise(resolve=>proxy.listen(0,'127.0.0.1',resolve));
  t.after(async()=>{gate.resolve();proxy.closeAllConnections();await new Promise(resolve=>proxy.close(resolve));});
  const warnings=[],voice=new CodexVoice(()=>({...f.connection,base:`http://127.0.0.1:${proxy.address().port}`}),(_,m)=>warnings.push(m));t.after(()=>voice.close());
  const ticket=await voice.ticket('chat','linux');ticket.url=f.connection.base.replace('http:','ws:')+'/voice';
  await f.connect(ticket);const e=events(voice);e.user();e.start();e.delta('This delayed text must remain silent.');e.end('This delayed text must remain silent.');
  await entered.promise;await voice.stop('chat');gate.resolve();await voice.flush();
  assert.deepEqual(f.spoken,[]);assert.deepEqual(warnings,[]);assert.equal(voice.active,true);
  await voice.release('chat');await until(()=>f.workers[0].closed);
});

test('voice refuses older companions before issuing tickets and never follows credential redirects',async t=>{
  let tickets=0,redirect=false,forwarded=0;
  const target=createServer((req,res)=>{forwarded++;res.end('{}');});await new Promise(resolve=>target.listen(0,'127.0.0.1',resolve));t.after(()=>new Promise(resolve=>target.close(resolve)));
  const server=createServer((req,res)=>{
    if(req.url==='/internal/ticket'){tickets++;if(redirect){res.writeHead(302,{location:`http://127.0.0.1:${target.address().port}/steal`});res.end();return;}}
    res.writeHead(200,{'content-type':'application/json'});res.end(JSON.stringify({protocol:'resonant-voice/1',...(redirect?{capabilities:{scopedHarnessBridge:1}}:{})}));
  });await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  t.after(()=>new Promise(resolve=>server.close(resolve)));
  const voice=new CodexVoice(()=>({base:`http://127.0.0.1:${server.address().port}`,token:'fixture'}));t.after(()=>voice.close());
  await assert.rejects(voice.ticket('chat','linux'),/0.1.17/);assert.equal(tickets,0);assert.equal(voice.active,false);
  redirect=true;await assert.rejects(voice.ticket('chat','linux'),/not confirm/);assert.equal(tickets,1);assert.equal(forwarded,0);assert.equal(voice.active,false);
  const remote=new CodexVoice(()=>({base:'https://example.test',token:'never-forward'}));
  await assert.rejects(remote.ticket('chat','linux'),/loopback/);
});

for(const surface of ['host','native','browser']) test(`actual pinned Codex ${surface} voice preserves request identity and delivers PCM`, {timeout:15000}, async t=>{
  const f=await fixture(t),root=mkdtempSync(join(tmpdir(),'codex-voice-')),inputs=[];
  const model=createServer(async(req,res)=>{
    let raw='';for await(const chunk of req)raw+=chunk;inputs.push(JSON.parse(raw));
    const item={id:'answer',type:'message',role:'assistant',status:'completed',content:[{type:'output_text',text:'Confirmed public reply.',annotations:[]}]};
    res.writeHead(200,{'content-type':'text/event-stream'});
    for(const event of [{type:'response.created',response:{id:'r',status:'in_progress',output:[]}},
      {type:'response.output_item.added',output_index:0,item},{type:'response.output_item.done',output_index:0,item},
      {type:'response.completed',response:{id:'r',status:'completed',output:[item]}}])res.write('data: '+JSON.stringify(event)+'\n\n');res.end();
  });await new Promise(resolve=>model.listen(0,'127.0.0.1',resolve));
  const host=new CodexHost({root,voiceConnection:()=>f.connection,resolveProfile:async id=>({id,revision:1,connection:{kind:'local',model:'fixture',endpoint:`http://127.0.0.1:${model.address().port}/v1`}})});
  t.after(async()=>{await host.close();model.closeAllConnections();await new Promise(resolve=>model.close(resolve));rmSync(root,{recursive:true,force:true});});
  if(surface!=='host') {
    const ipc=new CodexIpcServer(host,join(root,'runtime.sock'));await ipc.listen();t.after(()=>ipc.close());
    const home=join(root,'home');mkdirSync(home);const audioLog=join(root,'audio');
    const env={...process.env,HOME:home,XDG_CONFIG_HOME:join(home,'config'),XDG_DATA_HOME:join(home,'data'),XDG_STATE_HOME:join(home,'state'),
      AUGMENTOR_CODEX_STATE:root,AUGMENTOR_CODEX_SOCKET:ipc.socketPath,AUGMENTOR_CODEX_NO_AUTOSTART:'1',AUGMENTOR_CODEX_WORKSPACE:join(root,'workspace'),
      AUGMENTOR_CODEX_BROWSER_WORKSPACE:join(root,'browser'),AUGMENTOR_WINDOW_ID:'main',AUGMENTOR_WORKSPACE_PROFILE:'',
      AUGMENTOR_VOICE_TEST_AUDIO_LOG:audioLog,PYTHONPATH:resolve('apps/native'),QT_QPA_PLATFORM:'offscreen'};
    if(surface==='native') {
      const result=await promisify(execFile)(process.env.AUGMENTOR_PYTHON??'python3',['tests/fixtures/codex/native_voice.py'],{env,timeout:12000});
      assert.equal(JSON.parse(result.stdout).nativeVoice,'passed');
    } else {
      const quote=value=>"'"+value.replaceAll("'", "'\"'\"'")+"'";
      const wrapper=join(root,'python-voice');writeFileSync(wrapper,'#!/bin/sh\nexec '+quote(process.env.AUGMENTOR_PYTHON??'python3')+' '+quote(resolve('tests/fixtures/codex/voice_python.py'))+' "$@"\n',{mode:0o700});
      const child=spawn(process.execPath,['apps/browser/codex-bridge.mjs'],{env:{...env,AUGMENTOR_PYTHON:wrapper},stdio:['pipe','pipe','pipe']});
      const exited=once(child,'exit');t.after(async()=>{if(child.exitCode===null&&child.signalCode===null){child.kill();await exited;}});
      let buffer=Buffer.alloc(0),counter=0;const pending=new Map(),events=[];
      child.stdout.on('data',chunk=>{buffer=Buffer.concat([buffer,chunk]);while(buffer.length>=4&&buffer.length>=buffer.readUInt32LE(0)+4){
        const n=buffer.readUInt32LE(0),value=JSON.parse(buffer.subarray(4,n+4));buffer=buffer.subarray(n+4);const p=pending.get(value.id);
        if(p){pending.delete(value.id);value.error?p.reject(Error(value.error.message)):p.resolve(value.result);}else events.push(value);
      }});
      const call=(method,params={})=>new Promise((resolve,reject)=>{const id=++counter;pending.set(id,{resolve,reject});const body=Buffer.from(JSON.stringify({id,method,params})),head=Buffer.alloc(4);head.writeUInt32LE(body.length);child.stdin.write(Buffer.concat([head,body]));});
      const initialized=await call('initialize',{provider:'local',model:'fixture'});assert.equal(initialized.serverInfo.capabilities.voice,true);
      await call('session.create',{sessionId:'browser-chat'});
      const lease=await call('augmentor/voice/start',{sessionId:'browser-chat',id:'11111111-1111-4111-8111-111111111111'});
      const heartbeat=setInterval(()=>{void call('augmentor/voice/control',{...lease,action:'heartbeat'}).catch(()=>{});},1000);t.after(()=>clearInterval(heartbeat));
      await until(()=>events.find(e=>e.method==='voice.event'&&e.params.canRecord));
      await call('augmentor/voice/control',{...lease,action:'begin'});await delay(100);
      await call('augmentor/voice/control',{...lease,action:'end'});
      await until(()=>existsSync(audioLog));
      await call('augmentor/voice/control',{...lease,action:'close'});
      clearInterval(heartbeat);await call('shutdown');
    }
    assert.deepEqual(f.spoken,['Confirmed public reply.']);assert.equal(inputs.length,1);
    const rows=(await host.dispatch('session.list',{})).items;assert.equal(rows.length,1);
    const queue=await host.dispatch('session.queue',{sessionId:rows[0].sessionId});assert.equal(queue.operations.length,1);
    assert.match(queue.operations[0].id,/^resonant-voice:/);assert.equal(queue.operations[0].status,'completed');
    return;
  }
  await host.create({sessionId:'chat',profileId:'local',cwd:root});
  const a=await f.connect(await host.dispatch('voice.ticket',{sessionId:'chat',surface:'linux'}));
  await assert.rejects(host.dispatch('host.prepareShutdown',{}),/active/);
  await assert.rejects(host.release('chat'),/voice/);
  a.ws.send(JSON.stringify({type:'begin'}));a.ws.send(Buffer.alloc(640));a.ws.send(JSON.stringify({type:'end'}));
  const transcript=await until(()=>a.messages.find(m=>m.type==='transcript'));
  const requestId='resonant-voice:'+transcript.requestId;
  const params={sessionId:'chat',requestId,content:[{type:'text',text:transcript.text}]};
  await host.dispatch('session.prompt',params);
  await until(()=>a.messages.find(m=>m.type==='turn-complete'&&m.requestId===requestId));
  await host.voice.flush();assert.deepEqual(f.spoken,['Confirmed public reply.']);
  await host.dispatch('session.prompt',params);assert.equal(inputs.length,1,'stable voice request cannot dispatch twice');
  await host.close();await until(()=>f.workers[0].closed);
});
