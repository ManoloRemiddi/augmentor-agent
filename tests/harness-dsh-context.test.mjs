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
 const value=projectDshContext({records:[request('first',1),{kind:'context/edit',seq:2,time:20,data:{}},{kind:'compaction/end',seq:3,time:30,data:{}}],events:[],payloads:{}});assert.equal(value.timeline.counts.prunes,0);assert.equal(value.timeline.events.length,0);assert.equal(value.coverage.compactionAttempts,1);
});


test('changed or reordered provider messages reconstruct their own order without falsely reusing prefix identity',()=>{
 const value=projectDshContext({records:[request('before',1),request('after',2)],events:[],payloads:{before:{messages:[{role:'user',content:'A'},{role:'assistant',content:'B'}]},after:{messages:[{role:'assistant',content:'B'},{role:'user',content:'Changed A'}]}}});
 const at=seq=>[...value.timeline.nodes,...value.timeline.archive].filter(n=>n.seq<seq&&(n.gone===undefined||n.gone>seq)).sort((a,b)=>a.seq-b.seq);
 assert.deepEqual(at(value.timeline.requests[0].seq).map(n=>n.text),['A','B']);assert.deepEqual(at(value.timeline.requests[1].seq).map(n=>n.text),['B','Changed A']);assert.notEqual(at(value.timeline.requests[0].seq)[0].seq,at(value.timeline.requests[1].seq)[0].seq);
});

test('only confirmed saved summaries enter the supplier Compact markers; failed and aborted attempts stay in coverage',()=>{
 const records=[{kind:'compaction/end',seq:1,data:{operationId:'fail',returnedSummary:false}},{kind:'compaction/receipt',seq:2,data:{requestId:'fail',state:'failed'}},{kind:'compaction/end',seq:3,data:{operationId:'abort',aborted:true}},{kind:'compaction/end',seq:4,data:{operationId:'saved',returnedSummary:true}},{kind:'compaction/receipt',seq:5,data:{requestId:'saved',state:'completed',entryId:'native-summary',tokensBefore:26000,estimatedTokensAfter:20000}}];
 const value=projectDshContext({records,events:[],payloads:{}});assert.equal(value.timeline.counts.compactions,1);assert.equal(value.timeline.events.length,1);assert.match(value.timeline.events[0].detail,/native-summary/);assert.equal(value.coverage.compactionAttempts,3);assert.equal(value.coverage.confirmedCompactions,1);
});

test('tool-result cards retain exact preceding provider call arguments in each recorded request',()=>{
 const call=(path)=>({role:'assistant',content:'',tool_calls:[{id:'reused',type:'function',function:{name:'read',arguments:path}}]}),result={role:'tool',tool_call_id:'reused',content:'Recorded text'};
 const value=projectDshContext({records:[request('before',1),request('after',2)],events:[{type:'assistant/message',data:{message:{content:[{type:'toolCall',id:'reused',name:'read',arguments:{path:'sdk-value-must-not-replace-provider-value'}}]}}}],payloads:{before:{messages:[call(' { "path": "first.txt" } '),result]},after:{messages:[call('{"path":"changed.txt"}'),result]}}});
 assert.deepEqual(value.conversationNodes.filter(n=>n.kind==='tool-result').map(n=>n.call),[{name:'read',argsRaw:' { "path": "first.txt" } '},{name:'read',argsRaw:'{"path":"changed.txt"}'}]);
});

test('tool-result linkage is chronological, consumes calls once and accepts later reuse of a settled id',()=>{
 const call=(id,args)=>({role:'assistant',content:'',tool_calls:[{id,function:{name:'read',arguments:args}}]}),result=id=>({role:'tool',name:'read',tool_call_id:id,content:'Result'});
 const messages=[result('future'),call('future','{"path":"future.txt"}'),result('future'),result('future'),call('future','malformed retained arguments'),result('future'),call('duplicate','{"path":"one.txt"}'),call('duplicate','{"path":"two.txt"}'),result('duplicate'),call('empty','{}'),result('empty')];
 const cards=projectDshContext({records:[request('one',1)],events:[],payloads:{one:{messages}}}).conversationNodes.filter(n=>n.kind==='tool-result').map(n=>n.call.argsRaw);
 assert.deepEqual(cards,['[Call arguments unavailable in this recorded request]','{"path":"future.txt"}','[Call arguments unavailable in this recorded request]','malformed retained arguments','[Call arguments unavailable in this recorded request]','{}']);
});

