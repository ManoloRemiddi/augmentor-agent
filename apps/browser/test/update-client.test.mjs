// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.
import test from 'node:test'
import assert from 'node:assert/strict'
import {updateRequest} from '../extension/update-client.mjs'

test('update requests use an independent native port even when the model handshake is mismatched',async()=>{
 const sent=[];let receive,disconnect,closed=false
 const runtime={getManifest:()=>({version:'0.2.13'}),connectNative:name=>{
  assert.equal(name,'com.augmentor.agent')
  return {onMessage:{addListener:fn=>receive=fn},onDisconnect:{addListener:fn=>disconnect=fn},
   disconnect:()=>{closed=true;disconnect()},postMessage:frame=>{sent.push(frame);queueMicrotask(()=>receive(frame.id==='update-handshake'?
    {id:frame.id,error:{message:'Version mismatch'}}:{id:frame.id,result:{phase:'available'}}))}}
 }}
 assert.deepEqual(await updateRequest({method:'status'},runtime),{phase:'available'})
 assert.equal(closed,true);assert.equal(sent.length,2)
 assert.deepEqual(sent[1].params,{action:'updates',method:'status'})
})

test('a disconnected or unavailable updater rejects instead of replaying the request',async()=>{
 const unavailable={connectNative:()=>{throw Error('Host missing')}}
 await assert.rejects(updateRequest({method:'download'},unavailable),/Host missing/)
 let disconnect
 const runtime={getManifest:()=>({version:'0.2.13'}),lastError:{message:'Closed'},connectNative:()=>({
  onMessage:{addListener:()=>{}},onDisconnect:{addListener:fn=>disconnect=fn},
  postMessage:()=>queueMicrotask(()=>disconnect()),disconnect:()=>{}})}
 await assert.rejects(updateRequest({method:'download'},runtime),/Closed/)
})
