// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.
import test from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import {codexSetupDialog} from '../extension/codex-setup.mjs';
const settle=()=>new Promise(resolve=>setImmediate(resolve));
test('Codex settings save masked profiles and only check the saved, unchanged connection',async t=>{
  const dom=new JSDOM('<body></body>');t.after(()=>dom.window.close());
  dom.window.HTMLDialogElement.prototype.showModal=function(){this.open=true};
  let rows=[],calls=[];
  const send=async(type,{request}={})=>{
    if(type==='models-refresh')return {ok:true};
    calls.push(request);
    if(request.action==='profiles')return {ok:true,result:{profiles:rows}};
    if(request.action==='configure'){const {credential,...row}=request.profile;rows=[row];return {ok:true,result:row}};
    if(request.action==='test')return {ok:true,result:{valid:true}};
    throw Error('Unexpected request');
  };
  const dialog=codexSetupDialog(dom.window.document,send);await settle();
  const field=label=>dialog.querySelector(`[aria-label="${label}"]`);
  const button=label=>[...dialog.querySelectorAll('button')].find(button=>button.textContent===label);
  assert.equal(button('Check text response').disabled,true);
  field('Endpoint URL').value='http://127.0.0.1:8080/v1';field('Model ID').value='fixture';field('API key').value='fixture-secret';
  button('Save connection').click();await settle();
  assert.equal(field('API key').value,'');assert.equal(button('Check text response').disabled,false);
  assert.equal(calls.filter(row=>row.action==='test').length,0);
  button('Check text response').click();await settle();assert.match(dialog.textContent,/Tools and Codex agent compatibility still need/);
  field('Model ID').value='other';field('Model ID').dispatchEvent(new dom.window.Event('input'));
  assert.equal(button('Check text response').disabled,true);
  button('Save connection').click();await settle();
  assert.equal(Object.hasOwn(calls.filter(row=>row.action==='configure').at(-1).profile,'credential'),false);
  field('Remove the saved key').checked=true;button('Save connection').click();await settle();
  assert.equal(calls.filter(row=>row.action==='configure').at(-1).profile.credential,null);
});
