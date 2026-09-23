// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.
import test from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import {memoryDialog} from '../extension/memory.mjs';
test('automatic memory controls are independent of Hindsight',async t=>{
  const dom=new JSDOM('<body></body>',{pretendToBeVisual:true});t.after(()=>dom.window.close());
  dom.window.HTMLDialogElement.prototype.showModal=function(){this.open=true;};
  let enabled=true;const calls=[];
  const send=async(_type,{request})=>{
    calls.push(request);
    if(request.action==='dual.configure'){enabled=request.enabled;return {ok:true,result:{enabled}};}
    if(request.action==='dual.describe')return {ok:true,result:{enabled,events:4,pending:0}};
    if(request.action==='dual.recall')return {ok:true,result:{enabled,relationship:{summary:enabled?'Enjoys calm conversation.':''},work:{summary:enabled?'Project uses SQLite.':''}}};
    if(request.action==='describe')return {ok:true,result:{enabled:false}};
    throw Error('Unexpected operation');
  };
  const dialog=memoryDialog(dom.window.document,send,()=>({harness:'dsh',sessionId:'test'}));
  await new Promise(r=>setTimeout(r,20));
  assert.match(dialog.textContent,/Enjoys calm conversation/);assert.match(dialog.textContent,/Project uses SQLite/);
  [...dialog.querySelectorAll('button')].find(b=>b.textContent==='Pause automatic memory').click();await new Promise(r=>setTimeout(r,20));
  assert.equal(enabled,false);assert.match(dialog.textContent,/Resume automatic memory/);assert.ok(!calls.some(c=>c.action==='disable'));
});
