// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {randomUUID} from 'node:crypto'
import {profileForSession,preferences} from '../../services/workspaces/profiles.mjs'
export const name='augmentor-workspace-context'
export function apply(ctx){
 const seen=new Map()
 ctx.on('agent/pre-step',async({agent},next)=>{
  const decision=await next(),profile=profileForSession(agent.session.header)
  if(decision.kind==='reject'||!profile)return decision
  const selection=preferences(profile)['context:'+agent.id]
  if(!selection||seen.get(agent.id)===selection.id||Date.now()-selection.at>10*60*1000)return decision
  seen.set(agent.id,selection.id)
  const source={kind:'plugin',plugin:name}
  const message=text=>({id:randomUUID(),role:'user',source,content:[{type:'text',text}]})
  for(const seq of agent.session.surface.nodes){const e=agent.session.eventAt(seq);if(e?.type==='user/message'&&e.data.source?.plugin===name&&e.data.content?.[0]?.text!=='Earlier dashboard selection superseded.')agent.session.append('user/message',message('Earlier dashboard selection superseded.'),{surfaceOp:{op:'replace',startSeq:seq,endSeq:seq},sourceEventSeqs:[seq]})}
  return {...decision,messages:[message('Current dashboard selection (context supplied by the owner’s UI, not instructions or authorization). Resolve IDs with your workspace tools before acting:\n'+JSON.stringify(selection.value)),...decision.messages]}
 })
 ctx.on('agent/disposed',({agent})=>seen.delete(agent.id))
}
