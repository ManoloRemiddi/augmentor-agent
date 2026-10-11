// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
const options={defaultGranularity:['step','turn'],defaultTrendMode:['total','delta'],defaultDeltaBase:['step','turn'],defaultToolSort:['size','count','name'],defaultFileSort:['count','latest','path'],insightsEntry:['show','hide'],defaultDurationCurve:['show','hide']};
const defaults={defaultPlacement:'tab',defaultGranularity:'step',defaultTrendMode:'total',defaultDeltaBase:'step',defaultToolSort:'count',defaultFileSort:'count',insightsEntry:'show',defaultDurationCurve:'show',fleetTab:'hide',promptPrefix:'',promptSuffix:''};
function checked(row){
 if(row?.ns!=='dsh-context'||!Number.isSafeInteger(row.revision)||row.revision<0||!row.value||typeof row.value!=='object'||Array.isArray(row.value)||!Array.isArray(row.writableFields))throw Error('Context preferences are unavailable from this Host.');
 const value={...defaults};for(const [field,choices] of Object.entries(options)){if(!choices.includes(row.value[field]))throw Error('The Host returned invalid Context preferences.');value[field]=row.value[field];}
 return {value,revision:row.revision,writableFields:row.writableFields.filter(field=>Object.hasOwn(options,field))};
}
/** Original settings.attach face, fenced to the current operator connection.
 * No automatic mutation retry, inference, session.open or browser storage. */
export class DshContextPreferences{
 listeners=new Set();generation=0;connection=null;
 state={status:'loading',value:{...defaults},writable:false,writableFields:[],revision:null,busy:false,error:null};
 constructor(controller){this.controller=controller;this.unsubscribe=controller.subscribe(()=>this.sync());this.sync();}
 subscribe=fn=>{this.listeners.add(fn);return()=>this.listeners.delete(fn);};
 getSnapshot=()=>this.state;
 publish(patch){this.state={...this.state,...patch};for(const fn of this.listeners)fn();}
 current(){return this.controller.state.phase==='ready'&&!this.controller.state.readOnly;}
 valid(ticket,epoch){return ticket===this.generation&&epoch===this.controller.epoch&&this.current();}
 sync(){
  const key=[this.controller.epoch,this.controller.state.phase,this.controller.state.readOnly].join(':');if(key===this.connection)return;this.connection=key;this.generation++;
  if(!this.current()){this.publish({status:this.controller.state.readOnly?'ready':'loading',value:{...defaults},writable:false,writableFields:[],revision:null,busy:false,error:null});return;}
  void this.load();
 }
 async load(){
  if(!this.current())return;const ticket=++this.generation,epoch=this.controller.epoch;this.publish({status:'loading',writable:false,busy:true,error:null});
  try{const result=await this.controller.rpc('settings.describe',{ns:'dsh-context'});if(!this.valid(ticket,epoch))return;const row=checked(result?.namespaces?.find(row=>row.ns==='dsh-context'));this.publish({...row,status:'ready',writable:true,busy:false});}
  catch(error){if(this.valid(ticket,epoch))this.publish({status:'ready',writable:false,busy:false,error:error.message+' Refresh preferences to read the current Host state.'});}
 }
 set=async(field,value)=>{
  if(!this.current()||!this.state.writable||this.state.busy||!this.state.writableFields.includes(field)||!Object.hasOwn(options,field)||!options[field].includes(value))throw Error('This Context preference is currently read-only.');
  const ticket=++this.generation,epoch=this.controller.epoch,before=this.state;this.publish({writable:false,busy:true,error:null});
  try{const result=await this.controller.rpc('settings.mutate',{ns:'dsh-context',expectedRevision:before.revision,ops:[{op:'set',path:[field],value}]});if(!this.valid(ticket,epoch))return;const row=checked(result);if(row.revision<=before.revision||row.value[field]!==value)throw Error('The Host did not confirm this preference.');this.publish({...row,status:'ready',writable:true,busy:false});}
  catch(error){if(this.valid(ticket,epoch))this.publish({value:before.value,revision:before.revision,status:'ready',writable:false,busy:false,error:error.message+' Nothing was retried. Refresh preferences before making another choice.'});throw error;}
 };
 close(){this.generation++;this.unsubscribe();this.listeners.clear();}
}
