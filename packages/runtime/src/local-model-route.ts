// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import type {AgentSession} from '@earendil-works/pi-coding-agent';
import {createAssistantMessageEventStream,createAssistantMessageDiagnostic,type Model,type Api,type AssistantMessage} from '@earendil-works/pi-ai';

const MAX_METADATA_BYTES=1024*1024;
const DIAGNOSTIC='augmentor.local-model-route';
export function localModelRouteFailure(message:AssistantMessage){const reason=message.diagnostics?.find(row=>row.type===DIAGNOSTIC)?.error?.message;return message.stopReason==='error'&&reason?.startsWith('Local model route:')?reason.slice(0,1024):undefined;}
const installed=new WeakSet<AgentSession>();
export function localModelRouteProviders(){return [...new Set((process.env.AUGMENTOR_PI_LLAMA_CPP_PROVIDERS??'').split(',').map(s=>s.trim()).filter(Boolean))];}
function refuse(message:string):never{throw Error('Local model route: '+message);}
const object=(v:unknown):v is Record<string,unknown>=>!!v&&typeof v==='object'&&!Array.isArray(v);

/** A metadata check, not an attestation of weights or a model-loading operation.
 * Use the actual SDK fetch URL and assembled authentication, with no second
 * credential resolution and no prompt body sent to the metadata endpoint. */
async function advertised(input:Parameters<typeof fetch>[0],init:Parameters<typeof fetch>[1],model:Model<Api>,transport:typeof fetch,signal?:AbortSignal){
 const request=input instanceof Request?input:undefined;
 let url:URL;try{url=new URL(request?request.url:String(input));}catch{refuse('The configured server URL cannot be verified. Check the local provider settings.');}
 if(!['http:','https:'].includes(url.protocol)||url.username||url.password||!(url.pathname.endsWith('/chat/completions'))||(init?.method??request?.method??'GET').toUpperCase()!=='POST')refuse('This local server does not use the supported chat-completions endpoint. Check its provider settings.');
 url.pathname=url.pathname.slice(0,-'/chat/completions'.length)+'/models';url.hash='';
 const headers=new Headers(init?.headers??request?.headers);headers.delete('content-length');headers.delete('content-type');headers.set('accept','application/json');
 const original=init?.signal??request?.signal??signal;
 const bounded=AbortSignal.any([...(original?[original]:[]),AbortSignal.timeout(5000)]);
 let response:Response|undefined;
 try{
  response=await transport(url,{method:'GET',headers,signal:bounded,redirect:'error'});
  if(!response.ok||response.redirected)refuse('The server could not confirm its models. Check that the matching local server is running and its credentials are valid.');
  if(Number(response.headers.get('content-length'))>MAX_METADATA_BYTES)refuse('The server model list exceeds the verification bound.');
  if(!response.body)refuse('The server returned no model list.');
  const reader=response.body.getReader(),parts:Uint8Array[]=[];let bytes=0;
  try{while(true){const part=await reader.read();if(part.done)break;bytes+=part.value.byteLength;if(bytes>MAX_METADATA_BYTES)refuse('The server model list exceeds the verification bound.');parts.push(part.value);}}finally{await reader.cancel().catch(()=>{});reader.releaseLock();}
  const raw=new Uint8Array(bytes);let offset=0;for(const part of parts){raw.set(part,offset);offset+=part.byteLength;}
  let value:unknown;try{value=JSON.parse(new TextDecoder().decode(raw));}catch{refuse('The server returned an invalid model list.');}
  if(!object(value)||!Array.isArray(value.data)||value.data.length>10000||value.data.some(row=>!object(row)||typeof row.id!=='string'||!row.id||row.id.length>4096))refuse('The server returned an invalid model list.');
  if(!value.data.some(row=>row.id===model.id))refuse('The selected model is not advertised by this server. Load the matching profile in AI Model Manager, or select the running model. Nothing was generated.');
  bounded.throwIfAborted();
 }catch(error){
  if(original?.aborted)throw original.reason??Error('Stopped before local model dispatch.');
  if(error instanceof Error&&error.message.startsWith('Local model route:'))throw error;
  refuse('The selected model could not be verified. Check the local server and try a new request.');
 }finally{await response?.body?.cancel().catch(()=>{});}
}

