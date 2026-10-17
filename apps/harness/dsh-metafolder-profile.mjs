// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {blankMetafolders,checkedMetafolders} from '../../packages/protocol/src/metafolders.ts';
function checked(row){if(row?.ns!=='metafolders'||!Number.isSafeInteger(row.revision)||row.revision<0||JSON.stringify(row.writableFields)!=='["enabled","document"]')throw Error('Metafolder preferences are unavailable.');return {revision:row.revision,value:checkedMetafolders(row.value)};}
/** Accepted profile snapshots only; no optimistic grouping, retries or agent work. */
export class DshMetafolderProfile {
 listeners=new Set();generation=0;connection=null;flight=null;pendingRevision=0;state={revision:null,value:blankMetafolders(),writable:false,busy:false,error:null};
 constructor(controller){this.controller=controller;this.unsubscribe=controller.subscribe(()=>this.sync());this.sync();}
 subscribe=fn=>{this.listeners.add(fn);return()=>this.listeners.delete(fn);};getSnapshot=()=>this.state;
 publish(patch){this.state={...this.state,...patch};for(const fn of this.listeners)fn();}
 current(){const s=this.controller.state;return s.phase==='ready'&&!s.readOnly&&s.capabilities?.metafolders===true;}
 valid(ticket,epoch){return ticket===this.generation&&epoch===this.controller.epoch&&this.current();}
 sync(){
  const c=this.controller,key=[c.epoch,c.state.phase,c.state.readOnly,c.state.capabilities?.metafolders===true].join(':');
  if(key!==this.connection){this.connection=key;this.generation++;this.flight=null;this.pendingRevision=0;if(!this.current()){this.publish({revision:null,value:blankMetafolders(),writable:false,busy:false,error:null});return;}void this.load();return;}
  const rev=c.state.metafoldersRevision;if(this.current()&&Number.isSafeInteger(rev)&&rev>(this.state.revision??-1)){if(this.flight?.kind==='set'){this.pendingRevision=Math.max(rev,this.pendingRevision);return;}if(!this.state.busy&&!this.state.error)void this.load();}
 }
 async load(){
  if(!this.current()||this.flight?.kind==='set')return;const ticket=++this.generation,epoch=this.controller.epoch;this.flight={kind:'read',ticket};this.publish({writable:false,busy:true,error:null});
  try{const value=checked(await this.controller.rpc('metafolders.describe'));if(this.valid(ticket,epoch))this.publish({...value,writable:true,busy:false,error:null});}
  catch(error){if(this.valid(ticket,epoch))this.publish({writable:false,busy:false,error:error.message+' Refresh Metafolders to confirm the saved groups.'});}
  finally{if(this.flight?.ticket===ticket)this.flight=null;}
 }
 async set(value){
  const desired=checkedMetafolders(value);if(!this.current()||!this.state.writable||this.state.busy)throw Error('Metafolders are awaiting confirmation. Refresh before changing them.');
  const before=this.state,ticket=++this.generation,epoch=this.controller.epoch;this.flight={kind:'set',ticket};this.pendingRevision=0;this.publish({writable:false,busy:true,error:null});
  try{const accepted=checked(await this.controller.rpc('metafolders.set',{value:desired,expectedRevision:before.revision}));if(!this.valid(ticket,epoch))return false;if(accepted.revision!==before.revision+1||JSON.stringify(accepted.value)!==JSON.stringify(desired))throw Error('Metafolder save was not confirmed.');this.publish({...accepted,writable:true,busy:false,error:null});return true;}
  catch(error){if(this.valid(ticket,epoch))this.publish({writable:false,busy:false,error:error.message+' Nothing was retried. Refresh to confirm the saved groups.'});throw error;}
  finally{if(this.flight?.ticket===ticket){this.flight=null;if(this.current()&&this.pendingRevision>(this.state.revision??-1)&&!this.state.error)void this.load();this.pendingRevision=0;}}
 }
 setEnabled=enabled=>this.set({...this.state.value,enabled});
 update=mut=>this.set({...this.state.value,document:mut(this.state.value.document)});
 close(){this.generation++;this.unsubscribe();this.listeners.clear();}
}
