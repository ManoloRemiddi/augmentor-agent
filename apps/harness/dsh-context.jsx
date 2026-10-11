// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import React,{useMemo} from 'react';
import {makeContextView} from './vendor/dsh-context/src/client/components/contextView.tsx';
import {makeViewKit} from './vendor/dsh-context/src/client/viewkit.ts';
import {DICT_EN} from './vendor/dsh-context/src/client/i18nEn.ts';
import {createContextSettings} from './vendor/dsh-context/src/client/settings.ts';
import {projectDshContext} from './dsh-context-projection.mjs';
import {bindContextSnapshot} from './dsh-context-boundary.mjs';
import './vendor/dsh-context/src/client/styles/tailwind.css';
import './vendor/dsh-context/src/client/styles/base.css';
import './vendor/dsh-context/src/client/styles/stats.css';
import './vendor/dsh-context/src/client/styles/stackedBar.css';
import './vendor/dsh-context/src/client/styles/trendChart.css';
import './vendor/dsh-context/src/client/styles/requestDetail.css';
import './vendor/dsh-context/src/client/styles/events.css';
import './vendor/dsh-context/src/client/styles/fileCard.css';
import './vendor/dsh-context/src/client/styles/browser.css';
import './vendor/dsh-context/src/client/styles/detailSections.css';
import './vendor/dsh-context/src/client/styles/attachments.css';
const dictionary={...DICT_EN,'overview.title':'Latest recorded context','browser.live':'Latest recorded request','browser.liveNow':'Latest recorded request','timing.empty':'Detailed active-time breakdown is not captured by Pi. Recorded model durations appear in Context Trend.',footer:'Category sizes ≈ displayed-text estimates (4 characters/token), including redacted text and placeholders. Opaque provider reasoning/signatures, control fields and binary media token sizes are not measured; transport/provider transformations remain unobserved. Provider totals are SDK-normalized usage; zero fields may be unavailable. Image token sizes, injection/skill attribution and next-request occupancy are not established. Node fingerprints identify retained snapshot content, not causal edit lineage.','plugin.hint':'Apache 2.0 · Pi adapter','stats.unpriced':'Price unavailable (no external lookup)','stats.costUnavailable':'Model prices are unavailable; automatic external lookups are disabled.','agents.title':'Session Usage','stats.costTip':'Estimated cost for this session. Fleet usage is not available in this adapter.','stats.humanInputsTip':'Loaded user-message events; separate question-answer interactions are not counted.','events.empty':'No confirmed Pi compaction summaries in the loaded observations. Attempts and other context boundaries remain in Raw Pi records.','ev.compaction':'Pi saved a compaction summary. Removed-message count is unavailable; inspect Raw Pi records.','trend.durationTip':'Recorded model-call duration: after the provider payload hook through assistant settlement. Tool execution and user waits are not included. This is not full step active time.'};
const translate=(key,params={})=>Object.entries(params).reduce((text,[k,v])=>text.replaceAll('{'+k+'}',String(v)),dictionary[key]??key);
const ctx={get:name=>name==='locale'?{getLocale:()=>({active:'en'})}:undefined};
const settings=createContextSettings();settings.defaultPlacement=()=> 'tab';settings.fleetTab=()=> 'hide';
const Dashboard=makeContextView(ctx,makeViewKit(translate),settings,{headOf:async()=>null});
/** The original dashboard receives recorded Pi data through its projection seats. */
export function DshContextDashboard({state,controller,children}){
  const value=useMemo(()=>projectDshContext(state),[state.records,state.events,state.payloads,state.hasMore,state.observationHasMore]);bindContextSnapshot(value);
  const epoch=controller?.epoch,validScope=()=>controller?.epoch===epoch&&controller?.state.sessionId===state.sessionId;
  const requestPicker=controller?{choices:value.requestChoices.map(choice=>{const read=state.contextRead?.id===choice.id?state.contextRead:null;return {...choice,state:read?.state,note:read?.reason??(read?.state==='loading'?'Loading recorded provider request…':state.payloads[choice.id]?'This recorded provider format cannot be projected here; inspect its raw body.':'Choose this request to read its retained body.')};}),hasMore:state.observationHasMore===true,loading:state.contextPage?.loading===true,error:state.contextPage?.error,select:seq=>{const id=seq===null?null:value.requestChoices.find(c=>c.seq===seq)?.id;if(id!==undefined&&validScope())void controller.selectContextRequest(id).catch(()=>{});},older:()=>{if(validScope())void controller.loadContextOlder();}}:undefined;
  const projections={contextTimeline:value.timeline,contextHeaders:value.headers,tokenUsage:value.usage,contextPressure:value.pressure,augmentorContextRequests:requestPicker};
  const useProjection=key=>projections[key],useChat=select=>select({legacy:{nodes:value.conversationNodes}});
  return <div className="augmentor-context-dashboard"><div className="augmentor-extension" role="status">Recorded provider context: {value.coverage.available} of {value.coverage.observed} request bodies available. {value.coverage.observed&&!value.coverage.latestAvailable?'The newest body is unavailable; composition shows the latest retained body. ':''}{value.coverage.historyPartial?'Message/file counts cover the loaded history. ':''}Category sizes are estimates; request contents are retained, credential-redacted snapshots. The latest eight eligible bodies load automatically. The original selector reads one older body or pages earlier metadata; unavailable bodies have no chart bar. Turn/step labels cover loaded records. {state.records?.filter(r=>r.kind==='model/request').at(-1)?.data.purpose==='manual-compaction'?'The latest request is Pi’s summary input, before its saved compaction boundary; next-request occupancy is not yet observed. ':''}SDK onPayload snapshots use their recorded API; raw records expose unsupported or larger bodies and opaque provider fields. {value.coverage.opaque?`${value.coverage.opaque} loaded bodies contain opaque reasoning/signatures or media; displayed estimates exclude those bytes. `:''} {value.coverage.compactionAttempts?`${value.coverage.compactionAttempts} recorded compaction attempts; ${value.coverage.confirmedCompactions} confirmed summaries. Failed, aborted and uncertain attempts remain in Raw Pi records. `:''}</div><Dashboard key={state.sessionId} sessionId={state.sessionId} useProjection={useProjection} useChat={useChat}/><details className="augmentor-extension"><summary>Raw Pi context and saved entries</summary>{children}</details></div>;
}
