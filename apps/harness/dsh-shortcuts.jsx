// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Settings/left-sidebar command definitions derive from MIT DSH ui-settings-general
// and ui-layout client index.ts at d743267; original supplier notice remains retained.
import React,{useSyncExternalStore} from 'react';
import {ShortcutRegistry} from '@dsh-gui/shortcuts/src/client/registry.ts';
import {detectEnvironment,installKeyboard} from '@dsh-gui/shortcuts/src/client/dom.ts';
import {bindingIssue,normalizeBinding,overlappingBindings,presentBinding,initialShortcutConfig,parseShortcutDocument,editShortcutDocument} from '@dsh-gui/shortcuts/src/protocol.ts';
import {apply as registerReference} from '@dsh-gui/ui-shortcuts/src/client/index.ts';
import {installWorkspaceShortcuts} from '@dsh-gui/ui-workspace/src/client/shortcuts.ts';
import {registerSidebarShortcuts} from '@dsh-gui/ui-sidebar-right/src/client/shortcuts.ts';
import {sidebarTargetFromElement,observeSidebarFocus} from '@dsh-gui/ui-sidebar-right/src/client/focus.ts';
import {closeTopModal} from '@deepseek-ai/dsh-client-ui-primitives';
import {DshShortcutScope,checkedShortcutSnapshot} from './dsh-shortcut-scope.mjs';
const hook=source=>(selector=x=>x)=>selector(useSyncExternalStore(source.subscribe,source.getSnapshot));
/** UI-only seats for original registrants, settings row, reference and recorder.
 * Every action calls the existing control's owner; opaque frames get no bridge. */
