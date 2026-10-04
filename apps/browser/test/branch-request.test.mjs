// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {prepareBranch,finishBranch} from '../extension/branch-request.mjs';
const intent={sessionId:'source',newSessionId:'first-child',messageSeq:12,mode:'reply'};
function fixture(){const saved={};return {saved,storage:{get:async key=>({[key]:structuredClone(saved[key])}),set:async record=>Object.assign(saved,structuredClone(record))}};}

test('lost replies and a fresh caller reuse the persisted child identity',async()=>{
 const {storage}=fixture();await prepareBranch(storage,intent);
 assert.deepEqual(await prepareBranch(storage,{...intent,newSessionId:'another-child'}),intent);
 await assert.rejects(prepareBranch(storage,{...intent,mode:'edit'}),/previous branch/);
 await finishBranch(storage,intent,{'selected-child':'first-child'});
 assert.equal((await storage.get('selected-child'))['selected-child'],'first-child');
 assert.equal((await prepareBranch(storage,{...intent,newSessionId:'deliberate-second-child'})).newSessionId,'deliberate-second-child');
});
test('failed persistence cannot admit a new identity or clear uncertain intent',async()=>{
 const {storage}=fixture();await prepareBranch(storage,intent);
 storage.set=async()=>{throw Error('Storage unavailable')};
 await assert.rejects(finishBranch(storage,intent),/Storage unavailable/);
 assert.equal((await prepareBranch(storage,{...intent,newSessionId:'replacement'})).newSessionId,'first-child');
 await assert.rejects(prepareBranch(storage,{get:undefined}),/committed message/);
 await assert.rejects(finishBranch(storage,{...intent,newSessionId:'wrong'}),/identity changed/);
});
