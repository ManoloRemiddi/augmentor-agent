// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {createHash,randomUUID} from 'node:crypto';
import {existsSync,lstatSync,readFileSync,openSync,closeSync,writeFileSync,renameSync,fsyncSync,unlinkSync} from 'node:fs';
import {dirname} from 'node:path';

type Status='waiting'|'dispatching'|'active'|'steering'|'completed'|'failed'|'cancelled'|'removed'|'unconfirmed';
interface Item {id:string;input?:string;fingerprint:string;status:Status;queued:boolean;delivered:boolean;turnId?:string;steerTurnId?:string}
interface Journal {schema:1;sessionId:string;revision:number;paused:boolean;items:Item[]}
const statuses=new Set<Status>(['waiting','dispatching','active','steering','completed','failed','cancelled','removed','unconfirmed']);
const visible=(item:Item)=>item.status==='waiting'||item.status==='unconfirmed'||item.status==='failed'&&item.input!==undefined||['dispatching','active','steering'].includes(item.status)&&item.queued&&!item.delivered;
const fingerprint=(input:string)=>createHash('sha256').update(input).digest('hex');
export function promptIdentity(value:unknown):string {if(typeof value!=='string'||!/^[a-zA-Z0-9_.:-]{1,128}$/.test(value))throw Error('Invalid prompt identity.');return value;}

