// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import React,{useEffect,useMemo,useState,useSyncExternalStore} from 'react';
import {createSnapshotStore} from '@deepseek-ai/dsh-client-store';
import {fileAddressFor,parseFileAddress,pathPartsOf,sessionFileAddress} from '@deepseek-ai/dsh-util-workspace-path';
import {RightbarSeat} from '@dsh-gui/ui-sidebar-right/src/client/shell/SidebarRight.tsx';
import {ExpandButton} from '@dsh-gui/ui-sidebar-right/src/client/shell/ExpandButton.tsx';
import {createSidebarRightStore} from '@dsh-gui/ui-sidebar-right/src/client/stores.ts';
import {SidebarRightTabRegistry} from '@dsh-gui/ui-sidebar-right/src/client/tab-registry.ts';
import {TabDomain} from '@dsh-gui/ui-sidebar-right/src/client/tab-domain.ts';
import {tabInfoFactory} from '@dsh-gui/ui-sidebar-right/src/client/tab-info.ts';
import {pageAddress} from '@dsh-gui/ui-sidebar-right/src/client/contract/seed.ts';
import {GuideBody} from '@dsh-gui/ui-sidebar-right/src/client/tabs/guide/GuideBody.tsx';
import {GuideTitle} from '@dsh-gui/ui-sidebar-right/src/client/tabs/guide/GuideTitle.tsx';
import {en as rightEn} from '@dsh-gui/ui-sidebar-right/src/client/locales.ts';
import {TextPreview} from '@dsh-gui/ui-sidebar-documentpreview/src/client/TextPreview.tsx';
import {TextTitle} from '@dsh-gui/ui-sidebar-documentpreview/src/client/TextTitle.tsx';
import {createTextStore} from '@dsh-gui/ui-sidebar-documentpreview/src/client/store.ts';
import {textFace} from '@dsh-gui/ui-sidebar-documentpreview/src/client/face.ts';
import {TextBody} from '@dsh-gui/ui-sidebar-documentpreview/src/client/text/TextBody.tsx';
import {CodeBody} from '@dsh-gui/ui-sidebar-documentpreview/src/client/code/CodeBody.tsx';
import {MarkdownBody} from '@dsh-gui/ui-sidebar-documentpreview/src/client/markdown/MarkdownBody.tsx';
import {ImageBody} from '@dsh-gui/ui-sidebar-documentpreview/src/client/image/ImageBody.tsx';
import {createZoomStore} from '@dsh-gui/ui-sidebar-documentpreview/src/client/zoom/store.ts';
import {en as textEn} from '@dsh-gui/ui-sidebar-documentpreview/src/client/locales.ts';
import {en as codeEn} from '@dsh-gui/ui-sidebar-documentpreview/src/client/code/locales.ts';
import {en as markdownEn} from '@dsh-gui/ui-sidebar-documentpreview/src/client/markdown/locales.ts';
import {en as imageEn} from '@dsh-gui/ui-sidebar-documentpreview/src/client/image/locales.ts';
import {parseGfm} from '@dsh-gui/ui-primitives/src/markdown/parse.ts';
import {en as commonEn} from '@dsh-gui/locale/src/locales/en.ts';
const tr=map=>(key,args={})=>String(map[key]??commonEn[key]??key).replace(/\{(\w+)\}/g,(_,k)=>String(args[k]??''));
const bind=store=>(selector=x=>x)=>selector(useSyncExternalStore(store.subscribe,store.getSnapshot));
const staticHook=value=>(selector=x=>x)=>selector(value);
const errorResult=error=>({ok:false,error:{code:error.code??'gateway/internal',message:error.message,details:error.details??{}}});
const PLAIN='@deepseek-ai/dsh-client-ui-sidebar-documentpreview/text';
const definitions=[{id:'image',extensions:['png','jpg','jpeg','gif','webp','bmp','ico','svg'],binaryExtensions:['png','jpg','jpeg','gif','webp','bmp','ico','svg'],priority:'builtin',title:()=>imageEn.title,loading:'bytes-complete'},
 {id:'markdown',extensions:['md','markdown','mdx'],priority:'builtin',title:()=>markdownEn['viewer.label'],loading:'text-pages'},
 {id:'code',extensions:['js','jsx','ts','tsx','json','jsonc','py','css','scss','html','xml','yaml','yml','toml','sh','bash','c','cpp','h','rs','go','java','sql','ini','conf','txt'],priority:'builtin',title:()=>codeEn.title,loading:'text-pages',wrap:true},
 {id:PLAIN,extensions:[],priority:'builtin',title:()=>textEn['viewer.text'],loading:'text-pages',wrap:true}];
