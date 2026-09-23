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
  private async rpc(action:string,p:Record<string,unknown>={},signal?:AbortSignal){await this.bind(signal);return this.call('memory.dual.'+action,{session:this.session,...p},undefined,signal);}
  activity(phase:'foreground'|'tools'|'stop'){
    if(this.phase==='stop'&&phase!=='stop')this.owner=randomUUID();
    this.phase=phase;clearInterval(this.activityTimer);
    const send=()=>{const current=this.phase,owner=this.owner;this.activityWrites=this.activityWrites.then(()=>this.rpc('activity',{owner,phase:current},AbortSignal.timeout(1000))).catch(()=>{this.warn('Memory processing lease unavailable; capture continues.');});return this.activityWrites;};
    if(phase!=='stop'&&!this.closed){this.activityTimer=setInterval(()=>{void send();},2000);this.activityTimer.unref?.();}
    return send();
  }
  append(events:MemoryEvent[]){
    // Chunk without dropping raw text; IDs retain reconstruction order.
    const pieces=events.flatMap(event=>Array.from({length:Math.ceil(event.content.length/8000)},(_,n)=>({...event,id:event.id+':'+n,content:event.content.slice(n*8000,(n+1)*8000)})));
    this.pending.push(...pieces);
    const admission=this.activityWrites;
    this.writes=this.writes.then(async()=>{await admission;while(this.pending.length){const batch=this.pending.slice(0,50);await this.rpc('append',{events:batch},AbortSignal.timeout(5000));this.pending.splice(0,batch.length);}}).catch(()=>{
      this.warn('Automatic memory capture is unavailable; the harness transcript remains intact.');
      if(!this.closed){clearTimeout(this.captureTimer);this.captureTimer=setTimeout(()=>{void this.append([]);},5000);this.captureTimer.unref?.();}
    });
    return this.writes;
  }
  async recall(mode:'voice'|'text',query=''){
    const controller=new AbortController();let timer:ReturnType<typeof setTimeout>|undefined;
    try{return await Promise.race([(async()=>{await this.writes;return memoryContext(await this.rpc('recall',{},controller.signal),mode,query);})(),new Promise<string>((_resolve,reject)=>{timer=setTimeout(()=>{controller.abort();reject(new Error('Memory recall timed out'));},3000);})]);}
    catch{this.warn('Automatic memory recall is unavailable; continuing without recalled context.');return '';}
    finally{clearTimeout(timer);}
  }
  async flush(){await this.writes;}
  close(){this.closed=true;clearTimeout(this.captureTimer);void this.activity('stop');}
}
