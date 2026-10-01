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
    if(request.action==='account-status')return {ok:true,result:{enabled:false,reason:'Subscription login awaits eligibility confirmation.',accounts:[],attempt:null}};
    throw Error('Unexpected request');
  };
  const dialog=codexSetupDialog(dom.window.document,send);await settle();
  const field=label=>dialog.querySelector(`[aria-label="${label}"]`);
  const button=label=>[...dialog.querySelectorAll('button')].find(button=>button.textContent===label);
  assert.equal(button('Check Codex connection').disabled,true);
  field('Endpoint URL').value='http://127.0.0.1:8080/v1';field('Model ID').value='fixture';field('API key').value='fixture-secret';
  button('Save connection').click();await settle();
  assert.equal(field('API key').value,'');assert.equal(button('Check Codex connection').disabled,false);
  assert.equal(calls.filter(row=>row.action==='test').length,0);
  button('Check Codex connection').click();await settle();assert.deepEqual(calls.filter(row=>row.action==='test').at(-1),{action:'test',id:rows[0].id,capability:'agent'});assert.match(dialog.textContent,/Codex chat and the test tool worked/);
  button('Check image response').click();assert.equal(button('Check image response').disabled,true);await settle();
  assert.deepEqual(calls.filter(row=>row.action==='test').at(-1),{action:'test',id:rows[0].id,capability:'image'});
  assert.match(dialog.textContent,/Start a new chat/);
  field('Model ID').value='other';field('Model ID').dispatchEvent(new dom.window.Event('input'));
  assert.equal(button('Check Codex connection').disabled,true);assert.equal(button('Check image response').disabled,true);
  button('Save connection').click();await settle();
  assert.equal(Object.hasOwn(calls.filter(row=>row.action==='configure').at(-1).profile,'credential'),false);
  field('Remove the saved key').checked=true;button('Save connection').click();await settle();
  assert.equal(calls.filter(row=>row.action==='configure').at(-1).profile.credential,null);
});

function accountFixture(t,{enabled=true,startGate}={}){
  const dom=new JSDOM('<body></body>');t.after(()=>dom.window.close());
  dom.window.HTMLDialogElement.prototype.showModal=function(){this.open=true};
  dom.window.HTMLDialogElement.prototype.close=function(){this.open=false;this.dispatchEvent(new dom.window.Event('close'))};
  const timers=[];dom.window.setTimeout=fn=>{timers.push(fn);return timers.length};dom.window.clearTimeout=id=>{timers[id-1]=null};
  const calls=[],status={enabled,reason:enabled?undefined:'Subscription login awaits eligibility confirmation.',accounts:[],attempt:null};
  const send=async(type,{request}={})=>{
    calls.push(request);
    if(request.action==='profiles')return {ok:true,result:{profiles:[]}};
    if(request.action==='account-status')return {ok:true,result:structuredClone(status)};
    if(request.action==='account-start'){
      await startGate?.promise;status.attempt={id:'synthetic-attempt',state:'opening'};return {ok:true,result:{attempt:{...status.attempt}}};
    }
    if(request.action==='account-cancel'){status.attempt.state='cancelled';return {ok:true,result:{requested:true}}};
    if(request.action==='account-sign-out')return {ok:true,result:{status:structuredClone(status),remoteRevocationConfirmed:false,localCleanupConfirmed:false}};
    throw Error('Unexpected account request');
  };
  const dialog=codexSetupDialog(dom.window.document,send);
  const button=label=>[...dialog.querySelectorAll('button')].find(button=>button.textContent===label);
  return {dom,dialog,button,status,calls,timers,select:dialog.querySelector('[aria-label="ChatGPT account"]'),
    poll:async()=>{const next=timers.findIndex(Boolean);assert.notEqual(next,-1);const fn=timers[next];timers[next]=null;await fn();await settle();}};
}
test('unconfirmed subscription eligibility is visible and prevents Browser login',async t=>{
  const f=accountFixture(t,{enabled:false});await settle();
  assert.equal(f.button('Sign in with ChatGPT').disabled,true);assert.match(f.dialog.textContent,/eligibility confirmation/);
  f.button('Sign in with ChatGPT').click();await settle();assert.equal(f.calls.filter(row=>row.action==='account-start').length,0);
});
test('Browser login keeps Close available; explicit cancellation shares host status',async t=>{
  const f=accountFixture(t);await settle();f.button('Sign in with ChatGPT').click();await settle();
  assert.deepEqual(f.calls.find(row=>row.action==='account-start').account,{requestPlanUsage:false});
  assert.equal(f.button('Close').disabled,false);assert.equal(f.button('Sign in with ChatGPT').disabled,true);assert.equal(f.button('Cancel sign-in').disabled,false);
  f.button('Cancel sign-in').click();await settle();assert.equal(f.status.attempt.state,'cancelled');assert.equal(f.button('Sign in with ChatGPT').disabled,false);
});
test('closing Browser settings before a delayed start reply cancels the returned owned attempt and stops polling',async t=>{
  const startGate=Promise.withResolvers(),f=accountFixture(t,{startGate});await settle();f.button('Sign in with ChatGPT').click();await settle();
  f.button('Close').click();assert.equal(f.dialog.isConnected,false);assert.equal(f.timers.some(Boolean),false);
  startGate.resolve();await settle();assert.deepEqual(f.calls.find(row=>row.action==='account-cancel'),{action:'account-cancel',account:{attemptId:'synthetic-attempt'}});
});
test('Browser settings poll Desktop-owned attempts but do not cancel them on Close',async t=>{
  const f=accountFixture(t);await settle();f.status.attempt={id:'desktop-attempt',state:'waiting'};await f.poll();
  assert.equal(f.button('Cancel sign-in').disabled,false);f.button('Close').click();await settle();
  assert.equal(f.calls.some(row=>row.action==='account-cancel'),false);
});
test('Browser plan permission needs an explicit action and logout does not overstate revocation or cleanup',async t=>{
  const f=accountFixture(t);await settle();f.status.accounts=[{id:'fixture-account',label:'Fixture',active:true}];await f.poll();
  f.select.value='fixture-account';f.select.dispatchEvent(new f.dom.window.Event('change'));
  f.button('Allow ChatGPT plan usage').click();await settle();
  assert.deepEqual(f.calls.find(row=>row.action==='account-start').account,{accountId:'fixture-account',requestPlanUsage:true});
  f.button('Cancel sign-in').click();await settle();f.button('Sign out').click();await settle();
  assert.match(f.dialog.textContent,/Remote revocation is unconfirmed/);assert.match(f.dialog.textContent,/Unlock the OS credential store/);
});
