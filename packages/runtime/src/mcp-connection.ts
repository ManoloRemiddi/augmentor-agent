// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {randomUUID} from 'node:crypto';
import {isJsonRpcRequest,isJsonRpcResponse,type JsonRpcId,type McpTransport} from '@earendil-works/pi-mcp';
import {savedMcpAgentCall,type McpAgentCall} from './mcp-call-context.js';

export const MCP_CONNECTION_TYPE='augmentor-mcp-connection/1';
const events=new Set(['created','starting','transport-started','start-failed','initialize-sent','initialize-response','protocol-negotiated','initialized-notification-sent','metadata-response','rpc-error-response','tool-send-started','tool-send-settled','tool-response','tool-error-response','send-failed','request-cancelled','transport-error','close-requested','closed','authorization-challenge','authorization-handled','sign-in-required','refresh-failed','token-provider-failed','tracking-limit','tracking-collision']);
const methods=new Set(['initialize','tools/list','resources/list','resources/templates/list','resources/read','tools/call']);
const callEvents=new Set(['tool-send-started','tool-send-settled','tool-response','tool-error-response','send-failed','request-cancelled','authorization-challenge','authorization-handled','sign-in-required','refresh-failed','token-provider-failed']);
export interface McpConnectionObservation {
 server:string;instanceId:string;sequence:number;transport:'http'|'stdio';event:string;observedAt:string;
 method?:string;requestId?:JsonRpcId;requestAlreadyDispatched?:boolean;
 agentCall?:McpAgentCall;
}
/** Whitelist native metadata. Never retain result/error bodies, credentials,
 * configured endpoints/commands or supplier messages as connection status.
 */
export function savedMcpConnection(value:unknown):McpConnectionObservation|undefined{
 if(!value||typeof value!=='object')return;const row=value as McpConnectionObservation;
 if(typeof row.server!=='string'||!/^[-a-zA-Z0-9_]{1,128}$/.test(row.server)||typeof row.instanceId!=='string'||!(/^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/).test(row.instanceId)||!Number.isSafeInteger(row.sequence)||row.sequence<0||!['http','stdio'].includes(row.transport)||!events.has(row.event)||
  typeof row.observedAt!=='string'||row.observedAt.length!==24||!Number.isFinite(Date.parse(row.observedAt))||new Date(row.observedAt).toISOString()!==row.observedAt||
  row.method!==undefined&&!methods.has(row.method)||row.requestId!==undefined&&!((typeof row.requestId==='string'&&row.requestId.length<=256)||(typeof row.requestId==='number'&&Number.isSafeInteger(row.requestId)))||row.requestAlreadyDispatched!==undefined&&typeof row.requestAlreadyDispatched!=='boolean')return;
 const agentCall=row.agentCall===undefined?undefined:savedMcpAgentCall(row.agentCall);if(row.agentCall!==undefined&&(!agentCall||row.requestId===undefined||row.method!==undefined&&row.method!=='tools/call'||!callEvents.has(row.event)||!agentCall.toolName.startsWith('mcp__'+row.server.replaceAll('-','_')+'__')))return;
 return {server:row.server,instanceId:row.instanceId,sequence:row.sequence,transport:row.transport,event:row.event,observedAt:row.observedAt,...(row.method===undefined?{}:{method:row.method}),...(row.requestId===undefined?{}:{requestId:row.requestId}),...(row.requestAlreadyDispatched===undefined?{}:{requestAlreadyDispatched:row.requestAlreadyDispatched}),...(agentCall?{agentCall}:{})};
}
export interface McpConnectionSummary {instanceId:string;transport:'http'|'stdio';state:string;lastObservation:McpConnectionObservation;lastProblem?:McpConnectionObservation;protocolNegotiated:boolean;closed:boolean;trackingGap:boolean;}
export function connectionSummary(previous:McpConnectionSummary|undefined,row:McpConnectionObservation):McpConnectionSummary{
 const same=previous?.instanceId===row.instanceId;if(same&&row.sequence<=previous.lastObservation.sequence)return previous;
 const closed=(same&&previous.closed)||row.event==='closed';
 const cause=same?previous.lastProblem:undefined,preserveCause=row.event==='send-failed'&&row.requestId!==undefined&&cause?.requestId===row.requestId&&['token-provider-failed','sign-in-required','refresh-failed','authorization-challenge'].includes(cause.event);
 const lastProblem=preserveCause?cause:['start-failed','rpc-error-response','tool-error-response','send-failed','transport-error','authorization-challenge','sign-in-required','refresh-failed','token-provider-failed'].includes(row.event)?row:cause;
 return {instanceId:row.instanceId,transport:row.transport,state:closed?'closed':row.event,lastObservation:{...row},...(lastProblem?{lastProblem:{...lastProblem}}:{}),protocolNegotiated:row.event==='protocol-negotiated'||!!(same&&previous.protocolNegotiated),closed,trackingGap:['tracking-limit','tracking-collision'].includes(row.event)||!!(same&&previous.trackingGap)};
}
/** Observes only public transport methods/listeners. Its Proxy preserves public
 * transport properties and binds supplier methods to the original receiver.
 */
