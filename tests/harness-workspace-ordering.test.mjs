// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {DshPiController} from '../apps/harness/dsh-pi-controller.mjs';

const snapshot=(revision,archived=[])=>({revision,organizationRevision:revision,items:[{workspaceId:'project',title:'Project '+revision,sessionIds:['selected']}],pinnedSessionIds:[],archivedSessionIds:archived});
function fixture(holdMutation=false){
 const reads=[],calls=[],writes=[];
 const reply=result=>({ok:true,json:async()=>({result})});
 const controller=new DshPiController('authored-workspace-fixture',async(_url,options)=>{
  const {method,params}=JSON.parse(options.body);calls.push({method,params});
  if(method==='session.list')return reply({items:[{sessionId:'selected',title:'Retained conversation'}]});
  if(method==='workspace.list')return new Promise((resolve,reject)=>reads.push({finish:value=>resolve(reply(value)),reject}));
  if(method==='session.organize')return holdMutation?new Promise(resolve=>writes.push(()=>resolve(reply({workspaces:snapshot(2)})))):reply({workspaces:snapshot(2)});
  if(method==='workspace.rename')return reply(snapshot(2));
  throw Error('Unexpected fixture RPC '+method);
 });
 controller.update({phase:'ready',sessionId:'selected',workspaces:snapshot(1)});
 return {controller,reads,calls,writes};
}

test('confirmed restore survives a delayed older workspace refresh without clearing selection',async()=>{
 const {controller,reads,calls}=fixture(),refresh=controller.refresh();
 await controller.organize('restore','selected');
 reads[0].finish(snapshot(1,['selected']));await refresh;
 assert.equal(controller.state.workspaces.organizationRevision,2);
 assert.deepEqual(controller.state.workspaces.archivedSessionIds,[]);
 assert.equal(controller.state.sessionId,'selected');
 assert.equal(calls.filter(row=>row.method==='session.organize').length,1);
 assert(!calls.some(row=>/prompt|subscribe/.test(row.method)));
});

test('confirmed workspace rename survives a delayed older workspace refresh',async()=>{
 const {controller,reads,calls}=fixture(),refresh=controller.refresh();
 await controller.workspaceAction('rename',{workspaceId:'project',title:'Project 2'});
 reads[0].finish(snapshot(1));await refresh;
 assert.equal(controller.state.workspaces.items[0].title,'Project 2');
 assert.equal(calls.filter(row=>row.method==='workspace.rename').length,1);
});

test('a newer workspace refresh wins when two reads complete in reverse order',async()=>{
 const {controller,reads}=fixture(),older=controller.refresh(),newer=controller.refresh();
 reads[1].finish(snapshot(3));await newer;reads[0].finish(snapshot(2));await older;
 assert.equal(controller.state.workspaces.revision,3);
});

test('an invalidated old read error cannot replace a confirmed catalog change',async()=>{
 const {controller,reads}=fixture(),refresh=controller.refresh();
 await controller.organize('restore','selected');reads[0].reject(Error('Old connection read failed'));
 await assert.doesNotReject(refresh);assert.equal(controller.state.workspaces.organizationRevision,2);
 assert.equal(controller.state.error,null);
});

test('a current workspace read error still surfaces without retry',async()=>{
 const {controller,reads,calls}=fixture(),refresh=controller.refresh();reads[0].reject(Error('Current read failed'));
 await assert.rejects(refresh,/Current read failed/);assert.equal(calls.filter(row=>row.method==='workspace.list').length,1);
});

test('a fresh read after confirmed mutation can observe another owner change',async()=>{
 const {controller,reads}=fixture();await controller.organize('restore','selected');
 const refresh=controller.refresh();reads[0].finish(snapshot(3,['other']));await refresh;
 assert.equal(controller.state.workspaces.organizationRevision,3);
 assert.deepEqual(controller.state.workspaces.archivedSessionIds,['other']);
});

test('an operator catalog read cannot commit after access changes to a read-only inspector',async()=>{
 const {controller,reads}=fixture(),refresh=controller.refresh();controller.update({readOnly:true});
 reads[0].finish(snapshot(9));await refresh;assert.equal(controller.state.workspaces.revision,1);
});

test('a genuine fresh archive still clears its exact selected conversation',async()=>{
 const {controller,reads}=fixture(),refresh=controller.refresh();reads[0].finish(snapshot(2,['selected']));await refresh;
 assert.equal(controller.state.sessionId,null);assert.equal(controller.state.phase,'ready');
 assert.deepEqual(controller.state.workspaces.archivedSessionIds,['selected']);
});

test('a read begun during restore cannot overwrite its later confirmed result',async()=>{
 const {controller,reads,writes}=fixture(true),restoring=controller.organize('restore','selected'),refresh=controller.refresh();
 writes[0]();await restoring;reads[0].finish(snapshot(1,['selected']));await refresh;
 assert.equal(controller.state.workspaces.organizationRevision,2);assert.equal(controller.state.sessionId,'selected');
});

test('a departing conversation refresh cannot clear or replace the new selection',async()=>{
 const {controller,reads}=fixture(),refresh=controller.refresh();controller.epoch++;controller.update({sessionId:'newer-choice'});
 reads[0].finish(snapshot(9,['newer-choice']));await refresh;
 assert.equal(controller.state.sessionId,'newer-choice');assert.equal(controller.state.workspaces.revision,1);
});

test('a failed newest refresh cannot let an older reply silently become current',async()=>{
 const {controller,reads}=fixture(),older=controller.refresh(),newer=controller.refresh();
 reads[1].reject(Error('Newest read unavailable'));await assert.rejects(newer,/Newest read unavailable/);
 reads[0].finish(snapshot(9));await older;assert.equal(controller.state.workspaces.revision,1);
});

test('unrelated streaming state does not starve a current catalog refresh',async()=>{
 const {controller,reads}=fixture(),refresh=controller.refresh();controller.update({queue:{paused:true},familyRevision:1});
 reads[0].finish(snapshot(2));await refresh;assert.equal(controller.state.workspaces.revision,2);assert.equal(controller.state.queue.paused,true);
});
