#!/usr/bin/env node
// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.
import {surfaceRequest} from './shared/surface.mjs'
import {PRODUCT_PROTOCOL,HARNESS_CAPABILITIES} from '../../dist/contracts/src/index.js'
import {RELEASE} from '../../dist/contracts/src/release.js'
import {promptLibrary} from './shared/prompts.mjs'
import {dshSetup,dshConfiguration} from './shared/dsh-setup.mjs'
import {supportReport} from './shared/support.mjs'
import {startOnboarding} from './shared/onboarding.mjs'
import {memoryRequest} from './shared/memory.mjs'
import {spawn} from 'node:child_process'
import {loadProfile} from '../../services/workspaces/profiles.mjs'
const workspaceProfile=loadProfile()
import {describeWorkspace} from '../../services/workspaces/capabilities.mjs'
import {guardWorkspaceMethod,voiceEnabled,SDK_PROTOCOL} from '../../services/workspaces/policy.mjs'
import {fileURLToPath} from 'node:url'
import {NativeBrowserMaintenance,connectBrowserOwner} from './shared/native-maintenance.mjs'
import {existsSync} from 'node:fs'
import {join} from 'node:path'
import {unixControl,releaseStartup} from '../../services/lifecycle/unix-control.mjs'
import {componentEnvironment} from '../../dist/platform/src/index.js'
let child,childClosed=false,closing=false,compatible=false
const pending=new Set()
const childRequests=new Set(),childActions=new Set()
const reply=value=>{if(process.stdout.destroyed||process.stdout.writableEnded)return;const b=Buffer.from(JSON.stringify(value)),h=Buffer.alloc(4);h.writeUInt32LE(b.length);process.stdout.write(Buffer.concat([h,b]))}
const maintenance=new NativeBrowserMaintenance({send:reply,busy:()=>pending.size+childRequests.size+childActions.size,onCommit:()=>close(0)})
const root=fileURLToPath(new URL('../../',import.meta.url))
const unixOwner=process.platform!=='win32'&&existsSync(join(root,'release.json'))?await (async()=>{
 const env=componentEnvironment(),runtime=env.XDG_RUNTIME_DIR??`/run/user/${process.getuid()}`
 const control=await unixControl({runtime,root,component:'browser',control:(method,params)=>maintenance.control(method,params),
  onCommitted:()=>maintenance.finishCommit()})
 releaseStartup(runtime)
 return control
})():null
const owner=process.env.AUGMENTOR_BROWSER_OWNER_ENDPOINT?connectBrowserOwner({
  endpoint:process.env.AUGMENTOR_BROWSER_OWNER_ENDPOINT,nonce:process.env.AUGMENTOR_BROWSER_OWNER_NONCE,
  pid:Number(process.env.AUGMENTOR_BROWSER_OWNER_PID),root:process.env.AUGMENTOR_BROWSER_OWNER_ROOT,maintenance,
}):null
// Harness children do not receive the private bridge-registration capability.
for(const key of ['AUGMENTOR_BROWSER_OWNER_ENDPOINT','AUGMENTOR_BROWSER_OWNER_NONCE','AUGMENTOR_BROWSER_OWNER_PID','AUGMENTOR_BROWSER_OWNER_ROOT'])delete process.env[key]
function finish(){
  if(closing&&!pending.size&&(!child||childClosed)&&!process.stdout.writableEnded){owner?.close();void unixOwner?.close();process.stdout.end()}
}
function close(code=0){
  if(code)process.exitCode=code
  else process.exitCode??=0
  if(!closing){closing=true;maintenance.close();process.stdin.destroy();child?.stdin.end()}
  finish()
}
function shared(id,operation){
  const task=Promise.resolve().then(operation).then(result=>reply({id,result}),error=>reply({id,error:{message:error.message}}))
  pending.add(task)
  void task.finally(()=>{pending.delete(task);finish()}).catch(()=>close(1))
}
function readFrames(stream,receive){
  let buffer=Buffer.alloc(0),failed=false
  stream.on('data',chunk=>{
    if(failed)return
    buffer=Buffer.concat([buffer,chunk])
    try{
      while(buffer.length>=4){
        const n=buffer.readUInt32LE(0);if(n>1024*1024)throw Error('Invalid native frame.');if(buffer.length<n+4)return
        const value=JSON.parse(buffer.subarray(4,n+4));buffer=buffer.subarray(n+4)
        if(!value||typeof value!=='object'||Array.isArray(value))throw Error('Invalid native frame.')
        receive(value)
      }
    }catch{failed=true;buffer=Buffer.alloc(0);close(1)}
  })
}
function childSend(value){const body=Buffer.from(JSON.stringify(value)),head=Buffer.alloc(4);head.writeUInt32LE(body.length);child.stdin.write(Buffer.concat([head,body]))}
readFrames(process.stdin,first=>{
    if(closing)return
    if(maintenance.receive(first))return
    if(first.method!==undefined&&maintenance.paused){reply({id:first.id,error:{message:'Augmentor maintenance is in progress. This request was not started.'}});return}
    // Update status and manual delivery remain available to repair mismatched
    // components. Configuration still requires the normal product handshake.
    if(first.method==='augmentor/surface'&&first.params?.action==='updates'){
      try{
        guardWorkspaceMethod(workspaceProfile,first.method,first.params)
        if(!compatible&&!['status','check','download','cancel','reveal'].includes(first.params.method??'status'))throw Error('Reload matching Augmentor components before changing update preferences.')
      }catch(error){reply({id:first.id,error:{code:'PERMISSION_DENIED',message:error.message}});return}
      shared(first.id,()=>surfaceRequest(first.params));return
    }
    if(child){
      if(first.id!==undefined){if(first.method!==undefined)childRequests.add(first.id);else childActions.delete(first.id)}
      childSend(first);return
    }
    if(first.method==='workspace.describe'){
      if(!workspaceProfile?.sdkProtocol||first.params?.protocol!==SDK_PROTOCOL){reply({id:first.id,error:{code:'INCOMPATIBLE_RUNTIME',message:'Register an SDK v1 workspace profile before connecting'}});return}
      reply({id:first.id,result:describeWorkspace(loadProfile())});return
    }
    if(first.method==='augmentor/handshake'){
      compatible=first.params?.protocol===PRODUCT_PROTOCOL&&first.params?.version===RELEASE.version
      reply(compatible?{id:first.id,result:{protocol:PRODUCT_PROTOCOL,version:RELEASE.version}}:{id:first.id,error:{message:'Extension and companion versions differ. Update both Augmentor components, reload the extension, then reconnect.'}});return
    }
    if(!compatible){reply({id:first.id,error:{message:'Check Augmentor component compatibility before connecting.'}});return}
    try{guardWorkspaceMethod(workspaceProfile,first.method,first.params??{})}catch(error){reply({id:first.id,error:{code:'PERMISSION_DENIED',message:error.message}});return}
    // Shared prompts work even while harness discovery/connection is unavailable.
    if(first.method==='augmentor/surface'){shared(first.id,()=>surfaceRequest(first.params??{}));return}
    if(first.method==='augmentor/dsh'){shared(first.id,()=>dshSetup(first.params??{}));return}
    if(first.method==='augmentor/diagnostics'){shared(first.id,()=>supportReport());return}
    if(workspaceProfile&&first.method==='augmentor/onboarding'){reply({id:first.id,error:{message:'This workspace is already configured. Use standalone Augmentor for personal setup.'}});return}
    if(first.method==='augmentor/onboarding'){shared(first.id,()=>startOnboarding(first.params));return}
    if(first.method==='augmentor/memory'){
      if(workspaceProfile&&first.params?.action==='dual.recall'){reply({id:first.id,error:{message:'Connect the workspace harness before recalling memory.'}});return}
      shared(first.id,()=>memoryRequest(first.params??{}));return
    }
    if(first.method==='augmentor/prompts'){
      shared(first.id,()=>promptLibrary(first.params??{}));return
    }
    if(workspaceProfile&&first.method==='harness.select'&&first.params?.harness!==(workspaceProfile.harness??'dsh')){reply({id:first.id,error:{code:'PERMISSION_DENIED',message:'This workspace uses its registered harness.'}});return}
    if(first.method!=='harness.select'||!['pi','dsh','codex'].includes(first.params?.harness)){reply({id:first.id,error:{message:'Choose DSH, Pi or Codex. Other harnesses are no longer supported; saved data is retained.'}});return}
    const bridge={dsh:'./pipe.mjs',pi:'./pi-bridge.mjs',codex:'./codex-bridge.mjs'}[first.params.harness]
    child=spawn(process.execPath,[fileURLToPath(new URL(bridge,import.meta.url))],{stdio:['pipe','pipe','inherit'],windowsHide:true,env:{...process.env,AUGMENTOR_UNIFIED:'1',AUGMENTOR_BROWSER_HARNESS:first.params.harness}})
    readFrames(child.stdout,frame=>{
      if(frame.id!==undefined){
        if(frame.method!==undefined){
          if(maintenance.paused){childSend({id:frame.id,error:{message:'Augmentor maintenance is in progress. This request was not started.'}});return}
          childActions.add(frame.id)
        }else childRequests.delete(frame.id)
      }
      reply(frame)
    })
    child.on('error',()=>close(1))
    child.on('close',code=>{childClosed=true;close(Number.isInteger(code)&&code>=0?code:1)})
    child.stdin.on('error',()=>close(1))
    reply({id:first.id,result:{protocol:PRODUCT_PROTOCOL,harness:first.params.harness,capabilities:HARNESS_CAPABILITIES[first.params.harness]}})
})
process.stdin.on('end',()=>close(0));process.on('SIGTERM',()=>close(0));process.on('SIGINT',()=>close(130))
process.stdout.on('error',()=>close(1))
