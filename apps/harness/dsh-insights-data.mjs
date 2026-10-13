// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {projectDshContext} from './dsh-context-projection.mjs';
import {foldTimingRecords,timingSummary} from './dsh-context-timing.mjs';
const fields=['input','cacheRead','cacheWrite','output'];
const safeName=value=>typeof value==='string'&&value.length>0&&value.length<=1024&&!['__proto__','prototype','constructor'].includes(value);
const number=value=>typeof value==='number'&&Number.isFinite(value)&&value>=0;
export const localDay=time=>{const d=new Date(time);return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;};
/** Retain only the metadata this page needs; never keep provider/tool bodies. */
export function insightMetadata(record){
 if(typeof record?.id!=='string'||record.id.length>128||!Number.isSafeInteger(record.seq)||record.seq<1||!number(record.time)||!Number.isFinite(new Date(record.time).getTime()))throw Error('Invalid retained observation identity.');
 const base={id:record.id,seq:record.seq,time:record.time,kind:record.kind,requestId:record.requestId,turnId:record.turnId};
 const data=record.data??{};
 if(record.kind==='model/request')return {...base,data:{model:data.model,provider:data.provider,api:data.api,capacity:data.capacity,...(data.purpose==='manual-compaction'?{purpose:data.purpose}:{})},payload:record.payload?{state:record.payload.state,bytes:record.payload.bytes,sha256:record.payload.sha256}:undefined};
 if(record.kind==='model/complete')return {...base,data:{usage:data.usage?Object.fromEntries(fields.map(key=>[key,data.usage[key]])):undefined,durationMs:data.durationMs}};
 if(record.kind==='turn/start'||record.kind==='tool/end')return {...base,data:{durationMs:data.durationMs}};
 if(['step/start','step/end','step/incomplete'].includes(record.kind))return {...base,data:record.kind==='step/end'?timingSummary(data)??{schema:data.schema,stepId:data.stepId}:{schema:data.schema,stepId:data.stepId,boundary:data.boundary,clock:data.clock}};
 return null;
}
function addCost(cost,provider,model,usage){const branch=cost[provider]??={};const bucket=(branch[model]??={peak:{uncached:0,cacheRead:0,cacheWrite:0,output:0}}).peak;for(const [i,key] of fields.entries())bucket[['uncached','cacheRead','cacheWrite','output'][i]]+=usage[key];}
/** Request-local billing joins, with explicit gaps for ambiguous/missing records. */
export function foldInsightRecords(records){
 const requests=new Map(),ends=new Map(),turns=new Set();let tools=0;
 for(const record of records){
  if(record.kind==='model/request')requests.set(record.id,record);
  if(record.kind==='model/complete'){const list=ends.get(record.requestId)??[];list.push(record);ends.set(record.requestId,list);}
  if(record.kind==='turn/start')turns.add(record.turnId??record.id);
  if(record.kind==='tool/end')tools++;
 }
 const cost={},days={},accepted=[],gaps={unlinkedSettlements:0,usageUnavailable:0,duplicateSettlements:0,invalidBilling:0};let modelMs=0,timedCalls=0,billedTotal=0;
 for(const [id,settlements] of ends)if(!requests.has(id))gaps.unlinkedSettlements+=settlements.length;
 for(const request of requests.values()){
  const day=days[localDay(request.time)]??={tokens:0,requests:0,cost:{}};day.requests++;
  const settlements=ends.get(request.id)??[];
  if(settlements.length!==1){gaps[settlements.length?'duplicateSettlements':'usageUnavailable']++;continue;}
  const end=settlements[0],usage=end.data?.usage;
  if(end.seq>request.seq&&number(end.data.durationMs)&&Number.isFinite(modelMs+end.data.durationMs)){modelMs+=end.data.durationMs;timedCalls++;}
  if(end.seq<=request.seq||!safeName(request.data?.provider)||!safeName(request.data?.model)||!usage||!fields.every(key=>Number.isSafeInteger(usage[key])&&usage[key]>=0)||!Number.isSafeInteger(fields.reduce((sum,key)=>sum+usage[key],0))){gaps.invalidBilling++;continue;}
  const total=fields.reduce((sum,key)=>sum+usage[key],0);
  if(!Number.isSafeInteger(billedTotal+total)){gaps.invalidBilling++;continue;}
  billedTotal+=total;addCost(cost,request.data.provider,request.data.model,usage);addCost(day.cost,request.data.provider,request.data.model,usage);day.tokens+=total;accepted.push(end);
 }
 const stepTiming=foldTimingRecords(records);
 return {cost,days,accepted,latest:[...requests.values()].sort((a,b)=>a.seq-b.seq).at(-1),turns:turns.size,requests:requests.size,tools,modelMs,timedCalls,gaps,stepTiming:{timing:stepTiming.timing,coverage:stepTiming.coverage}};
}
export function insightProjection(records,payload){
 const summary=foldInsightRecords(records),latest=summary.latest;
 const safeLatest=latest&&safeName(latest.data?.provider)&&safeName(latest.data?.model)?latest:undefined;
 const value=projectDshContext({records:safeLatest?[safeLatest,...summary.accepted.filter(r=>r.requestId===safeLatest.id)]:[],events:[],payloads:safeLatest&&payload?{[safeLatest.id]:payload}:{}});
 // Corpus cards retain figures, never all provider texts or historical nodes.
 const timeline={...value.timeline,nodes:[],archive:[],requests:[],events:[],fileOps:[],cost:summary.cost,counts:{...value.timeline.counts,turns:summary.turns,steps:summary.requests}};
 return {summary:{...summary,accepted:undefined},timeline,activity:{days:summary.days},currentAvailable:Boolean(safeLatest&&payload&&value.coverage.latestAvailable)};
}
/** The original donut shows actual SDK-normalized buckets, not an inferred all-history composition. */
export function reportedInsightTokens(rows){
 const values={input:0,cacheRead:0,cacheWrite:0,output:0};let any=false;
 for(const row of rows)for(const models of Object.values(row.familyCost??{}))for(const periods of Object.values(models))for(const bucket of Object.values(periods)){
  any=true;values.input+=bucket.uncached;values.cacheRead+=bucket.cacheRead;values.cacheWrite+=bucket.cacheWrite;values.output+=bucket.output;
 }
 if(!any||!Object.values(values).every(value=>Number.isSafeInteger(value)&&value>=0)||!Number.isSafeInteger(Object.values(values).reduce((a,b)=>a+b,0)))return null;
 const parts=[['input','Uncached input','#6366f1'],['cacheRead','Cache read','#f59e0b'],['cacheWrite','Cache write','#22c55e'],['output','Output','#a855f7']].map(([key,label,color])=>({key,label,color,value:values[key]}));
 return {parts,total:parts.reduce((sum,p)=>sum+p.value,0)};
}
