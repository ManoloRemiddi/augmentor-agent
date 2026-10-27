// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test'
import assert from 'node:assert/strict'
import {mkdtempSync,mkdirSync,writeFileSync,readFileSync,rmSync} from 'node:fs'
import {tmpdir} from 'node:os'
import {join} from 'node:path'
import {spawn} from 'node:child_process'
import {fileURLToPath} from 'node:url'
import {guardWorkspaceMethod} from '../services/workspaces/policy.mjs'
import {RELEASE} from '../dist/contracts/src/release.js'

const profile={schemaVersion:1,sdkProtocol:'augmentor-app/1',id:'fixture',preset:'augmentor-fixture',cwd:'/tmp/fixture',memory:{person:'fixture-owner',project:'/tmp/fixture'},parentOrigin:'http://127.0.0.1:9999',publicPath:'/augmentor/',policy:{tools:[],voice:false,sharedSettings:false}}

test('SDK profiles allow draft improvement without granting settings, tools or other surface operations',()=>{
 const before=structuredClone(profile)
 assert.doesNotThrow(()=>guardWorkspaceMethod(profile,'augmentor/surface',{action:'improve',text:'Clarify this draft.',selection:{provider:'fixture',model:'fixture'}}))
 for(const params of [{},{action:'appearance'},{action:'appearance',settings:{theme:'light'}},{action:'dictation',method:'enable'},{action:'improvePrompt'},{action:['improve']},{action:null}])assert.throws(()=>guardWorkspaceMethod(profile,'augmentor/surface',params),/cannot administer/)
 for(const method of ['settings.mutate','updates/check','augmentor/dsh','augmentor/codex','augmentor/home','augmentor/diagnostics','augmentor/onboarding'])assert.throws(()=>guardWorkspaceMethod(profile,method,{action:'improve'}),/cannot administer/)
 assert.throws(()=>guardWorkspaceMethod({...profile,policy:{...profile.policy,sharedSettings:true}},'augmentor/surface',{action:'improve'}),/explicit tool/)
 assert.deepEqual(profile,before)
})

test('the SDK native host routes improvement before harness selection while rejecting settings',async t=>{
 const dir=mkdtempSync(join(tmpdir(),'workspace-improve-'));t.after(()=>rmSync(dir,{recursive:true,force:true}))
 const profiles=join(dir,'profiles');mkdirSync(profiles)
 writeFileSync(join(profiles,'fixture.json'),JSON.stringify({...profile,cwd:dir,memory:{person:'fixture-owner',project:dir}}))
 const helper=join(dir,'helper.mjs'),calls=join(dir,'calls.json')
 // An independently authored helper records the surface request and returns an editable draft.
 writeFileSync(helper,`#!${process.execPath}\nimport {writeFileSync} from 'node:fs';let text='';for await(const c of process.stdin)text+=c;const p=JSON.parse(text);writeFileSync(process.env.FIXTURE_CALLS,JSON.stringify(p));process.stdout.write(JSON.stringify({kind:'rewrite',text:'Please clarify this draft.'}));`,{mode:0o700})
 const child=spawn(process.execPath,[fileURLToPath(new URL('../apps/browser/native-host.mjs',import.meta.url))],{env:{...process.env,HOME:dir,XDG_CONFIG_HOME:dir,XDG_STATE_HOME:dir,AUGMENTOR_WORKSPACE_PROFILES:profiles,AUGMENTOR_WORKSPACE_PROFILE:'fixture',AUGMENTOR_PYTHON:helper,FIXTURE_CALLS:calls},stdio:['pipe','pipe','pipe']})
 const exited=new Promise(resolve=>child.once('close',resolve))
 let buffer=Buffer.alloc(0),next=0;const pending=new Map()
 child.stdout.on('data',chunk=>{buffer=Buffer.concat([buffer,chunk]);while(buffer.length>=4){const size=buffer.readUInt32LE(0);if(buffer.length<size+4)break;const frame=JSON.parse(buffer.subarray(4,size+4));buffer=buffer.subarray(size+4);const waiter=pending.get(frame.id);if(waiter){pending.delete(frame.id);clearTimeout(waiter.timer);waiter.resolve(frame)}}})
 const rpc=(method,params={})=>new Promise((resolve,reject)=>{const id=++next,timer=setTimeout(()=>{pending.delete(id);reject(Error('Native response timed out'))},5000);pending.set(id,{resolve,timer});const body=Buffer.from(JSON.stringify({id,method,params})),header=Buffer.alloc(4);header.writeUInt32LE(body.length);child.stdin.write(Buffer.concat([header,body]))})
 try{
  assert.ok((await rpc('augmentor/handshake',{protocol:'augmentor/1',version:RELEASE.version})).result)
  const original='clarify this draft',selection={provider:'fixture',model:'fixture-model'}
  const response=await rpc('augmentor/surface',{action:'improve',text:original,selection})
  assert.deepEqual(response.result,{kind:'rewrite',text:'Please clarify this draft.'})
  assert.deepEqual(JSON.parse(readFileSync(calls,'utf8')),{action:'improve',text:original,selection})
  const denied=await rpc('augmentor/surface',{action:'appearance',settings:{theme:'light'}})
  assert.equal(denied.error.code,'PERMISSION_DENIED')
  assert.deepEqual(JSON.parse(readFileSync(calls,'utf8')),{action:'improve',text:original,selection},'a denied operation never reaches the helper')
 }finally{
  for(const waiter of pending.values())clearTimeout(waiter.timer)
  child.stdin.end();await exited
 }
})
