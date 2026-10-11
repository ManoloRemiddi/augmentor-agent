// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {projectDshContext} from '../apps/harness/dsh-context-projection.mjs';
const request=(id,seq,turnId='t')=>({id,seq,turnId,kind:'model/request',time:seq*10,data:{provider:'fixture',model:'selected',capacity:1000}});
const done=(id,usage)=>({kind:'model/complete',requestId:id,data:{usage,durationMs:50}});
test('context snapshots keep request-specific headers/messages and disjoint provider usage',()=>{
 const state={records:[request('one',1),done('one',{input:10,cacheRead:20,cacheWrite:3,output:4}),request('two',2),done('two',{input:11,cacheRead:21,cacheWrite:0,output:5})],events:[],payloads:{one:{messages:[{role:'system',content:'First instructions'},{role:'user',content:'First input'}],tools:[]},two:{messages:[{role:'system',content:'Changed instructions'},{role:'user',content:'First input'},{role:'assistant',content:'Reply'},{role:'tool',name:'read',content:'Exact file content'}],tools:[{type:'function',function:{name:'read',parameters:{type:'object'}}}]}}};
 const value=projectDshContext(state),[first,second]=value.timeline.requests;
 const assemble=seq=>[...value.timeline.nodes,...value.timeline.archive].filter(n=>n.seq<seq&&(n.gone===undefined||n.gone>seq));
 assert.deepEqual(assemble(first.seq).map(n=>n.text),['First input']);assert.equal(assemble(first.seq)[0].seq,assemble(second.seq)[0].seq,'unchanged message prefix keeps one identity across requests');assert.deepEqual(assemble(second.seq).map(n=>n.text),['First input','Reply','Exact file content']);
 assert.equal(value.headerContent.get(value.headers.headers[0].seq).system,'First instructions');assert.equal(value.headerContent.get(value.headers.headers[1].seq).system,'Changed instructions');
 assert.deepEqual(value.usage,{uncachedInputTokens:21,cacheReadTokens:41,cacheWriteTokens:3,outputTokens:9});assert.equal(first.prompt,33);assert.equal(second.prompt,32);assert.equal(value.pressure.pressureTokens,32);assert.equal(value.pressure.contextWindow,1000);
 assert.equal(value.timeline.counts.turns,1);assert.equal(second.step,2);assert.equal(value.requestIds.get(first.seq),'one');assert.equal(value.timeline.current.inject,0);assert.equal(value.timeline.current.skill,0);
});
test('uncaptured/newest/unsupported requests do not inherit a provider anchor or fabricated empty bars',()=>{
 const value=projectDshContext({records:[request('old',1),done('old',{input:20}),request('latest',2)],events:[],payloads:{old:{messages:[{role:'user',content:'Retained'}]}}});
 assert.equal(value.coverage.available,1);assert.equal(value.coverage.observed,2);assert.equal(value.coverage.latestAvailable,false);assert.equal(value.pressure,null);assert.equal(value.timeline.contextWindow,undefined);assert.equal(value.timeline.requests.length,1);
 const unsupported=projectDshContext({records:[request('other',1)],events:[],payloads:{other:{contents:[{role:'user',parts:[{text:'Unmapped provider'}]}]}}});assert.equal(unsupported.coverage.unsupported,1);assert.equal(unsupported.timeline.requests.length,0);
 const empty=projectDshContext({records:[],events:[],payloads:{}});assert.equal(empty.pressure,null);assert.equal(empty.timeline.counts.steps,0);
});
test('images remain counted metadata without publishing binary data or treating model calls as file execution',()=>{
 const state={records:[request('a',1)],events:[],payloads:{a:{messages:[{role:'user',content:[{type:'text',text:'A picture'},{type:'image_url',image_url:{url:'data:image/png;base64,PRIVATEBYTES'}}]},{role:'assistant',content:'',tool_calls:[{id:'x',type:'function',function:{name:'read',arguments:'{"path":"/fixture.txt"}'}}]}]}}};
 const value=projectDshContext(state);assert.equal(value.timeline.images,1);assert(!JSON.stringify(value.timeline).includes('PRIVATEBYTES'));assert.equal(value.timeline.fileOps.length,0);
 state.events=[{type:'assistant/message',data:{message:{content:[{type:'toolCall',id:'x',name:'read',arguments:{path:'/fixture.txt'}}]}}},{type:'tool/result',data:{toolCallId:'x',isError:false}}];
 assert.equal(projectDshContext(state).timeline.fileOps.length,1);
});

test('repeated polling keeps the eight newest eligible bodies and never silently backfills the entire log',async()=>{
 const {DshPiController}=await import('../apps/harness/dsh-pi-controller.mjs');let reads=0;
 const controller=new DshPiController('fixture',async()=>{reads++;return {ok:true,json:async()=>({result:{available:true,text:'{"messages":[]}',hasMore:false}})};});
 controller.update({sessionId:'s',records:Array.from({length:12},(_,i)=>({...request(String(i),i+1),payload:{state:'retained',bytes:15}}))});
 await controller.hydrate();await controller.hydrate();assert.equal(reads,8);assert.deepEqual(Object.keys(controller.state.payloads),['4','5','6','7','8','9','10','11']);
 controller.update({records:[...controller.state.records,{...request('12',13),payload:{state:'retained',bytes:15}}]});await controller.hydrate();assert.equal(reads,9);assert.deepEqual(Object.keys(controller.state.payloads),['5','6','7','8','9','10','11','12']);
 const value=projectDshContext({records:[request('first',1),{kind:'context/edit',seq:2,time:20,data:{}},{kind:'compaction/end',seq:3,time:30,data:{}}],events:[],payloads:{}});assert.equal(value.timeline.counts.prunes,0);assert.equal(value.timeline.events.length,1);
});


test('changed or reordered provider messages reconstruct their own order without falsely reusing prefix identity',()=>{
 const value=projectDshContext({records:[request('before',1),request('after',2)],events:[],payloads:{before:{messages:[{role:'user',content:'A'},{role:'assistant',content:'B'}]},after:{messages:[{role:'assistant',content:'B'},{role:'user',content:'Changed A'}]}}});
 const at=seq=>[...value.timeline.nodes,...value.timeline.archive].filter(n=>n.seq<seq&&(n.gone===undefined||n.gone>seq)).sort((a,b)=>a.seq-b.seq);
 assert.deepEqual(at(value.timeline.requests[0].seq).map(n=>n.text),['A','B']);assert.deepEqual(at(value.timeline.requests[1].seq).map(n=>n.text),['B','Changed A']);assert.notEqual(at(value.timeline.requests[0].seq)[0].seq,at(value.timeline.requests[1].seq)[0].seq);
});
