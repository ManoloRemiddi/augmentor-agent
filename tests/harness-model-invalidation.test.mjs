// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Shared operator change hints never grant edit authority or replay an operation.
import test from 'node:test';import assert from 'node:assert/strict';
import {DshModelScope} from '../apps/harness/dsh-model-scope.mjs';
import {DshPiController} from '../apps/harness/dsh-pi-controller.mjs';
const descriptor=(hint=1,revision=100)=>({writable:true,revision,modelsRevision:hint,rows:[{entry:{provider:'authored'}}],accounts:[],namespaces:[{ns:'llm-pi-ai',revision,user:{providers:{}},base:{providers:{}},value:{providers:{}},schema:{}}]});
const deferred=()=>{let resolve;const promise=new Promise(done=>resolve=done);return {promise,resolve};};
function fixture(t,rpc=async()=>descriptor()){
 const controller=new DshPiController('authored');controller.rpc=rpc;controller.update({phase:'ready',capabilities:{modelSettings:true,modelSettingsRevisions:true},modelsRevision:1});const scope=new DshModelScope(controller);t.after(()=>scope.close());return {controller,scope};
}
test('a newer operator hint retires edit authority and discovery while preserving the accepted provider view',async t=>{
 const {controller,scope}=fixture(t);await scope.load();const before=scope.snapshot,discovery=new AbortController();scope.pendingDiscoveries.add(discovery);controller.update({modelsRevision:2});assert.equal(scope.accepted,false);assert.equal(scope.snapshot.status,'ready');assert.equal(scope.snapshot.writable,false);assert.equal(scope.snapshot.rows,before.rows);assert.equal(scope.snapshot.namespaces,before.namespaces);assert.equal(discovery.signal.aborted,true);await assert.rejects(scope.call('models.settingsMutate',{},true),/Refresh/);
});
test('settled peer maintenance cannot reauthorize the same profile revision without an explicit fresh read',async t=>{
 let hint=1;const calls=[],{controller,scope}=fixture(t,async method=>{calls.push(method);return descriptor(hint,100);});await scope.load();const accepted=scope.snapshot;
 controller.update({modelsRevision:2});assert.equal(scope.accepted,false);assert.equal(scope.snapshot.rows,accepted.rows);assert.equal(scope.revision,100);
 hint=3;controller.update({modelsRevision:3});assert.equal(scope.accepted,false);assert.equal(scope.snapshot.writable,false);assert.equal((await scope.operations.writeSettings('llm-pi-ai',[],100)).kind,'refused');assert.deepEqual(calls,['models.settingsDescribe']);
 await scope.load();assert.equal(scope.accepted,true);assert.equal(scope.snapshot.writable,true);assert.equal(scope.revision,100);assert.equal(scope.acceptedHint,3);assert.deepEqual(calls,['models.settingsDescribe','models.settingsDescribe']);
});
test('older notifications cannot invalidate a newer accepted descriptor or invent a fresh write',async t=>{
 let reads=0;const {controller,scope}=fixture(t,async()=>{reads++;return descriptor(4);});await scope.load();controller.update({modelsRevision:2});controller.update({modelsRevision:4});assert.equal(scope.accepted,true);assert.equal(scope.snapshot.writable,true);assert.equal(reads,1);
});
test('a late descriptor older than an observed change cannot restore editable controls',async t=>{
 const held=deferred(),{controller,scope}=fixture(t,()=>held.promise);const reading=scope.load();controller.update({modelsRevision:3});held.resolve(descriptor(2));await reading;assert.equal(scope.accepted,false);assert.equal(scope.snapshot.writable,false);assert.equal(scope.snapshot.status,'error');
});
test('a confirmed own write adopts its settled stamp without being invalidated by an intermediate busy notification',async t=>{
 const held=deferred(),calls=[];const {controller,scope}=fixture(t,async method=>{calls.push(method);return method==='models.settingsDescribe'?descriptor():held.promise;});await scope.load();const writing=scope.operations.storeCredential('AUTHORED_API_KEY','authored-value');controller.update({modelsRevision:2});assert.equal(scope.accepted,true);held.resolve({revision:101,modelsRevision:3});assert.equal(await writing,undefined);controller.update({modelsRevision:3});assert.equal(scope.accepted,true);assert.equal(scope.revision,101);assert.equal(calls.filter(row=>row==='models.credentialSet').length,1);
});
test('a peer change newer than a mutation reply keeps the outcome unconfirmed without replay',async t=>{
 const held=deferred();let writes=0;const {controller,scope}=fixture(t,async method=>{if(method==='models.settingsDescribe')return descriptor();writes++;return held.promise;});await scope.load();const writing=scope.operations.storeCredential('AUTHORED_API_KEY','authored-value');controller.update({modelsRevision:4});held.resolve({revision:101,modelsRevision:3});assert.match(await writing,/could not be confirmed/);assert.equal(scope.accepted,false);assert.equal(scope.snapshot.writable,false);assert.equal(writes,1);
});
test('revocation clears private provider data even when a late mutation carries a newer stamp',async t=>{
 const held=deferred(),{controller,scope}=fixture(t,async method=>method==='models.settingsDescribe'?descriptor():held.promise);await scope.load();const writing=scope.operations.storeCredential('AUTHORED_API_KEY','authored-value');controller.update({readOnly:true,modelsRevision:4});held.resolve({revision:101,modelsRevision:5});await writing;assert.equal(scope.accepted,false);assert.deepEqual(scope.snapshot.rows,[]);assert.equal(scope.snapshot.namespaces.size,0);
});
test('welcome-page polling carries only modern operator model hints and ignores inspector or malformed hints',async()=>{
 for(const [readOnly,supported,hint,expected] of [[false,true,7,7],[false,false,7,undefined],[false,true,-1,undefined],[false,true,'7',undefined],[true,true,7,undefined]]){
  const c=new DshPiController('authored',async()=>({ok:true,json:async()=>({modelsRevision:hint,cursor:0,frames:[]})}));c.update({phase:'ready',sessionId:readOnly?'authored-session':null,readOnly,capabilities:{appearancePreferences:true,modelSettingsRevisions:supported}});c.lastRefresh=Date.now();await c.poll();assert.equal(c.state.modelsRevision,expected);assert.equal(c.state.phase,'ready');
 }
});