/** The public Agent stream seam preserves Pi's owner and all existing hooks.
 * Request options.fetch is the supported HTTP transport injection point. A
 * throwing extension event handler alone would only warn and still dispatch. */
export function installLocalModelRouteGuard(session:AgentSession,providerIds:readonly string[]=localModelRouteProviders()){
 const providers=new Set(providerIds);if(!providers.size||installed.has(session))return;installed.add(session);
 const previous=session.agent.streamFunction;
 session.agent.streamFunction=async(model,context,options)=>{
  if(model.api!=='openai-completions'||!providers.has(model.provider))return previous(model,context,options);
  const transport=options?.fetch??globalThis.fetch,onPayload=options?.onPayload,onStream=options?.onProviderStreamEvent;
  let effective=model,routeIssue:{message:string;phase:'metadata'|'payload'|'response';httpPromptDispatched:boolean}|undefined;
  const upstream=await previous(model,context,{...options,
   onPayload:async(payload,prepared)=>{effective=prepared;const changed=await onPayload?.(payload,prepared),body=changed===undefined?payload:changed;if(!object(body)||body.model!==prepared.id){const message='A request hook changed the selected model. Refresh the local provider configuration.';routeIssue={message:'Local model route: '+message,phase:'payload',httpPromptDispatched:false};refuse(message);}return changed;},
   fetch:async(input,init)=>{try{await advertised(input,init,effective,transport,options?.signal);}catch(error){if(error instanceof Error&&error.message.startsWith('Local model route:'))routeIssue={message:error.message,phase:'metadata',httpPromptDispatched:false};throw error;}return transport(input,{...init,redirect:'error'});},
   onProviderStreamEvent:async(data,prepared)=>{await onStream?.(data,prepared);if(object(data)&&typeof data.model==='string'&&data.model!==prepared.id){const message='The server reported a different model ('+JSON.stringify(data.model.slice(0,200))+' instead of '+JSON.stringify(prepared.id.slice(0,200))+'). Its response was stopped; check the running profile before sending again.';routeIssue={message:'Local model route: '+message,phase:'response',httpPromptDispatched:true};refuse(message);}},
  });
  // HTTP clients may turn a transport rejection into "Connection error".
  // Preserve the SDK's terminal event/usage and attach our known pre-dispatch
  // cause, rather than inventing an HTTP response from the model server.
  const output=createAssistantMessageEventStream();let last:AssistantMessage|undefined;
  const annotate=(message:AssistantMessage)=>routeIssue&&message.stopReason==='error'?{...message,errorMessage:routeIssue.message,diagnostics:[...(message.diagnostics??[]),createAssistantMessageDiagnostic(DIAGNOSTIC,new Error(routeIssue.message),{phase:routeIssue.phase,httpPromptDispatched:routeIssue.httpPromptDispatched,provider:effective.provider,model:effective.id})]}:message;
  void(async()=>{
   try{
    for await(const event of upstream){
     if('partial' in event)last=event.partial;else if(event.type==='done')last=event.message;else if(event.type==='error')last=event.error;
     output.push(event.type==='error'?{...event,error:annotate(event.error)}:event);
    }
    output.end(annotate(await upstream.result()));
   }catch{
    const error:AssistantMessage={role:'assistant',api:model.api,provider:model.provider,model:model.id,content:[],usage:{input:0,output:0,cacheRead:0,cacheWrite:0,totalTokens:0,cost:{input:0,output:0,cacheRead:0,cacheWrite:0,total:0}},timestamp:Date.now(),...last,stopReason:options?.signal?.aborted?'aborted':'error',errorMessage:routeIssue?.message??'The local model stream ended unexpectedly. Inspect its existing outcome before sending again.'};
    output.push({type:'error',reason:error.stopReason==='aborted'?'aborted':'error',error});
   }
  })();
  return output;
 };
}
