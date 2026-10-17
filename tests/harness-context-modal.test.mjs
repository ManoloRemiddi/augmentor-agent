// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {DshContextModalBinding} from '../apps/harness/dsh-context-modal-binding.mjs';
function fixture(){
 const current={sessionId:'one',epoch:1,phase:'ready'},flags=new Map(),guards=new Map();let consumed=0;
 const binding=new DshContextModalBinding({current:()=>current,storeOf:id=>({set:value=>flags.set(id,value)}),setPending:(id,guard)=>guards.set(id,guard),takePending:id=>{const value=guards.get(id);guards.delete(id);return value;}});
 const open=()=>binding.open({sessionId:'one',epoch:1},{via:'enter',token:'/context'},()=>++consumed);
 return {binding,current,flags,guards,open,count:()=>consumed};
}
test('original modal close owns one exact local token guard and dispatches no Host action',()=>{
 const f=fixture();assert(f.open());assert.equal(f.count(),0);const scope=f.binding.scope('one'),guard=f.guards.get('one');
 assert.equal(scope.bail(scope,'other-event',{guard}),false);assert.equal(scope.bail({},'slash/input-consume-token',{guard}),false);assert.equal(scope.bail(scope,'slash/input-consume-token',{guard:{...guard}}),false);
 assert.equal(scope.bail(scope,'slash/input-consume-token',{guard}),1);assert.equal(scope.bail(scope,'slash/input-consume-token',{guard}),false);assert.equal(f.count(),1);
});
test('session, reconnect, interaction and authority changes discard modal consumption',()=>{
 for(const change of [{sessionId:'other'},{epoch:2},{phase:'disconnected'},{readOnly:true},{unconfirmed:{}},{interactions:[{}]}]){
  const f=fixture();f.open();const old=f.binding.scope('one'),guard=f.guards.get('one');Object.assign(f.current,change);f.binding.sync();
  assert.equal(f.flags.get('one'),false);assert.equal(f.guards.size,0);assert.equal(old.bail(old,'slash/input-consume-token',{guard}),false);assert.equal(f.count(),0);assert.equal(f.binding.scope('one'),undefined);
 }
});
test('replacement and invalidation revoke an earlier dialog close callback',()=>{
 const f=fixture();f.open();const old=f.binding.scope('one'),guard=f.guards.get('one');f.open();assert.equal(old.bail(old,'slash/input-consume-token',{guard}),false);
 f.binding.invalidate();assert.equal(f.flags.get('one'),false);assert.equal(f.guards.size,0);assert.equal(f.count(),0);assert.equal(f.binding.open({sessionId:'',epoch:1},{via:'enter',token:'/context'},()=>{}),false);
});