test('missing or conflicting call identities never invent arguments from names or another snapshot',()=>{
 const value=projectDshContext({records:[request('one',1),request('two',2)],events:[],payloads:{one:{messages:[{role:'assistant',content:'',tool_calls:[{id:'only-before',function:{name:'read',arguments:'{"path":"before.txt"}'}}]}]},two:{messages:[{role:'tool',name:'read',tool_call_id:'only-before',content:'Orphan'},{role:'assistant',tool_calls:[{id:'mismatch',function:{name:'write',arguments:'{"path":"wrong.txt"}'}}]},{role:'tool',name:'read',tool_call_id:'mismatch',content:'Conflicting name'},{role:'assistant',tool_calls:[{id:'missing',function:{name:'read'}}]},{role:'tool',name:'read',tool_call_id:'missing',content:'Missing arguments'}]}}});
 assert(value.conversationNodes.filter(n=>n.kind==='tool-result').every(n=>n.call.name==='read'&&n.call.argsRaw==='[Call arguments unavailable in this recorded request]'));
});

test('unloaded request choices stay out of charts and retain selection identity when older bodies arrive',()=>{
 const records=Array.from({length:12},(_,i)=>request(String(i),i+10)),payloads=Object.fromEntries(records.slice(-8).map(r=>[r.id,{messages:[{role:'user',content:r.id}]}]));
 const before=projectDshContext({records,events:[],payloads});assert.equal(before.requestChoices.length,12);assert.equal(before.timeline.requests.length,8);assert.equal(before.requestChoices[0].available,false);
 const identities=value=>Object.fromEntries(value.timeline.requests.map(r=>[value.requestIds.get(r.seq),r.seq]));
 const after=projectDshContext({records:[request('earlier-metadata',1),...records],events:[],payloads:{...payloads,0:{messages:[{role:'user',content:'Read explicitly'}]}}});assert.equal(after.timeline.requests.length,9);
 for(const [id,seq] of Object.entries(identities(before)))assert.equal(identities(after)[id],seq);assert.equal(after.requestChoices.find(r=>r.id==='0').seq,before.requestChoices[0].seq);
});

test('explicit older reads pin only one extra body, survive polling and evict prior selections without backfill',async()=>{
 const {DshPiController}=await import('../apps/harness/dsh-pi-controller.mjs'),reads=[];
 const controller=new DshPiController('fixture',async(_url,options)=>{const call=JSON.parse(options.body);assert.equal(call.method,'observation.payload');reads.push(call.params.eventId);return {ok:true,json:async()=>({result:{available:true,text:JSON.stringify({messages:[{role:'user',content:call.params.eventId}]}),hasMore:false}})};});
 const records=Array.from({length:12},(_,i)=>({...request(String(i),i+1),payload:{state:'retained',bytes:100,sha256:'immutable-'+i}}));controller.update({sessionId:'s',phase:'ready',readOnly:true,records});await controller.hydrate();assert.equal(reads.length,8);
 await controller.selectContextRequest('0');assert.equal(reads.length,9);assert.equal(Object.keys(controller.state.payloads).length,9);await controller.hydrate();assert.equal(reads.length,9);assert(controller.state.payloads['0']);
 await controller.selectContextRequest('1');assert.equal(reads.length,10);assert(!controller.state.payloads['0']);assert(controller.state.payloads['1']);await controller.selectContextRequest(null);assert.equal(Object.keys(controller.state.payloads).length,8);assert(!controller.state.payloads['1']);
 assert.equal(controller.state.readOnly,true);assert.equal(controller.state.contextRead,null);
});

test('late selected-body replies cannot replace a newer selection or another conversation',async()=>{
 const {DshPiController}=await import('../apps/harness/dsh-pi-controller.mjs'),pending=new Map();
 const controller=new DshPiController('fixture',async(_url,options)=>{const call=JSON.parse(options.body);return await new Promise(resolve=>pending.set(call.params.sessionId+':'+call.params.eventId,()=>resolve({ok:true,json:async()=>({result:{available:true,text:'{"messages":[]}',hasMore:false}})})));});
 const records=Array.from({length:12},(_,i)=>({...request(String(i),i+1),payload:{state:'retained',bytes:15}}));controller.update({sessionId:'one',phase:'ready',records});const first=controller.selectContextRequest('0'),second=controller.selectContextRequest('1');pending.get('one:1')();await second;pending.get('one:0')();await first;assert.equal(controller.state.contextRequestId,'1');assert.equal(controller.state.contextRead.id,'1');assert(!controller.state.payloads['0']);
 const old=controller.hydrate();controller.epoch++;controller.update({sessionId:'two',records:[{...request('new',1),payload:{state:'retained',bytes:15}}],payloads:{},contextRequestId:null,contextRead:null});const fresh=controller.hydrate();pending.get('two:new')();await fresh;pending.get('one:4')();await old;assert.deepEqual(Object.keys(controller.state.payloads),['new']);
});

