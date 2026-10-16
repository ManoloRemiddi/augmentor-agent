// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {bindContextSidebar} from './dsh-context-sidebar.jsx';
import {OriginalDictation,bindDictation} from './dsh-dictation.jsx';
import {dictationInsertion} from './dsh-dictation.mjs';
import {DshFilePreviews,DshPreviewSidebar,DshPreviewExpand} from './dsh-file-preview.jsx';
import React,{useEffect,useLayoutEffect,useMemo,useRef,useState,useSyncExternalStore} from 'react';
import {createRoot} from 'react-dom/client';
import {createEditor,$getRoot,$createParagraphNode,$createTextNode,$getSelection,$isRangeSelection,$getNearestNodeFromDOMNode} from 'lexical';
import {registerPlainText} from '@lexical/plain-text';
import {registerHistory,createEmptyHistoryState} from '@lexical/history';
import {AppFrame} from '@dsh-gui/ui-layout/src/client/AppFrame.tsx';
import {SidebarRoot} from '@dsh-gui/ui-sidebar/src/client/SidebarRoot.tsx';
import sidebarCss from '@dsh-gui/ui-sidebar/src/client/SidebarRoot.module.css';
import {ConversationRoot} from '@dsh-gui/ui-conversation/src/client/skeleton/ConversationRoot.tsx';
import {ConversationContent} from '@dsh-gui/ui-conversation/src/client/skeleton/ConversationContent.tsx';
import {ConversationHeader} from '@dsh-gui/ui-conversation/src/client/skeleton/ConversationHeader.tsx';
import {ConversationSessionHeader,ConversationSession} from '@dsh-gui/ui-conversation/src/client/skeleton/ConversationSession.tsx';
import {InputBar} from '@dsh-gui/ui-conversation/src/client/skeleton/InputBar.tsx';
import {MenuView} from '@dsh-gui/ui-input-trigger/src/client/MenuView.tsx';
import {InputTriggerController} from '@dsh-gui/ui-input-trigger/src/client/controller.ts';
import {PopupSelectView} from '@dsh-gui/ui-commands/src/client/PopupSelectView.tsx';
import {PopupSelectController} from '@dsh-gui/ui-commands/src/client/popup.ts';
import {builtinRowFace,sectionRows} from '@dsh-gui/ui-commands/src/client/presentation.ts';
import {en as commandEn} from '@dsh-gui/ui-commands/src/client/locales.ts';
import {en as menuEn} from '@dsh-gui/ui-input-trigger/src/client/locales.ts';
import {$projectComposer} from '@dsh-gui/ui-conversation/src/client/input/editor/projection.ts';
import {$replaceDetectSpanWithNodes,$replaceDetectSpanWithText} from '@dsh-gui/ui-conversation/src/client/input/editor/span-map.ts';
import {fileReferenceSource} from './dsh-file-references.mjs';
import {fileCandidate,crumbsFor,parseCandidate} from '@dsh-gui/ui-reference/src/client/index.ts';
import {en as referenceEn} from '@dsh-gui/ui-reference/src/client/locales.ts';
import {ReferenceChipNode,$createReferenceChipNode} from '@dsh-gui/ui-conversation/src/client/input/editor/chip-node.tsx';
import {TextRefNode,registerTextRefDecoration,rescanTextRefs} from '@dsh-gui/ui-conversation/src/client/input/editor/text-ref.ts';
import {registerReferenceActivation} from '@dsh-gui/ui-conversation/src/client/input/editor/reference-activation.ts';
import {DshCommandMenu} from './dsh-command-menu.mjs';
import {SessionLogDownloadController,downloadUrl} from './vendor/dsh/packages/session-query/session-log-export/src/client/controller.ts';
import {SessionLogDownloadHeaderAction} from './vendor/dsh/packages/session-query/session-log-export/src/client/HeaderAction.tsx';
import {en as exportEn} from './vendor/dsh/packages/session-query/session-log-export/src/client/locales.ts';
import {DshSessionExport} from './dsh-session-export.mjs';
import {ModelSelect} from '@dsh-gui/ui-model-selection/src/client/ModelSelect.tsx';
import {ChatView} from '@dsh-gui/ui-chat/src/client/chat/ChatView.tsx';
import {ChatFlow} from '@dsh-gui/ui-chat/src/client/chat/ChatFlow.tsx';
import {UserMessageNodeView,TurnErrorNodeView,CompactionNodeView} from '@dsh-gui/ui-chat/src/client/chat/MessageItem.tsx';
import {AssistantNodeView} from '@dsh-gui/ui-chat/src/client/chat/AssistantNodeView.tsx';
import {ApprovalPanel} from '@dsh-gui/ui-approval/src/client/ApprovalPanel.tsx';
import {QuestionComposer} from '@dsh-gui/ui-user-questions/src/client/QuestionComposer.tsx';
import {createQuestionDraftStore} from '@dsh-gui/ui-user-questions/src/client/draft-store.ts';
import {syncQuestionDrafts} from './dsh-question-drafts.mjs';
import {en as approvalEn} from '@dsh-gui/ui-approval/src/client/locales.ts';
import {en as questionEn} from '@dsh-gui/ui-user-questions/src/client/locales.ts';
import {readDshPayload} from './dsh-payload.mjs';
import {attachNativeHistory} from './native-history.mjs';
import {MessageIconActions} from '@dsh-gui/ui-chat/src/client/chat/MessageIconActions.tsx';
import {messageTargets} from './chat-projection.js';
import {DshShortcuts} from './dsh-shortcuts.jsx';
import {en as layoutShortcutEn} from '@dsh-gui/ui-layout/src/client/shortcut-locales.ts';
import {en as sidebarRightEn} from '@dsh-gui/ui-sidebar-right/src/client/locales.ts';
import {en as settingsEn} from '@dsh-gui/ui-settings-general/src/client/locales.ts';
import {OriginalSettings,settingsShell,connectAppearance} from './dsh-settings.jsx';
import {TrajectoryView} from '@dsh-gui/ui-trajectory/src/client/TrajectoryView.tsx';
import {WorkspaceBrowser} from '@dsh-gui/ui-workspace/src/client/rows/WorkspaceBrowser.tsx';
import {PinSessionMenuItem,PinSessionRowButton} from '@dsh-gui/ui-workspace/src/client/session-actions/PinSession.tsx';
import {ArchiveSessionMenuItem,ArchiveSessionRowButton,SessionArchiveConfirmDialog} from '@dsh-gui/ui-workspace/src/client/session-actions/ArchiveSession.tsx';
import {ForkSessionMenuItem} from '@dsh-gui/ui-workspace/src/client/session-actions/ForkSession.tsx';
import {RenameSessionMenuItem,SessionRenameDialog} from '@dsh-gui/ui-workspace/src/client/session-actions/RenameSession.tsx';
import {RowActionToast} from '@dsh-gui/ui-workspace/src/client/session-actions/RowActionToast.tsx';
import {pinOrderSource,pinOrderAccounts} from '@dsh-gui/ui-workspace/src/client/pin-order.ts';
import {QueueDock} from '@dsh-gui/ui-conversation/src/client/queue/QueueDock.tsx';
import {GoalBar} from '@dsh-gui/ui-goal/src/client/GoalBar.tsx';
import {DirectoryBrowser} from '@dsh-gui/ui-directory-picker-browse/src/client/DirectoryBrowser.tsx';
import {WorkspacePicker} from '@dsh-gui/ui-workspace/src/client/WorkspacePicker.tsx';
import {createLayoutStore} from '@dsh-gui/ui-layout/src/client/stores.ts';
import {createWorkspaceViewStore} from '@dsh-gui/ui-workspace/src/client/stores.ts';
import {createWorkspaceShortcutControls} from '@dsh-gui/ui-workspace/src/client/shortcuts.ts';
import {createTrajectoryDurationStore} from '@dsh-gui/ui-trajectory/src/client/duration-store.ts';
import {createTrajectoryStringWrappingStore} from '@dsh-gui/ui-trajectory/src/client/string-wrapping-store.ts';
import {createSnapshotStore} from '@deepseek-ai/dsh-client-store';
import {Button,Modal,Input,IconEditOutlineRegular,IconCopyOutlineRegular,IconGoalOutlineRegular,IconFolderCloseRegular,JsonBlock as OriginalJsonBlock,MarkdownText,DisclosureRow,StateDot} from '@deepseek-ai/dsh-client-ui-primitives';
import {en as commonEn} from '@dsh-gui/locale/src/locales/en.ts';
import {en as conversationEn} from '@dsh-gui/ui-conversation/src/client/locales.ts';
import {en as sidebarEn} from '@dsh-gui/ui-sidebar/src/client/locales.ts';
import {en as workspaceEn} from '@dsh-gui/ui-workspace/src/client/locales.ts';
import {en as chatEn} from '@dsh-gui/ui-chat/src/client/locale.ts';
import {en as trajectoryEn} from '@dsh-gui/ui-trajectory/src/client/locales.ts';
import {en as modelEn} from '@dsh-gui/ui-model-selection/src/client/locales.ts';
import {en as goalEn} from '@dsh-gui/ui-goal/src/client/locales.ts';
import {DshAttachments} from './dsh-attachments.mjs';
import {bindPlanReview,PlanModeControl} from './dsh-plan-review.jsx';
import {CurrentPermissionControl,permissionT} from './dsh-permission-control.jsx';
import {bindOriginalSkillSource,openCurrentSkill} from './dsh-skills.mjs';
import {apply as applyOriginalSkills} from '@dsh-gui/ui-skill/src/client/index.ts';
import {en as skillEn} from '@dsh-gui/ui-skill/src/client/locales.ts';
import {DshDrafts} from './dsh-drafts.mjs';
import {ComposerAttachments} from '@dsh-gui/ui-attachment/src/client/ComposerAttachments.tsx';
import {MessageImages} from '@dsh-gui/ui-attachment/src/client/MessageImages.tsx';
import {DshPiController} from './dsh-pi-controller.mjs';
import {projectDsh} from './dsh-pi-projection.mjs';
import {DshContextDashboard,DshContextFleet,DshContextOverlay,createDshContextModalBinding,bindContextNavigation} from './dsh-context.jsx';
import {DshContextInsights} from './dsh-insights.jsx';
import {DshContextPreferences} from './dsh-context-preferences.mjs';
import {DshDeveloperTools} from './dsh-developer-tools.mjs';
import {DeveloperToolsPreference} from '@dsh-gui/ui-settings/src/client/developer-tools.ts';
import {contextSettings} from './dsh-context-settings.jsx';
import {InsightPanelIcon} from './vendor/dsh-context/src/client/icon.tsx';
import {attachPlans} from './plans.js';
import {attachGoals} from './goals.js';
import {attachJobs} from './jobs.js';
import {PromptLibraryContent} from './dsh-prompt-library.jsx';
import {AugmentorBrand} from './augmentor-brand.jsx';
import {DshMetafolderProfile} from './dsh-metafolder-profile.mjs';
import {MetafolderSidebar} from './dsh-metafolder.jsx';
import './dsh-base.css';

