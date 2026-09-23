// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Loaded only by the isolated release proof. Performs no external action.
export const name='augmentor-approval-proof'
export const inject=['tools','approval']
export function apply(ctx){
 ctx.tools.register({name:'fixture_approval',description:'Request a harmless fixture decision.',parameters:{},
  output:{schema:{type:'object'},render:(_args,value)=>[{type:'text',text:JSON.stringify(value)}]},
  execute:async(_args,exec)=>({outcome:await ctx.approval.request({agent:exec.agent,signal:exec.signal,
   callId:exec.callId,toolName:'fixture_approval',reason:'Test decision only; no external action is performed.'})})})
}
