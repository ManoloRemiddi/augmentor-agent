// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {readDshPayload} from './dsh-payload.mjs';
import {appendDisplay} from './chat-projection.js';

/** Browser transport to the existing Pi Host; never owns an agent or retries a mutation. */
export class DshPiController {
  listeners=new Set(); epoch=0; polling=false; cursor=0; clientId=crypto.randomUUID();
  state={phase:'connecting',sessionId:null,readOnly:false,sessions:[],events:[],records:[],payloads:{},contextRequestId:null,contextRead:null,contextPage:null,queue:null,interactions:[],catalog:{groups:[]},selection:null,reasoning:null,goal:null,workspace:'',error:null,hasMore:false};
  constructor(token,fetcher=fetch){this.token=token;this.fetcher=(...args)=>fetcher(...args);}
  subscribe=fn=>{this.listeners.add(fn);return()=>this.listeners.delete(fn);};
  getSnapshot=()=>this.state;
  update(patch){this.state={...this.state,...patch};for(const fn of this.listeners)fn();}
  async rpc(method,params={}){
    const response=await this.fetcher('/api/rpc',{method:'POST',headers:{Authorization:'Bearer '+this.token,'Content-Type':'application/json'},body:JSON.stringify({id:crypto.randomUUID(),method,params})});
    const body=await response.json();if(!response.ok||body.error){const error=Error(body.error?.message||'The local connection failed.');error.authoritative=!!body.error;throw error;}return body.result;
  }
  async start(requestedSession){
    const access=await this.fetcher('/api/access',{headers:{Authorization:'Bearer '+this.token}}).then(async r=>{const v=await r.json();if(!r.ok)throw Error(v.error?.message||'Open a fresh Harness link.');return v;});
    const [host,catalog,list]=await Promise.all([this.rpc('host.describe'),this.rpc('models.list'),this.rpc('session.list')]);
    const workspaces=access.mode==='read-only'?null:await this.rpc('workspace.list');
    this.update({readOnly:access.mode==='read-only',catalog,workspace:host.workspace,workspaces,sessions:list.items,phase:'ready',attachmentLimits:host.attachmentLimits});
    const selected=access.sessionId||requestedSession||sessionStorage.getItem('augmentor-harness-session');
    const available=list.items.filter(x=>access.mode==='read-only'||!workspaces?.archivedSessionIds?.includes(x.sessionId));
    const row=available.find(x=>x.sessionId===selected)||available[0];
    if(row)await this.open(row.sessionId);
  }
  async open(sessionId){
    if(!this.state.readOnly&&this.state.workspaces?.archivedSessionIds?.includes(sessionId))throw Error('Restore the conversation before opening it.');
    const epoch=++this.epoch;
    this.update({sessionId,unconfirmed:this.pending.get(sessionId)||null,compaction:null,compactionPending:false,phase:'loading',events:[],records:[],payloads:{},contextRequestId:null,contextRead:null,contextPage:null,queue:null,interactions:[],selection:null,reasoning:null,goal:null,hasMore:false,error:null});
    const sub=await this.rpc('events.subscribe',{sessionId,clientId:this.clientId});if(epoch!==this.epoch)return;
    this.cursor=sub.cursor;
    const [history,observations,model,queue,goal,compaction]=await Promise.all([
      this.rpc('session.history',{sessionId,maxMessages:100}),this.rpc('observation.list',{sessionId}),this.rpc('session.models',{sessionId}),this.rpc('session.queue',{sessionId}),this.rpc('session.goal',{sessionId}),this.rpc('session.compaction',{sessionId}),
    ]);
    if(epoch!==this.epoch)return;
    const reasoning=this.state.readOnly?null:await this.rpc('session.reasoning',{sessionId});if(epoch!==this.epoch)return;
    sessionStorage.setItem('augmentor-harness-session',sessionId);
    this.update({events:history.events.map(x=>x.event),hasMore:history.hasMore===true,observationHasMore:observations.hasMore===true,records:observations.records,selection:model.current,queue,goal,reasoning,compaction,interactions:sub.pending,phase:'ready'});
    void this.hydrate().catch(error=>{if(epoch===this.epoch)this.update({error:error.message});});
  }
  hydrating=null;contextPayloadReads=new Map();contextPaging=null;
  eligibleContext(record){return record?.kind==='model/request'&&record.payload?.state==='retained'&&Number.isSafeInteger(record.payload.bytes)&&record.payload.bytes>=0&&record.payload.bytes<=1024*1024;}
  contextBodies(){
    const records=this.state.records.filter(r=>this.eligibleContext(r)),latest=records.slice(-8),selected=records.find(r=>r.id===this.state.contextRequestId);
    return [...latest,...(selected&&!latest.includes(selected)?[selected]:[])];
  }
  trimContextBodies(){
    const ids=new Set(this.contextBodies().map(r=>r.id)),payloads=Object.fromEntries(Object.entries(this.state.payloads).filter(([id])=>ids.has(id)));
    if(Object.keys(payloads).length!==Object.keys(this.state.payloads).length)this.update({payloads});
  }
  readContextBody(record,epoch=this.epoch,sessionId=this.state.sessionId){
    const key=epoch+':'+record.id;if(this.contextPayloadReads.has(key))return this.contextPayloadReads.get(key);
    const promise=readDshPayload((m,p)=>this.rpc(m,p),sessionId,record,{maxBytes:1024*1024}).then(result=>{
      if(epoch===this.epoch&&sessionId===this.state.sessionId&&result.available&&this.contextBodies().some(r=>r.id===record.id))this.update({payloads:{...this.state.payloads,[record.id]:result.value}});
      return result;
    }).finally(()=>{if(this.contextPayloadReads.get(key)===promise)this.contextPayloadReads.delete(key);});
    this.contextPayloadReads.set(key,promise);return promise;
  }
  async hydrate(){
    const epoch=this.epoch,sessionId=this.state.sessionId;this.trimContextBodies();if(this.hydrating?.epoch===epoch){this.hydrating.dirty=true;return this.hydrating.promise;}
    const job={epoch,dirty:false};this.hydrating=job;
    job.promise=(async()=>{do{job.dirty=false;this.trimContextBodies();for(const record of this.contextBodies()){
      if(epoch!==this.epoch)return;if(!this.state.payloads[record.id]&&this.contextBodies().some(r=>r.id===record.id))await this.readContextBody(record,epoch,sessionId);
    }}while(job.dirty&&epoch===this.epoch);})();
    try{await job.promise;}finally{if(this.hydrating===job)this.hydrating=null;}
  }
  async selectContextRequest(requestId){
    const epoch=this.epoch,sessionId=this.state.sessionId;if(!sessionId||this.state.phase!=='ready')return;
    const record=requestId===null?null:this.state.records.find(r=>r.id===requestId&&r.kind==='model/request');if(requestId!==null&&!record)throw Error('This recorded request is no longer loaded.');
    this.update({contextRequestId:requestId,contextRead:record?{id:requestId,state:'loading'}:null});this.trimContextBodies();if(!record)return;
    let read;
    try{
      if(!this.eligibleContext(record))read={id:requestId,state:'unavailable',reason:record.payload?.state==='retained'?'This recorded body exceeds the dashboard’s 1 MiB limit; use the raw inspector.':'This request body was not retained or is no longer available.'};
      else if(this.state.payloads[requestId])read={id:requestId,state:'ready'};
      else{const result=await this.readContextBody(record,epoch,sessionId);read={id:requestId,state:result.available?'ready':'unavailable',...(!result.available?{reason:'Recorded body unavailable: '+result.reason}:{})};}
    }catch(error){read={id:requestId,state:'failed',reason:error.message};}
    if(epoch===this.epoch&&sessionId===this.state.sessionId&&requestId===this.state.contextRequestId)this.update({contextRead:read});
  }
  async loadContextOlder(){
    const epoch=this.epoch,sessionId=this.state.sessionId;if(!sessionId||this.state.phase!=='ready'||!this.state.observationHasMore)return;
    if(this.contextPaging?.epoch===epoch)return this.contextPaging.promise;
    const beforeSeq=this.state.records[0]?.seq,job={epoch};this.contextPaging=job;this.update({contextPage:{loading:true,error:null}});
    job.promise=(async()=>{try{
      if(!Number.isSafeInteger(beforeSeq))throw Error('The earlier observation cursor is unavailable.');
      const page=await this.rpc('observation.list',{sessionId,beforeSeq,limit:100});if(epoch!==this.epoch||sessionId!==this.state.sessionId)return;
      if(page.hasMore&&(!page.records.length||page.records[0].seq>=beforeSeq))throw Error('The earlier observation cursor did not advance.');
      const records=new Map([...page.records,...this.state.records].map(r=>[r.id,r]));this.update({records:[...records.values()].sort((a,b)=>a.seq-b.seq),observationHasMore:page.hasMore===true,contextPage:{loading:false,error:null}});
    }catch(error){if(epoch===this.epoch)this.update({contextPage:{loading:false,error:error.message}});}})();
    try{await job.promise;}finally{if(this.contextPaging===job)this.contextPaging=null;}
  }
  clearSelection(){this.epoch++;globalThis.sessionStorage?.removeItem('augmentor-harness-session');this.update({sessionId:null,events:[],records:[],payloads:{},contextRequestId:null,contextRead:null,contextPage:null,queue:null,goal:null,compaction:null,compactionPending:false,interactions:[],selection:null,reasoning:null,hasMore:false,unconfirmed:null,phase:'ready'});}
  async refresh(){const [list,workspaces]=await Promise.all([this.rpc('session.list'),this.state.readOnly?null:this.rpc('workspace.list')]);this.update({sessions:list.items,workspaces});if(!this.state.readOnly&&workspaces?.archivedSessionIds?.includes(this.state.sessionId))this.clearSelection();}
  async organize(action,sessionId,stop=false){
    if(this.state.readOnly)throw Error('This conversation inspector is read-only.');
    try{const result=await this.rpc('session.organize',{sessionId,action,stop,expectedRevision:this.state.workspaces?.organizationRevision});this.update({workspaces:result.workspaces});if(result.workspaces.archivedSessionIds.includes(this.state.sessionId))this.clearSelection();return result;}
    catch(error){await this.refresh().catch(()=>{});throw error;}
  }
  async forkLast(sessionId){
    if(this.state.readOnly)throw Error('This conversation inspector is read-only.');
    const history=await this.rpc('session.history',{sessionId,maxMessages:100}),last=[...history.events].reverse().find(x=>x.event.type==='assistant/message'&&x.event.data?.message?.stopReason==='stop');
    if(!last)throw Error('This conversation has no completed assistant turn to fork.');
    const row=await this.rpc('session.branch',{sessionId,newSessionId:crypto.randomUUID(),messageSeq:last.event.seq,mode:'reply'});await this.refresh();await this.open(row.sessionId);return row;
  }
  async workspaceAction(action,params={}){
    if(this.state.readOnly)throw Error('This conversation inspector is read-only.');
    try{const workspaces=await this.rpc('workspace.'+action,{...params,expectedRevision:this.state.workspaces?.revision});this.update({workspaces});return workspaces;}
    catch(error){await this.refresh().catch(()=>{});throw error;}
  }
  async adoptWorkspace(path){const snapshot=await this.workspaceAction('adopt',{path});return snapshot.items.find(x=>x.workspaceId===snapshot.adoptedWorkspaceId);}
  async poll(){
    if(this.polling||!this.state.sessionId||this.state.phase!=='ready')return;
    this.polling=true;const sessionId=this.state.sessionId,epoch=this.epoch;
    try{
      const res=await this.fetcher('/api/events?'+new URLSearchParams({sessionId,clientId:this.clientId,after:String(this.cursor)}),{headers:{Authorization:'Bearer '+this.token}});
      const page=await res.json();if(!res.ok||page.error)throw Error(page.error?.message||'The event connection failed.');if(epoch!==this.epoch)return;
      this.cursor=page.cursor;
      const events=[...this.state.events],records=new Map(this.state.records.map(x=>[x.id,x])),interactions=new Map(this.state.interactions.map(x=>[x.rpcId,x]));let queue=this.state.queue,changed=false;
      for(const {frame} of page.frames){
        if(frame.method==='session/event'){appendDisplay(events,frame.payload.event);changed=true;}
        if(frame.method==='observation/event'){const r=frame.payload.observation;records.set(r.id,r);changed=true;}
        if(frame.method==='session/queue'){queue=frame.payload;changed=true;}
        if(frame.method==='session/compaction'){const info=frame.payload,row=info.lastReceipt;this.update({compaction:info,...(row?.state==='failed'?{error:'Pi did not save a compaction summary. This conversation may be too small or already compacted, or its summary request failed. Inspect Context for the recorded attempt.'}:{})});changed=true;}
        if(['approval/requested','question/requested'].includes(frame.method)){interactions.set(frame.rpcId,frame);changed=true;}
        if(frame.method==='interaction/updated'){const old=interactions.get(frame.rpcId);if(old?.method==='question/requested'&&(old.payload.wait?.revision??-1)<=frame.payload.wait?.revision){interactions.set(frame.rpcId,{...old,payload:{...old.payload,wait:frame.payload.wait}});changed=true;}}
        if(['interaction/resolved'].includes(frame.method)){interactions.delete(frame.rpcId);this.heldQuestions.delete(frame.rpcId);changed=true;}
      }
      if(changed)this.update({events,records:[...records.values()].sort((a,b)=>a.seq-b.seq),queue,interactions:[...interactions.values()]});
      if(changed)void this.hydrate().catch(error=>{if(epoch===this.epoch)this.update({error:error.message});});
      if(page.gap){await this.open(sessionId);return;}
      if(page.frames.length||!this.lastRefresh||Date.now()-this.lastRefresh>3000){this.lastRefresh=Date.now();await this.refresh();}
      if(page.frames.some(({frame})=>frame.method==='goal/updated')){const goal=await this.rpc('session.goal',{sessionId});if(epoch===this.epoch)this.update({goal});}
      for(const [key,held] of this.heldQuestions){
        const frame=this.state.interactions.find(x=>x.rpcId===key);
        if(held.epoch!==this.epoch||held.sessionId!==this.state.sessionId||frame?.payload.wait?.state!=='focused'){this.heldQuestions.delete(key);continue;}
        if(Date.now()-held.lastRenew>=4000)await this.questionWait(frame,'hold-focus');
      }
    }finally{this.polling=false;}
  }
  async create(cwd=this.state.workspace){
    if(this.state.readOnly)throw Error('This conversation inspector is read-only.');
    const selection=this.state.selection||this.state.catalog.default;if(!selection)throw Error('Choose a model first.');
    const sessionId=crypto.randomUUID();await this.rpc('session.create',{sessionId,selection,cwd});await this.refresh();await this.open(sessionId);
  }
  pending=new Map();
  heldQuestions=new Map();
  interactionScope(frame){
    const sessionId=this.state.sessionId,epoch=this.epoch;
    if(this.state.readOnly||this.state.phase!=='ready'||!sessionId||frame.payload?.sessionId&&frame.payload.sessionId!==sessionId||!this.state.interactions.some(x=>x.rpcId===frame.rpcId&&x.method===frame.method))throw Error('This interaction is no longer selected. Nothing was sent.');
    return {sessionId,epoch};
  }
  updateQuestionWait(rpcId,wait,epoch=this.epoch){
    if(epoch!==this.epoch||!wait)return;
    this.update({interactions:this.state.interactions.map(frame=>frame.rpcId===rpcId&&frame.method==='question/requested'&&(frame.payload.wait?.revision??-1)<=wait.revision?{...frame,payload:{...frame.payload,wait}}:frame)});
  }
  async questionWait(frame,action){
    const scope=this.interactionScope(frame);
    if(frame.method!=='question/requested')throw Error('Only questions have wait controls.');
    if(action==='hold-focus')this.heldQuestions.set(frame.rpcId,{frame,...scope,lastRenew:Date.now()});
    else this.heldQuestions.delete(frame.rpcId);
    try{
      const result=await this.rpc('interaction.wait',{sessionId:scope.sessionId,clientId:this.clientId,rpcId:frame.rpcId,action});
      this.updateQuestionWait(frame.rpcId,result.wait,scope.epoch);
      return result;
    }catch(error){this.heldQuestions.delete(frame.rpcId);throw error;}
  }
  async compact(scope){
    const {sessionId,selection}=this.state,epoch=this.epoch;
    if(scope.sessionId!==sessionId||scope.epoch!==epoch||this.state.readOnly||this.state.phase!=='ready'||this.state.sessions.find(x=>x.sessionId===sessionId)?.running||this.state.compaction?.blocked||this.pending.has(sessionId))throw Error('The conversation is not ready to compact. Your draft is preserved.');
    const requestId=crypto.randomUUID(),receipt={kind:'compaction',requestId,provider:selection.provider,model:selection.model};this.pending.set(sessionId,receipt);this.update({compactionPending:true});
    let result;
    try{result=await this.rpc('session.compact',{sessionId,...receipt});this.pending.delete(sessionId);}
    catch(error){if(error.authoritative)this.pending.delete(sessionId);if(epoch===this.epoch)this.update({compactionPending:false,...(!error.authoritative?{unconfirmed:receipt}:{})});throw Error(error.message+(!error.authoritative?' Compaction submission is unconfirmed; nothing was resent.':''));}
    if(epoch===this.epoch)this.update({compaction:result,compactionPending:false});
    void this.refresh().catch(()=>{});return result;
  }
  clearUnconfirmed(){this.pending.delete(this.state.sessionId);this.update({unconfirmed:null});}
  async send(text,mode='queue',attachments=[]){
    const {sessionId,queue}=this.state;if(!sessionId)throw Error('Choose a workspace first.');
    if(this.state.readOnly||this.state.phase!=='ready')throw Error('The conversation is not ready for submission.');
    if(this.state.workspaces?.archivedSessionIds?.includes(sessionId))throw Error('Restore the conversation before sending.');
    if(this.pending.has(sessionId))throw Error('The previous submission is unconfirmed. Inspect the history; it was not retried.');
    const requestId=crypto.randomUUID(),receipt={requestId,text,attachments};this.pending.set(sessionId,receipt);
    try{const result=await this.rpc('session.prompt',{sessionId,requestId,content:[...(text?[{type:'text',text}]:[]),...attachments],mode,resumeQueue:true,...(mode==='steer'?{expectedTurnId:queue?.activeTurnId}:{})});this.pending.delete(sessionId);return result;}
    catch(error){if(sessionId===this.state.sessionId)this.update({unconfirmed:receipt});throw Error(error.message+' Submission is unconfirmed. Nothing was resent.');}
  }
  edits=new Map();
  async updateQueue(itemId,action){
    const {sessionId,queue}=this.state;
    let edit={};if(action.kind==='edit'){
      const key=JSON.stringify([sessionId,itemId,action.content]);
      if(!this.edits.has(key))this.edits.set(key,crypto.randomUUID());
      edit={newItemId:this.edits.get(key),expectedRevision:queue.revision};
    }
    const value=await this.rpc('session.updateQueue',{sessionId,itemId,expectedTurnId:queue?.activeTurnId,action,...edit});
    if(sessionId===this.state.sessionId)this.update({queue:value});return value;
  }
  async answer(frame,value){
    const {sessionId,epoch}=this.interactionScope(frame);this.heldQuestions.delete(frame.rpcId);
    await this.rpc('interaction.respond',{sessionId,clientId:this.clientId,rpcId:frame.rpcId,value});
    if(epoch===this.epoch)this.update({interactions:this.state.interactions.filter(x=>x.rpcId!==frame.rpcId)});
  }
  async stop(){await this.rpc('session.cancel',{sessionId:this.state.sessionId});await this.refresh();}
  async older(){
    const epoch=this.epoch,sessionId=this.state.sessionId,beforeSeq=this.state.events[0]?.seq;
    const page=await this.rpc('session.history',{sessionId,maxMessages:100,beforeSeq});if(epoch!==this.epoch)return;
    const merged=new Map([...page.events.map(x=>x.event),...this.state.events].map(x=>[x.seq,x]));this.update({events:[...merged.values()].sort((a,b)=>a.seq-b.seq),hasMore:page.hasMore===true});
  }
  async choose(selection){
    const sessionId=this.state.sessionId,epoch=this.epoch;if(!sessionId)throw Error('Choose a workspace first.');
    let current=this.state.selection;
    if(selection.provider!==current.provider||selection.model!==current.model)current=(await this.rpc('session.selectModel',{sessionId,provider:selection.provider,model:selection.model})).current;
    const reasoning=await this.rpc('session.reasoning',{sessionId});
    const updated=selection.reasoningEffort===undefined?reasoning:await this.rpc('session.selectReasoning',{sessionId,mode:'manual',thinkingLevel:selection.reasoningEffort,expectedRevision:reasoning.revision});
    if(epoch===this.epoch)this.update({selection:current,reasoning:updated});
  }
}
