// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {DshCommandMenu} from '../apps/harness/dsh-command-menu.mjs';

// Business-boundary fixtures only. Original controller/render/key behavior is
// exercised by harness-dsh-chromium against the real public SDK/Host.
function store(value){const listeners=new Set();return {getSnapshot:()=>value,set:next=>{value=next;for(const fn of listeners)fn();},subscribe:fn=>{listeners.add(fn);return()=>listeners.delete(fn);}};}
class Trigger {
  constructor(deps){this.source=deps.roster.all()[0];for(const key of ['menu','headers','launcher','lexicon'])this[key]=store(key==='menu'?{open:false}:null);}
  track(){} dispose(){this.menu.set({open:false});} dismiss(){this.menu.set({open:false});}
  async adjudicate(line,signal,envelope){return this.source.matchEnter({},line,signal,envelope);}
  toggleSource(_,hit){this.launcher.set('command');this.menu.set({open:true,hit});}
}
class Popup {
  constructor(deps){this.deps=deps;this.state=store({open:false,options:[],search:''});}
  open(command,spec,context,segment){this.binding={command,spec,context,segment};this.state.set({open:true});}
  dispose(){this.binding=null;this.state.set({open:false,options:[],search:''});} dismiss(){this.dispose();}
}
function fixture(){
  const state={sessionId:'one',epoch:1,phase:'ready',readOnly:false,selection:{provider:'fixture',model:'first'},running:false};
  const draft={sessionId:'one',text:'/goal',rev:1,caret:5};const writes=[],actions=[],choices=[],notices=[];
  const deps={InputTriggerController:Trigger,PopupSelectController:Popup,store,sectionRows:x=>x,current:()=>state,draft:()=>draft,rows:()=>['goal','context','model'].map(name=>({name})),actions:{goal:()=>actions.push('goal'),context:()=>actions.push('context')},notice:text=>notices.push(text),focus:()=>actions.push('focus'),replace:(span,text)=>{writes.push({span,text});return true;},catalog:()=>({groups:[{provider:'fixture',name:'Fixture',models:[{model:'first',name:'First'},{model:'second',name:'Second'}]},{provider:'other',name:'Other',models:[{model:'first',name:'Same name elsewhere'}]}]}),choose:async selection=>choices.push(selection)};
  const menu=new DshCommandMenu(deps);menu.sync();return {menu,deps,state,draft,writes,actions,choices,notices};
}
const segment=(rev=1,start=0,end=5)=>({via:'menu',span:{start,end,draftRev:rev}});

test('Context defers exact draft consumption until close and refuses stale or launcher deletion',async()=>{
 const f=fixture();let close;f.deps.actions.context=(_scope,_segment,consume)=>{close=consume;};f.draft.text='/context';
 assert.equal(await f.menu.adjudicate('/context'),'handled');assert.deepEqual(f.writes,[]);assert(close());assert.equal(f.writes.length,1);
 f.writes.length=0;await f.menu.adjudicate('/context');f.draft.rev++;f.draft.text='/context edited';assert.equal(close(),false);assert.deepEqual(f.writes,[]);
 f.menu.dispatch('context',f.menu.scope,{via:'launcher',span:{start:0,end:15,draftRev:f.draft.rev}});assert(close());assert.deepEqual(f.writes,[]);
 await f.menu.adjudicate('/context edited').catch(()=>{});f.state.epoch++;assert.equal(close(),false);
});

test('command callbacks lose authority on conversation/reconnect/read-only transitions',async()=>{
  const f=fixture(),source=f.menu.engine.source;
  f.state.sessionId='two';f.state.epoch++;f.draft.sessionId='two';f.menu.sync();
  source.onPick({candidate:{name:'goal'},position:'leading',span:segment().span});
  assert.deepEqual(f.actions,[]);assert.deepEqual(f.writes,[]);
  const next=f.menu.engine.source;f.state.epoch++;f.menu.sync();next.onPick({candidate:{name:'context'},position:'leading',span:segment().span});assert.deepEqual(f.actions,[]);
  f.state.readOnly=true;f.menu.sync();assert.equal(f.menu.engine,null);assert.equal(await f.menu.adjudicate('/goal'),undefined);assert.equal(f.menu.popup.state.getSnapshot().open,false);
  f.state.readOnly=false;f.state.unconfirmed={requestId:'unknown'};f.menu.sync();assert.equal(f.menu.engine,null);assert.deepEqual(f.writes,[]);
});

test('draft revision and inline slash picks prevent unintended UI actions; launcher preserves selection',async()=>{
  const f=fixture(),source=f.menu.engine.source;
  f.draft.rev++;source.onPick({candidate:{name:'goal'},position:'leading',span:segment().span});assert.deepEqual(f.actions,[]);assert.deepEqual(f.writes,[]);
  f.draft.text='Explain /con';f.draft.caret=12;
  source.onPick({candidate:{name:'context'},position:'inline',span:segment(2,8,12).span});assert.deepEqual(f.actions,[]);assert.equal(f.writes[0].text,'/context ');
  f.writes.length=0;f.draft.text='Selected draft';f.menu.toggle({start:0,end:14});
  source.onPick({candidate:{name:'goal'},position:'leading',span:segment(2,0,14).span});assert.deepEqual(f.actions,['goal']);assert.deepEqual(f.writes,[]);
  assert.equal(f.menu.dispatch('goal',f.menu.scope,segment(2,-1,2)),false);
});

