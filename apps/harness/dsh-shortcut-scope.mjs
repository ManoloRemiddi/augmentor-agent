// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
/** Accepted private preference transport; no optimistic bindings or write replay. */
export class DshShortcutScope {
 listeners=new Set();generation=0;connection=null;accepted=false;
 constructor(controller,{platform,definitions,initial,validate,editDocument}){
  Object.assign(this,{controller,platform,definitions,validate,editDocument,snapshot:initial});this.unsubscribe=controller.subscribe(()=>this.sync());this.sync();
 }
 subscribe=fn=>{this.listeners.add(fn);return()=>this.listeners.delete(fn);};
 getSnapshot=()=>this.snapshot;
 publish(snapshot,accepted=false){this.snapshot=snapshot;this.accepted=accepted;for(const fn of this.listeners)fn();}
 current(){return !this.closed&&this.controller.state.phase==='ready'&&!this.controller.state.readOnly&&this.controller.state.capabilities?.shortcuts===true;}
 valid(ticket,epoch){return ticket===this.generation&&epoch===this.controller.epoch&&this.current();}
 sync(){const key=[this.controller.epoch,this.controller.state.phase,this.controller.state.readOnly,this.controller.state.capabilities?.shortcuts===true,this.controller.state.settingsRevision].join(':');if(key===this.connection)return;this.connection=key;this.generation++;if(!this.current()){this.publish({...this.snapshot,status:this.controller.state.phase==='ready'?'unreadable':'loading',error:this.controller.state.phase==='ready'?'read':null});return;}void this.load();}
 async load(){
  if(!this.current())return;const ticket=++this.generation,epoch=this.controller.epoch;this.publish({...this.snapshot,status:'loading',error:null});
  try{const result=await this.controller.rpc('shortcuts.describe',{platform:this.platform,definitions:this.definitions()});if(!this.valid(ticket,epoch))return;const snapshot=this.validate(result,true);this.publish(snapshot,snapshot.status==='ready');}
  catch{if(this.valid(ticket,epoch))this.publish({...this.snapshot,status:'unreadable',error:'read'});}
 }
 edit=async(edit,revision)=>{
  const before=this.snapshot,result=status=>({status,snapshot:this.snapshot});
  if(!this.current()||!this.accepted||before.status!=='ready')return result('not-ready');
  const ticket=++this.generation,epoch=this.controller.epoch;this.accepted=false;
  try{
   const value=await this.controller.rpc('shortcuts.edit',{platform:this.platform,edit,revision});if(!this.valid(ticket,epoch))return result('not-ready');
   if(!['saved','stale','unreadable','write-failed','not-ready','conflict'].includes(value?.status))throw Error('Unconfirmed shortcut write.');
   const snapshot=this.validate(value.snapshot,value.status==='unreadable');
   if(value.status==='saved'&&(revision!==before.revision||snapshot.revision===before.revision||snapshot.sequence!==before.sequence+1||JSON.stringify(snapshot.document)!==JSON.stringify(this.editDocument(before.document,edit))))throw Error('Unconfirmed shortcut binding.');
   if(snapshot.sequence<before.sequence)throw Error('Obsolete shortcut preferences.');
   this.publish(snapshot,snapshot.status==='ready');return {...value,snapshot};
  }catch{if(this.valid(ticket,epoch))this.publish({...before,status:'unreadable',error:'read'});return result('write-failed');}
 };
 close(){this.closed=true;this.generation++;this.unsubscribe();this.listeners.clear();this.accepted=false;}
}

export function checkedShortcutSnapshot(row,parseShortcutDocument,unreadable=false){
 if(!row||typeof row.revision!=='string'||!/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/.test(row.revision)||!Number.isSafeInteger(row.sequence)||row.sequence<0||typeof row.usingDefaults!=='boolean'||!(row.status==='ready'&&row.error===null||unreadable&&row.status==='unreadable'&&['read','invalid','future'].includes(row.error))||JSON.stringify(row.document).length>64*1024)throw Error('Shortcut preferences are unavailable.');
 if(typeof parseShortcutDocument(JSON.stringify(row.document))==='string')throw Error('Shortcut preferences are malformed.');return row;
}
