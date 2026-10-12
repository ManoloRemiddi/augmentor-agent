// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import React,{useEffect,useRef,useState,useSyncExternalStore} from 'react';
import {SettingsRoot} from '@dsh-gui/ui-settings-general/src/client/SettingsRoot.tsx';
import {createSettingsShellStore} from '@dsh-gui/ui-settings-general/src/client/shell-store.ts';
import {TriggerContent,HeaderContent,CloseLabel} from '@dsh-gui/ui-settings-general/src/client/chrome.tsx';
import {GeneralSection} from '@dsh-gui/ui-settings-general/src/client/GeneralSection.tsx';
import {CurrentVersionRow} from '@dsh-gui/ui-settings-general/src/client/CurrentVersionRow.tsx';
import {DeveloperToolsRow} from '@dsh-gui/ui-settings-general/src/client/DeveloperToolsRow.tsx';
import {en as settingsEn} from '@dsh-gui/ui-settings-general/src/client/locales.ts';
import {AppearanceRow} from '@dsh-gui/ui-theme/src/client/AppearanceRow.tsx';
import {en as themeEn} from '@dsh-gui/ui-theme/src/client/locales.ts';
import {Button} from '@deepseek-ai/dsh-client-ui-primitives';
import {createSnapshotStore} from '@deepseek-ai/dsh-client-store';
import {attachReasoning} from '../browser/extension/pi-reasoning.mjs';
import {attachMcpManagement} from './mcp-management.js';
import {DshContextSettingsCard} from './dsh-context-settings.jsx';

export const settingsShell=createSettingsShellStore().create();
const face=value=>(select=x=>x)=>select(value);
const bind=source=>(select=x=>x)=>select(useSyncExternalStore(source.subscribe,source.getSnapshot));
const useShell=bind(settingsShell);
const translate=dictionary=>(key,args={})=>String(dictionary[key]??key).replace(/\{(\w+)\}/g,(_,name)=>String(args[name]??''));
const t=translate(settingsEn),themeT=translate(themeEn);
const sections=[{id:'general',order:0,label:t('general.nav')},{id:'models',order:1,label:'Models'},{id:'plugins',order:2,label:'Plugins'}];

// Existing light/dark choices keep their meaning until an explicit new choice.
const persisted=localStorage.getItem('augmentor.dsh.theme');
const appearance=createSnapshotStore({preference:['light','dark','system'].includes(persisted)?persisted:localStorage.getItem('augmentor.dsh.dark')==='1'?'dark':'light'});
const useAppearance=bind(appearance),systemTheme=matchMedia('(prefers-color-scheme: dark)');
const applyTheme=()=>document.body.toggleAttribute('data-ds-dark-theme',appearance.getSnapshot().preference==='dark'||appearance.getSnapshot().preference==='system'&&systemTheme.matches);
const setTheme=preference=>{localStorage.setItem('augmentor.dsh.theme',preference);appearance.set({preference});applyTheme();localStorage.setItem('augmentor.dsh.dark',document.body.hasAttribute('data-ds-dark-theme')?'1':'0');};
systemTheme.addEventListener('change',applyTheme);applyTheme();

/** Existing Pi handlers retain their scoped authority and dialog lifecycle. */
function ManagedSetting({kind,state,controller,notice}){
  const button=useRef(null),latest=useRef(state),handler=useRef(null);latest.current=state;
  useEffect(()=>{
    let disposed=false;
    const current=()=>({sessionId:latest.current.sessionId,epoch:controller.epoch,ready:!disposed&&!latest.current.readOnly&&latest.current.phase==='ready'&&!latest.current.sessions.find(x=>x.sessionId===latest.current.sessionId)?.running});
    handler.current=(kind==='reasoning'?attachReasoning:attachMcpManagement)({button:button.current,rpc:(method,params)=>controller.rpc(method,params),current,notice});
    return ()=>{disposed=true;handler.current?.close();handler.current=null;};
  },[kind,controller,notice]);
  useEffect(()=>{handler.current?.changed();},[state,controller.epoch]);
  return <Button ref={button} disabled={state.readOnly||!state.sessionId||state.phase!=='ready'||state.sessions.find(x=>x.sessionId===state.sessionId)?.running}>{kind==='reasoning'?'Reasoning settings':'MCP servers'}</Button>;
}

