// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Operator-scoped transient auth interaction. Lost writes are inspected, never replayed.
const empty=()=>({status:'idle',available:false,busy:false,needsRefresh:false,receipt:null,interaction:null,providers:[],accounts:[],error:null});
const active=row=>row&&['running','cancel-requested'].includes(row.state);
const string=(value,max)=>typeof value==='string'&&value.length<=max;
const link=value=>{try{const url=new URL(value);return string(value,32768)&&!url.username&&!url.password&&(url.protocol==='https:'||url.protocol==='http:'&&['localhost','127.0.0.1','[::1]'].includes(url.hostname));}catch{return false;}};
export class DshAccountScope {
 listeners=new Set();generation=0;closed=false;timer=null;pending=new Set();snapshot=empty();finishedId=null;
 constructor(models){this.models=models;this.controller=models.controller;this.epoch=this.controller.epoch;let ready=models.snapshot.status==='ready';this.unsubscribe=this.controller.subscribe(()=>{if(!this.current())this.retire();});this.unsubscribeModels=models.subscribe(()=>{const next=models.snapshot.status==='ready',reload=next&&!ready;ready=next;if(this.current()&&reload&&!this.snapshot.busy)void this.load();});}
 current(){return !this.closed&&this.models.current()&&this.controller.epoch===this.epoch&&this.controller.state.capabilities?.modelAccountLogin===true;}
 subscribe=fn=>{this.listeners.add(fn);return()=>this.listeners.delete(fn);};getSnapshot=()=>this.snapshot;
 publish(value){this.snapshot=value;for(const fn of this.listeners)fn();}
 retire(){this.generation++;clearTimeout(this.timer);for(const request of this.pending)request.abort();this.publish({...empty(),status:'error',error:'The account connection changed. Reopen Settings.'});}
 checked(value,id,provider){
  if(!value||typeof value.available!=='boolean'||typeof value.busy!=='boolean'||typeof value.needsRefresh!=='boolean'||JSON.stringify(value).length>256*1024)throw Error('Invalid account status.');
  const row=value.receipt;
  if(row!==null&&(!row||!string(row.requestId,128)||!row.requestId||!string(row.provider,256)||!row.provider||!['running','cancel-requested','completed','failed','cancelled','interrupted'].includes(row.state)||row.result!==(active(row)?'pending':row.state==='completed'?'credential-stored':'unknown')))throw Error('Invalid account receipt.');
  if(id&&(row?.requestId!==id||provider&&row?.provider!==provider))throw Error('The account action changed.');
  if(value.busy&&!active(row))throw Error('Another account action owns the active interaction.');
  if(value.interaction!==null&&(!value.interaction||!active(row)||!value.busy))throw Error('Invalid active account interaction.');
  const ui=value.interaction;
  if(ui){
   if(ui.authorizationUrl!==undefined&&!link(ui.authorizationUrl)||ui.verificationUri!==undefined&&!link(ui.verificationUri)||ui.deviceCode!==undefined&&!string(ui.deviceCode,1024)||ui.message!==undefined&&!string(ui.message,8000))throw Error('Invalid account information.');
   if(ui.links!==undefined&&(!Array.isArray(ui.links)||ui.links.length>16||ui.links.some(item=>!item||!link(item.url)||item.label!==undefined&&!string(item.label,1024))))throw Error('Invalid account links.');
   const prompt=ui.prompt;
   if(prompt&&(!string(prompt.id,128)||!prompt.id||!['select','text','secret','manual_code'].includes(prompt.type)||!string(prompt.message,8000)||prompt.placeholder!==undefined&&!string(prompt.placeholder,2048)))throw Error('Invalid account prompt.');
   if(prompt?.type==='select'&&(!Array.isArray(prompt.options)||!prompt.options.length||prompt.options.length>128||prompt.options.some(item=>!item||!string(item.id,512)||!string(item.label,1024)||item.description!==undefined&&!string(item.description,2048))||new Set(prompt.options.map(item=>item.id)).size!==prompt.options.length))throw Error('Invalid account options.');
  }
  for(const key of ['providers','accounts'])if(value[key]!==undefined&&(!Array.isArray(value[key])||value[key].length>256||value[key].some(item=>!item||typeof item.provider!=='string'||!item.provider||item.provider.length>256)))throw Error('Invalid account catalog.');
  return value;
 }
 async rpc(method,params,ticket){
  if(!this.current())throw Error('Account scope changed.');
  const abort=new AbortController();this.pending.add(abort);
  try{const value=await this.controller.rpc(method,params,abort.signal);if(ticket!==this.generation||!this.current())throw Error('Account scope changed.');return value;}finally{this.pending.delete(abort);}
 }
 adopt(value,ticket){
  if(ticket!==this.generation||!this.current())return;
  const previous=this.snapshot;
  this.publish({status:'ready',available:value.available,busy:value.busy,needsRefresh:value.needsRefresh,receipt:value.receipt,interaction:value.interaction,providers:value.providers??previous.providers,accounts:value.accounts??previous.accounts,error:null});
  if(value.busy){this.models.suspend();clearTimeout(this.timer);this.timer=setTimeout(()=>void this.read(value.receipt?.requestId,value.receipt?.provider,ticket),400);}
  else if(previous.busy&&value.receipt?.requestId!==this.finishedId){this.finishedId=value.receipt?.requestId;void this.models.load();}
 }
 fail(ticket){if(ticket!==this.generation||!this.current())return;clearTimeout(this.timer);this.publish({...this.snapshot,status:'error',available:false,interaction:null,error:'Account sign-in could not be confirmed. Refresh account status before another action. Nothing was retried.'});this.models.fail('Account sign-in is unconfirmed. Inspect account status and refresh model settings before editing again. Nothing was retried.');}
 async load(){
  if(!this.current())return;const ticket=++this.generation;clearTimeout(this.timer);
  try{this.adopt(this.checked(await this.rpc('models.accountDescribe',{},ticket)),ticket);}catch{this.fail(ticket);}
 }
 async read(id,provider,ticket=this.generation){
  if(!this.current()||ticket!==this.generation)return;
  try{this.adopt(this.checked(await this.rpc('models.accountStatus',{requestId:id},ticket),id,provider),ticket);}catch{this.fail(ticket);}
 }
 async start(provider,requestId){
  if(!this.current()||!this.models.accepted||!this.models.snapshot.writable||!this.snapshot.available||this.snapshot.busy||this.snapshot.needsRefresh||!this.snapshot.providers.some(row=>row.provider===provider))throw Error('Refresh model settings before signing in.');
  const ticket=++this.generation,revision=this.models.revision;clearTimeout(this.timer);this.models.suspend();
  this.publish({...this.snapshot,busy:true,receipt:{requestId,provider,state:'running',result:'pending'},interaction:null,error:null});
  try{this.adopt(this.checked(await this.rpc('models.accountStart',{provider,revision,requestId},ticket),requestId,provider),ticket);}
  catch{await this.read(requestId,provider,ticket);if(this.snapshot.status==='error')throw Error('Account sign-in admission is unconfirmed.');}
 }
 async respond(requestId,promptId,value){
  if(!this.current()||this.snapshot.receipt?.requestId!==requestId||this.snapshot.interaction?.prompt?.id!==promptId||!this.snapshot.busy)throw Error('This account prompt is no longer active.');
  const ticket=this.generation,provider=this.snapshot.receipt.provider;
  this.publish({...this.snapshot,interaction:{...this.snapshot.interaction,prompt:undefined}});
  try{const reply=await this.rpc('models.accountRespond',{requestId,promptId,value},ticket);if(reply?.accepted!==true||reply.requestId!==requestId||reply.promptId!==promptId)throw Error('Unconfirmed account response.');}finally{await this.read(requestId,provider,ticket);}
 }
 async cancel(requestId){
  const ticket=this.generation,provider=this.snapshot.receipt?.provider;
  try{this.adopt(this.checked(await this.rpc('models.accountCancel',{requestId},ticket),requestId,provider),ticket);}catch{await this.read(requestId,provider,ticket);if(this.snapshot.status==='error')throw Error('Account cancellation is unconfirmed.');}
 }
 close(){this.closed=true;this.generation++;clearTimeout(this.timer);for(const request of this.pending)request.abort();this.unsubscribe?.();this.unsubscribeModels?.();this.snapshot=empty();this.listeners.clear();}
}
