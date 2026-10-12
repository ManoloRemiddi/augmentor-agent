// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {projectDshContext} from './dsh-context-projection.mjs';
import {readDshPayload} from './dsh-payload.mjs';
const states=new Set(['starting','running','stopping','completed','failed','cancelled','unknown']);
const validNumber=n=>Number.isSafeInteger(n)&&n>=0;
const cacheKey=row=>row.sessionId+':'+(row.jobId??'root')+':'+row.updatedAt;
const textOf=message=>message?.content?.filter(p=>p.type==='text').map(p=>p.text).join('\n')??'';
const cut=text=>({text:text.slice(0,16384),truncated:text.length>16384});
function checked(value,sid){
 if(value?.available===false)return value;
 if(value?.available!==true||!Array.isArray(value.items)||!value.coverage||value.items.length>257)throw Error('The saved family catalogue is unavailable.');
 const rows=new Map();
 for(const row of value.items){
  if(typeof row?.sessionId!=='string'||!row.sessionId||rows.has(row.sessionId)||typeof row.title!=='string'||!validNumber(row.updatedAt)||typeof row.running!=='boolean')throw Error('The saved family catalogue is malformed.');
  if(row.relation==='root'){if(row.sessionId!==sid||rows.size!==0||typeof row.cwd!=='string')throw Error('The family root belongs to another conversation.');}
  else if(row.relation!=='delegation'||row.parentId!==sid||typeof row.jobId!=='string'||!row.jobId||!states.has(row.reportedState))throw Error('A worker identity belongs to another family.');
  rows.set(row.sessionId,row);
 }
 if(rows.get(sid)?.relation!=='root'||!['retainedJobs','agentJobs','verifiedChildren','pendingChildren','unavailableChildren'].every(k=>validNumber(value.coverage[k]))||value.coverage.retainedJobs<value.coverage.agentJobs||value.coverage.agentJobs!==value.coverage.verifiedChildren+value.coverage.pendingChildren+value.coverage.unavailableChildren||value.coverage.verifiedChildren!==rows.size-1)throw Error('Family coverage does not match its identities.');
 return {...value,rows};
}
/** UI-only family seats and bounded readers. Every promise/cache belongs to one
 * Host epoch, operator role and selected parent, with fresh job/child authority. */
