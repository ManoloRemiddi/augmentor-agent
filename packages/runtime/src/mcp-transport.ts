// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {homedir} from 'node:os';
import {join,resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {isJsonRpcRequest,isJsonRpcResponse,McpHttpError,StdioTransport,StreamableHttpTransport,type JsonRpcId,type McpFetch} from '@earendil-works/pi-mcp';
import type {McpTransportFactory} from '@earendil-works/pi-coding-agent';
import {resolveConfigValueUncached} from '../vendor/pi/config-value.js';
import {MCP_BODY_MAX_BYTES,type McpFailureOriginal} from './mcp-originals.js';
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
export const createManagedMcpTransport=(save?:(original:McpFailureOriginal)=>boolean):McpTransportFactory=>(entry,cwd,authProvider)=>{
 const config=entry.config;
 if(!('url' in config))return new StdioTransport({command:home(config.command),args:config.args?.map(home),cwd:resolve(cwd,home(config.cwd??'.')),
  env:Object.fromEntries(Object.entries(config.env??{}).map(([name,value])=>[name,configured(value)])),stderr:'pipe'});
 let transport:StreamableHttpTransport;
 const pending=new Set<JsonRpcId>();let reset=false,closing=false;
 const release=()=>{
  if(!reset||pending.size||closing)return;
  closing=true;setImmediate(()=>{closing=false;if(reset&&!pending.size)void transport.close().catch(()=>{});});
 };
 const guardedFetch:McpFetch=async(input,init)=>{
  let tool=false,frame:any;
  if(init?.method==='POST'&&typeof init.body==='string'){
   try{frame=JSON.parse(init.body);tool=frame?.method==='tools/call';}catch{}
  }
  const response=await fetch(input,tool?{...init,redirect:'manual'}:init);
  if(!tool||response.ok)return response;
  const body=await originalBody(response);let saved=false;
  try{saved=save?.({server:entry.name,requestId:frame.id,method:'tools/call',params:frame.params,status:response.status,contentType:response.headers.get('content-type'),body})===true;}catch{}
  try{
   const challenge=response.headers.get('www-authenticate')??'';
   if(authProvider?.onUnauthorized&&(response.status===401||(response.status===403&&/(?:^|[\s,])error="?insufficient_scope"?/i.test(challenge)))){
    // Preserve SDK credential refresh/challenge handling, but never let the
    // transport resend this dispatched call after refreshing those credentials.
    const authorization=new Headers(init?.headers).get('authorization');
    await authProvider.onUnauthorized({response,serverUrl:new URL(config.url),fetch:guardedFetch,
     token:authorization?.match(/^Bearer (.*)$/i)?.[1]});
   }
   throw new McpHttpError(response.status,'MCP tool response HTTP '+response.status+'; outcome unknown. This call was not retried. Inspect the outcome before another action.'+(!saved?' Original HTTP evidence could not be saved.':''));
  }finally{
   await response.body?.cancel().catch(()=>{});
   reset=true;release();
  }
 };
 transport=new StreamableHttpTransport({url:config.url,headers:config.headers?Object.fromEntries(Object.entries(config.headers).map(([name,value])=>[name,configured(value)])):undefined,authProvider,fetch:guardedFetch});
 // Keep concurrent receipts, including asynchronous SSE replies, alive until
 // their SDK requests settle. SDK cancellation removes a timed-out request.
 transport.onMessage(message=>{if(isJsonRpcResponse(message)){pending.delete(message.id);release();}});
 return {
  start:()=>transport.start(),close:()=>transport.close(),setProtocolVersion:version=>transport.setProtocolVersion(version),
  onMessage:listener=>transport.onMessage(listener),onError:listener=>transport.onError(listener),onClose:listener=>transport.onClose(listener),
  async send(message){
   const tool=isJsonRpcRequest(message)&&message.method==='tools/call';
   if(tool)pending.add(message.id);
   if('method' in message&&message.method==='notifications/cancelled'){
    const params=message.params,id=params&&typeof params==='object'&&'requestId' in params?params.requestId:undefined;
    if(typeof id==='string'||typeof id==='number')pending.delete(id);
   }
   try{await transport.send(message);}catch(error){if(tool)pending.delete(message.id);throw error;}finally{release();}
  },
 };
};
export const managedMcpTransport=createManagedMcpTransport();
