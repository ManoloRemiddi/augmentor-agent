// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import React,{useSyncExternalStore} from 'react';
import {DocumentPreviewRegistry} from '@dsh-gui/ui-sidebar-documentpreview/src/client/document/registry.ts';
import {apply as registerPdf} from '@dsh-gui/ui-sidebar-documentpreview/src/client/pdf/index.ts';

/** UI-only seats for original metadata, keyed slots, locale and tab lifetimes.
 * Supplier registrations execute here without a Cordis service or agent owner.
 * Parser objects, bytes and workers stay in their original mounted components. */
export class DshDocumentPreviews {
 constructor(definitions){
  this.registry=new DocumentPreviewRegistry();this.slots=new Map();this.effects=[];this.locales=new Map();this.stores=new Set();
  for(const definition of definitions)this.effects.push(this.registry.register(definition));
  const ctx={effect:setup=>{const dispose=setup();if(typeof dispose==='function')this.effects.push(dispose);},documentPreviews:this.registry,
   locale:{register:(name,dictionary)=>{this.locales.set(name,dictionary.en);return()=>this.locales.delete(name);},bind:name=>(key,args={})=>String(this.locales.get(name)?.[key]??key).replace(/\{(\w+)\}/g,(_match,field)=>String(args[field]??''))},
   slots:{inject:(name,setup)=>{if(name!=='sidebar.right.tab.document')throw Error('Unsupported document slot.');return setup();},register:(definition,Body)=>{
    if(definition.name!=='sidebar.right.tab.document'||this.slots.has(definition.key))throw Error('Unsupported or duplicate document slot.');
    const store=definition.store?.create();if(store)this.stores.add(store);const entry={definition,Body,store,faces:new Map(),t:ctx.locale.bind(definition.locale)};this.slots.set(definition.key,entry);return()=>{this.slots.delete(definition.key);if(store)this.stores.delete(store);};
   }},
  };
  registerPdf(ctx);
  this.useDefinitions=(selector=value=>value)=>selector(useSyncExternalStore(this.registry.subscribe,this.registry.getSnapshot));
 }
 render(key,sessionId,props){const entry=this.slots.get(key);if(!entry)return null;
  if(!entry.faces.has(sessionId))entry.faces.set(sessionId,{...(entry.definition.inject?.(sessionId,entry.store?.actions)??{}),...(entry.store?{useStore:(selector=value=>value)=>selector(useSyncExternalStore(entry.store.subscribe,entry.store.getSnapshot)),actions:entry.store.actions}:{}),t:entry.t});
  return React.createElement(entry.Body,{...props,...entry.faces.get(sessionId)});
 }
 retire(){for(const store of this.stores)for(const tab of Object.keys(store.getSnapshot().byTab??{}))store.actions.forget(tab);for(const entry of this.slots.values())entry.faces.clear();}
 close(){this.retire();for(const dispose of this.effects.toReversed())dispose();this.effects=[];this.slots.clear();this.locales.clear();this.stores.clear();}
}
