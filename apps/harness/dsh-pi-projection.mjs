// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {projectChat} from './chat-projection.js';
import {trajectoryStream} from './dsh-trajectory-stream.mjs';
import {callScope,callViewId,toolOwnership,observedTool} from './dsh-call-identity.mjs';
import {attachToolChildren,retainedToolArguments} from './dsh-tool-tree.mjs';
const blocks=(content,scope)=>(content||[]).flatMap(p=>p.type==='text'?[{kind:'text',text:p.text||''}]:['thinking','reasoning'].includes(p.type)?[{kind:'reasoning',text:p.thinking??p.text??''}]:['toolCall','tool-call'].includes(p.type)?[{kind:'tool-call',callId:callViewId(scope,p.id??p.callId),sdkCallId:p.id??p.callId,name:p.name,argsRaw:JSON.stringify(p.arguments??p.args??{}),subCalls:[]}]:[]);
const usage=u=>u?{inputTokens:u.input,outputTokens:u.output,cacheReadTokens:u.cacheRead,cacheWriteTokens:u.cacheWrite}:undefined;
/** Pure projection into DSH presentation contracts. Missing timestamps remain absent. */
export function projectDsh(state){
  const current=state.sessions.find(x=>x.sessionId===state.sessionId),running=current?.running===true;
  const eventNodes=[],locations=new Map(),chatNodes=new Map(),navigation=[],ownership=toolOwnership(state.events);let turn=0,step=0;
  const turnIds=new Map(),times=new Map();
  for(const r of state.records){const key=r.turnId;if(key&&!turnIds.has(key))turnIds.set(key,turnIds.size+1);if(r.kind==='user/message'&&key)times.set(key,r.time);}
  for(const e of state.events){
    const d=e.data||{},t=turnIds.get(e.turnId)||turn||1,time=d.message?.timestamp??times.get(e.turnId)??null;
    let n;
    if(e.type==='user/message'){turn=t;step=0;n={kind:'user',seq:e.seq,time,turn,content:d.submittedContent??d.content??[],source:d.source};}
    if(e.type==='assistant/message'){
      step++;const request=d.requestId?state.records.find(r=>r.kind==='model/request'&&r.id===d.requestId):undefined;
      const end=request?state.records.find(r=>r.kind==='model/complete'&&r.requestId===request.id):undefined,first=request?state.records.find(r=>r.kind==='model/firstToken'&&r.requestId===request.id):undefined;
      // SDK message timestamps can mark creation rather than completion.
      // Use the matching observed generation boundary, never an older request.
      n={kind:'assistant',seq:e.seq,time:end?.time??null,turn:t,step,blocks:blocks(d.message?.content,callScope(d,e.turnId,e.seq)),usage:usage(d.message?.usage),...(request?{timing:{stepStartTime:request.time??null,firstTokenTime:first?.time??null,completedTime:end?.time??null}}:{}),...(['aborted','error','length'].includes(d.message?.stopReason)?{interrupted:true}:{})};
    }
    if(e.type==='tool/result'){
      const binding=ownership.get(e.seq),start=observedTool(state.records,'tool/start',e,binding),end=observedTool(state.records,'tool/end',e,binding);
      n={kind:'tool-result',seq:e.seq,time:end?.time??null,callTime:start?.time??null,turn:t,step,callId:binding.id,sdkCallId:d.toolCallId,name:d.name,content:d.result?.content||[],isError:d.isError,subCalls:[]};
    }
    if(n){eventNodes.push(n);locations.set(e.seq,{kind:'session'});}
  }
  const live=trajectoryStream(state,eventNodes,turnIds,ownership);
  const trajectoryNodes=attachToolChildren(state,eventNodes,live.runningCalls,ownership);
  for(const node of eventNodes)locations.set(node.seq,{kind:'session'});
  // The existing streaming projection removes overlaps with durable final messages.
  const visible=projectChat(state.events,{running,toolBindings:ownership});let ordinal=0,currentTurn=0;
  for(const item of visible){
    const key=item.seq?'event:'+item.seq:'tail:'+ordinal,anchorSeq=item.seq??state.events.at(-1)?.seq??0;
    let n;
    if(item.kind==='user'){
      currentTurn++;const event=state.events.find(e=>e.seq===item.seq),data={content:event?.data.submittedContent??event?.data.content??[{type:'text',text:item.text}],time:times.get(event?.turnId)};
      n={kind:'user',data};navigation.push({turn:currentTurn,anchorKey:key,prompt:item.text.slice(0,100),response:''});
    }
    if(item.kind==='assistant')n={kind:'assistant-step',data:{blocks:[...(item.thinking?[{kind:'reasoning',text:item.thinking}]:[]),...(item.text?[{kind:'text',text:item.text}]:[])],step:ordinal,status:item.status==='streaming'?'running':item.partial?'interrupted':'complete',...(item.seq?{finalNode:{seq:item.seq}}:{})}};
    if(item.kind==='tool'){const binding=ownership.get(item.seq),proposal=state.events.find(e=>e.seq===binding?.proposalSeq),start=state.events.find(e=>e.seq===item.seq),raw=retainedToolArguments(start?.data??{}),call=proposal?.data.message?.content?.find(p=>(p.id??p.callId)===item.toolCallId)??(raw===undefined?undefined:{name:item.name,arguments:JSON.parse(raw)});n={kind:'pi-tool',data:{...item,call,result:state.events.find(e=>e.type==='tool/result'&&ownership.get(e.seq)?.id===binding?.id&&ownership.get(e.seq)?.startSeq===item.seq)?.data.result}};}
    if(['status','warning'].includes(item.kind))n={kind:'pi-notice',data:item};
    if(n)chatNodes.set(key,{...n,key,anchorSeq,location:{kind:'session'}});ordinal++;
  }
  const store={get:key=>chatNodes.get(key),values:()=>[...chatNodes.values()]};
  const chat={order:[...chatNodes.keys()],nodes:store,navigation:{items:()=>navigation}};
  const latestComplete=state.records.filter(r=>r.kind==='model/complete').at(-1),latestRequest=state.records.filter(r=>r.kind==='model/request').at(-1),u=latestComplete?.data.usage;
  const pressureRequest=state.records.find(r=>r.id===latestComplete?.requestId);
  const pressure=u&&((u.input||0)+(u.cacheRead||0)+(u.cacheWrite||0))>0&&pressureRequest?.data.capacity?{pressureTokens:(u.input||0)+(u.cacheRead||0)+(u.cacheWrite||0),contextWindow:pressureRequest.data.capacity}:undefined;
  const callSchemas=new Map();
  for(const event of state.events.filter(e=>e.type==='tool/call')){const binding=ownership.get(event.seq),record=observedTool(state.records,'tool/start',event,binding),body=record&&state.payloads?.[record.requestId];if(!body)continue;const tool=(body.tools||[]).map(x=>x.function||x).find(x=>x.name===record.data.name);if(tool)callSchemas.set(binding.id,tool);}
  const requests=state.records.filter(r=>r.kind==='model/request').flatMap(r=>{
    // Observation and display sequences are independent. Join only an explicit request id.
    const result=state.events.find(e=>e.type==='assistant/message'&&e.data.requestId===r.id);
    const end=state.records.find(x=>x.kind==='model/complete'&&x.requestId===r.id);
    const pending=live.liveRequest?.id===r.id?live.liveRequest:null;
    if(!result&&!pending)return []; // Unlinked requests stay in Context without invented attribution.
    const node=result?eventNodes.find(node=>node.seq===result.seq):null;
    const turn=node?.turn??pending.turn,step=node?.step??pending.step;
    const body=state.payloads?.[r.id],config={provider:r.data.provider,model:r.data.model,reasoningEffort:r.data.thinkingLevel};
    const prompt=body?{config,system:body.system??(body.messages||[]).filter(m=>['system','developer'].includes(m.role)).map(m=>typeof m.content==='string'?m.content:JSON.stringify(m.content)).join('\n'),tools:(body.tools||[]).map(x=>x.function||x)}:undefined;
    const previous=state.events.filter(e=>e.seq<(result?.seq??pending.firstSeq)&&e.type!=='assistant/chunk').at(-1);
    return [{purpose:'assistant',startSeq:previous?.seq??result?.seq??pending.firstSeq,...(result?{resultSeq:result.seq}:{}),turn,step,startedAt:r.time,completedAt:end?.time??null,status:end?['aborted','error'].includes(end.data.stopReason)?'error':'complete':'running',requestConfig:{provider:r.data.provider,model:r.data.model,reasoningEffort:r.data.thinkingLevel},providerMetadata:{provider:r.data.provider,model:r.data.model},usage:end?.data.usage,...(prompt?{prompt}:{})}];
  });
  const inbox={'next-turn':(state.queue?.items||[]).filter(x=>x.canRemove).map(x=>({id:x.id,source:{kind:'user',rpcId:x.id},content:x.message?.content||[]})),'next-step':[]};
  return {chat,trajectory:{eventNodes:trajectoryNodes,eventLocations:locations,requests,callSchemas,partial:live.partial,runningCalls:live.runningCalls},session:{running,blank:!visible.length,openState:state.phase==='loading'?'loading':'open',openError:null,hasMore:state.hasMore,loadingOlder:false,pendingSubmissions:[],subagent:null,removed:false,promptError:null},conversation:{activeTargets:new Set(visible.length?['chat','trajectory']:[]),views:{get:()=>undefined,grouped:()=>undefined}},projection:{contextPressure:pressure,inbox,goal:state.goal?.goal}};
}
