// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test'
import assert from 'node:assert/strict'
import {mkdtempSync,mkdirSync,writeFileSync,readFileSync,rmSync,existsSync,realpathSync} from 'node:fs'
import {tmpdir} from 'node:os'
import {join} from 'node:path'
import {createServer} from 'node:http'
import {fileURLToPath,pathToFileURL} from 'node:url'
import {CodexHost} from '../dist/codex-runtime/src/host.js'
import {CodexIpcServer} from '../dist/codex-runtime/src/ipc.js'
import {ProfileStore} from '../dist/codex-runtime/src/profiles.js'
import {CodexWorkspaces} from '../dist/codex-runtime/src/workspaces.js'
import {CodexWorkspaceBoundary} from '../apps/browser/shared/codex-workspace.mjs'
import {installProfile} from '../services/workspaces/install.mjs'

function fixture(t){
 const root=realpathSync(mkdtempSync(join(tmpdir(),'codex-sdk-'))),profilesDir=join(root,'profiles'),prior=process.env.AUGMENTOR_WORKSPACE_PROFILES
 mkdirSync(profilesDir,{mode:0o700});process.env.AUGMENTOR_WORKSPACE_PROFILES=profilesDir
 t.after(()=>{if(prior===undefined)delete process.env.AUGMENTOR_WORKSPACE_PROFILES;else process.env.AUGMENTOR_WORKSPACE_PROFILES=prior;rmSync(root,{recursive:true,force:true})})
 const module=join(root,'tools.mjs');writeFileSync(module,process.env.AUGMENTOR_SDK_TOOLS_ENTRY?
  `import {createApplicationTools} from ${JSON.stringify(pathToFileURL(process.env.AUGMENTOR_SDK_TOOLS_ENTRY).href)};export function applicationTools(){return createApplicationTools({definitions:[['fixture_read','Read a synthetic record',{}, {type:'object',required:['id','version'],properties:{id:{type:'string'},version:{type:'integer'}}}]],async execute(name,args,execution){globalThis.__codexSdkExecutions??=[];globalThis.__codexSdkExecutions.push(execution.callId);return {id:'synthetic-record',version:1}}})}`:
  `export function applicationTools(){return {tools:[{name:'fixture_read',description:'Read a synthetic record',inputSchema:{type:'object',properties:{},additionalProperties:false}}],async execute(name,args,execution){globalThis.__codexSdkExecutions??=[];globalThis.__codexSdkExecutions.push(execution.callId);return {id:'synthetic-record',version:1}}}}`)
 const instructions=join(root,'role.md');writeFileSync(instructions,'SDK_APPLICATION_ROLE_FIXTURE')
 const profile={schemaVersion:1,sdkProtocol:'augmentor-app/1',harness:'codex',connection:'local',id:'fixture',name:'Fixture',preset:'augmentor-fixture',cwd:root,
  memory:{person:'app-fixture-owner',project:'app-fixture-project'},parentOrigin:'http://127.0.0.1:9876',publicPath:'/augmentor/',
  instructions:[instructions],tools:[{id:'fixture-tools',module,names:['fixture_read'],config:{}}],policy:{tools:['fixture_read'],voice:false,sharedSettings:false}}
 installProfile(profile,{root,home:join(root,'unused-dsh'),profilesDir})
 return {root,profilesDir,profile}
}
test('Codex registration needs no DSH preset and refuses a silent harness or connection migration',t=>{
 const f=fixture(t);assert.equal(existsSync(join(f.root,'unused-dsh')),false)
 assert.equal(JSON.parse(readFileSync(join(f.profilesDir,'fixture.json'))).harness,'codex')
 for(const patch of [{connection:'different'},{harness:'dsh'}])assert.throws(()=>installProfile({...f.profile,...patch},{root:f.root,home:join(f.root,'unused-dsh'),profilesDir:f.profilesDir}),/migration/)
})
test('Codex workspace memory identity cannot be supplied by an app/model or rebound to personal memory',async t=>{
 const f=fixture(t),binding=await new CodexWorkspaces().load('fixture');let received
 const call=binding.memoryCall(async(method,p)=>{received=p;return {person:p.person,project:p.project}})
 await call('memory.dual.bind',{session:'codex:owned',person:'personal',project:'foreign'})
 assert.equal(received.person,f.profile.memory.person);assert.equal(received.project,f.profile.memory.project)
 await assert.rejects(binding.memoryCall(async()=>({person:'personal',project:'foreign'}))('memory.dual.bind',{session:'codex:owned'}),/different workspace/)
})
test('Codex boundary filters history and rejects other app operations and shared configuration',async t=>{
 const f=fixture(t);let lookups=0
 const meta={id:'owned',cwd:f.root,profileId:'local',workspace:{id:'fixture',preset:f.profile.preset,cwd:f.root,connection:'local'}}
 const boundary=new CodexWorkspaceBoundary(async(method,p)=>{
  if(method==='models.list')return {groups:[{provider:'local',models:[{model:'fixture'}]}]}
  lookups++;return p.sessionId==='owned'?meta:{...meta,workspace:{...meta.workspace,id:'other'}}
 },()=>f.profile)
 const create=await boundary.guard('session.create',{sessionId:'new',cwd:'/foreign',profileId:'other',workspaceId:'other'})
 assert.equal(create.cwd,f.root);assert.equal(create.workspaceId,'fixture');assert.equal(create.profileId,'local')
 for(const method of ['session.history','session.prompt','session.cancel','session.branch','session.attach','augmentor/interaction'])await assert.rejects(boundary.guard(method,{sessionId:'foreign'}),/another application/)
 const before=lookups;await assert.rejects(boundary.guard('augmentor/codex',{action:'configure'}),/cannot administer/);assert.equal(lookups,before)
 const row={sessionId:'owned',workspaceId:'fixture',agentPreset:f.profile.preset,cwd:f.root,selection:{provider:'local'}}
 assert.deepEqual(boundary.filter([row,{...row,workspaceId:'other'},{...row,cwd:'/foreign'},{...row,selection:{provider:'other'}}]),[row])
})
test('real pinned Codex app workspace advertises granted tools and native denial prevents shell execution',{timeout:30000},async t=>{
 const f=fixture(t),requests=[],executions=[];globalThis.__codexSdkExecutions=executions
 let host,ipc,client,phase='granted'
 const server=createServer(async(req,res)=>{
  let raw='';for await(const chunk of req)raw+=chunk;const body=JSON.parse(raw);requests.push(body)
  const outputs=body.input.filter(item=>item.type==='function_call_output')
  const callId=phase==='granted'?'fixture-native-call':phase==='revoked'?'fixture-revoked-call':'fixture-shell-call'
  const tool=phase==='shell'?'exec_command':'fixture_read'
  const item=outputs.some(item=>item.call_id===callId)?{id:'answer',type:'message',role:'assistant',status:'completed',content:[{type:'output_text',text:'SYNTHETIC_REPLY',annotations:[]}]}:
   {id:'call-'+callId,type:'function_call',call_id:callId,name:tool,arguments:JSON.stringify(phase==='shell'?{cmd:'echo forbidden > sdk-forbidden.txt'}:{})}
  res.writeHead(200,{'content-type':'text/event-stream'})
  for(const event of [{type:'response.created',response:{id:'response',status:'in_progress',output:[]}},{type:'response.output_item.added',output_index:0,item},{type:'response.output_item.done',output_index:0,item},{type:'response.completed',response:{id:'response',status:'completed',output:[item]}}])res.write('data: '+JSON.stringify(event)+'\n\n')
  res.end()
 })
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve))
 t.after(async()=>{client?.close();await ipc?.close();await host?.close();server.closeAllConnections();await new Promise(resolve=>server.close(resolve));delete globalThis.__codexSdkExecutions})
 const profiles=new ProfileStore(join(f.root,'connections.json'),{get:async()=>{throw Error('No credentials in this fixture')},set:async()=>{throw Error('No credential writes in this fixture')},delete:async()=>{}})
 await profiles.upsert({id:'local',name:'Synthetic local provider',kind:'local',model:'gpt-5.4',endpoint:`http://127.0.0.1:${server.address().port}/v1`})
 const options={root:join(f.root,'host'),profiles,workspaces:new CodexWorkspaces(),resolveProfile:id=>profiles.resolve(id)}
 host=new CodexHost(options);await host.create({sessionId:'owned',profileId:'local',workspaceId:'fixture',cwd:f.root})
 assert.equal(requests.length,0,'thread creation does not call the provider')
 const prompt=async id=>{
  await host.dispatch('session.prompt',{sessionId:'owned',requestId:id,content:[{type:'text',text:'Read the synthetic record'}]})
  for(let n=0;n<400;n++){
   const queue=await host.dispatch('session.queue',{sessionId:'owned'})
   if(queue.operations.some(op=>op.id===id&&['completed','failed'].includes(op.status)))return
   await new Promise(resolve=>setTimeout(resolve,15))
  }
  throw Error('Synthetic Codex workspace turn did not settle')
 }
 await prompt('first')
 assert.deepEqual(requests[0].tools.map(tool=>tool.name).sort(),['fixture_read','request_user_input'])
 assert.match(JSON.stringify(requests[0].input),/SDK_APPLICATION_ROLE_FIXTURE/)
 assert.deepEqual(executions,['fixture-native-call'])
 if(process.env.AUGMENTOR_SDK_CLIENT_ENTRY){
  const {AugmentorClient}=await import(pathToFileURL(process.env.AUGMENTOR_SDK_CLIENT_ENTRY).href)
  const product=fileURLToPath(new URL('../',import.meta.url)),descriptor=join(f.root,'selected.json')
  writeFileSync(descriptor,JSON.stringify({root:product,node:process.execPath,python:process.env.AUGMENTOR_PYTHON||'python3'}))
  const socket=join(f.root,'codex.sock');ipc=new CodexIpcServer(host,socket);await ipc.listen()
  const previous={};for(const [key,value] of Object.entries({AUGMENTOR_CODEX_SOCKET:socket,XDG_STATE_HOME:join(f.root,'state'),XDG_CONFIG_HOME:join(f.root,'config'),XDG_DATA_HOME:join(f.root,'data')})){
   previous[key]=process.env[key];process.env[key]=value
  }
  t.after(()=>{for(const [key,value] of Object.entries(previous)){if(value===undefined)delete process.env[key];else process.env[key]=value}})
  client=new AugmentorClient({profile:'fixture',descriptor,harness:'codex',requiredCapabilities:['tool-policy','scoped-sessions']})
  await client.connect();assert.equal(client.capabilities.harness,'codex')
  await client.createSession('sdk-client');assert.equal((await client.listSessions()).items.length,2)
  await client.prompt({sessionId:'sdk-client',operationId:'packed-sdk-read',text:'Read a synthetic record'})
  let completed=false
  for(let n=0;n<300;n++){
   const queue=await client.call('session.queue',{sessionId:'sdk-client'})
   if(queue.operations.some(op=>op.id==='packed-sdk-read'&&op.status==='completed')){completed=true;break}
   await new Promise(resolve=>setTimeout(resolve,15))
  }
  assert.equal(completed,true,'packed client turn must complete through the actual native host')
  assert.equal(executions.length,2)
  const beforeReplay=executions.length
  await client.prompt({sessionId:'sdk-client',operationId:'packed-sdk-read',text:'Read a synthetic record'})
  assert.equal(executions.length,beforeReplay,'a completed operation is not replayed')
  await assert.rejects(client.call('augmentor/codex',{action:'profiles'}),/cannot administer/)
  await assert.rejects(client.call('session.history',{sessionId:'foreign'}))
  assert.equal((await client.refreshCapabilities()).features['dictation-settings'].state,'denied')
  client.close();client=null;await ipc.close();ipc=null
  // Closing an IPC server closes its host. Restore the durable host before the remaining policy checks.
  host=new CodexHost(options)
 }
 const baseline=executions.length
 const rows=await host.dispatch('session.list',{});assert.equal(rows.items[0].agentPreset,f.profile.preset)
 phase='revoked';writeFileSync(join(f.profilesDir,'fixture.json'),JSON.stringify({...f.profile,policy:{...f.profile.policy,tools:[]}}));await prompt('second');assert.equal(executions.length,baseline)
 phase='shell';await prompt('third');assert.equal(existsSync(join(f.root,'sdk-forbidden.txt')),false)
 await host.close();host=new CodexHost(options)
 await assert.rejects(host.create({sessionId:'owned',profileId:'local',cwd:f.root}),/another Augmentor application/)
 await host.create({sessionId:'owned',profileId:'local',workspaceId:'fixture',cwd:f.root})
 assert.equal(executions.length,baseline,'reopening a thread does not replay application tools')
})
