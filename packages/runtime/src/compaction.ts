// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {existsSync,readFileSync,statSync} from 'node:fs';
import {identifier,text} from '../../protocol/src/index.js';
import {atomicJson} from './storage.js';

type State='running'|'cancel-requested'|'completed'|'failed'|'cancelled'|'unknown';
export interface CompactionReceipt {
 requestId:string;sessionId:string;provider:string;model:string;state:State;
 startedAt:string;settledAt?:string;cancelRequested:boolean;acknowledged:boolean;
 beforeLeaf?:string|null;entryId?:string;tokensBefore?:number;estimatedTokensAfter?:number;
 sdkOutcome?:'returned'|'rejected'|'not-called';
}
type Admission=Pick<CompactionReceipt,'requestId'|'sessionId'|'provider'|'model'>;
type Outcome=Pick<CompactionReceipt,'state'|'sdkOutcome'|'entryId'|'tokensBefore'|'estimatedTokensAfter'>;
const active=(r:CompactionReceipt)=>r.state==='running'||r.state==='cancel-requested';
const iso=(v:unknown)=>typeof v==='string'&&!Number.isNaN(Date.parse(v))&&new Date(v).toISOString()===v;
function saved(value:any):CompactionReceipt {
 if(!value||!['running','cancel-requested','completed','failed','cancelled','unknown'].includes(value.state)||!iso(value.startedAt)||typeof value.cancelRequested!=='boolean'||typeof value.acknowledged!=='boolean')throw Error('Invalid compaction receipt');
 if(active(value)?value.settledAt!==undefined:!iso(value.settledAt))throw Error('Invalid compaction settlement');
 if(value.acknowledged&&value.state!=='unknown'||value.state==='completed'&&!value.entryId)throw Error('Invalid compaction outcome');
 const row:CompactionReceipt={requestId:identifier(value.requestId),sessionId:identifier(value.sessionId),provider:text(value.provider,256),model:text(value.model,512),state:value.state,startedAt:value.startedAt,cancelRequested:value.cancelRequested,acknowledged:value.acknowledged};
 if(value.settledAt)row.settledAt=value.settledAt;
 if(value.entryId!==undefined)row.entryId=identifier(value.entryId);
 if(value.beforeLeaf!==undefined)row.beforeLeaf=value.beforeLeaf===null?null:identifier(value.beforeLeaf);
 for(const key of ['tokensBefore','estimatedTokensAfter'] as const)if(value[key]!==undefined){if(!Number.isFinite(value[key])||value[key]<0)throw Error('Invalid token estimate');row[key]=value[key];}
 if(value.sdkOutcome!==undefined){if(!['returned','rejected','not-called'].includes(value.sdkOutcome))throw Error('Invalid SDK outcome');row.sdkOutcome=value.sdkOutcome;}
 return row;
}
/** A manual context operation, separate from prompt/turn admission. Durable IDs
 * are never replayed. Stop retains the lease until the supported SDK settles.
 */
