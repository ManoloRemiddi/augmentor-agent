// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {projectChat,appendDisplay} from '../apps/harness/chat-projection.js';
const chunk=(seq,type,text)=>({seq,type:'assistant/chunk',data:{chunk:{type,text}}});
test('reopening an interrupted stream keeps text and reasoning without submitting work',()=>{
 const events=[chunk(2,'reasoning-delta','Checking…'),chunk(3,'text-delta','A partial answer'),{seq:4,type:'turn/end',data:{reason:{kind:'interrupted'}}}];
 const items=projectChat(events);assert.equal(items[0].text,'A partial answer');assert.equal(items[0].thinking,'Checking…');assert(items[0].partial);assert.equal(items[0].status,'interrupted');assert(items[1].text.includes('outcomes may be unknown'));
 assert.deepEqual(projectChat(events),items);
});
test('live snapshot overlap and a final SDK message do not duplicate response bytes',()=>{
 const events=[chunk(2,'reasoning-delta','Think'),chunk(3,'text-delta','Answer')];
 assert.equal(appendDisplay(events,events[1]),false);
 assert.equal(appendDisplay(events,{seq:4,type:'assistant/message',data:{message:{content:[{type:'thinking',thinking:'Think'},{type:'text',text:'Answer'}],stopReason:'aborted'}}}),true);
 const items=projectChat(events);assert.equal(items.length,1);assert.equal(items[0].text,'Answer');assert.equal(items[0].thinking,'Think');assert.equal(items[0].status,'aborted');
});
test('tool status distinguishes finished results from missing outcomes after Stop',()=>{
 const call=(seq,id)=>({seq,type:'tool/call',data:{toolCallId:id,name:'write'}});
 const items=projectChat([call(1,'a'),{seq:2,type:'tool/result',data:{toolCallId:'a',isError:false}},call(3,'b'),{seq:4,type:'turn/end',data:{reason:{kind:'aborted'}}}]);
 assert.equal(items[0].status,'finished');assert.equal(items[1].status,'outcome unknown');assert.equal(items[2].text,'Stopped.');
});

test('recovery notices and truncated output survive reopen without becoming assistant answers',()=>{
 const events=[{seq:1,type:'assistant/message',data:{message:{content:[{type:'text',text:'Partial result'}],stopReason:'length'}}},
  {seq:2,type:'runtime/notice',data:{message:'Bounded recovery 1/2 is continuing from confirmed progress.',incomplete:false}},
  {seq:3,type:'runtime/notice',data:{message:'Task incomplete. The bounded response-recovery budget was exhausted.',incomplete:true}},
  {seq:4,type:'turn/end',data:{reason:{kind:'error'}}}];
 const items=projectChat(events);assert.equal(items[0].partial,true);assert.equal(items[0].status,'length');
 assert.equal(items.filter(item=>item.kind==='assistant').length,1);
 assert.equal(items.filter(item=>item.kind==='status'&&item.text.includes('Task incomplete')).length,1);
 assert.deepEqual(projectChat(events),items);
});
test('a steering notice during generation does not duplicate the final interrupted SDK message',()=>{
 const events=[chunk(1,'reasoning-delta','Thinking'),chunk(2,'text-delta','Partial'),
  {seq:3,type:'runtime/notice',data:{message:'Steering accepted.'}},chunk(4,'text-delta',' answer'),
  {seq:5,type:'assistant/message',data:{message:{content:[{type:'thinking',thinking:'Thinking'},{type:'text',text:'Partial answer'}],stopReason:'aborted'}}},
  {seq:6,type:'user/message',data:{content:[{type:'text',text:'Correction'}]}}];
 const items=projectChat(events);assert.equal(items.filter(item=>item.kind==='assistant').length,1);assert.equal(items[0].text,'Partial answer');assert.equal(items[0].status,'aborted');assert.equal(items[0].thinking,'Thinking');
 assert.equal(items[1].text,'Steering accepted.');assert.equal(items[2].text,'Correction');
 const during=projectChat(events.slice(0,4),{running:true});assert.equal(during.filter(item=>item.kind==='assistant').length,1);assert.equal(during[0].text,'Partial answer');assert.equal(during[0].status,'streaming');
});
