// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
/** Read-only display projection. Native Pi history remains authoritative. */
export function projectChat(events,{running=false}={}){
 const items=[],tools=new Map();let pending={text:'',thinking:''},pendingItem;
 const flush=(status=running?'streaming':'partial',keep=false)=>{
  if(pending.text||pending.thinking){
   const draft={kind:'assistant',...pending,partial:true,status};
   if(pendingItem)Object.assign(pendingItem,draft);else{pendingItem=draft;items.push(pendingItem);}
  }
  if(!keep){pending={text:'',thinking:''};pendingItem=undefined;}
 };
 for(const event of events){
  const data=event.data||{};
  if(event.type==='assistant/chunk'){
   const chunk=data.chunk||{};
   if(chunk.type==='text-delta')pending.text+=chunk.text||'';
   if(chunk.type==='reasoning-delta')pending.thinking+=chunk.text||'';
  }else if(event.type==='assistant/message'){
   const parts=data.message?.content||[];
   const text=parts.filter(p=>p.type==='text').map(p=>p.text||'').join('\n');
   const thinking=parts.filter(p=>p.type==='thinking'||p.type==='reasoning').map(p=>p.thinking||p.text||'').join('\n');
   if(text||thinking){
    // A final SDK message already contains its deltas, including partial
    // messages on Stop/error. Do not display those bytes a second time.
    const stop=data.message?.stopReason,partial=['aborted','error','length'].includes(stop);
    const complete={kind:'assistant',text,thinking,seq:event.seq,partial,status:partial?stop:'complete'};
    if(pendingItem)Object.assign(pendingItem,complete);else items.push(complete);
    pending={text:'',thinking:''};pendingItem=undefined;
   }else flush('partial');
  }else if(event.type==='user/message'){
   flush('partial');
   items.push({kind:'user',seq:event.seq,text:(data.content||[]).filter(p=>p.type==='text').map(p=>p.text||'').join('\n')});
  }else if(event.type==='tool/call'){
   flush('complete');const item={kind:'tool',name:data.name,toolCallId:data.toolCallId,status:'pending'};
   items.push(item);tools.set(data.toolCallId,item);
  }else if(event.type==='tool/result'){
   const tool=tools.get(data.toolCallId);
   if(tool){tool.status=data.isError?'error':'finished';tools.delete(data.toolCallId);}
  }else if(event.type==='turn/end'){
   const reason=data.reason?.kind||'interrupted';flush(reason);
   for(const tool of tools.values())tool.status='outcome unknown';tools.clear();
   if(['aborted','interrupted','error'].includes(reason))items.push({kind:'status',text:data.message||({aborted:'Stopped.',error:'This turn ended with an error.',interrupted:'The runtime stopped; pending action outcomes may be unknown.'})[reason]});
  }else if(event.type==='runtime/notice'){
   flush('partial',true);items.push({kind:'status',text:data.message||'Execution status unavailable.'});
  }else if(event.type==='runtime/error'||event.type==='runtime/warning'){
   flush('partial',true);items.push({kind:'warning',text:data.message||'Runtime observation unavailable.'});
  }
 }
 flush();return items;
}

/** Ignore overlap between a durable snapshot and live frames captured earlier. */
export function appendDisplay(events,event){
 const last=events.at(-1)?.seq||0;
 if(!Number.isSafeInteger(event?.seq)||event.seq<=last)return false;
 events.push(event);return true;
}
