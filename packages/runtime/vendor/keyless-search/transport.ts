// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {AsyncLocalStorage} from 'node:async_hooks';
import {publicHttpNetwork} from '../dsh-keyless-fetch/network.js';
import {parseFetchUrl} from '../dsh-keyless-fetch/policy.js';
const MAX=2*1024*1024;
export type KeylessNetwork=typeof publicHttpNetwork;
export interface KeylessRequest {signal:AbortSignal;limit:AbortController;origins:string[];allowedOrigins:string[];blockedDomains:string[];network:KeylessNetwork;timeoutMs:number}
const requests=new AsyncLocalStorage<KeylessRequest>();
export function withKeylessTransport<T>(context:KeylessRequest,run:()=>Promise<T>){return requests.run(context,run);}
export function searchDomainRules(){return [...(requests.getStore()?.blockedDomains??[])];}
/** Per-hop public-address pinning; no global fetch/proxy/cookie mutation. */
export async function keylessProviderFetch(input:string|URL,init:RequestInit={}):Promise<Response>{
 const ctx=requests.getStore();if(!ctx)throw Error('A keyless request scope is required.');
 const signal=AbortSignal.any([ctx.signal,...(init.signal?[init.signal]:[]),AbortSignal.timeout(ctx.timeoutMs)]);
 let url=parseFetchUrl(String(input)),hops=0;const method=init.method??'GET',body=typeof init.body==='string'?init.body:undefined,headers=Object.fromEntries(new Headers(init.headers));
 if(!['GET','POST'].includes(method)||init.body!==undefined&&typeof init.body!=='string'||body&&Buffer.byteLength(body)>65536||Object.keys(headers).some(name=>!['user-agent','accept-language','accept','content-type','x-tavily-access-mode'].includes(name)))throw Error('Invalid keyless request shape.');
 for(;;){
  signal.throwIfAborted();if(!ctx.allowedOrigins.includes(url.origin))throw Error('The keyless engine origin is not configured.');if(ctx.origins.length>=32){ctx.limit.abort();throw Error('Keyless request budget reached.');}ctx.origins.push(url.origin);
  const addresses=await ctx.network.resolve(url.hostname,signal);signal.throwIfAborted();const {response,close}=await ctx.network.request(url,addresses,headers,signal,{method,body});
  try{
   if([301,302,303,307,308].includes(response.status)){await response.body?.cancel();if(++hops>5||method!=='GET'||!response.headers.get('location'))throw Error('Keyless redirect is unavailable.');url=parseFetchUrl(new URL(response.headers.get('location')!,url).href);continue;}
   const declared=response.headers.get('content-length');if(declared!==null&&Number(declared)>MAX){await response.body?.cancel();throw Error('Keyless engine response exceeds its bound.');}
   const reader=response.body?.getReader(),parts:Uint8Array[]=[];let size=0;
   try{if(reader)for(;;){signal.throwIfAborted();const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>MAX)throw Error('Keyless engine response exceeds its bound.');parts.push(value);}}finally{await reader?.cancel().catch(()=>{});}
   const bytes=Buffer.concat(parts,size);return new Response([204,205,304].includes(response.status)?null:bytes,{status:response.status,headers:new Headers(response.headers as any)});
  }finally{await close();}
 }
}
