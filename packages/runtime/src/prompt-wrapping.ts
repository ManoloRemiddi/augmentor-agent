// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import type {ExtensionFactory} from '@earendil-works/pi-coding-agent';
import type {SystemMessage} from '@earendil-works/pi-ai';
import {watchPromptInjection,type PromptSection} from '../vendor/dsh-context-prompt.js';
import {contextPreferences} from './context-preferences.js';

/** Execute the original public section registration against a small Pi registry
 * seat. Request-time copies preserve native originals and every tool/section
 * declaration. Live preference reads apply from the next model call, not by
 * replaying a prompt or reloading its AgentSession. */
export function piPromptWrapping(read:()=>{revision:number;value:unknown},observe?:(record:unknown)=>void):ExtensionFactory{return pi=>{
 let value=contextPreferences({});const sections:PromptSection[]=[];
 watchPromptInjection({inject:(_dependencies,callback)=>callback({systemPrompt:{
  section:section=>{sections.push(section);return()=>{};},
  getSectionOrder:name=>name==='HARNESS_IDENTITY'?0:1000,
 }})},{promptPrefix:{get:()=>value.promptPrefix!},promptSuffix:{get:()=>value.promptSuffix!}});
 pi.on('context_with_system',event=>{
  const saved=read();value=contextPreferences(saved.value);
  const rendered=sections.toSorted((a,b)=>a.order-b.order).map(section=>({name:section.name,order:section.order,interpolate:section.interpolate,text:typeof section.text==='function'?section.text(null):section.text}));
  const prefix=rendered.find(section=>section.name==='dsh-context:prompt-prefix')?.text??'',suffix=rendered.find(section=>section.name==='dsh-context:prompt-suffix')?.text??'';
  const first=event.messages[0],systems=event.messages.map((message,index)=>message.role==='system'?index:-1).filter(index=>index>=0),last=systems.at(-1);
  let state='disabled',messages=event.messages,suffixSection:string|undefined;
  if(prefix||suffix){
   if(first?.role!=='system'||last===undefined)state='unavailable-no-leading-system-message';
   else{
    state='applied';messages=event.messages.slice();
    if(prefix)messages[0]={...first,content:typeof first.content==='string'?prefix+'\n\n'+first.content:[{type:'text',text:prefix+'\n\n'},...first.content]};
    if(suffix){
     // An approved extension may already own the canonical name. Append an
     // unused name rather than replacing any of its retained section values.
     const used=new Set(systems.flatMap(index=>Object.keys((messages[index] as SystemMessage).sections??{})));
     suffixSection='dsh-context:prompt-suffix';let ordinal=0;while(used.has(suffixSection))suffixSection='dsh-context:prompt-suffix:'+ ++ordinal;
     const end=messages[last] as SystemMessage;messages[last]={...end,sections:{...end.sections,[suffixSection]:suffix}};
    }
   }
  }
  try{observe?.({boundary:'managed-Pi-context-with-system-request-copy',revision:saved.revision,state,sections:rendered,...(suffixSection?{suffixSection}:{}),leadingSystemIndex:first?.role==='system'?0:null,lastSystemIndex:last??null,scope:'managed conversational requests; standalone improvement and summary requests are separate'});}catch{/* Inspection failure cannot change the composed request. */}
  return state==='applied'?{messages}:undefined;
 });
};}
