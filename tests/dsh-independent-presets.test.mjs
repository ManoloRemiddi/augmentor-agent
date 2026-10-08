// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Real installed DSH, independently authored fixtures, loopback fake model; no private presets.
import test from 'node:test'
import assert from 'node:assert/strict'
import {createRequire} from 'node:module'
import {pathToFileURL,fileURLToPath} from 'node:url'
import {mkdtempSync,writeFileSync,mkdirSync,rmSync} from 'node:fs'
import {tmpdir} from 'node:os'
import {join,resolve} from 'node:path'
import {createServer} from 'node:http'
import {once} from 'node:events'
const root=process.env.DSH_INSTALL_ROOT

test('real DSH scopes independent persona, tools, sandbox and approval without changing its sibling', {skip:!root,timeout:30000},async()=>{
 const req=createRequire(join(root,'package.json')),load=async n=>import(pathToFileURL(req.resolve('@deepseek-ai/'+n)).href)
 const temp=mkdtempSync(join(tmpdir(),'augmentor-independent-')),repo=fileURLToPath(new URL('../',import.meta.url))
 const priorHome=process.env.DSH_HOME,priorKey=process.env.AUGMENTOR_FIXTURE_KEY
 process.env.DSH_HOME=join(temp,'home');mkdirSync(process.env.DSH_HOME);process.env.AUGMENTOR_FIXTURE_KEY='invented-fixture-key'
 const {Context}=await load('cordis'),{createUserMessage}=await load('dsh-llm')
 const ctx=new Context(),handles=[],requests=[]
 const server=createServer(async(r,s)=>{
  let raw='';for await(const c of r)raw+=c;requests.push(JSON.parse(raw))
  s.writeHead(200,{'content-type':'text/event-stream'});s.end('data: '+JSON.stringify({id:'fixture',object:'chat.completion.chunk',model:'fixture',choices:[{index:0,delta:{role:'assistant',content:'Fixture completed.'},finish_reason:'stop'}]})+'\n\ndata: [DONE]\n\n')
 })
 try{
  await ctx.plugin((await load('cordis-plugin-loader')).default,{baseUrl:pathToFileURL(root+'/').href}).await()
  ctx.loader.builtins.group=(await load('cordis-plugin-loader')).Group
  for(const n of ['dsh-session-projection','dsh-session','dsh-session-persistence-jsonl','dsh-session-query','dsh-llm','dsh-system-prompt','dsh-sandbox-policy','dsh-user-approval','dsh-tools','dsh-agent','dsh-agent-loop','dsh-agent-preset-registry']){
   const m=await load(n),config=n==='dsh-session-persistence-jsonl'?{root:join(temp,'logs')}:n==='dsh-agent-loop'?{agents:[]}:n==='dsh-agent-preset-registry'?{default:'sibling'}:n==='dsh-sandbox-policy'?{mode:'danger-full-access',workspaceRoot:temp}:n==='dsh-user-approval'?{policy:'never'}:{}
   await ctx.plugin(m.default??m,config).await()
  }
  server.listen(0,'127.0.0.1');await once(server,'listening')
  await ctx.plugin(await load('dsh-llm-pi-ai'),{providers:{local:{api:'openai-completions',baseURL:`http://127.0.0.1:${server.address().port}/v1`,apiKeyEnv:'AUGMENTOR_FIXTURE_KEY',models:[{id:'fixture',contextWindow:65536,maxTokens:1024}]}}}).await()
  let inheritedCalls=0
  ctx.tools.register({name:'unrelated_mcp',description:'Sibling tool',parameters:{},output:{schema:{type:'string'},render:(_a,v)=>[{type:'text',text:v}]},execute:()=>{inheritedCalls++;return 'sibling'}})
  const tool=join(temp,'fixture-tool.mjs');writeFileSync(tool,"export const inject=['tools'];export function apply(ctx){ctx.tools.register({name:'fixture_status',description:'Preset status',parameters:{},output:{schema:{type:'string'},render:(_a,v)=>[{type:'text',text:v}]},execute:()=> 'safe'})}")
  await ctx.agentPresets.register({id:'independent',name:'Independent',plugins:[{id:'isolated',name:'cordis:group',group:true,isolate:{skills:true,sandboxPolicy:true,approval:true},config:[
   {id:'skills',name:req.resolve('@deepseek-ai/dsh-skill')},
   {id:'sandbox-policy',name:req.resolve('@deepseek-ai/dsh-sandbox-policy'),config:{mode:'workspace-write',workspaceRoot:temp}},
   {id:'approval',name:req.resolve('@deepseek-ai/dsh-user-approval'),config:{policy:'ask'}},
   {id:'fixture',name:tool},
   {id:'boundary',name:resolve(repo,'adapters/dsh-preset-boundary/index.mjs'),config:{preset:'independent',cwd:temp,tools:['fixture_status']}},
   {id:'persona',name:req.resolve('@deepseek-ai/dsh-persona'),config:{prefix:'Invented independent persona.'}}
  ]}]})
  await ctx.agentPresets.register({id:'sibling',name:'Sibling',plugins:[{id:'persona',name:req.resolve('@deepseek-ai/dsh-persona'),config:{prefix:'Invented sibling persona.'}}]})
  assert.equal((await ctx.agentPresets.list()).find(r=>r.id==='independent').broken,undefined)
  for(const preset of ['independent','sibling']){
   const handle=await ctx.agents.create({sessionId:'fixture-'+preset,meta:{cwd:temp,agentPreset:preset},agentOptions:{provider:'local',model:'fixture'},async setup(c){await ctx.agentPresets.mount(c,preset)}});handles.push(handle)
   handle.agent.followup(createUserMessage({content:[{type:'text',text:'Inspect fixture.'}],source:{kind:'user'}}));await handle.agent.whenIdle()
  }
  assert.equal(requests.length,2)
  const [independent,sibling]=requests
  assert.deepEqual(independent.tools.map(t=>t.function.name),['fixture_status'])
  assert.match(JSON.stringify(independent.messages),/Invented independent persona/);assert.doesNotMatch(JSON.stringify(independent.messages),/Invented sibling persona/)
  assert.match(JSON.stringify(independent.messages),/workspace-write/);assert.match(JSON.stringify(independent.messages),/ask/)
  assert.ok(sibling.tools.some(t=>t.function.name==='unrelated_mcp'));assert.match(JSON.stringify(sibling.messages),/danger-full-access/)
  const execute=(agent,name)=>ctx.tools.execute({callId:'fixture-'+name,name,arguments:{},agent,signal:new AbortController().signal})
  assert.equal((await execute(handles[0].agent,'unrelated_mcp')).isError,true);assert.equal(inheritedCalls,0)
  assert.equal((await execute(handles[1].agent,'unrelated_mcp')).isError,false);assert.equal(inheritedCalls,1)
 }finally{
  for(const h of handles)await h.dispose()
  await ctx.fiber.dispose();server.closeAllConnections();if(server.listening)await new Promise(r=>server.close(r))
  if(priorHome===undefined)delete process.env.DSH_HOME;else process.env.DSH_HOME=priorHome
  if(priorKey===undefined)delete process.env.AUGMENTOR_FIXTURE_KEY;else process.env.AUGMENTOR_FIXTURE_KEY=priorKey
  rmSync(temp,{recursive:true,force:true})
 }
})
