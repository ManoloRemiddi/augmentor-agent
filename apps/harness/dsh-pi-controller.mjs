// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {readDshPayload} from './dsh-payload.mjs';
import {appendDisplay} from './chat-projection.js';

/** Browser transport to the existing Pi Host; never owns an agent or retries a mutation. */
export class DshPiController {
  listeners=new Set(); epoch=0; polling=false; cursor=0; clientId=crypto.randomUUID();
  state={phase:'connecting',sessionId:null,readOnly:false,sessions:[],events:[],records:[],payloads:{},queue:null,interactions:[],catalog:{groups:[]},selection:null,reasoning:null,goal:null,workspace:'',error:null,hasMore:false};
  constructor(token,fetcher=fetch){this.token=token;this.fetcher=(...args)=>fetcher(...args);}
  subscribe=fn=>{this.listeners.add(fn);return()=>this.listeners.delete(fn);};
  getSnapshot=()=>this.state;
  update(patch){this.state={...this.state,...patch};for(const fn of this.listeners)fn();}
  async rpc(method,params={}){
    const response=await this.fetcher('/api/rpc',{method:'POST',headers:{Authorization:'Bearer '+this.token,'Content-Type':'application/json'},body:JSON.stringify({id:crypto.randomUUID(),method,params})});
    const body=await response.json();if(!response.ok||body.error)throw Error(body.error?.message||'The local connection failed.');return body.result;
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
    this.update({sessionId,unconfirmed:this.pending.get(sessionId)||null,phase:'loading',events:[],records:[],payloads:{},queue:null,interactions:[],selection:null,reasoning:null,goal:null,hasMore:false,error:null});
    const sub=await this.rpc('events.subscribe',{sessionId,clientId:this.clientId});if(epoch!==this.epoch)return;
    this.cursor=sub.cursor;
    const [history,observations,model,queue,goal]=await Promise.all([
      this.rpc('session.history',{sessionId,maxMessages:100}),this.rpc('observation.list',{sessionId}),this.rpc('session.models',{sessionId}),this.rpc('session.queue',{sessionId}),this.rpc('session.goal',{sessionId}),
    ]);
    if(epoch!==this.epoch)return;
    const reasoning=this.state.readOnly?null:await this.rpc('session.reasoning',{sessionId});if(epoch!==this.epoch)return;
    sessionStorage.setItem('augmentor-harness-session',sessionId);
    this.update({events:history.events.map(x=>x.event),hasMore:history.hasMore===true,observationHasMore:observations.hasMore===true,records:observations.records,selection:model.current,queue,goal,reasoning,interactions:sub.pending,phase:'ready'});
    void this.hydrate().catch(error=>{if(epoch===this.epoch)this.update({error:error.message});});
  }
  hydrating=false;
  async hydrate(){
    if(this.hydrating)return;this.hydrating=true;const epoch=this.epoch,sessionId=this.state.sessionId;
    try{const window=this.state.records.filter(r=>r.kind==='model/request'&&r.payload?.state==='retained'&&r.payload.bytes<=1024*1024).slice(-8),ids=new Set(window.map(r=>r.id));
      const retained=Object.fromEntries(Object.entries(this.state.payloads).filter(([id])=>ids.has(id)));if(Object.keys(retained).length!==Object.keys(this.state.payloads).length)this.update({payloads:retained});
      const requests=window.filter(r=>!this.state.payloads[r.id]);
      for(const record of requests){const result=await readDshPayload((m,p)=>this.rpc(m,p),sessionId,record);if(epoch!==this.epoch)return;if(result.available)this.update({payloads:{...this.state.payloads,[record.id]:result.value}});}
    }finally{this.hydrating=false;}
  }
  clearSelection(){this.epoch++;globalThis.sessionStorage?.removeItem('augmentor-harness-session');this.update({sessionId:null,events:[],records:[],payloads:{},queue:null,goal:null,interactions:[],selection:null,reasoning:null,hasMore:false,unconfirmed:null,phase:'ready'});}
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
        if(['approval/requested','question/requested'].includes(frame.method)){interactions.set(frame.rpcId,frame);changed=true;}
        if(['interaction/resolved'].includes(frame.method)){interactions.delete(frame.rpcId);changed=true;}
      }
      if(changed)this.update({events,records:[...records.values()].sort((a,b)=>a.seq-b.seq),queue,interactions:[...interactions.values()]});
      if(changed)void this.hydrate().catch(error=>{if(epoch===this.epoch)this.update({error:error.message});});
      if(page.gap){await this.open(sessionId);return;}
      if(page.frames.length||!this.lastRefresh||Date.now()-this.lastRefresh>3000){this.lastRefresh=Date.now();await this.refresh();}
      if(page.frames.some(({frame})=>frame.method==='goal/updated')){const goal=await this.rpc('session.goal',{sessionId});if(epoch===this.epoch)this.update({goal});}
    }finally{this.polling=false;}
  }
  async create(cwd=this.state.workspace){
    if(this.state.readOnly)throw Error('This conversation inspector is read-only.');
    const selection=this.state.selection||this.state.catalog.default;if(!selection)throw Error('Choose a model first.');
    const sessionId=crypto.randomUUID();await this.rpc('session.create',{sessionId,selection,cwd});await this.refresh();await this.open(sessionId);
  }
  pending=new Map();
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
    const sessionId=this.state.sessionId,epoch=this.epoch;
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
