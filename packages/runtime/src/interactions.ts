// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {randomUUID} from 'node:crypto';
import type {ExtensionUIContext, ExtensionUIDialogOptions} from '@earendil-works/pi-coding-agent';
import type {Data} from '../../protocol/src/index.js';
type QuestionWait={revision:number;state:'counting'|'focused'|'editing'|'waiting';remainingMs:number;deadline?:number};
type PendingInteraction={sessionId:string;ownerId:string;frame:Data;finish:(value:any,reason?:string)=>void;timer?:ReturnType<typeof setTimeout>;wait?:QuestionWait;focus:Map<string,number>};
export class Interactions {
  pending=new Map<string,PendingInteraction>();
  constructor(private publish:(sessionId:string,frame:Data)=>void,private connected:(sessionId:string)=>boolean,private timeout=120000,private focusLeaseMs=15000,private observeWait?:(ownerId:string,id:string,kind:string,active:boolean)=>void){
    if(!Number.isFinite(timeout)||timeout<0||!Number.isFinite(focusLeaseMs)||focusLeaseMs<=0)throw Error('Invalid interaction timeout');
  }
  private observed(ownerId:string,id:string,kind:string,active:boolean){try{this.observeWait?.(ownerId,id,kind,active);}catch{/* Diagnostics cannot alter dialog ownership or settlement. */}}
  private waitSnapshot(item:PendingInteraction){const wait=item.wait!;return {...wait,remainingMs:wait.deadline===undefined?wait.remainingMs:Math.max(0,wait.deadline-Date.now())};}
  private updateFrame(item:PendingInteraction){item.frame={...item.frame,payload:{...item.frame.payload,wait:this.waitSnapshot(item)}};}
  private changed(item:PendingInteraction){item.wait!.revision++;this.updateFrame(item);this.publish(item.sessionId,{method:'interaction/updated',rpcId:item.frame.rpcId,payload:{sessionId:item.sessionId,wait:item.frame.payload.wait}});}
  private schedule(item:PendingInteraction){
    clearTimeout(item.timer);
    if(!item.wait)return;
    const deadlines=[Date.now()+1000,...item.focus.values(),...(item.wait.deadline===undefined?[]:[item.wait.deadline])];
    item.timer=setTimeout(()=>{
      if(!this.pending.has(item.frame.rpcId))return;
      if(!this.connected(item.sessionId)){item.finish(undefined,'disconnected');return;}
      if(item.wait!.deadline!==undefined&&item.wait!.deadline<=Date.now()){item.finish(undefined,'timed-out');return;}
      for(const [client,expiry] of item.focus)if(expiry<=Date.now())item.focus.delete(client);
      if(item.wait!.state==='focused'&&!item.focus.size){item.wait!.state='counting';item.wait!.deadline=Date.now()+item.wait!.remainingMs;this.changed(item);}
      this.schedule(item);
    },Math.max(0,Math.min(...deadlines)-Date.now()));
  }
  ask(sessionId:string,method:string,payload:Data,options?:ExtensionUIDialogOptions,ownerId=sessionId):Promise<any> {
    if(!this.connected(sessionId)||options?.signal?.aborted)return Promise.resolve(undefined);
    return new Promise(resolve=>{
      const id=randomUUID();
      const duration=Math.min(options?.timeout??this.timeout,this.timeout);
      if(!Number.isFinite(duration)||duration<0)throw Error('Invalid dialog timeout');
      const frame={method,rpcId:id,payload:{...payload,sessionId,approvalId:id}};
      const finish=(value:any,reason='answered')=>{if(!this.pending.delete(id))return;clearTimeout(item.timer);options?.signal?.removeEventListener('abort',abort);this.observed(ownerId,id,method,false);this.publish(sessionId,{method:'interaction/resolved',rpcId:id,payload:{sessionId,rpcId:id,reason}});resolve(value);};
      const abort=()=>finish(undefined,'aborted');
      const item:PendingInteraction={sessionId,ownerId,frame,finish,focus:new Map(),...(method==='question/requested'?{wait:{revision:0,state:'counting',remainingMs:duration,deadline:Date.now()+duration}}:{})};
      this.pending.set(id,item);options?.signal?.addEventListener('abort',abort,{once:true});
      this.observed(ownerId,id,method,true);
      if(item.wait){this.updateFrame(item);this.schedule(item);}else item.timer=setTimeout(()=>finish(undefined,'timed-out'),duration);
      this.publish(sessionId,item.frame);
    });
  }
  wait(id:string,sessionId:string,clientId:string,action:unknown){
    const item=this.pending.get(id);
    if(!item||item.sessionId!==sessionId)throw Error('This interaction has already resolved');
    if(!item.wait||item.frame.method!=='question/requested')throw Error('Approval deadlines cannot be paused');
    if(!['take-time','engage','hold-focus','release-focus'].includes(action as string))throw Error('Invalid question wait action');
    if(item.wait.deadline!==undefined&&item.wait.deadline<=Date.now()){item.finish(undefined,'timed-out');throw Error('This interaction has already resolved');}
    if(!this.connected(sessionId)){item.finish(undefined,'disconnected');throw Error('This interaction has already resolved');}
    const before=item.wait.state,now=Date.now();
    if(action==='take-time'||action==='engage'){
      if(item.wait.state!=='waiting')item.wait.state=action==='take-time'?'waiting':'editing';
      item.focus.clear();
    }else if(!['waiting','editing'].includes(item.wait.state)){
      for(const [client,expiry] of item.focus)if(expiry<=now)item.focus.delete(client);
      if(action==='hold-focus')item.focus.set(clientId,now+this.focusLeaseMs);else item.focus.delete(clientId);
      item.wait.state=item.focus.size?'focused':'counting';
    }
    if(item.wait.state!=='counting'&&item.wait.deadline!==undefined){item.wait.remainingMs=Math.max(0,item.wait.deadline-now);delete item.wait.deadline;}
    if(item.wait.state==='counting'&&item.wait.deadline===undefined)item.wait.deadline=now+item.wait.remainingMs;
    if(before!==item.wait.state)this.changed(item);
    this.schedule(item);this.updateFrame(item);
    return {accepted:true,rpcId:id,wait:item.frame.payload.wait};
  }
  answer(id:string,value:any,sessionId:string){const item=this.pending.get(id);if(!item||item.sessionId!==sessionId)throw new Error('This interaction has already resolved');if(item.wait?.deadline!==undefined&&item.wait.deadline<=Date.now()){item.finish(undefined,'timed-out');throw new Error('This interaction has already resolved');}item.finish(value);return {accepted:true};}
  cancel(sessionId:string){for(const item of [...this.pending.values()])if(item.sessionId===sessionId||item.ownerId===sessionId)item.finish(undefined,'cancelled');}
  settleOwner(ownerId:string){for(const item of [...this.pending.values()])if(item.ownerId===ownerId)item.finish(undefined,'owner-settled');}
  frames(sessionId:string){return [...this.pending.values()].filter(p=>p.sessionId===sessionId).map(p=>{if(p.wait)this.updateFrame(p);return p.frame;});}
  async approve(sid:string,toolName:string,input:unknown,ownerId=sid){const result=await this.ask(sid,'approval/requested',{toolName,reason:JSON.stringify(input).slice(0,16000),...(ownerId!==sid?{delegatedSessionId:ownerId}:{})},undefined,ownerId);return result?.outcome==='allowed-once';}
  ui(sid:string,ownerId=sid):ExtensionUIContext {
    const question=async(title:string,options?:string[],opts?:ExtensionUIDialogOptions,prefill?:string)=>{
      const result=await this.ask(sid,'question/requested',{questions:[{id:'answer',header:'Augmentor question',question:title,options:options?.map(label=>({label})),prefill}]},opts,ownerId);
      const answer=result?.answer?.answers?.[0];return answer?.custom??answer?.selected?.[0];
    };
    const notify=(message:string)=>this.publish(sid,{method:'notification',payload:{sessionId:sid,message}});
    const supported:Partial<ExtensionUIContext>={
      select:(title,options,opts)=>question(title,options,opts),input:(title,placeholder,opts)=>question(title,undefined,opts,placeholder),
      editor:(title,prefill)=>question(title,undefined,undefined,prefill),
      confirm:async(title,message,opts)=>{const value=await this.ask(sid,'approval/requested',{toolName:title,reason:message},opts,ownerId);return value?.outcome==='allowed-once';},
      notify,setStatus:(_key,value)=>{if(value)notify(value);},setWorkingMessage:value=>{if(value)notify(value);},
      custom:async()=>{throw new Error('Terminal-only custom UI is unsupported by the native surface');},
      getEditorText:()=>'',getEditorComponent:()=>undefined,getToolsExpanded:()=>false,getAllThemes:()=>[],getTheme:()=>undefined,
      setTheme:()=>({success:false,error:'Use native appearance settings'}),onTerminalInput:()=>()=>{},
    };
    return new Proxy(supported,{get:(target,key)=>key in target?Reflect.get(target,key):()=>{}}) as ExtensionUIContext;
  }
}
