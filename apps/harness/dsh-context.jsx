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
const dictionary={...DICT_EN,'overview.title':'Latest recorded context','browser.live':'Latest recorded request','browser.liveNow':'Latest recorded request','timing.empty':'Detailed active-time breakdown is not captured by Pi. Recorded model durations appear in Context Trend.',footer:'Category sizes ≈ text estimates (4 characters/token), including redacted text. Provider totals are SDK-normalized usage; zero fields may be unavailable. Image token sizes, injection/skill attribution and next-request occupancy are not established. Node fingerprints identify retained snapshot content, not causal edit lineage.','plugin.hint':'Apache 2.0 · Pi adapter','stats.unpriced':'Price unavailable (no external lookup)','stats.costUnavailable':'Model prices are unavailable; automatic external lookups are disabled.','agents.title':'Session Usage','stats.costTip':'Estimated cost for this session. Fleet usage is not available in this adapter.','stats.humanInputsTip':'Loaded user-message events; separate question-answer interactions are not counted.','events.empty':'No Pi compaction-end events in the loaded observations. Other context boundaries remain in Raw Pi records.','trend.durationTip':'Recorded model-call duration: after the provider payload hook through assistant settlement. Tool execution and user waits are not included. This is not full step active time.'};
const translate=(key,params={})=>Object.entries(params).reduce((text,[k,v])=>text.replaceAll('{'+k+'}',String(v)),dictionary[key]??key);
const ctx={get:name=>name==='locale'?{getLocale:()=>({active:'en'})}:undefined};
const settings=createContextSettings();settings.defaultPlacement=()=> 'tab';settings.fleetTab=()=> 'hide';
const Dashboard=makeContextView(ctx,makeViewKit(translate),settings,{headOf:async()=>null});
/** The original dashboard receives recorded Pi data through its projection seats. */
export function DshContextDashboard({state,children}){
  const value=useMemo(()=>projectDshContext(state),[state.records,state.events,state.payloads,state.hasMore,state.observationHasMore]);bindContextSnapshot(value);
  const projections={contextTimeline:value.timeline,contextHeaders:value.headers,tokenUsage:value.usage,contextPressure:value.pressure};
  const useProjection=key=>projections[key],useChat=select=>select({legacy:{nodes:value.conversationNodes}});
  return <div className="augmentor-context-dashboard"><div className="augmentor-extension" role="status">Recorded provider context: {value.coverage.available} of {value.coverage.observed} request bodies available. {value.coverage.observed&&!value.coverage.latestAvailable?'The newest body is unavailable; composition shows the latest retained body. ':''}{value.coverage.historyPartial?'Message/file counts cover the loaded history. ':''}Category sizes are estimates; request contents are retained, credential-redacted snapshots. Charts show the latest eight automatically loaded bodies. Raw records below allow inspection of earlier requests.</div><Dashboard key={state.sessionId} sessionId={state.sessionId} useProjection={useProjection} useChat={useChat}/><details className="augmentor-extension"><summary>Raw Pi context and saved entries</summary>{children}</details></div>;
}
