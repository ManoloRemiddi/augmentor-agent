// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Mount in an Augmentor preset, not in DSH's global host plane.
import {recall,MEMORY_DESCRIPTION,memorySource,SOURCE_DESCRIPTION} from '../../dist/memory/src/index.js'
import {profileForSession} from '../../services/workspaces/profiles.mjs'
import {recallWorkspace,bindProfileMemory} from '../../services/workspaces/memory.mjs'
import {applyAutomaticMemory} from './automatic.mjs'
export const name='augmentor-memory'
export const inject=['tools','llm']
export function apply(ctx){
  applyAutomaticMemory(ctx)
  ctx.tools.register({name:'memory_source',description:SOURCE_DESCRIPTION,
    parameters:{type:'object',additionalProperties:false,required:['seq'],properties:{seq:{type:'integer',minimum:1}}},
    output:{schema:{type:'string'},render:(_args,value)=>[{type:'text',text:value}]},
    execute:async(args,exec)=>{
      if(!exec.agent||exec.agent.session.header.parentSession||exec.agent.session.header.isSeeded)throw Error('Automatic source recall is unavailable in historical branches');
      const profile=profileForSession(exec.agent.session.header);if(profile)await bindProfileMemory(profile,'dsh:'+exec.agent.id,exec.signal);
      return JSON.stringify(await memorySource(args.seq,'dsh:'+exec.agent.id,exec.signal));
    }})
  ctx.tools.register({name:'memory_recall',description:MEMORY_DESCRIPTION,
    parameters:{type:'object',additionalProperties:false,required:['query'],properties:{query:{type:'string',minLength:1,maxLength:4096}}},
    output:{schema:{type:'string'},render:(_args,value)=>[{type:'text',text:value}]},
    execute:async(args,exec)=>{if(exec.agent&&profileForSession(exec.agent.session.header))return JSON.stringify(await recallWorkspace(exec.agent,args.query,exec.signal));return JSON.stringify(await recall(args.query,exec.signal,exec.agent&&!exec.agent.session.header.parentSession&&!exec.agent.session.header.isSeeded?'dsh:'+exec.agent.id:undefined))}})
}
