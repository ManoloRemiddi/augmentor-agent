// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
/** Private provider-edit seat. Accepted reads fence original supplier drafts;
 * ambiguous writes retire the page until an explicit fresh read. */
export class DshModelScope {
 listeners=new Set();generation=0;closed=false;revision=null;accepted=false;pendingDiscoveries=new Set();
 snapshot={status:'idle',error:null,credentialError:null,writable:false,rows:[],accounts:[],namespaces:new Map()};
 constructor(controller){this.controller=controller;this.epoch=controller.epoch;this.store={getSnapshot:this.getSnapshot,subscribe:this.subscribe};this.unsubscribe=controller.subscribe(()=>{if(!this.current())this.fail('The model settings connection changed. Reopen Settings.');});}
 subscribe=fn=>{this.listeners.add(fn);return()=>this.listeners.delete(fn);};getSnapshot=()=>this.snapshot;
 current(){return !this.closed&&this.epoch===this.controller.epoch&&this.controller.state.phase==='ready'&&!this.controller.state.readOnly&&this.controller.state.capabilities?.modelSettings===true;}
 publish(value){this.snapshot=value;for(const fn of this.listeners)fn();}
 cancelDiscoveries(){for(const request of this.pendingDiscoveries)request.abort();}
 suspend(){this.accepted=false;this.cancelDiscoveries();this.publish({...this.snapshot,status:'loading',writable:false,error:null});}
 fail(message){this.generation++;this.accepted=false;this.cancelDiscoveries();this.publish({...this.snapshot,status:'error',writable:false,error:message,rows:[],accounts:[],namespaces:new Map()});}
 checked(value){if(!value||value.writable!==true||!Number.isSafeInteger(value.revision)||!Array.isArray(value.rows)||!Array.isArray(value.namespaces)||value.namespaces.length!==1||value.namespaces[0]?.ns!=='llm-pi-ai'||value.namespaces[0].revision!==value.revision)throw Error('Invalid model settings descriptor.');return value;}
 async load(){
  if(!this.current()){this.fail('Connect with operator access to edit model settings.');return;}
  const ticket=++this.generation;this.accepted=false;this.publish({...this.snapshot,status:'loading',writable:false,error:null});
  this.cancelDiscoveries();
  try{const value=this.checked(await this.controller.rpc('models.settingsDescribe'));if(ticket!==this.generation||!this.current())return;this.adopt(value);}
  catch{if(ticket===this.generation&&this.current())this.fail('Could not confirm model settings. Refresh before editing.');}
 }
 adopt(value){
  const accounts=value.accounts??[];
  if(!Array.isArray(accounts)||accounts.length>256||accounts.some(row=>!row||typeof row.provider!=='string'||!row.provider||row.provider.length>256||typeof row.registered!=='boolean')||new Set(accounts.map(row=>row.provider)).size!==accounts.length)throw Error('Invalid stored account descriptor.');
  this.revision=value.revision;this.accepted=true;this.publish({status:'ready',error:null,credentialError:null,writable:true,rows:value.rows,accounts,namespaces:new Map(value.namespaces.map(ns=>[ns.ns,ns]))});
 }
 async logoutAccount(provider){
  if(this.controller.state.capabilities?.modelAccountLogout!==true)throw Error('Stored account management is unavailable.');
  try{const value=this.checked(await this.call('models.accountLogout',{provider,revision:this.revision},true));if(value.accounts?.some(row=>row.provider===provider))throw Error('The account is still stored.');this.adopt(value);}
  catch{if(!this.closed)this.fail('Account sign-out could not be confirmed. Refresh model settings before trying again. Nothing was retried.');throw Error('Account sign-out could not be confirmed.');}
 }
 async call(method,params={},mutation=false,signal){
  if(!this.current()||!this.accepted)throw Error('Refresh model settings before editing.');
  const ticket=this.generation;try{const value=await this.controller.rpc(method,params,signal);if(ticket!==this.generation||!this.current())throw Error('The model settings scope changed.');return value;}
  catch{if(mutation&&ticket===this.generation&&!this.closed)this.fail('The edit outcome could not be confirmed. Refresh model settings before editing again. Nothing was retried.');throw Error(mutation?'The edit outcome could not be confirmed. Refresh before editing again. Nothing was retried.':'The model settings read could not be confirmed.');}
 }
 operations={
  describeCredential:async ref=>{try{return await this.call('models.credentialDescribe',{ref});}catch{return undefined;}},
  storeCredential:async(ref,value)=>{try{const response=await this.call('models.credentialSet',{ref,value,revision:this.revision},true);if(!Number.isSafeInteger(response?.revision)||response.revision<=this.revision){this.fail('The credential outcome could not be confirmed. Refresh before editing.');return 'The credential outcome could not be confirmed.';}this.revision=response.revision;return undefined;}catch(error){return error.message;}},
  removeCredential:async()=> 'Remove the provider profile to remove its profile API key. Stored Pi account credentials are retained.',
  writeSettings:async(ns,ops,expected)=>{
   if(ns!=='llm-pi-ai')return {kind:'refused',message:'Unsupported model settings namespace.'};
   try{const before=this.revision,value=await this.call('models.settingsMutate',{ops,revision:expected??before},true);if(value?.kind==='written'&&value.view?.ns===ns&&Number.isSafeInteger(value.view.revision)&&value.view.revision>=before){this.revision=value.view.revision;return value;}if(value?.kind==='conflict'){this.fail('Model settings changed. Reopen the card before editing.');return value;}this.fail('The model settings write could not be confirmed. Refresh before editing.');return {kind:'refused',message:'The model settings write could not be confirmed.'};}catch(error){return {kind:'refused',message:error.message};}
  },
  discoverModels:async(ns,request)=>{if(ns!=='llm-pi-ai')return {kind:'refused',message:'Unsupported provider namespace.'};const abort=new AbortController();this.pendingDiscoveries.add(abort);try{const result=await this.call('models.settingsDiscover',{request},false,abort.signal);if(result?.kind==='found'){if(!Array.isArray(result.models)||result.models.length>4096)throw Error('Invalid model candidates.');}return result;}catch{return {kind:'refused',message:'The model list could not be confirmed. Nothing was saved or retried.'};}finally{this.pendingDiscoveries.delete(abort);}},
 };
 async refresh(){
  if(!this.current())return;try{await this.controller.rpc('models.settingsRefresh');if(this.current())await this.load();}catch{if(this.current())this.fail('Pi could not confirm the stored configuration. Inspect the model profile and refresh again.');}
 }
 close(){this.closed=true;this.generation++;this.accepted=false;this.cancelDiscoveries();this.snapshot={status:'idle',error:null,credentialError:null,writable:false,rows:[],accounts:[],namespaces:new Map()};this.unsubscribe?.();this.listeners.clear();}
}

const getPath=(value,path)=>path.reduce((current,key)=>current&&Object.hasOwn(current,key)?current[key]:undefined,value);
const safePath=path=>{if(path.some(key=>['__proto__','constructor','prototype'].includes(key)))throw Error('Invalid settings path.');return path;};
export const modelSchema={
 rehydrate:value=>value,
 nodeAtPath:(root,path)=>path.length===3&&path[0]==='providers'&&path[2]==='api'?{type:'union',list:root.apis.map(value=>({value}))}:{meta:{}},
 validate:()=>undefined,getPath,hasPath:(value,path)=>getPath(value,path)!==undefined,
 setPath:(value,path,entry)=>{const copy=structuredClone(value??{});safePath(path);let node=copy;for(const key of path.slice(0,-1))node=node[key]??={};node[path.at(-1)]=entry;return copy;},
 deletePath:(value,path)=>{const copy=structuredClone(value??{});safePath(path);let node=copy;for(const key of path.slice(0,-1)){node=node[key];if(!node)return copy;}delete node[path.at(-1)];return copy;},
};
