// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {createSnapshotStore} from '@deepseek-ai/dsh-client-store';
import {watchFleetTab} from './vendor/dsh-context/src/client/fleetTab.ts';
import {watchPlacement} from './vendor/dsh-context/src/client/placement.ts';
import {watchSidebarContextTab} from './vendor/dsh-context/src/client/sidebar.ts';
import {DICT_EN} from './vendor/dsh-context/src/client/i18nEn.ts';

/** Bind the original plugin's presentation registrations to the copied slots.
 * These callbacks own UI entries only; no Cordis service or agent is mounted. */
export function bindContextSidebar(previews,settings,View,Fleet){
 const tab=createSnapshotStore(false),fleet=createSnapshotStore(false);
 tab.fleet=fleet;
 const slots={
  inject:(_name,setup)=>setup(),
  register:(entry,component)=>{
   if(entry.name==='conversation.view'&&entry.id==='fleet'){fleet.set(true);return()=>fleet.set(false);}
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
 const releaseFleet=watchFleetTab(ctx,settings,Fleet,key=>DICT_EN[key]??key,'dsh-context');
 previews.pluginDispose=()=>{releaseFleet();release();};
 return tab;
}
