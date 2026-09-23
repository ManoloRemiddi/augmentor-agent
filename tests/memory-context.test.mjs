// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {memoryContext,CONTEXT_LIMIT} from '../dist/memory/src/context.js';

test('unrelated assistant offers and old project excerpts do not become active context',()=>{
  const result=memoryContext({enabled:true,relationship:{pages:[{name:'Shared moments and commitments',content:'I offered a large game download.'}]},
    work:{summary:'An unrelated project is using SQLite.'},recent:[{role:'assistant',content:'Start that download.'}]},'text','How do I change font size?');
  assert.equal(result,'');
});
test('direct user boundary survives assistant chatter and a vague continuation',()=>{
  const receipts=[{seq:1,session:'one',role:'user',mode:'text',content:'Repair the launcher. I will download the game myself.'},
    {seq:201,session:'one',role:'user',mode:'text',content:'Fix it yourself.'}];
  const result=memoryContext({enabled:true,userReceipts:receipts,recent:Array.from({length:100},()=>({role:'assistant',content:'I will install it.'}))},'text','Fix it yourself.');
  assert.match(result,/I will download the game myself/);
  assert.doesNotMatch(result,/I will install it/);
  assert.match(result,/Continue previously authorized work within its scope/);
});
test('current reversal stays verbatim beside old restriction; no fabricated permission state',()=>{
  const result=memoryContext({enabled:true,userReceipts:[{seq:1,role:'user',content:'Do not send the email.'},{seq:2,role:'user',content:'Now send the email to Pat.'}]},'text','Continue');
  assert.match(result,/Do not send the email/);assert.match(result,/Now send the email to Pat/);
  assert.doesNotMatch(result,/"authorized":true/);
});
test('context is bounded, related legacy claims remain unverified, long passages are not silently truncated',()=>{
  const result=memoryContext({enabled:true,work:{summary:'SQLite is the selected database.',stale:true},userReceipts:[
    {seq:1,role:'user',content:'x'.repeat(20000)+' Do not delete any files.'},
    {seq:2,role:'user',content:'Check the SQLite database.'}]},'text','SQLite database');
  assert.ok(result.length<=CONTEXT_LIMIT);assert.match(result,/authorization and verification not established/);
  assert.match(result,/"omittedUserReceipts":1/);assert.doesNotMatch(result,/xxxx/);
});
