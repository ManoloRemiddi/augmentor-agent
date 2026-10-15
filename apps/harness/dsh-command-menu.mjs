// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0

const unavailable=new Set(['permission','export','feedback']);
const sameModel=(a,b)=>a?.provider===b?.provider&&a?.model===b?.model;

/** Pi bindings for the copied DSH trigger and popup controllers; no agent owner. */
export class DshCommandMenu {
  constructor(deps){
    this.deps=deps;this.scope=null;this.engine=null;this.select=null;this.offs=[];
    // Stable read faces let the original views survive session-scope teardown.
    this.menu=deps.store({open:false,groups:[],highlight:null,hit:null});
    this.headers=deps.store(new Map());this.launcher=deps.store(null);this.lexicon=deps.store(new Map());
    const vacant=new deps.PopupSelectController({consume:()=>false,focusComposer:()=>{}});this.closedPopup=vacant.state.getSnapshot();vacant.dispose();
    this.popup={state:deps.store(this.closedPopup),...Object.fromEntries(['retry','setSearch','move','highlight','select','acknowledge','cancelConfirmation','confirm','dismiss'].map(name=>[name,(...args)=>this.select?.[name](...args)]))};
  }
  current(){return this.deps.current();}
  enabled(s){return s.phase==='ready'&&!s.readOnly&&!s.unconfirmed&&!s.interactions?.length&&this.deps.ready?.()!==false&&s.sessionId&&this.deps.draft().sessionId===s.sessionId;}
  valid(scope){const now=this.current();return this.enabled(now)&&scope?.sessionId===now.sessionId&&scope.epoch===now.epoch;}
  mirror(source,target){target.set(source.getSnapshot());this.offs.push(source.subscribe(()=>target.set(source.getSnapshot())));}
  sync(){
    const now=this.current();
    if(this.scope&&this.valid(this.scope))return;
    this.engine?.dispose();this.select?.dispose();for(const off of this.offs)off();this.offs=[];
    this.scope=null;this.engine=null;this.select=null;this.launchSegment=null;
    this.menu.set({open:false,groups:[],highlight:null,hit:null});this.headers.set(new Map());this.launcher.set(null);this.lexicon.set(new Map());this.popup.state.set(this.closedPopup);
    if(!this.enabled(now))return;
    const scope=this.scope={sessionId:now.sessionId,epoch:now.epoch};
    const source={name:'command',trigger:'/',candidates:async(_,query)=>{
      if(query.signal.aborted||!this.valid(scope))return [];
      const rows=this.deps.rows();
      if(!query.query)return this.deps.sectionRows(rows);
      const search=query.query.toLowerCase();return rows.filter(row=>row.name.toLowerCase().includes(search)||row.label?.toLowerCase().includes(search));
    },onPick:pick=>{
      if(!this.valid(scope))return 'handled';
      // An inline slash is editable text, not permission to execute a UI command.
      if(pick.position==='inline'){this.consume(scope,{via:'menu',span:pick.span},'/'+pick.candidate.name+' ');return 'handled';}
      const launched=this.launchSegment&&['start','end','draftRev'].every(key=>this.launchSegment[key]===pick.span[key]);
      try{this.dispatch(pick.candidate.name,scope,{via:launched?'launcher':'menu',span:pick.span});}catch(error){this.deps.notice(error.message);}
      return 'handled';
    },matchEnter:(_,line)=>{
      const match=/^\/([^\s]+)(?:\s|$)/.exec(line);if(!match)return undefined;
      const name=match[1];if(name==='plan')return undefined; // Product /plan keeps its message and attachments in the admitted input chain.
      if(unavailable.has(name))throw Error('/'+name+' is not yet connected to Pi. Your draft is preserved.');
      if(!this.deps.rows().some(row=>row.name===name))return undefined;
      if(line!=='/'+name)throw Error('Use /'+name+' by itself to open this command. Your draft is preserved.');
      this.dispatch(name,scope,{via:'enter',token:line,rev:this.deps.draft().rev});return 'handled';
    }};
    const reference=this.deps.referenceSource?.(scope),sources=[source,...(reference?[reference]:[])];
    this.engine=new this.deps.InputTriggerController({sessionId:scope.sessionId,actx:{bail:(_,event,p)=>{
      if(event==='slash/input-insert-text')return this.consume(scope,{via:'menu',span:p.span},p.text);
      if(event==='slash/input-insert-reference'&&this.segmentValid(scope,{via:'menu',span:p.span}))return this.deps.insertReference?.(p.span,p.reference,this.deps.draft().rev,scope)===true;
      return false;
    }},roster:{sources:trigger=>sources.filter(s=>s.trigger===trigger),all:()=>sources}});
    this.select=new this.deps.PopupSelectController({consume:segment=>this.consume(scope,segment),focusComposer:()=>{if(this.valid(scope))this.deps.focus();}});
    for(const key of ['menu','headers','launcher','lexicon'])this.mirror(this.engine[key],this[key]);
    this.mirror(this.select.state,this.popup.state);
  }
  track(){this.sync();if(!this.engine||this.popup.state.getSnapshot().open)return;const value=this.deps.draft();if(value.rev!==this.launchSegment?.draftRev)this.launchSegment=null;this.engine.track(value.detectText??value.text,value.caret??-1,{tier:'plain'},value.rev);}
  toggle(span){this.sync();if(!this.engine)return;this.select.dismiss();this.launchSegment={...span,draftRev:this.deps.draft().rev};this.engine.toggleSource('command',{trigger:'/',query:'',quoted:false,position:'leading',span:this.launchSegment});}
  arbitrate(key,composing){this.sync();return this.engine?.arbitrate(key,composing)??'pass';}
  dismiss(){this.engine?.dismiss();}
  async adjudicate(text){this.sync();return this.engine?.adjudicate(text.trim(),new AbortController().signal,{attachments:0});}
  segmentValid(scope,segment){
    if(!this.valid(scope))return false;
    const draft=this.deps.draft();
    return segment.via==='enter'?draft.rev===segment.rev&&draft.text.trim()===segment.token:draft.rev===segment.span.draftRev&&segment.span.start>=0&&segment.span.end>=segment.span.start&&segment.span.end<=(draft.detectText??draft.text).length;
  }
  consume(scope,segment,replacement=''){
    if(!this.segmentValid(scope,segment))return false;
    if(segment.via==='launcher')return true; // Navigation never deletes selected user text.
    const draft=this.deps.draft(),span=segment.via==='enter'?{start:0,end:draft.text.length}:segment.span;
    return this.deps.replace(span,replacement,draft.rev,scope);
  }
  dispatch(name,scope,segment){
    if(!this.segmentValid(scope,segment))return false;
    if(name==='context'){
      const action=this.deps.actions.context;if(!action)return false;
      // The original plugin leaves its token until the dialog closes. The
      // captured revision/session/epoch still fence consumption at that time.
      return action(scope,segment,()=>this.consume(scope,segment))!==false;
    }
    if(name==='compact'||name==='plan'){
      if(name==='compact'&&this.current().running)throw Error('Stop active work before compacting. Your draft is preserved.');
      const action=this.deps.actions[name];if(!action)return false;
      // Only a confirmed admission may consume the owned slash span. Late
      // replies cannot erase a changed draft or another conversation's text.
      void Promise.resolve().then(()=>{if(!this.segmentValid(scope,segment))return;return action(scope);}).then(result=>{if(result?.accepted)this.consume(scope,segment);}).catch(error=>this.deps.notice(error.message));return true;
    }
    if(name!=='model'){
      const action=this.deps.actions[name];if(!action)return false;
      action(scope);this.consume(scope,segment);return true;
    }
    const now=this.current();if(now.running)throw Error('Wait for the current task to finish before changing model. Your draft is preserved.');
    const context={...scope,selection:now.selection,segment};
    this.select.open('model',{
      options:async(_,signal)=>{
        if(signal.aborted||!this.valid(context))return [];
        return this.deps.catalog().groups.flatMap(group=>group.models.map(model=>({id:JSON.stringify([model.provider??group.provider,model.model]),label:model.name||model.model,group:{name:group.provider,label:group.name||group.provider},detail:model.model,active:sameModel(context.selection,{provider:model.provider??group.provider,model:model.model}),value:{provider:model.provider??group.provider,model:model.model}})));
      },onSelect:async(option,captured)=>{
        const current=this.current();
        if(!this.segmentValid(captured,captured.segment)||current.running||!sameModel(current.selection,captured.selection))throw Error('The conversation, draft or model changed. Reopen /model; nothing was applied.');
        await this.deps.choose(option.value,captured);
      },
    },context,segment);return true;
  }
  dispose(){this.engine?.dispose();this.select?.dispose();for(const off of this.offs)off();this.offs=[];}
}