export class PiCompactions {
 private rows=new Map<string,CompactionReceipt>();
 private current?:{row:CompactionReceipt;abort:AbortController;task?:Promise<void>;stop?:()=>void};
 private storageError=false;
 constructor(private file:string,private changed:(row:CompactionReceipt)=>void=()=>{}){
  try{
   if(!existsSync(file))return;
   if(statSync(file).size>1024*1024)throw Error('size');
   const data=JSON.parse(readFileSync(file,'utf8'));
   if(data?.version!=='augmentor-compactions/1'||!Array.isArray(data.receipts)||data.receipts.length>256)throw Error('shape');
   for(const value of data.receipts){const row=saved(value);if(this.rows.has(row.requestId))throw Error('duplicate');this.rows.set(row.requestId,row);}
   let recovered=false;for(const row of this.rows.values())if(active(row)){row.state='unknown';row.settledAt=new Date().toISOString();recovered=true;}
   if(recovered)this.persist();
  }catch{this.storageError=true;}
 }
 get busy(){return !!this.current;}
 busySession(sid:string){return this.current?.row.sessionId===sid;}
 activeId(sid:string){return this.current?.row.sessionId===sid?this.current.row.requestId:undefined;}
 blocked(sid:string){return this.storageError||this.busySession(sid)||[...this.rows.values()].some(r=>r.sessionId===sid&&r.state==='unknown'&&!r.acknowledged);}
 private persist(){atomicJson(this.file,{version:'augmentor-compactions/1',receipts:[...this.rows.values()]});}
 private notify(row:CompactionReceipt){try{this.changed({...row});}catch{/* Notification gaps are repaired by status reads. */}}
 describe(sid:string){const last=[...this.rows.values()].filter(r=>r.sessionId===sid).at(-1);return {available:!this.storageError,busy:this.busySession(sid),blocked:this.blocked(sid),lastReceipt:last?{...last}:null,retention:this.storageError?'receipt-storage-gap':'private-compaction-receipts',coverage:'saved native compaction boundary; token counts are SDK estimates; no replay'};}
 duplicate(input:Admission){const row=this.rows.get(identifier(input.requestId));if(!row)return;
  if(row.sessionId!==input.sessionId||row.provider!==input.provider||row.model!==input.model)throw Error('Compaction request identity was already used for a different operation.');
  return {accepted:true,duplicate:true,...this.describe(input.sessionId)};
 }
 begin(input:Admission,effect:(signal:AbortSignal,checkpoint:(leaf:string|null,stop:()=>void)=>void)=>Promise<Outcome>){
  const duplicate=this.duplicate(input);if(duplicate)return duplicate;
  if(this.busy||this.blocked(input.sessionId))throw Error('Finish compaction or acknowledge its unknown outcome before starting another.');
  if(this.rows.size>=256)throw Error('Compaction receipt storage is full; nothing was sent.');
  const row=saved({...input,state:'running',startedAt:new Date().toISOString(),cancelRequested:false,acknowledged:false});
  this.rows.set(row.requestId,row);try{this.persist();}catch{this.rows.delete(row.requestId);throw Error('Compaction receipt could not be saved; nothing was sent.');}
  const current={row,abort:new AbortController(),task:undefined as Promise<void>|undefined,stop:undefined as (()=>void)|undefined};this.current=current;this.notify(row);
  current.task=Promise.resolve().then(()=>effect(current.abort.signal,(leaf,stop)=>{
   row.beforeLeaf=leaf;this.persist();current.stop=stop;if(current.abort.signal.aborted)stop();
  })).then(outcome=>{Object.assign(row,outcome);},()=>{row.state='unknown';}).finally(()=>{
   row.settledAt=new Date().toISOString();try{this.persist();}catch{this.storageError=true;}
   if(this.current===current)this.current=undefined;this.notify(row);
  });
  return {accepted:true,duplicate:false,...this.describe(input.sessionId)};
 }
 cancelSession(sid:string){const current=this.current;if(current?.row.sessionId!==sid)return false;
  current.row.cancelRequested=true;current.row.state='cancel-requested';current.abort.abort();current.stop?.();
  try{this.persist();}catch{this.storageError=true;}this.notify(current.row);return true;
 }
 waitSession(sid:string){return this.current?.row.sessionId===sid?this.current.task:Promise.resolve();}
 acknowledge(sid:string,requestId:string){const row=this.rows.get(identifier(requestId));if(!row||row.sessionId!==sid||row.state!=='unknown'||this.busySession(sid))throw Error('Inspect this conversation’s saved native history before acknowledging its unknown compaction outcome.');
  row.acknowledged=true;try{this.persist();}catch{row.acknowledged=false;this.storageError=true;throw Error('Compaction acknowledgement could not be saved.');}this.notify(row);return this.describe(sid);
 }
}
