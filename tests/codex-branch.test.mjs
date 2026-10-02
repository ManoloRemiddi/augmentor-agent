// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {branchBoundary, historyHash, verifyBranchHistory} from '../dist/codex-runtime/src/branch.js';
import {DisplayJournal} from '../dist/codex-runtime/src/journal.js';

function history() {return [
  {id:'first',status:'completed',items:[{id:'u1',type:'userMessage',content:[{type:'text',text:'first'}]},
    {id:'tool',type:'dynamicToolCall',success:true,contentItems:[{type:'inputText',text:'receipt'}]},
    {id:'a1',type:'agentMessage',phase:'final_answer',text:'answer'}]},
  {id:'second',status:'completed',items:[{id:'u2',type:'userMessage',content:[{type:'text',text:'later'}]},
    {id:'a2',type:'agentMessage',text:'later answer'}]},
];}
function event(turnId,itemId,mode='reply') {return {seq:7,type:mode==='reply'?'assistant/message':'user/message',turnId,data:{itemId}};}

test('exact reply and edit select inclusive, exclusive and empty native prefixes',()=>{
  const turns=history();
  const reply=branchBoundary(turns,event('first','a1'),'reply');
  assert.deepEqual(reply.params,{lastTurnId:'first'});
  verifyBranchHistory(reply,turns.slice(0,1));
  const edit=branchBoundary(turns,event('second','u2','edit'),'edit');
  assert.deepEqual(edit.params,{beforeTurnId:'second'});
  assert.equal(edit.historyHash,reply.historyHash);
  const empty=branchBoundary(turns,event('first','u1','edit'),'edit');
  verifyBranchHistory(empty,[]);
  assert.deepEqual(empty.params,{beforeTurnId:'first'});
});

test('fork validation detects copied later inputs, missing tools and changed tool receipts',()=>{
  const turns=history(), boundary=branchBoundary(turns,event('first','a1'),'reply');
  assert.throws(()=>verifyBranchHistory(boundary,turns),/differs/);
  for (const mutate of [
    turn=>turn.items.splice(1,1),
    turn=>turn.items[1].contentItems[0].text='changed receipt',
    turn=>turn.status='interrupted',
    turn=>turn.items.reverse(),
    turn=>turn.items[0].content[0].text='changed input',
  ]) {
    const copy=structuredClone(turns.slice(0,1));mutate(copy[0]);
    assert.throws(()=>verifyBranchHistory(boundary,copy),/differs/);
  }
  const copy=structuredClone(turns.slice(0,1));copy[0].durationMs=999;
  copy[0].items=copy[0].items.map(item=>Object.fromEntries(Object.entries(item).reverse()));
  verifyBranchHistory(boundary,copy);
  assert.notEqual(historyHash([]),boundary.historyHash);
});

test('mid-turn selections cannot silently include later actions or drop steered inputs',()=>{
  let turns=history();
  turns[0].items.push({id:'late-tool',type:'dynamicToolCall'});
  assert.throws(()=>branchBoundary(turns,event('first','a1'),'reply'),/final answer/);
  turns=history();turns[0].items[2].phase='commentary';
  assert.throws(()=>branchBoundary(turns,event('first','a1'),'reply'),/final answer/);
  turns=history();turns[0].items.splice(2,0,{id:'steer',type:'userMessage'});
  assert.throws(()=>branchBoundary(turns,event('first','steer','edit'),'edit'),/mid-turn/);
  turns=history();turns[1].status='inProgress';
  assert.throws(()=>branchBoundary(turns,event('first','a1'),'reply'),/stop before branching/);
});

test('branch selection requires an existing committed message of the correct kind',()=>{
  const turns=history();
  for(const selected of [undefined,event('missing','a1'),event('first','missing'),event('first','tool'),
    {...event('first','a1'),seq:0},{...event('first','a1'),type:'assistant/chunk'}])
    assert.throws(()=>branchBoundary(turns,selected,'reply'));
  assert.throws(()=>branchBoundary(turns,event('first','u1','edit'),'reply'));
  assert.throws(()=>branchBoundary(turns,event('first','a1'),'rollback'),/Invalid/);
});

test('exact journal lookup survives restart and cannot mutate saved event identity',t=>{
  const root=mkdtempSync(join(tmpdir(),'codex-boundary-'));t.after(()=>rmSync(root,{recursive:true,force:true}));
  const path=join(root,'display.jsonl'), journal=new DisplayJournal(path);
  journal.append({type:'turn/start',turnId:'first',data:{}});
  const saved=journal.append(event('first','a1'));
  assert.equal(saved.seq,2);
  assert.equal(journal.event(2).data.itemId,'a1');
  journal.event(2).data.itemId='corrupted';
  assert.equal(new DisplayJournal(path).event(2).data.itemId,'a1');
  assert.equal(journal.event(3),undefined);
  for(const value of [0,-1,1.5,'2',NaN,Infinity,Number.MAX_SAFE_INTEGER+1]) assert.throws(()=>journal.event(value),/sequence/);
});
