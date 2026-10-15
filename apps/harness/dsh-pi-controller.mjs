// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {readDshPayload} from './dsh-payload.mjs';
import {checkedSessionPermission} from './dsh-session-permissions.mjs';
import {appendDisplay,messageTargets} from './chat-projection.js';

/** Browser transport to the existing Pi Host; never owns an agent or retries a mutation. */
export class DshPiController {
  listeners=new Set(); epoch=0; polling=false; cursor=0; clientId=crypto.randomUUID();
  branchFlight=null; branchIntents=new Map();createFlight=null;
  catalogRevision=0;catalogRead=0;
  state={familyRevision:0,phase:'connecting',sessionId:null,readOnly:false,capabilities:{},sessions:[],events:[],records:[],payloads:{},contextRequestId:null,contextRead:null,contextPage:null,queue:null,interactions:[],catalog:{groups:[]},selection:null,reasoning:null,permission:null,permissionBusy:false,permissionError:null,planMode:null,goal:null,workspace:'',error:null,hasMore:false};
  constructor(token,fetcher=fetch){this.token=token;this.fetcher=(...args)=>fetcher(...args);}
  subscribe=fn=>{this.listeners.add(fn);return()=>this.listeners.delete(fn);};
  getSnapshot=()=>this.state;
  update(patch){if(Object.hasOwn(patch,'workspaces'))this.catalogRevision++;this.state={...this.state,...patch};for(const [id,scope] of this.hiddenQuestions)if(this.state.readOnly||this.state.phase!=='ready'||scope.epoch!==this.epoch||scope.sessionId!==this.state.sessionId||!this.state.interactions.some(f=>f.rpcId===id))this.hiddenQuestions.delete(id);for(const fn of this.listeners)fn();}
  async rpc(method,params={},signal){
    const response=await this.fetcher('/api/rpc',{method:'POST',headers:{Authorization:'Bearer '+this.token,'Content-Type':'application/json'},body:JSON.stringify({id:crypto.randomUUID(),method,params}),...(signal?{signal}:{})});
    const body=await response.json();if(!response.ok||body.error){const error=Error(body.error?.message||'The local connection failed.');error.authoritative=!!body.error;throw error;}return body.result;
  }
  async start(requestedSession){
    const access=await this.fetcher('/api/access',{headers:{Authorization:'Bearer '+this.token}}).then(async r=>{const v=await r.json();if(!r.ok)throw Error(v.error?.message||'Open a fresh Harness link.');return v;});
    const [host,catalog,list]=await Promise.all([this.rpc('host.describe'),this.rpc('models.list'),this.rpc('session.list')]);
    const workspaces=access.mode==='read-only'?null:await this.rpc('workspace.list');
    this.update({modelsRevision:undefined,readOnly:access.mode==='read-only',catalog,workspace:host.workspace,workspaces,sessions:list.items,phase:'ready',attachmentLimits:host.attachmentLimits,capabilities:host.capabilities??{}});
    const selected=access.sessionId||requestedSession||sessionStorage.getItem('augmentor-harness-session');
    const available=list.items.filter(x=>access.mode==='read-only'||!workspaces?.archivedSessionIds?.includes(x.sessionId));
    const row=available.find(x=>x.sessionId===selected)||available[0];
    if(row)await this.open(row.sessionId);
  }
  async open(sessionId){
    if(!this.state.readOnly&&this.state.workspaces?.archivedSessionIds?.includes(sessionId))throw Error('Restore the conversation before opening it.');
    const epoch=++this.epoch;
    this.update({sessionId,unconfirmed:this.pending.get(sessionId)||null,compaction:null,compactionPending:false,phase:'loading',events:[],records:[],payloads:{},contextRequestId:null,contextRead:null,contextPage:null,queue:null,interactions:[],selection:null,reasoning:null,permission:null,permissionBusy:false,permissionError:null,planMode:null,goal:null,hasMore:false,error:null});
    const sub=await this.rpc('events.subscribe',{sessionId,clientId:this.clientId});if(epoch!==this.epoch)return;
    this.cursor=sub.cursor;
    const [history,observations,model,queue,goal,compaction]=await Promise.all([
      this.rpc('session.history',{sessionId,maxMessages:100}),this.rpc('observation.list',{sessionId}),this.rpc('session.models',{sessionId}),this.rpc('session.queue',{sessionId}),this.rpc('session.goal',{sessionId}),this.rpc('session.compaction',{sessionId}),
    ]);
    if(epoch!==this.epoch)return;
    const reasoning=this.state.readOnly?null:await this.rpc('session.reasoning',{sessionId});if(epoch!==this.epoch)return;
    sessionStorage.setItem('augmentor-harness-session',sessionId);
    this.update({events:history.events.map(x=>x.event),hasMore:history.hasMore===true,observationHasMore:observations.hasMore===true,records:observations.records,selection:model.current,queue,goal,reasoning,compaction,interactions:sub.pending,phase:'ready'});
    this.permissionUnconfirmed=false;
    if(this.state.capabilities?.sessionPermissions)await this.refreshPermission({sessionId,epoch},{explicit:true});
    if(this.state.capabilities?.planMode)await this.refreshPlanMode({sessionId,epoch});
    void this.hydrate().catch(error=>{if(epoch===this.epoch)this.update({error:error.message});});
  }
  permissionRead=0;permissionMutation=null;permissionUnconfirmed=false;
  async refreshPermission(scope={sessionId:this.state.sessionId,epoch:this.epoch},{explicit=false}={}){
    if(!this.modeScope(scope)||!this.state.capabilities?.sessionPermissions||this.permissionUnconfirmed&&!explicit)return;
    if(this.permissionMutation&&this.modeScope(this.permissionMutation)){this.permissionMutation.needsRefresh=true;return;}
    const ticket=++this.permissionRead;this.update({permissionBusy:true});
    try{const value=checkedSessionPermission(await this.rpc('session.permission',{sessionId:scope.sessionId}));if(this.modeScope(scope)&&ticket===this.permissionRead){this.permissionUnconfirmed=false;this.update({permission:value,permissionBusy:false,permissionError:null});return value;}}
    catch(error){if(this.modeScope(scope)&&ticket===this.permissionRead){this.permissionUnconfirmed=true;this.update({permission:null,permissionBusy:false,permissionError:error.message});}}
  }
  async selectPermission(preset,scope={sessionId:this.state.sessionId,epoch:this.epoch,revision:this.state.permission?.revision}){
    if(!this.modeScope(scope)||this.state.readOnly||!this.state.capabilities?.sessionPermissions||!this.state.permission?.canSelect||this.state.permissionBusy||this.permissionUnconfirmed||scope.revision!==this.state.permission.revision||!this.state.permission.options.some(x=>x.value===preset))throw Error('Refresh the current operator permission mode before choosing again.');
    const operation={...scope};this.permissionMutation=operation;++this.permissionRead;this.update({permissionBusy:true,permissionError:null});
    try{
      const result=await this.rpc('session.selectPermission',{sessionId:scope.sessionId,preset,expectedRevision:scope.revision});if(!this.modeScope(scope))return {accepted:false,retired:true};if(result?.accepted!==true)throw Error('The permission change was not acknowledged.');const receipt=checkedSessionPermission(result);if(receipt.currentValue!==preset||(preset!==this.state.permission?.currentValue&&receipt.revision===scope.revision))throw Error('The permission receipt does not confirm the selected mode.');
      if(this.permissionMutation===operation)this.permissionMutation=null;
      this.permissionUnconfirmed=false;this.update({permission:receipt,permissionBusy:false,permissionError:null});
      // A notification received while the write was pending may be newer than
      // its accepted receipt. Reconcile by reading, never by repeating a choice.
      if(operation.needsRefresh)await this.refreshPermission(scope,{explicit:true});
      if(!this.modeScope(scope))return {accepted:false,retired:true};return {accepted:true,...receipt};
    }catch(error){if(this.modeScope(scope)){this.permissionUnconfirmed=true;this.update({permission:null,permissionBusy:false,permissionError:error.message,error:error.message+' Nothing was retried. Refresh permission mode to inspect the saved choice.'});}throw error;}
    finally{if(this.permissionMutation===operation)this.permissionMutation=null;}
  }
  planModeRead=0;
  modeScope(scope){return scope?.epoch===this.epoch&&scope.sessionId===this.state.sessionId&&this.state.phase==='ready';}
  async refreshPlanMode(scope={sessionId:this.state.sessionId,epoch:this.epoch}){
    if(!this.modeScope(scope)||!this.state.capabilities?.planMode)return;
    const ticket=++this.planModeRead;
    try{const planMode=await this.rpc('session.planMode',{sessionId:scope.sessionId});if(this.modeScope(scope)&&ticket===this.planModeRead)this.update({planMode});}
    catch(error){if(this.modeScope(scope)&&ticket===this.planModeRead)throw error;}
  }
  async setPlanMode(active,scope={sessionId:this.state.sessionId,epoch:this.epoch}){
    if(!this.modeScope(scope)||this.state.readOnly||!this.state.capabilities?.planMode||!this.state.planMode?.available)throw Error('Refresh the current operator conversation before changing plan mode.');
    ++this.planModeRead;
    const result=await this.rpc('session.setPlanMode',{sessionId:scope.sessionId,active,expectedRevision:this.state.planMode.revision});
    await this.refreshPlanMode(scope);return {accepted:true,...result};
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
  clearSelection(){this.epoch++;globalThis.sessionStorage?.removeItem('augmentor-harness-session');this.update({sessionId:null,events:[],records:[],payloads:{},contextRequestId:null,contextRead:null,contextPage:null,queue:null,goal:null,planMode:null,compaction:null,compactionPending:false,interactions:[],selection:null,reasoning:null,permission:null,permissionBusy:false,permissionError:null,hasMore:false,unconfirmed:null,phase:'ready'});}
  async refresh(){
    const epoch=this.epoch,sessionId=this.state.sessionId,readOnly=this.state.readOnly,revision=this.catalogRevision,read=++this.catalogRead;
    // A confirmed catalog update invalidates reads already in flight, including
    // reads started during its mutation. Only the latest read may commit.
    const current=()=>epoch===this.epoch&&sessionId===this.state.sessionId&&readOnly===this.state.readOnly&&revision===this.catalogRevision&&read===this.catalogRead;
    let list,workspaces;
    try{
      [list,workspaces]=await Promise.all([this.rpc('session.list'),readOnly?null:this.rpc('workspace.list')]);
    }catch(error){if(current())throw error;return;}
    if(!current())return;
    this.update({sessions:list.items,workspaces});
    if(!readOnly&&workspaces?.archivedSessionIds?.includes(this.state.sessionId))this.clearSelection();
  }
  async organize(action,sessionId,stop=false){
    if(this.state.readOnly)throw Error('This conversation inspector is read-only.');
    try{const result=await this.rpc('session.organize',{sessionId,action,stop,expectedRevision:this.state.workspaces?.organizationRevision});this.update({workspaces:result.workspaces});if(result.workspaces.archivedSessionIds.includes(this.state.sessionId))this.clearSelection();return result;}
    catch(error){await this.refresh().catch(()=>{});throw error;}
  }
  forkAt(messageSeq,canSelect=()=>true){return this.forkBoundary(this.state.sessionId,messageSeq,canSelect);}
  forkLast(sessionId,canSelect=()=>true){return this.forkBoundary(sessionId,null,canSelect);}
  async forkBoundary(sessionId,messageSeq,canSelect){
    // One explicit UI action. The Host retains prepared child identity across
    // process replacement; cleanup never retries branch creation or inference.
    if(this.branchFlight)return null;
    const scope={epoch:this.epoch,sessionId:this.state.sessionId};
    const current=()=>scope.epoch===this.epoch&&scope.sessionId===this.state.sessionId&&!this.state.readOnly;
    const durable=this.state.capabilities?.durableBranches===true;
    const flight={sessionId,messageSeq};let intent,key,attempted=false,creationConfirmed=false,warning=null;
    const matches=row=>row?.sessionId===intent.newSessionId&&row?.fork?.sessionId===sessionId&&row?.fork?.messageSeq===messageSeq&&row?.fork?.mode==='reply';
    const releaseUncreated=async()=>{
      const row=await this.rpc('session.settleBranch',{...intent,outcome:'not-created'});
      return row?.settled===true&&row?.outcome==='not-created'&&row?.newSessionId===intent.newSessionId;
    };
    this.branchFlight=flight;
    try{
      if(this.state.readOnly)throw Error('This conversation inspector is read-only.');
      if(this.state.phase!=='ready'||!sessionId||this.state.unconfirmed||this.state.compactionPending||this.state.compaction?.blocked)throw Error('Review the current conversation state before branching.');
      if(this.state.sessions.find(row=>row.sessionId===sessionId)?.running)throw Error('Stop the current response before branching.');
      if(messageSeq!==null&&(!Number.isSafeInteger(messageSeq)||!messageTargets(this.state.events).replies.has(messageSeq)))throw Error('Choose a loaded assistant reply after its tools have finished.');
      this.update({branchPending:flight,error:null});
      if(messageSeq===null){
        const history=await this.rpc('session.history',{sessionId,maxMessages:100});
        if(!current())return null;
        const last=[...history.events].reverse().find(x=>x.event.type==='assistant/message'&&x.event.data?.message?.stopReason==='stop');
        if(!last||!Number.isSafeInteger(last.event.seq)||last.event.seq<1)throw Error('This conversation has no completed assistant reply in its recent history.');
        messageSeq=last.event.seq;
      }
      if(!current())return null;
      key=JSON.stringify([sessionId,messageSeq,'reply']);
      if(durable){
        intent=await this.rpc('session.prepareBranch',{sessionId,messageSeq,mode:'reply'});
        if(intent?.sessionId!==sessionId||intent?.messageSeq!==messageSeq||intent?.mode!=='reply'||typeof intent?.newSessionId!=='string'||!/^[a-zA-Z0-9_-]{1,128}$/.test(intent.newSessionId)||intent.newSessionId===sessionId){intent=null;throw Error('Branch preparation is unconfirmed. No child was requested; an explicit click can read its saved identity.');}
        if(!current()){await releaseUncreated().catch(()=>false);return null;}
      }else{
        // Explicit compatibility with older Hosts; their loaded-controller
        // recovery scope stays separate from the advertised durable protocol.
        intent=this.branchIntents.get(key);
        if(!intent){
          if(this.branchIntents.size>=64)throw Error('Review unconfirmed branch operations before starting another.');
          intent={sessionId,newSessionId:crypto.randomUUID(),messageSeq,mode:'reply'};this.branchIntents.set(key,intent);
        }
      }
      attempted=true;const row=await this.rpc('session.branch',{...intent,...(durable?{prepared:true}:{})});
      if(!matches(row))throw Error('The branch response did not match the requested boundary.');
      creationConfirmed=true;
      if(durable){
        try{const settled=await this.rpc('session.settleBranch',{...intent,outcome:'created'});if(settled?.settled!==true||settled?.outcome!=='created'||!matches(settled))throw Error('Recovery acknowledgment mismatch.');}
        catch{warning='Branch created. Recovery acknowledgment is unconfirmed; inspect the child in the conversation list.';}
      }else this.branchIntents.delete(key);
      if(!current())return row;
      await this.refresh();
      if(current()&&canSelect()&&!this.state.sessions.find(value=>value.sessionId===scope.sessionId)?.running){
        const childEpoch=this.epoch+1;await this.open(row.sessionId);
        if(warning&&this.epoch===childEpoch&&this.state.sessionId===row.sessionId&&!this.state.readOnly)this.update({error:warning});
      }else if(warning&&current())this.update({error:warning});
      return row;
    }catch(error){
      let noChild=false;
      if(!creationConfirmed&&durable&&intent&&error.authoritative)noChild=await releaseUncreated().catch(()=>false);
      if(error.authoritative&&key&&!durable)this.branchIntents.delete(key);
      if(current()){
        this.update({error:creationConfirmed?'Branch created. The conversation list could not be refreshed; inspect the child before branching again.':attempted&&(!error.authoritative||durable&&!noChild)?'Branch creation unconfirmed. Inspect the conversation list; an explicit click at the same boundary uses the same child identity. No prompt was sent or operation retried.':error.message});
        error.presentedByBranch=true;throw error;
      }
      return null;
    }finally{
      if(this.branchFlight===flight){this.branchFlight=null;if(this.state.branchPending===flight)this.update({branchPending:null});}
    }
  }
  async workspaceAction(action,params={}){
    if(this.state.readOnly)throw Error('This conversation inspector is read-only.');
    try{const workspaces=await this.rpc('workspace.'+action,{...params,expectedRevision:this.state.workspaces?.revision});this.update({workspaces});return workspaces;}
    catch(error){await this.refresh().catch(()=>{});throw error;}
  }
  async adoptWorkspace(path){const snapshot=await this.workspaceAction('adopt',{path});return snapshot.items.find(x=>x.workspaceId===snapshot.adoptedWorkspaceId);}
  async poll(){
    if(this.polling||this.state.phase!=='ready'||!this.state.sessionId&&(this.state.readOnly||this.state.capabilities?.appearancePreferences!==true))return;
    this.polling=true;const sessionId=this.state.sessionId,epoch=this.epoch;
    try{
      const res=await this.fetcher(sessionId?'/api/events?'+new URLSearchParams({sessionId,clientId:this.clientId,after:String(this.cursor)}):'/api/appearance/revision',{headers:{Authorization:'Bearer '+this.token}});
      const page=await res.json();if(!res.ok||page.error)throw Error(page.error?.message||'The event connection failed.');if(epoch!==this.epoch)return;
      if(sessionId)this.cursor=page.cursor;
      if(!this.state.readOnly&&Number.isSafeInteger(page.settingsRevision)&&page.settingsRevision!==this.state.settingsRevision)this.update({settingsRevision:page.settingsRevision});
      if(!this.state.readOnly&&Number.isSafeInteger(page.appearanceRevision)&&page.appearanceRevision>(this.state.appearanceRevision??-1))this.update({appearanceRevision:page.appearanceRevision});
      if(!this.state.readOnly&&Number.isSafeInteger(page.metafoldersRevision)&&page.metafoldersRevision>(this.state.metafoldersRevision??-1))this.update({metafoldersRevision:page.metafoldersRevision});
      if(!this.state.readOnly&&this.state.capabilities?.modelSettingsRevisions===true&&Number.isSafeInteger(page.modelsRevision)&&page.modelsRevision>=0&&page.modelsRevision!==this.state.modelsRevision)this.update({modelsRevision:page.modelsRevision});
      if(!sessionId)return;
      const events=[...this.state.events],records=new Map(this.state.records.map(x=>[x.id,x])),interactions=new Map(this.state.interactions.map(x=>[x.rpcId,x]));let queue=this.state.queue,changed=false,familyChanged=false;
      for(const {frame} of page.frames){
        if(['job/updated','job/observation'].includes(frame.method)||frame.method==='session/event'&&['user/message','assistant/message','turn/start','turn/end'].includes(frame.payload.event.type)){familyChanged=true;changed=true;}
        if(frame.method==='session/event'){appendDisplay(events,frame.payload.event);changed=true;}
        if(frame.method==='observation/event'){const r=frame.payload.observation;records.set(r.id,r);changed=true;}
        if(frame.method==='session/queue'){queue=frame.payload;changed=true;}
        if(frame.method==='session/compaction'){const info=frame.payload,row=info.lastReceipt;this.update({compaction:info,...(row?.state==='failed'?{error:'Pi did not save a compaction summary. This conversation may be too small or already compacted, or its summary request failed. Inspect Context for the recorded attempt.'}:{})});changed=true;}
        if(['approval/requested','question/requested'].includes(frame.method)){interactions.set(frame.rpcId,frame);changed=true;}
        if(frame.method==='interaction/updated'){const old=interactions.get(frame.rpcId);if(old?.method==='question/requested'&&(old.payload.wait?.revision??-1)<=frame.payload.wait?.revision){interactions.set(frame.rpcId,{...old,payload:{...old.payload,wait:frame.payload.wait}});changed=true;}}
        if(['interaction/resolved'].includes(frame.method)){interactions.delete(frame.rpcId);this.heldQuestions.delete(frame.rpcId);changed=true;}
      }
      if(changed)this.update({familyRevision:this.state.familyRevision+(familyChanged?1:0),events,records:[...records.values()].sort((a,b)=>a.seq-b.seq),queue,interactions:[...interactions.values()]});
      if(changed)void this.hydrate().catch(error=>{if(epoch===this.epoch)this.update({error:error.message});});
      if(page.gap){await this.open(sessionId);return;}
      if(page.frames.length||!this.lastRefresh||Date.now()-this.lastRefresh>3000){this.lastRefresh=Date.now();await this.refresh();}
      if(this.state.capabilities?.sessionPermissions&&page.frames.some(({frame})=>frame.method==='permission/updated'))await this.refreshPermission({sessionId,epoch});
      if(this.state.capabilities?.planMode&&page.frames.some(({frame})=>frame.method==='plan-mode/updated'))await this.refreshPlanMode({sessionId,epoch});
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
    if(this.createFlight?.epoch===this.epoch&&this.createFlight.sessionId===this.state.sessionId)return null;
    const selection=this.state.selection||this.state.catalog.default;if(!selection)throw Error('Choose a model first.');
    const sessionId=crypto.randomUUID(),flight={epoch:++this.epoch,sessionId:this.state.sessionId,previousPhase:this.state.phase,opening:false};this.createFlight=flight;
    const current=()=>this.createFlight===flight&&this.epoch===flight.epoch&&this.state.sessionId===flight.sessionId&&!this.state.readOnly;
    // Freeze the outgoing composer before the first async boundary. Its private
    // draft remains owned by that conversation while the new owner is prepared.
    this.update({phase:'loading',error:null});
    try{
      const created=await this.rpc('session.create',{sessionId,selection,cwd});
      if(created?.sessionId!==sessionId)throw Error('The new conversation was not confirmed. Inspect the conversation list before trying again.');
      if(!current())return created;
      await this.refresh();if(!current())return created;
      flight.epoch=this.epoch+1;flight.sessionId=sessionId;flight.opening=true;
      await this.open(sessionId);return created;
    }catch(error){
      if(current())this.update({...(!flight.opening?{phase:flight.previousPhase}:{}),error:error.message});
      error.presentedByCreate=true;throw error;
    }finally{if(this.createFlight===flight)this.createFlight=null;}
  }
  pending=new Map();
  heldQuestions=new Map();
  hiddenQuestions=new Map();
  visibleInteraction(){return this.state.interactions.find(frame=>!this.hiddenQuestions.has(frame.rpcId));}
  questionForTool(data){
    if(data.name!=='ask_user'||this.state.readOnly||this.state.phase!=='ready')return;
    const call=this.state.events.findLast(e=>e.type==='tool/call'&&e.data.name==='ask_user'&&e.data.toolCallId===data.toolCallId);
    if(call?.seq!==data.seq)return;
    return this.state.interactions.find(frame=>frame.method==='question/requested'&&frame.payload.sessionId===this.state.sessionId&&frame.payload.ownerId===this.state.sessionId&&frame.payload.toolCallId===data.toolCallId);
  }
  canHideQuestion(frame){
    const call=this.state.events.findLast(e=>e.type==='tool/call'&&e.data.name==='ask_user'&&e.data.toolCallId===frame.payload?.toolCallId);
    return !!call&&this.questionForTool({...call.data,seq:call.seq})?.rpcId===frame.rpcId;
  }
  hideQuestion(frame){const scope=this.interactionScope(frame);if(!this.canHideQuestion(frame))throw Error('This question has no current tool row.');this.hiddenQuestions.set(frame.rpcId,scope);this.heldQuestions.delete(frame.rpcId);this.update({});}
  revealQuestion(frame){this.interactionScope(frame);if(!this.canHideQuestion(frame))throw Error('This question has no current tool row.');this.hiddenQuestions.delete(frame.rpcId);this.update({});}

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
  clearUnconfirmed(){const sid=this.state.sessionId,epoch=this.epoch;const finish=()=>{this.pending.delete(sid);if(sid===this.state.sessionId&&epoch===this.epoch)this.update({unconfirmed:null});};if(this.draftAcknowledge)return Promise.resolve(this.draftAcknowledge()).then(finish).catch(error=>{if(sid===this.state.sessionId&&epoch===this.epoch&&!this.state.readOnly)this.update({error:error.message});});finish();}
  async send(text,mode='queue',attachments=[],requestId=crypto.randomUUID()){
    const {sessionId,queue}=this.state;if(!sessionId)throw Error('Choose a workspace first.');
    if(this.state.readOnly||this.state.phase!=='ready')throw Error('The conversation is not ready for submission.');
    if(this.state.workspaces?.archivedSessionIds?.includes(sessionId))throw Error('Restore the conversation before sending.');
    if(this.pending.has(sessionId))throw Error('The previous submission is unconfirmed. Inspect the history; it was not retried.');
    const receipt={requestId,text,attachments};this.pending.set(sessionId,receipt);
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
  async stop(){
    const epoch=this.epoch,sessionId=this.state.sessionId;
    await this.rpc('session.cancel',{sessionId});
    if(epoch!==this.epoch||sessionId!==this.state.sessionId)return;
    try{
      // Stop may settle before this client's next event poll. Read canonical
      // receipts before idle metadata removes the original running seats.
      const [history,observations]=await Promise.all([this.rpc('session.history',{sessionId,maxMessages:100}),this.rpc('observation.list',{sessionId})]);
      if(epoch!==this.epoch||sessionId!==this.state.sessionId)return;
      const events=new Map([...this.state.events,...history.events.map(row=>row.event)].map(event=>[event.seq,event])),records=new Map([...this.state.records,...observations.records].map(record=>[record.id,record]));
      this.update({familyRevision:this.state.familyRevision+1,events:[...events.values()].sort((a,b)=>a.seq-b.seq),records:[...records.values()].sort((a,b)=>a.seq-b.seq),hasMore:this.state.hasMore||history.hasMore===true,observationHasMore:this.state.observationHasMore||observations.hasMore===true});
    }catch{
      if(epoch!==this.epoch||sessionId!==this.state.sessionId)return;
      await this.refresh().catch(()=>{});
      if(epoch!==this.epoch||sessionId!==this.state.sessionId)return;
      throw Error('Stop was acknowledged, but its saved details could not be loaded. Refresh to inspect the outcome.');
    }
    await this.refresh();
  }
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
