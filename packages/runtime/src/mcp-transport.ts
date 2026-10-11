// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {homedir} from 'node:os';
import {join,resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {isJsonRpcRequest,isJsonRpcResponse,McpHttpError,StdioTransport,StreamableHttpTransport,type AuthProvider,type JsonRpcId,type McpFetch} from '@earendil-works/pi-mcp';
import {McpOAuthAuthorizationRequiredError} from '@earendil-works/pi-mcp/oauth';
import type {McpTransportFactory} from '@earendil-works/pi-coding-agent';
import {resolveConfigValueUncached} from '../vendor/pi/config-value.js';
import {MCP_BODY_MAX_BYTES,type McpFailureOriginal} from './mcp-originals.js';
import type {McpAuthorizationObservation} from './mcp-authorization.js';
export type {McpFailureOriginal} from './mcp-originals.js';

const home=(value:string)=>value==='~'?homedir():value.startsWith('~/')||(process.platform==='win32'&&value.startsWith('~\\'))?join(homedir(),value.slice(2)):value;
const configured=(value:string)=>{
 const result=resolveConfigValueUncached(value);
 if(result===undefined)throw Error('A managed MCP configuration value could not be resolved.');
 return result;
};

async function originalBody(response:Response):Promise<McpFailureOriginal['body']>{
 const reader=response.body?.getReader(),chunks:Buffer[]=[];let bytes=0,coverage:McpFailureOriginal['body']['coverage']='complete',reason:string|undefined,timer:ReturnType<typeof setTimeout>|undefined;
 const deadline=new Promise<never>((_,reject)=>{timer=setTimeout(()=>reject(Error('body deadline')),500);});
 try{
  if(reader)for(;;){
   const next=await Promise.race([reader.read(),deadline]);if(next.done)break;
   const remaining=MCP_BODY_MAX_BYTES-bytes,part=Buffer.from(next.value.subarray(0,remaining));chunks.push(part);bytes+=part.length;
   if(next.value.length>remaining){coverage='partial';reason='body exceeds 1 MiB';break;}
  }
 }catch{coverage=bytes?'partial':'unavailable';reason='body read failed or exceeded its deadline';}
 finally{if(timer)clearTimeout(timer);await reader?.cancel().catch(()=>{});}
 const body=Buffer.concat(chunks);
 return {coverage,...(reason?{reason}:{}),retainedBytes:body.length,prefixSha256:createHash('sha256').update(body).digest('hex'),text:body.toString('utf8'),base64:body.toString('base64')};
}

/** Public SDK transport factory. The SDK still owns clients, sessions, OAuth,
 * discovery and tools. A dispatched tool failure cannot authorize another POST.
 */
export const createManagedMcpTransport=(save?:(original:McpFailureOriginal)=>boolean,authorizationObserved?:(event:McpAuthorizationObservation)=>boolean):McpTransportFactory=>(entry,cwd,authProvider)=>{
 const config=entry.config;
 if(!('url' in config))return new StdioTransport({command:home(config.command),args:config.args?.map(home),cwd:resolve(cwd,home(config.cwd??'.')),
  env:Object.fromEntries(Object.entries(config.env??{}).map(([name,value])=>[name,configured(value)])),stderr:'pipe'});
 let transport:StreamableHttpTransport;
 const pending=new Set<JsonRpcId>(),authFailures=new Set<JsonRpcId>(),drains=new Set<()=>void>(),challenged=new Set<Response>();let reset=false,closing=false,closed=false,cancellations=0,failedAdmission=false;
 type AuthBoundary=Omit<McpAuthorizationObservation,'state'|'observedAt'>;
 const boundaries=new WeakMap<Response,AuthBoundary>();
 const observe=(info:AuthBoundary,state:McpAuthorizationObservation['state'])=>{try{authorizationObserved?.({...info,state,observedAt:new Date().toISOString()});}catch{}};
 const active=()=>!closed&&(cancellations>0||[...pending].some(id=>!authFailures.has(id)));
 const release=()=>{
  if(!active()){for(const done of drains)done();drains.clear();}
  if(closed||!reset||pending.size||cancellations||closing)return;
  closing=true;setImmediate(()=>{closing=false;if(!closed&&reset&&!pending.size&&!cancellations){closed=true;void transport.close().catch(()=>{});}});
 };
 const drainAuth=async(id?:JsonRpcId)=>{
  if(id!==undefined)authFailures.add(id);release();
  try{if(active())await new Promise<void>(done=>drains.add(done));}
  finally{if(id!==undefined)authFailures.delete(id);}
 };
 const end=()=>{closed=true;pending.clear();challenged.clear();release();};
 const protectedAuth:AuthProvider|undefined=authProvider?{
  token:()=>authProvider.token(),
  ...(authProvider.onUnauthorized?{onUnauthorized:async(context)=>{
   const info=boundaries.get(context.response);
   try{await authProvider.onUnauthorized!(context);if(info)observe(info,'challenge-handled');challenged.delete(context.response);}
   catch(error){
    if(info){observe(info,error instanceof McpOAuthAuthorizationRequiredError?'sign-in-required':'refresh-failed');reset=true;
     if(info.boundary!=='http-control-response')await drainAuth(info.requestId);}
    if(error instanceof McpOAuthAuthorizationRequiredError)throw new McpOAuthAuthorizationRequiredError();
    throw new McpHttpError(context.response.status,'MCP HTTP response '+context.response.status+'; outcome unknown. Authorization handling failed and this call was not retried.');
   }finally{release();}
  }}:{}),
 }:undefined;
 const guardedFetch:McpFetch=async(input,init)=>{
  let tool=false,frame:any;
  if(init?.method==='POST'&&typeof init.body==='string'){
   try{frame=JSON.parse(init.body);tool=frame?.method==='tools/call';}catch{}
  }
  const response=await fetch(input,tool?{...init,redirect:'manual'}:init);
  const needsAuth=response.status===401||(response.status===403&&/(?:^|[\s,])error="?insufficient_scope"?/i.test(response.headers.get('www-authenticate')??''));
  if(needsAuth&&new URL(input).href===new URL(config.url).href&&(init?.method==='GET'||(init?.method==='POST'&&frame?.jsonrpc==='2.0'))){
   const id=frame?.id,requestId=(typeof id==='string'&&id.length<=256)||(typeof id==='number'&&Number.isSafeInteger(id))?id:undefined;
   const info:AuthBoundary={server:entry.name,status:response.status as 401|403,boundary:tool?'http-tool-response':init?.method==='GET'?'http-get-response':requestId===undefined?'http-control-response':'http-request-response',...(requestId===undefined?{}:{requestId})};
   boundaries.set(response,info);challenged.add(response);observe(info,'challenge-observed');
   // The SDK can close the whole client after a metadata or GET auth error.
   // Keep every already-admitted request alive before handing it that boundary.
   if(!tool&&info.boundary!=='http-control-response'){await drainAuth(requestId);reset=true;release();}
  }
  if(!tool||response.ok)return response;
  failedAdmission=true;
  const body=await originalBody(response);let saved=false;
  try{saved=save?.({server:entry.name,requestId:frame.id,method:'tools/call',params:frame.params,status:response.status,contentType:response.headers.get('content-type'),body})===true;}catch{}
  try{
   const challenge=response.headers.get('www-authenticate')??'';
   if(protectedAuth?.onUnauthorized&&(response.status===401||(response.status===403&&/(?:^|[\s,])error="?insufficient_scope"?/i.test(challenge)))){
    // Preserve SDK credential refresh/challenge handling, but never let the
    // transport resend this dispatched call after refreshing those credentials.
    const authorization=new Headers(init?.headers).get('authorization');
    try{await protectedAuth.onUnauthorized({response,serverUrl:new URL(config.url),fetch:guardedFetch,
     token:authorization?.match(/^Bearer (.*)$/i)?.[1]});}catch(error){
      if(error instanceof McpHttpError&&!saved)throw new McpHttpError(response.status,error.message+' Original HTTP evidence could not be saved.');
      throw error;
     }}
   throw new McpHttpError(response.status,'MCP tool response HTTP '+response.status+'; outcome unknown. This call was not retried. Inspect the outcome before another action.'+(!saved?' Original HTTP evidence could not be saved.':''));
  }finally{
   await response.body?.cancel().catch(()=>{});
   reset=true;release();
  }
 };
 transport=new StreamableHttpTransport({url:config.url,headers:config.headers?Object.fromEntries(Object.entries(config.headers).map(([name,value])=>[name,configured(value)])):undefined,authProvider:protectedAuth,fetch:guardedFetch});
 // Keep concurrent receipts, including asynchronous SSE replies, alive until
 // their SDK requests settle. SDK cancellation removes a timed-out request.
 transport.onMessage(message=>{if(isJsonRpcResponse(message)){pending.delete(message.id);release();}});
 transport.onClose(end);
 return {
  start:()=>transport.start(),close:()=>{end();return transport.close();},setProtocolVersion:version=>transport.setProtocolVersion(version),
  onMessage:listener=>transport.onMessage(listener),onError:listener=>transport.onError(listener),onClose:listener=>transport.onClose(listener),
  async send(message){
   const request=isJsonRpcRequest(message),tool=request&&message.method==='tools/call';
   const cancellation='method' in message&&message.method==='notifications/cancelled';
   if(tool&&!closed&&(failedAdmission||reset||challenged.size||drains.size))throw new McpHttpError(challenged.size?401:409,'MCP tool call was not dispatched: the connection is settling a failed request or authorization challenge. Inspect the outcome before an explicit retry.');
   if(request)pending.add(message.id);
   if(cancellation){
    cancellations++;
    const params=message.params,id=params&&typeof params==='object'&&'requestId' in params?params.requestId:undefined;
    if(typeof id==='string'||typeof id==='number'){pending.delete(id);release();}
   }
   try{await transport.send(message);}catch(error){if(request)pending.delete(message.id);throw error;}finally{if(cancellation)cancellations--;release();}
  },
 };
};
export const managedMcpTransport=createManagedMcpTransport();