test('owned commands are adjudicated before inference; arguments and unbound DSH commands preserve the draft',async()=>{
  const f=fixture();assert.equal(await f.menu.adjudicate('/goal'),'handled');assert.deepEqual(f.actions,['goal']);assert.equal(f.writes.length,1);
  f.writes.length=0;f.actions.length=0;
  for(const command of ['permission','export','feedback'])await assert.rejects(f.menu.adjudicate('/'+command),/not yet connected to Pi/);
  await assert.rejects(f.menu.adjudicate('/goal draft arguments'),/by itself/);
  assert.equal(await f.menu.adjudicate('/unrelated-saved-template'),undefined);
  assert.deepEqual(f.actions,[]);assert.deepEqual(f.writes,[]);assert.deepEqual(f.choices,[]);
});

test('model popup captures provider identity and refuses stale draft/model/running selections',async()=>{
  const f=fixture();f.draft.text='/model';f.menu.dispatch('model',f.menu.scope,segment(1,0,6));
  const {spec,context}=f.menu.select.binding,options=await spec.options(context,new AbortController().signal);
  assert.deepEqual(options.map(x=>[x.group.name,x.active]),[['fixture',true],['fixture',false],['other',false]]);
  assert.notEqual(options[0].id,options[2].id);
  f.draft.rev++;await assert.rejects(spec.onSelect(options[1],context),/changed/);f.draft.rev--;
  f.state.selection={provider:'other',model:'first'};await assert.rejects(spec.onSelect(options[1],context),/changed/);f.state.selection=context.selection;
  f.state.running=true;await assert.rejects(spec.onSelect(options[1],context),/changed/);f.state.running=false;
  await spec.onSelect(options[1],context);assert.deepEqual(f.choices,[{provider:'fixture',model:'second'}]);
  f.state.epoch++;await assert.rejects(spec.onSelect(options[1],context),/changed/);assert.equal(f.choices.length,1);assert.deepEqual(f.writes,[]);
});

// Async command admission must not erase a rejected or subsequently edited draft.
test('Plan menu activation consumes only confirmed draft ownership; typed messages keep their admitted input path',async()=>{
 const f=fixture();f.draft.text='/plan';f.deps.rows=()=>[{name:'plan'}];let finish;
 f.deps.actions.plan=()=>new Promise(resolve=>finish=resolve);assert.equal(await f.menu.adjudicate('/plan inspect the project'),undefined);assert.equal(await f.menu.adjudicate('/plan off'),undefined);assert.deepEqual(f.writes,[]);
 assert(f.menu.dispatch('plan',f.menu.scope,segment(1,0,5)));await Promise.resolve();assert.deepEqual(f.writes,[]);f.draft.rev++;finish({accepted:true});await new Promise(resolve=>setImmediate(resolve));assert.deepEqual(f.writes,[]);
 f.draft.rev--;f.deps.actions.plan=async()=>{throw Error('Mode revision changed');};f.menu.dispatch('plan',f.menu.scope,segment(1,0,5));await new Promise(resolve=>setImmediate(resolve));assert.deepEqual(f.writes,[]);assert.deepEqual(f.notices,['Mode revision changed']);
 f.deps.actions.plan=async()=>({accepted:true});f.menu.dispatch('plan',f.menu.scope,segment(1,0,5));await new Promise(resolve=>setImmediate(resolve));assert.equal(f.writes.length,1);
});
test('Compact consumes only a confirmed, unchanged command span and refuses active work',async()=>{
 const f=fixture();f.draft.text='/compact';f.deps.rows=()=>[{name:'compact'}];let settle;
 f.deps.actions.compact=()=>new Promise(resolve=>settle=resolve);
 assert.equal(await f.menu.adjudicate('/compact'),'handled');await Promise.resolve();assert.deepEqual(f.writes,[]);
 f.draft.rev++;settle({accepted:true});await new Promise(resolve=>setImmediate(resolve));assert.deepEqual(f.writes,[]);
 f.draft.rev--;f.deps.actions.compact=async()=>{throw Error('Authoritative refusal');};
 await f.menu.adjudicate('/compact');await new Promise(resolve=>setImmediate(resolve));assert.deepEqual(f.writes,[]);assert.deepEqual(f.notices,['Authoritative refusal']);
 f.deps.actions.compact=async()=>({accepted:true});await f.menu.adjudicate('/compact');await new Promise(resolve=>setImmediate(resolve));assert.equal(f.writes.length,1);
 f.state.running=true;await assert.rejects(f.menu.adjudicate('/compact'),/Stop active/);await assert.rejects(f.menu.adjudicate('/compact arguments'),/by itself/);
});
