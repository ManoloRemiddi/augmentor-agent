// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Isolated real-Pi/browser fixture. No private source, models or histories are copied.
import http from 'node:http';
import {once} from 'node:events';
import {spawn} from 'node:child_process';
import {mkdtempSync,mkdirSync,writeFileSync,appendFileSync,readFileSync,existsSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {randomUUID,createHash} from 'node:crypto';
import {SessionManager} from '@earendil-works/pi-coding-agent';
import {serveContextProvider} from './fixtures/context-provider-http.mjs';
const source=resolve(process.env.AUGMENTOR_PI_TEST_ROOT??fileURLToPath(new URL('..',import.meta.url)));
const root=mkdtempSync(join(tmpdir(),'augmentor-harness-ui-'));
const config=join(root,'config'),state=join(root,'state'),workspace=join(root,'work');
const sharedState=join(root,'shared-state'),sharedData=join(root,'shared-data'),home=join(root,'home');
const wikiVault=process.env.AUGMENTOR_HARNESS_PROOF_WIKI==='1'?join(root,'wiki-vault'):null;
const wikiExtension=process.env.AUGMENTOR_HARNESS_PROOF_WIKI_SETTINGS==='1'?join(root,'wiki-settings-resource.mjs'):null;
const requestLog=process.env.AUGMENTOR_HARNESS_PROOF_RECORD_REQUESTS==='1'?join(root,'requests.jsonl'):null;
const discoveryLog=process.env.AUGMENTOR_HARNESS_PROOF_MODEL_DISCOVERY==='1'?join(root,'model-listings.jsonl'):null;
const providerApi=process.env.AUGMENTOR_HARNESS_PROOF_PROVIDER_API??'openai-completions';
let releaseArguments=null;
if(!['openai-completions','anthropic-messages','openai-responses','google-generative-ai'].includes(providerApi))throw Error('Unsupported authored provider fixture.');
mkdirSync(join(config,'agent'),{recursive:true});mkdirSync(workspace);mkdirSync(home);
writeFileSync(join(workspace,'note.txt'),'Harness fixture ready.\n');
if(process.env.AUGMENTOR_HARNESS_PROOF_QUESTIONS==='1'){
 const extension=join(root,'question-ui.mjs');
 writeFileSync(extension,`export default pi=>pi.registerTool({name:'ask_user',label:'Fixture question',description:'Ask an independently authored test question; no external action.',parameters:{type:'object',properties:{}},async execute(_id,_args,signal,_update,ctx){const answer=await ctx.ui.select('Keep the authored fixture going?',['Keep going','Stop here'],{timeout:3000,signal});return {content:[{type:'text',text:answer===undefined?'No fixture answer.':'Fixture choice: '+answer}],details:{}};}});`);
 writeFileSync(join(config,'resources.json'),JSON.stringify({sources:[extension],skills:[]}));
}
if(wikiVault){
 mkdirSync(join(wikiVault,'.raw'),{recursive:true});writeFileSync(join(wikiVault,'.raw/source.txt'),'AUTHORED WIKI RAW SOURCE\n');
 if(process.env.AUGMENTOR_HARNESS_PROOF_WIKI_FAILURE==='1'){mkdirSync(join(wikiVault,'.archive'));writeFileSync(join(wikiVault,'.raw/conflict.txt'),'AUTHORED NEW RAW');writeFileSync(join(wikiVault,'.archive/conflict.txt'),'AUTHORED OLDER ARCHIVE');}
 writeFileSync(join(config,'wiki.json'),JSON.stringify({schema:'augmentor-wiki/1',enabled:true,vaultPath:wikiVault}),{mode:0o600});
}
if(wikiExtension){writeFileSync(wikiExtension,`import {existsSync} from 'node:fs';export default pi=>{if(existsSync(${JSON.stringify(wikiExtension+'.collision')}))pi.registerTool({name:'wiki_query',label:'Authored collision',description:'Authored reload collision',parameters:{type:'object',properties:{}},execute:async()=>({content:[{type:'text',text:'MUST NOT RUN'}]})});};`);writeFileSync(join(config,'resources.json'),JSON.stringify({sources:[wikiExtension],skills:[]}));}
const model=http.createServer(async(req,res)=>{
  if(process.env.AUGMENTOR_HARNESS_PROOF_NESTED_TOOLS==='1'&&req.method==='POST'&&req.url==='/fixture/release-nested'){
    writeFileSync(join(root,'release-nested'),'Authored fixture release.');res.writeHead(204).end();return;
  }
  if(process.env.AUGMENTOR_HARNESS_PROOF_TOOL_ARGUMENTS==='1'&&req.method==='POST'&&req.url==='/fixture/release-arguments'){
    if(!releaseArguments){res.writeHead(409).end();return;}releaseArguments();res.writeHead(204).end();return;
  }
  if(discoveryLog&&req.method==='GET'&&new URL(req.url,'http://fixture.invalid').pathname.endsWith('/models')){
    appendFileSync(discoveryLog,JSON.stringify({url:req.url,headers:req.headers})+'\n',{mode:0o600});
    if(req.url.startsWith('/slow/')){res.once('close',()=>appendFileSync(discoveryLog,JSON.stringify({closed:true,url:req.url})+'\n',{mode:0o600}));return;}
    res.writeHead(200,{'content-type':'application/json'});res.end(JSON.stringify({has_more:true,data:[{id:'harness-fixture',name:'Existing fixture'},{id:'authored-listed',name:'Authored discovered model',context_window:16000,max_output_tokens:512}]}));return;
  }
  if(providerApi!=='openai-completions'){await serveContextProvider(providerApi,req,res,{path:join(workspace,'note.txt'),requestLog});return;}
  if(req.url!='/v1/chat/completions'){res.writeHead(404).end();return;}
  let raw='';for await(const chunk of req)raw+=chunk;
  const body=JSON.parse(raw),afterTool=body.messages.at(-1)?.role==='tool';
  if(requestLog)appendFileSync(requestLog,JSON.stringify(body)+'\n',{mode:0o600});
  res.writeHead(200,{'content-type':'text/event-stream'});
  const chunk=(delta,finish=null,usage)=>res.write('data: '+JSON.stringify({id:'fixture',object:'chat.completion.chunk',model:'harness-fixture',choices:[{index:0,delta,finish_reason:finish}],...(usage?{usage}:{})})+'\n\n');
  const lastUser=[...body.messages].reverse().find(message=>message.role==='user');
  const wikiUser=wikiVault?[...body.messages].reverse().find(message=>message.role==='user'&&JSON.stringify(message.content).includes('WIKI_')):undefined;
  if(wikiUser){
    if(JSON.stringify(wikiUser.content).includes('WIKI_SETTINGS_HOLD')){res.write(': Authored held provider request.\n\n');return;}
    if(JSON.stringify(wikiUser.content).includes('WIKI_BROWSER_CATALOG')||JSON.stringify(wikiUser.content).includes('WIKI_SETTINGS_CATALOG')){chunk({role:'assistant',content:'Authored browser catalog inspection only.'},'stop',{prompt_tokens:10,completion_tokens:10,total_tokens:20});res.end('data: [DONE]\n\n');return;}
    const reviewNext=JSON.stringify(wikiUser.content).includes('WIKI_REVIEW_NEXT');
    const readonly=JSON.stringify(wikiUser.content).includes('WIKI_READONLY');
    const unknown=JSON.stringify(wikiUser.content).includes('WIKI_UNKNOWN');
    const sequence=unknown?[['wiki_archive',{source_path:'.raw/conflict.txt'}],['wiki_write',{type:'concept',title:'Never Reached',content:'MUST NOT WRITE AFTER UNCERTAINTY'}]]:readonly?[
      ['wiki_write',{type:'concept',title:'Not Allowed',content:'READONLY MUST NOT WRITE'}],
      ['wiki_query',{query:'Authored',mode:'quick'}],
    ]:reviewNext?[['wiki_scaffold',{mode:'generic',purpose:'Authored explicit review qualification'}],['wiki_write',{type:'concept',title:'After Explicit Review',content:'AUTHORED NEW INTENT AFTER REVIEW'}]]:[
      ['wiki_scaffold',{mode:'generic',purpose:'Independent Augmentor wiki qualification'}],
      ['wiki_query',{query:'Authored',mode:'quick'}],
      ['wiki_write',{type:'concept',title:'Authored Page',content:'AUTHORED WIKI CONTENT',source_path:'.raw/source.txt'}],
      ['wiki_write',{type:'concept',title:'Authored Link',content:'See [[Authored Page]].'}],
      ['wiki_rename',{title:'Authored Page',new_title:'Renamed Authored Page'}],
      ['wiki_archive',{source_path:'.raw/source.txt'}],
      ['wiki_lint',{}],
      ['wiki_query',{query:'AUTHORED WIKI CONTENT',mode:'standard'}],
    ];
    const step=body.messages.filter(message=>message.role==='tool').length;
    if(step<sequence.length){const [name,args]=sequence[step];chunk({role:'assistant',tool_calls:[{index:0,id:'wiki_'+step,type:'function',function:{name,arguments:JSON.stringify(args)}}]},'tool_calls');}
    else chunk({role:'assistant',content:'The authored Wiki sequence ended; effects require independent verification.'},'stop',{prompt_tokens:100,completion_tokens:20,total_tokens:120});
    res.end('data: [DONE]\n\n');return;
  }
  if(process.env.AUGMENTOR_HARNESS_PROOF_NESTED_TOOLS==='1'&&JSON.stringify(lastUser?.content).includes('NESTED_TRAJECTORY')){
    if(!afterTool)chunk({role:'assistant',tool_calls:[{index:0,id:'fixture_nested_root',type:'function',function:{name:'fixture_outer',arguments:JSON.stringify({path:join(workspace,'note.txt'),label:JSON.stringify(lastUser.content).includes('STOP')?'nested-stop':'nested-complete'})}}]},'tool_calls');
    else chunk({role:'assistant',content:'The authored nested trajectory fixture finished.'},'stop',{prompt_tokens:100,completion_tokens:20,total_tokens:120});
    res.end('data: [DONE]\n\n');return;
  }
  if(process.env.AUGMENTOR_HARNESS_PROOF_TOOL_ARGUMENTS==='1'&&JSON.stringify(lastUser?.content).includes('ARGUMENT_STREAM')){
    if(afterTool){chunk({role:'assistant',content:'The authored argument stream completed one real read.'},'stop',{prompt_tokens:100,completion_tokens:20,total_tokens:120});res.end('data: [DONE]\n\n');return;}
    const args=JSON.stringify({path:join(workspace,'note.txt')}),middle=Math.floor(args.length/2),almost=args.length-3;
    chunk({role:'assistant',tool_calls:[{index:0,id:'fixture_argument_read',type:'function',function:{name:'read',arguments:args.slice(0,middle)}}]});
    let middleSent=false;
    const timer=setTimeout(()=>{middleSent=true;chunk({tool_calls:[{index:0,function:{arguments:args.slice(middle,almost)}}]});},100);
    const release=()=>{clearTimeout(timer);releaseArguments=null;chunk({tool_calls:[{index:0,function:{arguments:args.slice(middleSent?almost:middle)}}]},'tool_calls');res.end('data: [DONE]\n\n');};
    releaseArguments=release;res.once('close',()=>{clearTimeout(timer);if(releaseArguments===release)releaseArguments=null;});return;
  }
  if(process.env.AUGMENTOR_HARNESS_PROOF_QUESTIONS==='1'&&JSON.stringify(lastUser?.content).includes('QUESTION_FIXTURE')){
    if(!afterTool)chunk({role:'assistant',tool_calls:[{index:0,id:'authored_question',type:'function',function:{name:'ask_user',arguments:'{}'}}]},'tool_calls');
    else chunk({role:'assistant',content:'Original question answer received: '+JSON.stringify(body.messages.at(-1).content)},'stop',{prompt_tokens:100,completion_tokens:20,total_tokens:120});
    res.end('data: [DONE]\n\n');return;
  }
  if(body.messages.some(message=>['system','developer'].includes(message.role)&&JSON.stringify(message.content).includes('context summarization assistant'))){
    chunk({role:'assistant',content:'# Goal\nPreserve the authored summary fixture.\n# Progress\nSynthetic history only.\n# Next steps\nContinue explicitly.'},'stop',{prompt_tokens:6000,completion_tokens:40,total_tokens:6040});res.end('data: [DONE]\n\n');return;
  }
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
  if(process.env.AUGMENTOR_HARNESS_PROOF_FILE_PREVIEWS==='1'){
    chunk({role:'assistant',content:'Authored fixture preview link: [Open exact line](pages.txt#L350).'},'stop',{prompt_tokens:10,completion_tokens:10,total_tokens:20});res.end('data: [DONE]\n\n');return;
  }
  if(!afterTool){
    chunk({role:'assistant',reasoning_content:'I will inspect the isolated fixture note.'});
    chunk({tool_calls:[{index:0,id:'fixture_read',type:'function',function:{name:'read',arguments:JSON.stringify({path:process.env.AUGMENTOR_HARNESS_PROOF_REFERENCES==='1'?join(workspace,'docs','a note.txt'):process.env.AUGMENTOR_HARNESS_PROOF_ATTACHMENTS==='1'?(()=>{const text=typeof lastUser.content==='string'?lastUser.content:lastUser.content.map(p=>p.text??'').join('');const row=text.split('\n').find(line=>line.startsWith('{"name":'));return row?JSON.parse(row).path:join(workspace,'note.txt');})():join(workspace,'note.txt')})}}]},'tool_calls');
  }else{
    chunk({role:'assistant',reasoning_content:'The read tool returned the fixture note.'});
    chunk({content:'The note says: Harness fixture ready. The real Pi session executed one read tool; this provider is a deterministic test fixture.'},'stop',{prompt_tokens:640,completion_tokens:45,total_tokens:685});
  }
  res.end('data: [DONE]\n\n');
});
model.listen(0,'127.0.0.1');await once(model,'listening');
const selection={provider:'fixture',model:'harness-fixture'};
// Anthropic's client appends /v1/messages; the other fixture clients use /v1
// as their base. This is test endpoint configuration, never owner model setup.
writeFileSync(join(config,'agent/models.json'),JSON.stringify({providers:{fixture:{api:providerApi,baseUrl:'http://127.0.0.1:'+model.address().port+(providerApi==='anthropic-messages'?'':'/v1'),apiKey:'synthetic-not-a-real-key',models:[{id:selection.model,name:'Harness deterministic fixture',reasoning:providerApi==='openai-completions',...(providerApi==='openai-completions'?{compat:{supportsReasoningEffort:true}}:{}),input:['text','image'],contextWindow:32000,maxTokens:2048}]}}}));
writeFileSync(join(config,'settings.json'),JSON.stringify({revision:0,defaultPreset:wikiVault?'danger-full-access':'workspace-write',defaultModel:selection,pinned:[],hidden:[],observation:{capturePayloads:true}}));
if(wikiVault){mkdirSync(join(state,'sessions'),{recursive:true});writeFileSync(join(state,'sessions','wiki-readonly.meta.json'),JSON.stringify({id:'wiki-readonly',cwd:workspace,selection,title:'Authored read-only Wiki fixture',saved:false,policy:'read-only',updatedAt:1,requests:[],running:false}),{mode:0o600});}
// Large independently authored native context exercises default Pi compaction;
// these saved messages do not represent executed actions or private history.
if(process.env.AUGMENTOR_HARNESS_PROOF_COMPACTION==='1'){
 const sid='compact-fixture',manager=SessionManager.create(workspace,join(state,'sessions',sid));manager.appendModelChange(selection.provider,selection.model);manager.appendThinkingLevelChange('off');
 const assistant=text=>({role:'assistant',content:[{type:'text',text}],api:'openai-completions',provider:selection.provider,model:selection.model,stopReason:'stop',timestamp:1,usage:{input:0,output:0,cacheRead:0,cacheWrite:0,totalTokens:0,cost:{input:0,output:0,cacheRead:0,cacheWrite:0,total:0}}});
 manager.appendMessage({role:'user',content:'Old authored context '+ 'x'.repeat(12000),timestamp:1});manager.appendMessage(assistant('Old authored answer '+ 'y'.repeat(12000)));manager.appendMessage({role:'user',content:'Kept authored context '+ 'z'.repeat(80000),timestamp:2});manager.appendMessage(assistant('Keep this authored answer.'));
 writeFileSync(join(state,'sessions',sid+'.meta.json'),JSON.stringify({id:sid,cwd:workspace,file:manager.getSessionFile(),selection,title:'Synthetic Compact fixture',saved:false,policy:'read-only',updatedAt:1,requests:[],running:false}),{mode:0o600});
}
// Independently authored saved fixture state; no executed actions are fabricated.
if(process.env.AUGMENTOR_HARNESS_PROOF_CONTEXT_HISTORY==='1'){
 const sid='context-history-proof',directory=join(state,'observations',sid),time=Date.now();mkdirSync(directory,{recursive:true,mode:0o700});mkdirSync(join(state,'sessions'),{recursive:true,mode:0o700});
 const manager=SessionManager.create(workspace,join(state,'sessions',sid));manager.appendModelChange(selection.provider,selection.model);
 writeFileSync(join(state,'sessions',sid+'.meta.json'),JSON.stringify({id:sid,cwd:workspace,file:manager.getSessionFile(),selection,title:'Synthetic recorded Context history',saved:true,policy:'read-only',updatedAt:time,requests:[],running:false}),{mode:0o600});
 const records=[];
 for(let i=0;i<12;i++){
  const id='context-request-'+i,seq=i*12+1,payload=i===2?{contents:[{role:'user',parts:[{text:'Unsupported authored format'}]}]}:{messages:[{role:'system',content:'AUTHORED_HEADER_'+i},{role:'user',content:'AUTHORED_INPUT_'+i},{role:'assistant',content:'',tool_calls:[{id:'authored-call-'+i,function:{name:'read',arguments:JSON.stringify({path:'authored-note-'+i+'.txt'})}}]},{role:'tool',tool_call_id:'authored-call-'+i,content:'AUTHORED_RESULT_'+i}],tools:[{type:'function',function:{name:'read',parameters:{type:'object'}}}],...(i===3?{padding:'x'.repeat(1024*1024)}:{})},raw=JSON.stringify(payload);
  if(i!==1)writeFileSync(join(directory,id+'.payload.json'),raw,{mode:0o600});
  records.push({protocol:'augmentor-observation/1',id,seq,sessionId:sid,time:time+i,kind:'model/request',turnId:'authored-turn',data:{provider:selection.provider,model:selection.model,capacity:32000},payload:i===1?{state:'disabled'}:{state:'retained',bytes:Buffer.byteLength(raw),sha256:createHash('sha256').update(raw).digest('hex'),redactions:[]}});
  records.push({protocol:'augmentor-observation/1',id:id+'-complete',seq:seq+1,sessionId:sid,time:time+i+1,kind:'model/complete',requestId:id,data:{usage:{input:100+i,output:5,cacheRead:0,cacheWrite:0},durationMs:50}});
  for(let j=2;j<12;j++)records.push({protocol:'augmentor-observation/1',id:id+'-metadata-'+j,seq:seq+j,sessionId:sid,time,kind:'fixture/history',data:{name:'Independently authored saved metadata'}});
 }
 writeFileSync(join(directory,'events.jsonl'),records.map(r=>JSON.stringify(r)+'\n').join(''),{mode:0o600});writeFileSync(join(directory,'counter.json'),JSON.stringify({seq:records.length}),{mode:0o600});
}
if(process.env.AUGMENTOR_HARNESS_PROOF_INDEXED==='1'){
 const sid='trajectory-index-proof',directory=join(state,'observations',sid),time=Date.now();mkdirSync(directory,{recursive:true,mode:0o700});mkdirSync(join(state,'sessions'),{recursive:true,mode:0o700});
 writeFileSync(join(state,'sessions',sid+'.meta.json'),JSON.stringify({id:sid,cwd:workspace,selection,title:'Indexed synthetic metadata',saved:true,policy:'read-only',updatedAt:time,requests:[],running:false}),{mode:0o600});
 const lines=Array.from({length:1100},(_,i)=>{const record={protocol:'augmentor-observation/1',id:randomUUID(),seq:i+1,sessionId:sid,time,kind:'fixture/history',data:{name:'Saved synthetic metadata',marker:i===4?'rare older café':'ordinary metadata '+(i+1)}};
  if(i===6&&process.env.AUGMENTOR_HARNESS_PROOF_PAYLOADS==='1'){const payload=JSON.stringify({authorization:'[Redacted credential field]',text:'EARLY_PAYLOAD_TERM '+ 'x'.repeat(3*1024*1024)+' DEEP_PAYLOAD_NEEDLE 日本語'});writeFileSync(join(directory,record.id+'.payload.json'),payload,{mode:0o600});record.payload={state:'retained',bytes:Buffer.byteLength(payload),sha256:createHash('sha256').update(payload).digest('hex'),redactions:['authorization']};}
  return JSON.stringify(record)+'\n';}).join('');
 writeFileSync(join(directory,'events.jsonl'),lines,{mode:0o600});writeFileSync(join(directory,'counter.json'),JSON.stringify({seq:1100}),{mode:0o600});
}
const lazy=process.env.AUGMENTOR_HARNESS_PROOF_LAZY==='1';
const fixtureEnv={...process.env,HOME:home,XDG_CONFIG_HOME:join(root,'xdg-config'),XDG_STATE_HOME:join(root,'xdg-state'),XDG_DATA_HOME:join(root,'xdg-data'),XDG_CACHE_HOME:join(root,'xdg-cache'),AUGMENTOR_PI_CONFIG:config,AUGMENTOR_PI_STATE:state,AUGMENTOR_SHARED_STATE:sharedState,AUGMENTOR_SHARED_DATA:sharedData,AUGMENTOR_PI_LINUX_TOOLS:'0',AUGMENTOR_HARNESS:lazy?'0':'1',PI_OFFLINE:'1'};
if(process.env.AUGMENTOR_HARNESS_PROOF_NESTED_TOOLS==='1'){
 const extension=join(root,'nested-tools.mjs'),resourcePath=join(config,'resources.json');
 writeFileSync(extension,readFileSync(join(source,'scripts/fixtures/nested-tool-extension.mjs'),'utf8'));
 const resources=existsSync(resourcePath)?JSON.parse(readFileSync(resourcePath,'utf8')):{sources:[],skills:[]};resources.sources.push(extension);writeFileSync(resourcePath,JSON.stringify(resources));
 fixtureEnv.AUGMENTOR_HARNESS_PROOF_NESTED_RELEASE=join(root,'release-nested');
}
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
const startRuntime=()=>{
  const runtime=spawn(process.execPath,[join(source,'dist/runtime/src/main.js')],{cwd:workspace,env:fixtureEnv,stdio:['ignore','pipe','pipe']});
  runtime.stderr.on('data',data=>process.stderr.write(data));return runtime;
};
let child=startRuntime(),closing=false,reopenRequested=false,reopened=false;
async function close(){
  if(closing)return;closing=true;
  for(const owned of [child,prompts])if(owned?.pid&&owned.exitCode===null){const exit=once(owned,'exit');owned.kill('SIGTERM');await exit;}
  model.closeAllConnections();await new Promise(resolve=>model.close(resolve));
  rmSync(root,{recursive:true,force:true});
}
process.on('SIGINT',()=>void close());process.on('SIGTERM',()=>void close());
// Explicit test-only cold reopen: keep independently authored state and the
// synthetic provider, stop the idle Host, then construct a fresh Host process.
process.on('message',message=>{
  if(process.env.AUGMENTOR_HARNESS_PROOF_REOPEN==='1'&&message?.type==='reopen'&&!closing&&!reopenRequested&&child.exitCode===null){reopenRequested=true;child.kill('SIGTERM');}
});
process.channel?.unref();
while(!closing){
  const deadline=Date.now()+20000;
  while(!existsSync(join(state,lazy?'runtime.sock':'harness.json'))){
    if(child.exitCode!==null){await close();throw Error('Fixture runtime stopped before readiness');}
    if(Date.now()>deadline){await close();throw Error('Fixture readiness timed out');}
    await new Promise(resolve=>setTimeout(resolve,25));
  }
  const link=lazy?{url:null}:JSON.parse(readFileSync(join(state,'harness.json'),'utf8'));
  console.log(JSON.stringify({fixture:true,...(reopened?{reopened:true}:{}),url:link.url,workspace,config,state,home,...(wikiVault?{wikiVault}:{}),...(wikiExtension?{wikiExtension}:{}),sharedState,sharedData,pid:child.pid,requestLog,...(discoveryLog?{discoveryLog}:{}),...(process.env.AUGMENTOR_HARNESS_PROOF_TOOL_ARGUMENTS==='1'?{argumentControlUrl:'http://127.0.0.1:'+model.address().port+'/fixture/release-arguments'}:{}),...(process.env.AUGMENTOR_HARNESS_PROOF_NESTED_TOOLS==='1'?{nestedControlUrl:'http://127.0.0.1:'+model.address().port+'/fixture/release-nested'}:{})}));
  await once(child,'exit');
  if(!reopenRequested||closing){await close();break;}
  reopenRequested=false;reopened=true;
  rmSync(join(state,'harness.json'),{force:true});child=startRuntime();
}
