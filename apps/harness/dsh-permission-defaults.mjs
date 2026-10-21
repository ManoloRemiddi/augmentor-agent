// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
const presets=['read-only','workspace-write','danger-full-access'];
const empty={status:'unavailable',error:null,writable:false,currentValue:'',options:[],revision:0};
function checked(row){
 if(row?.ns!=='permission'||!Number.isSafeInteger(row.revision)||row.revision<0||!presets.includes(row.value?.defaultPreset)||JSON.stringify(row.writableFields)!==JSON.stringify(['defaultPreset'])||!Array.isArray(row.options)||row.options.length!==3||new Set(row.options.map(x=>x?.id)).size!==3||row.options.some(x=>!presets.includes(x?.id)||typeof x.label!=='string'||!x.label.length||x.label.length>100))throw Error('Permission defaults are unavailable.');
 return {revision:row.revision,currentValue:row.value.defaultPreset,options:row.options.map(x=>({...x}))};
}
/** Bind only the original new-session preference to the existing Pi settings API.
 * No current-session policy, model turn, action approval or provider is changed. */
export class DshPermissionDefaults {
 listeners=new Set();generation=0;closed=false;state={...empty};connection=null;
 constructor(controller){this.controller=controller;this.unsubscribe=controller.subscribe(()=>this.sync());this.sync();}
 subscribe=fn=>{this.listeners.add(fn);return()=>this.listeners.delete(fn);};
 getSnapshot=()=>this.state;
 publish(patch){this.state={...this.state,...patch};for(const fn of this.listeners)fn();}
 current(){return !this.closed&&this.controller.state.phase==='ready'&&!this.controller.state.readOnly&&this.controller.state.capabilities?.permissionDefaults===true;}
 valid(ticket,epoch){return ticket===this.generation&&epoch===this.controller.epoch&&this.current();}
 sync(){const key=[this.controller.epoch,this.controller.state.phase,this.controller.state.readOnly,this.controller.state.capabilities?.permissionDefaults===true].join(':');if(this.connection===key)return;this.connection=key;this.generation++;this.publish({...empty,status:this.current()?'idle':'unavailable'});}
 load=async()=>{
  if(!this.current()||this.state.status==='saving')return;
  const ticket=++this.generation,epoch=this.controller.epoch;this.publish({...empty,status:'loading'});
  try{const result=await this.controller.rpc('settings.describe',{ns:'permission'});if(this.valid(ticket,epoch))this.publish({...checked(result?.namespaces?.find(x=>x.ns==='permission')),status:'ready',writable:true,error:null});}
  catch(error){if(this.valid(ticket,epoch))this.publish({...empty,status:'error',error:error.message+' Refresh to confirm the default.'});}
 };
 select=async preset=>{
  if(!this.current()||!this.state.writable||this.state.status!=='ready'||!this.state.options.some(x=>x.id===preset)||preset===this.state.currentValue)return;
  const before=this.state,ticket=++this.generation,epoch=this.controller.epoch;this.publish({status:'saving',writable:false,error:null});
  try{
   const accepted=await this.controller.rpc('settings.mutate',{ns:'permission',expectedRevision:before.revision,ops:[{op:'set',path:['defaultPreset'],value:preset}]});if(!this.valid(ticket,epoch))return;if(accepted?.ok!==true)throw Error('The permission change was not acknowledged.');
   const result=await this.controller.rpc('settings.describe',{ns:'permission'});if(!this.valid(ticket,epoch))return;const row=checked(result?.namespaces?.find(x=>x.ns==='permission'));if(row.currentValue!==preset||row.revision<=before.revision)throw Error('The saved permission default was not confirmed.');
   this.publish({...row,status:'ready',writable:true,error:null});
  }catch(error){if(this.valid(ticket,epoch))this.publish({...empty,status:'error',error:error.message+' Nothing was retried. Refresh to confirm the default.'});}
 };
 close(){this.closed=true;this.generation++;this.unsubscribe();this.listeners.clear();}
}
