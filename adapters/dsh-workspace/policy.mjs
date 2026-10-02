// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Final monotonic DSH guard: prompt content cannot expand an installed grant.
import {loadProfile,canonical} from '../../services/workspaces/profiles.mjs'
import {validatePolicy} from '../../services/workspaces/policy.mjs'
export const name='augmentor-workspace-policy'
export const inject=['tools']
export function apply(ctx,{profileId}={}){
 const profile=loadProfile(profileId);validatePolicy(profile)
 if(typeof ctx.tools.guard!=='function')throw Error('This DSH tools runtime lacks the required monotonic execution guard; update the qualified runtime before using SDK profiles')
 ctx.tools.presentAs('native')
 // Match the model's catalog to the grant. The final guard remains mandatory:
 // visibility alone is not an execution authorization boundary.
 ctx.on('system-prompt/assemble',async(_assembly,_context,next)=>{
  const assembly=await next(),allowed=validatePolicy(loadProfile(profileId)).tools
  return {...assembly,tools:assembly.tools.filter(tool=>allowed.includes(tool.name))}
 })
 ctx.tools.guard(exec=>{
  const current=loadProfile(profileId),policy=validatePolicy(current),header=exec.agent?.session?.header
  if(!header||header.agentPreset!==current.preset||typeof header.cwd!=='string'||canonical(header.cwd)!==current.cwd)return 'Tool call does not belong to this workspace'
  if(!policy.tools.includes(exec.name))return 'This tool is not granted to the application workspace'
 })
}