export class McpConnectionObserver {
 private sequence=0;
 private instanceId=randomUUID();
 private metadata=new Map<JsonRpcId,{method:string;agentCall?:McpAgentCall}>();
 private ambiguous=new Set<JsonRpcId>();
 constructor(private server:string,private transport:'http'|'stdio',private changed?:(row:McpConnectionObservation)=>void,private currentToolCall?:()=>McpAgentCall|undefined){this.record('created');}
 callFor(id:JsonRpcId){return savedMcpAgentCall(this.metadata.get(id)?.agentCall);}
 record(event:string,details:Pick<McpConnectionObservation,'method'|'requestId'|'requestAlreadyDispatched'|'agentCall'>={}){
  const agentCall=details.agentCall??(details.requestId===undefined?undefined:this.callFor(details.requestId));
  const row=savedMcpConnection({server:this.server,instanceId:this.instanceId,sequence:this.sequence++,transport:this.transport,event,observedAt:new Date().toISOString(),...details,...(agentCall?{agentCall}:{}),...(details.method&&!methods.has(details.method)?{method:undefined}:{})});
  if(row)try{this.changed?.(row);}catch{}
 }
 wrap<T extends McpTransport>(transport:T):T{
  transport.onError(()=>this.record('transport-error'));transport.onClose(()=>{this.metadata.clear();this.ambiguous.clear();this.record('closed');});
  transport.onMessage(message=>{
   if(!isJsonRpcResponse(message))return;const pending=this.metadata.get(message.id);if(!pending)return;
   this.record(pending.method==='tools/call'?('error' in message?'tool-error-response':'tool-response'):'error' in message?'rpc-error-response':pending.method==='initialize'?'initialize-response':'metadata-response',{method:pending.method,requestId:message.id});this.metadata.delete(message.id);
  });
  return new Proxy(transport,{get:(target,key)=>{
   if(key==='start')return async()=>{this.record('starting');try{await target.start();this.record('transport-started');}catch(error){this.record('start-failed');throw error;}};
   if(key==='close')return async()=>{this.record('close-requested');await target.close();};
   if(key==='setProtocolVersion')return (version:string)=>{target.setProtocolVersion?.(version);this.record('protocol-negotiated');};
   if(key==='send')return async(message:Parameters<McpTransport['send']>[0])=>{
    const request=isJsonRpcRequest(message),method='method' in message&&methods.has(message.method)?message.method:undefined;
    if('method' in message&&message.method==='notifications/cancelled'){
     const params=message.params,id=params&&typeof params==='object'&&'requestId' in params?params.requestId:undefined;if(typeof id==='string'||typeof id==='number'){const cancelled=this.metadata.get(id);if(cancelled)this.record('request-cancelled',{method:cancelled.method,requestId:id});this.metadata.delete(id);}
    }
    let agentCall:McpAgentCall|undefined;if(request&&method==='tools/call')try{agentCall=savedMcpAgentCall(this.currentToolCall?.());}catch{}
    if(request&&method){
     if(this.metadata.has(message.id)||this.ambiguous.has(message.id)){this.metadata.delete(message.id);this.ambiguous.add(message.id);agentCall=undefined;this.record('tracking-collision');}
     else if(this.metadata.size+this.ambiguous.size<256)this.metadata.set(message.id,{method,...(agentCall?{agentCall}:{})});else this.record('tracking-limit');
     if(method==='initialize')this.record('initialize-sent',{method,requestId:message.id});
     if(method==='tools/call')this.record('tool-send-started',{method,requestId:message.id,...(agentCall?{agentCall}:{})});
    }
    try{await target.send(message);if('method' in message&&message.method==='notifications/initialized')this.record('initialized-notification-sent');if(request&&method==='tools/call')this.record('tool-send-settled',{method,requestId:message.id,...(agentCall&&!this.ambiguous.has(message.id)?{agentCall}:{})});}
    catch(error){this.record('send-failed',{...(method?{method}:{}),...(request?{requestId:message.id}:{}),...(agentCall&&(!request||!this.ambiguous.has(message.id))?{agentCall}:{})});if(request)this.metadata.delete(message.id);throw error;}
   };
   const value=Reflect.get(target,key);return typeof value==='function'?value.bind(target):value;
  }});
 }
}
