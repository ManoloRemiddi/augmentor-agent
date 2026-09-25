// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Shared product integration, mounted on DSH's host plane by guided setup.
import {readFileSync} from 'node:fs'
import {createHash,timingSafeEqual} from 'node:crypto'
import {isIP} from 'node:net'
import {join} from 'node:path'
import {homedir} from 'node:os'
import {spawn} from 'node:child_process'
import {fileURLToPath} from 'node:url'
import {improvePrompt} from './improve-prompt.mjs'
import {exactFork} from './exact-fork.mjs'
import {InteractionBroker,interactionOperation,registerInteractions} from './interactions.mjs'
import {RELEASE} from '../../dist/contracts/src/release.js'
import {pythonExecutable,componentEnvironment} from '../../dist/platform/src/index.js'
export const name='augmentor-product'
export const inject=['webServer','workspaceRegistry','sessionPersistence','llm','sessionQuery','sessionController','agents','agentDefaultModel']
export async function apply(ctx){
 const token=readFileSync(join(process.env.DSH_HOME??join(homedir(),'.dsh'),'augmentor-product-token'),'utf8').trim()
 if(!/^[a-f0-9]{64}$/.test(token))throw Error('Run Augmentor DSH setup to create the integration token.')
 const lease=spawn(pythonExecutable(),[fileURLToPath(new URL('../../services/lifecycle/dsh-lease.py',import.meta.url))],{stdio:['pipe','pipe','ignore'],env:componentEnvironment()})
 let disposing=false,ready=false
 lease.stdin.on('error',()=>{})
 lease.on('exit',()=>{
  if(ready&&!disposing){
   console.error('[augmentor-product] Runtime maintenance protection was lost. DSH must stop; restart it after checking the installation.')
   process.kill(process.pid,'SIGTERM')
  }
 })
 await new Promise((resolve,reject)=>{
  const finish=error=>{clearTimeout(timer);lease.off('error',failed);lease.off('exit',exited);error?reject(error):resolve()}
  const failed=()=>finish(Error('Augmentor runtime lease could not start.'))
  const exited=()=>finish(Error('Finish the Augmentor package installation before starting DSH.'))
  const timer=setTimeout(()=>finish(Error('Augmentor runtime lease did not start.')),5000)
  lease.once('error',failed);lease.once('exit',exited)
  lease.stdout.once('data',value=>finish(String(value).trim()==='READY'?null:Error('Invalid runtime lease response.')))
 }).catch(error=>{disposing=true;lease.stdin.end();throw error})
 ready=true
 ctx.on('dispose',()=>{disposing=true;lease.stdin.end()})
 const interactions=new InteractionBroker()
 registerInteractions(ctx,interactions)
 ctx.on('dispose',()=>interactions.close())
 const hash=value=>createHash('sha256').update(value).digest()
 const homeId=hash(token).toString('hex')
 const allowed=new Set(['augmentor-linux-product','augmentor-browser-product'])
 ctx.effect(()=>ctx.webServer.register({kind:'exact',path:'/api/augmentor-product',handler:async(req,res)=>{
  const answer=(code,data)=>{res.writeHead(code,{'content-type':'application/json','cache-control':'no-store'});res.end(JSON.stringify(data))}
  let url
  try{url=new URL('http://'+req.headers.host)}catch{answer(403,{ok:false,error:'Host not allowed'});return}
  const host=url.hostname.replace(/^\[|\]$/g,'')
  if(!isIP(host)||!(host==='::1'||host.startsWith('127.'))||req.headers.origin&&req.headers.origin!==url.origin){answer(403,{ok:false,error:'Origin not allowed'});return}
  if(req.method==='GET'){answer(200,{protocol:'augmentor-dsh/1',version:RELEASE.version,homeId,presets:[...allowed],exactFork:1,nativeInteractions:1});return}
  if(req.method!=='POST'||!req.headers['content-type']?.startsWith('application/json')||!timingSafeEqual(hash(String(req.headers['x-augmentor-product-token']??'')),hash(token))){answer(403,{ok:false,error:'Authorized JSON request required'});return}
  try{
   let raw='';for await(const chunk of req){raw+=chunk;if(Buffer.byteLength(raw)>16384)throw Error('Request too large')}
   const p=JSON.parse(raw),surface=p.surface==='browser'?'browser':p.surface==='linux'?'linux':null
   if(p.action==='interaction'){
    const result=await interactionOperation(ctx,interactions,p);answer(200,{ok:true,...result});return
   }
   if(surface&&p.action==='exactFork'){
    const result=await exactFork(ctx,p);answer(200,{ok:true,...result});return
   }
   if(surface&&p.action==='improvePrompt'){
    const cancellation=new AbortController();res.once('close',()=>{if(!res.writableEnded)cancellation.abort()})
    try{const result=await improvePrompt(ctx.llm,p,AbortSignal.any([cancellation.signal,AbortSignal.timeout(60000)]));answer(200,{ok:true,...result})}
    catch(error){answer(400,{ok:false,error:String(error?.message??error)})}
    return
   }
   if(!surface||!['state','save','unsave'].includes(p.action))throw Error('Unsupported product operation')
   const sessions=(await ctx.sessionPersistence.list()).map(row=>row.header).filter(row=>['augmentor-linux-product','augmentor-browser-product'].includes(row.agentPreset)&&row.origin!=='subagent')
   if(p.action!=='state'){
    const row=sessions.find(row=>row.id===p.sessionId);if(!row?.cwd)throw Error('This conversation belongs to another role')
    const workspace=await ctx.workspaceRegistry.create(row.cwd)
    if(p.action==='save')await workspace.attachSession(row.id);else await workspace.detachSession(row.id)
   }
   const ids=new Set(sessions.map(row=>row.id))
   answer(200,{ok:true,saved:ctx.workspaceRegistry.list().flatMap(w=>w.sessionIds).filter(id=>ids.has(id))})
  }catch{answer(400,{ok:false,error:'DSH could not complete this Augmentor chat operation.'})}
 }}))
}
