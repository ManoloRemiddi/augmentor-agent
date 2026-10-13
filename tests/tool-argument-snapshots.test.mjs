// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {pathToFileURL} from 'node:url';import {resolve} from 'node:path';
import {projectDsh} from '../apps/harness/dsh-pi-projection.mjs';
const {ToolArgumentSnapshots}=await import(pathToFileURL(resolve(process.env.AUGMENTOR_PI_TEST_ROOT??'.','dist/runtime/src/tool-argument-snapshots.js')));
const update=(type,args,{index=0,id='call',name='read'}={})=>({type,contentIndex:index,partial:{content:Array.from({length:index+1},(_,i)=>i===index?{type:'toolCall',id,name,arguments:args,privateExtra:'never copied'}:{type:'text',text:'unrelated private content'})},toolCall:{type:'toolCall',id,name,arguments:args,privateExtra:'never copied'},delta:'untrusted raw provider update'});
const display=(seq,chunk,requestId='request',turnId='turn')=>({seq,type:'assistant/chunk',turnId,data:{requestId,chunk}});
const state=events=>({sessionId:'s',sessions:[{sessionId:'s',running:true}],events,records:[{kind:'model/request',id:'request',turnId:'turn',time:1,data:{}}]});

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
 const live=projectDsh(state(events)).trajectory;assert.deepEqual(live.partial.blocks.map(b=>b.callId),['call','two']);assert.deepEqual(live.partial.blocks.map(b=>JSON.parse(b.argsRaw).path),['new one','two']);assert.equal(live.runningCalls.length,0);
 const final={seq:4,type:'assistant/message',turnId:'turn',data:{requestId:'request',message:{content:[{type:'toolCall',id:'call',name:'read',arguments:{path:'new one'}},{type:'toolCall',id:'two',name:'read',arguments:{path:'two'}}],stopReason:'toolUse'}}};
 const completed=projectDsh(state([...events,final])).trajectory;assert.equal(completed.partial,null);assert.equal(completed.eventNodes.length,1);assert.equal(completed.eventNodes[0].blocks.length,2);assert.equal(completed.runningCalls.length,0);
 const stopped=projectDsh({...state([...events,{seq:4,type:'turn/end',turnId:'turn',data:{reason:{kind:'aborted'}}}]),sessions:[{sessionId:'s',running:false}]}).trajectory;assert.equal(stopped.partial,null);assert.equal(stopped.eventNodes[0].interrupted,true);assert.equal(stopped.eventNodes[0].time,null);assert.equal(stopped.runningCalls.length,0);
});
test('oversized, cyclic and excessive live captures expose a gap and reset safely for the next SDK message',()=>{
 let clock=0;const capture=new ToolArgumentSnapshots(()=>clock);capture.begin();assert.equal(capture.update(update('toolcall_start',{text:'x'.repeat(512*1024)})).argsRaw,null);
 const cycle={};cycle.self=cycle;clock=60;assert.equal(capture.update(update('toolcall_delta',cycle)).argsRaw,null);
 capture.begin();for(let i=0;i<128;i++){clock+=60;assert(capture.update(update('toolcall_start',{path:'small'},{index:i,id:'call'+i})));}const overflow=capture.update(update('toolcall_start',{path:'extra'},{index:128,id:'extra'}));assert.equal(overflow.argsRaw,null);clock+=60;assert.equal(capture.update(update('toolcall_delta',{path:'after cap'})),undefined);
 capture.begin();let bytes=0,gap;for(let i=0;i<12;i++){clock+=60;const row=capture.update(update(i?'toolcall_delta':'toolcall_start',{text:(i%2?'b':'a').repeat(450000)}));if(!row)break;if(row.argsRaw===null){gap=row;break;}bytes+=Buffer.byteLength(JSON.stringify(row));}assert(gap);assert(bytes<=2*1024*1024);assert.match(gap.reason,/budget/);capture.begin();assert.equal(capture.update(update('toolcall_start',{path:'recovered'})).argsRaw,'{"path":"recovered"}');
});
test('a lost intermediate SDK snapshot cannot make a later patch fabricate valid but different arguments',()=>{
 let clock=0;const capture=new ToolArgumentSnapshots(()=>clock);capture.begin();const first=capture.update(update('toolcall_start',{path:'aaaa'}));clock=60;capture.update(update('toolcall_delta',{path:'bbbb'}));clock=120;const last=capture.update(update('toolcall_delta',{path:'bcbb'}));
 const value=projectDsh(state([display(1,first),display(3,last)])).trajectory.partial.blocks[0];assert.equal(value.kind,'other','a missing patch base must show a gap, never the fabricated {path:"acaa"}');
 capture.begin();clock=180;const fresh=capture.update(update('toolcall_start',{path:'fresh'}));const unknown=chunk=>({type:'assistant/chunk',turnId:'turn',data:{chunk}});const unlinked=projectDsh(state([{seq:1,...unknown(first)},{seq:2,...unknown(fresh)}])).trajectory;assert.equal(unlinked.partial.blocks[0].argsRaw,'{"path":"fresh"}');assert.equal(unlinked.partial.timing,undefined);assert.equal(unlinked.runningCalls.length,0);assert.equal(unlinked.eventNodes[0].interrupted,true,'a new capture never extends an earlier unlinked message');
});
