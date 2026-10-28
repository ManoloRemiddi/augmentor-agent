// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {insightMetadata,insightProjection,foldInsightRecords} from './dsh-insights-data.mjs';
import {readDshPayload} from './dsh-payload.mjs';
/** Page-local, operator-only corpus reads. No session opening, inference or mutation. */
export class DshInsightsReader {
 listeners=new Set();generation=0;inflight=null;
 state={phase:'idle',snapshot:null,workspaces:null,details:new Map(),coverage:null,error:null};
 constructor({rpc,current,maxRecords=50000,maxSessionRecords=10000}){Object.assign(this,{rpc,current,maxRecords,maxSessionRecords});}
 subscribe=fn=>{this.listeners.add(fn);return()=>this.listeners.delete(fn);};
 getSnapshot=()=>this.state;
 update(patch){this.state={...this.state,...patch};for(const fn of this.listeners)fn();}
 valid(scope){const now=this.current();return scope.ticket===this.generation&&scope.epoch===now.epoch&&scope.sessionId===now.sessionId&&now.phase==='ready'&&!now.readOnly;}
 close(){this.generation++;}
 load(){
  if(this.inflight)return this.inflight;
  const now=this.current(),scope={ticket:++this.generation,epoch:now.epoch,sessionId:now.sessionId};
  if(!this.valid(scope))return Promise.resolve(false);
  const job=this.read(scope).finally(()=>{if(this.inflight===job)this.inflight=null;});this.inflight=job;return job;
 }
 async read(scope){
  this.update({phase:'loading',snapshot:null,details:new Map(),error:null});
  try{
   const [list,workspaces]=await Promise.all([this.rpc('session.list'),this.rpc('workspace.list')]);if(!this.valid(scope))return false;
   if(!Array.isArray(list.items)||!Array.isArray(workspaces.items))throw Error('The saved conversation catalog is unavailable.');
   const archived=new Set(workspaces.archivedSessionIds??[]),rows=list.items.filter(row=>!archived.has(row.sessionId)),details=new Map(),byId=Object.create(null);
   if(rows.some(row=>typeof row.sessionId!=='string'||!row.sessionId||row.sessionId.length>128)||new Set(rows.map(row=>row.sessionId)).size!==rows.length)throw Error('Invalid saved conversation identities.');
   const coverage={sessions:rows.length,read:0,failed:0,partial:0,scanned:0,bodies:0,bodyUnavailable:0,retentionChanged:0,usageGaps:0};let next=0,leased=0;
   const worker=async()=>{while(next<rows.length&&this.valid(scope)){
    const row=rows[next++],records=[],seen=new Set();let before,firstEarliest,latestSeq,partial=false,error=null,scanned=0;
    try{
     while(this.valid(scope)){
      const limit=Math.min(500,this.maxSessionRecords-scanned,this.maxRecords-coverage.scanned-leased);
      if(limit<=0){partial=true;break;}
      leased+=limit;let page;
      try{page=await this.rpc('observation.list',{sessionId:row.sessionId,limit,...(before!==undefined?{beforeSeq:before}:{})});}finally{leased-=limit;}
      if(!this.valid(scope))return;
      if(!Array.isArray(page.records)||!Number.isSafeInteger(page.scanned)||page.scanned<0||page.scanned>limit||page.records.length!==page.scanned)throw Error('Invalid saved metadata page.');
      if(firstEarliest===undefined){firstEarliest=page.earliestSeq;latestSeq=page.latestSeq;}else if(firstEarliest!==page.earliestSeq)coverage.retentionChanged++;
      if(page.records.length&&(!Number.isSafeInteger(latestSeq)||latestSeq<1))throw Error('Invalid saved metadata high-water mark.');
      coverage.scanned+=page.scanned;scanned+=page.scanned;
      for(const record of page.records){
       if(record.sessionId!==row.sessionId||!Number.isSafeInteger(record.seq)||latestSeq!==null&&record.seq>latestSeq||before!==undefined&&record.seq>=before)throw Error('Saved metadata changed its conversation or cursor.');
       if(seen.has(record.id))throw Error('Saved metadata duplicated an observation identity.');seen.add(record.id);
       const value=insightMetadata(record);if(value)records.push(value);
      }
      if(!page.hasMore)break;
      if(!page.records.length||!Number.isSafeInteger(page.nextBeforeSeq)||page.nextBeforeSeq!==Math.min(...page.records.map(r=>r.seq))||before!==undefined&&page.nextBeforeSeq>=before)throw Error('Saved metadata paging did not advance.');
      before=page.nextBeforeSeq;
     }
    }catch(e){error=e.message;coverage.failed++;}
    if(!this.valid(scope))return;
    if(partial)coverage.partial++;
    const newest=foldInsightRecords(records).latest;let payload=null,bodyReason='No recorded request body.';
    if(!error&&newest?.payload?.state==='retained'&&Number.isSafeInteger(newest.payload.bytes)&&newest.payload.bytes>=0&&newest.payload.bytes<=1024*1024&&/^[a-f0-9]{64}$/.test(newest.payload.sha256??'')){
     try{const body=await readDshPayload(async(method,params)=>{if(!this.valid(scope))throw Error('The Context Insights scope changed.');return this.rpc(method,params);},row.sessionId,newest,{maxBytes:1024*1024});if(body.available){payload=body.value;bodyReason=null;}else bodyReason=body.reason;}catch(e){bodyReason=e.message;}
    }else if(newest)bodyReason='Newest body unavailable, oversized or missing its captured identity.';
    if(!this.valid(scope))return;
    const value=insightProjection(records,payload);if(!value.currentAvailable)bodyReason??='Newest provider format cannot be projected.';
    coverage.usageGaps+=Object.values(value.summary.gaps).reduce((sum,n)=>sum+n,0);details.set(row.sessionId,{...value,partial,error,bodyReason});coverage.read++;coverage[value.currentAvailable?'bodies':'bodyUnavailable']++;
    byId[row.sessionId]={...row,id:row.sessionId,projectionValues:error?{}:{contextTimeline:value.timeline,contextActivity:value.activity}};
   }};
   await Promise.all([worker(),worker()]);if(!this.valid(scope))return false;
   this.update({phase:'ready',snapshot:{ids:rows.map(row=>row.sessionId),byId,current:scope.sessionId},workspaces,details,coverage});return true;
  }catch(error){if(this.valid(scope))this.update({phase:'failed',error:error.message});return false;}
 }
}