const hash=new URLSearchParams(location.hash.slice(1));
const token=hash.get('token')||sessionStorage.getItem('augmentor-harness-token');
if(token)sessionStorage.setItem('augmentor-harness-token',token);
history.replaceState(null,'',location.pathname);
// A fresh private link can arrive as same-document navigation. Reinitialize
// the controller so a scoped inspector never retains the previous authority.
addEventListener('hashchange',()=>{if(new URLSearchParams(location.hash.slice(1)).has('token'))location.reload();});
const controller=new DshPiController(token);
bindDictation(controller);
const appearanceProfile=connectAppearance(controller);
const metafolders=new DshMetafolderProfile(controller);
const developerTools=new DshDeveloperTools(controller);developerTools.preference=new DeveloperToolsPreference(developerTools);
const contextPreferences=new DshContextPreferences(controller);contextSettings.attach(contextPreferences);
const contextModal=createDshContextModalBinding(controller);
const layout=createLayoutStore().create(),workspaceView=createWorkspaceViewStore().create();
const filePreviews=new DshFilePreviews(controller,layout,developerTools);bindContextNavigation(filePreviews);
const planReviews=bindPlanReview(filePreviews);
const contextTab=bindContextSidebar(filePreviews,contextSettings,DshContextDashboard,DshContextFleet);
const shortcuts=createWorkspaceShortcutControls(),duration=createTrajectoryDurationStore(),wrapping=createTrajectoryStringWrappingStore();
const attachmentDrafts=new DshAttachments(controller);let openFiles=null;
const questionDrafts=new Map();
controller.subscribe(()=>syncQuestionDrafts(questionDrafts,createQuestionDraftStore,controller.state));
const rowNotice=createSnapshotStore(null),archiveRequest=createSnapshotStore(null);let noticeSeq=0;
const draft=createSnapshotStore(''),modelDirectory=createSnapshotStore({current:null,routable:null,groups:[],failures:[],status:'idle',pending:null,error:null});
const noOp=()=>{},selectorFace=value=>(selector=x=>x)=>selector(value);
const bind=source=>(selector=x=>x)=>selector(useSyncExternalStore(source.subscribe,source.getSnapshot));
const sessionExports=new DshSessionExport({Controller:SessionLogDownloadController,controller,save:downloadUrl});
const useSessionLogDownload=bind(sessionExports.store);
window.addEventListener('pagehide',()=>void sessionExports.dispose(),{once:true});
const useLayout=bind(layout),useWorkspaceView=bind(workspaceView),useWorkspaceShortcuts=bind(shortcuts.state),useDuration=bind(duration),useDraft=bind(draft);
const useRowNotice=bind(rowNotice),useArchiveRequest=bind(archiveRequest);
const notifyRow=(kind,extra={})=>rowNotice.set({kind,...extra,seq:++noticeSeq});
const tr=dictionary=>(key,args={})=>String(dictionary[key]??commonEn[key]??key).replace(/\{(\w+)\}/g,(_,name)=>String(args[name]??''));
const t={conversation:tr({...conversationEn,'hero.headline':'Build with Augmentor','error.sessionInUse':'This conversation is already open in another Harness instance. Close that instance and try again.'}),sidebar:tr(sidebarEn),workspace:tr(workspaceEn),chat:tr({...chatEn,'chat.deepDiving':'Working','chat.deepDivingFor':'Working for {duration} ···'}),trajectory:tr(trajectoryEn),model:tr(modelEn),goal:tr(goalEn),approval:tr(approvalEn),question:tr(questionEn),common:tr(commonEn),command:tr(commandEn),menu:tr(menuEn)};
const settingsNotice=text=>controller.update({error:text});
const harnessShortcuts=new DshShortcuts(controller,{previews:filePreviews,layout,workspaceControls:shortcuts,settingsShell,dictionaries:{workspace:workspaceEn,sidebarRight:sidebarRightEn,settings:settingsEn,layout:layoutShortcutEn}});filePreviews.useShortcuts=harnessShortcuts.useCatalog;
const control={run:async action=>{try{return await action();}catch(error){if(!error.presentedByBranch&&!error.presentedByCreate)controller.update({error:error.message});return undefined;}}};
let activeDraft=null;
let draftRev=0,composerProjection={detectText:'',clipboardText:'',occurrences:[],selection:null,caret:null},commandMenu;const occurrenceIds=new Map();let nextOccurrenceId=0;
const forkLast=sid=>{const revision=draftRev;return control.run(()=>controller.forkLast(sid,()=>draftRev===revision));};
const references=()=>composerProjection.occurrences.map(({occurrenceId,...ref})=>ref);
const editor=createEditor({namespace:'augmentor-dsh-composer',nodes:[ReferenceChipNode,TextRefNode],onError:error=>controller.update({error:error.message}),theme:{}});
registerPlainText(editor);registerHistory(editor,createEmptyHistoryState(),300);
registerTextRefDecoration(editor,()=>commandMenu?.lexicon.getSnapshot()??new Map(),()=>null);
registerReferenceActivation(editor,(source,reference)=>commandMenu?.openReference(source,reference)===true);
editor.registerUpdateListener(({editorState})=>editorState.read(()=>{const previous=composerProjection;composerProjection=$projectComposer(key=>{if(!occurrenceIds.has(key))occurrenceIds.set(key,++nextOccurrenceId);return occurrenceIds.get(key);});const value=composerProjection.clipboardText;if(value!==draft.getSnapshot()||previous.detectText!==composerProjection.detectText||JSON.stringify(previous.occurrences)!==JSON.stringify(composerProjection.occurrences))draftRev++;draft.set(value);if(activeDraft)draftArchive.edit(value,references());commandMenu?.track();}));
function setDraft(value){const text=typeof value==='string'?value:value.text,refs=typeof value==='string'?[]:value.references??[];editor.update(()=>{const paragraph=$createParagraphNode();let offset=0;for(const ref of refs){if(ref.offset>offset)paragraph.append($createTextNode(text.slice(offset,ref.offset)));const chip=$createReferenceChipNode(ref);if(ref.invalid)chip.setInvalid(true);paragraph.append(chip);offset=ref.offset+ref.length;}if(offset<text.length)paragraph.append($createTextNode(text.slice(offset)));$getRoot().clear().append(paragraph);},{discrete:true});}
const draftArchive=new DshDrafts(controller,{restore:(sid,text,references)=>{activeDraft=sid;setDraft({text,references});},attachments:attachmentDrafts});
const dictationActions=dictationInsertion({scope:()=>JSON.stringify([activeDraft,controller.epoch]),revision:()=>draftRev,span:()=>composerProjection.selection||{start:composerProjection.detectText.length,end:composerProjection.detectText.length},replace:(span,text)=>{let applied=false;editor.update(()=>{applied=$replaceDetectSpanWithText(span,text);},{discrete:true});return applied;}});
const commandRows=[
  {name:'file',label:t.conversation('input.file'),description:'Attach files to this draft',icon:IconFolderCloseRegular},
  {name:'goal',...builtinRowFace({definitionId:'@deepseek-ai/dsh-command-goal'},t.command)},
  {name:'plan',...builtinRowFace({definitionId:'@deepseek-ai/dsh-plan-mode'},t.command),description:'Enter plan mode; use /plan off to leave'},
  {name:'compact',...builtinRowFace({definitionId:'@deepseek-ai/dsh-command-compact'},t.command)},
  {name:'export',...builtinRowFace({definitionId:'@deepseek-ai/dsh-session-log-export'},t.command)},
  {name:'permission',...builtinRowFace({definitionId:'@deepseek-ai/dsh-permission-presets'},t.command),description:'Choose this chat’s approval mode for new actions'},
  {name:'model',label:'Model',description:'Select a model for this conversation'},
  {name:'prompts',label:'Prompt library',description:'Use or edit a saved prompt'},
  {name:'jobs',label:'Jobs',description:'Inspect and manage this conversation’s jobs'},
  {name:'context',label:'Context',description:'Inspect the recorded context dashboard'},
  {name:'inspect',label:'Full Pi record inspector',description:'Open the advanced conversation inspector'},
];
commandMenu=new DshCommandMenu({InputTriggerController,PopupSelectController,store:createSnapshotStore,sectionRows:rows=>sectionRows(rows,t.command),rows:()=>commandRows.filter(row=>(row.name!=='permission'||controller.state.capabilities?.sessionPermissions===true)&&(row.name!=='export'||controller.state.capabilities?.sessionExport===true)).map(row=>row.name==='plan'&&!controller.state.capabilities?.planMode?{...row,description:'View this conversation’s plan and todos'}:row),actions:{},
  permission:{read:scope=>controller.refreshPermission(scope,{explicit:true}),current:()=>controller.state.permission,select:(preset,scope)=>controller.selectPermission(preset,scope),t:permissionT},
  current:()=>({...controller.state,epoch:controller.epoch,running:controller.state.sessions.find(x=>x.sessionId===controller.state.sessionId)?.running===true}),
  ready:()=>draftArchive.getSnapshot().ready,skillSource:scope=>controller.state.capabilities?.skillReferences?bindOriginalSkillSource({apply:applyOriginalSkills,controller,previews:filePreviews,valid:s=>commandMenu.valid(s),scope,dictionary:skillEn}):null,referenceSource:scope=>fileReferenceSource({controller,valid:s=>commandMenu.valid(s),fileCandidate,crumbsFor,parseCandidate,t:tr(referenceEn),openFile:path=>filePreviews.open(path)},scope),
  draft:()=>({text:draft.getSnapshot(),detectText:composerProjection.detectText,rev:draftRev,sessionId:activeDraft,caret:composerProjection.caret}),catalog:()=>controller.state.catalog,choose:selection=>controller.choose(selection),notice:text=>controller.update({error:text}),focus:()=>editor.focus(),
  insertReference:(span,ref,rev,scope)=>{let applied=false;editor.update(()=>{if(draftRev===rev&&activeDraft===scope.sessionId&&controller.epoch===scope.epoch){const tail=composerProjection.detectText.slice(span.end);applied=$replaceDetectSpanWithNodes(span,[$createReferenceChipNode(ref),...(tail.startsWith(' ')?[]:[$createTextNode(' ')])]);}},{discrete:true});return applied;},
  replace:(span,text,rev,scope)=>{let applied=false;editor.update(()=>{if(draftRev===rev&&activeDraft===scope.sessionId&&controller.epoch===scope.epoch)applied=$replaceDetectSpanWithText(span,text);},{discrete:true});return applied;},
});
controller.subscribe(()=>commandMenu.sync());draftArchive.subscribe(()=>commandMenu.sync());
const useLexicon=bind(commandMenu.lexicon),useMenuLauncher=bind(commandMenu.launcher);
commandMenu.lexicon.subscribe(()=>rescanTextRefs(editor));
const keyboard={editor,arbitrate:(key,composing)=>commandMenu.arbitrate(key,composing),space:()=>commandMenu.engine?.onSpace()??false,dismissPopup:()=>commandMenu.popup.dismiss(),bindFilePicker:fn=>{openFiles=fn;return()=>{if(openFiles===fn)openFiles=null;};},caretSpan:()=>composerProjection.selection||{start:composerProjection.detectText.length,end:composerProjection.detectText.length},paste:text=>editor.update(()=>{const selection=$getSelection();if($isRangeSelection(selection))selection.insertText(text);}),submit:mode=>void control.run(async()=>{
  const text=draft.getSnapshot(),sid=controller.state.sessionId,items=[...attachmentDrafts.draft(sid).items],epoch=controller.epoch;if(attachmentDrafts.busy||!text.trim()&&!items.length)return;
  if(await commandMenu.adjudicate(text)!==undefined)return;
  if(sid!==controller.state.sessionId||draft.getSnapshot()!==text)throw Error('The conversation or draft changed; nothing was submitted.');
  attachmentDrafts.busy=true;attachmentDrafts.changed();
  try{const parts=await attachmentDrafts.content(sid,items);if(sid!==controller.state.sessionId)throw Error('The selected conversation changed; the draft is preserved.');const requestId=await draftArchive.prepare(sid,text,mode,parts);if(sid!==controller.state.sessionId||epoch!==controller.epoch)throw Error('The selected conversation changed; no prompt was sent. Inspect the prepared draft before continuing.');await controller.send(text,mode,parts,requestId);await draftArchive.complete(sid,requestId);await controller.refresh();}
  finally{attachmentDrafts.busy=false;attachmentDrafts.changed();}
}),steerQueue:()=>void control.run(async()=>{for(const item of controller.state.queue?.items||[])if(item.canSteer)await controller.rpc('session.updateQueue',{sessionId:controller.state.sessionId,itemId:item.id,expectedTurnId:controller.state.queue.activeTurnId,action:{kind:'steer'}});})};

