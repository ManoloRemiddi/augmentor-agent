// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
const choices=['light','dark','system'];
function checked(row){if(row?.ns!=='appearance'||!Number.isSafeInteger(row.revision)||row.revision<0||row.value?.preference!==null&&!choices.includes(row.value?.preference)||!Array.isArray(row.writableFields)||row.writableFields.length!==1||row.writableFields[0]!=='preference')throw Error('Appearance preferences are unavailable.');return {revision:row.revision,preference:row.value.preference};}
/** Accepted profile choices survive origins. Inspectors and old Hosts style locally. */
export class DshAppearance {
 listeners=new Set();generation=0;connection=null;pendingRevision=0;flight=null;state={revision:null,preference:null,writable:false,busy:false,localOnly:false,error:null};
 constructor(controller,apply){this.controller=controller;this.apply=apply;this.unsubscribe=controller.subscribe(()=>this.sync());this.sync();}
 subscribe=fn=>{this.listeners.add(fn);return()=>this.listeners.delete(fn);};getSnapshot=()=>this.state;
 publish(patch){this.state={...this.state,...patch};for(const fn of this.listeners)fn();}
 current(){return this.controller.state.phase==='ready'&&!this.controller.state.readOnly&&this.controller.state.capabilities?.appearancePreferences===true;}
 valid(ticket,epoch){return ticket===this.generation&&epoch===this.controller.epoch&&this.current();}
 sync(){
  const c=this.controller,key=[this.controller.epoch,c.state.phase,c.state.readOnly,c.state.capabilities?.appearancePreferences===true].join(':');
  if(key!==this.connection){this.connection=key;this.generation++;this.flight=null;this.pendingRevision=0;if(!this.current()){const localOnly=c.state.phase==='ready'&&(c.state.readOnly||c.state.capabilities?.appearancePreferences!==true);this.publish({revision:null,preference:null,writable:localOnly,busy:false,localOnly,error:null});return;}void this.load();return;}
  const revision=c.state.appearanceRevision;if(this.current()&&Number.isSafeInteger(revision)&&revision>(this.state.revision??-1)){if(this.flight?.kind==='set'){this.pendingRevision=Math.max(this.pendingRevision,revision);return;}if(!this.state.busy&&!this.state.error)void this.load();}
 }
 async load(){
  if(!this.current()||this.flight?.kind==='set')return;const ticket=++this.generation,epoch=this.controller.epoch;this.flight={kind:'read',ticket};this.publish({writable:false,busy:true,localOnly:false,error:null});
  try{const value=checked(await this.controller.rpc('appearance.describe'));if(!this.valid(ticket,epoch))return;if(value.preference!==null)this.apply(value.preference);this.publish({...value,writable:true,busy:false,error:null});}
  catch(error){if(this.valid(ticket,epoch))this.publish({writable:false,busy:false,error:error.message+' Reopen Settings to confirm appearance.'});}
  finally{if(this.flight?.ticket===ticket)this.flight=null;}
 }
 set=async preference=>{
  if(!choices.includes(preference))throw Error('Choose Light, Dark or System.');if(this.state.localOnly&&this.state.writable){this.apply(preference);return true;}
  if(!this.current()||!this.state.writable||this.state.busy)throw Error('Appearance is awaiting confirmation. Reopen Settings.');
  const before=this.state,ticket=++this.generation,epoch=this.controller.epoch;this.flight={kind:'set',ticket};this.pendingRevision=0;this.publish({writable:false,busy:true,error:null});
  try{const value=checked(await this.controller.rpc('appearance.set',{preference,expectedRevision:before.revision}));if(!this.valid(ticket,epoch))return false;if(value.revision!==before.revision+1||value.preference!==preference)throw Error('Appearance was not confirmed.');this.apply(value.preference);this.publish({...value,writable:true,busy:false,error:null});return true;}
  catch(error){if(this.valid(ticket,epoch))this.publish({writable:false,busy:false,error:error.message+' Nothing was retried. Reopen Settings to confirm appearance.'});throw error;}
  finally{if(this.flight?.ticket===ticket){this.flight=null;if(this.current()&&this.pendingRevision>(this.state.revision??-1)&&!this.state.error)void this.load();this.pendingRevision=0;}}
 };
 close(){this.generation++;this.unsubscribe();this.listeners.clear();}
}
