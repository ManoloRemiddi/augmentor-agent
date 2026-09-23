// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// DSH's default steer waits for a whole model request. Supersede that request
// while preserving the identified correction and all unrelated inbox work.
export function applyResponsiveSteering(ctx) {
  const streaming=new Set(),tools=new Map(),moving=new Set()
  ctx.on('agent/assistant-stream',({agent,frame})=>{
    if(frame.type==='start')streaming.add(agent.id)
    else if(frame.type==='end')streaming.delete(agent.id)
  })
  ctx.on('tools/execute',async(exec,next)=>{
    const id=exec.agent?.id
    if(!id)return next()
    tools.set(id,(tools.get(id)??0)+1)
    try{return await next()}finally{
      const left=(tools.get(id)??1)-1
      if(left)tools.set(id,left);else tools.delete(id)
    }
  })
  ctx.on('agent/inbox/inserted',({agent,message})=>{
    if(moving.has(agent.id)||message.source.kind!=='user'||!streaming.has(agent.id)||tools.has(agent.id))return
    if(!agent.inbox.nextStep.some(row=>row.id===message.id))return
    // Recheck after the original send has finished publishing its insertion.
    queueMicrotask(()=>{
      if(moving.has(agent.id)||agent.status!=='running'||!streaming.has(agent.id)||tools.has(agent.id))return
      const pending=agent.inbox.nextStep.find(row=>row.id===message.id)
      if(!pending)return
      moving.add(agent.id)
      try{
        streaming.delete(agent.id)
        agent.cancel({kind:'hook',reason:'Augmentor: apply user steering now'},{keepInbox:true})
        agent.inbox.remove(pending.id)
        // A waking send after cancellation is routed to the next turn by DSH.
        // Preserve its ID and put it before ordinary queued follow-ups.
        agent.steer(pending)
        const index=agent.inbox.nextTurn.findIndex(row=>row.id===pending.id)
        if(index>0){agent.inbox.splice('next-turn',index,1,[]);agent.inbox.prepend('next-turn',pending)}
      }finally{moving.delete(agent.id)}
    })
  })
  ctx.on('agent/status',({agent,status})=>{if(status==='idle')streaming.delete(agent.id)})
  ctx.on('agent/disposed',({agent})=>{streaming.delete(agent.id);tools.delete(agent.id);moving.delete(agent.id)})
  ctx.on('dispose',()=>{streaming.clear();tools.clear();moving.clear()})
}
