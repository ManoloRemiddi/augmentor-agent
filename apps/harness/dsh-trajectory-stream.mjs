// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
/** Read-only live seats for the original DSH Trajectory. No provider work. */
export function trajectoryStream(state,nodes,turnIds){
  const steps=new Map(),bySeq=new Map(nodes.map(node=>[node.seq,node])),activeCalls=new Map();
  let pending=null,turn=1;
  const nextStep=t=>(steps.get(t)||0)+1;
  const finish=()=>{
    if(!pending)return;
    const frozen={kind:'assistant',seq:pending.lastSeq,time:null,turn:pending.turn,step:pending.step,blocks:pending.blocks,interrupted:true};
    nodes.push(frozen);steps.set(pending.turn,pending.step);pending=null;
  };
  for(const event of state.events){
    const data=event.data||{},t=turnIds.get(event.turnId)||turn;
    if(['user/message','turn/start'].includes(event.type)){finish();if(t!==turn)activeCalls.clear();turn=t;}
    if(event.type==='assistant/chunk'){
      const chunk=data.chunk||{},kind=chunk.type==='text-delta'?'text':chunk.type==='reasoning-delta'?'reasoning':null;
      const patch=chunk.argsPatch,hasPatch=patch?.units==='utf16-code-units'&&Number.isSafeInteger(patch.prefix)&&patch.prefix>=0&&Number.isSafeInteger(patch.remove)&&patch.remove>=0&&typeof patch.insert==='string';
      const tool=chunk.type==='tool-call-snapshot'&&chunk.boundary==='public-sdk-partial-tool-call-arguments'&&Number.isSafeInteger(chunk.index)&&chunk.index>=0&&chunk.index<=4095&&typeof chunk.callId==='string'&&chunk.callId.length>0&&chunk.callId.length<=256&&typeof chunk.name==='string'&&chunk.name.length>0&&chunk.name.length<=256&&(typeof chunk.argsRaw==='string'||chunk.argsRaw===null||hasPatch);
      if((!kind||!chunk.text)&&!tool)continue;
      // A missing identity must never inherit a preceding observed request.
      if(pending&&(pending.requestId!==data.requestId||pending.turn!==t))finish();
      pending??={turn:t,step:nextStep(t),requestId:data.requestId,firstSeq:event.seq,lastSeq:event.seq,blocks:[],calls:new Map()};
      pending.lastSeq=event.seq;
      if(tool){
        let position=pending.calls.get(chunk.index);
        if(position===undefined){position=pending.blocks.length;pending.calls.set(chunk.index,position);}
        const previous=pending.blocks[position];let raw=chunk.argsRaw,reason=chunk.reason;
        if(hasPatch){if(previous?.kind==='tool-call'&&previous.callId===chunk.callId&&previous.name===chunk.name&&patch.prefix+patch.remove<=previous.argsRaw.length)raw=previous.argsRaw.slice(0,patch.prefix)+patch.insert+previous.argsRaw.slice(patch.prefix+patch.remove);else{raw=null;reason='Live SDK argument patch has no available base; inspect the native message.';}}
        if(typeof raw==='string'&&raw.length>512*1024){raw=null;reason='Live SDK argument display limit exceeded; inspect the native message.';}
        pending.blocks[position]=raw===null?{kind:'other',block:{type:'pi-sdk-tool-arguments',callId:chunk.callId,name:chunk.name,status:'unavailable',reason}}:{kind:'tool-call',callId:chunk.callId,name:chunk.name,argsRaw:raw,subCalls:[]};
        continue;
      }
      const last=pending.blocks.at(-1);if(last?.kind===kind)last.text+=chunk.text;else pending.blocks.push({kind,text:chunk.text});
    }
    if(event.type==='assistant/message'){
      if(pending&&pending.requestId&&pending.requestId!==data.requestId)finish();
      // The final SDK message owns all its delta bytes, including Stop/error.
      pending=null;const node=bySeq.get(event.seq);if(node){node.step=nextStep(t);steps.set(t,node.step);}
    }
    if(event.type==='tool/call'&&!data.parentToolCallId)activeCalls.set(data.toolCallId,{event,turn:t});
    if(event.type==='tool/result')activeCalls.delete(data.toolCallId);
    if(event.type==='turn/end'){finish();activeCalls.clear();}
  }
  const running=state.sessions.find(row=>row.sessionId===state.sessionId)?.running===true;
  if(!running)finish();
  const timing=requestId=>{
    if(!requestId)return undefined;
    const request=state.records.find(row=>row.kind==='model/request'&&row.id===requestId);
    if(!request)return undefined;
    const first=state.records.find(row=>row.kind==='model/firstToken'&&row.requestId===requestId);
    return {stepStartTime:request.time??null,firstTokenTime:first?.time??null};
  };
  const partial=pending?{turn:pending.turn,step:pending.step,blocks:pending.blocks,...(timing(pending.requestId)?{timing:timing(pending.requestId)}:{})}:null;
  const runningCalls=running?[...activeCalls.values()].flatMap(({event,turn})=>{
    const id=event.data.toolCallId,parent=[...nodes].reverse().find(node=>node.kind==='assistant'&&node.turn===turn&&node.seq<event.seq&&node.blocks.some(block=>block.kind==='tool-call'&&block.callId===id));
    // Only an actual dispatch with a retained proposal can supply arguments.
    if(!parent)return [];
    const block=parent.blocks.find(block=>block.kind==='tool-call'&&block.callId===id),start=state.records.find(row=>row.kind==='tool/start'&&row.data.toolCallId===id);
    return [{callId:id,name:event.data.name,turn:parent.turn,step:parent.step,phase:'start',time:start?.time??null,argsRaw:block.argsRaw,subCalls:[]}];
  }):[];
  nodes.sort((a,b)=>a.seq-b.seq);
  return {partial,runningCalls,liveRequest:pending?.requestId?{id:pending.requestId,firstSeq:pending.firstSeq,turn:pending.turn,step:pending.step}:null};
}
