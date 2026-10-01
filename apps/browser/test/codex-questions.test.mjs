// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.
import test from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import {codexQuestions} from '../extension/codex-questions.mjs';
function document(t){const dom=new JSDOM('<body></body>');t.after(()=>dom.window.close());dom.window.HTMLDialogElement.prototype.showModal=function(){this.open=true};dom.window.HTMLDialogElement.prototype.close=function(){this.open=false};return dom.window.document}
const questions=[{id:'format',header:'Format',question:'Pick <b>literal</b> text',options:[{label:'Text',description:'Plain text'}]},{id:'detail',header:'Details',question:'What should it cover?',options:[]}];
test('Codex question form requires explicit complete answers and renders model text literally',async t=>{
 const doc=document(t);const result=codexQuestions(doc,questions);const submit=[...doc.querySelectorAll('button')].find(b=>b.textContent==='Send answers');
 assert.equal(submit.disabled,true);assert.equal(doc.querySelector('b'),null);
 const select=doc.querySelector('select');select.value='Text';select.dispatchEvent(new doc.defaultView.Event('change'));assert.equal(submit.disabled,true);
 const text=doc.querySelectorAll('textarea')[1];text.value='The next step';text.dispatchEvent(new doc.defaultView.Event('input'));assert.equal(submit.disabled,false);
 submit.click();assert.deepEqual(await result,[{id:'format',selected:['Text']},{id:'detail',selected:[],custom:'The next step'}]);assert.equal(doc.querySelector('dialog'),null);assert.equal(text.value,'');
});
test('cancelling or upstream resolution dismisses questions without partial answers',async t=>{
 const doc=document(t);let result=codexQuestions(doc,questions);doc.querySelector('textarea').value='Partial';doc.querySelector('button').click();assert.equal(await result,null);
 const controller=new AbortController();result=codexQuestions(doc,questions,controller.signal);controller.abort();assert.equal(await result,null);assert.equal(doc.querySelector('dialog'),null);
});
