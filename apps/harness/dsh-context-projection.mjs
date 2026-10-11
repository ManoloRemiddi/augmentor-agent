// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {contextFrame} from './dsh-context-frame.mjs';
const number=x=>typeof x==='number'&&Number.isFinite(x)&&x>=0?x:0;
const empty=()=>({system:0,tools:0,user:0,inject:0,skill:0,assistant:0,tool:0,total:0});
const estimate=text=>text?Math.ceil(text.length/4)+4:0;
const textOf=content=>typeof content==='string'?content:Array.isArray(content)?content.map(p=>p?.text??p?.thinking??(p?.type==='tool_result'?textOf(p.content):'')).join('\n'):'';
const imagesOf=content=>Array.isArray(content)?content.filter(p=>['image','image_url','input_image'].includes(p?.type)).length:0;
// Sparse supplier ordinals keep request selection stable when an older body
// arrives. A <=1 MiB body cannot fill this message range. Observation identities
// remain separate; numbers outside the exact ordinal range stay unsupported.
export const CONTEXT_REQUEST_STRIDE=2**20;
export function contextRequestSequence(record){
  const seq=record.seq*CONTEXT_REQUEST_STRIDE+CONTEXT_REQUEST_STRIDE-1;
  return Number.isSafeInteger(record.seq)&&record.seq>0&&seq<2**52?seq:null;
}
function blocksOf(message){
  const content=message.content,blocks=typeof content==='string'?[{kind:'text',text:content}]:Array.isArray(content)?content.flatMap(p=>{
    if(['text','input_text','output_text'].includes(p?.type))return [{kind:'text',text:p.text??''}];
    if(['thinking','reasoning'].includes(p?.type))return [{kind:'reasoning',text:p.thinking??p.text??''}];
    if(p?.type==='tool_use')return [{kind:'tool-call',name:p.name,argsRaw:JSON.stringify(p.input??{})}];
    if(p?.type==='tool_result')return [{kind:'text',text:textOf(p.content)}];
    if(['image','image_url','input_image'].includes(p?.type))return [{kind:'text',text:'[Image input — binary content remains in the authenticated attachment viewer]'}];
    return [{kind:'text',text:JSON.stringify(p)}];
  }):[];
  if(typeof message.reasoning_content==='string')blocks.push({kind:'reasoning',text:message.reasoning_content});
  for(const call of message.tool_calls??[])blocks.push({kind:'tool-call',name:call.function?.name??'unknown',argsRaw:call.function?.arguments??''});
  return blocks;
}
// Link only a preceding, unambiguous provider call in this exact snapshot.
// Consume each id once; a later settled reuse may have different arguments.
// SDK arguments and calls from other snapshots are not effective wire input.
function resultCalls(messages){
  const pending=new Map();
  return messages.map(message=>{
    if(message.role==='assistant')for(const call of message.tool_calls??[]){
      if(typeof call?.id!=='string'||!call.id)continue;
      pending.set(call.id,pending.has(call.id)?null:call.function);
    }
    if(message.role!=='tool')return undefined;
    const call=pending.get(message.tool_call_id);pending.delete(message.tool_call_id);
    if(typeof call?.name!=='string'||(message.name!==undefined&&message.name!==call.name))return undefined;
    return call;
  });
}
/** Read-only presentation of retained provider snapshots, never a prediction of the next request.
 * Internal node ordinals only join the supplier browser; observation identities stay in requestIds.
 */
