// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {DshPluginControls} from '../apps/harness/dsh-plugin-controls.mjs';
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function fixture(override={}){
 const listeners=new Set(),calls=[];let version=0;
 let wiki={revision:'missing',value:{enabled:true,vaultPath:'/authored-vault',maxQueryResults:10,typeFolders:{}},pending:false,loadedSessions:0,appliedSessions:0};
 const search={revision:'missing',enabled:false,user:{},value:{},pending:false,loadedSessions:0,appliedSessions:0};
 const memory={protocol:'augmentor-memory-settings/1',connected:true,enabled:true,configured:false,available:false,requestMode:'unconfigured',events:0,pending:0,stopped:0,actions:{capture:true,processing:true},processing:{known:true,paused:true,active:false}};
 const policy={revision:0,config:{enabled:true,textOnly:true,presets:['augmentor-linux-pi'],routes:[]}};
 const handlers={
  'search.describe':()=>structuredClone(search), 'wiki.describe':()=>structuredClone(wiki), 'memory.status':()=>structuredClone(memory),'reasoning.describe':()=>structuredClone(policy),
  'wiki.set':p=>{assert.equal(p.expectedRevision,wiki.revision);wiki={...wiki,revision:String(++version).padStart(64,'0'),value:structuredClone(p.value)};return structuredClone(wiki);},...override,
 };
 const controller={epoch:1,state:{phase:'ready',readOnly:false,sessions:[],capabilities:{searchSettings:true,wikiSettings:true,memorySettings:true}},subscribe(fn){listeners.add(fn);return()=>listeners.delete(fn);},async rpc(method,params={}){calls.push({method,params});if(!handlers[method])throw Error('Unexpected authored method '+method);return handlers[method](params);}};
 const folders={subscribe:()=>()=>{},getSnapshot:()=>({revision:0,value:{enabled:false},writable:true,busy:false,error:null}),load:async()=>{},setEnabled:async()=>{}};
 const controls=new DshPluginControls(controller,folders);return {controller,calls,controls,handlers,changed(){for(const fn of listeners)fn();},wiki:()=>wiki};
}
test('overview status reads do not enable plugins and an inspector never reads privileged settings',async t=>{
 const f=fixture();t.after(()=>f.controls.close());await tick();const rows=f.controls.getSnapshot().rows;assert.equal(rows.search.enabled,false);assert.equal(rows.wiki.enabled,true);assert.equal(rows.reasoning.enabled,true);assert.equal(rows.memory.enabled,true);assert(f.calls.every(x=>x.method.endsWith('.describe')||x.method==='memory.status'));
 f.controller.epoch++;f.controller.state.readOnly=true;f.changed();const n=f.calls.length;await f.controls.refresh();await f.controls.toggle('search');assert.equal(f.calls.length,n);assert(Object.values(f.controls.getSnapshot().rows).every(row=>!row.writable));f.controller.state.readOnly=false;f.controller.epoch++;f.changed();await tick();f.controls.close();const retired=f.calls.length;await f.controls.toggle('wiki');assert.equal(f.calls.length,retired,'retired overview cannot write through an otherwise ready controller');
});
test('Wiki overview writes only the committed enable field and reconciles rather than saving a hidden draft',async t=>{
 const f=fixture();t.after(()=>f.controls.close());await tick();f.controls.wiki.edit('maxQueryResults','17');await f.controls.toggle('wiki');assert.equal(f.wiki().value.enabled,false);assert.equal(f.wiki().value.maxQueryResults,10);assert.equal(f.controls.wiki.state.draft.maxQueryResults,'17');assert.equal(f.controls.wiki.state.draft.enabled,false);
 f.handlers['wiki.describe']=()=>{throw Error('Authored read outage');};await f.controls.refresh();assert.equal(f.controls.wiki.state.draft.maxQueryResults,'17');assert.equal(f.controls.getSnapshot().rows.wiki.writable,false);assert.match(f.controls.getSnapshot().rows.wiki.error,/outage/);
});
test('a committed but lost Wiki response is fenced until a read; no automatic mutation replay',async t=>{
 const f=fixture();t.after(()=>f.controls.close());await tick();const write=f.handlers['wiki.set'];f.handlers['wiki.set']=p=>{write(p);throw Error('Authored lost response');};f.controls.wiki.edit('maxQueryResults','23');await f.controls.toggle('wiki');assert.equal(f.wiki().value.enabled,false);assert.match(f.controls.getSnapshot().rows.wiki.error,/Nothing was retried/);const n=f.calls.filter(x=>x.method==='wiki.set').length;await f.controls.toggle('wiki');assert.equal(f.calls.filter(x=>x.method==='wiki.set').length,n);await f.controls.refresh();assert.equal(f.controls.getSnapshot().rows.wiki.enabled,false);assert.equal(f.controls.wiki.state.draft.maxQueryResults,'23');
});
test('late reasoning and malformed status cannot repopulate a retired or unconfirmed switch',async t=>{
 let release;const held=new Promise(resolve=>release=resolve),f=fixture({'reasoning.describe':()=>held});t.after(()=>f.controls.close());await tick();f.controller.epoch++;f.controller.state.readOnly=true;f.changed();release({revision:0,config:{enabled:true}});await tick();assert.equal(f.controls.getSnapshot().rows.reasoning.enabled,null);assert.equal(f.controls.getSnapshot().rows.reasoning.writable,false);
 const bad=fixture({'reasoning.describe':()=>({revision:0,config:{enabled:'true'}})});t.after(()=>bad.controls.close());await tick();assert.equal(bad.controls.getSnapshot().rows.reasoning.enabled,null);const n=bad.calls.length;await bad.controls.toggle('reasoning');assert.equal(bad.calls.length,n);
});
