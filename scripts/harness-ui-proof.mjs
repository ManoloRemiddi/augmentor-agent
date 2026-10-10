// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Isolated real-Pi/browser fixture. No private source, models or histories are copied.
import http from 'node:http';
import {once} from 'node:events';
import {spawn} from 'node:child_process';
import {mkdtempSync,mkdirSync,writeFileSync,appendFileSync,readFileSync,existsSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
const source=resolve(process.env.AUGMENTOR_PI_TEST_ROOT??fileURLToPath(new URL('..',import.meta.url)));
const root=mkdtempSync(join(tmpdir(),'augmentor-harness-ui-'));
const config=join(root,'config'),state=join(root,'state'),workspace=join(root,'work');
const sharedState=join(root,'shared-state'),sharedData=join(root,'shared-data'),home=join(root,'home');
const requestLog=process.env.AUGMENTOR_HARNESS_PROOF_RECORD_REQUESTS==='1'?join(root,'requests.jsonl'):null;
mkdirSync(join(config,'agent'),{recursive:true});mkdirSync(workspace);mkdirSync(home);
writeFileSync(join(workspace,'note.txt'),'Harness fixture ready.\n');
const model=http.createServer(async(req,res)=>{
  if(req.url!='/v1/chat/completions'){res.writeHead(404).end();return;}
  let raw='';for await(const chunk of req)raw+=chunk;
  const body=JSON.parse(raw),afterTool=body.messages.at(-1)?.role==='tool';
  if(requestLog)appendFileSync(requestLog,JSON.stringify(body)+'\n',{mode:0o600});
  res.writeHead(200,{'content-type':'text/event-stream'});
  const chunk=(delta,finish=null,usage)=>res.write('data: '+JSON.stringify({id:'fixture',object:'chat.completion.chunk',model:'harness-fixture',choices:[{index:0,delta,finish_reason:finish}],...(usage?{usage}:{})})+'\n\n');
  const lastUser=[...body.messages].reverse().find(message=>message.role==='user');
  if(body.messages.some(message=>['system','developer'].includes(message.role)&&JSON.stringify(message.content).includes('Inline editor override:'))){
    const draft=typeof lastUser?.content==='string'?lastUser.content:lastUser?.content?.map(part=>part.text??'').join('');
    if(draft?.includes('IMPROVE_SLOW')){const timer=setInterval(()=>chunk({content:' '}),50);res.once('close',()=>clearInterval(timer));return;}
    if(draft?.includes('IMPROVE_TOOL'))chunk({role:'assistant',tool_calls:[{index:0,id:'forbidden',type:'function',function:{name:'bash',arguments:JSON.stringify({command:'touch '+join(workspace,'must-not-exist')})}}]},'tool_calls');
    else chunk({role:'assistant',content:draft?.includes('IMPROVE_INVALID')?'not json':JSON.stringify({kind:'rewrite',text:'Improved '+draft})},draft?.includes('IMPROVE_TRUNCATED')?'length':'stop',{prompt_tokens:81,completion_tokens:12,total_tokens:93});
    res.end('data: [DONE]\n\n');return;
  }
  const original=[...body.messages].reverse().filter(message=>message.role==='user').map(message=>JSON.stringify(message.content)).find(content=>content.includes('EMPTY_FIXTURE')||content.includes('RECOVER_FIXTURE'));
  if(original){
    const recovering=JSON.stringify(body.messages).includes('Execution recovery:');
    if(original.includes('EMPTY_FIXTURE')||!recovering)chunk({role:'assistant',reasoning_content:'Synthetic reasoning-only recovery fixture.'},'length');
    else chunk({role:'assistant',content:'The recovery fixture produced this public answer. Task success remains unverified by this synthetic provider.'},'stop');
    res.end('data: [DONE]\n\n');return;
  }

  if(JSON.stringify(lastUser?.content).includes('SLOW')){
    chunk({role:'assistant',reasoning_content:'This is the isolated interruption fixture.'});
    const timer=setInterval(()=>chunk({content:'Partial fixture output. '}),300);
    res.on('close',()=>clearInterval(timer));return;
  }
  if(!afterTool){
    chunk({role:'assistant',reasoning_content:'I will inspect the isolated fixture note.'});
    chunk({tool_calls:[{index:0,id:'fixture_read',type:'function',function:{name:'read',arguments:JSON.stringify({path:join(workspace,'note.txt')})}}]},'tool_calls');
  }else{
    chunk({role:'assistant',reasoning_content:'The read tool returned the fixture note.'});
    chunk({content:'The note says: Harness fixture ready. The real Pi session executed one read tool; this provider is a deterministic test fixture.'},'stop',{prompt_tokens:640,completion_tokens:45,total_tokens:685});
  }
  res.end('data: [DONE]\n\n');
});
model.listen(0,'127.0.0.1');await once(model,'listening');
const selection={provider:'fixture',model:'harness-fixture'};
writeFileSync(join(config,'agent/models.json'),JSON.stringify({providers:{fixture:{api:'openai-completions',baseUrl:'http://127.0.0.1:'+model.address().port+'/v1',apiKey:'synthetic-not-a-real-key',models:[{id:selection.model,name:'Harness deterministic fixture',reasoning:true,compat:{supportsReasoningEffort:true},input:['text','image'],contextWindow:32000,maxTokens:2048}]}}}));
writeFileSync(join(config,'settings.json'),JSON.stringify({revision:0,defaultPreset:'workspace-write',defaultModel:selection,pinned:[],hidden:[],observation:{capturePayloads:true}}));
const lazy=process.env.AUGMENTOR_HARNESS_PROOF_LAZY==='1';
const fixtureEnv={...process.env,HOME:home,XDG_CONFIG_HOME:join(root,'xdg-config'),XDG_STATE_HOME:join(root,'xdg-state'),XDG_DATA_HOME:join(root,'xdg-data'),XDG_CACHE_HOME:join(root,'xdg-cache'),AUGMENTOR_PI_CONFIG:config,AUGMENTOR_PI_STATE:state,AUGMENTOR_SHARED_STATE:sharedState,AUGMENTOR_SHARED_DATA:sharedData,AUGMENTOR_PI_LINUX_TOOLS:'0',AUGMENTOR_HARNESS:lazy?'0':'1',PI_OFFLINE:'1'};
const prompts=process.env.AUGMENTOR_HARNESS_PROOF_PROMPTS==='1'?spawn(process.env.AUGMENTOR_PYTHON??'python3',['-Xutf8','-B',join(source,'services/prompt-library/service.py')],{cwd:workspace,env:fixtureEnv,stdio:['ignore','ignore','pipe']}):null;
prompts?.stderr.on('data',data=>process.stderr.write(data));
prompts?.on('error',error=>process.stderr.write('Fixture prompt service: '+error.message+'\n'));
// Wait for our service before the runtime can try to auto-start a companion.
if(prompts){
  const end=Date.now()+5000;
  while(!existsSync(join(sharedState,'prompts.sock'))){
    if(prompts.exitCode!==null||Date.now()>end){prompts.kill('SIGTERM');model.closeAllConnections();model.close();rmSync(root,{recursive:true,force:true});throw Error('Fixture prompt service did not start');}
    await new Promise(resolve=>setTimeout(resolve,25));
  }
}
const child=spawn(process.execPath,[join(source,'dist/runtime/src/main.js')],{cwd:workspace,
  env:fixtureEnv,stdio:['ignore','pipe','pipe']});
child.stderr.on('data',data=>process.stderr.write(data));
let closing=false;
async function close(){
  if(closing)return;closing=true;
  for(const owned of [child,prompts])if(owned?.pid&&owned.exitCode===null){const exit=once(owned,'exit');owned.kill('SIGTERM');await exit;}
  model.closeAllConnections();await new Promise(resolve=>model.close(resolve));
  rmSync(root,{recursive:true,force:true});
}
process.on('SIGINT',()=>void close());process.on('SIGTERM',()=>void close());
const deadline=Date.now()+20000;
while(!existsSync(join(state,lazy?'runtime.sock':'harness.json'))){
  if(child.exitCode!==null){await close();throw Error('Fixture runtime stopped before readiness');}
  if(Date.now()>deadline){await close();throw Error('Fixture readiness timed out');}
  await new Promise(resolve=>setTimeout(resolve,25));
}
const link=lazy?{url:null}:JSON.parse(readFileSync(join(state,'harness.json'),'utf8'));
console.log(JSON.stringify({fixture:true,url:link.url,workspace,config,state,home,sharedState,sharedData,pid:child.pid,requestLog}));
await once(child,'exit');await close();
