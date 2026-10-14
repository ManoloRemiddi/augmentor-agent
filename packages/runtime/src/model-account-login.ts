// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {existsSync,statSync} from 'node:fs';
import {randomUUID} from 'node:crypto';
import type {AuthInteraction,AuthPrompt,AuthEvent} from '@earendil-works/pi-ai';
import {identifier} from '../../protocol/src/index.js';
import {atomicJson,readJson} from './storage.js';

type State='running'|'cancel-requested'|'completed'|'failed'|'cancelled'|'interrupted';
export interface AccountLoginReceipt {requestId:string;provider:string;state:State;result:'pending'|'credential-stored'|'unknown';startedAt:string;settledAt?:string;cancelRequested:boolean}
type PromptView={id:string;type:AuthPrompt['type'];message:string;placeholder?:string;options?:{id:string;label:string;description?:string}[]};
type Display={message?:string;authorizationUrl?:string;links?:{url:string;label?:string}[];deviceCode?:string;verificationUri?:string;prompt?:PromptView};
type Current={row:AccountLoginReceipt;abort:AbortController;display:Display;task?:Promise<void>;answer?:{id:string;finish:(value?:string)=>void};timer?:ReturnType<typeof setTimeout>};
const active=(row:AccountLoginReceipt)=>row.state==='running'||row.state==='cancel-requested';
const text=(value:unknown,max=8000)=>{if(typeof value!=='string'||value.length>max)throw Error('Invalid account interaction.');return value;};
export const accountProvider=(value:unknown)=>{const id=text(value,256);if(!id||id.trim()!==id||/[\x00-\x1f]/.test(id)||['__proto__','constructor','prototype'].includes(id))throw Error('Choose a registered account provider.');return id;};
const url=(value:unknown)=>{const raw=text(value,32768),parsed=new URL(raw);if(!['https:','http:'].includes(parsed.protocol)||parsed.username||parsed.password||parsed.protocol==='http:'&&!['localhost','127.0.0.1','[::1]'].includes(parsed.hostname))throw Error('Invalid account sign-in link.');return raw;};
const timestamp=(value:unknown)=>typeof value==='string'&&new Date(value).toISOString()===value;
function receipt(value:AccountLoginReceipt):AccountLoginReceipt{
 if(!value||!['running','cancel-requested','completed','failed','cancelled','interrupted'].includes(value.state)||!['pending','credential-stored','unknown'].includes(value.result)||!timestamp(value.startedAt)||typeof value.cancelRequested!=='boolean'||(active(value)?value.result!=='pending'||value.settledAt!==undefined:!timestamp(value.settledAt)||value.result!==(value.state==='completed'?'credential-stored':'unknown')))throw Error('Invalid account receipt.');
 return {requestId:identifier(value.requestId),provider:accountProvider(value.provider),state:value.state,result:value.result,startedAt:value.startedAt,...(value.settledAt?{settledAt:value.settledAt}:{}),cancelRequested:value.cancelRequested};
}

/** One explicit supported SDK login, separate from conversation execution.
 * Only bounded metadata is durable. Links, codes, prompts, answers, credentials
 * and SDK errors never enter this file or conversation/observation history. */
