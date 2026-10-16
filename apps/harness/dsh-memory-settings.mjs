// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
function checked(row){
 if(row?.protocol!=='augmentor-memory-settings/1'||typeof row.connected!=='boolean')throw Error('Memory status could not be confirmed.');
 if(!row.connected)return {protocol:row.protocol,connected:false,message:'Memory status is unavailable. Refresh to check it again.'};
 if(typeof row.enabled!=='boolean'||typeof row.configured!=='boolean'||typeof row.available!=='boolean'||!['default','off','unknown','unconfigured'].includes(row.requestMode)||
  !['events','pending','stopped'].every(key=>Number.isSafeInteger(row[key])&&row[key]>=0)||typeof row.actions?.capture!=='boolean'||typeof row.actions?.processing!=='boolean'||typeof row.processing?.known!=='boolean'||
  row.processing.known&&(typeof row.processing.paused!=='boolean'||typeof row.processing.active!=='boolean'))throw Error('Memory status could not be confirmed.');
 return row;
}
export class DshMemorySettings {
 listeners=new Set();generation=0;connection=null;closed=false;state={busy:false,value:null,error:null};
 constructor(controller){this.controller=controller;this.unsubscribe=controller.subscribe(()=>this.sync());this.sync();}
 subscribe=fn=>{this.listeners.add(fn);return()=>this.listeners.delete(fn);};getSnapshot=()=>this.state;
 publish(patch){this.state={...this.state,...patch};for(const fn of this.listeners)fn();}
 current(){const s=this.controller.state;return !this.closed&&s.phase==='ready'&&!s.readOnly&&s.capabilities?.memorySettings===true;}
 sync(){const s=this.controller.state,key=[this.controller.epoch,s.phase,s.readOnly,s.capabilities?.memorySettings===true].join(':');if(key===this.connection)return;this.connection=key;this.generation++;this.publish({busy:false,value:null,error:null});if(this.current())void this.load();}
 valid(ticket,epoch){return ticket===this.generation&&epoch===this.controller.epoch&&this.current();}
 async load(){
  if(!this.current()||this.state.busy)return;const ticket=++this.generation,epoch=this.controller.epoch;this.publish({busy:true,error:null});
  try{const value=checked(await this.controller.rpc('memory.status',{}));if(this.valid(ticket,epoch))this.publish({value,busy:false,error:null});}
  catch{if(this.valid(ticket,epoch))this.publish({value:null,busy:false,error:'Memory status could not be confirmed. Refresh before choosing again.'});}
 }
 async change(kind){
  if(!['capture','processing'].includes(kind))throw Error('Choose capture or processing.');
  const value=this.state.value;if(!this.current()||this.state.busy||!value?.connected||!value.actions[kind])throw Error('Refresh memory status before choosing again.');
  const processing=kind==='processing',expected=processing?value.processing.paused:value.enabled,ticket=++this.generation,epoch=this.controller.epoch;
  this.publish({busy:true,error:null});
  try{const next=checked(await this.controller.rpc(processing?'memory.processing':'memory.configure',processing?{paused:!expected,expectedPaused:expected}:{enabled:!expected,expectedEnabled:expected}));if(!next.connected)throw Error('Unconfirmed memory change');if(this.valid(ticket,epoch))this.publish({value:next,busy:false,error:null});}
  catch{if(this.valid(ticket,epoch))this.publish({value:null,busy:false,error:'The memory change could not be confirmed. Refresh before choosing again. Nothing was retried.'});}
 }
 close(){this.closed=true;this.generation++;this.unsubscribe();this.listeners.clear();}
}