export class DshContextFleetData{
 listeners=new Set();leases=0;generation=0;key=null;revision=null;rows=new Map();heads=new Map();details=new Map();jobs=new Map();bodies=new Map();aborts=new Map();queued=[];running=0;
 state={status:'idle',scope:null,catalogue:null,list:null,error:null};
 constructor(controller){this.controller=controller;this.sessions={list:{subscribe:this.subscribe,getSnapshot:()=>this.state.list},refreshSubagents:sid=>sid===this.controller.state.sessionId?this.refresh():Promise.resolve(null)};this.unsubscribe=controller.subscribe(()=>this.sync());this.sync();}
 subscribe=fn=>{this.listeners.add(fn);return()=>this.listeners.delete(fn);};
 getSnapshot=()=>this.state;
 emit(patch){this.state={...this.state,...patch};for(const fn of this.listeners)fn();}
 operator(){const s=this.controller.state;return s.phase==='ready'&&!s.readOnly&&!!s.sessionId;}
 sync(){
  const s=this.controller.state,key=[this.controller.epoch,s.readOnly,s.sessionId,s.phase].join(':');
  if(key!==this.key){this.key=key;this.retire();this.emit({scope:key,status:'idle',catalogue:null,list:null,error:null});this.revision=null;}
  if(!this.operator()||!this.leases)return;
  const revision=s.familyRevision??0;if(revision!==this.revision){this.revision=revision;void this.refresh();}
 }
 acquire(){this.leases++;this.sync();if(this.operator()&&this.state.status==='idle')void this.refresh();let held=true;return()=>{if(!held)return;held=false;if(--this.leases===0){this.retire();this.emit({status:'idle',catalogue:null,list:null,error:null});}};}
 retire(){this.dirty=false;this.generation++;for(const abort of this.aborts.keys())abort.abort();this.aborts.clear();this.rows.clear();this.heads.clear();this.details.clear();this.jobs.clear();this.bodies.clear();for(const work of this.queued.splice(0))work.resolve(null);this.loading=null;}
 valid(ticket,row){return ticket===this.generation&&this.leases>0&&this.operator()&&(!row||this.rows.get(row.sessionId)?.jobId===row.jobId&&this.rows.get(row.sessionId)?.updatedAt===row.updatedAt);}
 authority(ticket,row){return ticket===this.generation&&this.leases>0&&this.operator()&&(!row||this.rows.has(row.sessionId)&&this.rows.get(row.sessionId)?.jobId===row.jobId);}
 async rpc(method,params,ticket,row){if(!this.authority(ticket,row))throw Error('Family inspection scope changed.');const abort=new AbortController();this.aborts.set(abort,{ticket,row});try{const value=await this.controller.rpc(method,params,abort.signal);if(!this.authority(ticket,row))throw Error('Family inspection scope changed.');return value;}finally{this.aborts.delete(abort);}}
 refresh(){
  if(!this.operator()||!this.leases)return Promise.resolve(null);
  if(this.loading){this.dirty=true;return this.loading;}
  const ticket=this.generation,sid=this.controller.state.sessionId;this.emit({status:'loading',list:null,error:null});
  const pending=(async()=>{try{const value=checked(await this.rpc('session.family',{sessionId:sid},ticket),sid);if(!this.valid(ticket))return null;
   if(!value.available){this.retire();this.emit({scope:this.key+':'+this.generation,status:'unavailable',catalogue:value,list:null,error:value.reason??'Family data is unavailable.'});return null;}
   this.rows=value.rows;this.prune();this.publish(value);return value;
  }catch(error){if(this.valid(ticket)){this.retire();this.emit({scope:this.key+':'+this.generation,status:'unavailable',catalogue:null,list:null,error:error.message});}return null;
  }finally{if(this.loading===pending){this.loading=null;if(this.dirty){this.dirty=false;void this.refresh();}}}})();this.loading=pending;return pending;
 }
 publish(catalogue=this.state.catalogue){
  if(!catalogue?.available)return;
  const byId=Object.fromEntries([...this.rows].map(([id,row])=>{
   const saved=this.heads.get(cacheKey(row))?.value;
   const projections={...(row.relation==='root'?{subagentCatalog:[...this.rows.values()].filter(child=>child.relation==='delegation').map(child=>({id:child.sessionId}))}:{}),contextTimeline:saved?.timeline??null,...(saved?.pressure?{contextPressure:saved.pressure}:{}),...(saved?.usage?{tokenUsage:saved.usage}:{}),...(row.relation==='delegation'?{subagent:{mode:'one-shot',label:row.title+' · '+row.reportedState},subagentTiming:{lastTurnCompleted:row.reportedState==='completed'}}:{})};
   return [id,{...row,origin:row.relation==='delegation'?'subagent':'main',reportedState:row.relation==='delegation'?row.reportedState:'idle',blank:false,projectionValues:projections}];
  }));
  this.emit({status:'ready',catalogue,list:{byId},error:null});
 }
 prune(){const keys=new Set([...this.rows.values()].map(row=>cacheKey(row)));for(const cache of [this.heads,this.details,this.jobs])for(const key of cache.keys())if(!keys.has(key))cache.delete(key);for(const [abort,seat] of this.aborts)if(seat.row&&!this.authority(seat.ticket,seat.row))abort.abort();for(const id of this.bodies.keys())if(!this.rows.has(id))this.bodies.delete(id);this.queued=this.queued.filter(work=>{if(this.valid(work.ticket,work.row))return true;work.resolve(null);return false;});}
 schedule(run,row,ticket){return new Promise(resolve=>{this.queued.push({run,resolve,row,ticket});this.drain();});}
 drain(){while(this.running<4&&this.queued.length){const work=this.queued.shift();this.running++;Promise.resolve().then(work.run).catch(()=>null).then(work.resolve).finally(()=>{this.running--;this.drain();});}}
 ownedJob(row,ticket){const key=cacheKey(row);if(!this.jobs.has(key))this.jobs.set(key,this.rpc('session.job',{sessionId:this.controller.state.sessionId,jobId:row.jobId},ticket,row).then(value=>{const job=value?.job;if(job?.childId!==row.sessionId||job.owner!==this.controller.state.sessionId||job.id!==row.jobId)throw Error('The job no longer owns this child.');return job;}));return this.jobs.get(key);}
 headOf=id=>{
  const row=this.rows.get(id);if(!row||row.relation!=='delegation'||!this.operator()||!this.leases)return Promise.resolve(null);
  const key=cacheKey(row),known=this.heads.get(key);if(known)return known.promise;
  const ticket=this.generation,entry={value:null};entry.promise=this.schedule(async()=>{
   if(!this.valid(ticket,row))return null;const sid=this.controller.state.sessionId;
   const [job,page]=await Promise.all([this.ownedJob(row,ticket),this.rpc('session.jobObservations',{sessionId:sid,jobId:row.jobId,limit:100},ticket,row)]);
   if(!Array.isArray(page.records)||page.records.some(r=>r.sessionId!==id))throw Error('Child observations belong to another conversation.');
   const records=page.records,request=records.findLast(r=>r.kind==='model/request'&&r.payload?.state==='retained'&&validNumber(r.payload.bytes)&&r.payload.bytes<=1024*1024),payloads={};
   if(request){const identity=row.jobId+':'+request.id+':'+request.payload.sha256;let cached=this.bodies.get(id);if(cached?.identity!==identity){cached={identity,promise:readDshPayload((_method,params)=>this.rpc('session.jobPayload',{...params,sessionId:sid,jobId:row.jobId},ticket,row),id,request,{maxBytes:1024*1024}).catch(()=>({available:false}))};this.bodies.set(id,cached);}const body=await cached.promise;if(body.available)payloads[request.id]=body.value;}else this.bodies.delete(id);
   const value=projectDshContext({sessionId:id,records,payloads,events:[],hasMore:true,observationHasMore:page.hasMore===true});
   const usage=job.usage?.value,validUsage=usage&&['input','output','cacheRead','cacheWrite'].every(k=>typeof usage[k]==='number'&&Number.isFinite(usage[k])&&usage[k]>=0);
   const timeline={ok:true,augmentorCompositionAvailable:value.coverage.latestAvailable===true,model:value.timeline.model,provider:value.timeline.provider,contextWindow:value.timeline.contextWindow,current:value.timeline.current,requests:[],events:[],nodes:[],archive:[],...(validNumber(row.reportedRequests)?{counts:{steps:row.reportedRequests}}:{})};
   if(!this.valid(ticket,row))return null;
   entry.value={timeline,pressure:value.pressure,usage:validUsage?{uncachedInputTokens:usage.input,outputTokens:usage.output,cacheReadTokens:usage.cacheRead,cacheWriteTokens:usage.cacheWrite}:null};this.publish();return timeline;
  },row,ticket);this.heads.set(key,entry);return entry.promise;
 };
 invalidateDetail(id){const row=this.rows.get(id);if(row){const key=cacheKey(row);this.details.delete(key);this.jobs.delete(key);this.heads.delete(key);this.bodies.delete(id);this.publish();}}
 detailOf=id=>{
  const row=this.rows.get(id);if(!row||!this.operator()||!this.leases)return Promise.resolve(null);
  const key=cacheKey(row);if(this.details.has(key))return this.details.get(key);
  const ticket=this.generation,pending=this.schedule(async()=>{
   if(!this.valid(ticket,row))return null;const sid=this.controller.state.sessionId,isChild=row.relation==='delegation';
   const [job,history]=await Promise.all([isChild?this.ownedJob(row,ticket):null,this.rpc(isChild?'session.jobHistory':'session.history',{sessionId:sid,...(isChild?{jobId:row.jobId}:{}),maxMessages:30},ticket,row)]);
   if(isChild&&history.childId!==row.sessionId)throw Error('Child history belongs to another conversation.');
   const events=(history.events??[]).map(r=>r.event),reply=events.findLast(e=>e.type==='assistant/message')?.data?.message,body=cut(textOf(reply)),first=history.hasMore?undefined:events.find(e=>e.type==='user/message'),task=isChild?job.spec.task:first?.data?.content?.filter(p=>p.type==='text').map(p=>p.text).join('\n');
   const prompt=typeof task==='string'?cut(task):null;
   if(!this.valid(ticket,row))return null;
   return {descriptor:isChild?{mode:'one-shot',label:row.title,...(job.usage?.provider?{provider:job.usage.provider}:{}),...(job.usage?.model?{agentModel:job.usage.model}:{})}:undefined,...(prompt?{initialPrompt:prompt.text}:{}),...(body.text&&validNumber(reply?.timestamp)?{lastReply:{time:reply.timestamp,text:body.text}}:{}),messages:[],truncated:history.hasMore===true||body.truncated||prompt?.truncated===true};
  },row,ticket);this.details.set(key,pending);return pending;
 };
 async open(id,show){const row=this.rows.get(id),ticket=this.generation;if(!row||row.relation!=='delegation'||!this.valid(ticket,row))throw Error('This worker is no longer available in the selected family.');const link=await this.rpc('session.jobInspection',{sessionId:this.controller.state.sessionId,jobId:row.jobId},ticket,row);const url=new URL(link.url,location.href);if(!['http:','https:'].includes(url.protocol)||url.pathname!=='/'||url.origin!==location.origin||link.mode!=='read-only'||link.sessionId!==id)throw Error('The child inspector scope is invalid.');show(url.href);}
 close(){this.leases=0;this.retire();this.unsubscribe();this.listeners.clear();}
}
