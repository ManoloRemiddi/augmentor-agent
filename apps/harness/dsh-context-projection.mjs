// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
const number=x=>typeof x==='number'&&Number.isFinite(x)&&x>=0?x:0;
const empty=()=>({system:0,tools:0,user:0,inject:0,skill:0,assistant:0,tool:0,total:0});
const estimate=text=>text?Math.ceil(text.length/4)+4:0;
const textOf=content=>typeof content==='string'?content:Array.isArray(content)?content.map(p=>p?.text??p?.thinking??(p?.type==='tool_result'?textOf(p.content):'')).join('\n'):'';
const imagesOf=content=>Array.isArray(content)?content.filter(p=>['image','image_url','input_image'].includes(p?.type)).length:0;
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
function frameOf(payload){
  if(!payload||!Array.isArray(payload.messages))return null;
  const system=[textOf(payload.system),...payload.messages.filter(m=>['system','developer'].includes(m?.role)).map(m=>textOf(m.content))].filter(Boolean).join('\n\n');
  const tools=(payload.tools??[]).map(t=>t.function??t).filter(t=>typeof t?.name==='string').map(t=>({name:t.name,description:t.description,schema:t.parameters??t.input_schema}));
  return {system,tools,messages:payload.messages.filter(m=>['user','assistant','tool'].includes(m?.role))};
}
/** Read-only presentation of retained provider snapshots, never a prediction of the next request.
 * Internal node ordinals only join the supplier browser; observation identities stay in requestIds.
 */
