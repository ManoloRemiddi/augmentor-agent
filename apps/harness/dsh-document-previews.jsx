// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import React,{useSyncExternalStore} from 'react';
import {DocumentPreviewRegistry} from '@dsh-gui/ui-sidebar-documentpreview/src/client/document/registry.ts';
import {apply as registerPdf} from '@dsh-gui/ui-sidebar-documentpreview/src/client/pdf/index.ts';
import {apply as registerOffice} from '@dsh-gui/ui-sidebar-documentpreview/src/client/office/index.ts';
import {apply as registerExcel} from '@dsh-gui/ui-sidebar-documentpreview/src/client/excel/index.ts';
import {en as documentEn} from '@dsh-gui/ui-sidebar-documentpreview/src/client/locales.ts';

/** UI-only seats for original metadata, keyed slots, locale and tab lifetimes.
 * Supplier registrations execute here without a Cordis service or agent owner.
 * Parser objects, bytes and workers stay in their original mounted components. */
export class DshDocumentPreviews {
 constructor(definitions,remote){
  this.registry=new DocumentPreviewRegistry();this.slots=new Map();this.effects=[];this.resets=[];this.locales=new Map([['sidebarDocumentPreview',documentEn]]);this.stores=new Map();
  for(const definition of definitions)this.effects.push(this.registry.register(definition));
  const ctx={effect:setup=>{const dispose=setup();if(typeof dispose==='function')this.effects.push(dispose);},documentPreviews:this.registry,
   locale:{register:(name,dictionary)=>{this.locales.set(name,dictionary.en);return()=>this.locales.delete(name);},bind:name=>(key,args={})=>String(this.locales.get(name)?.[key]??key).replace(/\{(\w+)\}/g,(_match,field)=>String(args[field]??''))},
   slots:{inject:(name,setup)=>{if(!['sidebar.right.tab.document','sidebar.right.tab.document.action','sidebar.right.tab.document.office.pdf'].includes(name))throw Error('Unsupported document slot.');return setup();},register:(definition,Body)=>{
    const key=definition.name+':'+definition.key;if(this.slots.has(key))throw Error('Duplicate document slot.');
    if(definition.store&&!this.stores.has(definition.store))this.stores.set(definition.store,definition.store.create());
    const store=this.stores.get(definition.store),entry={definition,Body,store,faces:new Map(),t:ctx.locale.bind(definition.locale)};this.slots.set(key,entry);return()=>this.slots.delete(key);
   }},
   inject:(names,setup)=>{if(names.join(',')!=='remote,remote.officeToPdf,remote.workspaceFiles')throw Error('Unsupported document service seat.');setup({remote,effect:ctx.effect,on:(event,handler)=>{if(event!=='connection/reset')throw Error('Unsupported document event.');this.resets.push(handler);}});},
  };
  registerPdf(ctx);
  registerOffice(ctx,{maxCachedEntries:8,maxCachedBytes:64*1024*1024,maxPending:8,maxReaders:32});
  registerExcel(ctx,{maxBytes:16*1024*1024,maxCells:250_000,timeoutMs:15_000});
  this.useDefinitions=(selector=value=>value)=>selector(useSyncExternalStore(this.registry.subscribe,this.registry.getSnapshot));
 }
 render(key,sessionId,props,name='sidebar.right.tab.document'){const entry=this.slots.get(name+':'+key);if(!entry)return null;
  if(!entry.faces.has(sessionId))entry.faces.set(sessionId,{...(entry.definition.inject?.(sessionId,entry.store?.actions)??{}),...(entry.store?{useStore:(selector=value=>value)=>selector(useSyncExternalStore(entry.store.subscribe,entry.store.getSnapshot)),actions:entry.store.actions}:{}),t:entry.t});
  return React.createElement(entry.Body,{...props,...entry.faces.get(sessionId),renderSlot:(slot,owner,options={})=>this.render(options.entryKey,sessionId,{...owner,useTabInfo:options.hookContext??props.useTabInfo,useResource:props.useResource},slot)});
 }
 retire(){for(const reset of this.resets)reset();for(const store of this.stores.values())for(const tab of Object.keys(store.getSnapshot().byTab??{}))store.actions.forget(tab);for(const entry of this.slots.values())entry.faces.clear();}
 close(){this.retire();const retired=this.effects.toReversed().map(dispose=>dispose());this.effects=[];this.resets=[];this.slots.clear();this.locales.clear();this.stores.clear();return Promise.allSettled(retired);}
}
