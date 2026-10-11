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
export async function until(fn,label,ms=15000){const end=Date.now()+ms;while(Date.now()<end){if(await fn())return;await delay(25);}throw Error('Plan fixture timeout: '+label);}
export async function planFixture(t,{policy='danger-full-access'}={}){
 const root=await mkdtemp(join(tmpdir(),'augmentor-plan-')),config=join(root,'config'),state=join(root,'state'),workspace=join(root,'work');
 for(const path of [join(config,'agent'),workspace])await mkdir(path,{recursive:true,mode:0o700});
 const requests=[],children=[],connections=[];let child,owner,errors='';
 const model=http.createServer(async(req,res)=>{
  if(req.url!='/v1/chat/completions'){res.writeHead(404).end();return;}
  let raw='';for await(const bytes of req)raw+=bytes;const body=JSON.parse(raw);requests.push(body);
  const user=body.messages.findLast(message=>message.role==='user'),text=typeof user?.content==='string'?user.content:user?.content?.map(p=>p.text??'').join('');
  let op;try{op=JSON.parse(text);}catch{op={kind:'read'};}
  res.writeHead(200,{'content-type':'text/event-stream'});
  const send=(delta,finish=null)=>res.write('data: '+JSON.stringify({id:'plan-fixture',object:'chat.completion.chunk',model:'plan-fixture',choices:[{index:0,delta,finish_reason:finish}]})+'\n\n');
  const last=body.messages.at(-1),proposal=body.messages.findLast(m=>m.role==='assistant'&&m.tool_calls?.length),toolName=proposal?.tool_calls?.at(-1)?.function?.name;
  if(last?.role!=='tool')send({role:'assistant',tool_calls:[{index:0,id:'plan-read-call',type:'function',function:{name:'plan_read',arguments:'{}'}}]},'tool_calls');
  else if(toolName==='plan_read'&&op.kind==='update'){
   const result=JSON.parse(last.content),args={expectedRevision:op.expectedRevision??result.revision,title:op.title,steps:op.steps};
   send({role:'assistant',tool_calls:[{index:0,id:'plan-update-call',type:'function',function:{name:'plan_update',arguments:JSON.stringify(args)}}]},'tool_calls');
  }else if(op.slow){send({role:'assistant',content:'Synthetic provider holding after the recorded plan. '});const timer=setInterval(()=>send({content:' '}),100);res.once('close',()=>clearInterval(timer));return;}
  else send({role:'assistant',content:'Synthetic planning reply. The tools report progress without verifying task completion.'},'stop');
  res.end('data: [DONE]\n\n');
 });model.listen(0,'127.0.0.1');await once(model,'listening');
 const selection={provider:'fixture',model:'plan-fixture'};
 await writeFile(join(config,'agent','models.json'),JSON.stringify({providers:{fixture:{api:'openai-completions',baseUrl:'http://127.0.0.1:'+model.address().port+'/v1',apiKey:'synthetic-plan-key',models:[{id:selection.model,name:'Synthetic planning provider',reasoning:false,input:['text'],contextWindow:131072,maxTokens:2048}]}}}),{mode:0o600});
 await writeFile(join(config,'settings.json'),JSON.stringify({revision:0,defaultPreset:policy,pinned:[],hidden:[],defaultModel:selection,observation:{capturePayloads:true}}),{mode:0o600});
 const env=Object.fromEntries(Object.entries(process.env).filter(([k])=>!/^(AUGMENTOR_|DSH_|PI_)/.test(k)));
 Object.assign(env,{HOME:root,XDG_CONFIG_HOME:join(root,'xdg-config'),XDG_STATE_HOME:join(root,'xdg-state'),XDG_DATA_HOME:join(root,'xdg-data'),XDG_CACHE_HOME:join(root,'xdg-cache'),AUGMENTOR_PI_CONFIG:config,AUGMENTOR_PI_STATE:state,AUGMENTOR_SHARED_STATE:join(root,'shared-state'),AUGMENTOR_SHARED_DATA:join(root,'shared-data'),AUGMENTOR_PI_LINUX_TOOLS:'0',AUGMENTOR_HARNESS:'1',PI_OFFLINE:'1'});
 const source=resolve(process.env.AUGMENTOR_PI_TEST_ROOT??'.');
 async function start(){
  errors='';child=spawn(process.execPath,[join(source,'dist/runtime/src/main.js')],{env,cwd:workspace,stdio:['ignore','pipe','pipe']});children.push(child);let ready=false;
  child.stdout.on('data',data=>{for(const line of String(data).split('\n'))try{if(JSON.parse(line).ready)ready=true;}catch{}});child.stderr.on('data',data=>errors+=data);
  await until(()=>{assert.equal(child.exitCode,null,errors);return ready;},'owner startup');
  const socket=localConnect(join(state,'runtime.sock'));await once(socket,'connect');owner=new PiConnection(socket);connections.push(owner);await owner.call('host.hello',{protocol:'augmentor-pi/1'});
 }
 async function stop(){owner?.close();if(child?.exitCode===null&&child.signalCode===null){const ended=once(child,'exit');child.kill('SIGTERM');await ended;}}
 t.after(async()=>{for(const connection of connections)connection.close();for(const process of children)if(process.exitCode===null&&process.signalCode===null){const ended=once(process,'exit');process.kill('SIGTERM');await ended;}model.closeAllConnections();await new Promise(done=>model.close(done));await rm(root,{recursive:true,force:true,maxRetries:5,retryDelay:100});});
 await start();
 const call=(method,params={})=>owner.call(method,params);
 const settled=sid=>until(async()=>!(await call('session.list')).items.find(m=>m.sessionId===sid)?.running,'settled '+sid);
 async function prompt(sid,op,{wait=true}={}){const result=await call('session.prompt',{sessionId:sid,requestId:crypto.randomUUID(),content:[{type:'text',text:JSON.stringify(op)}]});if(wait)await settled(sid);return result;}
 async function native(sid){const meta=JSON.parse(await readFile(join(state,'sessions',sid+'.meta.json'),'utf8'));return {file:meta.file,bytes:await readFile(meta.file)};}
 const link=()=>readFile(join(state,'harness.json'),'utf8').then(JSON.parse);
 return {root,env,workspace,state,config,selection,requests,call,prompt,settled,native,link,stop,start,errors:()=>errors};
}
