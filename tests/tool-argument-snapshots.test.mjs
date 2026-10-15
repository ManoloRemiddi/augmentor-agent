// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {pathToFileURL} from 'node:url';import {resolve} from 'node:path';
import {setTimeout as delay} from 'node:timers/promises';
const {projectDsh}=await import(process.env.AUGMENTOR_DSH_PROJECTION_OVERRIDE?pathToFileURL(resolve(process.env.AUGMENTOR_DSH_PROJECTION_OVERRIDE)):new URL('../apps/harness/dsh-pi-projection.mjs',import.meta.url));
const {ToolArgumentSnapshots}=await import(pathToFileURL(resolve(process.env.AUGMENTOR_PI_TEST_ROOT??'.','dist/runtime/src/tool-argument-snapshots.js')));
const update=(type,args,{index=0,id='call',name='read'}={})=>({type,contentIndex:index,partial:{content:Array.from({length:index+1},(_,i)=>i===index?{type:'toolCall',id,name,arguments:args,privateExtra:'never copied'}:{type:'text',text:'unrelated private content'})},toolCall:{type:'toolCall',id,name,arguments:args,privateExtra:'never copied'},delta:'untrusted raw provider update'});
const display=(seq,chunk,requestId='request',turnId='turn')=>({seq,type:'assistant/chunk',turnId,data:{requestId,chunk}});
const state=events=>({sessionId:'s',sessions:[{sessionId:'s',running:true}],events,records:[{kind:'model/request',id:'request',turnId:'turn',time:1,data:{}}]});

test('a quiet SDK burst emits its latest partial after the sample interval with the original request scope',async()=>{
 let clock=0;const emitted=[],capture=new ToolArgumentSnapshots(()=>clock,(chunk,requestId)=>emitted.push({chunk,requestId}));capture.begin();
 const first=capture.update(update('toolcall_start',{path:'first'}),'request-one');clock=10;assert.equal(capture.update(update('toolcall_delta',{path:'second'}),'request-one'),undefined);clock=20;assert.equal(capture.update(update('toolcall_delta',{path:'latest 😀'}),'request-one'),undefined);
 clock=60;await delay(90);assert.equal(emitted.length,1);assert.equal(emitted[0].requestId,'request-one');assert.equal(emitted[0].chunk.complete,false);assert.equal(emitted[0].chunk.argsPatch.baseRevision,first.revision);
 assert.equal(projectDsh(state([display(1,first),display(2,emitted[0].chunk)])).trajectory.partial.blocks[0].argsRaw,JSON.stringify({path:'latest 😀'}));capture.end();
});

test('quiet parallel partials retain their own request identities and bounded per-call sampling',async()=>{
 let clock=0;const emitted=[],capture=new ToolArgumentSnapshots(()=>clock,(chunk,requestId)=>emitted.push({chunk,requestId}));capture.begin();
 capture.update(update('toolcall_start',{path:'one'}),'request-one');capture.update(update('toolcall_start',{path:'two'},{index:1,id:'two'}),'request-two');clock=10;
 capture.update(update('toolcall_delta',{path:'new one'}),'request-one');capture.update(update('toolcall_delta',{path:'new two'},{index:1,id:'two'}),'request-two');clock=60;await delay(90);
 assert.deepEqual(emitted.map(row=>[row.chunk.index,row.requestId,row.chunk.revision]),[[0,'request-one',2],[1,'request-two',2]]);capture.end();
});

test('ending or replacing a SDK message and a final update retire queued partials without late display',async()=>{
 let clock=0;const emitted=[],capture=new ToolArgumentSnapshots(()=>clock,chunk=>emitted.push(chunk));capture.begin();capture.update(update('toolcall_start',{}));clock=10;capture.update(update('toolcall_delta',{path:'stopped'}));capture.end();clock=60;await delay(90);assert.deepEqual(emitted,[]);
 capture.begin();capture.update(update('toolcall_start',{}));clock=70;capture.update(update('toolcall_delta',{path:'replaced'}));capture.begin();clock=130;await delay(90);assert.deepEqual(emitted,[]);
 capture.update(update('toolcall_start',{}));clock=140;capture.update(update('toolcall_delta',{path:'pending'}));const final=capture.update(update('toolcall_end',{path:'final'}));assert.equal(final.complete,true);clock=200;await delay(90);assert.deepEqual(emitted,[]);capture.end();
});

