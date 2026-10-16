// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {DshSearchScope} from './dsh-search-scope.mjs';
import {DshWikiProfile} from './dsh-wiki-profile.mjs';
import {DshMemorySettings} from './dsh-memory-settings.mjs';
/** Saved plugin settings only: no inferred health, optimistic changes or retries.
 * The directory and detail forms share these owners and accepted revisions. */
export class DshPluginControls {
 listeners=new Set();closed=false;generation=0;connection=null;reasoning={value:null,busy:false,error:null};state={rows:{}};
 constructor(controller,folders){
  this.controller=controller;this.folders=folders;
  this.search=new DshSearchScope(controller);this.wiki=new DshWikiProfile(controller);this.memory=new DshMemorySettings(controller);
  this.stops=[this.search,this.wiki,this.memory,folders].map(profile=>profile.subscribe(()=>this.emit()));
  this.stops.push(controller.subscribe(()=>{this.sync();this.emit();}));this.sync();this.emit();
 }
 subscribe=fn=>{this.listeners.add(fn);return()=>this.listeners.delete(fn);};getSnapshot=()=>this.state;
 current(){const s=this.controller.state;return !this.closed&&s.phase==='ready'&&!s.readOnly;}
 sync(){const key=[this.controller.epoch,this.controller.state.phase,this.controller.state.readOnly].join(':');if(key===this.connection)return;this.connection=key;this.generation++;this.reasoning={value:null,busy:false,error:null};if(this.current())void this.loadReasoning();}
 emit(){
  if(this.closed)return;const search=this.search.getSnapshot(),wiki=this.wiki.getSnapshot(),memory=this.memory.getSnapshot(),folders=this.folders.getSnapshot(),r=this.reasoning;
  const idle=!(this.controller.state.sessions??[]).some(row=>row.running||row.jobsRunning),current=this.current();
  const row=(value,busy,error,writable,note)=>({enabled:typeof value==='boolean'?value:null,busy,error:error||null,writable:!!(current&&writable&&!busy&&!error),note});
  this.state={rows:{
   search:row(search.accepted?.enabled,search.busy,search.error,search.writable&&idle,search.accepted?.pending?'Saved; application pending':!idle?'Finish active work before switching':search.accepted?.mode==='keyless'?'Keyless engines':'API engines'),
   wiki:row(wiki.accepted?.value.enabled,wiki.busy,wiki.error,wiki.writable&&!wiki.accepted?.pending&&idle&&!!wiki.accepted?.value.vaultPath.trim(),wiki.accepted?.pending?'Saved; application pending':!idle?'Finish active work before switching':wiki.accepted?.value.vaultPath?'Tools & skills':'Choose a vault in Settings'),
   folders:row(folders.revision===null?null:folders.value.enabled,folders.busy,folders.error,folders.writable,'Sidebar grouping'),
   memory:row(memory.value?.connected?memory.value.enabled:null,memory.busy,memory.error,this.memory.current()&&memory.value?.actions.capture,memory.value?.connected?(memory.value.processing.issue==='gateway-in-use'?'Processing gateway in use; local capture still works':!memory.value.configured?'Engine not configured; processing is separate':!memory.value.available?'Engine availability unconfirmed; processing is separate':'Off also pauses processing; On does not resume it'):'Refresh to check memory capture'),
   reasoning:row(r.value?.config.enabled,r.busy,r.error,!!r.value&&idle,idle?'Adaptive policy; saved effort stays':'Finish active work before switching'),
  }};for(const fn of this.listeners)fn();
 }
 async loadReasoning(){
  if(!this.current()||this.reasoning.busy)return;const ticket=++this.generation,epoch=this.controller.epoch;this.reasoning={...this.reasoning,busy:true,error:null};this.emit();
  try{const value=await this.controller.rpc('reasoning.describe');if(!Number.isSafeInteger(value?.revision)||typeof value?.config?.enabled!=='boolean')throw Error('Reasoning status is unavailable.');if(!this.closed&&ticket===this.generation&&epoch===this.controller.epoch&&this.current())this.reasoning={value,busy:false,error:null};}
  catch{if(!this.closed&&ticket===this.generation&&epoch===this.controller.epoch&&this.current())this.reasoning={value:null,busy:false,error:'Status could not be confirmed. Refresh before switching.'};}
  this.emit();
 }
 async refresh(){if(!this.current())return;await Promise.allSettled([this.search.load(),this.wiki.load(true),this.memory.load(),this.folders.load(),this.loadReasoning()]);this.emit();}
 async toggle(id){
  if(!this.current())return;
  const row=this.state.rows[id];if(!row?.writable||typeof row.enabled!=='boolean')return;const enabled=!row.enabled;
  try{
   if(id==='search')await this.search.enable(enabled);
   else if(id==='wiki')await this.wiki.setEnabled(enabled);
   else if(id==='folders')await this.folders.setEnabled(enabled);
   else if(id==='memory')await this.memory.change('capture');
   else if(id==='reasoning'){
    const before=this.reasoning.value,ticket=++this.generation,epoch=this.controller.epoch;this.reasoning={...this.reasoning,busy:true,error:null};this.emit();
    try{const value=await this.controller.rpc('reasoning.configure',{expectedRevision:before.revision,config:{...before.config,enabled}});if(!Number.isSafeInteger(value?.revision)||value.revision<=before.revision||value.config?.enabled!==enabled)throw Error('Reasoning change is not confirmed.');if(!this.closed&&ticket===this.generation&&epoch===this.controller.epoch&&this.current())this.reasoning={value,busy:false,error:null};}
    catch{if(!this.closed&&ticket===this.generation&&epoch===this.controller.epoch&&this.current())this.reasoning={value:null,busy:false,error:'Change not confirmed. Nothing was retried. Refresh before switching.'};}
   }
  }catch{/* Existing profile holds the unconfirmed outcome and refresh guard. */}
  this.emit();
 }
 close(){this.closed=true;this.generation++;for(const stop of this.stops)stop();this.search.close();this.wiki.close();this.memory.close();this.listeners.clear();}
}