function useDisclosure(){const [expanded,set]=useState(false);return {expanded,toggle:()=>set(x=>!x)};}
function useGroupAction(){return useRef(null);}
const presentation={mode:'detailed',foldCompletedTurns:false,collapseTiming:'immediate',settledReasoningPreview:true};
const position={read:()=>null,save:noOp};
function OwnedMessage(props){return <AssistantNodeView {...props} useDisclosure={useDisclosure} useTurnData={()=>undefined} useGroupAction={useGroupAction} usePresentation={selectorFace(presentation)} t={t.chat}/>;}
function PiTool({node,onInspect,state}){const [expanded,set]=useState(false),data=node.data,question=controller.questionForTool(data);return <DisclosureRow open={expanded} expandable onToggle={()=>set(x=>!x)} title={data.name} icon={<StateDot state={data.status==='pending'?'ongoing':data.status==='error'?'error':data.status==='finished'?'done':'warning'}/>} headerAccessory={<>{question&&!state.readOnly&&<Button variant="ghost" onClick={()=>void control.run(async()=>controller.revealQuestion(question))}>{t.question('reply.open')}</Button>}<Button variant="ghost" onClick={onInspect}>Inspect</Button></>} children={<><planReviews.Recorded data={data} state={state}/>{expanded&&<><JsonBlock payload={data.call?.arguments??{}} label="Arguments"/><JsonBlock payload={data.result??{status:data.status}} label="Result"/></>}</>}/>;}
const directoryT=tr({'browser.title':'Select Workspace Directory','browser.home':'Home','browser.newFolder':'New folder','browser.folderName':'Folder name','browser.createIn':'New folder in "{name}"','browser.untitledFolder':'Untitled folder','browser.create':'Create','browser.cancel':'Cancel','browser.open':'Open','browser.editPath':'Edit path','browser.loading':'Loading…','browser.truncated':'Too many folders to list; only the beginning is shown.','browser.showHidden':'Show hidden files'});
// Upstream restarts navigation when its listing callback changes. Keep these
// bindings stable while Host polls refresh the surrounding conversation.
const listDshDirectory=path=>controller.rpc('workspace.listDirectory',{path});
const createDshDirectory=async(path,name)=>(await controller.rpc('workspace.createDirectory',{path,name})).path;
function DirectoryFlow(owner){return <DirectoryBrowser {...owner} t={directoryT} listDirectory={listDshDirectory} createDirectory={createDshDirectory} onOpen={owner.onPicked} onClose={owner.onCancel}/>;}

