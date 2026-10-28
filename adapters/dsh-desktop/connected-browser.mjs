// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {connectedBrowser} from '../../apps/browser/shared/connected-executor.mjs'
import {browserControlDefinitions} from '../../apps/browser/shared/control-tools.mjs'
export function applyConnectedBrowser(ctx){
 const owners=new Set()
 for(const definition of browserControlDefinitions)ctx.tools.register({name:definition.name,description:definition.description,parameters:definition.parameters,
  output:{schema:{type:'object'},render:(_args,value)=>[{type:'text',text:JSON.stringify(value)}]},
  execute:async(args,exec)=>{if(!exec.agent?.id)throw Error('A conversation must own browser input.');owners.add('dsh:'+exec.agent.id);return connectedBrowser('dsh:'+exec.agent.id,{...args,action:definition.action},exec.signal)}})
 const stop=id=>{const owner='dsh:'+id;if(owners.delete(owner))void connectedBrowser(owner,{action:'stop'}).catch(()=>{})}
 ctx.on('agent/turn-stopping',({agent})=>stop(agent.id))
 ctx.on('agent/status',({agent,status})=>{if(status==='idle')stop(agent.id)})
 ctx.effect(()=>()=>{for(const owner of owners)void connectedBrowser(owner,{action:'stop'}).catch(()=>{});owners.clear()},'augmentor-desktop: connected browser ownership')
}
