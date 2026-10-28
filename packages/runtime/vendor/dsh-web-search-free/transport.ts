// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {AsyncLocalStorage} from 'node:async_hooks';
export type SearchTransport=typeof globalThis.fetch;
type Scope={signal:AbortSignal;transport:SearchTransport;origins:string[];limit:AbortController};
const scopes=new AsyncLocalStorage<Scope>();
const origins=new Set(['https://api.anysearch.com','https://api.search.brave.com','https://api.exa.ai','https://api.firecrawl.dev','https://s.jina.ai','https://r.jina.ai','https://serpapi.com','https://api.serpingapi.com','https://api.tavily.com','https://api.search.tinyfish.ai','https://api.fetch.tinyfish.ai']);
export async function withSearchTransport<T>(scope:Scope,run:()=>Promise<T>){return scopes.run(scope,run);}
export const providerFetch:SearchTransport=async(input,init)=>{
 const scope=scopes.getStore();if(!scope)throw Error('Search requires an admitted request-local transport.');scope.signal.throwIfAborted();
 const url=new URL(typeof input==='string'?input:input instanceof URL?input.href:input.url);
 if(!origins.has(url.origin)||url.username||url.password)throw Error('Unexpected search provider endpoint.');
 if(scope.origins.length>=32){scope.limit.abort();scope.signal.throwIfAborted();}
 scope.origins.push(url.origin);
 const response=await scope.transport(input,{...init,signal:scope.signal,redirect:'error'});
 scope.signal.throwIfAborted();
 if(Number(response.headers.get('content-length')??0)>8*1024*1024){await response.body?.cancel();throw Error('Search provider response exceeds its bound.');}
 const reader=response.body?.getReader();let total=0;
 const body=reader?new ReadableStream<Uint8Array>({async pull(controller){try{scope.signal.throwIfAborted();const next=await reader.read();scope.signal.throwIfAborted();if(next.done){controller.close();return;}total+=next.value.byteLength;if(total>8*1024*1024){await reader.cancel();throw Error('Search provider response exceeds its bound.');}controller.enqueue(next.value);}catch(error){controller.error(error);await reader.cancel().catch(()=>{});}},cancel(reason){return reader.cancel(reason);}}):null;
 return new Response(body,{status:response.status,statusText:response.statusText,headers:response.headers});
};
