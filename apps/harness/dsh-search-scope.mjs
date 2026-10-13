// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
const providers=['tinyfish','anysearch','exa','tavily','firecrawl','serpingapi','brave','serpapi','jina'];
function checked(row){
 const fields=[...providers.map(name=>name+'ApiKey'),'enableFetch','providerOrder'];
 const config=value=>value&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).every(key=>fields.includes(key))&&providers.every(name=>value[name+'ApiKey']===undefined||typeof value[name+'ApiKey']==='string'&&value[name+'ApiKey'].length<=65536)&&(value.enableFetch===undefined||typeof value.enableFetch==='boolean')&&(value.providerOrder===undefined||Array.isArray(value.providerOrder)&&value.providerOrder.length<=9&&value.providerOrder.every(name=>providers.includes(name))&&new Set(value.providerOrder).size===value.providerOrder.length);
 if(!row||typeof row.revision!=='string'||row.revision!=='missing'&&!/^[a-f0-9]{64}$/.test(row.revision)||typeof row.enabled!=='boolean'||!config(row.user)||!config(row.value)||typeof row.pending!=='boolean'||!Number.isSafeInteger(row.loadedSessions)||!Number.isSafeInteger(row.appliedSessions)||row.loadedSessions<0||row.appliedSessions<0||row.appliedSessions>row.loadedSessions)throw Error('Search settings could not be confirmed.');return row;
}
/** The original DSH scope face, bound only to this connected operator generation. */
export class DshSearchScope {
 listeners=new Set();generation=0;connection=null;closed=false;writing=false;
 state={status:'unavailable',writable:false,busy:false,error:null,accepted:null};
 constructor(controller){this.controller=controller;this.unsubscribe=controller.subscribe(()=>this.sync());this.sync();}
 subscribe=fn=>{this.listeners.add(fn);return()=>this.listeners.delete(fn);};getSnapshot=()=>this.state;
 publish(patch){this.state={...this.state,...patch};for(const fn of this.listeners)fn();}
 current(){const s=this.controller.state;return !this.closed&&s.phase==='ready'&&!s.readOnly&&s.capabilities?.searchSettings===true;}
 sync(){const s=this.controller.state,key=[this.controller.epoch,s.phase,s.readOnly,s.capabilities?.searchSettings===true].join(':');if(key===this.connection)return;this.connection=key;this.generation++;this.writing=false;this.publish({status:'unavailable',writable:false,busy:false,error:null,accepted:null,value:undefined,user:undefined});if(this.current())void this.load();}
 valid(ticket,epoch){return ticket===this.generation&&epoch===this.controller.epoch&&this.current();}
 confirm(row){this.publish({status:'ready',writable:!row.pending,busy:false,error:null,accepted:row,value:row.value,user:row.user});}
 async load(apply=false){
  if(!this.current()||this.state.busy||this.writing)return false;
  const ticket=++this.generation,epoch=this.controller.epoch;this.publish({status:this.state.accepted?'ready':'loading',writable:false,busy:true,error:null});
  try{const row=checked(await this.controller.rpc(apply?'search.refresh':'search.describe'));if(!this.valid(ticket,epoch))return false;this.confirm(row);return true;}
  catch{if(this.valid(ticket,epoch))this.publish({status:this.state.accepted?'ready':'unavailable',writable:false,busy:false,error:'Search settings could not be confirmed. Nothing was retried. Refresh to inspect the stored configuration.'});return false;}
 }
 async write(edit){
  // The supplier calls a sequence of field writes. Its first uncertain result
  // fences the remainder, including a clear; there is no automatic read/retry.
  if(!this.current()||!this.state.writable||this.state.busy||this.writing)return false;
  const ticket=++this.generation,epoch=this.controller.epoch;this.writing=true;this.publish({busy:true,error:null});
  try{const row=checked(await this.controller.rpc('search.set',{edit,expectedRevision:this.state.accepted.revision}));if(!this.valid(ticket,epoch))return false;if(row.pending)throw Error('Pending Search application');this.confirm(row);return true;}
  catch{if(this.valid(ticket,epoch))this.publish({writable:false,busy:false,error:'The save was not confirmed. Nothing was retried. Refresh to inspect the stored configuration.'});return false;}
  finally{if(this.valid(ticket,epoch))this.writing=false;}
 }
 set=(field,value)=>this.write({field,action:'set',value});
 unset=field=>this.write({field,action:'unset'});
 enable=value=>this.write({field:'enabled',action:'set',value});
 close(){this.closed=true;this.generation++;this.unsubscribe();this.state={status:'unavailable',writable:false,busy:false,error:null,accepted:null};this.listeners.clear();}
}
