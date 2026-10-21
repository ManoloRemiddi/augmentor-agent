// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,rmSync,readFileSync,writeFileSync,chmodSync,symlinkSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {PiPromptQueue} from '../dist/runtime/src/queue.js';
function fixture(t){const root=mkdtempSync(join(tmpdir(),'augmentor-queue-'));t.after(()=>rmSync(root,{recursive:true,force:true}));const path=join(root,'queue.json');return {root,path,queue:new PiPromptQueue(path,'fixture')};}
test('Pi queue keeps stable receipts after completion, removal and more than 100 later prompts',t=>{
 const {queue,path}=fixture(t);queue.enqueue('first','Same text',false);queue.dispatch('first','turn-one');queue.accepted('first');queue.delivered('first');queue.finish('first','completed');
 for(let n=0;n<110;n++){queue.enqueue('item-'+n,'Same text',true);queue.remove('item-'+n);}
 const reopened=new PiPromptQueue(path,'fixture');assert.equal(reopened.enqueue('first','Same text',false),false);assert.equal(reopened.enqueue('item-0','Same text',true),false);
 assert.throws(()=>reopened.enqueue('first','Different text',false),/identity was reused/);assert.equal(reopened.snapshot().items.length,0);
 assert(!JSON.stringify(JSON.parse(readFileSync(path))).includes('Same text'));
});
test('Pi queue uses FIFO and preserves paused waiting prompts across restart without dispatching them',t=>{
 const {queue,path}=fixture(t);queue.enqueue('one','First',true);queue.enqueue('two','Second',true);queue.pause();const revision=queue.snapshot().revision;
 const reopened=new PiPromptQueue(path,'fixture');reopened.recover();assert(reopened.paused);assert(reopened.snapshot().revision>revision);assert.equal(reopened.next.id,'one');
 assert.throws(()=>reopened.dispatch('one','turn'),/cannot be dispatched/);reopened.remove('one');reopened.resume();assert.equal(reopened.next.id,'two');
});
test('Pi queue never replays a prompt whose process died during dispatch or execution',t=>{
 for(const state of ['dispatching','active']){
  const {queue,path}=fixture(t);queue.enqueue('one','Potential action',false);queue.dispatch('one','turn');if(state==='active')queue.accepted('one');queue.enqueue('two','Waiting action',true);
  const reopened=new PiPromptQueue(path,'fixture');reopened.recover();const item=reopened.snapshot().items[0];assert.equal(item.canResolve,true);assert.equal(item.canRemove,false);assert.equal(item.canSteer,false);
  assert.throws(()=>reopened.resume(),/unknown outcome/);assert.throws(()=>reopened.remove('one'),/cannot be removed/);assert.equal(reopened.enqueue('one','Potential action',true),false);
  reopened.resolve('one');assert(reopened.paused);reopened.resume();assert.equal(reopened.next.id,'two');
 }
});
test('Pi queue rejects a concurrent SDK owner and retains only waiting prompts on Stop',t=>{
 const {queue}=fixture(t);queue.enqueue('one','Original',false);queue.dispatch('one','turn');queue.accepted('one');queue.enqueue('two','Next',true);
 assert.throws(()=>queue.dispatch('two','other-turn'),/cannot be dispatched/);queue.pause();queue.finish('one','cancelled');assert.equal(queue.snapshot().items[0].stateLabel,'Paused');
 queue.resume();queue.dispatch('two','other-turn');assert.equal(queue.snapshot().activeTurnId,'other-turn');
});
test('Pi queue bounds waiting rows and UTF-8 storage, including unsent failures',t=>{
 const first=fixture(t).queue;for(let n=0;n<100;n++)first.enqueue('id-'+n,'Waiting',true);assert.throws(()=>first.enqueue('excess','Waiting',true),/full/);first.remove('id-0');first.enqueue('replacement','Replacement',true);
 const second=fixture(t).queue;for(let n=0;n<2;n++)second.enqueue('big-'+n,'界'.repeat(65536),true);assert.throws(()=>second.enqueue('excess','界'.repeat(65536),true),/full/);second.notSent('big-0');assert.throws(()=>second.enqueue('excess','界'.repeat(65536),true),/full/);second.remove('big-0');second.enqueue('replacement','Small',true);
});
test('Pi queue rejects changed identity, malformed receipts and mismatched session state',t=>{
 const {queue,path}=fixture(t);queue.enqueue('one','Original',true);assert.throws(()=>new PiPromptQueue(path,'another'),/mismatched|Unsupported/);
 const data=JSON.parse(readFileSync(path));data.items[0].input='Tampered';writeFileSync(path,JSON.stringify(data));assert.throws(()=>new PiPromptQueue(path,'fixture'),/Corrupt/);
 assert.throws(()=>queue.enqueue('bad identity','text',false),/Invalid prompt identity/);
});
test('Pi queue rejects symlink or public state files on POSIX',{skip:process.platform==='win32'},t=>{
 const {queue,path,root}=fixture(t);queue.enqueue('one','Private',true);chmodSync(path,0o644);assert.throws(()=>new PiPromptQueue(path,'fixture'),/private/);chmodSync(path,0o600);
 const link=join(root,'linked.json');symlinkSync(path,link);assert.throws(()=>new PiPromptQueue(link,'fixture'),/private/);
});
test('Pi steering receipts share the original turn and finish atomically with it',t=>{
 const {queue,path}=fixture(t);queue.enqueue('root','Original',false);queue.dispatch('root','turn');queue.accepted('root');queue.delivered('root');
 queue.enqueue('correction','Correction',true);queue.enqueue('followup','Follow-up',true);
 assert(queue.snapshot(true).items.every(item=>item.canSteer));assert.throws(()=>queue.promote('correction','stale'),/observed active turn/);
 queue.promote('correction','turn');assert.equal(queue.snapshot(true).items[0].placement,'steering');assert(queue.snapshot(true).items.every(item=>!item.canSteer));
 queue.delivered('correction');queue.finish('root','completed');const reopened=new PiPromptQueue(path,'fixture');assert.equal(reopened.read('correction').status,'completed');
 assert.equal(reopened.enqueue('correction','Correction',true),false);assert.deepEqual(reopened.snapshot().items.map(item=>item.id),['followup']);
});
test('Stop returns known withdrawn steering to paused FIFO while unknown delivery remains unconfirmed',t=>{
 for(const withdrawn of [true,false]){
  const {queue,path}=fixture(t);queue.enqueue('root','Original',false);queue.dispatch('root','turn');queue.accepted('root');queue.enqueue('correction','Correction',true);queue.promote('correction','turn');queue.pause();
  if(withdrawn)queue.withdrawSteer('correction');queue.finish('root','cancelled');const reopened=new PiPromptQueue(path,'fixture');
  assert.equal(reopened.read('correction').status,withdrawn?'waiting':'unconfirmed');assert.equal(reopened.uncertain,!withdrawn);assert(reopened.paused);
 }
});
test('a crash leaves both the active and promoted steering receipts unknown without replay',t=>{
 const {queue,path}=fixture(t);queue.enqueue('root','Original',false);queue.dispatch('root','turn');queue.accepted('root');queue.enqueue('correction','Correction',true);queue.promote('correction','turn');
 const reopened=new PiPromptQueue(path,'fixture');reopened.recover();assert(reopened.paused);assert(reopened.snapshot().items.every(item=>item.canResolve&&!item.canSteer));assert.throws(()=>reopened.resume(),/unknown outcome/);
});
test('a handled correction retains a terminal identity without claiming model delivery or replay',t=>{
 const {queue,path}=fixture(t);queue.enqueue('root','Original',false);queue.dispatch('root','turn');queue.accepted('root');queue.enqueue('handled','Handled input',true);queue.promote('handled','turn');queue.handledSteer('handled');queue.finish('root','completed');
 const reopened=new PiPromptQueue(path,'fixture');assert.equal(reopened.read('handled').status,'completed');assert.equal(reopened.read('handled').delivered,false);assert.equal(reopened.enqueue('handled','Handled input',true),false);assert.equal(reopened.snapshot().items.length,0);
});
test('interrupted initial preparation stays unknown even after late native delivery and survives reopen',t=>{
 const {queue,path}=fixture(t);queue.enqueue('input','Potential extension effect',false);queue.dispatch('input','turn');queue.accepted('input');queue.pause();queue.delivered('input');queue.finish('input','unconfirmed');queue.enqueue('waiting','Next',true);
 const reopened=new PiPromptQueue(path,'fixture');assert(reopened.snapshot().items.find(item=>item.id==='input').canResolve);assert.equal(reopened.read('input').input,'Potential extension effect');assert.throws(()=>reopened.resume(),/unknown outcome/);assert.equal(reopened.enqueue('input','Potential extension effect',false),false);reopened.resolve('input');reopened.resume();assert.equal(reopened.next.id,'waiting');assert.equal(reopened.read('input').input,undefined);
});
