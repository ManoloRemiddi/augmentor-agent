// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {existsSync,readFileSync,statSync} from 'node:fs';
import type {ExtensionCommandContext,RegisteredCommand} from '@earendil-works/pi-coding-agent';
import {identifier} from '../../protocol/src/index.js';
import {atomicJson} from './storage.js';

export type McpManagementAction='login'|'logout'|'reconnect';
type State='running'|'cancel-requested'|'completed'|'failed'|'cancelled'|'interrupted';
type Result='pending'|'sdk-reported-success'|'sdk-reported-error'|'sdk-reported-warning'|'sdk-command-settled'|'unknown';
export interface McpManagementReceipt {
 requestId:string;sessionId:string;server:string;action:McpManagementAction;state:State;result:Result;
 startedAt:string;settledAt?:string;cancelRequested:boolean;
}
const actions=new Set(['login','logout','reconnect']),states=new Set(['running','cancel-requested','completed','failed','cancelled','interrupted']),results=new Set(['pending','sdk-reported-success','sdk-reported-error','sdk-reported-warning','sdk-command-settled','unknown']);
const terminal=(row:McpManagementReceipt)=>!['running','cancel-requested'].includes(row.state);
const iso=(value:unknown)=>typeof value==='string'&&value.length===24&&!Number.isNaN(Date.parse(value))&&new Date(value).toISOString()===value;
const serverName=(value:unknown)=>{if(typeof value!=='string'||!/^[-a-zA-Z0-9_]{1,128}$/.test(value))throw Error('Choose a registered MCP server.');return value;};
function saved(value:unknown):McpManagementReceipt {
 const row=value as McpManagementReceipt;
 if(!row||typeof row!=='object'||!actions.has(row.action)||!states.has(row.state)||!results.has(row.result)||!iso(row.startedAt)||(row.settledAt!==undefined&&!iso(row.settledAt))||typeof row.cancelRequested!=='boolean')throw Error('Invalid MCP management receipt');
 if(terminal(row)?!row.settledAt||row.result==='pending':row.settledAt!==undefined||row.result!=='pending')throw Error('Invalid MCP management settlement');
 if(row.state==='interrupted'&&row.result!=='unknown'||row.state==='completed'&&!['sdk-reported-success','sdk-command-settled'].includes(row.result)||row.state==='cancelled'&&row.result!=='sdk-command-settled')throw Error('Invalid MCP management outcome');
 return {requestId:identifier(row.requestId),sessionId:identifier(row.sessionId),server:serverName(row.server),action:row.action,state:row.state,result:row.result,startedAt:row.startedAt,...(row.settledAt?{settledAt:row.settledAt}:{}),cancelRequested:row.cancelRequested};
}
/** Explicit operator commands, separate from prompts and the agent loop. No
 * token, authorization/redirect URL or SDK error text enters retained receipts.
 * A cancelled command keeps its lease until the actual SDK handler settles.
 */