export function projectDshContext(state){
  const requests=(state.records??[]).filter(r=>r.kind==='model/request'),ends=new Map((state.records??[]).filter(r=>r.kind==='model/complete'&&r.requestId).map(r=>[r.requestId,r]));
  const headers=[],headerContent=new Map(),nodes=[],archive=[],conversationNodes=[],requestRecords=[],requestIds=new Map(),turns=new Map(),steps=new Map();
  const usage={uncachedInputTokens:0,outputTokens:0,cacheReadTokens:0,cacheWriteTokens:0},cost={};let ordinal=0,previous=[],previousKeys=[],current=empty(),latest=null,latestEnd=null;
  for(const request of requests){
    if(!turns.has(request.turnId??request.id))turns.set(request.turnId??request.id,turns.size+1);
    const turn=turns.get(request.turnId??request.id),step=(steps.get(turn)??0)+1;steps.set(turn,step);
    const end=ends.get(request.id),u=end?.data?.usage;
    if(u){usage.uncachedInputTokens+=number(u.input);usage.outputTokens+=number(u.output);usage.cacheReadTokens+=number(u.cacheRead);usage.cacheWriteTokens+=number(u.cacheWrite);
      const provider=request.data.provider,model=request.data.model;const bucket=((cost[provider]??={})[model]??={peak:{uncached:0,output:0,cacheRead:0,cacheWrite:0}}).peak;bucket.uncached+=number(u.input);bucket.output+=number(u.output);bucket.cacheRead+=number(u.cacheRead);bucket.cacheWrite+=number(u.cacheWrite);}
    const frame=frameOf(state.payloads?.[request.id]);if(!frame)continue;
    const keys=frame.messages.map(m=>JSON.stringify(m));let prefix=0;
    while(prefix<previousKeys.length&&prefix<keys.length&&previousKeys[prefix]===keys[prefix])prefix++;
    const headerSeq=++ordinal;for(const node of previous.slice(prefix))archive.push({...node,gone:headerSeq});
    headers.push({seq:headerSeq,time:request.time,systemTokens:estimate(frame.system),tools:frame.tools.map(tool=>({name:tool.name,tokens:estimate(JSON.stringify(tool))}))});headerContent.set(headerSeq,frame);
    current=empty();current.system=estimate(frame.system);current.tools=headers.at(-1).tools.reduce((total,t)=>total+t.tokens,0);previous=previous.slice(0,prefix);previousKeys=keys;
    for(const node of previous)current[node.cat]+=node.tokens;
    const names=new Map(frame.messages.flatMap(m=>(m.tool_calls??[]).map(c=>[c.id,c.function?.name])));
    for(const message of frame.messages.slice(prefix)){
      const cat=message.role==='tool'||(message.role==='user'&&Array.isArray(message.content)&&message.content.every(p=>p.type==='tool_result'))?'tool':message.role;
      const blocks=blocksOf(message),text=blocks.filter(b=>b.kind!=='tool-call').map(b=>b.text??'').join('\n');
      const callText=blocks.filter(b=>b.kind==='tool-call').map(b=>b.name+' '+b.argsRaw).join('\n');
      const toolName=message.name??names.get(message.tool_call_id);
      const node={seq:++ordinal,time:request.time,cat,tokens:estimate(textOf(message.content)+'\n'+callText+(message.reasoning_content??'')),text,imgs:imagesOf(message.content),form:cat==='tool'?'tool-result':cat,tool:cat==='tool'?toolName:undefined,calls:blocks.filter(b=>b.kind==='tool-call').map(b=>b.name),...(message.tool_call_id?{callId:message.tool_call_id}:{})};
      const conv={seq:node.seq,kind:cat==='tool'?'tool-result':cat,...(cat==='assistant'?{blocks}:{content:blocks}),...(cat==='tool'&&toolName?{call:{name:toolName,argsRaw:''}}:{})};
      previous.push(node);conversationNodes.push(conv);current[cat]+=node.tokens;
    }
    current.total=Object.entries(current).filter(([k])=>k!=='total').reduce((sum,[,v])=>sum+v,0);
    const seq=++ordinal,prompt=u?number(u.input)+number(u.cacheRead)+number(u.cacheWrite):undefined;
    requestRecords.push({...current,seq,time:request.time,turn,step,...(prompt>0?{prompt}:{}),...(u?{cacheRead:number(u.cacheRead),output:number(u.output)}:{}),...(Number.isFinite(end?.data.durationMs)?{activeMs:end.data.durationMs}:{})});
    requestIds.set(seq,request.id);latest=request;latestEnd=end;
  }
  nodes.push(...previous);
  const latestAvailable=latest?.id===requests.at(-1)?.id;
  const prompt=latestEnd?.data.usage?number(latestEnd.data.usage.input)+number(latestEnd.data.usage.cacheRead)+number(latestEnd.data.usage.cacheWrite):0;
  const capacity=latestAvailable?number(latest?.data.capacity):0;
  const nextSeq=r=>requestRecords.find(x=>requests.find(q=>q.id===requestIds.get(x.seq))?.seq>r.seq)?.seq;
  const events=(state.records??[]).filter(r=>r.kind==='compaction/end').map(r=>({seq:nextSeq(r)!==undefined?nextSeq(r)-0.5:++ordinal,time:r.time,kind:'compaction',detail:'Recorded Pi compaction-end event; effect, cause and removed-token count are unavailable. Context edits remain in Raw Pi records.'}));
  const completed=state.events??[],toolCalls=new Map();
  for(const event of completed)for(const block of event.data?.message?.content??[])if(block.type==='toolCall')toolCalls.set(block.id,block);
  const fileOps=[];
  for(const result of completed.filter(e=>e.type==='tool/result')){const call=toolCalls.get(result.data.toolCallId),kind={read:'read',write:'write',edit:'write',grep:'search',glob:'search'}[call?.name],path=call?.arguments?.path;if(!kind||typeof path!=='string')continue;
    fileOps.push({seq:[...nodes,...archive].find(n=>n.callId===result.data.toolCallId)?.seq??++ordinal,path,kind,tool:call.name,time:(state.records??[]).find(r=>r.kind==='tool/end'&&r.data.toolCallId===result.data.toolCallId)?.time,err:result.data.isError===true,added:0,removed:0});}
  const timeline={ok:true,model:latest?.data.model,provider:latest?.data.provider,...(capacity?{contextWindow:capacity}:{}),current,nodes,archive,droppedNodes:0,requests:requestRecords,events,fileOps,cost,
    counts:{turns:turns.size,steps:requests.length,injects:0,compactions:events.filter(e=>e.kind==='compaction').length,prunes:events.filter(e=>e.kind==='prune').length},
    humanInputs:completed.filter(e=>e.type==='user/message').length,answers:completed.filter(e=>e.type==='assistant/message'&&e.data.message?.content?.some(p=>p.type==='text'&&p.text?.trim())).length,toolCalls:completed.filter(e=>e.type==='tool/result').length,images:nodes.reduce((sum,n)=>sum+(n.imgs??0),0)};
  return {timeline,headers:{headers},headerContent,conversationNodes,requestIds,usage,pressure:latestAvailable&&prompt>0?{pressureTokens:prompt,...(capacity?{contextWindow:capacity}:{})}:null,
    coverage:{observed:requests.length,available:requestRecords.length,latestAvailable,historyPartial:state.hasMore===true||state.observationHasMore===true,unsupported:requests.filter(r=>state.payloads?.[r.id]&&!frameOf(state.payloads[r.id])).length}};
}