test('public SDK snapshots sample growing objects, flush final updates and encode exact Unicode changes without copying unrelated content',()=>{
 let clock=0;const capture=new ToolArgumentSnapshots(()=>clock);assert.equal(capture.update(update('toolcall_start',{})),undefined);capture.begin();
 const first=capture.update(update('toolcall_start',{}));clock=10;assert.equal(capture.update(update('toolcall_delta',{path:'early'})),undefined);clock=60;const growing=capture.update(update('toolcall_delta',{path:'f😀.txt'}));clock=61;const final=capture.update(update('toolcall_end',{path:'f😀.txt',line:2}));
 assert.equal(growing.argsPatch.units,'utf16-code-units');assert(!JSON.stringify([first,growing,final]).includes('privateExtra'));assert(!JSON.stringify([first,growing,final]).includes('untrusted raw provider update'));
 const trajectory=projectDsh(state([display(1,first),display(2,growing),display(3,final)])).trajectory;assert.equal(trajectory.partial.blocks[0].argsRaw,JSON.stringify({path:'f😀.txt',line:2}));assert.equal(trajectory.runningCalls.length,0,'streamed proposals are not dispatched tools');capture.end();assert.equal(capture.update(update('toolcall_delta',{path:'after'})),undefined);
});
test('missing bases, foreign request identities, changed calls and malformed patches stay unavailable instead of borrowing an old argument object',()=>{
 const base={type:'tool-call-snapshot',captureId:'capture-one',revision:1,index:0,callId:'call',name:'read',boundary:'public-sdk-partial-tool-call-arguments',argsRaw:'{"path":"first"}'};
 const patch={...base,revision:2,argsRaw:undefined,argsPatch:{units:'utf16-code-units',baseRevision:1,prefix:9,remove:5,insert:'next'}};
 assert.equal(projectDsh(state([display(1,patch)])).trajectory.partial.blocks[0].kind,'other');
 const foreign=projectDsh(state([display(1,base),display(2,patch,'other')])).trajectory;assert(foreign.eventNodes.some(n=>n.interrupted));assert.equal(foreign.partial.blocks[0].kind,'other');assert.equal(foreign.partial.timing,undefined);
 assert.equal(projectDsh(state([display(1,base),display(2,{...patch,callId:'other'})])).trajectory.partial.blocks[0].kind,'other');
 assert.equal(projectDsh(state([display(1,base),display(2,{...patch,argsPatch:{...patch.argsPatch,remove:1000000}})])).trajectory.partial.blocks[0].kind,'other');
 const unknown=projectDsh(state([{seq:1,type:'assistant/chunk',turnId:'turn',data:{chunk:base}}])).trajectory;assert.equal(unknown.partial.timing,undefined);
});
test('sampling preserves interleaved tool order and normal completion replaces all provisional blocks without granting dispatch authority',()=>{
 let clock=0;const capture=new ToolArgumentSnapshots(()=>clock);capture.begin();const one=capture.update(update('toolcall_start',{path:'one'}));clock=60;const two=capture.update(update('toolcall_start',{path:'two'},{index:1,id:'two'}));clock=120;const next=capture.update(update('toolcall_delta',{path:'new one'}));const events=[display(1,one),display(2,two),display(3,next)];
 const live=projectDsh(state(events)).trajectory;assert.deepEqual(live.partial.blocks.map(b=>b.sdkCallId),['call','two']);assert.deepEqual(live.partial.blocks.map(b=>JSON.parse(b.argsRaw).path),['new one','two']);assert.equal(live.runningCalls.length,0);
 const final={seq:4,type:'assistant/message',turnId:'turn',data:{requestId:'request',message:{content:[{type:'toolCall',id:'call',name:'read',arguments:{path:'new one'}},{type:'toolCall',id:'two',name:'read',arguments:{path:'two'}}],stopReason:'toolUse'}}};
 const completed=projectDsh(state([...events,final])).trajectory;assert.equal(completed.partial,null);assert.equal(completed.eventNodes.length,1);assert.equal(completed.eventNodes[0].blocks.length,2);assert.equal(completed.runningCalls.length,0);
 const stopped=projectDsh({...state([...events,{seq:4,type:'turn/end',turnId:'turn',data:{reason:{kind:'aborted'}}}]),sessions:[{sessionId:'s',running:false}]}).trajectory;assert.equal(stopped.partial,null);assert.equal(stopped.eventNodes[0].interrupted,true);assert.equal(stopped.eventNodes[0].time,null);assert.equal(stopped.runningCalls.length,0);
});
test('oversized, cyclic and excessive live captures expose a gap and reset safely for the next SDK message',async()=>{
 let clock=0;const capture=new ToolArgumentSnapshots(()=>clock);capture.begin();assert.equal(capture.update(update('toolcall_start',{text:'x'.repeat(512*1024)})).argsRaw,null);
 const cycle={};cycle.self=cycle;clock=60;assert.equal(capture.update(update('toolcall_delta',cycle)).argsRaw,null);
 capture.begin();for(let i=0;i<128;i++){clock+=60;assert(capture.update(update('toolcall_start',{path:'small'},{index:i,id:'call'+i})));}const overflow=capture.update(update('toolcall_start',{path:'extra'},{index:128,id:'extra'}));assert.equal(overflow.argsRaw,null);clock+=60;assert.equal(capture.update(update('toolcall_delta',{path:'after cap'})),undefined);
 capture.begin();let bytes=0,gap;for(let i=0;i<12;i++){clock+=60;const row=capture.update(update(i?'toolcall_delta':'toolcall_start',{text:(i%2?'b':'a').repeat(450000)}));if(!row)break;if(row.argsRaw===null){gap=row;break;}bytes+=Buffer.byteLength(JSON.stringify(row));}assert(gap);assert(bytes<=2*1024*1024);assert.match(gap.reason,/budget/);capture.begin();assert.equal(capture.update(update('toolcall_start',{path:'recovered'})).argsRaw,'{"path":"recovered"}');
 const emitted=[],bounded=new ToolArgumentSnapshots(()=>clock,chunk=>emitted.push(chunk));bounded.begin();for(let i=0;i<128;i++)bounded.update(update('toolcall_start',{path:'small'},{index:i,id:'bounded'+i}));clock+=10;bounded.update(update('toolcall_delta',{path:'pending'},{id:'bounded0'}));assert.equal(bounded.update(update('toolcall_start',{}, {index:128,id:'overflow'})).argsRaw,null);clock+=60;await delay(90);assert.deepEqual(emitted,[],'exhaustion retires queued partials');bounded.end();
});
test('a lost intermediate SDK snapshot cannot make a later patch fabricate valid but different arguments',()=>{
 let clock=0;const capture=new ToolArgumentSnapshots(()=>clock);capture.begin();const first=capture.update(update('toolcall_start',{path:'aaaa'}));clock=60;capture.update(update('toolcall_delta',{path:'bbbb'}));clock=120;const last=capture.update(update('toolcall_delta',{path:'bcbb'}));
 const value=projectDsh(state([display(1,first),display(3,last)])).trajectory.partial.blocks[0];assert.equal(value.kind,'other','a missing patch base must show a gap, never the fabricated {path:"acaa"}');
 capture.begin();clock=180;const fresh=capture.update(update('toolcall_start',{path:'fresh'}));const unknown=chunk=>({type:'assistant/chunk',turnId:'turn',data:{chunk}});const unlinked=projectDsh(state([{seq:1,...unknown(first)},{seq:2,...unknown(fresh)}])).trajectory;assert.equal(unlinked.partial.blocks[0].argsRaw,'{"path":"fresh"}');assert.equal(unlinked.partial.timing,undefined);assert.equal(unlinked.runningCalls.length,0);assert.equal(unlinked.eventNodes[0].interrupted,true,'a new capture never extends an earlier unlinked message');
});
test('reused SDK call IDs remain distinct across requests and turns, preserve raw IDs, and never borrow arguments, schemas or timings',()=>{
 for(const sameTurn of [false,true]){
  const t1='first-turn',t2=sameTurn?t1:'second-turn',events=[{seq:1,type:'assistant/message',turnId:t1,data:{requestId:'first',message:{content:[{type:'toolCall',id:'reused',name:'read',arguments:{path:'first'}}],stopReason:'aborted'}}},{seq:2,type:'assistant/message',turnId:t2,data:{requestId:'second',message:{content:[{type:'toolCall',id:'reused',name:'read',arguments:{path:'second'}}],stopReason:'toolUse'}}},{seq:3,type:'tool/call',turnId:t2,data:{name:'read',toolCallId:'reused'}},{seq:4,type:'tool/result',turnId:t2,data:{name:'read',toolCallId:'reused',result:{content:[{type:'text',text:'second result'}]}}}],records=[{kind:'model/request',id:'first',turnId:t1,time:1,data:{}},{kind:'model/request',id:'second',turnId:t2,time:2,data:{}},{kind:'tool/start',requestId:'first',turnId:t1,time:10,data:{toolCallId:'reused',name:'read'}},{kind:'tool/start',requestId:'second',turnId:t2,time:20,data:{toolCallId:'reused',name:'read'}},{kind:'tool/end',requestId:'second',turnId:t2,time:30,data:{toolCallId:'reused'}}];
  const original=JSON.stringify(events),value=projectDsh({sessionId:'s',sessions:[{sessionId:'s',running:false}],events,records,payloads:{second:{tools:[{function:{name:'read',description:'second schema'}}]}}}),messages=value.trajectory.eventNodes.filter(n=>n.kind==='assistant'),result=value.trajectory.eventNodes.find(n=>n.kind==='tool-result');
  assert.notEqual(messages[0].blocks[0].callId,messages[1].blocks[0].callId);assert.equal(messages[1].blocks[0].sdkCallId,'reused');assert.equal(result.callId,messages[1].blocks[0].callId);assert.equal(result.callTime,20);assert.equal(value.trajectory.callSchemas.get(result.callId).description,'second schema');assert.equal(value.trajectory.callSchemas.has(messages[0].blocks[0].callId),false);
  const chat=value.chat.nodes.values().find(n=>n.kind==='pi-tool');assert.equal(chat.data.call.arguments.path,'second');assert.equal(chat.data.result.content[0].text,'second result');assert.equal(JSON.stringify(events),original,'presentation IDs never alter recorded SDK events');
 }
 const unknownEvents=[{seq:1,type:'assistant/message',turnId:'same',data:{captureId:'capture-a',message:{content:[{type:'toolCall',id:'same',name:'read',arguments:{path:'a'}}]}}},{seq:2,type:'assistant/message',turnId:'same',data:{captureId:'capture-b',message:{content:[{type:'toolCall',id:'same',name:'read',arguments:{path:'b'}}]}}},{seq:3,type:'tool/call',turnId:'same',data:{captureId:'capture-b',toolCallId:'same',name:'read'}},{seq:4,type:'tool/result',turnId:'same',data:{captureId:'capture-b',toolCallId:'same',name:'read',result:{content:[]}}}];const unknown=projectDsh({sessionId:'s',sessions:[{sessionId:'s',running:false}],events:unknownEvents,records:[]}).trajectory;assert.notEqual(unknown.eventNodes[0].blocks[0].callId,unknown.eventNodes[1].blocks[0].callId);assert.equal(unknown.eventNodes[2].callId,unknown.eventNodes[1].blocks[0].callId);assert.equal(unknown.requests.length,0);assert.equal(unknown.eventNodes[2].callTime,null);
});
test('nested execution-start arguments share the SDK message capture budget, omit unrelated event fields and reset for the next message',()=>{
 const capture=new ToolArgumentSnapshots();capture.begin();capture.end();
 const exact=capture.captureExecutionArguments({path:'authored 日本語.txt'});assert.equal(exact.argsRaw,'{"path":"authored 日本語.txt"}');assert.equal(exact.argsBoundary,'public-sdk-tool-execution-start-before-validation');
 const cycle={};cycle.self=cycle;assert.equal(capture.captureExecutionArguments(cycle).argsRaw,null);assert.equal(capture.captureExecutionArguments(undefined).argsRaw,null);assert.equal(capture.captureExecutionArguments({text:'x'.repeat(512*1024)}).argsRaw,null);
 capture.begin();assert.equal(typeof capture.update(update('toolcall_start',{text:'x'.repeat(500000)})).argsRaw,'string');capture.end();for(let i=0;i<3;i++)assert.equal(typeof capture.captureExecutionArguments({text:'x'.repeat(500000)}).argsRaw,'string');assert.equal(capture.captureExecutionArguments({text:'x'.repeat(100000)}).argsRaw,null);
 capture.begin();for(let i=0;i<256;i++)assert.equal(capture.captureExecutionArguments({i}).argsRaw,JSON.stringify({i}));assert.equal(capture.captureExecutionArguments({extra:true}).argsRaw,null);
 capture.begin();for(let i=0;i<2;i++)assert.equal(typeof capture.captureExecutionArguments({text:'\\'.repeat(200000)}).argsRaw,'string');assert(capture.captureExecutionArguments({text:'\\'.repeat(200000)}).argsRaw===null,'escaped stored snapshots, not only their raw JSON values, must respect the capture budget');
 capture.begin();assert.equal(capture.captureExecutionArguments({recovered:true}).argsRaw,'{"recovered":true}');
});
