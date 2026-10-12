// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {DshContextPreferences} from '../apps/harness/dsh-context-preferences.mjs';
import {contextPreferences,contextPreferenceChange,CONTEXT_PREFERENCE_OPTIONS} from '../dist/runtime/src/context-preferences.js';
import {Host} from '../dist/runtime/src/host.js';
import {mkdtemp,writeFile,rm} from 'node:fs/promises';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
const snapshot=(revision=2,patch={})=>({ns:'dsh-context',revision,value:contextPreferences(patch),writableFields:Object.keys(CONTEXT_PREFERENCE_OPTIONS)});
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function fixture(rpc,state={phase:'ready',readOnly:false}){const listeners=new Set(),calls=[];const controller={epoch:1,state,subscribe:fn=>{listeners.add(fn);return()=>listeners.delete(fn);},rpc:async(m,p)=>{calls.push([m,p]);return rpc(m,p);},update(patch){Object.assign(this.state,patch);for(const fn of listeners)fn();}};const preferences=new DshContextPreferences(controller);return {controller,preferences,calls};}
test('Host accepts only connected scalar display defaults and normalizes corrupt persisted fields safely',()=>{
 assert.equal(contextPreferences({defaultGranularity:'invalid',defaultPlacement:'all',fleetTab:'show',promptPrefix:'must not enter prompts'}).defaultGranularity,'step');assert.equal(contextPreferences({defaultPlacement:'all'}).defaultPlacement,'all');assert.equal(contextPreferences({fleetTab:'show'}).fleetTab,'show');assert.equal(contextPreferences({promptPrefix:'x'}).promptPrefix,'');
 for(const [field,choices] of Object.entries(CONTEXT_PREFERENCE_OPTIONS))for(const value of choices)assert.deepEqual(contextPreferenceChange([{op:'set',path:[field],value}]),{field,value});
 for(const field of ['promptPrefix','promptSuffix','__proto__','constructor'])assert.throws(()=>contextPreferenceChange([{op:'set',path:[field],value:'show'}]),/not supported/);
 for(const ops of [null,[],[{op:'set',path:['defaultGranularity','nested'],value:'turn'}],[{op:'set',path:['insightsEntry'],value:1}],[{op:'remove',path:['insightsEntry'],value:'hide'}],[{op:'set',path:['defaultGranularity'],value:'turn'},{op:'set',path:['insightsEntry'],value:'hide'}]])assert.throws(()=>contextPreferenceChange(ops));
});
test('confirmed original settings writes use the exact revision and never call sessions or provider methods',async t=>{
 const f=fixture(async m=>m==='settings.describe'?{namespaces:[snapshot()]}:snapshot(3,{defaultGranularity:'turn'}));t.after(()=>f.preferences.close());await tick();await f.preferences.set('defaultGranularity','turn');
 assert.equal(f.preferences.state.value.defaultGranularity,'turn');assert.equal(f.preferences.state.revision,3);assert.deepEqual(f.calls.map(([m])=>m),['settings.describe','settings.mutate']);assert.equal(f.calls[1][1].expectedRevision,2);
});
test('failed or unconfirmed preference writes restore served truth and require explicit refresh without replay',async t=>{
 let served=snapshot();const f=fixture(async m=>{if(m==='settings.describe')return {namespaces:[served]};throw Error('lost response');});t.after(()=>f.preferences.close());await tick();await assert.rejects(()=>f.preferences.set('insightsEntry','hide'),/lost response/);
 assert.equal(f.preferences.state.value.insightsEntry,'show');assert.equal(f.preferences.state.writable,false);assert.match(f.preferences.state.error,/Nothing was retried/);await assert.rejects(()=>f.preferences.set('insightsEntry','hide'),/read-only/);assert.equal(f.calls.length,2);
 served=snapshot(3,{insightsEntry:'hide'});await f.preferences.load();assert.equal(f.preferences.state.value.insightsEntry,'hide');assert.equal(f.calls.filter(([m])=>m==='settings.mutate').length,1);
});
test('read-only inspectors read no global preferences and cannot mutate even through the binding',async t=>{
 const f=fixture(async()=>{throw Error('must not read');},{phase:'ready',readOnly:true});t.after(()=>f.preferences.close());await f.preferences.load();await assert.rejects(()=>f.preferences.set('insightsEntry','hide'));assert.deepEqual(f.calls,[]);assert.equal(f.preferences.state.writable,false);
});
test('late reads and writes cannot publish after reconnect, revocation or disposal',async()=>{
 for(const writing of [false,true]){let resolve;const f=fixture(async m=>{if(writing&&m==='settings.describe')return {namespaces:[snapshot()]};return new Promise(r=>resolve=r);});await tick();const pending=writing?f.preferences.set('insightsEntry','hide'):null;await tick();f.controller.epoch++;f.controller.update({readOnly:true});resolve(writing?snapshot(3,{insightsEntry:'hide'}):{namespaces:[snapshot(3,{insightsEntry:'hide'})]});await pending;await tick();assert.equal(f.preferences.state.value.insightsEntry,'show');assert.equal(f.preferences.state.writable,false);assert.equal(f.calls.length,writing?2:1);f.preferences.close();}
});
test('unsupported controls and malformed Host replies fail closed rather than granting preference authority',async t=>{
 const f=fixture(async()=>({namespaces:[snapshot()]}));t.after(()=>f.preferences.close());await tick();await assert.rejects(()=>f.preferences.set('promptPrefix','unbound'));await assert.rejects(()=>f.preferences.set('defaultGranularity','bad'));assert.equal(f.calls.length,1);
 const bad=fixture(async()=>({namespaces:[{...snapshot(),revision:-1}]}));t.after(()=>bad.preferences.close());await tick();assert.equal(bad.preferences.state.writable,false);assert.match(bad.preferences.state.error,/unavailable/);
});
test('a failed private preference commit leaves the exact Host settings and revision unchanged',async t=>{
 const root=await mkdtemp(join(tmpdir(),'augmentor-context-commit-'));t.after(()=>rm(root,{recursive:true,force:true}));const blocked=join(root,'not-a-directory');await writeFile(blocked,'owned synthetic sentinel');const host=Object.create(Host.prototype);host.mcpManagement={busy:false};host.jobs={busy:false};host.compactions={busy:false};host.dirs={config:blocked};host.settings={revision:4,defaultModel:{provider:'fixture',model:'untouched'},contextPreferences:contextPreferences({})};const before=structuredClone(host.settings);
 await assert.rejects(()=>host.handle('settings.mutate',{ns:'dsh-context',expectedRevision:4,ops:[{op:'set',path:['defaultGranularity'],value:'turn'}]},'fixture'),error=>['ENOTDIR','EEXIST'].includes(error.code));assert.deepEqual(host.settings,before);
 await assert.rejects(()=>host.handle('settings.mutate',{ns:'dsh-context',expectedRevision:3,ops:[{op:'set',path:['insightsEntry'],value:'hide'}]},'fixture'),/Settings changed/);assert.deepEqual(host.settings,before);
});
test('a success-shaped reply without a matching revision and choice never confirms an optimistic write',async t=>{
 const f=fixture(async m=>m==='settings.describe'?{namespaces:[snapshot()]}:snapshot());t.after(()=>f.preferences.close());await tick();await assert.rejects(()=>f.preferences.set('insightsEntry','hide'),/did not confirm/);assert.equal(f.preferences.state.value.insightsEntry,'show');assert.equal(f.preferences.state.writable,false);assert.equal(f.calls.length,2);
});
