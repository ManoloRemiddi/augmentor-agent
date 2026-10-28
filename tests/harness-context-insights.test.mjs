// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {foldInsightRecords,insightMetadata,insightProjection,localDay,reportedInsightTokens} from '../apps/harness/dsh-insights-data.mjs';
import {DshInsightsReader} from '../apps/harness/dsh-insights-reader.mjs';
const time=new Date(2026,9,10,12).getTime();
const usage={input:100,cacheRead:20,cacheWrite:3,output:7};
const record=(seq,kind,data={},extra={})=>({id:'r'+seq,sessionId:'a',seq,time,kind,data,...extra});
const request=(seq,extra={})=>record(seq,'model/request',{provider:'fixture',model:'model',api:'openai-completions',capacity:10000},extra);
const end=(seq,requestId,billing=usage)=>record(seq,'model/complete',{usage:billing,durationMs:50},{requestId});
const payload={messages:[{role:'system',content:'Public fixture instructions.'},{role:'user',content:'Authored fixture question.'}]};
const raw=JSON.stringify(payload),sha256=createHash('sha256').update(raw).digest('hex');
const retained={state:'retained',bytes:Buffer.byteLength(raw),sha256};
const current=()=>({phase:'ready',readOnly:false,epoch:1,sessionId:'a'});
function fixture({rows=[{sessionId:'a'}],entries=[request(1,{payload:retained}),end(2,'r1')],workspace={},pageSize=500,body=raw,alter,limits={}}={}){
 const calls=[];const rpc=async(method,params)=>{calls.push({method,params});if(method==='session.list')return {items:rows};if(method==='workspace.list')return {items:[],...workspace};if(method==='observation.payload')return {available:true,text:body,hasMore:false};if(method==='observation.list'){
  let all=entries.map(r=>({...r,sessionId:params.sessionId})).filter(r=>params.beforeSeq===undefined||r.seq<params.beforeSeq);const taken=all.slice(-Math.min(pageSize,params.limit));const page={records:taken,scanned:taken.length,earliestSeq:entries[0]?.seq??null,latestSeq:entries.at(-1)?.seq??null,hasMore:all.length>taken.length,nextBeforeSeq:taken[0]?.seq??null};return alter?alter(page,calls):page;
 }throw Error('Unexpected action '+method);};return {calls,reader:new DshInsightsReader({rpc,current,...limits})};
}
test('Insights joins exact request-local usage across browser-local days and preserves gaps',()=>{
 const second=request(5,{time:time+86400000});const folded=foldInsightRecords([record(1,'turn/start',{}, {turnId:'t1'}),request(2),end(3,'r2'),record(4,'tool/end'),second,end(6,'r5'),request(7),end(8,'absent'),request(9),end(10,'r9'),end(11,'r9')]);
 assert.deepEqual(folded.cost.fixture.model.peak,{uncached:200,cacheRead:40,cacheWrite:6,output:14});assert.equal(folded.days[localDay(time)].requests,3);assert.equal(folded.days[localDay(time+86400000)].tokens,130);assert.equal(folded.turns,1);assert.equal(folded.tools,1);assert.deepEqual(folded.gaps,{unlinkedSettlements:1,usageUnavailable:1,duplicateSettlements:1,invalidBilling:0});assert.equal(folded.modelMs,100);
 const tokens=reportedInsightTokens([{familyCost:folded.cost}]);assert.equal(tokens.total,260);assert.deepEqual(tokens.parts.map(p=>p.value),[200,40,6,14]);assert.equal(reportedInsightTokens([{familyCost:null}]),null);
});
test('Insights never invents missing/malformed/ambiguous billing or unsafe totals',()=>{
 for(const billing of [undefined,{...usage,input:-1},{...usage,input:1.5},{input:2},{...usage,output:Infinity}]){const f=foldInsightRecords([request(1),billing===undefined?record(2,'model/complete',{durationMs:50},{requestId:'r1'}):end(2,'r1',billing)]);assert.deepEqual(f.cost,{});assert.equal(f.gaps.invalidBilling,1);assert.equal(f.modelMs,50,'duration has its own evidence');}
 for(const provider of ['__proto__','constructor','prototype'])assert.deepEqual(foldInsightRecords([{...request(1),data:{provider,model:'m'}},end(2,'r1')]).cost,{});
 assert.deepEqual(foldInsightRecords([request(2),end(1,'r2')]).cost,{});
 const max={input:Number.MAX_SAFE_INTEGER,cacheRead:0,cacheWrite:0,output:0};const f=foldInsightRecords([request(1),end(2,'r1',max),request(3),end(4,'r3')]);assert.equal(f.gaps.invalidBilling,1);assert.equal(f.cost.fixture.model.peak.uncached,Number.MAX_SAFE_INTEGER);
 assert.equal(reportedInsightTokens([{familyCost:f.cost},{familyCost:f.cost}]),null);
 assert.throws(()=>insightMetadata(record(1,'tool/end',{}, {time:1e20})),/identity/);
 const compact=insightMetadata(record(1,'model/complete',{usage,durationMs:20,privateText:'must not retain'}));assert(!JSON.stringify(compact).includes('must not retain'));
});
test('Insights metadata paging folds all retained calls but reads only the newest body',async()=>{
 const entries=[request(1,{payload:retained}),end(2,'r1'),request(3,{payload:retained}),end(4,'r3')];const {reader,calls}=fixture({entries,pageSize:2});assert.equal(await reader.load(),true);const d=reader.state.details.get('a');assert.equal(d.summary.requests,2);assert.equal(d.currentAvailable,true);assert.equal(d.timeline.counts.turns,0);assert.deepEqual(d.timeline.nodes,[]);assert.deepEqual(d.timeline.requests,[]);assert(!JSON.stringify(d).includes('Authored fixture question'));
 assert.equal(calls.filter(c=>c.method==='observation.list').length,2);assert.deepEqual(calls.filter(c=>c.method==='observation.payload').map(c=>c.params.eventId),['r3']);assert.deepEqual(calls.map(c=>c.method).filter(m=>!['session.list','workspace.list','observation.list','observation.payload'].includes(m)),[]);
});
test('Insights omits archived sessions and never borrows an older available context',async()=>{
 for(const descriptor of [{state:'expired'}, {...retained,bytes:-1},{...retained,bytes:1024*1024+1},{...retained,sha256:'bad'}]){
  const {reader,calls}=fixture({rows:[{sessionId:'a'},{sessionId:'archived'}],workspace:{archivedSessionIds:['archived']},entries:[request(1,{payload:retained}),end(2,'r1'),request(3,{payload:descriptor}),end(4,'r3')]});await reader.load();assert.equal(reader.state.coverage.sessions,1);assert.equal(reader.state.details.get('a').currentAvailable,false);assert.equal(reader.state.details.get('a').summary.cost.fixture.model.peak.uncached,200);assert.equal(calls.filter(c=>c.method==='observation.payload').length,0);
 }
 const {reader}=fixture({body:JSON.stringify({unsupported:'provider body'})});await reader.load();assert.equal(reader.state.details.get('a').currentAvailable,false);assert.match(reader.state.details.get('a').bodyReason,/projected/);
});
test('Insights reports malformed cursors, duplicated identities and wrong-session pages per row',async()=>{
 for(const alter of [p=>({...p,records:p.records.map(r=>({...r,sessionId:'wrong'}))}),p=>({...p,records:[p.records[0],p.records[0]]}),p=>({...p,hasMore:true,nextBeforeSeq:500}),p=>({...p,latestSeq:null})]){
  const {reader,calls}=fixture({alter});await reader.load();assert.equal(reader.state.coverage.failed,1);assert.deepEqual(reader.state.snapshot.byId.a.projectionValues,{});assert.equal(calls.filter(c=>c.method==='observation.payload').length,0);
 }
});
test('Insights coalesces reads, revokes changed scope and stops before any later page/body',async()=>{
 let release;const wait=new Promise(resolve=>release=resolve);let state=current(),calls=[];const reader=new DshInsightsReader({current:()=>state,rpc:async(method)=>{calls.push(method);if(method==='workspace.list')return {items:[]};if(method==='session.list')return {items:[{sessionId:'a'}]};await wait;return {records:[request(1,{payload:retained})],scanned:1,earliestSeq:1,latestSeq:1,hasMore:true,nextBeforeSeq:1};}});
 const first=reader.load();assert.equal(first,reader.load());await new Promise(resolve=>setImmediate(resolve));state={...state,epoch:2};release();assert.equal(await first,false);assert.equal(reader.state.snapshot,null);assert.deepEqual(calls,['session.list','workspace.list','observation.list']);
 state={...state,readOnly:true};assert.equal(await reader.load(),false);assert.equal(calls.length,3);
 const b=fixture();b.reader.close();assert.equal(await b.reader.load(),true);
});
test('Insights enforces the corpus and per-session budgets with two concurrent workers',async()=>{
 const entries=Array.from({length:12},(_,i)=>record(i+1,'tool/end'));const {reader,calls}=fixture({rows:[{sessionId:'a'},{sessionId:'b'},{sessionId:'c'}],entries,limits:{maxRecords:13,maxSessionRecords:10}});await reader.load();assert.equal(reader.state.coverage.scanned,13);assert.equal(reader.state.coverage.partial,3);assert(calls.filter(c=>c.method==='observation.list').every(c=>c.params.limit<=10));assert.equal(reader.state.coverage.read,3);
});
test('Insights does not retain context messages in corpus projections',()=>{
 const value=insightProjection([request(1,{payload:retained}),end(2,'r1')],payload);assert(value.currentAvailable);assert(!JSON.stringify(value).includes('Public fixture instructions.'));assert.deepEqual(value.timeline.archive,[]);
});

test('Insights empty sessions have no available body or invented zero context ring',async()=>{
 const projected=insightProjection([],null);assert.equal(projected.currentAvailable,false);
 const {reader,calls}=fixture({entries:[]});assert.equal(await reader.load(),true);assert.equal(reader.state.coverage.bodies,0);assert.equal(reader.state.coverage.bodyUnavailable,1);assert.equal(reader.state.details.get('a').currentAvailable,false);assert.equal(calls.filter(c=>c.method==='observation.payload').length,0);
});