export function projectDshContext(state){
  const requests=(state.records??[]).filter(r=>r.kind==='model/request'),ends=new Map((state.records??[]).filter(r=>r.kind==='model/complete'&&r.requestId).map(r=>[r.requestId,r]));
  const headers=[],headerContent=new Map(),nodes=[],archive=[],conversationNodes=[],requestRecords=[],requestChoices=[],requestIds=new Map(),turns=new Map(),steps=new Map();
  const usage={uncachedInputTokens:0,outputTokens:0,cacheReadTokens:0,cacheWriteTokens:0},cost={};let ordinal=0,previous=[],previousKeys=[],current=empty(),latest=null,latestEnd=null;
  for(const request of requests){
    if(!turns.has(request.turnId??request.id))turns.set(request.turnId??request.id,turns.size+1);
    const turn=turns.get(request.turnId??request.id),step=(steps.get(turn)??0)+1;steps.set(turn,step);
    const requestSeq=contextRequestSequence(request),choice=requestSeq===null?null:{seq:requestSeq,id:request.id,time:request.time,turn,step,available:false};if(choice)requestChoices.push(choice);
    const end=ends.get(request.id),u=end?.data?.usage;
    if(u){usage.uncachedInputTokens+=number(u.input);usage.outputTokens+=number(u.output);usage.cacheReadTokens+=number(u.cacheRead);usage.cacheWriteTokens+=number(u.cacheWrite);
      const provider=request.data.provider,model=request.data.model;const bucket=((cost[provider]??={})[model]??={peak:{uncached:0,output:0,cacheRead:0,cacheWrite:0}}).peak;bucket.uncached+=number(u.input);bucket.output+=number(u.output);bucket.cacheRead+=number(u.cacheRead);bucket.cacheWrite+=number(u.cacheWrite);}
    const frame=contextFrame(state.payloads?.[request.id],request.data.api);if(!frame||requestSeq===null||frame.messages.length>=CONTEXT_REQUEST_STRIDE-2)continue;
    const keys=frame.messages.map(m=>JSON.stringify(m));let prefix=0;
    while(prefix<previousKeys.length&&prefix<keys.length&&previousKeys[prefix]===keys[prefix])prefix++;
    const headerSeq=requestSeq-CONTEXT_REQUEST_STRIDE+2;for(const node of previous.slice(prefix))archive.push({...node,gone:headerSeq});
    headers.push({seq:headerSeq,time:request.time,systemTokens:estimate(frame.system),tools:frame.tools.map(tool=>({name:tool.name,tokens:estimate(JSON.stringify(tool))}))});headerContent.set(headerSeq,frame);
    current=empty();current.system=estimate(frame.system);current.tools=headers.at(-1).tools.reduce((total,t)=>total+t.tokens,0);previous=previous.slice(0,prefix);previousKeys=keys;
    for(const node of previous)current[node.cat]+=node.tokens;
    const calls=resultCalls(frame.messages);
    for(const [index,message] of frame.messages.entries()){
      if(index<prefix)continue;
      const cat=message.role==='tool'||(message.role==='user'&&Array.isArray(message.content)&&message.content.every(p=>p.type==='tool_result'))?'tool':message.role;
      const blocks=blocksOf(message),text=blocks.filter(b=>b.kind!=='tool-call').map(b=>b.text??'').join('\n');
      const callText=blocks.filter(b=>b.kind==='tool-call').map(b=>b.name+' '+b.argsRaw).join('\n');
      const call=calls[index],toolName=message.name??call?.name;
      const node={seq:headerSeq+index+1,time:request.time,cat,tokens:estimate(textOf(message.content)+'\n'+callText+(message.reasoning_content??'')),text,imgs:imagesOf(message.content),form:cat==='tool'?'tool-result':cat,tool:cat==='tool'?toolName:undefined,calls:blocks.filter(b=>b.kind==='tool-call').map(b=>b.name),...(message.tool_call_id?{callId:message.tool_call_id}:{}),...(typeof message.isError==='boolean'?{err:message.isError}:{})};
      const conv={seq:node.seq,kind:cat==='tool'?'tool-result':cat,...(cat==='assistant'?{blocks}:{content:blocks}),...(cat==='tool'&&toolName?{call:{name:toolName,argsRaw:typeof call?.arguments==='string'?call.arguments:'[Call arguments unavailable in this recorded request]'}}:{}),...(typeof message.isError==='boolean'?{isError:message.isError}:{})};
      previous.push(node);conversationNodes.push(conv);current[cat]+=node.tokens;
    }
    current.total=Object.entries(current).filter(([k])=>k!=='total').reduce((sum,[,v])=>sum+v,0);
    const seq=requestSeq,prompt=u?number(u.input)+number(u.cacheRead)+number(u.cacheWrite):undefined;ordinal=Math.max(ordinal,seq);choice.available=true;
    requestRecords.push({...current,seq,time:request.time,turn,step,...(prompt>0?{prompt}:{}),...(u?{cacheRead:number(u.cacheRead),output:number(u.output)}:{}),...(Number.isFinite(end?.data.durationMs)?{activeMs:end.data.durationMs}:{})});
    requestIds.set(seq,request.id);choice.gaps=frame.gaps;latest=request;latestEnd=end;
  }
  nodes.push(...previous);
  const latestAvailable=latest?.id===requests.at(-1)?.id;
  const prompt=latestEnd?.data.usage?number(latestEnd.data.usage.input)+number(latestEnd.data.usage.cacheRead)+number(latestEnd.data.usage.cacheWrite):0;
  const capacity=latestAvailable?number(latest?.data.capacity):0;
  const nextSeq=r=>requestRecords.find(x=>requests.find(q=>q.id===requestIds.get(x.seq))?.seq>r.seq)?.seq;
  const receipts=new Map((state.records??[]).filter(r=>r.kind==='compaction/receipt').map(r=>[r.data.requestId,r.data]));
  const compactionAttempts=(state.records??[]).filter(r=>r.kind==='compaction/end');
  // The supplier marker asserts a saved compaction. Attempts remain in raw
  // records/coverage; feeding them here would falsely label them completed.
  const events=compactionAttempts.filter(r=>receipts.get(r.data.operationId)?.state==='completed'||r.data.returnedSummary===true).map(r=>{const receipt=receipts.get(r.data.operationId);return {seq:nextSeq(r)!==undefined?nextSeq(r)-0.5:++ordinal,time:r.time,kind:'compaction',committed:true,detail:`Pi summary saved${receipt?.entryId?` as native entry ${receipt.entryId}`:''}. SDK context estimate before: ${receipt?.tokensBefore??r.data.tokensBefore??'unavailable'}; after: ${receipt?.estimatedTokensAfter??r.data.estimatedTokensAfter??'unavailable'}. Original history is preserved.`};});
  const completed=state.events??[],toolCalls=new Map();
  for(const event of completed)for(const block of event.data?.message?.content??[])if(block.type==='toolCall')toolCalls.set(block.id,block);
  const fileOps=[];
  for(const result of completed.filter(e=>e.type==='tool/result')){const call=toolCalls.get(result.data.toolCallId),kind={read:'read',write:'write',edit:'write',grep:'search',glob:'search'}[call?.name],path=call?.arguments?.path;if(!kind||typeof path!=='string')continue;
    fileOps.push({seq:[...nodes,...archive].find(n=>n.callId===result.data.toolCallId)?.seq??++ordinal,path,kind,tool:call.name,time:(state.records??[]).find(r=>r.kind==='tool/end'&&r.data.toolCallId===result.data.toolCallId)?.time,err:result.data.isError===true,added:0,removed:0});}
  const timeline={ok:true,model:latest?.data.model,provider:latest?.data.provider,...(capacity?{contextWindow:capacity}:{}),current,nodes,archive,droppedNodes:0,requests:requestRecords,events,fileOps,cost,
    counts:{turns:turns.size,steps:requests.length,injects:0,compactions:events.filter(e=>e.kind==='compaction'&&e.committed).length,prunes:events.filter(e=>e.kind==='prune').length},
    humanInputs:completed.filter(e=>e.type==='user/message').length,answers:completed.filter(e=>e.type==='assistant/message'&&e.data.message?.content?.some(p=>p.type==='text'&&p.text?.trim())).length,toolCalls:completed.filter(e=>e.type==='tool/result').length,images:nodes.reduce((sum,n)=>sum+(n.imgs??0),0)};
  return {timeline,headers:{headers},headerContent,conversationNodes,requestIds,requestChoices,usage,pressure:latestAvailable&&prompt>0?{pressureTokens:prompt,...(capacity?{contextWindow:capacity}:{})}:null,
    coverage:{observed:requests.length,available:requestRecords.length,latestAvailable,compactionAttempts:compactionAttempts.length,confirmedCompactions:events.length,historyPartial:state.hasMore===true||state.observationHasMore===true,unsupported:requests.filter(r=>state.payloads?.[r.id]&&!contextFrame(state.payloads[r.id],r.data.api)).length,opaque:requestChoices.filter(r=>r.gaps?.length).length}};
}
