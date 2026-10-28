// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
function checked(v){if(!v||typeof v.configured!=='boolean'||typeof v.profileRevision!=='string'||!Array.isArray(v.rows)||typeof v.blocked!=='boolean'||v.configured&&typeof v.revision!=='string')throw Error('Wiki receipt inspection is unavailable.');return v;}
/** An operator review is never a model tool or an automatic retry. */
export class DshWikiReceipts {
 listeners=new Set();generation=0;state={snapshot:null,busy:false,writable:false,error:null};
 constructor(controller){this.controller=controller;this.unsubscribe=controller.subscribe(()=>{if(!this.current()){this.generation++;this.publish({snapshot:null,busy:false,writable:false,error:null});}});}
 subscribe=fn=>{this.listeners.add(fn);return()=>this.listeners.delete(fn);};getSnapshot=()=>this.state;
 publish(patch){this.state={...this.state,...patch};for(const fn of this.listeners)fn();}
 current(){const s=this.controller.state;return s.phase==='ready'&&!s.readOnly&&s.capabilities?.wikiSettings===true;}
 valid(ticket,epoch){return ticket===this.generation&&epoch===this.controller.epoch&&this.current();}
 scope(profileRevision){this.profileRevision=profileRevision;this.generation++;this.publish({snapshot:null,busy:false,writable:false,error:null});void this.load();}
 async load(){if(!this.current()||this.state.busy)return;const ticket=++this.generation,epoch=this.controller.epoch,profile=this.profileRevision;this.publish({busy:true,writable:false,error:null});try{const snapshot=checked(await this.controller.rpc('wiki.receipts'));if(!this.valid(ticket,epoch))return;if(profile!==undefined&&snapshot.profileRevision!==profile)throw Error('The stored Wiki vault changed. Refresh Wiki settings before reviewing its actions.');this.publish({snapshot,busy:false,writable:snapshot.configured,error:null});}catch(e){if(this.valid(ticket,epoch))this.publish({snapshot:null,busy:false,writable:false,error:e.message});}}
 async review(target,acknowledged){if(!this.current()||!this.state.writable||this.state.busy||acknowledged!==true)throw Error('Inspect the original action and vault, then acknowledge its unknown outcome.');const before=this.state.snapshot,ticket=++this.generation,epoch=this.controller.epoch;this.publish({busy:true,writable:false,error:null});try{const snapshot=checked(await this.controller.rpc('wiki.review',{key:target.key,sha256:target.sha256,expectedRevision:before.revision,expectedProfileRevision:before.profileRevision,acknowledgeUnknownOutcome:true,reviewId:crypto.randomUUID()}));if(!this.valid(ticket,epoch))return false;this.publish({snapshot,busy:false,writable:true,error:null});return true;}catch(e){if(this.valid(ticket,epoch))this.publish({busy:false,writable:false,error:e.message+' Nothing was retried. Refresh receipt inspection before continuing.'});throw e;}}
 close(){this.generation++;this.unsubscribe();this.listeners.clear();}
}
