// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Independent local provider, real private Host/SDK; no owner profile/service source.
import assert from 'node:assert/strict';
import http from 'node:http';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {mkdtemp,mkdir,readFile,writeFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {setTimeout as delay} from 'node:timers/promises';
import {PiConnection} from '../../dist/client/src/socket.js';
import {localConnect} from '../../dist/platform/src/transport.js';
import {pythonExecutable} from '../../dist/platform/src/index.js';
import {desktopJobPeer} from './desktop-job-peer.mjs';
export async function until(fn,label,ms=15000){const end=Date.now()+ms;while(Date.now()<end){if(await fn())return;await delay(25);}throw Error('Plan fixture timeout: '+label);}
export async function planFixture(t,{policy='danger-full-access',goalMode,jobMode,desktopMode}={}){
 const root=await mkdtemp(join(tmpdir(),'augmentor-plan-')),config=join(root,'config'),state=join(root,'state'),workspace=join(root,'work');
 const runtime=join(root,'runtime');for(const path of [join(config,'agent'),workspace,runtime])await mkdir(path,{recursive:true,mode:0o700});
 const desktop=desktopMode?await desktopJobPeer(runtime,state,desktopMode):undefined;
 const requests=[],children=[],connections=[],frames=[];let child,owner,errors='';
 const model=http.createServer(async(req,res)=>{
  if(req.url!='/v1/chat/completions'){res.writeHead(404).end();return;}
  let raw='';for await(const bytes of req)raw+=bytes;const body=JSON.parse(raw);requests.push(body);
  const user=body.messages.findLast(message=>message.role==='user'),text=typeof user?.content==='string'?user.content:user?.content?.map(p=>p.text??'').join('');
  let op;try{op=JSON.parse(text);}catch{op={kind:'read'};}
  if(goalMode?.failGoal&&text?.startsWith('Continue the explicitly started goal')){res.writeHead(500,{'content-type':'application/json'}).end(JSON.stringify({error:{message:'Independent synthetic provider failure'}}));return;}
  res.writeHead(200,{'content-type':'text/event-stream'});
  const send=(delta,finish=null)=>res.write('data: '+JSON.stringify({id:'plan-fixture',object:'chat.completion.chunk',model:'plan-fixture',choices:[{index:0,delta,finish_reason:finish}]})+'\n\n');
  const last=body.messages.at(-1),proposal=body.messages.findLast(m=>m.role==='assistant'&&m.tool_calls?.length),toolName=proposal?.tool_calls?.at(-1)?.function?.name;
  if(desktopMode){
   const tool=(name,args={})=>send({role:'assistant',tool_calls:[{index:0,id:'desktop-call-'+requests.length,type:'function',function:{name,arguments:JSON.stringify(args)}}]},'tool_calls');
   const worker=body.tools?.some(tool=>tool.function.name==='desktop_finish');
   if(worker){
    for(const message of body.messages.filter(message=>message.role==='user')){const value=typeof message.content==='string'?message.content:message.content?.map(part=>part.text??'').join('');try{const brief=JSON.parse(value);if(typeof brief.task==='string'&&typeof brief.successCriteria==='string'){op=brief;break;}}catch{}}
    if(desktopMode.holdBeforeConnect||desktopMode.holdAfterAction&&toolName==='desktop_action'){
     send({role:'assistant',content:'Synthetic desktop provider holding. '});const timer=setInterval(()=>send({content:' '}),100);res.once('close',()=>clearInterval(timer));return;
    }
    if(!toolName)tool('desktop_connect');
    else if(toolName==='desktop_connect'||toolName==='desktop_action')tool('desktop_snapshot');
    else if(toolName==='desktop_snapshot'&&!body.messages.some(m=>m.role==='assistant'&&m.tool_calls?.some(c=>c.function.name==='desktop_action'))){
     const result=body.messages.findLast(message=>message.role==='tool'),metadata=typeof result.content==='string'?result.content:result.content.find(p=>p.type==='text')?.text;tool('desktop_action',{token:JSON.parse(metadata).token,kind:'click',x:0,y:0});
    }else tool('desktop_finish',{status:'completed',summary:op.task,verification:op.successCriteria});
   }else if(op.kind==='desktop-direct'&&last?.role!=='tool')tool(op.tool,{});
   else if(op.kind==='desktop-parent'&&last?.role!=='tool')tool('desktop_delegate',op.brief);
   else if(op.kind==='desktop-parent'&&desktopMode.doubleDelegate&&toolName==='desktop_delegate'&&!body.messages.some(m=>m.role==='tool'&&String(m.content).includes('Only one desktop delegation')))tool('desktop_delegate',op.brief);
   else send({role:'assistant',content:op.reply??'Synthetic parent result; inspect evidence.'},'stop');
   res.write('data: '+JSON.stringify({id:'desktop-usage',object:'chat.completion.chunk',choices:[],usage:{prompt_tokens:10,completion_tokens:5,total_tokens:15}})+'\n\n');res.end('data: [DONE]\n\n');return;
  }
  if(jobMode){
   if(text?.startsWith('Delegated task from the parent conversation.')){try{op=JSON.parse(text.split('\n\n').slice(1).join('\n\n'));}catch{op={kind:'worker-reply'};}}
   const tool=(name,args)=>send({role:'assistant',tool_calls:[{index:0,id:'job-call-'+requests.length,type:'function',function:{name,arguments:JSON.stringify(args)}}]},'tool_calls');
   if(op.kind==='worker-hold'){send({role:'assistant',content:'Synthetic delegated worker holding. '});const timer=setInterval(()=>send({content:' '}),100);res.once('close',()=>clearInterval(timer));return;}
   if(op.kind==='worker-loop'||last?.role!=='tool'&&['worker-write','worker-forbidden','worker-nested'].includes(op.kind))tool(op.kind==='worker-nested'?'worker_nested':op.kind==='worker-loop'?'read':'write',op.kind==='worker-nested'?{path:op.path}:{path:op.path,content:op.content??'Independent synthetic worker output'});
   else if(op.kind==='job-start'&&last?.role!=='tool')tool('job_start',op.spec);
   else if(op.kind==='job-start'&&toolName==='job_start')tool('job_wait',{jobId:JSON.parse(last.content).job.id,timeoutMs:10000});
   else if(op.kind==='job-start'&&toolName==='job_wait')tool('job_read',{jobId:JSON.parse(last.content).job.id});
   else send({role:'assistant',content:op.reply??'Synthetic job reply; verify tool outcomes.'},'stop');
   res.write('data: '+JSON.stringify({id:'job-usage',object:'chat.completion.chunk',choices:[],usage:{prompt_tokens:10,completion_tokens:5,total_tokens:15}})+'\n\n');
   res.end('data: [DONE]\n\n');return;
  }

  if(goalMode){
   const tool=(name,args)=>send({role:'assistant',tool_calls:[{index:0,id:'goal-'+requests.length,type:'function',function:{name,arguments:JSON.stringify(args)}}]},'tool_calls');
   if(last?.role!=='tool')tool('get_goal',{});
   else if(toolName==='get_goal'){
    const view=JSON.parse(last.content),g=view.goal,expectedRef=g?{id:g.id,revision:g.revision}:null;
    if(op.kind==='goal-create')tool('create_goal',{expectedRef,...op.change});
    else if(op.kind==='goal-update')tool('update_goal',{expectedRef,...op.change});
    else if(text?.startsWith('Continue the explicitly started goal')&&goalMode.hold){
     send({role:'assistant',content:'Synthetic goal round holding after admission. '});const timer=setInterval(()=>send({content:' '}),100);res.once('close',()=>clearInterval(timer));return;
    }else if(text?.startsWith('Continue the explicitly started goal')&&goalMode.completeAfter&&g?.roundsStarted>=goalMode.completeAfter)tool('update_goal',{operation:'complete',expectedRef});
    else send({role:'assistant',content:'Synthetic goal progress report.'},'stop');
   }else send({role:'assistant',content:'Synthetic goal tool result observed.'},'stop');
   res.end('data: [DONE]\n\n');return;
  }

  if(last?.role!=='tool')send({role:'assistant',tool_calls:[{index:0,id:'plan-read-call',type:'function',function:{name:'plan_read',arguments:'{}'}}]},'tool_calls');
  else if(toolName==='plan_read'&&op.kind==='update'){
   const result=JSON.parse(last.content),args={expectedRevision:op.expectedRevision??result.revision,title:op.title,steps:op.steps};
   send({role:'assistant',tool_calls:[{index:0,id:'plan-update-call',type:'function',function:{name:'plan_update',arguments:JSON.stringify(args)}}]},'tool_calls');
  }else if(op.slow){send({role:'assistant',content:'Synthetic provider holding after the recorded plan. '});const timer=setInterval(()=>send({content:' '}),100);res.once('close',()=>clearInterval(timer));return;}
  else send({role:'assistant',content:'Synthetic planning reply. The tools report progress without verifying task completion.'},'stop');
  res.end('data: [DONE]\n\n');
 });model.listen(0,'127.0.0.1');await once(model,'listening');
 const selection={provider:'fixture',model:'plan-fixture'};
 await writeFile(join(config,'agent','models.json'),JSON.stringify({providers:{fixture:{api:'openai-completions',baseUrl:'http://127.0.0.1:'+model.address().port+'/v1',apiKey:'synthetic-plan-key',models:[{id:selection.model,name:'Synthetic planning provider',reasoning:false,input:desktopMode&&!desktopMode.textOnly?['text','image']:['text'],contextWindow:131072,maxTokens:2048}]}}}),{mode:0o600});
 await writeFile(join(config,'settings.json'),JSON.stringify({revision:0,defaultPreset:policy,pinned:[],hidden:[],defaultModel:selection,observation:{capturePayloads:true}}),{mode:0o600});
 const env=Object.fromEntries(Object.entries(process.env).filter(([k])=>!/^(AUGMENTOR_|DSH_|PI_)/.test(k)));
 Object.assign(env,{HOME:root,XDG_CONFIG_HOME:join(root,'xdg-config'),XDG_STATE_HOME:join(root,'xdg-state'),XDG_DATA_HOME:join(root,'xdg-data'),XDG_CACHE_HOME:join(root,'xdg-cache'),XDG_RUNTIME_DIR:runtime,AUGMENTOR_PI_CONFIG:config,AUGMENTOR_PI_STATE:state,AUGMENTOR_SHARED_STATE:join(root,'shared-state'),AUGMENTOR_SHARED_DATA:join(root,'shared-data'),AUGMENTOR_PI_LINUX_TOOLS:desktopMode?'1':'0',AUGMENTOR_DESKTOP_NO_AUTOSTART:'1',AUGMENTOR_HARNESS:'1',PI_OFFLINE:'1'});
 // Keep only the explicitly resolved component interpreter in this private
 // profile; source Windows proofs use the hash-locked prepared interpreter.
 env.AUGMENTOR_PYTHON=pythonExecutable();
 if(desktopMode&&process.platform==='darwin'){
  // Satisfy the existing installed-helper presence gate in this synthetic profile.
  // Actual control goes to the private wire peer; this stub cannot capture/input.
  env.AUGMENTOR_MACOS_HELPER=join(root,'synthetic-macos-helper');await writeFile(env.AUGMENTOR_MACOS_HELPER,'#!/bin/sh\nexit 3\n',{mode:0o700});
 }
 const source=resolve(process.env.AUGMENTOR_PI_TEST_ROOT??'.');
 async function start(){
  errors='';child=spawn(process.execPath,[join(source,'dist/runtime/src/main.js')],{env,cwd:workspace,stdio:['ignore','pipe','pipe']});children.push(child);let ready=false;
  child.stdout.on('data',data=>{for(const line of String(data).split('\n'))try{if(JSON.parse(line).ready)ready=true;}catch{}});child.stderr.on('data',data=>errors+=data);
  await until(()=>{assert.equal(child.exitCode,null,errors);return ready;},'owner startup');
  const socket=localConnect(join(state,'runtime.sock'));await once(socket,'connect');owner=new PiConnection(socket,frame=>frames.push(frame));connections.push(owner);await owner.call('host.hello',{protocol:'augmentor-pi/1'});
 }
 async function stop(){owner?.close();if(child?.exitCode===null&&child.signalCode===null){const ended=once(child,'exit');child.kill('SIGTERM');await ended;}}
 async function crash(){owner?.close();if(child?.exitCode===null&&child.signalCode===null){const ended=once(child,'exit');child.kill('SIGKILL');await ended;}}
 t.after(async()=>{for(const connection of connections)connection.close();for(const process of children)if(process.exitCode===null&&process.signalCode===null){const ended=once(process,'exit');process.kill('SIGTERM');await ended;}model.closeAllConnections();await new Promise(done=>model.close(done));await desktop?.close();await rm(root,{recursive:true,force:true,maxRetries:5,retryDelay:100});});
 await start();
 const call=(method,params={})=>owner.call(method,params);
 const settled=sid=>until(async()=>!(await call('session.list')).items.find(m=>m.sessionId===sid)?.running,'settled '+sid);
 async function prompt(sid,op,{wait=true}={}){const result=await call('session.prompt',{sessionId:sid,requestId:crypto.randomUUID(),content:[{type:'text',text:JSON.stringify(op)}]});if(wait)await settled(sid);return result;}
 async function native(sid){const meta=JSON.parse(await readFile(join(state,'sessions',sid+'.meta.json'),'utf8'));return {file:meta.file,bytes:await readFile(meta.file)};}
 const link=()=>readFile(join(state,'harness.json'),'utf8').then(JSON.parse);
 return {root,env,workspace,state,config,selection,requests,frames,desktop,call,prompt,settled,native,link,stop,crash,start,errors:()=>errors};
}
