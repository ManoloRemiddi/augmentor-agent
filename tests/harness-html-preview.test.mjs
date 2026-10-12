// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {developerTools,developerToolsChange} from '../dist/runtime/src/developer-tools.js';
import {DshDeveloperTools} from '../apps/harness/dsh-developer-tools.mjs';
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const row=(revision=2,enabled=false)=>({ns:'ui-settings',revision,value:{enabled},writableFields:['enabled']});
function fixture(rpc,state={phase:'ready',readOnly:false,capabilities:{htmlPreviewSettings:true}}){const listeners=new Set(),calls=[],controller={state,epoch:1,subscribe:fn=>{listeners.add(fn);return()=>listeners.delete(fn);},rpc:async(m,p)=>{calls.push([m,p]);return rpc(m,p);},update(patch){Object.assign(this.state,patch);for(const fn of listeners)fn();}};return {controller,calls,scope:new DshDeveloperTools(controller)};}
test('HTML execution preserves the original enabled default and requires one exact boolean change, without permission or model fields',()=>{
 for(const raw of [null,[],{enabled:1},{enabled:'true'}])assert.deepEqual(developerTools(raw),{enabled:false});assert.deepEqual(developerTools({enabled:true}),{enabled:true});assert.deepEqual(developerTools(undefined),{enabled:true});assert.deepEqual(developerTools({}),{enabled:true});
 for(const enabled of [false,true])assert.equal(developerToolsChange([{op:'set',path:['enabled'],value:enabled}]),enabled);
 for(const ops of [[],null,[{op:'set',path:['enabled','nested'],value:true}],[{op:'set',path:['enabled'],value:'true'}],[{op:'set',path:['defaultPreset'],value:true}],[{op:'remove',path:['enabled'],value:true}],[{op:'set',path:['enabled'],value:true},{op:'set',path:['enabled'],value:false}]])assert.throws(()=>developerToolsChange(ops));
});
test('original preference scope waits for an accepted exact revision and never starts a session or inference',async t=>{
 let finish;const f=fixture(async m=>m==='settings.describe'?{namespaces:[row()]}:new Promise(resolve=>finish=resolve));t.after(()=>f.scope.close());await tick();const writing=f.scope.set('enabled',true);assert.equal(f.scope.state.value.enabled,false);finish(row(3,true));assert.equal(await writing,true);assert.equal(f.scope.state.value.enabled,true);assert.deepEqual(f.calls.map(([m])=>m),['settings.describe','settings.mutate']);assert.equal(f.calls[1][1].expectedRevision,2);
});
test('lost or success-shaped unconfirmed HTML settings disable execution and cannot replay before explicit refresh',async t=>{
 for(const response of [Error('lost reply'),row(2,true),{...row(3,true),value:{enabled:false}},row(4,true)]){
  let served=row(2,true);const f=fixture(async m=>{if(m==='settings.describe')return {namespaces:[served]};if(response instanceof Error)throw response;return response;});t.after(()=>f.scope.close());await tick();await assert.rejects(()=>f.scope.set('enabled',true));assert.equal(f.scope.state.value,undefined);assert.equal(f.scope.state.writable,false);await assert.rejects(()=>f.scope.set('enabled',true));assert.equal(f.calls.filter(([m])=>m==='settings.mutate').length,1);served=row(3,true);await f.scope.load();assert.equal(f.scope.state.value.enabled,true);
 }
});
test('read-only, late and malformed preference replies cannot grant HTML execution',async()=>{
 const inspect=fixture(async()=>{throw Error('No read allowed');},{phase:'ready',readOnly:true,capabilities:{htmlPreviewSettings:true}});await inspect.scope.load();await assert.rejects(()=>inspect.scope.set('enabled',true));assert.deepEqual(inspect.calls,[]);inspect.scope.close();
 for(const writing of [false,true]){let finish;const f=fixture(async m=>writing&&m==='settings.describe'?{namespaces:[row()]}:new Promise(resolve=>finish=resolve));await tick();const pending=writing?f.scope.set('enabled',true):null;await tick();f.controller.epoch++;f.controller.update({readOnly:true});finish(writing?row(3,true):{namespaces:[row(3,true)]});if(pending)assert.equal(await pending,false);await tick();assert.equal(f.scope.state.value,undefined);f.scope.close();}
 for(const bad of [{...row(),ns:'permission'},{...row(),revision:-1},{...row(),value:{enabled:'true'}},{...row(),writableFields:['enabled','defaultPreset']}]){const f=fixture(async()=>({namespaces:[bad]}));await tick();assert.equal(f.scope.state.writable,false);assert.equal(f.scope.state.value,undefined);f.scope.close();}
});

test('unsupported Hosts send no preference RPC and capability revocation retires an outstanding reply',async()=>{
 for(const capabilities of [undefined,{}, {htmlPreviewSettings:'true'}, {htmlPreviewSettings:false}]){
  const f=fixture(async()=>{throw Error('Unsupported RPC');},{phase:'ready',readOnly:false,capabilities});await tick();await f.scope.load();await assert.rejects(()=>f.scope.set('enabled',true));assert.deepEqual(f.calls,[]);assert.equal(f.scope.state.value,undefined);assert.equal(f.scope.state.writable,false);f.scope.close();
 }
 let finish;const f=fixture(async()=>new Promise(resolve=>finish=resolve));await tick();f.controller.update({capabilities:{}});finish({namespaces:[row(2,true)]});await tick();assert.equal(f.scope.state.value,undefined);assert.equal(f.scope.state.writable,false);assert.equal(f.calls.length,1);f.scope.close();
});
