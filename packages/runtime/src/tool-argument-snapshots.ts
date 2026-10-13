// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import type {AssistantMessageEvent} from '@earendil-works/pi-ai';
import {randomUUID} from 'node:crypto';
const identity=(v:unknown):v is string=>typeof v==='string'&&v.length>0&&v.length<=256;
/** Sample public SDK argument objects for display. Never proposes or executes a tool. */
export class ToolArgumentSnapshots {
  private active=false;
  private calls=new Map<number,{time:number;bytes:number;raw?:string;callId:string;name:string;revision:number}>();
  private captureId='';
  private capturedBytes=0;
  private exhausted=false;
  constructor(private clock=()=>performance.now()){}
  identity(){return this.captureId||undefined;}
  begin(){this.calls.clear();this.captureId=randomUUID();this.capturedBytes=0;this.exhausted=false;this.active=true;}
  end(){this.calls.clear();this.active=false;}
  update(event:AssistantMessageEvent){
    if(!this.active||this.exhausted||!['toolcall_start','toolcall_delta','toolcall_end'].includes(event.type)||!('contentIndex' in event)||!Number.isSafeInteger(event.contentIndex)||event.contentIndex<0||event.contentIndex>4095)return;
    const call=event.type==='toolcall_end'?event.toolCall:'partial' in event?event.partial.content[event.contentIndex]:undefined;
    if(!call||call.type!=='toolCall'||!identity(call.id)||!identity(call.name))return;
    const now=this.clock(),old=this.calls.get(event.contentIndex);
    if(event.type==='toolcall_delta'&&old?.callId===call.id&&old.name===call.name&&now-old.time<50)return;
    const same=old?.callId===call.id&&old.name===call.name;
    const base={type:'tool-call-snapshot',captureId:this.captureId,index:event.contentIndex,callId:call.id,name:call.name,revision:(same?old!.revision:0)+1,boundary:'public-sdk-partial-tool-call-arguments',complete:event.type==='toolcall_end'};
    if(!old&&this.calls.size>=128){this.exhausted=true;return {...base,argsRaw:null,reason:'Live SDK tool-call snapshot limit reached; inspect the completed native message.'};}
    let raw:string|undefined;
    try{raw=JSON.stringify(call.arguments);}catch{/* A broken diagnostic value cannot affect the SDK loop. */}
    const bytes=raw===undefined?0:Buffer.byteLength(raw),total=[...this.calls.values()].reduce((n,row)=>n+row.bytes,0)-(old?.bytes??0)+bytes;
    const reason=raw===undefined?'SDK arguments cannot be represented as JSON.':bytes>512*1024||total>2*1024*1024?'Live SDK argument snapshot exceeds the display limit; inspect the completed native message.':undefined;
    if(!reason&&old&&old.raw===raw&&same&&event.type!=='toolcall_end'){this.calls.set(event.contentIndex,{...old,time:now});return;}
    this.calls.set(event.contentIndex,{time:now,bytes:reason?0:bytes,...(!reason?{raw}:{}),callId:call.id,name:call.name,revision:base.revision});
    let result;
    if(reason)result={...base,argsRaw:null,reason};
    else if(old?.raw!==undefined&&old.callId===call.id&&old.name===call.name){
      let prefix=0,suffix=0;
      while(prefix<old.raw.length&&prefix<raw!.length&&old.raw[prefix]===raw![prefix])prefix++;
      while(suffix<old.raw.length-prefix&&suffix<raw!.length-prefix&&old.raw[old.raw.length-1-suffix]===raw![raw!.length-1-suffix])suffix++;
      result={...base,argsPatch:{units:'utf16-code-units',baseRevision:old.revision,prefix,remove:old.raw.length-prefix-suffix,insert:raw!.slice(prefix,raw!.length-suffix)}};
    }else result={...base,argsRaw:raw!};
    const captured=Buffer.byteLength(JSON.stringify(result));
    if(this.capturedBytes+captured>2*1024*1024){this.exhausted=true;return {...base,argsRaw:null,reason:'Live SDK argument capture budget reached; inspect the completed native message.'};}
    this.capturedBytes+=captured;
    return result;
  }
}