// Bind the copied widget's required copy face; its display cap and layout stay upstream.
const jsonTruncatedLabel=total=>`[Display truncated; ${total} JSON characters retained.]`;
function JsonBlock(props){return <OriginalJsonBlock {...props} truncatedLabel={jsonTruncatedLabel}/>;}
/** Existing Augmentor feature extensions occupy DSH's view slots. */
function ExtensionView({kind,state}){
  const ref=useRef(null),refresh=useRef(noOp),session=useRef(state);session.current=state;
  useEffect(()=>{
    const current=()=>({sessionId:session.current.sessionId,epoch:controller.epoch,readOnly:session.current.readOnly});
    const attach={plan:attachPlans,goal:attachGoals,jobs:attachJobs}[kind];
    const view=attach({container:ref.current,rpc:(method,params)=>controller.rpc(method,params),current});
    refresh.current=()=>view.refresh();
    void view.refresh();
    return()=>{refresh.current=noOp;view.reset();};
  },[kind,state.sessionId]);
  return <div className="augmentor-extension"><Button onClick={()=>void refresh.current()}>Refresh {kind}</Button><div ref={ref}/></div>;
}
function ContextView({state}){
  const requests=state.records.filter(r=>r.kind==='model/request').reverse();const [selected,set]=useState(null),[payload,setPayload]=useState(null),[lineage,setLineage]=useState(null),[payloadError,setPayloadError]=useState(null),[lineageError,setLineageError]=useState(null);
  const request=requests.find(r=>r.id===selected)||requests[0];
  const provenance=state.records.find(r=>r.kind==='context/provenance'&&r.requestId===request?.id),error=payloadError||lineageError;
  // Observation records are immutable, but the matching provenance can arrive
  // on a later event page. Its arrival must not restart the provider-body read.
  useEffect(()=>{
    let live=true;setPayload(null);setPayloadError(null);
    if(request)readDshPayload((m,p)=>controller.rpc(m,p),state.sessionId,request).then(value=>{
      if(live){if(value.available)setPayload(value.value);else setPayloadError(value.reason);}
    },e=>{if(live)setPayloadError(e.message);});
    return()=>{live=false;};
  },[request?.id,state.sessionId]);
  useEffect(()=>{
    let live=true;setLineage(null);setLineageError(null);
    if(provenance)readDshPayload((m,p)=>controller.rpc(m,p),state.sessionId,provenance).then(value=>{
      if(live)setLineage({...value,metadata:provenance.data});
    },e=>{if(live)setLineageError(e.message);});
    return()=>{live=false;};
  },[provenance?.id,request?.id,state.sessionId]);
  return <div className="augmentor-extension"><h2>Context</h2><label>Recorded request <select value={request?.id||''} onChange={e=>set(e.target.value)}>{requests.map(r=><option key={r.id} value={r.id}>{r.data.provider}/{r.data.model} · #{r.seq}</option>)}</select></label>{!request?<p>No provider request has been recorded for this conversation.</p>:<><JsonBlock payload={request.data} label="Request settings"/><JsonBlock payload={request.payload||{available:false}} label="Retained payload identity"/>{error&&<p role="status">{error}</p>}{payload&&<><JsonBlock label="Effective provider request" payload={payload}/><JsonBlock label="Tool declarations" payload={payload.tools||[]}/>{lineage&&<><JsonBlock label="Composition coverage" payload={lineage.metadata}/>{lineage.available?Object.entries(lineage.value.snapshots||{}).map(([name,value])=><JsonBlock key={name} label={name} payload={value}/>):<p role="status">{lineage.reason}</p>}</>}</>}</>}<NativeRecords state={state}/></div>;
}
function NativeRecords({state}){const ref=useRef(null);useEffect(()=>{let live=true;attachNativeHistory(ref.current,{rpc:(m,p)=>controller.rpc(m,p),sessionId:state.sessionId,alive:()=>live,archived:state.capabilities?.archivedDsh===true});return()=>{live=false;ref.current?.replaceChildren();};},[state.sessionId]);return <div ref={ref}/>;}
function PromptLibrary({close,initialTab}){
 const [dirty,setDirty]=useState(false),[confirm,setConfirm]=useState(null);
 const afterEdits=action=>{if(dirty)setConfirm(()=>action);else action();};
 const requestClose=()=>afterEdits(close);
 return <Modal open onClose={requestClose} title="Prompt library" closeLabel="Close" className="augmentor-library-modal" contentClassName="augmentor-library-content"><PromptLibraryContent controller={controller} initialTab={initialTab} onDirtyChange={setDirty} onUse={body=>afterEdits(()=>{setDraft(body);close();})}/>{confirm&&<Modal open onClose={()=>setConfirm(null)} title="Unsaved library changes" closeLabel="Close" description="Discard your unsaved changes and close the library?" footer={<><Button onClick={()=>setConfirm(null)}>Keep editing</Button><Button onClick={()=>confirm()}>Discard changes and close</Button></>}/>}</Modal>;
}


function InteractionTakeover({frame,state}){
  const [,tick]=useState(0);
  useEffect(()=>{if(frame.method!=='question/requested'||frame.payload.wait?.deadline===undefined)return;const timer=setInterval(()=>tick(x=>x+1),1000);return()=>clearInterval(timer);},[frame.rpcId,frame.payload.wait?.deadline]);
  const draft=useMemo(()=>questionDrafts.get(state.sessionId)??syncQuestionDrafts(questionDrafts,createQuestionDraftStore,state),[state.sessionId]);
  function useQuestionDraft(selector=x=>x){return selector(useSyncExternalStore(draft.subscribe,draft.getSnapshot));}
  const pending=useMemo(()=>{
    const epoch=controller.epoch,sessionId=state.sessionId;
    const snapshot=()=>{const current=controller.state.sessionId===sessionId&&controller.epoch===epoch?controller.state.interactions.find(x=>x.rpcId===frame.rpcId):null,wait=current?.payload.wait;
      return {state:'open',waitState:wait?.state||'waiting',countdown:wait?{remainingMs:wait.deadline===undefined?wait.remainingMs:Math.max(0,wait.deadline-Date.now()),running:wait.deadline!==undefined}:undefined,channel:current?'waterfall':'none',closed:!current};};
    const keys=()=>controller.state.interactions.map(x=>x.rpcId);
    const wait=action=>{void controller.questionWait(frame,action).catch(error=>{if(epoch===controller.epoch&&controller.state.interactions.some(x=>x.rpcId===frame.rpcId))controller.update({error:error.message});});};
    return {key:frame.rpcId,kind:'question',sessionId:state.sessionId,toolName:frame.payload.toolName,reason:frame.payload.reason,answerable:true,
      questions:(frame.payload.questions||[]).map((q,i)=>({...q,id:q.id||String(i)})),review:undefined,get dismissal(){return controller.canHideQuestion(frame)?'hide':'cancel';},snapshot,liveKeys:keys,
      takeTime:()=>wait('take-time'),engage:()=>wait('engage'),holdFocus:()=>wait('hold-focus'),releaseFocus:()=>wait('release-focus'),
      dismiss:async()=>{if(controller.canHideQuestion(frame))controller.hideQuestion(frame);else await controller.answer(frame,{cancelled:true});},answer:value=>controller.answer(frame,frame.method==='approval/requested'?{outcome:value==='rejected'?'denied':value}:{answer:value})};
  },[frame.rpcId,frame.method,state.sessionId,controller.epoch]);
  return frame.method==='approval/requested'?<ApprovalPanel matched={pending} t={t.approval} resolveReason={x=>String(x)} renderSlot={()=>null}/>:<QuestionComposer matched={pending} t={t.question} useStore={useQuestionDraft} actions={draft.actions} useQuestionCard={(_,selector=x=>x)=>selector(pending.snapshot())} renderSlot={(name,owner)=>name==='conversation.plan-review.actions'?<planReviews.Actions {...owner} state={state}/>:null}/>;
}
function QueueStatus({state}){
  const queue=state.queue;if(!queue)return null;
  const uncertain=(queue.items||[]).filter(x=>x.canResolve);
  const compact=state.compaction,unknown=compact?.lastReceipt?.state==='unknown'&&!compact.lastReceipt.acknowledged;
  return <>{state.unconfirmed&&<DisclosureRow open expandable={false} title="Submission unconfirmed; inspect history before continuing"><JsonBlock label={state.unconfirmed.kind==='compaction'?'Unconfirmed compaction':'Unconfirmed prompt'} payload={state.unconfirmed}/><Button onClick={()=>controller.clearUnconfirmed()}>Acknowledge; do not retry</Button></DisclosureRow>}{(unknown||compact?.available===false)&&<DisclosureRow open expandable={false} title={unknown?'Compaction outcome unknown; inspect native history':'Compaction receipt storage unavailable'}><JsonBlock label="Compaction receipt" payload={compact}/>{unknown&&<Button disabled={state.readOnly||compact.busy} onClick={()=>void control.run(async()=>{const result=await controller.rpc('session.acknowledgeCompaction',{sessionId:state.sessionId,requestId:compact.lastReceipt.requestId,acknowledgeUnknownOutcome:true});controller.update({compaction:result});})}>Acknowledge unknown; do not retry</Button>}</DisclosureRow>}{queue.paused&&<Button disabled={state.readOnly||!!uncertain.length||compact?.blocked} onClick={()=>void control.run(()=>controller.rpc('session.continueQueue',{sessionId:state.sessionId}))}>Resume waiting messages</Button>}{uncertain.map(item=><DisclosureRow key={item.id} open expandable={false} title={item.stateLabel||'Interrupted action: outcome unknown'}><JsonBlock label="Prompt" payload={item.message}/><Button disabled={state.readOnly} onClick={()=>void control.run(()=>controller.rpc('session.resolveQueue',{sessionId:state.sessionId,itemId:item.id,acknowledgeUnknownOutcome:true}))}>Keep interrupted; do not retry</Button></DisclosureRow>)}</>;
}

function ImproveDraft({state}){
  const [job,setJob]=useState(null),[undo,setUndo]=useState(null),text=useDraft(x=>x),active=useRef(null);
  const cancel=()=>{const value=active.current;active.current=null;setJob(null);if(value)void controller.rpc('prompt.cancelImprovement',{requestId:value.id,scopeId:value.id}).catch(()=>{});};
  useEffect(()=>{if(active.current&&(active.current.sessionId!==state.sessionId||active.current.original!==text))cancel();},[state.sessionId,text]);
  useEffect(()=>()=>{const value=active.current;if(value)void controller.rpc('prompt.cancelImprovement',{requestId:value.id,scopeId:value.id}).catch(()=>{});},[]);
  const improve=async()=>{
    if(job){cancel();return;}
    if(undo&&undo.sessionId===state.sessionId&&undo.text===text){setDraft(undo.original);setUndo(null);return;}
    const value={id:crypto.randomUUID(),sessionId:state.sessionId,original:text};active.current=value;setJob(value);
    try{const instructions=(await controller.rpc('prompts.list')).improvement;
      if(active.current!==value)return;
      const result=await controller.rpc('prompt.improve',{sessionId:value.sessionId,selection:state.selection,text:value.original,requestId:value.id,scopeId:value.id,expectedInstructionsRevision:instructions.revision});
      if(active.current!==value||controller.state.sessionId!==value.sessionId||draft.getSnapshot()!==value.original)return;
      if(result.kind!=='rewrite'||!result.text?.trim())throw Error('Invalid prompt improvement; the original draft is preserved.');
      active.current=null;setJob(null);setUndo({...value,text:result.text});setDraft(result.text);
    }catch(error){if(active.current===value)controller.update({error:error.message});}
    finally{if(active.current===value){active.current=null;setJob(null);}}
  };
  const label=job?'Cancel prompt improvement':undo?.sessionId===state.sessionId&&undo.text===text?'Undo prompt improvement':'Improve prompt';
  return <Button variant="ghost" aria-label={label} title={label} disabled={state.readOnly||state.draftReady===false||!state.sessionId||!text.trim()||state.phase!=='ready'} onClick={()=>void improve()}>{job?'×':label.startsWith('Undo')?'↶':'✦'}</Button>;
}

const SessionBridge=React.createContext(null);
function BoundSession(){return <ConversationSession {...React.useContext(SessionBridge)}/>;}
function CommandOverlays(){
  const composing=useRef(false),ended=useRef(0);
  // Keep IME candidate acceptance out of the generic copied option picker.
  return <div style={{display:'contents'}} onCompositionStart={()=>{composing.current=true;}} onCompositionEnd={()=>{composing.current=false;ended.current=performance.now();}} onKeyDownCapture={event=>{if(composing.current||event.nativeEvent.isComposing||event.nativeEvent.keyCode===229||performance.now()-ended.current<10)event.stopPropagation();}}>
    <MenuView menu={commandMenu.menu} headers={commandMenu.headers} onPick={(source,index,action)=>commandMenu.engine?.pick(source,index,action)} onHover={(source,index)=>commandMenu.engine?.hover(source,index)} onCrumb={(source,index)=>commandMenu.engine?.pickCrumb(source,index)} onDismiss={()=>commandMenu.dismiss()} t={t.menu}/>
    <PopupSelectView popup={commandMenu.popup} t={t.command}/>
  </div>;
}
function App(){
  const hasContextTab=useSyncExternalStore(contextTab.subscribe,contextTab.getSnapshot);
  const fleetPreference=useSyncExternalStore(contextTab.fleet.subscribe,contextTab.fleet.getSnapshot);
  const contextPrefs=useSyncExternalStore(contextPreferences.subscribe,contextPreferences.getSnapshot);
  const metafolderState=useSyncExternalStore(metafolders.subscribe,metafolders.getSnapshot);
  const settingsState=useSyncExternalStore(settingsShell.subscribe,settingsShell.getSnapshot);
  const shortcutRename=useWorkspaceShortcuts(state=>state.renameTarget);
  const state=useSyncExternalStore(controller.subscribe,controller.getSnapshot),[view,setView]=useState(hash.get('view')==='trajectory'?'trajectory':'chat'),[dialog,setDialog]=useState(null);
  const hasFleetTab=fleetPreference||state.capabilities?.archivedDsh===true;
  const pickerCuration=React.useMemo(()=>({...state.catalog,unavailable:state.catalog.groups.flatMap(group=>group.models.filter(model=>model.available===false).map(model=>group.provider+'/'+model.model))}),[state.catalog]);
  useEffect(()=>{document.title=state.readOnly?'Conversation inspector · Augmentor Harness':'Augmentor Harness';},[state.readOnly]);
  React.useLayoutEffect(()=>{if(!hasContextTab&&view==='context'||!hasFleetTab&&view==='fleet')setView('chat');contextModal.sync();if(state.phase!=='ready'||state.readOnly||contextPrefs.value.insightsEntry==='hide')layout.actions.selectPanel(null);});
  useEffect(()=>{commandMenu.deps.actions={export:scope=>sessionExports.download(scope.sessionId),compact:scope=>controller.compact(scope),file:()=>openFiles?.open(),goal:()=>setView('goal'),plan:scope=>controller.state.capabilities?.planMode?controller.setPlanMode(true,scope):setView('plan'),prompts:()=>setDialog({kind:'prompts'}),jobs:()=>setView('jobs'),context:(scope,segment,consume)=>contextModal.open(scope,segment,consume),inspect:scope=>window.open('/inspection#'+new URLSearchParams({token:controller.token,session:scope.sessionId}),'_blank','noopener,noreferrer')};},[]);
  const composed=useMemo(()=>projectDsh(state),[state.events,state.records,state.sessions,state.sessionId,state.phase,state.queue,state.goal,state.hasMore,state.payloads]);
  const liveDraft=useDraft(x=>x);useSyncExternalStore(attachmentDrafts.subscribe,attachmentDrafts.snapshot);const attached=attachmentDrafts.draft(state.sessionId);const loadImage=attachmentDrafts.loader(state.sessionId);
  const draftState=useSyncExternalStore(draftArchive.subscribe,draftArchive.getSnapshot);
  useEffect(()=>{const key=e=>{if(e.key==='Escape'&&!e.defaultPrevented&&!e.isComposing&&!dialog&&!settingsState.open&&!commandMenu.menu.getSnapshot().open&&!commandMenu.popup.state.getSnapshot().open&&!controller.visibleInteraction()&&state.sessions.find(x=>x.sessionId===state.sessionId)?.running){e.preventDefault();void control.run(()=>controller.stop());}};window.addEventListener('keydown',key);return()=>window.removeEventListener('keydown',key);},[state,dialog,settingsState.open]);
  const current=state.sessions.find(x=>x.sessionId===state.sessionId);
  const workspaces=useMemo(()=>{
    if(state.workspaces)return {...state.workspaces,phase:'ready',state:'ready'};
    const paths=[...new Set([state.workspace,...state.sessions.map(x=>x.cwd)].filter(Boolean))];
    return {phase:'ready',state:'ready',items:paths.map(cwd=>({workspaceId:cwd,cwd,title:cwd.split('/').filter(Boolean).at(-1)||cwd,sessionIds:state.sessions.filter(x=>x.cwd===cwd).map(x=>x.sessionId)})),pinnedSessionIds:[],archivedSessionIds:[]};
  },[state.sessions,state.workspace,state.workspaces]);
  const list=useMemo(()=>({projectionsBySession:{},ids:state.sessions.map(x=>x.sessionId),byId:Object.fromEntries(state.sessions.map(x=>[x.sessionId,{...x,id:x.sessionId,displayTitle:x.title||'New conversation',origin:'main',retainedBy:{mainView:x.sessionId===state.sessionId?1:0}}]))}),[state.sessions,state.sessionId]);
  const tabs=[{id:'chat',label:'Chat'},{id:'trajectory',label:'Trajectory'},...(hasContextTab?[{id:'context',label:'Context'}]:[]),...(hasFleetTab?[{id:'fleet',label:'Fleet'}]:[]),{id:'plan',label:'Plan'},{id:'goal',label:'Goal'},{id:'jobs',label:'Jobs'}];
  const useSession=selectorFace({...composed.session,blank:composed.session.blank&&view==='chat'&&!state.compactionPending&&!state.compaction?.blocked&&state.unconfirmed?.kind!=='compaction'}),useSessions=selectorFace(list),useWorkspaces=selectorFace(workspaces),useConversation=selectorFace(composed.conversation),useChat=selectorFace(composed.chat),useProjection=(name,selector=x=>x)=>selector(name==='imageLimits'?state.attachmentLimits:composed.projection[name]);
  const open=sid=>{layout.actions.selectPanel(null);void control.run(()=>controller.open(sid));},startSession=cwd=>{layout.actions.selectPanel(null);void control.run(()=>controller.create(cwd||current?.cwd||state.workspace));};
  const restoreSession=sid=>controller.organize('restore',sid);
  const pinSession=(sid,action)=>void controller.organize(action,sid).then(result=>{if(action==='pin'){const snapshot=result.workspaces;workspaceView.actions.pinSessionOrder(sid,pinOrderAccounts(snapshot.items,sid),pinOrderSource(snapshot.items,list,snapshot));}}).catch(()=>notifyRow(action==='pin'?'pinFailed':'unpinFailed'));
  const archiveSession=sid=>void control.run(async()=>{const result=await controller.organize('archive',sid);if(result.confirmation)archiveRequest.set(result.confirmation);else notifyRow('archived',{sessionId:sid});});
  const stopAndArchiveSession=async sid=>{const result=await controller.organize('archive',sid,true);if(result.confirmation)throw Error('Stopping is still pending. The conversation was not archived. Inspect its work before trying again.');notifyRow('stoppedAndArchived',{sessionId:sid});};
  const sessionActions={t:t.workspace,usePinned:selectorFace(new Set(workspaces.pinnedSessionIds)),useArchived:selectorFace(new Set(workspaces.archivedSessionIds)),useShortcuts:harnessShortcuts.useCatalog,pinSession:sid=>pinSession(sid,'pin'),unpinSession:sid=>pinSession(sid,'unpin'),archiveSession,unarchiveSession:sid=>void control.run(()=>restoreSession(sid)),forkSession:sid=>void control.run(()=>forkLast(sid)),requestSessionRename:(sid,title)=>setDialog({kind:'rename',sid,title})};
  useLayoutEffect(()=>{harnessShortcuts.update({startSession,forkSession:sid=>forkLast(sid),archiveSession},state.phase==='ready'&&current?{...list.byId[state.sessionId],blank:composed.session.blank}:null);});
  const createWorkspace=async({path})=>controller.adoptWorkspace(path);
  const unsupported=()=>Promise.reject(Error('This operation is not yet available in Harness. Use Full Pi record inspector in Settings for the retained Augmentor controls.'));
  const branch=seq=>{const revision=draftRev;void control.run(()=>controller.forkAt(seq,()=>draftRev===revision));};
  const edit=seq=>{const revision=draftRev,sid=controller.state.sessionId,epoch=controller.epoch;void control.run(async()=>{await draftArchive.flush(sid);if(draftRev!==revision||controller.epoch!==epoch||controller.state.sessionId!==sid)return;return controller.editAt(seq,()=>draftRev===revision);});};
  const renderMessageImages=props=><MessageImages {...props} loadImage={loadImage} t={t.conversation}/>;
  const common={renderMessageImages,sessionId:state.sessionId||undefined,useSession,useSessions,useWorkspaces,useConversation,useProjection,useConversationViews:selectorFace(tabs),useSessionStatus:selectorFace(new Map()),useInput:selectorFace({draft:liveDraft,phase:'plain',attachmentIds:attached.items.map(x=>x.id),queue:state.queue?.items||[]}),useStore:selectorFace({view}),actions:{setDraft:value=>{const text=typeof value==='string'?value:value.text;if(text!==draft.getSnapshot()||JSON.stringify(value.references??[])!==JSON.stringify(references()))setDraft(value);},completeViewRequest:noOp},inputActions:{...dictationActions,pruneAttachments:ids=>{for(const id of ids)attachmentDrafts.remove(id);},persistDraft:()=>{void draftArchive.persist().catch(()=>{});}},selectWorkspace:async cwd=>startSession(cwd),useComposerBlock:selectorFace(undefined),useFactorySlot:(_,fallback)=>fallback,bindDraftPersistence:writer=>draft.subscribe(()=>writer({text:draft.getSnapshot(),references:references()})),openView:setView,useInspectCall:selectorFace(undefined),t:t.conversation};
  useEffect(()=>{
    const groups=state.catalog.groups.map(g=>({id:g.provider,name:g.name,models:g.models.map(m=>({id:m.model,name:m.name||m.model,...(m.provider===state.selection?.provider&&m.model===state.selection?.model&&state.reasoning?{reasoning:{efforts:state.reasoning.availableLevels.map(id=>({id,label:id})),defaultEffort:state.reasoning.thinkingLevel}}:{})}))}));
    modelDirectory.set({current:state.selection?{...state.selection,reasoningEffort:state.reasoning?.thinkingLevel}:null,routable:true,groups,failures:state.catalog.failures||[],status:'ready',pending:null,error:null});
  },[state.catalog,state.selection,state.reasoning]);
  const goalAction=async(operation,extra={})=>{
    try{const goal=controller.state.goal?.goal;await controller.rpc('session.updateGoal',{sessionId:state.sessionId,change:{operation,expectedRef:goal?{id:goal.id,revision:goal.revision}:null,...extra,...(operation==='resume'?{continueAutomatically:true}:{})}});const next=await controller.rpc('session.goal',{sessionId:state.sessionId});controller.update({goal:next});return {ok:true,value:next};}catch(e){return {ok:false,error:{message:e.message,code:'goal-update'}};}
  };
  const render=(name,owner={},options={})=>{
    const p={...common,...owner,renderSlot:render,renderSlotChain:(name,owner,opts)=>name==='conversation.composer'&&!state.readOnly&&controller.visibleInteraction()?<InteractionTakeover frame={controller.visibleInteraction()} state={state}/>:opts.fallback,renderFactorySlot:(name,owner,opts)=><ConversationContent {...common} {...owner} renderSlot={render} renderSlotChain={(name,owner,o)=>name==='conversation.composer'&&!state.readOnly&&controller.visibleInteraction()?<InteractionTakeover frame={controller.visibleInteraction()} state={state}/>:o.fallback} useFactorySlot={(key,fallback)=>key==='views'?BoundSession:opts.slots?.[key]||fallback}/>};
    switch(name){
      case 'sidebar':return <SidebarRoot {...p} t={t.sidebar} usePanels={selectorFace(state.readOnly||contextPrefs.value.insightsEntry==='hide'?[]:[{id:'dsh-context',label:'Context Insights'}])} useShortcuts={harnessShortcuts.useCatalog} usePanelInfo={selector=>useLayout(s=>selector(s.panelInfo))} startSession={()=>startSession()} toggleSidebar={layout.actions.toggleSidebar} selectPanel={layout.actions.selectPanel}/>;
      case 'sidebar.brand.mark':return <AugmentorBrand size={owner.size}/>;
      case 'conversation.hero.brand.mark':return <AugmentorBrand size={owner.size} className={owner.className}/>;
      case 'sidebar.brand.name':return <span className={sidebarCss.fallbackBrandName}>Augmentor Harness</span>;
      case 'sidebar.workspaces':if(!state.readOnly&&metafolderState.value.enabled)return <MetafolderSidebar {...owner} state={state} controller={controller} profile={metafolders} workspaces={workspaces} list={list} layout={layout} workspaceView={workspaceView} shortcuts={shortcuts} t={t.workspace} open={open} startSession={startSession} sessionActions={sessionActions} rowActions={sid=><><ArchiveSessionRowButton sessionId={sid} {...sessionActions}/><PinSessionRowButton sessionId={sid} {...sessionActions}/></>} searchSessions={async query=>({items:state.sessions.filter(x=>x.title.toLowerCase().includes(query.toLowerCase())).map(x=>({sessionId:x.sessionId,title:x.title,cwd:x.cwd}))})}/>;return <WorkspaceBrowser {...p} t={t.workspace} useStore={useWorkspaceView} actions={workspaceView.actions} usePanelInfo={selector=>useLayout(s=>selector(s.panelInfo))} useHostInfo={selectorFace({home:''})} useWorkspaceShortcuts={useWorkspaceShortcuts} useShortcuts={harnessShortcuts.useCatalog} useDirectoryFlow={selectorFace(!state.readOnly)} open={open} startSession={startSession} searchResultLimit={100} searchSessions={async query=>({items:state.sessions.filter(x=>x.title.toLowerCase().includes(query.toLowerCase())).map(x=>({sessionId:x.sessionId,title:x.title,cwd:x.cwd}))})} requestSearch={shortcuts.search} requestAddWorkspace={shortcuts.add} closeAddWorkspace={shortcuts.closeAdd} setDirectoryBusy={shortcuts.directoryBusy} dismissForkError={shortcuts.dismissForkError} requestSessionRename={(sid,title)=>{setDialog({kind:'rename',sid,title});}} notifyArchivedNotOpenable={()=>notifyRow('archivedNotOpenable')} renameWorkspace={(workspaceId,title)=>controller.workspaceAction('rename',{workspaceId,title})} deleteWorkspace={workspaceId=>controller.workspaceAction('remove',{workspaceId})} insertWorkspaceBefore={(workspaceId,beforeWorkspaceId)=>controller.workspaceAction('move',{workspaceId,beforeWorkspaceId})} unarchiveSession={restoreSession} createWorkspace={createWorkspace}/>;
      case 'sidebar.workspaces.directoryFlow':return DirectoryFlow(owner);
      case 'sidebar.settings':return <OriginalSettings wide={owner.wide} state={state} controller={controller} preferences={contextPreferences} developerTools={developerTools} appearanceProfile={appearanceProfile} metafolders={metafolders} shortcutsUi={harnessShortcuts} notice={settingsNotice} onPrompts={initialTab=>setDialog({kind:'prompts',initialTab})} onTrajectory={sid=>{layout.actions.selectPanel(null);open(sid);setView('trajectory');}} onContext={()=>{layout.actions.selectPanel(null);if(hasContextTab)setView('context');else{setView('chat');filePreviews.openTab(state.sessionId,'dsh-context');}}}/>;
      case 'sidebar.workspaces.session.menu.item':{if(state.readOnly)return null;const props={...p,...sessionActions,useMenuOpenState:()=>options.hookContext||[false,noOp]};return <><PinSessionMenuItem {...props}/><RenameSessionMenuItem {...props}/><ForkSessionMenuItem {...props}/><ArchiveSessionMenuItem {...props}/></>;}
      case 'sidebar.workspaces.session.row.action':return state.readOnly?null:<><ArchiveSessionRowButton {...p} {...sessionActions}/><PinSessionRowButton {...p} {...sessionActions}/></>;
      case 'sidebar.panellist':return options.only==='dsh-context'?<InsightPanelIcon size={owner.size}/>:null;
      case 'main':return options.entryKey==='dsh-context'&&!state.readOnly?<DshContextInsights controller={controller} onOpen={sid=>{layout.actions.selectPanel(null);open(sid);}} onSettings={()=>settingsShell.actions.openSection('plugins')}/>:<ConversationRoot {...p}/>;
      case 'rightbar':return <DshPreviewSidebar previews={filePreviews} state={state} {...owner}/>;
      case 'conversation.session.header.corner':return <DshPreviewExpand previews={filePreviews} state={state}/>;
      case 'conversation.header':return <ConversationHeader {...p}/>;
      case 'conversation.header.leading':return state.readOnly?<span role="status" aria-label="Read-only conversation inspector" data-augmentor-access="read-only">Read-only{state.capabilities?.archivedDsh?' · Archived DSH cut':''}</span>:options.fallback??null;
      case 'conversation.session.header':return <ConversationSessionHeader {...p} open={open} selectView={setView}/>;
      case 'conversation.session.header.utilities':return state.readOnly||!state.capabilities?.sessionExport?null:<SessionLogDownloadHeaderAction {...p} t={tr(exportEn)} useSessionLogDownload={useSessionLogDownload} useFeedbackAvailable={selector=>selector(false)} request={sid=>control.run(()=>sessionExports.download(sid))} dismiss={sessionExports.dismiss} openFeedback={noOp}/>;
      case 'conversation.session.header.actions':return <Button variant="ghost" disabled={state.readOnly} aria-label="Rename conversation" onClick={()=>setDialog({kind:'rename',sid:state.sessionId,title:current?.title||''})}><IconEditOutlineRegular/></Button>;
      case 'conversation.hero.workspace':return <WorkspacePicker {...p} t={t.workspace} useDirectoryFlow={selectorFace(!state.readOnly)} createWorkspace={createWorkspace}/>;
      case 'conversation.workspace.directoryFlow':return DirectoryFlow(owner);
      case 'conversation.session':return <ConversationSession {...p}/>;
      case 'conversation.view':{
        const id=options.only||view;
        if(id==='chat')return <ChatView {...p} t={t.chat} useChat={useChat} usePresentation={selectorFace(presentation)} openFile={async(path,options)=>{if(!filePreviews.open(path,{params:options?.line===undefined?undefined:{line:options.line}}))throw Error('File preview is unavailable in this conversation.');}} openSkill={name=>void control.run(()=>openCurrentSkill(controller,filePreviews,name))} openExternalLink={url=>{window.open(url,'_blank','noopener,noreferrer');}} loadOlder={()=>controller.older()} loadThrough={()=>controller.older()} loadImage={loadImage} inspectCall={()=>setView('trajectory')} chatScroll={position} forkAt={branch} fileMentions={()=>undefined}/>;
        if(id==='trajectory')return <TrajectoryView {...p} t={t.trajectory} recordedRequestsOnly useTrajectory={selectorFace(composed.trajectory)} useDuration={useDuration} setActualDuration={value=>duration.set(value)} jsonStringWrapping={{getDefault:()=>wrapping.getSnapshot(),setDefault:value=>wrapping.set(value)}} loadOlder={()=>controller.older()} loadImage={loadImage} viewRequest={null}/>;
        if(id==='fleet'&&hasFleetTab)return <DshContextFleet key={state.sessionId} state={state} controller={controller}/>;
        if(id==='context'&&hasContextTab)return <DshContextDashboard key={state.sessionId} state={state} controller={controller}><ContextView state={state}/></DshContextDashboard>;
        return <ExtensionView key={id+state.sessionId} kind={id} state={state}/>;
      }
      case 'conversation.chat.flow':return <ChatFlow {...p} t={t.chat} useChat={useChat} useChatNode={(key,selector=x=>x)=>selector(composed.chat.nodes.get(key))} useChatNodeBottom={()=>false} useChatNodeProcess={()=>undefined} useChatGroup={()=>undefined} usePresentation={selectorFace(presentation)} useStore={selectorFace({})} useGroupAction={useGroupAction} useGroupHeaderAction={useGroupAction}/>;
      case 'conversation.chat.node':
        if(owner.node.kind==='user')return <UserMessageNodeView {...p} t={t.chat} onEdit={!state.readOnly&&state.capabilities?.messageEditDrafts===1&&owner.node.data.messageSeq===messageTargets(state.events).editSeq?()=>edit(owner.node.data.messageSeq):undefined} editUnavailable={state.phase!=='ready'||!draftState.ready||!!state.branchPending||current?.running===true||!!state.unconfirmed||state.compactionPending||state.compaction?.blocked||attachmentDrafts.busy}/>;
        if(owner.node.kind==='assistant-step')return <><OwnedMessage {...p}/>{Number.isSafeInteger(owner.node.data.finalNode?.seq)&&messageTargets(state.events).replies.has(owner.node.data.finalNode.seq)&&<MessageIconActions text={owner.node.data.blocks.filter(x=>x.kind==='text').map(x=>x.text).join('')} clock="end" t={t.chat} onBranch={state.readOnly?undefined:()=>branch(owner.node.data.finalNode.seq)} branchUnavailable={current?.running===true||!!state.branchPending}/>}</>;
        if(owner.node.kind==='compaction')return <CompactionNodeView {...p} t={t.chat}/>;
        if(owner.node.kind==='pi-tool')return <PiTool node={owner.node} state={state} onInspect={()=>setView('trajectory')}/>;
        return <p role="status">{owner.node.data.text}</p>;
      case 'conversation.chat.reasoning.body':return <MarkdownText text={owner.text} streaming={owner.running}/>;
      case 'conversation.input.dock':return <><QueueStatus state={state}/><QueueDock {...p} useSession={selectorFace({...composed.session,subagent:state.readOnly?{address:{mode:'read-only'}}:null})} updateQueue={(itemId,action)=>controller.updateQueue(itemId,action)} notify={(_,text)=>controller.update({error:text})} loadImage={loadImage}/>{!state.readOnly&&<GoalBar goal={state.goal?.goal} activation={state.goal?.activation} t={t.goal} onPause={()=>goalAction('pause')} onResume={()=>goalAction('resume')} onClear={()=>goalAction('clear')} onEdit={objective=>goalAction('edit',{objective,maxGoalRounds:state.goal?.goal?.maxGoalRounds})}/>}</>;
      case 'conversation.composer.bar':return <InputBar {...p} contextMeterPlacement="toolbar" placeholder={state.readOnly?'Read-only conversation':owner.variant==='hero'?'Describe what you want to build':'Message or run a task'} disabled={state.readOnly||state.phase!=='ready'||!draftState.ready||!!state.unconfirmed||state.compactionPending||state.compaction?.blocked||attachmentDrafts.busy||owner.disabled} keyboard={keyboard} addFiles={attachmentDrafts.add} removeAttachment={attachmentDrafts.remove} retryFileUpload={attachmentDrafts.retry} stop={()=>void control.run(()=>controller.stop())} useBusyEnter={selectorFace('queue')} useFileUploads={selectorFace(attached.uploads)} useNotices={selectorFace(undefined)} useLexicon={useLexicon} useMenuLauncher={useMenuLauncher} useStopShortcut={selectorFace(['Escape'])} resolveDraftAttachments={ids=>attached.items.filter(x=>ids.includes(x.id))} toggleCommandMenu={span=>commandMenu.toggle(span)}/>;
      case 'conversation.input.activity':return state.readOnly||state.phase!=='ready'?null:<OriginalDictation {...p} openSettings={()=>settingsShell.actions.openSection('plugins')}/>;
      case 'conversation.input.attachments':return <ComposerAttachments {...owner} t={t.conversation}/>;
      case 'conversation.message.images':return <MessageImages {...owner} loadImage={loadImage} t={t.conversation}/>;
      case 'conversation.input.permission':return <CurrentPermissionControl state={state} controller={controller} locked={owner.locked}/>;
      case 'conversation.input.plan':return <PlanModeControl state={state} controller={controller} locked={owner.locked}/>;
      case 'conversation.input.right':return <ImproveDraft state={{...state,draftReady:draftState.ready}}/>;
      case 'conversation.input.model':return <ModelSelect {...p} openAtTop curation={pickerCuration} t={t.model} locked={owner.locked||state.readOnly||current?.running===true} available={!state.readOnly} directory={modelDirectory} load={async()=>modelDirectory.getSnapshot()} select={async selection=>{modelDirectory.update(s=>({...s,status:'selecting',pending:selection}));try{await controller.choose(selection);return {ok:true,value:undefined};}catch(e){modelDirectory.update(s=>({...s,status:'error',pending:null,error:e.message}));return {ok:false,error:{code:'models/selection-failed',message:e.message}};}}}/>;
      case 'conversation.input.overlay':return <><CommandOverlays/><DshContextOverlay key={state.sessionId} state={state} controller={controller} binding={contextModal}/></>;
      default:return options.fallback??null;
    }
  };
  return <SessionBridge.Provider value={{...common,renderSlot:render}}><AppFrame t={t.common} useStore={useLayout} actions={layout.actions} useSessions={useSessions} usePanelInfo={selector=>useLayout(s=>selector(s.panelInfo))} renderSlot={render}/>{state.phase==='connecting'&&<Modal open title="Augmentor Harness" closeLabel="Close" onClose={noOp} description="Connecting to Pi…"/>}{state.error&&<Modal open title="Augmentor Harness" closeLabel="Close" onClose={()=>controller.update({error:null})} description={state.error}/>}<SessionRenameDialog t={t.workspace} useRenameRequest={selectorFace(dialog?.kind==='rename'?{sessionId:dialog.sid,currentTitle:dialog.title}:state.phase==='ready'&&!state.readOnly&&shortcutRename?.sessionId===state.sessionId?shortcutRename:null)} settleSessionRename={()=>{shortcuts.closeRename();setDialog(null);}} renameSession={async(sessionId,title)=>{await controller.rpc('session.rename',{sessionId,title});await controller.refresh();}}/><SessionArchiveConfirmDialog t={t.workspace} useArchiveRequest={useArchiveRequest} settleSessionArchive={()=>archiveRequest.set(null)} stopAndArchiveSession={stopAndArchiveSession}/><RowActionToast t={t.workspace} useToast={useRowNotice} useStore={useWorkspaceView} dismissToast={()=>rowNotice.set(null)} undoArchive={sid=>void control.run(()=>restoreSession(sid))} showArchived={()=>workspaceView.actions.setArchivedFilter('show')} openForkSource={open}/> {dialog?.kind==='prompts'&&<PromptLibrary initialTab={dialog.initialTab} close={()=>setDialog(null)}/>} {harnessShortcuts.render('shell.overlay')}</SessionBridge.Provider>;
}

createRoot(document.getElementById('root')).render(<App/>);
void controller.start(hash.get('session')).catch(error=>controller.update({phase:'error',error:error.message}));
setInterval(()=>void controller.poll().catch(error=>controller.update({error:error.message})),350);
