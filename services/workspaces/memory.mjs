// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {promptCall} from '../../dist/prompt-library/src/client.js'
import {profileForSession} from './profiles.mjs'
export async function bindProfileMemory(profile,session,signal,call=promptCall){
 const expected={person:profile.memory.person,project:profile.memory.project}
 const value=await call('memory.dual.bind',{session,cwd:profile.cwd,...expected},undefined,signal)
 if(value.person!==expected.person||value.project!==expected.project)throw Error('Conversation memory belongs to a different workspace; no memory was recalled')
 return value
}
export function profileMemoryCall(profile,call=promptCall){return async(method,params,id,signal)=>{
 if(method==='memory.dual.bind')return bindProfileMemory(profile,params.session,signal,call)
 return call(method,params,id,signal)
}}
export async function recallWorkspace(agent,query,signal){
 const p=profileForSession(agent.session.header);if(!p)return null
 const session='dsh:'+agent.id;await bindProfileMemory(p,session,signal)
 return promptCall('memory.dual.search',{session,query},undefined,signal)
}
