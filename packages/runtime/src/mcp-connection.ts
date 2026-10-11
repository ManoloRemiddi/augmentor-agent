// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {randomUUID} from 'node:crypto';
import {isJsonRpcRequest,isJsonRpcResponse,type JsonRpcId,type McpTransport} from '@earendil-works/pi-mcp';

export const MCP_CONNECTION_TYPE='augmentor-mcp-connection/1';
const events=new Set(['created','starting','transport-started','start-failed','initialize-sent','initialize-response','protocol-negotiated','initialized-notification-sent','metadata-response','rpc-error-response','send-failed','request-cancelled','transport-error','close-requested','closed','authorization-challenge','authorization-handled','sign-in-required','refresh-failed','token-provider-failed','tracking-limit']);
const methods=new Set(['initialize','tools/list','resources/list','resources/templates/list','resources/read','tools/call']);
export interface McpConnectionObservation {
 server:string;instanceId:string;sequence:number;transport:'http'|'stdio';event:string;observedAt:string;
 method?:string;requestId?:JsonRpcId;requestAlreadyDispatched?:boolean;
}
/** Whitelist native metadata. Never retain result/error bodies, credentials,
 * configured endpoints/commands or supplier messages as connection status.
 */
export function savedMcpConnection(value:unknown):McpConnectionObservation|undefined{
 if(!value||typeof value!=='object')return;const row=value as McpConnectionObservation;
 if(typeof row.server!=='string'||!/^[-a-zA-Z0-9_]{1,128}$/.test(row.server)||typeof row.instanceId!=='string'||!(/^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/).test(row.instanceId)||!Number.isSafeInteger(row.sequence)||row.sequence<0||!['http','stdio'].includes(row.transport)||!events.has(row.event)||
  typeof row.observedAt!=='string'||row.observedAt.length!==24||!Number.isFinite(Date.parse(row.observedAt))||new Date(row.observedAt).toISOString()!==row.observedAt||
  row.method!==undefined&&!methods.has(row.method)||row.requestId!==undefined&&!((typeof row.requestId==='string'&&row.requestId.length<=256)||(typeof row.requestId==='number'&&Number.isSafeInteger(row.requestId)))||row.requestAlreadyDispatched!==undefined&&typeof row.requestAlreadyDispatched!=='boolean')return;
 return {server:row.server,instanceId:row.instanceId,sequence:row.sequence,transport:row.transport,event:row.event,observedAt:row.observedAt,...(row.method===undefined?{}:{method:row.method}),...(row.requestId===undefined?{}:{requestId:row.requestId}),...(row.requestAlreadyDispatched===undefined?{}:{requestAlreadyDispatched:row.requestAlreadyDispatched})};
}
export interface McpConnectionSummary {instanceId:string;transport:'http'|'stdio';state:string;lastObservation:McpConnectionObservation;lastProblem?:McpConnectionObservation;protocolNegotiated:boolean;closed:boolean;trackingGap:boolean;}
export function connectionSummary(previous:McpConnectionSummary|undefined,row:McpConnectionObservation):McpConnectionSummary{
 const same=previous?.instanceId===row.instanceId;if(same&&row.sequence<=previous.lastObservation.sequence)return previous;
 const closed=(same&&previous.closed)||row.event==='closed';
 const cause=same?previous.lastProblem:undefined,preserveCause=row.event==='send-failed'&&row.requestId!==undefined&&cause?.requestId===row.requestId&&['token-provider-failed','sign-in-required','refresh-failed','authorization-challenge'].includes(cause.event);
 const lastProblem=preserveCause?cause:['start-failed','rpc-error-response','send-failed','transport-error','authorization-challenge','sign-in-required','refresh-failed','token-provider-failed'].includes(row.event)?row:cause;
 return {instanceId:row.instanceId,transport:row.transport,state:closed?'closed':row.event,lastObservation:{...row},...(lastProblem?{lastProblem:{...lastProblem}}:{}),protocolNegotiated:row.event==='protocol-negotiated'||!!(same&&previous.protocolNegotiated),closed,trackingGap:row.event==='tracking-limit'||!!(same&&previous.trackingGap)};
}
/** Observes only public transport methods/listeners. Its Proxy preserves public
 * transport properties and binds supplier methods to the original receiver.
 */
export class McpConnectionObserver {
 private sequence=0;
 private instanceId=randomUUID();
 private metadata=new Map<JsonRpcId,string>();
 constructor(private server:string,private transport:'http'|'stdio',private changed?:(row:McpConnectionObservation)=>void){this.record('created');}
 record(event:string,details:Pick<McpConnectionObservation,'method'|'requestId'|'requestAlreadyDispatched'>={}){
  const row=savedMcpConnection({server:this.server,instanceId:this.instanceId,sequence:this.sequence++,transport:this.transport,event,observedAt:new Date().toISOString(),...details,...(details.method&&!methods.has(details.method)?{method:undefined}:{})});
  if(row)try{this.changed?.(row);}catch{}
 }
 wrap<T extends McpTransport>(transport:T):T{
  transport.onError(()=>this.record('transport-error'));transport.onClose(()=>{this.metadata.clear();this.record('closed');});
  transport.onMessage(message=>{
   if(!isJsonRpcResponse(message))return;const method=this.metadata.get(message.id);if(!method)return;this.metadata.delete(message.id);
   this.record('error' in message?'rpc-error-response':method==='initialize'?'initialize-response':'metadata-response',{method,requestId:message.id});
  });
  return new Proxy(transport,{get:(target,key)=>{
   if(key==='start')return async()=>{this.record('starting');try{await target.start();this.record('transport-started');}catch(error){this.record('start-failed');throw error;}};
   if(key==='close')return async()=>{this.record('close-requested');await target.close();};
   if(key==='setProtocolVersion')return (version:string)=>{target.setProtocolVersion?.(version);this.record('protocol-negotiated');};
   if(key==='send')return async(message:Parameters<McpTransport['send']>[0])=>{
    const request=isJsonRpcRequest(message),method='method' in message&&methods.has(message.method)?message.method:undefined;
    if('method' in message&&message.method==='notifications/cancelled'){
     const params=message.params,id=params&&typeof params==='object'&&'requestId' in params?params.requestId:undefined;if(typeof id==='string'||typeof id==='number'){const cancelled=this.metadata.get(id);this.metadata.delete(id);if(cancelled)this.record('request-cancelled',{method:cancelled,requestId:id});}
    }
    if(request&&method&&method!=='tools/call'){
     if(this.metadata.size<256)this.metadata.set(message.id,method);else this.record('tracking-limit');
     if(method==='initialize')this.record('initialize-sent',{method,requestId:message.id});
    }
    try{await target.send(message);if('method' in message&&message.method==='notifications/initialized')this.record('initialized-notification-sent');}
    catch(error){if(request)this.metadata.delete(message.id);this.record('send-failed',{...(method?{method}:{}),...(request?{requestId:message.id}:{})});throw error;}
   };
   const value=Reflect.get(target,key);return typeof value==='function'?value.bind(target):value;
  }});
 }
}
