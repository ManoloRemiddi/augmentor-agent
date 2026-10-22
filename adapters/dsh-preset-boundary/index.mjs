// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Optional DSH-owned preset composition: no persona, skills or tools are authored here.
export const name='augmentor-preset-boundary'
export const inject=['tools','sandboxPolicy','approval']
export function apply(ctx,{preset,cwd,tools,mode='workspace-write'}={}){
 if(typeof preset!=='string'||!Array.isArray(tools)||!tools.length||tools.some(n=>typeof n!=='string')||!['read-only','workspace-write'].includes(mode))throw Error('Explicit preset, tools and confined sandbox mode are required')
 if(typeof ctx.tools.guard!=='function')throw Error('This DSH runtime cannot enforce independent preset tool boundaries')
 const granted=new Set(tools)
 ctx.tools.presentAs('native')
 // Mask every inherited registration; this preset's local registrations survive.
 const inherited=ctx.tools.schemas().map(t=>t.name)
 if(inherited.length)ctx.tools.restrict({deny:inherited})
 ctx.on('agent/created',({agent})=>{
  if(agent.session.header.agentPreset!==preset)throw Error('Preset boundary mounted for another agent')
  if(cwd&&agent.session.header.cwd!==cwd)throw Error('Selected working folder is outside this preset boundary')
  const policy=ctx.sandboxPolicy.resolve({session:agent.session})
  if(policy.mode==='danger-full-access'||mode==='read-only'&&policy.mode!=='read-only')agent.session.append('sandbox/mode',{mode})
  if(ctx.approval.effectivePolicy(agent.session)!=='ask')agent.session.append('approval/policy',{policy:'ask'})
 })
 ctx.on('system-prompt/assemble',async(_assembly,_context,next)=>{
  const assembly=await next()
  return {...assembly,tools:assembly.tools.filter(t=>granted.has(t.name))}
 })
 ctx.tools.guard(exec=>{
  const session=exec.agent?.session
  if(!session||session.header.agentPreset!==preset||cwd&&session.header.cwd!==cwd)return 'This call is outside the selected DSH preset boundary'
  if(!granted.has(exec.name))return 'This tool is not granted by the selected DSH preset'
  if(ctx.approval.effectivePolicy(session)!=='ask')return 'The selected DSH preset requires its approval policy'
  const effective=ctx.sandboxPolicy.resolve({session}).mode
  if(effective==='danger-full-access'||mode==='read-only'&&effective!=='read-only')return 'The selected DSH preset requires its confined sandbox policy'
 })
}
