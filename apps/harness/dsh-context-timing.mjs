// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Pi metadata adapter for the original Apache-2.0 Timing Stats card/strip.
export const STEP_TIMING_SCHEMA='augmentor-sdk-step-timing/1';
export const TIMING_LABELS={'timing.total':'Measured SDK step time','timing.ttft':'Wait before stream','timing.gen':'Model stream','timing.reasoning':'Reasoning stream','timing.text':'Text stream','timing.toolArgs':'Argument stream','timing.tools':'Tool intervals','timing.other':'Other step time','timing.strip':'Measured SDK steps in recorded order; concurrent intervals are merged in the strip. These are SDK observations, not provider-internal timings.','timing.empty':'No complete recorded SDK step timings in this view. Older logs still expose their recorded model durations in Context Trend.'};
const number=x=>typeof x==='number'&&Number.isFinite(x)&&x>=0&&x<=Number.MAX_SAFE_INTEGER;
const identity=x=>typeof x==='string'&&x.length>0&&x.length<=256;
const empty=()=>({wallMs:0,ttftMs:0,genMs:0,calls:0,toolsMs:0,toolCalls:0,tools:Object.create(null)});
const span=(w,wall)=>w&&number(w.start)&&number(w.end)&&w.end>=w.start&&w.end<=wall;
function union(windows,wall){let total=0,cursor=0;for(const w of [...windows].sort((a,b)=>a.start-b.start||a.end-b.end)){const from=Math.max(cursor,w.start),to=Math.min(wall,w.end);if(to>from){total+=to-from;cursor=to;}}return total;}
export function timingSummary(value){
 if(!value||value.schema!==STEP_TIMING_SCHEMA||value.boundary!=='public-pi-sdk-turn-end'||value.clock!=='step-relative-monotonic-ms'||!identity(value.stepId)||!number(value.wallMs))return null;
 if(![value.models,value.tools,value.waits].every(a=>Array.isArray(a)&&a.length<=512)||value.models.length+value.tools.length+value.waits.length+value.models.reduce((sum,m)=>sum+(Array.isArray(m?.blocks)?m.blocks.length:0),0)>512)return null;
 const c=value.coverage;if(!c||!['dropped','unclosedModels','unclosedTools','openInteractions'].every(k=>Number.isSafeInteger(c[k])&&c[k]>=0))return null;
 const models=[],tools=[],waits=[];
 for(const m of value.models){if(!span(m,value.wallMs)||m.requestId!==undefined&&!identity(m.requestId)||m.firstDelta!==undefined&&(!number(m.firstDelta)||m.firstDelta<m.start||m.firstDelta>m.end)||!Array.isArray(m.blocks)||m.blocks.length>129)return null;let cursor=m.start;const blocks=[];for(const b of m.blocks){if(!['reasoning','text','toolarg'].includes(b.kind)||!span(b,value.wallMs)||b.start<cursor||b.end>m.end)return null;cursor=b.end;blocks.push({kind:b.kind,start:b.start,end:b.end});}models.push({start:m.start,end:m.end,blocks,...(m.requestId===undefined?{}:{requestId:m.requestId}),...(m.firstDelta===undefined?{}:{firstDelta:m.firstDelta})});}
 for(const t of value.tools){if(!span(t,value.wallMs)||!identity(t.id)||!identity(t.name)||t.parentId!==undefined&&!identity(t.parentId))return null;tools.push({id:t.id,name:t.name,start:t.start,end:t.end,...(t.parentId===undefined?{}:{parentId:t.parentId})});}
 for(const w of value.waits){if(!span(w,value.wallMs)||!identity(w.id)||!identity(w.kind))return null;waits.push({id:w.id,kind:w.kind,start:w.start,end:w.end});}
 return {schema:STEP_TIMING_SCHEMA,stepId:value.stepId,clock:value.clock,boundary:value.boundary,wallMs:value.wallMs,models,tools,waits,coverage:Object.fromEntries(['dropped','unclosedModels','unclosedTools','openInteractions'].map(k=>[k,c[k]]))};
}
/** Only paired, unambiguous completed SDK steps contribute. No wall-clock subtraction. */
export function foldTimingRecords(records){
 const starts=new Map(),ends=new Map(),incomplete=new Set(),requestIds=new Set();
 for(const r of records){const id=r.data?.stepId;if(!identity(id)||r.data?.schema!==STEP_TIMING_SCHEMA)continue;if(r.kind==='step/start'){const rows=starts.get(id)??[];rows.push(r);starts.set(id,rows);}if(r.kind==='step/end'){const rows=ends.get(id)??[];rows.push(r);ends.set(id,rows);}if(r.kind==='step/incomplete')incomplete.add(id);}
 let timing=null,spans=[],stripAvailable=true;const requestActiveMs=new Map();const coverage={completeSteps:0,incompleteSteps:0,invalidSteps:0,partialSteps:0,legacyRequests:0,unattributedModels:0,interactionMs:0};
 for(const [id,list] of starts){const endRows=ends.get(id)??[];if(list.length!==1||endRows.length!==1||incomplete.has(id)){coverage.incompleteSteps++;continue;}const start=list[0],end=endRows[0],value=timingSummary(end.data),epoch=typeof start.time==='number'?start.time:Date.parse(start.time);
  if(!value||start.seq>=end.seq||start.turnId!==end.turnId||!Number.isFinite(epoch)||start.data.boundary!=='public-pi-sdk-turn-start'||start.data.clock!=='step-relative-monotonic-ms'){coverage.invalidSteps++;continue;}
  const t=empty(),painted=[];let completeStrip=true,unattributed=0;t.wallMs=value.wallMs;t.calls=value.models.length;
  for(const m of value.models){const decode=Math.min(m.firstDelta??Infinity,m.blocks[0]?.start??Infinity);if(Number.isFinite(decode)){t.ttftMs+=decode-m.start;t.genMs+=m.end-decode;painted.push({kind:'ttft',start:m.start,end:decode});const classified=m.blocks.reduce((sum,b)=>sum+b.end-b.start,0);if(Math.abs(classified-(m.end-decode))>1e-6)completeStrip=false;for(const b of m.blocks){const key={reasoning:'reasoning',text:'text',toolarg:'toolArg'}[b.kind];t[key+'Ms']=(t[key+'Ms']??0)+b.end-b.start;t[key+'Blocks']=(t[key+'Blocks']??0)+1;painted.push({...b});}}else unattributed++;}
  for(const tool of value.tools){const ms=tool.end-tool.start;t.toolsMs+=ms;t.toolCalls++;const row=t.tools[tool.name]??={calls:0,ms:0};row.calls++;row.ms+=ms;painted.push({kind:'tools',start:tool.start,end:tool.end});}
  const waiting=union(value.waits,value.wallMs);
  // A completed SDK step normally has one request. Ambiguous retries or
  // missing hooks must not duplicate the whole step onto several chart bars.
  if(!Object.values(t).filter(v=>typeof v==='number').every(number)){coverage.invalidSteps++;continue;}
  const merged=mergeTimings([timing,t].filter(Boolean));if(!merged){coverage.invalidSteps++;continue;}timing=merged;coverage.completeSteps++;coverage.interactionMs+=waiting;coverage.unattributedModels+=unattributed;stripAvailable&&=completeStrip;if(Object.values(value.coverage).some(n=>n>0))coverage.partialSteps++;
  for(const m of value.models)if(m.requestId)requestIds.add(m.requestId);
  if(value.models.length===1&&value.models[0].requestId)requestActiveMs.set(value.models[0].requestId,value.wallMs-waiting);
  let cursor=0;for(const p of painted.sort((a,b)=>a.start-b.start||a.end-b.end)){const from=Math.max(cursor,p.start);if(p.end<=from)continue;if(from>cursor)spans.push({kind:'other',start:epoch+cursor,end:epoch+from});spans.push({kind:p.kind,start:epoch+from,end:epoch+p.end});cursor=p.end;}if(value.wallMs>cursor)spans.push({kind:'other',start:epoch+cursor,end:epoch+value.wallMs});
 }
 coverage.incompleteSteps+= [...ends.keys()].filter(id=>!starts.has(id)).length;
 coverage.legacyRequests=records.filter(r=>r.kind==='model/request'&&r.data?.purpose!=='manual-compaction'&&!requestIds.has(r.id)).length;
 return {timing,spans:stripAvailable?spans:undefined,coverage,requestActiveMs};
}
export function mergeTimings(values){
 if(!values.length)return null;const total=empty();
 for(const t of values){for(const key of ['wallMs','ttftMs','genMs','calls','toolsMs','toolCalls','reasoningMs','reasoningBlocks','textMs','textBlocks','toolArgMs','toolArgBlocks'])if(t[key]!==undefined){const next=(total[key]??0)+t[key];if(!number(next))return null;total[key]=next;}for(const [name,row] of Object.entries(t.tools)){if(!Object.hasOwn(total.tools,name)&&Object.keys(total.tools).length>=128)continue;const target=total.tools[name]??={calls:0,ms:0};target.calls+=row.calls;target.ms+=row.ms;if(!number(target.calls)||!number(target.ms))return null;}}
 if(values.some(t=>t.genMs>0&&Math.abs(['reasoningMs','textMs','toolArgMs'].reduce((sum,key)=>sum+(t[key]??0),0)-t.genMs)>1e-6))for(const key of ['reasoningMs','reasoningBlocks','textMs','textBlocks','toolArgMs','toolArgBlocks'])delete total[key];
 return total;
}
