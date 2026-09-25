// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {definitions,homeTool} from '../../dist/home-client/src/index.js';
export const name='augmentor-home-client';
export const inject=['tools'];
export function apply(ctx){
 for(const d of definitions)ctx.tools.register({...d,
  augmentorExecution:{effect:()=>['home_status','home_result','home_read','home_devices'].includes(d.name)?'read':'change',outcome:(_args,value)=>({status:['unknown','incomplete','interrupted'].includes(value?.response?.status??value?.status)?'unknown':value?.status==='running'?'running':'completed'})},
  output:{schema:{type:'object'},render:(_args,value)=>[{type:'text',text:JSON.stringify(value)}]},
  execute:async(args,exec)=>{if(!exec.agent?.id)throw Error('Home requires an active Augmentor conversation');return homeTool(d.name,args,'dsh:'+exec.agent.id,String(exec.callId),exec.signal);}
 });
}
