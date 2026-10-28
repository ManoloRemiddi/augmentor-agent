// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {projectDsh} from '../apps/harness/dsh-pi-projection.mjs';
import {projectDshContext} from '../apps/harness/dsh-context-projection.mjs';
import {DshPiController} from '../apps/harness/dsh-pi-controller.mjs';
const boundary='public-sdk-tool-execution-start-before-validation';
function fixture({requestId='request',turnId='turn',offset=0,legacy=false}={}){
 const identity=legacy?{}:{requestId,captureId:'capture-'+requestId};
 const event=(seq,type,data)=>({seq:seq+offset,type,turnId,data:{...identity,...data}});
 const start=(seq,id,name,parent,args)=>event(seq,'tool/call',{toolCallId:id,name,...(parent?{parentToolCallId:parent,argsRaw:JSON.stringify(args),argsBoundary:boundary}:{})});
 const result=(seq,id,name,parent,text,isError=false)=>event(seq,'tool/result',{toolCallId:id,name,...(parent?{parentToolCallId:parent}:{}),isError,result:{content:[{type:'text',text}]}});
 const events=[event(1,'user/message',{content:[{type:'text',text:'Authored nested tool fixture'}]}),event(2,'assistant/message',{message:{content:[{type:'toolCall',id:'root',name:'outer',arguments:{path:requestId+'.txt'}}],stopReason:'toolUse'}}),start(3,'root','outer'),start(4,'root/1','inner','root',{path:requestId+'.txt'}),start(5,'root/1/1','read','root/1',{path:requestId+'.txt'}),result(6,'root/1/1','read','root/1','Exact nested read: '+requestId),start(7,'root/1/2','wait','root/1',{label:requestId})];
 const records=[{kind:'model/request',id:requestId,turnId,time:100+offset,data:{}}];
 for(const e of events.filter(e=>e.type==='tool/call'||e.type==='tool/result'))records.push({kind:e.type==='tool/call'?'tool/start':'tool/end',requestId,turnId,time:100+e.seq,data:{toolCallId:e.data.toolCallId,name:e.data.name,...(e.data.parentToolCallId?{parentToolCallId:e.data.parentToolCallId}:{})}});
 const settle=[result(8,'root/1/2','wait','root/1','Authored cancelled wait',true),result(9,'root/1','inner','root','Authored inner failed',true),result(10,'root','outer',undefined,'Authored outer failed',true),event(11,'turn/end',{reason:{kind:'aborted'}})];
 const completedRecords=settle.filter(e=>e.type==='tool/result').map(e=>({kind:'tool/end',requestId,turnId,time:100+e.seq,data:{toolCallId:e.data.toolCallId,name:e.data.name,...(e.data.parentToolCallId?{parentToolCallId:e.data.parentToolCallId}:{})}}));
 const state={sessionId:'s',sessions:[{sessionId:'s',running:true}],events,records,payloads:{[requestId]:{tools:['outer','inner','read','wait'].map(name=>({function:{name,description:'Recorded '+requestId+' '+name}}))}}};
 return {state,settle,completedRecords,start,result,event};
}
test('original running root seats carry exact nested running and settled children, without additional root rows or source mutation',()=>{
 const {state}=fixture(),original=JSON.stringify(state),view=projectDsh(state).trajectory;
 assert.equal(view.runningCalls.length,1);
 const inner=view.runningCalls[0].subCalls[0];assert(inner,'a real nested start belongs under its observed parent');
 assert.equal(inner.name,'inner');assert.equal(inner.argsRaw,'{"path":"request.txt"}');assert.equal(inner.time,104);
 const [read,wait]=inner.subCalls;assert.equal(read.kind,'tool-result');assert.equal(read.call.name,'read');assert.equal(read.call.argsRaw,'{"path":"request.txt"}');assert.equal(read.content[0].text,'Exact nested read: request');assert.equal(read.callTime,105);assert.equal(read.time,106);
 assert.equal(wait.phase,'start');assert.equal(wait.name,'wait');assert.equal(wait.argsRaw,'{"label":"request"}');assert.equal(wait.time,107);
 assert.equal(view.eventNodes.filter(n=>n.kind==='tool-result').length,0,'attached nested results are not duplicate root rows');
 assert.equal(view.callSchemas.get(read.callId).description,'Recorded request read');assert.equal(JSON.stringify(state),original);
 const chat=projectDsh(state).chat.nodes.values().find(n=>n.kind==='pi-tool'&&n.data.name==='read');assert.equal(chat.data.call.arguments.path,'request.txt');assert.equal(chat.data.result.content[0].text,'Exact nested read: request');assert.equal(chat.data.status,'finished');
});
test('nested failed and completed receipts survive Stop and cold projection with their exact parent and independent outcomes',()=>{
 const f=fixture(),state={...f.state,sessions:[{sessionId:'s',running:false}],events:[...f.state.events,...f.settle],records:[...f.state.records,...f.completedRecords]},view=projectDsh(state).trajectory;
 assert.equal(view.runningCalls.length,0);assert.equal(view.eventNodes.filter(n=>n.kind==='tool-result').length,1);
 const root=view.eventNodes.find(n=>n.kind==='tool-result'),inner=root.subCalls[0],[read,wait]=inner.subCalls;
 assert.equal(root.call.name,'outer');assert.equal(root.isError,true);assert.equal(inner.call.name,'inner');assert.equal(inner.isError,true);assert.equal(read.isError,false);assert.equal(wait.isError,true);assert.equal(wait.content[0].text,'Authored cancelled wait');assert.equal(wait.time,108);
 assert.deepEqual(projectDsh(JSON.parse(JSON.stringify(state))).trajectory.eventNodes,view.eventNodes);
});
test('legal SDK nested identifiers longer than the provider root retain their explicit parent and exact observed clocks',()=>{
 const f=fixture(),root='r'.repeat(256),replace=id=>id?.startsWith('root')?root+id.slice(4):id;
 const events=f.state.events.map(e=>({...e,data:{...e.data,...(e.data.toolCallId?{toolCallId:replace(e.data.toolCallId)}:{}),...(e.data.parentToolCallId?{parentToolCallId:replace(e.data.parentToolCallId)}:{}),...(e.data.message?{message:{...e.data.message,content:e.data.message.content.map(p=>p.type==='toolCall'?{...p,id:replace(p.id)}:p)}}:{})}}));
 const records=f.state.records.map(r=>({...r,data:{...r.data,...(r.data.toolCallId?{toolCallId:replace(r.data.toolCallId)}:{}),...(r.data.parentToolCallId?{parentToolCallId:replace(r.data.parentToolCallId)}:{})}}));
 const inner=projectDsh({...f.state,events,records}).trajectory.runningCalls[0].subCalls[0];assert.equal(inner.sdkCallId.length,258);assert.equal(inner.time,104);assert.equal(inner.subCalls[0].sdkCallId.length,260);assert.equal(inner.subCalls[0].callTime,105);assert.equal(inner.subCalls[0].time,106);
});
test('repeated nested SDK IDs in a later request keep their own arguments, result, schema and clocks',()=>{
 const a=fixture({requestId:'first'}),b=fixture({requestId:'second',turnId:'second-turn',offset:20});
 const state={...b.state,events:[...a.state.events,...a.settle,...b.state.events],records:[...a.state.records,...a.completedRecords,...b.state.records],payloads:{...a.state.payloads,...b.state.payloads}};
 const view=projectDsh(state).trajectory,old=view.eventNodes.find(n=>n.kind==='tool-result'),current=view.runningCalls[0],oldRead=old.subCalls[0].subCalls[0],newRead=current.subCalls[0].subCalls[0];
 assert.notEqual(oldRead.callId,newRead.callId);assert.equal(oldRead.sdkCallId,newRead.sdkCallId);assert.equal(newRead.call.argsRaw,'{"path":"second.txt"}');assert.equal(newRead.content[0].text,'Exact nested read: second');assert.equal(newRead.callTime,125);assert.equal(view.callSchemas.get(newRead.callId).description,'Recorded second read');
 const operations=projectDshContext(state).timeline.fileOps;assert.deepEqual(operations.map(x=>({path:x.path,time:x.time,err:x.err})),[{path:'first.txt',time:106,err:false},{path:'second.txt',time:126,err:false}]);assert.notEqual(operations[0].seq,operations[1].seq);
});
test('Context File Activity never borrows later reused root proposals or marks a proposal as an executed file operation',()=>{
 const events=[{seq:1,type:'assistant/message',turnId:'t',data:{requestId:'a',message:{content:[{type:'toolCall',id:'same',name:'read',arguments:{path:'first.txt'}}]}}},{seq:2,type:'tool/call',turnId:'t',data:{requestId:'a',toolCallId:'same',name:'read'}},{seq:3,type:'tool/result',turnId:'t',data:{requestId:'a',toolCallId:'same',name:'read',isError:false,result:{content:[]}}},{seq:4,type:'assistant/message',turnId:'t',data:{requestId:'b',message:{content:[{type:'toolCall',id:'same',name:'read',arguments:{path:'later.txt'}}]}}}];
 const value=projectDshContext({events,records:[]}).timeline.fileOps;assert.equal(value.length,1);assert.equal(value[0].path,'first.txt');assert.equal(value[0].time,undefined);
 assert.equal(projectDshContext({events:[events[0]],records:[]}).timeline.fileOps.length,0);
 const late=projectDshContext({events:[events[0],events[1],events[3],events[2]],records:[]}).timeline.fileOps;assert.equal(late.length,1);assert.equal(late[0].path,'first.txt','an existing start owns its arguments even after a later proposal');
});
test('missing legacy arguments and foreign or absent parents retain results without invented payloads, hierarchy or timing',()=>{
 const f=fixture({legacy:true}),state={...f.state,sessions:[{sessionId:'s',running:false}],events:[...f.state.events,...f.settle].map(e=>e.data.parentToolCallId?{...e,data:{...e.data,argsRaw:undefined,argsBoundary:undefined}}:e),records:[]};
 const root=projectDsh(state).trajectory.eventNodes.find(n=>n.kind==='tool-result');assert(root.subCalls[0]);assert.equal(root.subCalls[0].call,null);assert.equal(root.subCalls[0].subCalls[0].call,null);assert.equal(root.subCalls[0].subCalls[0].content[0].text,'Exact nested read: request');assert.equal(root.subCalls[0].subCalls[0].callTime,null);
 const foreign=fixture(),events=foreign.state.events.map(e=>e.seq===4?{...e,data:{...e.data,requestId:'foreign'}}:e);
 const view=projectDsh({...foreign.state,events}).trajectory;assert.equal(view.runningCalls[0].subCalls.length,0,'a parent from another request cannot own this child');
 const orphan=projectDsh({...foreign.state,sessions:[{sessionId:'s',running:false}],events:foreign.state.events.filter(e=>e.seq>=5)}).trajectory;
 assert.equal(orphan.eventNodes.filter(n=>n.kind==='tool-result').length,1);assert.equal(orphan.eventNodes.find(n=>n.kind==='tool-result').call.argsRaw,'{"path":"request.txt"}');
});
test('acknowledged Stop reads and merges canonical receipts before idle metadata, preserving late live events without replay',async()=>{
 const f=fixture(),events=[...f.state.events,...f.settle],records=[...f.state.records,...f.completedRecords].map((r,i)=>({...r,id:r.id??'record-'+i})),calls=[];let finishHistory;
 const waiting=new Promise(resolve=>finishHistory=resolve),controller=new DshPiController('authored-fixture',async(_url,options)=>{
  const {method,params}=JSON.parse(options.body);calls.push({method,params});
  const result=method==='session.history'?await waiting:method==='observation.list'?{records,hasMore:false}:method==='session.list'?{items:[{sessionId:'s',running:false}]}:method==='workspace.list'?{items:[],archivedSessionIds:[]}:{};
  return {ok:true,json:async()=>({result})};
 });
 controller.update({...f.state,records:records.slice(0,f.state.records.length),phase:'ready'});const stopping=controller.stop();await Promise.resolve();
 const late={seq:100,type:'runtime/warning',turnId:'turn',data:{message:'Authored later diagnostic'}};controller.update({events:[...controller.state.events,late]});finishHistory({events:events.map(event=>({event})),hasMore:false});await stopping;
 const root=projectDsh(controller.state).trajectory.eventNodes.find(n=>n.kind==='tool-result');assert(root?.subCalls[0],'idle metadata must not discard terminal child receipts');assert.equal(root.subCalls[0].subCalls[0].content[0].text,'Exact nested read: request');assert.equal(root.subCalls[0].subCalls[1].isError,true);
 assert(controller.state.events.some(e=>e.seq===100));assert.deepEqual(controller.state.events.map(e=>e.seq),[...events.map(e=>e.seq),100]);assert.equal(controller.state.records.length,records.length);
 assert.equal(controller.state.familyRevision,1,'canonical receipts notify retained family readers');
 assert(calls.some(c=>c.method==='session.history'&&c.params.sessionId==='s'));assert(calls.every(c=>['session.cancel','session.history','observation.list','session.list','workspace.list'].includes(c.method)),'receipt reads never submit or replay work');
});
test('failed receipt reads report an acknowledged Stop and retain unknown details without retrying cancellation or work',async()=>{
 const f=fixture(),calls=[],controller=new DshPiController('authored-fixture',async(_url,options)=>{const {method}=JSON.parse(options.body);calls.push(method);if(method==='session.history')throw Error('Authored unavailable history');const result=method==='observation.list'?{records:[],hasMore:false}:method==='session.list'?{items:[{sessionId:'s',running:false}]}:method==='workspace.list'?{items:[],archivedSessionIds:[]}:{};return {ok:true,json:async()=>({result})};});
 controller.update({...f.state,phase:'ready'});await assert.rejects(controller.stop(),/Stop was acknowledged.*saved details/);assert.deepEqual(controller.state.events,f.state.events);assert.equal(controller.state.sessions[0].running,false);assert.equal(calls.filter(x=>x==='session.cancel').length,1);assert(calls.every(x=>['session.cancel','session.history','observation.list','session.list','workspace.list'].includes(x)));
});
test('a Stop receipt read retiring into a foreign or readonly selection never changes that new conversation',async()=>{
 const f=fixture();let finishHistory;const waiting=new Promise(resolve=>finishHistory=resolve);
 const controller=new DshPiController('authored-fixture',async(_url,options)=>{const {method}=JSON.parse(options.body);const result=method==='session.history'?await waiting:method==='observation.list'?{records:[],hasMore:false}:method==='session.list'?{items:[]}:{};return {ok:true,json:async()=>({result})};});
 controller.update({...f.state,phase:'ready'});const stopping=controller.stop();await Promise.resolve();controller.epoch++;controller.update({sessionId:'foreign',readOnly:true,events:[],records:[],sessions:[{sessionId:'foreign',running:false}]});
 finishHistory({events:[...f.state.events,...f.settle].map(event=>({event})),hasMore:false});await stopping;assert.equal(controller.state.sessionId,'foreign');assert.equal(controller.state.readOnly,true);assert.deepEqual(controller.state.events,[]);assert.deepEqual(controller.state.sessions,[{sessionId:'foreign',running:false}]);
});
