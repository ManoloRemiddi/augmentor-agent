// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {ownsProductSession,profileForSession,profiles} from '../../services/workspaces/profiles.mjs'
// DSH rc.1 host adapter: create an exact completed-turn seed through host services.
import {randomUUID} from 'node:crypto'

export async function exactFork(ctx,p){
 let preset=['browser','linux'].includes(p.surface)
 if(!preset||typeof p.sessionId!=='string'||!Number.isSafeInteger(p.atSeq)||p.atSeq<0||!Number.isSafeInteger(p.expectedCursor))throw Error('Invalid exact branch request')
 const observation=await ctx.sessionQuery.observeSession(p.sessionId)
 try{
  preset=observation.header.agentPreset
  if(!ownsProductSession(observation.header))throw Error('This conversation belongs to another role')
  if(observation.cursor!==p.expectedCursor)throw Error('Source conversation changed')
  const events=observation.events
  const boundary=events.findIndex(event=>event.seq===p.atSeq&&event.type==='turn/end')
  if(boundary<0)throw Error('Choose a completed turn boundary')
  const live=ctx.agents.get(p.sessionId)
  if(live?.status==='running')throw Error('Stop the source conversation before branching')
  const composition=await ctx.sessionController.agents.composeAgent(preset)
  // Recheck after asynchronous preset resolution, before the first mutation.
  const latest=await ctx.sessionQuery.observeSession(p.sessionId)
  try{
   if(latest.cursor!==observation.cursor||latest.header.agentPreset!==preset)throw Error('Source conversation changed')
  }finally{latest[Symbol.dispose]()}
  if(ctx.agents.get(p.sessionId)?.status==='running')throw Error('Stop the source conversation before branching')
  const sessionId='session-'+randomUUID()
  const selection=ctx.agentDefaultModel.currentSelection()
  await ctx.agents.create({sessionId,seed:events.slice(0,boundary+1),inheritedEventCount:boundary+1,
   meta:{...(observation.header.cwd?{cwd:observation.header.cwd}:{}),parentSession:p.sessionId,isSeeded:true,agentPreset:preset},
   agentOptions:{provider:selection.provider,model:selection.model},setup:composition.setup})
  const workspace=ctx.workspaceRegistry.list().find(item=>item.sessionIds.includes(p.sessionId))
  if(workspace)await workspace.attachSession(sessionId)
  return {sessionId}
 }finally{observation[Symbol.dispose]()}
}