/** Presentation/IO adapter behind the original sidebar, store and readers.
 * No DSH owner, SDK lifecycle, filesystem mutation or model-facing content. */
export class DshFilePreviews {
 constructor(controller,layout){
  this.controller=controller;this.layout=layout;this.resources=new Map();this.sidebarHandle=createSidebarRightStore(()=>({kind:'guide',title:rightEn['tab.guide.title']}));this.sidebars=new Map();this.sidebar=this.sidebarHandle.create();this.text=createTextStore().create();this.zoom=createZoomStore().create();this.generation=createSnapshotStore(0);this.domain=this.newDomain();
  this.registry=new SidebarRightTabRegistry({effect:setup=>setup()});this.slots=new Map();this.baseTypes=[{id:'guide',kind:'guide',title:()=>rightEn['tab.guide.title']},{id:'text',kind:'text',title:address=>pathPartsOf(parseFileAddress(address)?.path??address).name}].map(def=>this.registry.register(def));this.useSidebar=bind(this.sidebar);this.useText=bind(this.text);this.useZoom=bind(this.zoom);this.useTypes=(selector=x=>x)=>{const types=useSyncExternalStore(fn=>this.registry.subscribe(fn),()=>this.registry.entries());return selector(types.filter(x=>x.kind!=='text'||this.fileEnabled()));};this.useGuideEntries=(selector=x=>x)=>selector(useSyncExternalStore(fn=>this.registry.subscribe(fn),()=>this.registry.guide()));this.canSplit=()=>true;this.autoFullscreen=false;
  this.face=textFace((sid,path,offset,signal)=>this.rpc('workspaceFiles.read',{sessionId:sid,path,range:{offset}},signal), (file,signal)=>this.readAll(file,signal),{source:address=>this.source(address)})(null,this.text.actions);
  this.unsubSidebar=this.sidebar.subscribe(()=>this.reconcile());this.unsubController=controller.subscribe(()=>this.sync());this.timer=setInterval(()=>{if(this.enabled())for(const [address,seat] of this.resources)if(seat.held)this.refresh(address,seat);},3000);
 }
 enabled(){const s=this.controller.state;return s.phase==='ready'&&!s.readOnly&&s.sessionId&&s.sessions.some(x=>x.sessionId===s.sessionId);}
 fileEnabled(){return this.enabled()&&this.controller.state.sessions.find(x=>x.sessionId===this.controller.state.sessionId)?.agentPreset!=='augmentor-browser-pi';}
 fileValid(sid,epoch=this.controller.epoch){return this.fileEnabled()&&this.valid(sid,epoch);}
 valid(sid,epoch=this.controller.epoch){return this.enabled()&&this.controller.state.sessionId===sid&&this.controller.epoch===epoch;}
 newDomain(){return new TabDomain({openResourceIn:(sid,address,p)=>this.openAddress(sid,address,p),openTabIn:(sid,kind,p)=>this.openTab(sid,kind,p),closeIn:(sid,id)=>this.sidebar.actions.closeTab(sid,id)},(address,signal)=>this.pin(address,signal));}
 reconcile(){for(const [sid,seat] of Object.entries(this.sidebar.getSnapshot().bySession))this.domain.sync(sid,seat.layout);}
 sync(){const key=this.controller.epoch+':'+this.controller.state.sessionId+':'+this.controller.state.readOnly+':'+this.controller.state.phase;if(key===this.scope)return;this.scope=key;this.domain.dispose();for(const seat of this.resources.values()){seat.abort?.abort();seat.store.set({status:'none'});}this.resources.clear();for(const id of Object.keys(this.text.getSnapshot().byTab))this.text.actions.forget(id);for(const id of Object.keys(this.zoom.getSnapshot().byTab))this.zoom.actions.forget(id);this.unsubSidebar();const sid=this.controller.state.sessionId;if(this.enabled()){if(!this.sidebars.has(sid))this.sidebars.set(sid,this.sidebarHandle.create(sid));this.sidebar=this.sidebars.get(sid);this.sidebar.actions.open(sid);}else this.sidebar=this.sidebarHandle.create();this.useSidebar=bind(this.sidebar);this.domain=this.newDomain();this.unsubSidebar=this.sidebar.subscribe(()=>this.reconcile());this.layout.actions.closeRightbar();this.generation.set(this.generation.getSnapshot()+1);if(this.enabled())this.reconcile();}
 source(address){if(!this.resources.has(address))this.resources.set(address,{store:createSnapshotStore({status:'none'}),held:0,pending:false});return this.resources.get(address).store;}
 pin(address,signal){const file=parseFileAddress(address);if(file?.scope!=='session'||!this.fileValid(file.sessionId)||signal.aborted)return;this.source(address);const seat=this.resources.get(address);seat.held++;void this.refresh(address,seat);signal.addEventListener('abort',()=>{seat.held--;if(!seat.held){seat.abort?.abort();seat.store.set({status:'none'});this.resources.delete(address);}},{once:true});}
 async refresh(address,seat){if(seat.pending||!seat.held)return;const file=parseFileAddress(address),epoch=this.controller.epoch;if(!this.fileValid(file?.sessionId))return;seat.pending=true;const abort=new AbortController();seat.abort=abort;try{const result=await this.rpc('workspaceFiles.stat',{sessionId:file.sessionId,path:file.path},abort.signal);if(this.fileValid(file.sessionId,epoch)&&!abort.signal.aborted&&this.resources.get(address)===seat)seat.store.set(result.ok?{status:'live',value:result.value}:{status:'failed',failure:result.error});}finally{seat.pending=false;}}
 async rpc(method,p,signal){const epoch=this.controller.epoch;if(!this.fileValid(p.sessionId)||signal?.aborted)return errorResult(Error('Preview authority changed.'));try{const result=await this.controller.rpc(method,p,signal);if(!this.fileValid(p.sessionId,epoch)||signal?.aborted)return errorResult(Error('Preview authority changed.'));return result;}catch(error){return errorResult(error);}}
 async readAll(file,signal,baseFile){const epoch=this.controller.epoch;if(!this.fileValid(file.sessionId)||signal.aborted)return errorResult(Error('Preview authority changed.'));try{const q=new URLSearchParams({sessionId:file.sessionId,path:file.path,...(baseFile?{baseFile}:{})}),response=await this.controller.fetcher('/api/preview/bytes?'+q,{headers:{Authorization:'Bearer '+this.controller.token},signal});if(!response.ok){const e=(await response.json()).error;return {ok:false,error:{code:e.code??'gateway/internal',message:e.message,details:e.details??{}}};}const meta=JSON.parse(atob(response.headers.get('X-Augmentor-Preview')??'')),data=new Uint8Array(await response.arrayBuffer());if(!this.fileValid(file.sessionId,epoch)||signal.aborted||!Number.isSafeInteger(meta.bytes)||meta.bytes<0||data.length!==meta.bytes||meta.eof!==true||meta.offset!==0||typeof meta.absolutePath!=='string'||!meta.absolutePath||typeof meta.version!=='string'||!/^[a-f0-9]{64}$/.test(meta.version)||data.length>20*1024*1024)throw Error('Preview bytes are unavailable or incomplete.');return {ok:true,value:{...meta,data}};}catch(error){return errorResult(error);}}
 open(path,options={}){if(!this.fileEnabled()||typeof path!=='string')return false;const s=this.controller.state,row=s.sessions.find(x=>x.sessionId===s.sessionId);return this.openAddress(s.sessionId,fileAddressFor(s.sessionId,row?.cwd,path),options);}
 openAddress(sid,address,options={}){if(!this.fileValid(sid))return false;const file=parseFileAddress(address);if(!file||file.scope==='session'&&file.sessionId!==sid)return false;if(file.scope==='absolute')address=sessionFileAddress(sid,file.path);this.sidebar.actions.openContent(sid,{kind:'text',contentId:address,title:pathPartsOf(file.path).name,...options},id=>this.domain.navigate(sid,id,{address,params:options.params}));return true;}
 openTab(sid,kind,options={}){const definition=this.registry.get(kind);if(!this.valid(sid)||!definition||kind==='text')return false;const address=pageAddress(kind);this.sidebar.actions.openContent(sid,{kind,contentId:address,title:definition.title(address),...options},id=>this.domain.navigate(sid,id,{address,params:options.params}));return true;}
 syncPresentation=p=>p.shown?this.layout.actions.openRightbar(p.track,p.fullscreen):this.layout.actions.closeRightbar();
 measureRoom=fn=>{this.canSplit=fn;};reportAutoFullscreen=value=>{this.autoFullscreen=value;};
 useNavigation=key=>{const source=this.domain.occurrence(this.controller.state.sessionId,{id:key}).navigation;return useSyncExternalStore(source.subscribe,source.getSnapshot);};
 useResource=address=>{const source=this.source(address);return useSyncExternalStore(source.subscribe,source.getSnapshot);};
 dispose(){clearInterval(this.timer);this.unsubSidebar();this.unsubController();this.domain.dispose();for(const seat of this.resources.values()){seat.abort?.abort();seat.store.set({status:'none'});}this.resources.clear();this.pluginDispose?.();for(const release of this.baseTypes)release();}
}
export function DshPreviewExpand({previews,state}){useSyncExternalStore(previews.generation.subscribe,previews.generation.getSnapshot);if(!previews.enabled())return null;return <ExpandButton sessionId={state.sessionId} useStore={previews.useSidebar} actions={previews.sidebar.actions} t={tr(rightEn)} useShortcuts={staticHook([])}/>;}
export function DshPreviewSidebar({previews,state,...geometry}){
 const epoch=useSyncExternalStore(previews.generation.subscribe,previews.generation.getSnapshot);if(!previews.enabled())return null;return <PreviewSeat key={state.sessionId+':'+epoch} previews={previews} state={state} {...geometry}/>;
}
function PreviewSeat({previews:p,state,...geometry}){
 const sid=state.sessionId;
 const render=(name,owner,opts={})=>{const useTabInfo=opts.hookContext?tabInfoFactory({sessionId:sid},opts.hookContext):null;const registered=p.slots.get(name+'::'+opts.entryKey);if(registered){const Component=registered;return <Component sessionId={sid} state={state} controller={p.controller} useTabInfo={useTabInfo} scrollScope={'sidebar:'+p.controller.epoch+':'+sid+':'+opts.hookContext.tabId}/>;}
  if(name==='sidebar.right.pane.tab.title')return opts.entryKey==='text'?<TextTitle useTabInfo={useTabInfo}/>:opts.entryKey==='guide'?<GuideTitle useTabInfo={useTabInfo}/>:opts.fallback??null;
  if(name==='sidebar.right.pane.tab'&&opts.entryKey==='guide')return <GuideBody useTabInfo={useTabInfo} useGuideEntries={p.useGuideEntries} useShortcuts={staticHook([])} renderSlot={render} renderSlotChain={(_n,_o,x)=>x.fallback}/>;
  if(name==='sidebar.right.pane.tab'&&opts.entryKey==='text'&&p.fileEnabled())return <TextPreview useTabInfo={useTabInfo} useResource={p.useResource} useStore={p.useText} actions={p.text.actions} {...p.face} useDocumentPreviews={staticHook(definitions)} renderSlot={(n,o,x)=>documentRender(p,useTabInfo,n,o,x)} t={tr(textEn)}/>;
  return opts.fallback??null;
 };
 return <RightbarSeat {...geometry} sessionId={sid} active={state.phase==='ready'&&!state.readOnly&&p.layout.getSnapshot().panelInfo.activePanelId===null} retainTab={(_id,signal)=>()=>{}} useStore={p.useSidebar} actions={p.sidebar.actions} renderSlot={render} t={tr(rightEn)} syncPresentation={p.syncPresentation} measureRoom={p.measureRoom} reportAutoFullscreen={p.reportAutoFullscreen} openTab={(kind,opts)=>p.openTab(sid,kind,opts)} closeTab={id=>p.sidebar.actions.closeTab(sid,id)} splitPane={id=>{if(p.canSplit(id))p.sidebar.actions.splitPane(sid,id);}} toggleFullscreen={()=>p.autoFullscreen?p.sidebar.actions.setExpanded(sid,false):p.sidebar.actions.setMode(sid,p.sidebar.getSnapshot().bySession[sid].layout.mode==='fullscreen'?'push':'fullscreen')} useTabTypes={p.useTypes} useTabNavigation={p.useNavigation} occurrence={tab=>p.domain.occurrence(sid,tab)} useShortcuts={staticHook([])}/>;
}
function documentRender(p,useTabInfo,name,owner,opts={}){
 if(name!=='sidebar.right.tab.document')return null;
 const props={...owner,useTabInfo,useResource:p.useResource};
 if(opts.entryKey===PLAIN)return <TextBody {...props}/>;
 if(opts.entryKey==='code')return <CodeBody {...props} t={tr(codeEn)}/>;
 if(opts.entryKey==='markdown')return <LocalMarkdown {...props} previews={p} t={tr(markdownEn)}/>;
 if(opts.entryKey==='image')return <ImageBody {...props} useStore={p.useZoom} actions={p.zoom.actions} retainTab={(id,signal)=>{signal.addEventListener('abort',()=>p.zoom.actions.forget(id),{once:true});}} t={tr(imageEn)}/>;
 return opts.fallback??null;
}
function LocalMarkdown({previews:p,...props}){
 const [urls,setUrls]=useState(new Map()),{tab}=props.useTabInfo(),file=parseFileAddress(props.resourceAddress),text=props.content.kind==='text'?props.content.text:'';
 useEffect(()=>{const abort=new AbortController(),signal=AbortSignal.any([abort.signal,tab.signal]),kept=new Map(),root=parseGfm(text),definitions=new Map();const walk=(node,fn)=>{fn(node);for(const c of node.children??[])walk(c,fn);};walk(root,n=>{if(n.type==='definition')definitions.set(n.identifier.toUpperCase(),n.url);});const targets=new Set();walk(root,n=>{const value=n.type==='image'?n.url:n.type==='imageReference'?definitions.get(n.identifier.toUpperCase()):null;if(typeof value==='string'&&targets.size<20&&!value.startsWith('//')&&!/^[a-z][a-z\d+.-]*:/i.test(value))targets.add(value);});setUrls(new Map());void(async()=>{let remaining=20*1024*1024;for(const value of targets){if(signal.aborted)break;let path;try{path=decodeURIComponent(value.split(/[?#]/)[0]);}catch{continue;}const extension=path.split('.').at(-1).toLowerCase(),types={png:'image/png',jpg:'image/jpeg',jpeg:'image/jpeg',gif:'image/gif',webp:'image/webp',svg:'image/svg+xml',bmp:'image/bmp',ico:'image/x-icon'};if(!types[extension])continue;const stat=await p.rpc('workspaceFiles.stat',{sessionId:file.sessionId,path,baseFile:file.path},signal);if(!stat.ok||!Number.isSafeInteger(stat.value.bytes)||stat.value.bytes<0||stat.value.bytes>remaining)continue;const result=await p.readAll({sessionId:file.sessionId,path},signal,file.path);if(!result.ok||signal.aborted||result.value.data.length>remaining)continue;remaining-=result.value.data.length;const address=fileAddressFor(file.sessionId,undefined,result.value.absolutePath);p.pin(address,signal);props.addResource(address);kept.set(value,URL.createObjectURL(new Blob([result.value.data],{type:types[extension]})));setUrls(new Map(kept));}})();return()=>{abort.abort();for(const url of kept.values())URL.revokeObjectURL(url);};},[text,file.sessionId,file.path,tab.signal,p]);
 const images=useMemo(()=>({allowRemote:false,resolve:value=>urls.get(value)}),[urls]);return <MarkdownBody {...props} images={images}/>;
}