/** Durable product admission. Pi owns execution; waiting inputs never enter its transient string queue. */
export class PiPromptQueue {
 private data:Journal;
 constructor(readonly path:string,readonly sessionId:string,private changed:()=>void=()=>{}){
  if(existsSync(path)){
   const stat=lstatSync(path);
   if(!stat.isFile()||stat.isSymbolicLink()||(process.getuid&&stat.uid!==process.getuid())||(process.platform!=='win32'&&(stat.mode&0o077)))throw Error('The prompt queue requires a private, owned file.');
   const data=JSON.parse(readFileSync(path,'utf8')) as Journal;
   if(data?.schema!==1||data.sessionId!==sessionId||!Number.isSafeInteger(data.revision)||data.revision<0||typeof data.paused!=='boolean'||!Array.isArray(data.items))throw Error('Unsupported prompt queue; automatic submission is disabled.');
   const ids=new Set<string>();
   for(const item of data.items){
    promptIdentity(item.id);
    if(ids.has(item.id)||!statuses.has(item.status)||typeof item.queued!=='boolean'||typeof item.delivered!=='boolean'||!/^[a-f0-9]{64}$/.test(item.fingerprint)||
     (item.turnId!==undefined&&promptIdentity(item.turnId)!==item.turnId)||
     (item.steerTurnId!==undefined&&promptIdentity(item.steerTurnId)!==item.steerTurnId)||
     (item.status==='steering'&&(!item.steerTurnId||item.turnId!==item.steerTurnId))||
     (item.input!==undefined&&(typeof item.input!=='string'||!item.input.trim()||item.input.length>65536||fingerprint(item.input)!==item.fingerprint))||
     (['waiting','dispatching','active','steering','unconfirmed'].includes(item.status)&&item.input===undefined))throw Error('Corrupt prompt queue; automatic submission is disabled.');
    ids.add(item.id);
   }
   if(data.items.filter(visible).length>100||Buffer.byteLength(JSON.stringify(data.items.filter(visible)))>512*1024)throw Error('The saved prompt queue exceeds its bounds.');
   this.data=data;
  }else this.data={schema:1,sessionId,revision:0,paused:false,items:[]};
 }
 get paused(){return this.data.paused;}
 get uncertain(){return this.data.items.some(item=>item.status==='unconfirmed');}
 get next(){return this.data.items.find(item=>item.status==='waiting');}
 get active(){return this.data.items.find(item=>['dispatching','active'].includes(item.status));}
 get pendingSteer(){return this.data.items.find(item=>item.status==='steering'&&!item.delivered);}
 read(id:string){return structuredClone(this.item(id));}
 promote(id:string,turnId:string){
  const item=this.item(id);
  if(item.steerTurnId===turnId&&item.status!=='waiting')return false;
  if(this.paused||this.uncertain||this.active?.turnId!==turnId||item.status!=='waiting'||this.pendingSteer)throw Error('Only a waiting prompt can steer the observed active turn.');
  this.patch(id,{status:'steering',turnId,steerTurnId:turnId,queued:true});return true;
 }
 withdrawSteer(id:string){if(this.item(id).status!=='steering'||this.item(id).delivered)throw Error('Steering input has already crossed its delivery boundary.');this.patch(id,{status:'waiting',turnId:undefined,steerTurnId:undefined});}
 lookup(id:string,input:string){
  const existing=this.data.items.find(item=>item.id===id);
  if(existing&&existing.fingerprint!==fingerprint(input))throw Error('Prompt identity was reused for different input.');
  return existing?structuredClone(existing):undefined;
 }
 enqueue(id:string,input:string,queued:boolean){
  promptIdentity(id);if(typeof input!=='string'||!input.trim()||input.length>65536)throw Error('Invalid queued prompt.');const duplicate=this.lookup(id,input);if(duplicate)return false;
  const item:Item={id,input,fingerprint:fingerprint(input),status:'waiting',queued,delivered:false};
  const pending=[...this.data.items.filter(visible),item];
  if(pending.length>100||Buffer.byteLength(JSON.stringify(pending))>512*1024)throw Error('The prompt queue is full. Remove waiting or unsent prompts before adding more.');
  this.commit({...this.data,items:[...this.data.items,item]});return true;
 }
 pause(){if(!this.paused)this.commit({...this.data,paused:true});}
 resume(){if(this.uncertain)throw Error('A previous prompt has an unknown outcome. Inspect its history before explicitly resolving that receipt; it cannot be replayed.');if(this.paused)this.commit({...this.data,paused:false});}
 dispatch(id:string,turnId:string){
  const item=this.item(id);if(this.paused||this.uncertain||this.active||item.status!=='waiting')throw Error('The next prompt cannot be dispatched.');
  this.patch(id,{status:'dispatching',turnId});
 }
 accepted(id:string){if(this.item(id).status!=='dispatching')throw Error('Prompt was not dispatched.');this.patch(id,{status:'active'});}
 delivered(id:string){const item=this.item(id);if(!['dispatching','active','steering'].includes(item.status))throw Error('Prompt delivery has no active receipt.');this.patch(id,{delivered:true});}
 handledSteer(id:string){const item=this.item(id);if(item.status!=='steering'||item.delivered)throw Error('Correction input no longer awaits preparation.');this.patch(id,{status:'completed',input:undefined});}
 finish(id:string,status:'completed'|'failed'|'cancelled'){
  const item=this.item(id);
  if(!['dispatching','active'].includes(item.status))throw Error('Prompt has no active execution receipt.');
  // Terminal receipts retain their fingerprint indefinitely, without retaining all historical prompt text.
  this.commit({...this.data,items:this.data.items.map(value=>value.id===id?{...value,status,input:undefined}:value.status==='steering'&&value.turnId===item.turnId?
   (value.delivered?{...value,status,input:undefined}:{...value,status:'unconfirmed' as const}):value)});
 }
 notSent(id:string){if(this.item(id).status!=='waiting')throw Error('Only an undispatched prompt can be rejected.');this.patch(id,{status:'failed'});this.pause();}
 remove(id:string){const item=this.item(id);if(item.status==='removed')return;if(!['waiting','failed'].includes(item.status))throw Error('Active or unconfirmed prompts cannot be removed.');this.patch(id,{status:'removed',input:undefined});}
 /** Explicit owner acknowledgment, never a retry. The unknown native/tool outcome remains in history. */
 resolve(id:string){if(this.item(id).status!=='unconfirmed')throw Error('Only an unknown prompt receipt can be acknowledged.');this.patch(id,{status:'cancelled',input:undefined});}
 recover(){
  const unsettled=this.active;
  if(unsettled||this.next||this.data.items.some(item=>item.status==='steering'))this.commit({...this.data,paused:true,items:this.data.items.map(item=>['dispatching','active','steering'].includes(item.status)?{...item,status:'unconfirmed' as const}:item)});
 }
 snapshot(steeringAvailable=false){return {revision:this.data.revision,activeTurnId:!this.paused?this.active?.turnId??null:null,paused:this.paused,items:this.data.items.filter(visible).map(item=>({
  id:item.id,rpcId:item.id,placement:item.status==='steering'?'steering':'queued',message:{content:[{type:'text',text:item.input}]},
  stateLabel:item.status==='unconfirmed'?(item.delivered?'Interrupted — check the action outcome':'Not confirmed — check history'):item.status==='failed'?'Not sent':item.status==='steering'?'Steering — waiting for the safe boundary':item.status==='waiting'&&this.paused?'Paused':item.status==='waiting'?undefined:'Sending…',
  canSteer:steeringAvailable&&!this.paused&&!this.uncertain&&!this.pendingSteer&&!!this.active&&item.status==='waiting',canRemove:['waiting','failed'].includes(item.status),canResolve:item.status==='unconfirmed',
 }))};}
 private item(id:string){const item=this.data.items.find(value=>value.id===id);if(!item)throw Error('Queued prompt not found.');return item;}
 private patch(id:string,patch:Partial<Item>){this.commit({...this.data,items:this.data.items.map(item=>item.id===id?{...item,...patch}:item)});}
 private commit(value:Journal){
  const directory=dirname(this.path),stat=lstatSync(directory);
  if(!stat.isDirectory()||stat.isSymbolicLink()||(process.getuid&&stat.uid!==process.getuid())||(process.platform!=='win32'&&(stat.mode&0o077)))throw Error('The prompt queue requires a private, owned directory.');
  const next={...value,revision:this.data.revision+1},temporary=this.path+'.'+randomUUID()+'.tmp',fd=openSync(temporary,'wx',0o600);
  try{writeFileSync(fd,JSON.stringify(next)+'\n');fsyncSync(fd);}catch(error){try{unlinkSync(temporary);}catch{}throw error;}finally{closeSync(fd);}
  try{renameSync(temporary,this.path);if(process.platform!=='win32'){const directoryFd=openSync(directory,'r');try{fsyncSync(directoryFd);}finally{closeSync(directoryFd);}}}catch(error){try{unlinkSync(temporary);}catch{}throw error;}
  this.data=next;this.changed();
 }
}
