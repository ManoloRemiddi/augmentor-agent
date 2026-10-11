// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {AsyncLocalStorage} from 'node:async_hooks';
import {randomUUID} from 'node:crypto';
import type {ExtensionAPI,ToolDefinition} from '@earendil-works/pi-coding-agent';

/** Public execution identity. Transport request IDs remain a separate domain. */
export interface McpAgentCall {
 operationId:string;sessionId:string;nativeSessionId:string;branchLeafId:string|null;
 toolName:string;toolCallId:string;parentToolCallId?:string;parentCoverage:'observed'|'unavailable';
 hostTurnId?:string;hostRequestId?:string;modelRequestObservationId?:string;
}
const id=(value:unknown)=>typeof value==='string'&&value.length>0&&value.length<=256&&!/[\u0000-\u001f\u007f]/.test(value);
const uuid=(value:unknown)=>typeof value==='string'&&/^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/.test(value);
/** Admit only bounded identity metadata, never arguments, URLs or credentials. */
export function savedMcpAgentCall(value:unknown):McpAgentCall|undefined{
 if(!value||typeof value!=='object')return;const row=value as McpAgentCall;
 if(!uuid(row.operationId)||!id(row.sessionId)||!id(row.nativeSessionId)||row.branchLeafId!==null&&!id(row.branchLeafId)||
  !id(row.toolName)||!/^mcp__[a-zA-Z0-9_]+$/.test(row.toolName)||!id(row.toolCallId)||!['observed','unavailable'].includes(row.parentCoverage)||
  row.parentToolCallId!==undefined&&(!id(row.parentToolCallId)||row.parentCoverage!=='observed')||
  row.hostTurnId!==undefined&&!id(row.hostTurnId)||row.hostRequestId!==undefined&&!id(row.hostRequestId)||row.modelRequestObservationId!==undefined&&!id(row.modelRequestObservationId))return;
 return {operationId:row.operationId,sessionId:row.sessionId,nativeSessionId:row.nativeSessionId,branchLeafId:row.branchLeafId,toolName:row.toolName,toolCallId:row.toolCallId,parentCoverage:row.parentCoverage,
  ...(row.parentToolCallId===undefined?{}:{parentToolCallId:row.parentToolCallId}),...(row.hostTurnId===undefined?{}:{hostTurnId:row.hostTurnId}),...(row.hostRequestId===undefined?{}:{hostRequestId:row.hostRequestId}),...(row.modelRequestObservationId===undefined?{}:{modelRequestObservationId:row.modelRequestObservationId})};
}
/** Compose public ToolDefinition.execute at managed registration. Async-local
 * scope follows only this invocation, including parallel nested calls. A public
 * tool_call event supplies parent identity; never derive it by parsing an ID.
 */
export class McpCallContext {
 private scope=new AsyncLocalStorage<{namespace:string;call:McpAgentCall}>();
 private prepared=new Map<string,{toolName:string;parentToolCallId?:string;ambiguous?:boolean}>();
 private active=new Map<string,{count:number;ambiguous:boolean}>();
 private finished=new Map<string,McpAgentCall>();
 private dropped=0;private unlinked=0;
 constructor(private sessionId:string,private owner?:()=>{hostTurnId?:string;hostRequestId?:string;modelRequestObservationId?:string}){}
 observe(pi:ExtensionAPI){
  pi.on('tool_call',event=>{if(!event.toolName.startsWith('mcp__'))return;
   if(!this.prepared.has(event.toolCallId)&&this.prepared.size>=256){this.dropped++;return;}
   const ambiguous=this.prepared.has(event.toolCallId);this.prepared.set(event.toolCallId,{toolName:event.toolName,...(event.parentToolCallId===undefined?{}:{parentToolCallId:event.parentToolCallId}),...(ambiguous?{ambiguous:true}:{})});
  });
  pi.on('tool_result',event=>{this.prepared.delete(event.toolCallId);this.finished.delete(event.toolCallId);});
  pi.on('session_shutdown',()=>{this.prepared.clear();this.finished.clear();});
 }
 wrap<T extends ToolDefinition<any,any,any>>(definition:T):T{
  const namespace=definition.namespace?.name;if(!namespace?.startsWith('mcp__'))return definition;
  const context=this;
  return {...definition,execute:async function(toolCallId,params,signal,onUpdate,ctx){
   const prepared=context.prepared.get(toolCallId);context.prepared.delete(toolCallId);
   const unsettledResult=context.finished.has(toolCallId);context.finished.delete(toolCallId);
   let call:McpAgentCall|undefined;
   try{call=savedMcpAgentCall({operationId:randomUUID(),sessionId:context.sessionId,nativeSessionId:ctx.sessionManager.getSessionId(),branchLeafId:ctx.sessionManager.getLeafId(),
    toolName:definition.name,toolCallId,parentCoverage:prepared?.toolName===definition.name&&!prepared.ambiguous?'observed':'unavailable',
    ...(prepared?.toolName===definition.name&&!prepared.ambiguous&&prepared.parentToolCallId!==undefined?{parentToolCallId:prepared.parentToolCallId}:{}),...context.owner?.()});}catch{}
   if(!call){context.unlinked++;return definition.execute.call(definition,toolCallId,params,signal,onUpdate,ctx);}
   let active=context.active.get(toolCallId);if(active){active.count++;active.ambiguous=true;}else if(context.active.size<256){active={count:1,ambiguous:unsettledResult};context.active.set(toolCallId,active);}
   try{return await context.scope.run({namespace,call:Object.freeze(call)},()=>definition.execute.call(definition,toolCallId,params,signal,onUpdate,ctx));}
   finally{if(active){active.count--;if(!active.count)context.active.delete(toolCallId);if(!active.ambiguous&&context.finished.size<256)context.finished.set(toolCallId,call);else context.unlinked++;}else context.unlinked++;}
  }};
 }
 takeResult(toolCallId:string,toolName:string){const call=this.finished.get(toolCallId);this.finished.delete(toolCallId);return call?.toolName===toolName?savedMcpAgentCall(call):undefined;}
 current(server:string){const current=this.scope.getStore();return current?.namespace==='mcp__'+server.replaceAll('-','_')?savedMcpAgentCall(current.call):undefined;}
 describe(){return {boundary:'public managed ToolDefinition.execute to public transport send and pre-hook result',preparedLimit:256,resultLimit:256,droppedPreparations:this.dropped,unlinkedBoundaries:this.unlinked};}
}
