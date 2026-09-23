// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {storedHarness} from '../apps/browser/extension/state.mjs';
test('existing DSH profiles retain their harness and fresh profiles start with Pi',()=>{
 assert.equal(storedHarness({}),'pi');
 assert.equal(storedHarness({'augmentor-session-id':'original-dsh-chat'}),'dsh');
 assert.equal(storedHarness({'augmentor-model-selection':{provider:'saved',model:'saved'}}),'dsh');
 assert.equal(storedHarness({'augmentor-harness':'pi','augmentor-session-id':'original-dsh-chat'}),'pi');
 assert.equal(storedHarness({'augmentor-harness':'dsh'}),'dsh');
});
test('retired engine selection does not reopen its conversation through another engine',()=>{
 const saved={'augmentor-harness':'opencode','augmentor-session-id':'legacy-dsh','augmentor-session-id-opencode':'retained'};
 assert.equal(storedHarness(saved),null);
 assert.equal(saved['augmentor-session-id-opencode'],'retained');
 assert.equal(storedHarness({...saved,'augmentor-harness':'pi'}),'pi');
});
