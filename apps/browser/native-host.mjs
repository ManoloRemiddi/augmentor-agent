#!/usr/bin/env node
import {surfaceRequest} from './shared/surface.mjs'
// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.
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
import {fileURLToPath} from 'node:url'
let child,compatible=false,buffer=Buffer.alloc(0)
const reply=value=>{const b=Buffer.from(JSON.stringify(value)),h=Buffer.alloc(4);h.writeUInt32LE(b.length);process.stdout.write(Buffer.concat([h,b]))}
process.stdin.on('data',chunk=>{
  if(child){child.stdin.write(chunk);return}
  buffer=Buffer.concat([buffer,chunk])
  while(buffer.length>=4){
    const n=buffer.readUInt32LE(0);if(n>1024*1024)process.exit(1);if(buffer.length<n+4)return
    let first;try{first=JSON.parse(buffer.subarray(4,n+4))}catch{process.exit(1)}buffer=buffer.subarray(n+4)
    if(first.method==='augmentor/handshake'){
      compatible=first.params?.protocol===PRODUCT_PROTOCOL&&first.params?.version===RELEASE.version
      reply(compatible?{id:first.id,result:{protocol:PRODUCT_PROTOCOL,version:RELEASE.version}}:{id:first.id,error:{message:'Extension and companion versions differ. Update both Augmentor components, reload the extension, then reconnect.'}});continue
    }
    if(!compatible){reply({id:first.id,error:{message:'Check Augmentor component compatibility before connecting.'}});continue}
    // Shared prompts work even while harness discovery/connection is unavailable.
    if(first.method==='augmentor/surface'){surfaceRequest(first.params??{}).then(result=>reply({id:first.id,result}),error=>reply({id:first.id,error:{message:error.message}}));continue}
    if(first.method==='augmentor/dsh'){dshSetup(first.params??{}).then(result=>reply({id:first.id,result}),error=>reply({id:first.id,error:{message:error.message}}));continue}
    if(first.method==='augmentor/diagnostics'){supportReport().then(result=>reply({id:first.id,result}),error=>reply({id:first.id,error:{message:error.message}}));continue}
    if(first.method==='augmentor/onboarding'){startOnboarding(first.params).then(result=>reply({id:first.id,result}),error=>reply({id:first.id,error:{message:error.message}}));continue}
    if(first.method==='augmentor/memory'){
      if(workspaceProfile&&first.params?.action==='dual.recall'){reply({id:first.id,error:{message:'Connect the workspace harness before recalling memory.'}});continue}
      memoryRequest(first.params??{}).then(result=>reply({id:first.id,result}),error=>reply({id:first.id,error:{message:error.message}}));continue
    }
    if(first.method==='augmentor/prompts'){
      promptLibrary(first.params??{}).then(result=>reply({id:first.id,result}),error=>reply({id:first.id,error:{message:error.message}}));continue
    }
    if(workspaceProfile&&first.method==='harness.select'&&first.params?.harness!=='dsh'){reply({id:first.id,error:{message:'This workspace uses its configured DSH specialist.'}});continue}
    if(first.method!=='harness.select'||!['pi','dsh'].includes(first.params?.harness)){reply({id:first.id,error:{message:'Choose DSH or Pi. Other harnesses are no longer supported; saved data is retained.'}});continue}
    child=spawn(process.execPath,[fileURLToPath(new URL(first.params.harness==='dsh'?'./pipe.mjs':'./pi-bridge.mjs',import.meta.url))],{stdio:['pipe','pipe','inherit'],env:{...process.env,AUGMENTOR_UNIFIED:'1',AUGMENTOR_BROWSER_HARNESS:first.params.harness}})
    child.stdout.pipe(process.stdout);child.on('error',()=>process.exit(1));child.on('exit',()=>process.exit(0));child.stdin.on('error',()=>process.exit(1))
    reply({id:first.id,result:{protocol:PRODUCT_PROTOCOL,harness:first.params.harness,capabilities:HARNESS_CAPABILITIES[first.params.harness]}})
    if(buffer.length)child.stdin.write(buffer);buffer=Buffer.alloc(0);return
  }
})
process.stdin.on('end',()=>{child?.kill();process.exit(0)});process.on('SIGTERM',()=>{child?.kill();process.exit(0)})
