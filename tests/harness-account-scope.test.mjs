// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';import {DshAccountScope} from '../apps/harness/dsh-account-scope.mjs';
const state=(changes={})=>({available:true,busy:false,needsRefresh:false,receipt:null,interaction:null,providers:[{provider:'authored',name:'Authored'}],accounts:[],...changes});
const running=(id='request',provider='authored')=>state({busy:true,needsRefresh:true,receipt:{requestId:id,provider,state:'running',result:'pending'},interaction:{prompt:{id:'prompt',type:'secret',message:'Authored secret'}}});
function fixture(t,rpc){
 const events=new Set(),modelEvents=new Set(),controller={epoch:1,state:{phase:'ready',readOnly:false,capabilities:{modelAccountLogin:true}},rpc,subscribe:fn=>{events.add(fn);return()=>events.delete(fn);},revoke(){this.state.readOnly=true;for(const fn of events)fn();}};
 const models={controller,revision:42,accepted:true,snapshot:{status:'ready',writable:true},current:()=>controller.state.phase==='ready'&&!controller.state.readOnly,subscribe:fn=>{modelEvents.add(fn);return()=>modelEvents.delete(fn);},suspend(){this.accepted=false;this.snapshot={status:'loading',writable:false};for(const fn of modelEvents)fn();},fail(){this.accepted=false;this.snapshot={status:'error',writable:false};for(const fn of modelEvents)fn();},loads:0,async load(){this.loads++;}};
 const scope=new DshAccountScope(models);t.after(()=>scope.close());return {scope,models,controller};
}
test('lost login admission replies read the exact saved receipt and never repeat the mutation',async t=>{
 const calls=[],f=fixture(t,async(method,p)=>{calls.push({method,p});if(method==='models.accountDescribe')return state();if(method==='models.accountStart')throw Error('Lost reply after admission');if(method==='models.accountStatus')return running(p.requestId);throw Error('Unexpected operation');});await f.scope.load();await f.scope.start('authored','owned');assert.equal(f.scope.snapshot.receipt.requestId,'owned');assert.equal(f.scope.snapshot.interaction.prompt.id,'prompt');assert.equal(f.models.accepted,false);assert.equal(calls.filter(row=>row.method==='models.accountStart').length,1);assert.equal(calls.filter(row=>row.method==='models.accountStatus').length,1);await assert.rejects(f.scope.start('authored','replayed'),/Refresh model settings/);assert.equal(calls.filter(row=>row.method==='models.accountStart').length,1);
});
test('lost prompt-answer replies refresh the step without resubmitting its secret',async t=>{
 const calls=[],f=fixture(t,async(method,p)=>{calls.push({method,p});if(method==='models.accountDescribe')return running();if(method==='models.accountRespond')throw Error('Lost answer reply');if(method==='models.accountStatus')return {...running(),interaction:{prompt:{id:'next',type:'text',message:'Next step'}}};});await f.scope.load();await assert.rejects(f.scope.respond('request','prompt','AUTHORED_SECRET'));assert.equal(f.scope.snapshot.interaction.prompt.id,'next');assert.equal(calls.filter(row=>row.method==='models.accountRespond').length,1);await assert.rejects(f.scope.respond('request','prompt','AUTHORED_SECRET'),/no longer active/);assert.equal(calls.filter(row=>row.method==='models.accountRespond').length,1);
});
test('a changed provider or another action cannot donate its prompt to a lost request',async t=>{
 const f=fixture(t,async(method)=>method==='models.accountDescribe'?state():method==='models.accountStart'?Promise.reject(Error('Lost reply')):running('owned','other-provider'));await f.scope.load();await assert.rejects(f.scope.start('authored','owned'));assert.equal(f.scope.snapshot.status,'error');assert.equal(f.scope.snapshot.interaction,null);assert.equal(f.models.accepted,false);
});
test('role revocation clears transient data and fences a delayed account descriptor',async t=>{
 let release;const f=fixture(t,()=>new Promise(resolve=>release=resolve)),loading=f.scope.load();f.controller.revoke();release(running());await loading;assert.equal(f.scope.snapshot.status,'error');assert.equal(f.scope.snapshot.interaction,null);assert.deepEqual(f.scope.snapshot.providers,[]);assert.deepEqual(f.scope.snapshot.accounts,[]);
});
test('unsafe links, invalid prompt options and inconsistent completion receipts retire account authority',async t=>{
 for(const value of [{...running(),interaction:{authorizationUrl:'javascript:AUTHORED_SECRET'}},{...running(),interaction:{authorizationUrl:'http://remote.invalid/?state=AUTHORED_SECRET'}},state({receipt:{requestId:'request',provider:'authored',state:'completed',result:'unknown'}})]){
  const f=fixture(t,async()=>value);await f.scope.load();assert.equal(f.scope.snapshot.status,'error');assert.equal(f.scope.snapshot.interaction,null);assert.equal(f.models.accepted,false);
 }
 const f=fixture(t,async()=>({...running(),interaction:{prompt:{id:'choice',type:'select',message:'Choose',options:[{id:'same',label:'A'},{id:'same',label:'B'}]}}}));await f.scope.load();assert.equal(f.scope.snapshot.status,'error');
});
test('an older completed receipt cannot represent a different globally active action',async t=>{
 const f=fixture(t,async()=>state({busy:true,needsRefresh:true,receipt:{requestId:'old',provider:'authored',state:'completed',result:'credential-stored'}}));await f.scope.load();assert.equal(f.scope.snapshot.status,'error');assert.equal(f.scope.snapshot.interaction,null);
});
test('an unconfirmed active status retains only the known action identity for explicit cancellation and keeps retries blocked',async t=>{
 const calls=[],f=fixture(t,async(method,p)=>{calls.push({method,p});if(method==='models.accountDescribe')return running();if(method==='models.accountStatus')throw Error('Authored status reply lost');if(method==='models.accountCancel')return state({needsRefresh:true,receipt:{requestId:'request',provider:'authored',state:'cancelled',result:'unknown'}});throw Error('No new login is authorized');});
 await f.scope.load();await f.scope.read('request','authored');assert.equal(f.scope.snapshot.status,'error');assert.equal(f.scope.snapshot.busy,true);assert.equal(f.scope.snapshot.receipt.requestId,'request');assert.equal(f.scope.snapshot.interaction,null);await assert.rejects(f.scope.start('authored','must-not-retry'),/Refresh model settings/);await f.scope.cancel('request');assert.equal(f.scope.snapshot.receipt.state,'cancelled');assert.equal(f.scope.snapshot.needsRefresh,true);assert.equal(f.scope.snapshot.busy,false);assert.equal(calls.filter(row=>row.method==='models.accountCancel').length,1);assert(!calls.some(row=>row.method==='models.accountStart'||row.method==='models.accountRespond'));
});
test('a newer prompt answer or cancellation retires an older in-flight status read',async t=>{
 for(const action of ['respond','cancel']){
  let release,reads=0;const f=fixture(t,async(method,p)=>{
   if(method==='models.accountDescribe')return running();
   if(method==='models.accountStatus'){if(++reads===1)return new Promise(resolve=>release=resolve);return {...running(),interaction:{prompt:{id:'next',type:'text',message:'Current next step'}}};}
   if(method==='models.accountRespond')return {accepted:true,requestId:p.requestId,promptId:p.promptId};
   if(method==='models.accountCancel')return state({needsRefresh:true,receipt:{requestId:'request',provider:'authored',state:'cancelled',result:'unknown'}});
  });await f.scope.load();const stale=f.scope.read('request','authored');await new Promise(resolve=>setImmediate(resolve));
  if(action==='respond')await f.scope.respond('request','prompt','AUTHORED_ANSWER');else await f.scope.cancel('request');
  const accepted=f.scope.snapshot;release(running());await stale;assert.deepEqual(f.scope.snapshot,accepted,action+' must not restore an older prompt/active state');
 }
});
test('unconfirmed admission is distinguishable from a previously observed active receipt without starting or replaying another login',async t=>{
 let starts=0;const f=fixture(t,async method=>{if(method==='models.accountDescribe')return state();if(method==='models.accountStart')starts++;throw Error('No account receipt was confirmed');});await f.scope.load();await assert.rejects(f.scope.start('authored','unconfirmed'));assert.equal(starts,1);assert.equal(f.scope.known('unconfirmed'),false);assert.equal(f.scope.snapshot.interaction,null);assert.equal(f.scope.snapshot.status,'error');
});
