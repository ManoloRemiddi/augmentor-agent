// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {randomUUID} from 'node:crypto';
import type {ExtensionUIContext, ExtensionUIDialogOptions} from '@earendil-works/pi-coding-agent';
import type {Data} from '../../protocol/src/index.js';
export class Interactions {
  pending=new Map<string,{sessionId:string;frame:Data;finish:(value:any)=>void}>();
  constructor(private publish:(sessionId:string,frame:Data)=>void,private connected:(sessionId:string)=>boolean,private timeout=120000){}
  ask(sessionId:string,method:string,payload:Data,options?:ExtensionUIDialogOptions):Promise<any> {
    if(!this.connected(sessionId)||options?.signal?.aborted)return Promise.resolve(undefined);
    return new Promise(resolve=>{
      const id=randomUUID();
      const frame={method,rpcId:id,payload:{...payload,sessionId,approvalId:id}};
      const finish=(value:any)=>{if(!this.pending.delete(id))return;clearTimeout(timer);options?.signal?.removeEventListener('abort',abort);this.publish(sessionId,{method:'interaction/resolved',rpcId:id,payload:{sessionId,rpcId:id}});resolve(value);};
      const abort=()=>finish(undefined);
      const timer=setTimeout(abort,Math.min(options?.timeout??this.timeout,this.timeout));
      this.pending.set(id,{sessionId,frame,finish});options?.signal?.addEventListener('abort',abort,{once:true});this.publish(sessionId,frame);
    });
  }
  answer(id:string,value:any,sessionId:string){const item=this.pending.get(id);if(!item||item.sessionId!==sessionId)throw new Error('This interaction has already resolved');item.finish(value);return {accepted:true};}
  cancel(sessionId:string){for(const item of [...this.pending.values()])if(item.sessionId===sessionId)item.finish(undefined);}
  frames(sessionId:string){return [...this.pending.values()].filter(p=>p.sessionId===sessionId).map(p=>p.frame);}
  async approve(sid:string,toolName:string,input:unknown){const result=await this.ask(sid,'approval/requested',{toolName,reason:JSON.stringify(input).slice(0,16000)});return result?.outcome==='allowed-once';}
  ui(sid:string):ExtensionUIContext {
    const question=async(title:string,options?:string[],opts?:ExtensionUIDialogOptions,prefill?:string)=>{
      const result=await this.ask(sid,'question/requested',{questions:[{id:'answer',header:'Augmentor question',question:title,options:options?.map(label=>({label})),prefill}]},opts);
      const answer=result?.answer?.answers?.[0];return answer?.custom??answer?.selected?.[0];
    };
    const notify=(message:string)=>this.publish(sid,{method:'notification',payload:{sessionId:sid,message}});
    const supported:Partial<ExtensionUIContext>={
      select:(title,options,opts)=>question(title,options,opts),input:(title,placeholder,opts)=>question(title,undefined,opts,placeholder),
      editor:(title,prefill)=>question(title,undefined,undefined,prefill),
      confirm:async(title,message,opts)=>{const value=await this.ask(sid,'approval/requested',{toolName:title,reason:message},opts);return value?.outcome==='allowed-once';},
      notify,setStatus:(_key,value)=>{if(value)notify(value);},setWorkingMessage:value=>{if(value)notify(value);},
      custom:async()=>{throw new Error('Terminal-only custom UI is unsupported by the native surface');},
      getEditorText:()=>'',getEditorComponent:()=>undefined,getToolsExpanded:()=>false,getAllThemes:()=>[],getTheme:()=>undefined,
      setTheme:()=>({success:false,error:'Use native appearance settings'}),onTerminalInput:()=>()=>{},
    };
    return new Proxy(supported,{get:(target,key)=>key in target?Reflect.get(target,key):()=>{}}) as ExtensionUIContext;
  }
}
