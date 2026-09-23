// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {actionEffect,actionKey,actionOutcome,recoveryDenial} from '../adapters/dsh-execution/actions.mjs';
const outcome=(name,value)=>actionOutcome({name,arguments:{}},{isError:false,value},undefined,'unknown');
test('pinned shell DTO detects partial failure even when tool isError is false',()=>{
  for(const data of [{exitCode:1},{exitCode:0,timedOut:true},{exitCode:null,signal:'SIGTERM'},{exitCode:0,aborted:true}])
    assert.equal(outcome('bash',{kind:'foreground',...data}).status,'unknown');
  assert.equal(outcome('bash',{kind:'foreground',exitCode:0}).status,'completed');
  assert.equal(outcome('bash','success').status,'unknown');
});
test('background launch and status query retain exact job identity',()=>{
  assert.deepEqual(outcome('bash',{kind:'background',jobId:'job-123'}),{status:'running',jobId:'job-123'});
  for(const [status,want] of [['running','running'],['stopping','running'],['completed','completed'],['failed','unknown'],['killed','unknown']])
    assert.deepEqual(outcome('job_output',{job:{id:'job-123',status}}),{status:want,jobId:'job-123'});
});
test('action identity ignores JSON property order and shell display wording',()=>{
  assert.equal(actionKey('submit',{a:1,b:2}),actionKey('submit',{b:2,a:1}));
  assert.equal(actionKey('bash',{command:'send',description:'first'}),actionKey('bash',{command:'send',description:'again',timeoutMs:5}));
  assert.notEqual(actionKey('submit',{a:1}),actionKey('submit',{a:2}));
});
test('shell and browser changes are not inferred safe from names or descriptions',()=>{
  for(const name of ['bash','browser_click','browser_type','browser_navigate','run_code','unknown'])
    assert.equal(actionEffect(name,{description:'read only'}),'unknown');
  for(const name of ['read','browser_snapshot','job_output'])assert.equal(actionEffect(name,{}),'read');
});
test('trusted operation adapter may classify arguments while broken contracts fail conservatively',()=>{
  const definition={augmentorExecution:{effect:a=>a.operation==='inspect'?'read':'external'}};
  assert.equal(actionEffect('mixed',{operation:'inspect'},definition),'read');
  assert.equal(actionEffect('mixed',{operation:'send'},definition),'external');
  assert.equal(actionEffect('mixed',{}, {augmentorExecution:{effect:()=>{throw Error();}}}),'unknown');
  assert.equal(actionEffect('read',{}, {augmentorExecution:{effect:()=> 'invalid'}}),'unknown');
  assert.equal(actionOutcome({name:'mixed',arguments:{}},{isError:false,value:{}},
    {augmentorExecution:{outcome:()=>({status:'invented'})}},'external').status,'unknown');
});
test('only an explicit pre-dispatch failure permits identical recovery mutation',()=>{
  const ledger=new Map([['same',{effect:'external',status:'failed-before-dispatch'}]]);
  assert.equal(recoveryDenial(ledger,'same','external'),null);
  ledger.get('same').status='completed';assert.match(recoveryDenial(ledger,'same','external'),/already ran/);
  ledger.get('same').status='unknown';assert.match(recoveryDenial(ledger,'different','unknown'),/uncertain/);
  assert.equal(recoveryDenial(ledger,'same','read'),null);
});

test('pinned DSH argument rejection is distinguished from post-dispatch failure',()=>{
  assert.equal(actionOutcome({name:'write'},{isError:true,error:{info:{code:'INVALID_ARGS'}}},undefined,'change').status,'failed-before-dispatch');
  assert.equal(actionOutcome({name:'write'},{isError:true,error:{info:{code:'ABORTED'}}},undefined,'change').status,'unknown');
});
