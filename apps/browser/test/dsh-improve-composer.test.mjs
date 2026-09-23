// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.
import test from 'node:test';import assert from 'node:assert/strict';import {JSDOM} from 'jsdom';import React from 'react';import {createRoot} from 'react-dom/client';import {registerImproveComposer} from '../../../adapters/dsh-prompt-library/src/improve-composer.js';
const delay=ms=>new Promise(r=>setTimeout(r,ms));
test('supported composer slot preserves newer drafts, replaces only on completion and offers Undo',async()=>{
 const dom=new JSDOM('<div data-composer-card><div id="root"></div><div contenteditable="true"></div></div>',{pretendToBeVisual:true});
 const prior={window:globalThis.window,document:globalThis.document,ResizeObserver:globalThis.ResizeObserver,getComputedStyle:globalThis.getComputedStyle,fetch:globalThis.fetch};Object.assign(globalThis,{window:dom.window,document:dom.window.document,ResizeObserver:class{observe(){}disconnect(){}},getComputedStyle:dom.window.getComputedStyle});
 let component,input={draft:'Original draft',draftRev:1,phase:'plain',occurrences:[]},resolve,failWrite=false;const writes=[];
 globalThis.fetch=()=>new Promise(r=>resolve=r);const scope={slots:{inject:(name,fn)=>{assert.equal(name,'conversation.input.overlay');fn()},register:(meta,view)=>{component=view}},modelDirectories:{}};
 registerImproveComposer({inject:(_,fn)=>fn(scope)},React);const root=createRoot(document.querySelector('#root'));
 const render=()=>root.render(React.createElement(component,{useInput:fn=>fn(input),inputActions:{setDraft:text=>{if(failWrite)throw Error('Editor unavailable');writes.push(text);setTimeout(()=>{input={...input,draft:text,draftRev:input.draftRev+1};render()},20)}},directory:{load:async()=>({current:{provider:'test',model:'test'}})}}));
 try{
  render();await delay(30);document.querySelector('[aria-label="Improve prompt"]').click();await delay(30);assert.deepEqual(writes,[]);
  input={...input,draft:'Newer draft',draftRev:2};render();await delay(20);resolve({ok:true,json:async()=>({ok:true,kind:'rewrite',text:'Stale result'})});await delay(740);assert.deepEqual(writes,[]);
  document.querySelector('[aria-label="Improve prompt"]').click();await delay(30);resolve({ok:true,json:async()=>({ok:true,kind:'rewrite',text:'Improved draft'})});await delay(760);assert.deepEqual(writes,['Improved draft']);
  assert.equal(document.querySelector('.augmentor-improve-note'),null);assert.equal(document.querySelector('[aria-label="Undo prompt improvement"]').textContent,'↶');document.querySelector('[aria-label="Undo prompt improvement"]').click();await delay(50);assert.deepEqual(writes,['Improved draft','Newer draft']);
  document.querySelector('[aria-label="Improve prompt"]').click();await delay(30);resolve({ok:true,json:async()=>({ok:true,kind:'clarify',text:'Which document?'})});await delay(30);assert.equal(document.querySelector('.augmentor-improve-note'),null);assert.equal(document.querySelector('.augmentor-improve').getAttribute('title'),null);assert.deepEqual(writes,['Improved draft','Newer draft']);
  failWrite=true;document.querySelector('[aria-label="Improve prompt"]').click();await delay(30);resolve({ok:true,json:async()=>({ok:true,kind:'rewrite',text:'Cannot apply this'})});await delay(760);assert.equal(document.querySelector('.augmentor-improve-busy'),null);assert.equal(document.querySelector('.augmentor-improve').textContent,'!');
 }finally{root.unmount();dom.window.close();Object.assign(globalThis,prior)}
});
