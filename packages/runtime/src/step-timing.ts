// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {randomUUID} from 'node:crypto';
export const STEP_TIMING_SCHEMA='augmentor-sdk-step-timing/1';
type Window={start:number;end:number};
type BlockWindow=Window&{kind:'reasoning'|'text'|'toolarg'};
type ModelWindow=Window&{requestId?:string;firstDelta?:number;blocks:BlockWindow[]};
type ToolWindow=Window&{id:string;name:string;parentId?:string};
type WaitWindow=Window&{id:string;kind:string};
type OpenModel=Omit<ModelWindow,'end'>&{block?:Omit<BlockWindow,'end'>};
type OpenStep={id:string;start:number;models:ModelWindow[];tools:ToolWindow[];waits:WaitWindow[];model?:OpenModel;toolMap:Map<string,Omit<ToolWindow,'end'>>;waitMap:Map<string,Omit<WaitWindow,'end'>>;dropped:number;bytes:number};
const identity=(value:unknown):value is string=>typeof value==='string'&&value.length>0&&value.length<=256;
/** Observes public SDK boundaries only. No request, tool or interaction owner. */
export class StepTiming {
  private step?:OpenStep;
  constructor(private clock=()=>performance.now(),private id=()=>randomUUID(),private limit=512){}
  private offset(){return this.step?Math.max(0,this.clock()-this.step.start):0;}
  private room(bytes=256){const s=this.step!;const size=s.models.length+s.tools.length+s.waits.length+s.toolMap.size+s.waitMap.size+s.models.reduce((sum,m)=>sum+m.blocks.length,0)+(s.model?1+s.model.blocks.length+(s.model.block?1:0):0);if(size>=this.limit||s.bytes+bytes>6000){s.dropped++;return false;}s.bytes+=bytes;return true;}
  begin(){
    this.step={id:this.id(),start:this.clock(),models:[],tools:[],waits:[],toolMap:new Map(),waitMap:new Map(),dropped:0,bytes:0};
    return {schema:STEP_TIMING_SCHEMA,stepId:this.step.id,boundary:'public-pi-sdk-turn-start',clock:'step-relative-monotonic-ms'};
  }
  modelStart(requestId?:string){const s=this.step;if(!s)return;if(s.model){s.dropped++;delete s.model;}if(this.room(Buffer.byteLength(JSON.stringify({requestId}))+256))s.model={start:this.offset(),blocks:[],...(requestId?{requestId}:{})};}
  stream(type:string){
    const s=this.step,m=s?.model;if(!s||!m)return;const now=this.offset();
    if(['text_delta','thinking_delta','toolcall_delta'].includes(type)&&m.firstDelta===undefined)m.firstDelta=now;
    const kind=({text_start:'text',thinking_start:'reasoning',toolcall_start:'toolarg'} as const)[type as 'text_start'|'thinking_start'|'toolcall_start'];
    if(kind){if(m.block)m.blocks.push({...m.block,end:now});delete m.block;if(m.blocks.length>=128)s.dropped++;else if(this.room())m.block={kind,start:now};}
  }
  modelEnd(){const s=this.step;if(!s)return;if(!s.model){s.dropped++;return;}const end=this.offset(),{block,...m}=s.model;if(block)m.blocks.push({...block,end});s.models.push({...m,end});delete s.model;}
  toolStart(id:string,name:string,parentId?:string){const s=this.step;if(!s)return;if(!identity(id)||!identity(name)||parentId!==undefined&&!identity(parentId)){s.dropped++;return;}if(s.toolMap.has(id)){s.dropped++;s.toolMap.delete(id);}if(this.room(Buffer.byteLength(JSON.stringify({id,name,parentId}))+128))s.toolMap.set(id,{id,name,start:this.offset(),...(parentId?{parentId}:{})});}
  toolEnd(id:string){const s=this.step,item=s?.toolMap.get(id);if(!s)return;if(!item){s.dropped++;return;}s.toolMap.delete(id);s.tools.push({...item,end:this.offset()});}
  wait(id:string,kind:string,active:boolean){const s=this.step;if(!s)return;if(active){if(!identity(id)||!identity(kind)){s.dropped++;return;}if(!s.waitMap.has(id)&&this.room(Buffer.byteLength(JSON.stringify({id,kind}))+128))s.waitMap.set(id,{id,kind,start:this.offset()});}else{const item=s.waitMap.get(id);if(item){s.waitMap.delete(id);s.waits.push({...item,end:this.offset()});}}}
  end(){
    const s=this.step;if(!s)return;const wallMs=this.offset();delete this.step;
    return {schema:STEP_TIMING_SCHEMA,stepId:s.id,boundary:'public-pi-sdk-turn-end',clock:'step-relative-monotonic-ms',wallMs,models:s.models,tools:s.tools,waits:[...s.waits,...[...s.waitMap.values()].map(item=>({...item,end:wallMs}))],coverage:{dropped:s.dropped,unclosedModels:s.model?1:0,unclosedTools:s.toolMap.size,openInteractions:s.waitMap.size}};
  }
  abandon(reason:string){const s=this.step;if(!s)return;delete this.step;return {schema:STEP_TIMING_SCHEMA,stepId:s.id,reason,boundary:'missing-public-sdk-turn-end'};}
}