export class ModelAccountLogin {
 private rows=new Map<string,AccountLoginReceipt>();private current?:Current;
 private refreshNeeded=false;private storageError=false;
 constructor(private file:string){
  try{
   if(!existsSync(file))return;
   if(statSync(file).size>1024*1024)throw Error('size');
   const data=readJson<any>(file,null);if(data?.version!=='augmentor-model-account-login/1'||typeof data.needsRefresh!=='boolean'||!Array.isArray(data.receipts)||data.receipts.length>256)throw Error('shape');
   this.refreshNeeded=data.needsRefresh;
   for(const item of data.receipts){const row=receipt(item);if(this.rows.has(row.requestId))throw Error('duplicate');this.rows.set(row.requestId,row);}
   let recovered=false;for(const row of this.rows.values())if(active(row)){row.state='interrupted';row.result='unknown';row.settledAt=new Date().toISOString();this.refreshNeeded=true;recovered=true;}
   if(recovered)this.persist();
  }catch{this.storageError=true;this.refreshNeeded=true;}
 }
 get busy(){return !!this.current;}
 get needsRefresh(){return this.refreshNeeded||this.storageError;}
 private persist(){atomicJson(this.file,{version:'augmentor-model-account-login/1',needsRefresh:this.refreshNeeded,receipts:[...this.rows.values()]});}
 describe(requestId?:unknown){
  const row=requestId===undefined?[...this.rows.values()].at(-1):this.rows.get(identifier(requestId));if(requestId!==undefined&&!row)throw Error('Account sign-in receipt not found.');
  return {available:!this.storageError,busy:this.busy,needsRefresh:this.needsRefresh,receipt:row?{...row}:null,interaction:row&&this.current?.row===row?structuredClone(this.current.display):null,retention:'metadata-only; active interaction is transient',maxReceipts:256};
 }
 start(provider:unknown,requestId:unknown,run:(interaction:AuthInteraction)=>Promise<void>){
  const id=identifier(requestId),route=accountProvider(provider);
  if(this.rows.has(id))throw Error('This account sign-in already has a receipt. Inspect it; nothing was retried.');
  if(this.busy||this.needsRefresh)throw Error('Finish the current sign-in and refresh model settings before another account action.');
  if(this.rows.size>=256)throw Error('Account receipt retention is full. Inspect the private account receipts before starting another sign-in.');
  const row:AccountLoginReceipt={requestId:id,provider:route,state:'running',result:'pending',startedAt:new Date().toISOString(),cancelRequested:false};
  this.rows.set(id,row);this.refreshNeeded=true;
  try{this.persist();}catch{this.storageError=true;throw Error('Account sign-in admission could not be saved. No SDK login was started.');}
  const current:Current={row,abort:new AbortController(),display:{}};this.current=current;
  const interaction:AuthInteraction={signal:current.abort.signal,prompt:prompt=>this.prompt(current,prompt),notify:event=>this.notify(current,event)};
  current.timer=setTimeout(()=>this.cancel(id),15*60*1000);current.timer.unref();
  current.task=Promise.resolve().then(async()=>{
   try{current.abort.signal.throwIfAborted();await run(interaction);current.abort.signal.throwIfAborted();row.state='completed';row.result='credential-stored';this.refreshNeeded=false;}
   catch{row.state=current.abort.signal.aborted?'cancelled':'failed';row.result='unknown';this.refreshNeeded=true;}
   finally{
    clearTimeout(current.timer);current.answer?.finish();current.display={};row.settledAt=new Date().toISOString();
    try{this.persist();}catch{this.storageError=true;this.refreshNeeded=true;row.state='failed';row.result='unknown';}
    current.abort.abort();if(this.current===current)this.current=undefined;
   }
  });
  return this.describe(id);
 }
 private notify(current:Current,event:AuthEvent){
  if(this.current!==current||current.abort.signal.aborted)return;
  switch(event.type){
   case 'auth_url':current.display.authorizationUrl=url(event.url);current.display.message=event.instructions===undefined?undefined:text(event.instructions);break;
   case 'device_code':current.display.deviceCode=text(event.userCode,1024);current.display.verificationUri=url(event.verificationUri);break;
   case 'info':
    if(event.links&&event.links.length>16)throw Error('Too many account links.');
    current.display.links=event.links?.map(link=>({url:url(link.url),...(link.label===undefined?{}:{label:text(link.label,1024)})}));
    current.display.message=text(event.message);break;
   case 'progress':current.display.message=text(event.message);break;
   default:throw Error('Unsupported account interaction.');
  }
 }
 private prompt(current:Current,input:AuthPrompt):Promise<string>{
  if(this.current!==current||current.abort.signal.aborted||input.signal?.aborted)return Promise.reject(Error('Account prompt cancelled.'));
  if(current.answer)throw Error('Account provider requested overlapping prompts.');
  if(!['text','secret','select','manual_code'].includes(input.type))throw Error('Unsupported account prompt.');
  const id=randomUUID(),view:PromptView={id,type:input.type,message:text(input.message)};
  if(input.type==='select'){
   if(!Array.isArray(input.options)||input.options.length<1||input.options.length>128)throw Error('Invalid account options.');
   view.options=input.options.map(option=>({id:text(option.id,512),label:text(option.label,1024),...(option.description===undefined?{}:{description:text(option.description,2048)})}));
   if(new Set(view.options.map(option=>option.id)).size!==view.options.length)throw Error('Duplicate account options.');
  }else if(input.placeholder!==undefined)view.placeholder=text(input.placeholder,2048);
  current.display.prompt=view;
  return new Promise((resolve,reject)=>{
   const abort=()=>finish();
   const finish=(value?:string)=>{
    current.abort.signal.removeEventListener('abort',abort);input.signal?.removeEventListener('abort',abort);
    if(current.answer?.id===id){current.answer=undefined;delete current.display.prompt;}
    value===undefined?reject(Error('Account prompt cancelled.')):resolve(value);
   };
   current.answer={id,finish};current.abort.signal.addEventListener('abort',abort,{once:true});input.signal?.addEventListener('abort',abort,{once:true});
   if(current.abort.signal.aborted||input.signal?.aborted)finish();
  });
 }
 respond(requestId:unknown,promptId:unknown,value:unknown){
  const current=this.current,id=identifier(requestId),step=identifier(promptId);
  if(!current||current.row.requestId!==id||current.abort.signal.aborted||current.answer?.id!==step||current.display.prompt?.id!==step)throw Error('This account prompt is no longer active. Nothing was submitted.');
  const answer=text(value,65536),prompt=current.display.prompt;
  if(prompt.type==='select'&&!prompt.options?.some(option=>option.id===answer))throw Error('Choose a current account option.');
  current.answer.finish(answer);return {accepted:true,requestId:id,promptId:step};
 }
 cancel(requestId:unknown){
  const id=identifier(requestId),current=this.current;
  if(current?.row.requestId===id&&!current.abort.signal.aborted){
   current.row.cancelRequested=true;current.row.state='cancel-requested';
   try{this.persist();}catch{this.storageError=true;}
   current.display={};current.abort.abort(Error('Account login cancelled.'));
  }
  return this.describe(id);
 }
 reconcile(){
  if(this.busy)throw Error('Wait for account sign-in to settle before refreshing models.');
  if(this.storageError)throw Error('Account receipt storage needs repair before reconciliation.');
  this.refreshNeeded=false;try{this.persist();}catch{this.storageError=true;this.refreshNeeded=true;throw Error('Account reconciliation could not be saved.');}
 }
 async close(){const current=this.current;if(current){this.cancel(current.row.requestId);await current.task;}}
}

/** Created only if an explicitly requested SDK login asks for installation ID. */
export function accountDeviceId(file:string){
 const existing=readJson<any>(file,null);
 if(existing!==null){if(existing?.version!=='augmentor-account-device/1'||typeof existing.id!=='string'||!/^[-a-f0-9]{36}$/.test(existing.id))throw Error('Invalid account installation identity.');return existing.id;}
 const id=randomUUID();atomicJson(file,{version:'augmentor-account-device/1',id});return id;
}
