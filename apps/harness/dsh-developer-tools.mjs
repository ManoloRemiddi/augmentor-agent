// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
const unavailable={mode:'host',value:undefined,revision:null,writable:false,busy:false,error:null};
function checked(row){
 if(row?.ns!=='ui-settings'||!Number.isSafeInteger(row.revision)||row.revision<0||typeof row.value?.enabled!=='boolean'||!Array.isArray(row.writableFields)||row.writableFields.length!==1||row.writableFields[0]!=='enabled')throw Error('HTML preview preferences are unavailable.');
 return {value:{enabled:row.value.enabled},revision:row.revision,writable:true};
}
/** Accepted Host values drive the original preference; uncertain writes disable
 * execution until an explicit refresh, without replay or optimistic enablement. */
export class DshDeveloperTools {
 listeners=new Set();generation=0;connection=null;state={...unavailable};
 constructor(controller){this.controller=controller;this.unsubscribe=controller.subscribe(()=>this.sync());this.sync();}
 subscribe=fn=>{this.listeners.add(fn);return()=>this.listeners.delete(fn);};
 getSnapshot=()=>this.state;
 publish(patch){this.state={...this.state,...patch};for(const fn of this.listeners)fn();}
 current(){return this.controller.state.phase==='ready'&&!this.controller.state.readOnly&&this.controller.state.capabilities?.htmlPreviewSettings===true;}
 valid(ticket,epoch){return ticket===this.generation&&epoch===this.controller.epoch&&this.current();}
 sync(){const key=[this.controller.epoch,this.controller.state.phase,this.controller.state.readOnly,this.controller.state.capabilities?.htmlPreviewSettings===true].join(':');if(key===this.connection)return;this.connection=key;this.generation++;if(!this.current()){this.publish({...unavailable});return;}void this.load();}
 async load(){
  if(!this.current())return;const ticket=++this.generation,epoch=this.controller.epoch;this.publish({value:undefined,writable:false,busy:true,error:null});
  try{const result=await this.controller.rpc('settings.describe',{ns:'ui-settings'});if(!this.valid(ticket,epoch))return;this.publish({...checked(result?.namespaces?.find(row=>row.ns==='ui-settings')),busy:false});}
  catch(error){if(this.valid(ticket,epoch))this.publish({value:undefined,writable:false,busy:false,error:error.message+' Refresh to confirm the setting.'});}
 }
 set=async(field,enabled)=>{
  if(field!=='enabled'||typeof enabled!=='boolean'||!this.current()||!this.state.writable||this.state.busy)throw Error('HTML preview preferences are currently read-only.');
  const before=this.state,ticket=++this.generation,epoch=this.controller.epoch;this.publish({writable:false,busy:true,error:null});
  try{const result=await this.controller.rpc('settings.mutate',{ns:'ui-settings',expectedRevision:before.revision,ops:[{op:'set',path:['enabled'],value:enabled}]});if(!this.valid(ticket,epoch))return false;const row=checked(result);if(row.revision!==before.revision+1||row.value.enabled!==enabled)throw Error('The setting was not confirmed.');this.publish({...row,busy:false});return true;}
  catch(error){if(this.valid(ticket,epoch))this.publish({value:undefined,writable:false,busy:false,error:error.message+' Nothing was retried. Refresh to confirm the setting.'});throw error;}
 };
 close(){this.generation++;this.unsubscribe();this.listeners.clear();}
}