export class DshShortcuts {
 actions={};main=null;slots=new Map();disposers=[];dictionaries=new Map();stopSequenceMs=1200;
 constructor(controller,{previews,layout,workspaceControls,settingsShell,dictionaries}){
  Object.assign(this,{controller,previews,layout,workspaceControls,settingsShell});for(const [k,v] of Object.entries(dictionaries))this.dictionaries.set(k,v);
  this.platform=detectEnvironment(document,navigator).platform;this.runtime='web';this.registry=new ShortcutRegistry(this.runtime,this.platform,initialShortcutConfig());
  this.catalog=this.registry.catalog;this.config=this.registry.config;this.fixedCatalog=this.registry.fixedCatalog;this.useCatalog=hook(this.catalog);
  this.scope=new DshShortcutScope(controller,{platform:this.platform,definitions:()=>this.registry.definitions(),initial:initialShortcutConfig(),validate:(row,unreadable)=>checkedShortcutSnapshot(row,parseShortcutDocument,unreadable),editDocument:(document,edit)=>editShortcutDocument(document,edit,this.runtime,this.platform)});
  this.config=this.scope;this.disposers.push(this.scope.subscribe(()=>{const snapshot=this.scope.getSnapshot();this.registry.configure(this.scope.accepted?snapshot:{...snapshot,status:'loading'});}));
  const ctx={shortcuts:this,layout:{panelInfo:{getSnapshot:()=>layout.getSnapshot().panelInfo}},sessions:{list:{getSnapshot:()=>({byId:this.main?{[this.main.id]:this.main}:{}})}},
   locale:{register:(name,dictionary)=>{this.dictionaries.set(name,dictionary.en);return()=>this.dictionaries.delete(name);},bind:name=>(key,args={})=>String(this.dictionaries.get(name)?.[key]??key).replace(/\{(\w+)\}/g,(_match,field)=>String(args[field]??''))},
   effect:setup=>{const release=setup();if(typeof release==='function')this.disposers.push(release);},
   slots:{entries:name=>name==='sidebar.workspaces.directoryFlow'?[{}]:[],inject:(_name,setup)=>setup(),register:(definition,Component)=>{
    const key=definition.name+':'+definition.id,store=definition.store?.create(),injected=definition.inject?.()??{},hooks=Object.fromEntries(Object.entries(injected.hooks??{}).map(([name,source])=>['use'+name[0].toUpperCase()+name.slice(1),hook(source)]));
    this.slots.set(key,{Component,props:{...injected,...hooks,...(store?{useStore:hook(store),actions:store.actions}:{}),t:ctx.locale.bind(definition.locale)}});return()=>this.slots.delete(key);
   }},
  };
  registerReference(ctx);
  installWorkspaceShortcuts(ctx,{startSession:()=>this.run('startSession'),forkSession:sid=>this.run('forkSession',sid)},workspaceControls,sid=>this.run('archiveSession',sid));
  this.disposers.push(registerSidebarShortcuts(this,this.sidebarSeat(),ctx.locale.bind('sidebarRight'),()=>{}));
  // Preserve the upstream browser bindings; supply its omitted web:linux profile
  // from web:windows in register(), with the original reservation checks intact.
  const defaults=(code,desktop,web)=>Object.fromEntries(['desktop:macos','desktop:windows','desktop:linux','web:macos','web:windows'].map(profile=>[profile,{code,modifiers:profile.startsWith('desktop:')?desktop:web}]));
  this.register({id:'sidebar.left.toggle',label:()=>dictionaries.layout.toggle,aliases:['sidebar','toggle left sidebar'],defaults:defaults('KeyB',['primary'],['primary','alt']),regions:['page','editable'],modals:[],resolve:()=>({status:'handled',run:()=>layout.actions.toggleSidebar()})});
  this.register({id:'settings.open',label:()=>dictionaries.settings['shortcut.open'],aliases:['settings','preferences'],defaults:defaults('Comma',['primary'],['primary','alt']),regions:['page','editable','terminal'],modals:['settings'],resolve:({modal})=>modal!==null&&modal!=='settings'?{status:'blocked',reason:'modal'}:{status:'handled',run:()=>modal==='settings'?closeTopModal(document):settingsShell.actions.open()}});
  this.disposers.push(installKeyboard(window,this),observeSidebarFocus(document));
 }
 ready(){return this.scope.current()&&this.scope.accepted;}
 run(name,...args){if(!this.ready())return Promise.reject(Error('Shortcut action is unavailable.'));return this.actions[name]?.(...args);}
 update(actions,main){if(this.main?.id!==main?.id&&this.workspaceControls.state.getSnapshot().renameTarget)this.workspaceControls.closeRename();this.actions=actions;this.main=main;}
 register(command){
  const defaults={...command.defaults,...(!command.defaults['web:linux']&&command.defaults['web:windows']&&bindingIssue(normalizeBinding(command.defaults['web:windows'],'linux'),'web','linux')===null?{'web:linux':command.defaults['web:windows']}:{})};
  const mutations=new Set(['session.new','workspace.add','session.rename','session.fork','session.archive']);
  const release=this.registry.register({...command,defaults,resolve:context=>mutations.has(command.id)&&(!this.ready())?{status:'blocked',reason:'Unavailable conversation'}:command.resolve(context)});this.disposers.push(release);return release;
 }
 registerFixed=command=>{const release=this.registry.registerFixed(command);this.disposers.push(release);return release;};
 dispatch(gesture,context,consume){return this.ready()?this.registry.dispatch(gesture,context,consume):{status:'pass'};}
 edit=(...args)=>this.scope.edit(...args);
 recording=async()=>{};
 describeBinding=binding=>{const normalized=binding===null?null:normalizeBinding(binding,this.platform);return {binding:normalized,keys:presentBinding(normalized,this.platform).keys,issue:normalized===null?null:bindingIssue(normalized,this.runtime,this.platform),conflicts:normalized===null?[]:[...this.catalog.getSnapshot().filter(row=>row.binding!==null&&overlappingBindings(row.binding,normalized)).map(row=>row.id),...this.fixedCatalog.getSnapshot().filter(row=>row.bindings.some(binding=>overlappingBindings(binding,normalized))).map(row=>row.id)]};};
 sidebarSeat(){
  const p=this.previews,current=target=>p.enabled()&&p.layout.getSnapshot().panelInfo.activePanelId===null&&target?.sessionId===p.controller.state.sessionId;
  const layout=()=>p.sidebar.getSnapshot().bySession[p.controller.state.sessionId]?.layout;
  const occurrence=id=>p.domain.occurrence(p.controller.state.sessionId,{id});
  const focused=element=>{const l=layout();return p.enabled()&&p.layout.getSnapshot().panelInfo.activePanelId===null&&l?sidebarTargetFromElement(element??document.activeElement,p.controller.state.sessionId,l,occurrence):undefined;};
  const isTargetCurrent=target=>{const l=layout();return current(target)&&l?.nodes[target.paneId]?.kind==='pane'&&(target.tabId===undefined||l.tabs[target.tabId]&&occurrence(target.tabId)===target.occurrence&&target.occurrence.navigation.getSnapshot().revision===target.navigationRevision);};
  return {focusedTarget:focused,commandTarget:()=>{const l=layout();if(!p.enabled()||p.layout.getSnapshot().panelInfo.activePanelId!==null||!l)return;const pane=Object.values(l.nodes).find(n=>n.kind==='pane'&&n.host==='dock');return pane?{sessionId:p.controller.state.sessionId,paneId:pane.id,host:'dock'}:undefined;},isTargetCurrent,
   toggleExpanded:()=>p.sidebar.actions.toggleExpanded(p.controller.state.sessionId),
   splitBlock:target=>!isTargetCurrent(target)?'stale':target.host==='float'?'float':!p.canSplit(target.paneId)?'noRoom':undefined,
   split:paneId=>p.sidebar.actions.splitPane(p.controller.state.sessionId,paneId),
   toggleFullscreen:()=>p.toggleFullscreen(),canCloseTarget:target=>isTargetCurrent(target)&&target.tabId!==undefined,
   closeTarget:target=>p.sidebar.actions.closeTab(target.sessionId,target.tabId)};
 }
 render(name){const entry=this.slots.get(name+':shortcuts');return entry?React.createElement(entry.Component,entry.props):null;}
 close(){this.scope.close();for(const release of this.disposers.reverse())release();this.slots.clear();this.actions={};this.main=null;}
}
