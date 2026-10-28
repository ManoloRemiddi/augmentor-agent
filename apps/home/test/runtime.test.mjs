// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {fixture,turnOn,args,tool,answer} from './fixtures/runtime.mjs';
import {READ_TOOL} from '../../../adapters/dsh-home/index.mjs';

test('actual DSH + MCP discovers tools, executes once and resumes persisted context',async t=>{
  const h=await fixture(t,n=>[tool(READ_TOOL,{},'read'),tool(turnOn,args,'write'),answer('Lamp switched on.'),answer('You asked me to turn on the test lamp.')][n-1]);
  const result=await h.runtime.ask('one','household','Turn on the test lamp');
  assert.equal(result.status,'completed');assert.equal(h.writes(),1);
  assert.ok(result.tool_calls.some(x=>x.status==='completed'&&x.action_id));
  assert.ok(h.requests[0].tools.every(x=>!x.function.name.includes('Unlock')));
  await h.restart();
  await h.runtime.ask('two','household','What did I ask you to do?');
  assert.match(JSON.stringify(h.requests.at(-1).messages),/Turn on the test lamp/);
  assert.equal(h.writes(),1);
});

test('uncertain MCP mutation blocks same-request retry and subsequent requests',async t=>{
  const h=await fixture(t,n=>n===1?tool(turnOn,args,'first'):n===2?tool(turnOn,args,'retry'):n===4?tool(turnOn,args,'later'):answer('Action outcome is unknown.'),{failWrite:true});
  assert.equal((await h.runtime.ask('one','household','Turn on test')).status,'incomplete');
  await h.runtime.ask('two','household','Try again');
  assert.equal(h.writes(),1);assert.equal(h.ledger.pending()[0].status,'unknown');
});

test('unadvertised administrative tools and unsafe domains are denied before MCP',async t=>{
  const h=await fixture(t,n=>[tool('mcp__homeassistant__intent__HassUnlock',{name:'Door',domain:['lock']},'bad'),tool(turnOn,{name:'Door',domain:['lock']},'bad-domain'),answer('Not permitted.')][n-1]);
  await h.runtime.ask('one','household','Unlock the door');assert.equal(h.writes(),0);
});

 test('deadline cancellation after dispatch latches uncertainty and does not replay', {timeout:10000}, async t=>{
  // Hold the MCP write and fire the real deadline callback only after dispatch.
  // A 100 ms wall-clock race also timed out before dispatch on loaded CI hosts.
  const dispatched=Promise.withResolvers(),release=Promise.withResolvers();
  let deadline;
  const originalSetTimeout=globalThis.setTimeout;
  t.mock.method(globalThis,'setTimeout',(callback,delay,...args)=>{
    if(delay===30001)deadline=callback;
    return originalSetTimeout(callback,delay,...args);
  });
  t.after(()=>release.resolve());
  const h=await fixture(t,n=>n<=2?tool(turnOn,args,'write-'+n):answer('Stopped.'),{
    onWrite:()=>{dispatched.resolve();return release.promise;},requestTimeoutMs:30001,
  });
  const pending=h.runtime.ask('deadline','home','Turn on test');
  await dispatched.promise;
  assert.equal(typeof deadline,'function');deadline();
  const result=await pending;
  assert.equal(result.status,'incomplete');assert.equal(result.reason,'Request deadline exceeded');
  assert.equal(h.writes(),1);assert.equal(h.ledger.pending()[0].status,'unknown');
  release.resolve();
  await h.runtime.ask('after-deadline','home','Try again');
  assert.equal(h.writes(),1);assert.equal(h.ledger.pending()[0].status,'unknown');
});

 test('provider failure returns incomplete without a device action',async t=>{
  const h=await fixture(t,()=>({role:'assistant',content:''}));
  const result=await h.runtime.ask('failure','home','Read test lamp');
  assert.equal(result.status,'incomplete');assert.equal(h.writes(),0);
});

 test('partial HA intent failure inside successful MCP envelope blocks further changes',async t=>{
  const h=await fixture(t,n=>n===1?tool(turnOn,args,'partial'):n===2?tool(turnOn,{name:'Another Lamp',domain:['light']},'different'):answer('Partial failure; inspect state.'),{
    writeResult:{response_type:'action_done',data:{success:[{id:'light.one'}],failed:[{id:'light.two'}]}}
  });
  const result=await h.runtime.ask('partial','home','Turn on lights');
  assert.equal(result.status,'incomplete');assert.equal(h.writes(),1);
  assert.equal(h.ledger.pending()[0].status,'unknown');
 });

 test('read-only authority denies a model-requested write before MCP dispatch',async t=>{
  const h=await fixture(t,n=>n===1?tool(turnOn,args,'forbidden'):answer('Read-only access.'));
  await h.runtime.ask('readonly','viewer','Turn on test',{readOnly:true});
  assert.equal(h.writes(),0);assert.equal(h.ledger.pending().length,0);
 });

 test('cancelling while the session is being created prevents the first model and device call',async t=>{
  const h=await fixture(t,n=>n===1?tool(turnOn,args,'must-not-run'):answer('Done'));
  const pending=h.runtime.ask('startup','home','Turn on test');h.runtime.cancel();
  const result=await pending;assert.equal(result.status,'incomplete');assert.equal(h.requests.length,0);assert.equal(h.writes(),0);
 });

test('legacy Home rollback refuses to silently replace a Pi conversation with an empty DSH history',async t=>{
 const h=await fixture(t,()=>answer('Authored Pi history'),{harness:'pi'});await h.runtime.ask('pi-one','household','Retain this Pi conversation');const before=h.requests.length;
 h.config.harness='dsh';await h.restart();await assert.rejects(h.runtime.ask('dsh-two','household','Continue here'),/Pi history/);assert.equal(h.requests.length,before);assert.equal(h.writes(),0);
});
