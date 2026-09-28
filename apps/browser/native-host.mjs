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
import {fileURLToPath} from 'node:url'
let child,childClosed=false,closing=false,compatible=false,buffer=Buffer.alloc(0)
const pending=new Set()
const reply=value=>{if(process.stdout.destroyed||process.stdout.writableEnded)return;const b=Buffer.from(JSON.stringify(value)),h=Buffer.alloc(4);h.writeUInt32LE(b.length);process.stdout.write(Buffer.concat([h,b]))}
function finish(){
  if(closing&&!pending.size&&(!child||childClosed)&&!process.stdout.writableEnded)process.stdout.end()
}
function close(code=0){
  if(code)process.exitCode=code
  else process.exitCode??=0
  if(!closing){closing=true;process.stdin.destroy();child?.stdin.end()}
  finish()
}
function shared(id,operation){
  const task=Promise.resolve().then(operation).then(result=>reply({id,result}),error=>reply({id,error:{message:error.message}}))
  pending.add(task)
  void task.finally(()=>{pending.delete(task);finish()}).catch(()=>close(1))
}
process.stdin.on('data',chunk=>{
  if(closing)return
  if(child){child.stdin.write(chunk);return}
  buffer=Buffer.concat([buffer,chunk])
  while(buffer.length>=4){
    const n=buffer.readUInt32LE(0);if(n>1024*1024){close(1);return}if(buffer.length<n+4)return
    let first;try{first=JSON.parse(buffer.subarray(4,n+4))}catch{close(1);return}buffer=buffer.subarray(n+4)
    if(!first||typeof first!=='object'||Array.isArray(first)){close(1);return}
    if(first.method==='augmentor/handshake'){
      compatible=first.params?.protocol===PRODUCT_PROTOCOL&&first.params?.version===RELEASE.version
      reply(compatible?{id:first.id,result:{protocol:PRODUCT_PROTOCOL,version:RELEASE.version}}:{id:first.id,error:{message:'Extension and companion versions differ. Update both Augmentor components, reload the extension, then reconnect.'}});continue
    }
    if(!compatible){reply({id:first.id,error:{message:'Check Augmentor component compatibility before connecting.'}});continue}
    // Shared prompts work even while harness discovery/connection is unavailable.
    if(first.method==='augmentor/surface'){shared(first.id,()=>surfaceRequest(first.params??{}));continue}
    if(first.method==='augmentor/dsh'){shared(first.id,()=>dshSetup(first.params??{}));continue}
    if(first.method==='augmentor/diagnostics'){shared(first.id,()=>supportReport());continue}
    if(first.method==='augmentor/onboarding'){shared(first.id,()=>startOnboarding(first.params));continue}
    if(first.method==='augmentor/memory'){
      shared(first.id,()=>memoryRequest(first.params??{}));continue
    }
    if(first.method==='augmentor/prompts'){
      shared(first.id,()=>promptLibrary(first.params??{}));continue
    }
    if(first.method!=='harness.select'||!['pi','dsh'].includes(first.params?.harness)){reply({id:first.id,error:{message:'Choose DSH or Pi. Other harnesses are no longer supported; saved data is retained.'}});continue}
    child=spawn(process.execPath,[fileURLToPath(new URL(first.params.harness==='dsh'?'./pipe.mjs':'./pi-bridge.mjs',import.meta.url))],{stdio:['pipe','pipe','inherit'],windowsHide:true,env:{...process.env,AUGMENTOR_UNIFIED:'1',AUGMENTOR_BROWSER_HARNESS:first.params.harness}})
    child.stdout.pipe(process.stdout,{end:false})
    child.on('error',()=>close(1))
    child.on('close',code=>{childClosed=true;close(Number.isInteger(code)&&code>=0?code:1)})
    child.stdin.on('error',()=>close(1))
    reply({id:first.id,result:{protocol:PRODUCT_PROTOCOL,harness:first.params.harness,capabilities:HARNESS_CAPABILITIES[first.params.harness]}})
    if(buffer.length)child.stdin.write(buffer);buffer=Buffer.alloc(0);return
  }
})
process.stdin.on('end',()=>close(0));process.on('SIGTERM',()=>close(0));process.on('SIGINT',()=>close(130))
process.stdout.on('error',()=>close(1))
