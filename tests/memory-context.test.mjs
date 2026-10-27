// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {memoryContext,selectContinuity,CONTEXT_LIMIT} from '../dist/memory/src/context.js';

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
test('page headings do not consume fact slots or displace personal reply preferences',()=>{
 const value={enabled:true,relationship:{items:[{text:'I prefer concise replies.'},{text:'Do not start downloads.'}]},work:{pages:[{name:'Current project state',content:'# Current project state\n\n## Plans versus completed work\n\n## Current database\n\nAtlas uses SQLite.'}]}};
 const selected=selectContinuity(value,'Current Atlas project state and database; plans versus completed work and preferred reply style?');
 assert(selected.some(row=>row.content==='I prefer concise replies.'),'a stored personal preference remains available beside relevant project facts');
 assert(selected.some(row=>row.content==='Atlas uses SQLite.'));assert(!selected.some(row=>/^#{1,6}\s/.test(row.content)),'heading-only blocks are navigation metadata, not fact excerpts');
 assert(selected.length<=4);assert(memoryContext(value,'text','Current Atlas project state and database; plans versus completed work and preferred reply style?').length<=CONTEXT_LIMIT);
});
test('a page fragment containing a heading and factual text remains verbatim',()=>{
 const content='## Atlas database\nAtlas uses SQLite.';const selected=selectContinuity({work:{pages:[{name:'Current project state',content}]}},'Atlas database');assert.equal(selected[0].content,content);
});
test('eligible extracted claims take precedence over synthesized pages in the same scope',()=>{
 const value={relationship:{pages:[{name:'Preferences and boundaries',content:'No preferred reply style is recorded.\n\nNo concise reply preference is recorded.\n\nThere are no supported communication preferences.\n\nThe current preferred reply style is unknown.'}],items:[{id:'preference',text:'User prefers concise replies.'},{id:'boundary',text:'User asked Augmentor not to start downloads.'}]},work:{items:[{id:'database',text:'Atlas uses SQLite as its database.'}]}};
 const selected=selectContinuity(value,'State the Atlas database and my preferred reply style using recalled memory.');
 assert(selected.some(row=>row.source==='preference'),'synthesized page prose cannot crowd out the extracted preference');
 assert(selected.some(row=>row.source==='boundary'));assert(selected.some(row=>row.source==='database'));
 assert(!selected.some(row=>row.content.includes('is recorded')),'pages remain available through explicit recall rather than contradicting eligible extracted claims in the automatic brief');
 assert(selected.every(row=>row.provenance==='derived claim; authorization and verification not established'));
});
test('pages remain a fallback when a scope has no eligible extracted claims',()=>{
 const value={work:{pages:[{name:'Current project state',content:'Atlas uses SQLite as its database.'}],items:[{text:'The unrelated renderer uses Vulkan.'}]}};
 const selected=selectContinuity(value,'Atlas database');assert.equal(selected.length,1);assert.equal(selected[0].content,'Atlas uses SQLite as its database.');
});

test('a conversational performance check does not recall unrelated historical tests',()=>{
  const value={enabled:true,work:{pages:[{name:'Current project state',content:
    '- Network speed: a download test returned a low rate.\n- Network performance testing remains unfinished.\n- Check the remote endpoint and repeat the test.'}]}};
  for(const query of ["Okay, this is just a test to see how you're performing.",'Just checking your performance.',
    'Hello, are you working?','This is a quick responsiveness test.']){
    assert.equal(memoryContext(value,'text',query),'',query);
    assert.equal(memoryContext(value,'voice',query),'',query);
  }
  assert.match(memoryContext(value,'text','Check the network download speed.'),/Network speed/);
});

test('generic check-ins preserve exact current-session boundaries and specific topic recall',()=>{
  const value={enabled:true,userReceipts:[{seq:1,session:'fixture',role:'user',content:'Do not download files or change the server.'}],
    work:{summary:'SQLite is the selected database.'}};
  const checkin=memoryContext(value,'text','Just testing your response.');
  assert.match(checkin,/Do not download files or change the server/);
  assert.doesNotMatch(checkin,/SQLite/);
  assert.match(checkin,/recalled unfinished work is not automatically/);
  assert.match(memoryContext(value,'text','SQLite'),/SQLite is the selected database/);
});
