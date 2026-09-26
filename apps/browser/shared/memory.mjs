// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.
import {promptCall} from '../../../dist/prompt-library/src/client.js'
import {loadProfile} from '../../../services/workspaces/profiles.mjs'
import {bindProfileMemory} from '../../../services/workspaces/memory.mjs'
const profile=loadProfile()
const actions=new Set(['dual.describe','dual.configure','dual.recall','describe','check','configure','disable','recall','retain','operations','operation','documents','document','delete','exportPage'])
export async function memoryRequest(request={}){
  const {action='describe',requestId,...params}=request
  if(profile){
    if(action==='describe')return {enabled:false,scoped:true,workspace:profile.name}
    if(action==='dual.describe')return {enabled:true,workspace:profile.name,person:profile.memory.person,project:profile.memory.project,scoped:true}
    if(action!=='dual.recall'||!/^dsh:[A-Za-z0-9_.-]{1,160}$/.test(params.session||''))throw Error('Workspace memory is managed by its dedicated profile. Open standalone Augmentor for personal memory settings.')
    await bindProfileMemory(profile,params.session)
    return promptCall('memory.dual.recall',{session:params.session},requestId)
  }
  if(!actions.has(action))throw new Error('Unsupported memory action')
  return promptCall('memory.'+action,params,requestId)
}