test('a new request arriving during hydration is reconciled within the same bounded window',async()=>{
 const {DshPiController}=await import('../apps/harness/dsh-pi-controller.mjs');let release;const reads=[];
 const controller=new DshPiController('fixture',async(_url,options)=>{const id=JSON.parse(options.body).params.eventId;reads.push(id);if(id==='4')await new Promise(resolve=>release=resolve);return {ok:true,json:async()=>({result:{available:true,text:'{"messages":[]}',hasMore:false}})};});
 const records=Array.from({length:12},(_,i)=>({...request(String(i),i+1),payload:{state:'retained',bytes:15}}));controller.update({sessionId:'s',records});const first=controller.hydrate();controller.update({records:[...records,{...request('12',13),payload:{state:'retained',bytes:15}}]});const again=controller.hydrate();release();await Promise.all([first,again]);assert.deepEqual(Object.keys(controller.state.payloads),['5','6','7','8','9','10','11','12']);assert.equal(reads.length,9);
});

test('earlier metadata pages use advancing cursors, coalesce reads and reject stale or failed pages without body reads',async()=>{
 const {DshPiController}=await import('../apps/harness/dsh-pi-controller.mjs');let release,calls=0;
 const controller=new DshPiController('fixture',async(_url,options)=>{const call=JSON.parse(options.body);assert.equal(call.method,'observation.list');assert.equal(call.params.beforeSeq,100);assert.equal(call.params.limit,100);calls++;await new Promise(resolve=>release=resolve);return {ok:true,json:async()=>({result:{records:[request('older',99)],hasMore:false}})};});
 controller.update({sessionId:'s',phase:'ready',records:[request('latest',100)],observationHasMore:true});const a=controller.loadContextOlder(),b=controller.loadContextOlder();assert.equal(calls,1);release();await Promise.all([a,b]);assert.deepEqual(controller.state.records.map(r=>r.id),['older','latest']);assert.equal(controller.state.observationHasMore,false);assert.deepEqual(controller.state.payloads,{});
 controller.update({records:[request('latest',100)],observationHasMore:true});const stale=controller.loadContextOlder();controller.epoch++;controller.update({sessionId:'other',records:[],contextPage:null});release();await stale;assert.deepEqual(controller.state.records,[]);assert.equal(controller.state.contextPage,null);
 controller.update({sessionId:'s',records:[request('latest',100)],observationHasMore:true});controller.rpc=async()=>({records:[request('latest',100)],hasMore:true});await controller.loadContextOlder();assert.match(controller.state.contextPage.error,/did not advance/);assert.equal(controller.state.records.length,1);assert.equal(controller.state.observationHasMore,true);
});

test('unretained, oversized and byte-limit failures remain unavailable rather than being read or projected as empty',async()=>{
 const {DshPiController}=await import('../apps/harness/dsh-pi-controller.mjs');let calls=0;
 const controller=new DshPiController('fixture',async()=>{calls++;return {ok:true,json:async()=>({result:{available:true,text:JSON.stringify({messages:[],text:'日'.repeat(400000)}),hasMore:false}})};});
 controller.update({sessionId:'s',phase:'ready',records:[{...request('off',1),payload:{state:'disabled'}},{...request('large',2),payload:{state:'retained',bytes:1024*1024+1}},{...request('bound',3),payload:{state:'retained',bytes:15}}]});await controller.selectContextRequest('off');assert.equal(controller.state.contextRead.state,'unavailable');await controller.selectContextRequest('large');assert.match(controller.state.contextRead.reason,/1 MiB/);assert.equal(calls,0);await controller.selectContextRequest('bound');assert.equal(controller.state.contextRead.state,'failed');assert.match(controller.state.contextRead.reason,/1 MiB/);assert.deepEqual(controller.state.payloads,{});assert.equal(projectDshContext(controller.state).timeline.requests.length,0);
});
