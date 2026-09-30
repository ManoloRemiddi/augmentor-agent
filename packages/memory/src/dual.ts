// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {promptCall} from '../../prompt-library/src/client.js';
import {randomUUID} from 'node:crypto';
import {memoryContext} from './context.js';
export {memoryContext} from './context.js';
export type MemoryEvent={id:string;role:'user'|'assistant';mode:'voice'|'text';content:string;status?:'complete'|'interrupted'|'error';live?:boolean};

// One owner per harness session. Writes are serialized, deduplicated by durable
// transcript IDs, and have no authority to replay model/tool actions.
export class DualMemoryClient{
  private writes:Promise<unknown>=Promise.resolve();
  private bound=false;
  private pending:MemoryEvent[]=[];
  private captureTimer?:ReturnType<typeof setTimeout>;
  private closed=false;
  private owner=randomUUID();
  private activityTimer?:ReturnType<typeof setInterval>;
  private activityWrites:Promise<unknown>=Promise.resolve();
  private phase:'foreground'|'tools'|'stop'='stop';
  constructor(readonly session:string,readonly cwd:string,readonly call:typeof promptCall=promptCall,readonly warn:(message:string)=>void=()=>{}){}
  private async bind(signal?:AbortSignal){if(!this.bound){await this.call('memory.dual.bind',{session:this.session,cwd:this.cwd},undefined,signal);this.bound=true;}}
  private async rpc(action:string,p:Record<string,unknown>={},signal?:AbortSignal){signal?.throwIfAborted();await this.bind(signal);signal?.throwIfAborted();return this.call('memory.dual.'+action,{session:this.session,...p},undefined,signal);}
  activity(phase:'foreground'|'tools'|'stop'){
    if(this.phase==='stop'&&phase!=='stop')this.owner=randomUUID();
    this.phase=phase;clearInterval(this.activityTimer);
    const send=()=>{const current=this.phase,owner=this.owner;this.activityWrites=this.activityWrites.then(()=>this.rpc('activity',{owner,phase:current},AbortSignal.timeout(1000))).catch(()=>{this.warn('Memory processing lease unavailable; capture continues.');});return this.activityWrites;};
    if(phase!=='stop'&&!this.closed){this.activityTimer=setInterval(()=>{void send();},2000);this.activityTimer.unref?.();}
    return send();
  }
  append(events:MemoryEvent[]){
    // Chunk without dropping raw text; IDs retain reconstruction order.
    const pieces=events.flatMap(event=>{
      const parts:MemoryEvent[]=[];
      for(let start=0,n=0;start<event.content.length;n++){
        let end=Math.min(start+8000,event.content.length);
        // Never turn a valid non-BMP character into two lone surrogates. SQLite
        // rejects those strings; one bad piece would roll back the whole batch.
        if(end<event.content.length&&event.content.charCodeAt(end-1)>=0xd800&&event.content.charCodeAt(end-1)<=0xdbff&&event.content.charCodeAt(end)>=0xdc00&&event.content.charCodeAt(end)<=0xdfff)end--;
        parts.push({...event,id:event.id+':'+n,content:event.content.slice(start,end)});start=end;
      }
      return parts;
    });
    this.pending.push(...pieces);
    const admission=this.activityWrites;
    this.writes=this.writes.then(async()=>{await admission;while(this.pending.length){const batch=this.pending.slice(0,50);await this.rpc('append',{events:batch},AbortSignal.timeout(5000));this.pending.splice(0,batch.length);}}).catch(()=>{
      this.warn('Automatic memory capture is unavailable; the harness transcript remains intact.');
      if(!this.closed){clearTimeout(this.captureTimer);this.captureTimer=setTimeout(()=>{void this.append([]);},5000);this.captureTimer.unref?.();}
    });
    return this.writes;
  }
  async recall(mode:'voice'|'text',query='',signal?:AbortSignal){
    signal?.throwIfAborted();
    const controller=new AbortController();let timer:ReturnType<typeof setTimeout>|undefined;
    let rejectAbort!:(error:unknown)=>void;
    const cancelled=new Promise<never>((_resolve,reject)=>{rejectAbort=reject;});
    const abort=()=>{controller.abort();rejectAbort(signal?.reason??new Error('Memory recall cancelled'));};
    signal?.addEventListener('abort',abort,{once:true});
    if(signal?.aborted)abort();
    try{return await Promise.race([(async()=>{await this.writes;controller.signal.throwIfAborted();return memoryContext(await this.rpc('recall',{},controller.signal),mode,query);})(),cancelled,new Promise<string>((_resolve,reject)=>{timer=setTimeout(()=>{controller.abort();reject(new Error('Memory recall timed out'));},3000);})]);}
    catch(error){if(signal?.aborted)throw error;this.warn('Automatic memory recall is unavailable; continuing without recalled context.');return '';}
    finally{clearTimeout(timer);signal?.removeEventListener('abort',abort);}
  }
  async flush(){await Promise.all([this.writes,this.activityWrites]);}
  close(){this.closed=true;clearTimeout(this.captureTimer);void this.activity('stop');}
}
