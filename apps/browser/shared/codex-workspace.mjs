// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {loadProfile,canonical,preferences} from '../../../services/workspaces/profiles.mjs'
import {guardWorkspaceMethod,SDK_PROTOCOL} from '../../../services/workspaces/policy.mjs'
import {describeWorkspace} from '../../../services/workspaces/capabilities.mjs'

export class CodexWorkspaceBoundary {
 constructor(call,profileLoader=loadProfile){this.call=call;this.profileLoader=profileLoader}
 profile(){const p=this.profileLoader();if(p?.harness!=='codex'||p.sdkProtocol!==SDK_PROTOCOL)throw Error('A registered Codex application workspace is required');return p}
 async owns(sessionId){
  const p=this.profile(),meta=await this.call('session.describe',{sessionId})
  if(meta.workspace?.id!==p.id||meta.workspace.preset!==p.preset||canonical(meta.cwd)!==p.cwd||meta.profileId!==p.connection)throw Error('This Codex conversation belongs to another application workspace')
  return meta
 }
 async selection(){
  const p=this.profile(),catalog=await this.call('models.list')
  const group=catalog.groups.find(group=>group.provider===p.connection),model=group?.models?.[0]?.model
  if(!model)throw Error('Configure the registered Codex connection in standalone Augmentor')
  return {provider:p.connection,model}
 }
 async guard(method,params={}){
  const p=this.profile();guardWorkspaceMethod(p,method,params)
  if(method==='workspace.describe'){if(params.protocol!==SDK_PROTOCOL)throw Error('Incompatible application SDK protocol');return}
  if(method==='session.create')return {...params,cwd:p.cwd,workspaceId:p.id,profileId:p.connection,selection:await this.selection()}
  if(method==='session.branchStatus'){await this.owns(params.sessionId);return {...params,workspaceId:p.id}}
  if((method.startsWith('session.')&&!['session.list'].includes(method))||['augmentor/interaction','augmentor/voice/start','augmentor/save','augmentor/unsave'].includes(method))await this.owns(params.sessionId)
  if(method==='session.selectModel'&&params.provider!==p.connection)throw Error('This workspace uses its registered Codex connection')
  if(method==='augmentor/memory'){
   if(params.action!=='dual.recall'||typeof params.session!=='string'||!params.session.startsWith('codex:'))throw Error('Shared memory administration is unavailable in application workspaces')
   await this.owns(params.session.slice(6))
  }
  return params
 }
 filter(items){const p=this.profile();return items.filter(row=>row.workspaceId===p.id&&row.agentPreset===p.preset&&typeof row.cwd==='string'&&canonical(row.cwd)===p.cwd&&row.selection?.provider===p.connection)}
 describe(){return describeWorkspace(this.profile())}
 saved(method,params={}){
  const p=this.profile(),saved=new Set(preferences(p)['saved-sessions']??[])
  if(method!=='augmentor/state'){method==='augmentor/save'?saved.add(params.sessionId):saved.delete(params.sessionId);preferences(p,{set:{'saved-sessions':[...saved]}})}
  return {ok:true,saved:[...saved]}
 }
}