function InspectionSettings({state,controller}){
  const [capture,setCapture]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState(null),live=useRef(state),generation=useRef(0);live.current=state;
  const read=async()=>{
    const ticket=++generation.current;setBusy(true);setError(null);
    try{const value=await controller.rpc('observation.describe');if(ticket===generation.current)setCapture(value);}
    catch(e){if(ticket===generation.current){setCapture(null);setError(e.message);}}
    finally{if(ticket===generation.current)setBusy(false);}
  };
  useEffect(()=>{void read();return ()=>{generation.current++;};},[controller,state.readOnly]);
  const configure=async()=>{
    if(busy||!capture||live.current.readOnly||live.current.phase!=='ready')return;
    const ticket=++generation.current,epoch=controller.epoch,sid=live.current.sessionId;setBusy(true);setError(null);
    const valid=()=>ticket===generation.current&&epoch===controller.epoch&&sid===live.current.sessionId&&!live.current.readOnly&&live.current.phase==='ready';
    try{
      const before=await controller.rpc('observation.describe');if(!valid())return;
      const value=await controller.rpc('observation.configure',{expectedRevision:before.revision,capturePayloads:!before.capturePayloads});if(valid())setCapture(value);
    }catch(e){if(valid()){setCapture(null);setError(e.message+' Refresh capture state before making another change. Nothing was retried.');}}
    finally{if(ticket===generation.current)setBusy(false);}
  };
  return <>
    <Button onClick={()=>window.open('/inspection#'+new URLSearchParams({token:controller.token,session:state.sessionId||''}),'_blank','noopener,noreferrer')}>Full Pi record inspector</Button>
    <Button disabled={state.readOnly||state.phase!=='ready'||!capture||busy} onClick={()=>void configure()}>Request payload capture: {capture===null?'unavailable':capture.capturePayloads?'on':'off'}</Button>
    {error&&<><p role="status">{error}</p><Button disabled={busy} onClick={()=>void read()}>Refresh capture state</Button></>}
  </>;
}


function HtmlPreviewSetting({developerTools,state}){
 const accepted=useSyncExternalStore(developerTools.subscribe,developerTools.getSnapshot),source=developerTools.preference.enabled;
 const useDeveloperTools=selector=>selector(useSyncExternalStore(source.subscribe,source.getSnapshot));
 const copy=translate({...settingsEn,'developerTools.title':'Interactive HTML previews','developerTools.description':'Run scripts from previewed HTML documents in an isolated frame. External requests are blocked.','developerTools.error':'The setting could not be confirmed. Refresh before choosing again.'});
 return <><DeveloperToolsRow t={copy} useDeveloperTools={useDeveloperTools} setEnabled={enabled=>developerTools.preference.setEnabled(enabled)} disabled={state.readOnly||accepted.busy||!accepted.writable}/>{accepted.error&&<div className="augmentor-extension"><p role="status">{accepted.error}</p><Button disabled={accepted.busy} onClick={()=>void developerTools.load()}>Refresh HTML preview setting</Button></div>}</>;
}

/** Pure supplier shell; section contents call the existing Pi owner. */
export function OriginalSettings({wide,state,controller,preferences,developerTools,shortcutsUi,onPrompts,onContext,notice}){
  const renderSlot=(name,owner={},options={})=>{
    if(name==='settings.trigger')return <TriggerContent {...owner} t={t}/>;
    if(name==='settings.header')return <HeaderContent t={t}/>;
    if(name==='settings.close')return <CloseLabel t={t}/>;
    if(name==='settings.section'){
      if(options.only==='general')return <GeneralSection renderSlot={renderSlot}/>;
      if(options.only==='models')return <GeneralSection renderSlot={()=> <div className="augmentor-extension"><p>Current model: {state.selection?state.selection.provider+' / '+state.selection.model:'No model selected'}. Use the conversation model chooser to change it.</p><ManagedSetting kind="reasoning" state={state} controller={controller} notice={notice}/></div>}/>;
      if(options.only==='plugins')return <GeneralSection renderSlot={()=> <div className="augmentor-extension"><ManagedSetting kind="mcp" state={state} controller={controller} notice={notice}/><p>dsh-context 0.68.1 · Apache-2.0</p><DshContextSettingsCard preferences={preferences}/><Button onClick={()=>{owner.close();onContext();}}>Open Context</Button></div>}/>;
    }
    if(name==='settings.general.item')return <><AppearanceRow t={themeT} useStore={useAppearance} setTheme={setTheme}/>{developerTools&&<HtmlPreviewSetting developerTools={developerTools} state={state}/>}<div className="augmentor-extension"><Button disabled={state.readOnly} onClick={()=>{settingsShell.actions.close();onPrompts();}}>Prompt library</Button><InspectionSettings state={state} controller={controller}/></div>{shortcutsUi?.render('settings.general.item')}<CurrentVersionRow t={t}/></>;
    return options.fallback??null;
  };
  return <SettingsRoot wide={wide} t={t} useStore={useShell} actions={settingsShell.actions} renderSlot={renderSlot} useSections={face(sections)} useOnboardingSteps={face([])} useSessions={face({phase:state.phase,byId:{}})} useShortcuts={shortcutsUi?.useCatalog??face([])} useDesktopUpdate={face({failed:false,opening:false})} openDesktopUpdate={()=>{}} useConnectionState={face(state.phase==='ready'?'connected':state.phase==='connecting'?'connecting':'disconnected')} reconnect={()=>void controller.start(controller.state.sessionId).catch(e=>notice(e.message))}/>;
}
