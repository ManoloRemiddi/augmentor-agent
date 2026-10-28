// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
/** Service faces for the original MIT DSH slash source. Pi owns the catalog and
 * input expansion. No DSH Host, catalog scanner, model tool or agent is created. */
export function checkedSkillCatalog(value,sessionId){
 if(sessionId!==undefined&&value?.sessionId!==sessionId||value?.available!==true||typeof value.revision!=='string'||!Array.isArray(value.skills)||value.skills.length>2048||value.skills.some(row=>!row||typeof row.name!=='string'||!row.name.length||row.name.length>256||typeof row.description!=='string'||typeof row.path!=='string'||!row.path.length||row.path.length>4096||typeof row.modelInvocable!=='boolean'||![`/${row.name}`,`/skill:${row.name}`].includes(row.command)))throw Error(value?.reason??'The approved skill catalog is unavailable.');
 return value;
}
export function bindOriginalSkillSource({apply,controller,previews,valid,scope,dictionary}){
 const effects=[],handlers=new Map();let source,disposed=false,revision=controller.state.skillsRevision??0;
 const current=()=>!disposed&&valid(scope),session={sessionId:scope.sessionId};
 const binding=()=>current()?{session:{getSnapshot:()=>({openState:'open',openError:null})}}:undefined;
 const on=(name,fn)=>{const rows=handlers.get(name)??new Set();rows.add(fn);handlers.set(name,rows);return()=>rows.delete(fn);};
 const inputTriggers={registerSource:value=>{source=value;return()=>{source=undefined;};}};
 const ctx={locale:{register:()=>()=>{},bind:()=>key=>dictionary[key]??key},
  // The actual Pi skill load is an input preparation, so no synthetic skill
  // tool card is registered by this presentation-only source adapter.
  slots:{inject:()=>{}},get:name=>name==='inputTriggers'?inputTriggers:undefined,
  sessions:{binding,subagentAddress:()=>undefined,list:{getSnapshot:()=>({byId:Object.fromEntries(controller.state.sessions.map(row=>[row.sessionId,row]))})},async using(sid,{signal},fn){if(sid!==scope.sessionId||!binding())throw Error('The selected skill scope changed.');signal.throwIfAborted();const result=await fn({binding:binding()});signal.throwIfAborted();if(!current())throw Error('The selected skill scope changed.');return result;}},
  remote:{$on:on,skills:{async list({sessionId},signal){if(!current()||sessionId!==scope.sessionId)throw Error('The selected skill scope changed.');const catalog=checkedSkillCatalog(await controller.rpc('session.skills',{sessionId},signal),sessionId);if(!current())throw Error('The selected skill scope changed.');return {ok:true,value:{skills:catalog.skills.map(row=>({name:row.command.slice(1),path:row.path,description:row.description,modelInvocable:row.modelInvocable}))}};}}},
  sidebarRight:{openResource:address=>current()&&previews.openAddress(scope.sessionId,address)},on,effect(fn){const end=fn();if(typeof end==='function')effects.push(end);},
 };
 apply(ctx);if(!source)throw Error('The original skill source did not register.');
 const original=source;
 const off=controller.subscribe(()=>{const next=controller.state.skillsRevision??0;if(next!==revision){revision=next;for(const fn of handlers.get('agent-preset/selected')??[])fn(scope.sessionId);}});
 const wrapped={...original,candidates:(_,query)=>current()?original.candidates(session,query):Promise.resolve([]),warm:()=>{if(current())original.warm?.(session);},lexicon:()=>current()?original.lexicon?.(session):[],subscribeLexicon:(_,fn)=>current()?(original.subscribeLexicon?.(session,fn)??(()=>{})):(()=>{}),openReference:(_,params)=>current()&&original.openReference(session,params)};
 return {source:wrapped,dispose(){if(disposed)return;disposed=true;off();for(const end of effects.reverse())end();handlers.clear();}};
}
export async function openCurrentSkill(controller,previews,name){
 const scope={sessionId:controller.state.sessionId,epoch:controller.epoch};
 const current=()=>scope.sessionId===controller.state.sessionId&&scope.epoch===controller.epoch&&controller.state.phase==='ready'&&!controller.state.readOnly;
 if(!current()||!controller.state.capabilities?.skillReferences)throw Error('Skill source preview is unavailable in this conversation.');
 const catalog=checkedSkillCatalog(await controller.rpc('session.skills',{sessionId:scope.sessionId}),scope.sessionId);if(!current())return false;
 const skill=catalog.skills.find(row=>row.name===name);if(!skill)throw Error('That skill is not in the current approved resources. Its past instructions remain in the recorded conversation.');
 if(!previews.open(skill.path))throw Error('Skill source preview is unavailable in this conversation.');return true;
}
export function invokedSkillNames(event){const receipt=event?.data?.skillInvocation;if(receipt?.version!==1||typeof receipt.name!=='string'||receipt.name.length>256||!['sourceSha256','instructionsSha256','expandedInputSha256'].every(key=>/^[a-f0-9]{64}$/.test(receipt[key]))||receipt.boundary!=='managed-input-read; delivered-sdk-user-message')return [];return [receipt.name];}
