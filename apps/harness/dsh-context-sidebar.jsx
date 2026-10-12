// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {createSnapshotStore} from '@deepseek-ai/dsh-client-store';
import {watchPlacement} from './vendor/dsh-context/src/client/placement.ts';
import {watchSidebarContextTab} from './vendor/dsh-context/src/client/sidebar.ts';
import {DICT_EN} from './vendor/dsh-context/src/client/i18nEn.ts';

/** Bind the original plugin's presentation registrations to the copied slots.
 * These callbacks own UI entries only; no Cordis service or agent is mounted. */
export function bindContextSidebar(previews,settings,View){
 const tab=createSnapshotStore(false);
 const slots={
  inject:(_name,setup)=>setup(),
  register:(entry,component)=>{
   const key=entry.name+'::'+entry.key;
   if(previews.slots.has(key))throw Error('Sidebar presentation is already registered.');
   previews.slots.set(key,component);
   return ()=>{if(previews.slots.get(key)===component)previews.slots.delete(key);};
  },
 };
 const ctx={slots,sidebarRightTabs:previews.registry,inject:(_names,setup)=>{
  const release=setup(ctx);let disposed=false;
  return {dispose(){if(!disposed){disposed=true;release?.();}}};
 }};
 const release=watchPlacement(settings,{
  tab:()=>{tab.set(true);return()=>tab.set(false);},
  sidebar:()=>watchSidebarContextTab(ctx,View,key=>DICT_EN[key]??key,'dsh-context'),
 });
 previews.pluginDispose=release;
 return tab;
}