export class McpManagement {
 private rows=new Map<string,McpManagementReceipt>();
 private current?:{row:McpManagementReceipt;abort:AbortController;url?:string;task?:Promise<void>;prompt?:{finish:(value:string|undefined)=>void}};
 private storageError=false;
 private notificationGap=false;
 constructor(private file:string,private changed:(row:McpManagementReceipt)=>void=()=>{}){
  try{
   if(!existsSync(file))return;
   if(statSync(file).size>1024*1024)throw Error('size');
   const data=JSON.parse(readFileSync(file,'utf8'));
   if(data?.version!=='augmentor-mcp-management/1'||!Array.isArray(data.receipts)||data.receipts.length>256)throw Error('shape');
   const admitted=new Map<string,McpManagementReceipt>();for(const item of data.receipts){const row=saved(item);if(admitted.has(row.requestId))throw Error('duplicate');admitted.set(row.requestId,row);}this.rows=admitted;
   let recovered=false;for(const row of this.rows.values())if(!terminal(row)){row.state='interrupted';row.result='unknown';row.settledAt=new Date().toISOString();recovered=true;}
   if(recovered)this.persist();
  }catch{this.storageError=true;}
 }
 get busy(){return !!this.current;}
 private persist(){atomicJson(this.file,{version:'augmentor-mcp-management/1',receipts:[...this.rows.values()]});}
 private notify(row:McpManagementReceipt){try{this.changed({...row});}catch{this.notificationGap=true;}}
 private retain(row:McpManagementReceipt){try{this.persist();}catch{this.storageError=true;}this.notify(row);}
 describe(sessionId?:string){const last=[...this.rows.values()].filter(row=>row.sessionId===sessionId).at(-1);return {available:!this.storageError,busy:this.busy,lastReceipt:last?{...last}:null,notificationGap:this.notificationGap,retention:this.storageError?'receipt-storage-gap':'private-management-receipts',coverage:'explicit SDK command observations; not current connection or credential health',maxReceipts:256};}
 lookup(sessionId:string,requestId:string){const row=this.rows.get(identifier(requestId));if(!row||row.sessionId!==identifier(sessionId))throw Error('MCP management receipt not found for this conversation.');return {...row,retention:this.storageError?'receipt-storage-gap':'saved',authorizationUrl:this.current?.row===row?this.current.url??null:null,waitingForRedirect:this.current?.row===row&&!!this.current.prompt};}
 duplicate(input:{sessionId:string;requestId:string;server:string;action:McpManagementAction}){
  const row=this.rows.get(identifier(input.requestId));if(!row)return;
  if(row.sessionId!==input.sessionId||row.server!==input.server||row.action!==input.action)throw Error('MCP management request ID already has different parameters.');
  return {accepted:true,duplicate:true,...this.lookup(input.sessionId,input.requestId)};
 }
 authorizationUrl(sessionId:string,url:string){
  const current=this.current;if(!current||current.row.sessionId!==sessionId||current.row.action!=='login'||current.abort.signal.aborted)return;
  let parsed:URL;try{parsed=new URL(url);}catch{throw Error('Invalid MCP authorization URL');}
  if(url.length>8192||parsed.username||parsed.password||(parsed.protocol!=='https:'&&!(parsed.protocol==='http:'&&['127.0.0.1','localhost','[::1]'].includes(parsed.hostname))))throw Error('Unsupported MCP authorization URL');
  current.url=parsed.href;
 }
 begin(input:{sessionId:string;requestId:string;server:string;action:McpManagementAction},command:RegisteredCommand['handler'],context:ExtensionCommandContext){
  identifier(input.sessionId);identifier(input.requestId);serverName(input.server);if(!actions.has(input.action))throw Error('Choose sign in, sign out or reconnect.');
  const duplicate=this.duplicate(input);if(duplicate)return duplicate;
  if(this.storageError)throw Error('MCP management receipts are unavailable; no command was dispatched.');
  if(this.busy)throw Error('Finish the active MCP management command before starting another.');
  if(this.rows.size>=256)throw Error('MCP management receipt storage is full; no command was dispatched.');
  const row:McpManagementReceipt={...input,state:'running',result:'pending',startedAt:new Date().toISOString(),cancelRequested:false};
  this.rows.set(row.requestId,row);try{this.persist();}catch{this.rows.delete(row.requestId);throw Error('MCP management receipt could not be saved; no command was dispatched.');}
  const current={row,abort:new AbortController(),url:undefined as string|undefined,task:undefined as Promise<void>|undefined,prompt:undefined as {finish:(value:string|undefined)=>void}|undefined};this.current=current;
  this.notify(row);
  let report:Result='sdk-command-settled',cancelled=false;
  const ui=new Proxy(context.ui,{get:(target,key)=>{
   if(key==='notify')return (message:string,type?:string)=>{
    // The pinned SDK handler returns void. Preserve the distinction between
    // its report and verified server/credential health; never retain raw text.
    if(message==='Sign-in cancelled.'){cancelled=true;return;}
    if(type==='error'){report='sdk-reported-error';return;}
    if(type==='warning'){report='sdk-reported-warning';return;}
    if(message.startsWith('Signed in to MCP server "'+row.server+'" (')||message.startsWith('Reconnected to MCP server "'+row.server+'" (')||message==='Signed out of MCP server "'+row.server+'".'||message==='No stored credentials for MCP server "'+row.server+'".')report='sdk-reported-success';
   };
   if(key==='input')return (_title:string,_placeholder:string,options?:{signal?:AbortSignal;timeout?:number})=>{
    const signal=options?.signal?AbortSignal.any([options.signal,current.abort.signal]):current.abort.signal;
    if(signal.aborted)return Promise.resolve(undefined);
    return new Promise<string|undefined>(resolve=>{
     const finish=(value:string|undefined)=>{if(current.prompt?.finish!==finish)return;current.prompt=undefined;clearTimeout(timer);signal.removeEventListener('abort',abort);resolve(value);};
     const abort=()=>finish(undefined),timer=setTimeout(abort,Math.min(options?.timeout??120000,120000));current.prompt={finish};signal.addEventListener('abort',abort,{once:true});
    });
   };
   return Reflect.get(target,key);
  }});
  current.task=Promise.resolve().then(()=>command(row.action+' '+row.server,{...context,ui})).then(()=>{
   row.state=cancelled?'cancelled':report==='sdk-reported-error'||report==='sdk-reported-warning'?'failed':'completed';row.result=cancelled?'sdk-command-settled':report;
  },()=>{row.state='failed';row.result='unknown';}).finally(()=>{
   row.settledAt=new Date().toISOString();current.url=undefined;current.prompt?.finish(undefined);this.retain(row);if(this.current===current)this.current=undefined;
  });
  return {accepted:true,duplicate:false,...this.lookup(row.sessionId,row.requestId)};
 }
 cancel(sessionId:string,requestId:string){
  this.lookup(sessionId,requestId);const current=this.current;
  if(current?.row.requestId===requestId){current.row.state='cancel-requested';current.row.cancelRequested=true;current.url=undefined;current.abort.abort();this.retain(current.row);}
  return {accepted:!!current&&current.row.requestId===requestId,...this.lookup(sessionId,requestId)};
 }
 cancelSession(sessionId:string){return this.current?.row.sessionId===sessionId?this.cancel(sessionId,this.current.row.requestId).accepted:false;}
 submitRedirect(sessionId:string,requestId:string,url:unknown){
  this.lookup(sessionId,requestId);const current=this.current;
  if(current?.row.requestId!==requestId||!current.prompt||current.abort.signal.aborted)throw Error('This MCP sign-in is not waiting for a redirected URL.');
  if(typeof url!=='string'||!url.trim()||url.length>8192)throw Error('Paste the full redirected URL, up to 8192 characters.');
  // The SDK validates this sign-in's exact redirect URI, state and code. The
  // value is never appended to a receipt, diagnostic record or model input.
  current.prompt.finish(url);return {accepted:true};
 }
 async settled(){await this.current?.task;}
}
