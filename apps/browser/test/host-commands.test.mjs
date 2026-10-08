// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test'
import assert from 'node:assert/strict'
import {createHostCommands,HOST_CAPABILITIES} from '../extension/host-commands.mjs'

function fixture({phase='ready',running=false,accepted=true,viewing=false,editing=false,newChat=true}={}){
 const events=[],calls=[]
 class Event{constructor(type){this.type=type}}
 const input={value:'',disabled:false,focused:0,ownerDocument:{defaultView:{Event}},dispatchEvent:e=>events.push(e.type),focus(){this.focused++}}
 const ui={state:{phase,running,submitting:false}}
 const commands=createHostCommands({input,ui,wait:async()=>{ui.state.phase='ready'},
  submit:async()=>{calls.push(['submit',input.value]);if(accepted)input.value='';return accepted},
  newChat:async()=>{calls.push(['newChat']);return newChat},viewing:()=>viewing,editing:()=>editing})
 return {commands,input,ui,events,calls}
}

test('host capabilities are the documented panel protocol v2 set',()=>{
 assert.deepEqual([...HOST_CAPABILITIES].sort(),['events','focus','new-chat','prompt','status-session'])
})

test('a host prompt is sent through the owner composer',async()=>{
 const f=fixture()
 assert.deepEqual(await f.commands.prompt({text:'Triage deal d1.',send:true}),{sent:true})
 assert.deepEqual(f.calls,[['submit','Triage deal d1.']]);assert.deepEqual(f.events,['input'])
})

test('prefill places text for the owner without sending',async()=>{
 const f=fixture()
 assert.deepEqual(await f.commands.prompt({text:'Draft',send:false}),{sent:false})
 assert.equal(f.input.value,'Draft');assert.equal(f.input.focused,1);assert.deepEqual(f.calls,[])
})

test('an unsent owner draft is never replaced',async()=>{
 const f=fixture();f.input.value='My own words'
 await assert.rejects(f.commands.prompt({text:'Other',send:true}),{code:'BUSY'})
 await assert.rejects(f.commands.prompt({text:'Other',send:false}),{code:'BUSY'})
 assert.equal(f.input.value,'My own words');assert.deepEqual(f.calls,[])
})

test('busy, editing, history view and refused sends are reported, not forced',async()=>{
 await assert.rejects(fixture({running:true}).commands.prompt({text:'x',send:true}),{code:'BUSY'})
 await assert.rejects(fixture({editing:true}).commands.prompt({text:'x',send:true}),{code:'BUSY'})
 await assert.rejects(fixture({viewing:true}).commands.prompt({text:'x',send:true}),{code:'REFUSED'})
 await assert.rejects(fixture({accepted:false}).commands.prompt({text:'x',send:true}),{code:'REFUSED'})
 const fresh=fixture({viewing:true})
 assert.deepEqual(await fresh.commands.prompt({text:'x',send:true,fresh:true}),{sent:true})
 assert.deepEqual(fresh.calls,[['newChat'],['submit','x']])
})

test('a prompt waits for the connection before sending',async()=>{
 const f=fixture({phase:'connecting'})
 assert.deepEqual(await f.commands.prompt({text:'x',send:true}),{sent:true})
})

test('new chat and focus',async()=>{
 const f=fixture()
 assert.deepEqual(await f.commands.newChat(),{});f.commands.focus();assert.equal(f.input.focused,1)
 await assert.rejects(fixture({newChat:false}).commands.newChat(),{code:'REFUSED'})
})
