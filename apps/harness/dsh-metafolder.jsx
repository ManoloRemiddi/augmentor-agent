// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import React,{useEffect,useSyncExternalStore} from 'react';
import original from '@dsh-metafolder';
import {DeveloperToolsRow} from '@dsh-gui/ui-settings-general/src/client/DeveloperToolsRow.tsx';
import {Button,IconPinFillRegular} from '@deepseek-ai/dsh-client-ui-primitives';
let faces,Browser;
const snapshot=()=>faces;
function guard(){if(!faces||faces.controller.state.phase!=='ready'||faces.controller.state.readOnly||!faces.profile.getSnapshot().value.enabled)throw Error('The Metafolder view is no longer available.');return faces;}
async function invoke(run){const f=guard(),epoch=f.controller.epoch;const value=await run(f);if(epoch!==f.controller.epoch||!f.profile.getSnapshot().value.enabled||f.controller.state.readOnly)throw Error('The view changed. Inspect the saved workspace before continuing; nothing was retried.');return value;}
const adapter={
 useDocument(){const f=snapshot(),s=useSyncExternalStore(f.profile.subscribe,f.profile.getSnapshot);return [s.value.document,f.profile.update];},
 useView(){const f=snapshot();return useSyncExternalStore(f.workspaceView.subscribe,f.workspaceView.getSnapshot);},
 useShortcuts(){const f=snapshot();return useSyncExternalStore(f.shortcuts.state.subscribe,f.shortcuts.state.getSnapshot);},
 startSession(wid){const f=guard(),w=f.workspaces.items.find(w=>w.workspaceId===wid);if(wid!==undefined&&!w)throw Error('The workspace changed. Refresh before creating a conversation.');f.startSession(w?.cwd);},
 forkSession(sid){guard().sessionActions.forkSession(sid);},
 archived(sid){return snapshot().workspaces.archivedSessionIds.includes(sid);},
 visibleSession(sid){const f=snapshot(),archived=adapter.archived(sid),filter=f.workspaceView.getSnapshot().archivedFilter??'default';return filter==='only'?archived:filter==='show'||!archived;},
 sessionOrder(account){return snapshot().workspaceView.getSnapshot().sessionOrderByAccount?.[account];},
 orderPinned(nodes){const pins=new Set(snapshot().workspaces.pinnedSessionIds);return nodes.slice().sort((a,b)=>Number(pins.has(b.id))-Number(pins.has(a.id)));},
 pinMarker(sid){return snapshot().workspaces.pinnedSessionIds.includes(sid)?<span className="wsg-glyph" aria-label="Pinned"><IconPinFillRegular size={14}/></span>:null;},
 rowActions(sid){return snapshot().rowActions(sid);},
 sessionMenuItems(sid){const f=snapshot();if(adapter.archived(sid))return [{id:'restore',label:f.t('menu.unarchiveSession'),run:()=>guard().sessionActions.unarchiveSession(sid)}];const pinned=f.workspaces.pinnedSessionIds.includes(sid);return [{id:'pin',label:f.t(pinned?'menu.unpinSession':'menu.pinSession'),run:()=>{const a=guard().sessionActions;(pinned?a.unpinSession:a.pinSession)(sid);}}];},
 viewItems(){const f=snapshot(),filter=f.workspaceView.getSnapshot().archivedFilter??'default';return [{sep:true,id:'archive-sep'},...['default','show','only'].map((id,i)=>({id:'archive-'+id,label:(filter===id?'✓  ':'')+f.t(['viewOptions.hideArchived','viewOptions.showArchived','viewOptions.onlyArchived'][i]),run:()=>guard().workspaceView.actions.setArchivedFilter(id)}))];},
 closeAdd(){snapshot().shortcuts.closeAdd();},
};
const services={
 'augmentor.metafolder':adapter,
 locale:{getLocale:()=>({id:'en'})},
 layout:{selectPanel:id=>guard().layout.actions.selectPanel(id)},
 sessions:{list:{getSnapshot:()=>snapshot().list},open:sid=>guard().open(sid),search:async(query,signal)=>({ok:true,value:await invoke(f=>f.searchSessions(query,signal))}),searchResultLimit:100,binding:sid=>({session:{rename:title=>invoke(async f=>{const value=await f.controller.rpc('session.rename',{sessionId:sid,title});await f.controller.refresh();return value;})}})},
 workspaces:{list:{getSnapshot:()=>{const s=snapshot().workspaces;return {...s,items:s.items.map(w=>({...w,path:w.cwd}))};}},create:({path})=>invoke(f=>f.controller.adoptWorkspace(path)),rename:(workspaceId,title)=>invoke(f=>f.controller.workspaceAction('rename',{workspaceId,title})),delete:workspaceId=>invoke(f=>f.controller.workspaceAction('remove',{workspaceId})),insertBefore:(workspaceId,beforeWorkspaceId)=>invoke(f=>f.controller.workspaceAction('move',{workspaceId,beforeWorkspaceId})),archiveSession:sid=>guard().sessionActions.archiveSession(sid)},
 slots:{inject:(_,fn)=>fn(),register:(_,component)=>{if(Browser)throw Error('Duplicate Metafolder seat.');Browser=component;return ()=>{};}},
};
function ensureBrowser(){if(Browser)return;original.apply({get:key=>services[key],effect:fn=>fn(),remote:{directoryPicker:{list:path=>invoke(async f=>({ok:true,value:await f.controller.rpc('workspace.listDirectory',path?{path}:{})}))}}});if(!Browser)throw Error('The original Metafolder component was not registered.');}

export function MetafolderSettings({profile}){
 const s=useSyncExternalStore(profile.subscribe,profile.getSnapshot),useEnabled=select=>select(s.value.enabled);
 const t=key=>({'developerTools.title':'Metafolders','developerTools.description':'Group workspaces and conversations using the original Metafolder interface. Saved groups stay with this profile.','developerTools.error':'The change was not confirmed. Refresh before changing groups again.'}[key]??key);
 return <><DeveloperToolsRow t={t} useDeveloperTools={useEnabled} setEnabled={profile.setEnabled} disabled={!s.writable||s.busy}/>{s.error&&<p role="status">{s.error}</p>}{s.error&&<Button disabled={s.busy} onClick={()=>void profile.load()}>Refresh Metafolders</Button>}</>;
}
export function MetafolderSidebar(props){
 faces=props;
 ensureBrowser();
 const s=useSyncExternalStore(props.profile.subscribe,props.profile.getSnapshot);
 useEffect(()=>()=>props.shortcuts.closeAdd(),[props.shortcuts]);
 const useSessions=select=>select({...props.list,current:props.state.sessionId});
 const useWorkspaces=select=>select({...props.workspaces,items:props.workspaces.items.map(w=>({...w,path:w.cwd}))});
 const pending=new Map((props.state.interactions||[]).map(frame=>[props.state.sessionId,{kind:frame.method==='question/requested'?'question':frame.method==='plan/review'?'plan-review':'approval'}]));
 return <>{s.error&&<div className="augmentor-extension" role="status">{s.error}<Button disabled={s.busy} onClick={()=>void props.profile.load()}>Refresh Metafolders</Button></div>}<fieldset disabled={s.busy} style={{display:'contents',border:0,padding:0,margin:0}}><Browser wide={props.wide} t={props.t} useSessions={useSessions} useWorkspaces={useWorkspaces} useSessionPendingInteraction={select=>select(pending)} searchSessions={props.searchSessions} searchResultLimit={100} expandSidebar={()=>props.layout.actions.toggleSidebar()}/></fieldset></>;
}
