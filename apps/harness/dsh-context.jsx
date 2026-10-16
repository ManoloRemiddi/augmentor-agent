// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import React,{useEffect,useMemo,useSyncExternalStore} from 'react';
import {makeFleetView} from './vendor/dsh-context/src/client/components/fleetView.tsx';
import {FleetDetailCache} from './vendor/dsh-context/src/client/fleetDetail.ts';
import {DshContextFleetData} from './dsh-context-fleet-data.mjs';
import {makeContextModal} from './vendor/dsh-context/src/client/components/contextModal.tsx';
import {modalStoreOf,setPendingConsume,takePendingConsume} from './vendor/dsh-context/src/client/modalStore.ts';
import {DshContextModalBinding} from './dsh-context-modal-binding.mjs';
import {makeContextView} from './vendor/dsh-context/src/client/components/contextView.tsx';
import {makeViewKit} from './vendor/dsh-context/src/client/viewkit.ts';
import {DICT_EN} from './vendor/dsh-context/src/client/i18nEn.ts';
import {contextSettings as settings} from './dsh-context-settings.jsx';
import {projectDshContext} from './dsh-context-projection.mjs';
import {TIMING_LABELS} from './dsh-context-timing.mjs';
import {bindContextSnapshot} from './dsh-context-boundary.mjs';
import './vendor/dsh-context/src/client/styles/fleet.css';
import './vendor/dsh-context/src/client/styles/agentGraph.css';
import './vendor/dsh-context/src/client/styles/tailwind.css';
import './vendor/dsh-context/src/client/styles/base.css';
import './vendor/dsh-context/src/client/styles/modal.css';
import './vendor/dsh-context/src/client/styles/stats.css';
import './vendor/dsh-context/src/client/styles/stackedBar.css';
import './vendor/dsh-context/src/client/styles/trendChart.css';
import './vendor/dsh-context/src/client/styles/requestDetail.css';
import './vendor/dsh-context/src/client/styles/events.css';
import './vendor/dsh-context/src/client/styles/fileCard.css';
import './vendor/dsh-context/src/client/styles/browser.css';
import './vendor/dsh-context/src/client/styles/detailSections.css';
import './vendor/dsh-context/src/client/styles/attachments.css';
const dictionary={...DICT_EN,'overview.title':'Latest recorded context','browser.live':'Latest recorded request','browser.liveNow':'Latest recorded request','timing.empty':'Detailed active-time breakdown is not captured by Pi. Recorded model durations appear in Context Trend.',footer:'Category sizes ≈ displayed-text estimates (4 characters/token), including redacted text and placeholders. Opaque provider reasoning/signatures, control fields and binary media token sizes are not measured; transport/provider transformations remain unobserved. Provider totals are SDK-normalized usage; zero fields may be unavailable. Image token sizes, injection/skill attribution and next-request occupancy are not established. Node fingerprints identify retained snapshot content, not causal edit lineage.','plugin.hint':'Apache 2.0 · Pi adapter','stats.unpriced':'Price unavailable (no external lookup)','stats.costUnavailable':'Model prices are unavailable; automatic external lookups are disabled.','agents.title':'Agent Network','agents.sub':'Recorded context and saved workers · open a node to inspect','agents.solo':'No workers in the retained job catalogue.','fleet.prompt':'Initial prompt / assigned task','fleet.comms.sub':'Pi mailbox/relay data unavailable','stats.costTip':'Estimated cost for this session. Child usage uses saved producer aggregation; effect success is unverified.','stats.humanInputsTip':'Loaded user-message events; separate question-answer interactions are not counted.','events.empty':'No confirmed Pi compaction summaries in the loaded observations. Attempts and other context boundaries remain in Raw Pi records.','ev.compaction':'Pi saved a compaction summary. Removed-message count is unavailable; inspect Raw Pi records.','trend.durationTip':'Recorded model-call duration: after the provider payload hook through assistant settlement. Tool execution and user waits are not included. This is not full step active time.',...TIMING_LABELS};
const translate=(key,params={})=>Object.entries(params).reduce((text,[k,v])=>text.replaceAll('{'+k+'}',String(v)),dictionary[key]??key);
const locale={getLocale:()=>({active:'en'})};let navigation=null,family=null;
export function bindContextNavigation(previews){navigation=previews;family=new DshContextFleetData(previews.controller);}
const ctx={locale,get:name=>name==='locale'?locale:name==='sessions'&&family?.operator()?family.sessions:name==='uiWorkspace'&&family?.operator()?{openSession:id=>{const epoch=navigation.controller.epoch,sid=navigation.controller.state.sessionId;const pending=id===sid?navigation.controller.open(id):family.open(id,url=>window.open(url,'_blank','noopener,noreferrer'));void pending.catch(error=>{if(navigation.controller.epoch===epoch&&navigation.controller.state.sessionId===sid)navigation.controller.update({error:error.message});});}}:name==='sidebarRight'&&navigation?.enabled()?{openTab:kind=>{if(!navigation.openTab(navigation.controller.state.sessionId,kind))throw Error('Context sidebar is unavailable.');},...(navigation.fileEnabled()?{openResource:address=>{if(!navigation.openAddress(navigation.controller.state.sessionId,address))throw Error('Local file preview is unavailable.');}}:{})}:undefined};
const heads={headOf:id=>family?.headOf(id)??Promise.resolve(null)};
const Dashboard=makeContextView(ctx,makeViewKit(translate),settings,heads);
function useFamily(state,controller,active){
 const snapshot=useSyncExternalStore(family.subscribe,family.getSnapshot);
 useEffect(()=>active&&state.phase==='ready'&&(!state.readOnly||state.capabilities?.archivedDsh)?family.acquire():undefined,[active,controller.epoch,state.sessionId,state.readOnly,state.phase]);
 return snapshot;
}
function FamilyNotice({value}){return <div className="augmentor-extension" role="status" data-fleet-coverage>{value.status==='ready'?<>Saved family: {value.catalogue.coverage.verifiedChildren} verified workers; {value.catalogue.coverage.pendingChildren} pending, {value.catalogue.coverage.unavailableChildren} unavailable. {value.catalogue.coverage.archivedChildren?` ${value.catalogue.coverage.archivedChildren} archived DSH children (read-only).`:''} {value.catalogue.coverage.archiveAvailable===false?value.catalogue.coverage.archiveReason:''} Producer outcomes need verification.<details><summary>Family coverage</summary>Native workers come from retained parent jobs; archived DSH children come from checksum-verified source cuts and parent catalogues. Archived children have no live job, provider context, token accounting or resumable work. Ordinary branches and shell jobs are excluded. Child tokens use saved producer aggregation, counted separately from the parent's own requests. Job active-time, coordinated Teams and mailbox/relay records are unavailable. The inspector briefing is the saved assigned task; full effective input is in the worker's Context view.</details></>:value.status==='loading'?'Reading saved family identities…':value.error??'Family data is unavailable in this view.'}</div>;}
export function DshContextFleet({state,controller}){
 const value=useFamily(state,controller,true);
 const cache=useMemo(()=>new FleetDetailCache(id=>family.detailOf(id),id=>family.invalidateDetail(id)),[value.scope]);
 const View=useMemo(()=>makeFleetView(ctx,makeViewKit(translate),heads,cache),[cache]);
 const seats=useContextSeats(state,controller);
 return <div data-augmentor-context-host="fleet"><FamilyNotice value={value}/><View key={value.scope} sessionId={state.sessionId} useProjection={seats.useProjection} useChat={seats.useChat}/></div>;
}
const sharedProjections=new WeakMap();
function contextProjection(controller,state){
 const inputs=[controller.epoch,state.sessionId,state.readOnly,state.records,state.events,state.payloads,state.hasMore,state.observationHasMore];
 const previous=sharedProjections.get(controller);if(previous&&inputs.every((input,i)=>input===previous.inputs[i]))return previous.value;
 const value=projectDshContext(state);sharedProjections.set(controller,{inputs,value});return value;
}
/** Both original presentations use the same bounded retained-data seats. */
function useContextSeats(state,controller){
  const value=useMemo(()=>contextProjection(controller,state),[controller,controller.epoch,state.sessionId,state.readOnly,state.records,state.events,state.payloads,state.hasMore,state.observationHasMore]);bindContextSnapshot(value);
  const epoch=controller?.epoch,validScope=()=>controller?.epoch===epoch&&controller?.state.sessionId===state.sessionId;
  const requestPicker=controller?{choices:value.requestChoices.map(choice=>{const read=state.contextRead?.id===choice.id?state.contextRead:null;return {...choice,state:read?.state,note:read?.reason??(read?.state==='loading'?'Loading recorded provider request…':state.payloads[choice.id]?'This recorded provider format cannot be projected here; inspect its raw body.':'Choose this request to read its retained body.')};}),hasMore:state.observationHasMore===true,loading:state.contextPage?.loading===true,error:state.contextPage?.error,select:seq=>{const id=seq===null?null:value.requestChoices.find(c=>c.seq===seq)?.id;if(id!==undefined&&validScope())void controller.selectContextRequest(id).catch(()=>{});},older:()=>{if(validScope())void controller.loadContextOlder();}}:undefined;
  const projectedTimeline=useMemo(()=>({...value.timeline,augmentorCompositionAvailable:value.coverage.latestAvailable===true}),[value]);
  const projections={contextTimeline:projectedTimeline,contextHeaders:value.headers,tokenUsage:value.usage,contextPressure:value.pressure,augmentorContextRequests:requestPicker,augmentorContextNotice:`Recorded SDK snapshots: ${value.coverage.available} of ${value.coverage.observed} bodies loaded. Category sizes estimate displayed text; opaque/provider transformations and next-request occupancy are unobserved. ${value.coverage.observed&&!value.coverage.latestAvailable?'Composition shows the latest retained body; the newest body is unavailable. ':''}Raw Pi records remain in the Context tab. Measured SDK steps: ${value.coverage.timing.completeSteps}; ${value.coverage.timing.partialSteps} partial; ${value.coverage.timing.incompleteSteps+value.coverage.timing.invalidSteps} incomplete/invalid; ${value.coverage.timing.legacyRequests} older/unlinked calls. Model time uses SDK stream markers; tool intervals include validation/approval and may overlap; the original ring clamps sums and the strip merges concurrent intervals.`};
  const useProjection=key=>projections[key],useChat=select=>select({legacy:{nodes:value.conversationNodes}});
  return {value,useProjection,useChat};
}
export function createDshContextModalBinding(controller){return new DshContextModalBinding({current:()=>({...controller.state,epoch:controller.epoch}),storeOf:modalStoreOf,setPending:setPendingConsume,takePending:takePendingConsume});}
export function DshContextOverlay({state,controller,binding}){
  const preferences=useSyncExternalStore(settings.store.subscribe,settings.store.getSnapshot);
  const seats=useContextSeats(state,controller);
  const Modal=useMemo(()=>makeContextModal({get:name=>name==='sessions'?binding:ctx.get(name)},makeViewKit(translate),settings),[binding]);
  const modal=modalStoreOf(state.sessionId??''),useContextModal=selector=>selector(useSyncExternalStore(modal.subscribe,modal.getSnapshot)&&binding.valid(binding.pending?.scope));
  return preferences.status==='loading'?null:<Modal key={state.sessionId} sessionId={state.sessionId} useProjection={seats.useProjection} useChat={seats.useChat} useContextModal={useContextModal}/>;
}
/** The original dashboard receives recorded Pi data through its projection seats. */
export function DshContextDashboard({state,controller,children,host,scrollScope}){
  const preferences=useSyncExternalStore(settings.store.subscribe,settings.store.getSnapshot);
  const familyState=useFamily(state,controller,host==='sidebar'||settings.fleetTab()==='show');
  const {value,useProjection,useChat}=useContextSeats(state,controller);
  if(preferences.status==='loading')return <div className="augmentor-extension" role="status">Reading saved Context display defaults…</div>;
  return <div className="augmentor-context-dashboard" data-augmentor-context-host={host??'tab'} style={host==='sidebar'?{height:'100%',display:'flex',flexDirection:'column',minHeight:0,overflow:'hidden'}:undefined}><div className="augmentor-extension" role="status">{host==='sidebar'?<>Retained context: {value.coverage.available} of {value.coverage.observed} request bodies. Category sizes are estimates. {familyState.status==='ready'?'Saved family identities are available.':'Family data is unavailable or still loading.'}</>:<>Recorded provider context: {value.coverage.available} of {value.coverage.observed} request bodies available. {value.coverage.observed&&!value.coverage.latestAvailable?'The newest body is unavailable; composition shows the latest retained body. ':''}{value.coverage.historyPartial?'Message/file counts cover the loaded history. ':''}Category sizes are estimates; request contents are retained, credential-redacted snapshots. The latest eight eligible bodies load automatically. The original selector reads one older body or pages earlier metadata; unavailable bodies have no chart bar. Turn/step labels cover loaded records. {state.records?.filter(r=>r.kind==='model/request').at(-1)?.data.purpose==='manual-compaction'?'The latest request is Pi’s summary input, before its saved compaction boundary; next-request occupancy is not yet observed. ':''}SDK onPayload snapshots use their recorded API; raw records expose unsupported or larger bodies and opaque provider fields. {value.coverage.opaque?`${value.coverage.opaque} loaded bodies contain opaque reasoning/signatures or media; displayed estimates exclude those bytes. `:''} {value.coverage.compactionAttempts?`${value.coverage.compactionAttempts} recorded compaction attempts; ${value.coverage.confirmedCompactions} confirmed summaries. Failed, aborted and uncertain attempts remain in Raw Pi records. `:''}</>}</div>{host==='sidebar'?<FamilyNotice value={familyState}/>:null}<Dashboard key={state.sessionId} sessionId={state.sessionId} host={host} scrollScope={scrollScope} useProjection={useProjection} useChat={useChat}/>{host==='sidebar'?null:<details className="augmentor-extension"><summary>{state.capabilities?.archivedDsh?'Archived DSH source records':'Raw Pi context and saved entries'}</summary>{children}</details>}</div>;
}
