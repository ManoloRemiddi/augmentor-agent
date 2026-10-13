// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import React,{useEffect,useMemo,useRef,useSyncExternalStore} from 'react';
import {Button} from '@deepseek-ai/dsh-client-ui-primitives';
import {makeOverviewPanel} from './vendor/dsh-context/src/client/components/overviewPanel.tsx';
import {makeViewKit} from './vendor/dsh-context/src/client/viewkit.ts';
import {DICT_EN} from './vendor/dsh-context/src/client/i18nEn.ts';
import {DshInsightsReader} from './dsh-insights-reader.mjs';
import {reportedInsightTokens} from './dsh-insights-data.mjs';
import {TIMING_LABELS,mergeTimings} from './dsh-context-timing.mjs';
import './vendor/dsh-context/src/client/styles/overview.css';
import './vendor/dsh-context/src/client/styles/dateRange.css';
const dictionary={...DICT_EN,'ov.range.all':'All retained','tokens.title':'Reported token buckets','ov.card.teamUsage':'Recorded session usage','ov.card.teamCost':'Price unavailable','stats.turns':'Recorded turns','stats.toolCalls':'Tool settlements','timing.total':'Recorded model time','ov.kpi.toolSub':'Effect success remains unverified','ov.kpi.wallSub':'{n} calls with a duration','timing.empty':'Detailed active-time breakdown is unavailable in Pi.','ov.heat.metric.steps':'Recorded requests','ov.skills.title':'Skills','augmentor.skillsUnavailable':'Skill-load attribution is not captured by Pi.','augmentor.currentUnavailable':'Newest context body unavailable','ov.unavailable':'Reading retained Pi metadata…'};
const t=(key,args={})=>Object.entries(args).reduce((text,[k,v])=>text.replaceAll('{'+k+'}',String(v)),dictionary[key]??key);
export function DshContextInsights({controller,onOpen,onSettings}){
 const opener=useRef(onOpen);opener.current=onOpen;
 const reader=useMemo(()=>new DshInsightsReader({rpc:(m,p)=>controller.rpc(m,p),current:()=>({...controller.state,epoch:controller.epoch})}),[controller]);
 const state=useSyncExternalStore(reader.subscribe,reader.getSnapshot);
 useEffect(()=>{void reader.load();return()=>reader.close();},[reader]);
 const Panel=useMemo(()=>makeOverviewPanel({locale:{getLocale:()=>({active:'en'})},get:name=>name==='locale'?{getLocale:()=>({active:'en'})}:name==='sessions'?{refresh:()=>reader.load()}:name==='uiWorkspace'?{openSession:id=>{if(reader.state.snapshot?.ids.includes(id)&&controller.state.phase==='ready'&&!controller.state.readOnly)opener.current(id);}}:undefined},makeViewKit(t),TIMING_LABELS),[reader,controller]);
 const recordedMetrics=ids=>{let tools=0,modelMs=0,timedCalls=0;for(const id of ids){const row=state.details.get(id);if(!row||row.error||row.partial)return null;tools+=row.summary.tools;modelMs+=row.summary.modelMs;timedCalls+=row.summary.timedCalls;}return {tools,modelMs,timedCalls};};
 const recordedTiming=ids=>{const values=[];for(const id of ids){const row=state.details.get(id);if(!row||row.error||row.partial)return null;if(row.summary.stepTiming.timing)values.push(row.summary.stepTiming.timing);}return mergeTimings(values);};
 const timingCoverage=[...state.details.values()].reduce((total,row)=>{const c=row.summary?.stepTiming?.coverage;if(c){total.complete+=c.completeSteps;total.legacy+=c.legacyRequests;total.partial+=c.partialSteps;total.incomplete+=c.incompleteSteps+c.invalidSteps;}return total;},{complete:0,legacy:0,partial:0,incomplete:0});
 const coverage=state.coverage;
 return <section className="lc-ov-page"><div className="augmentor-extension" role="status">{state.phase==='loading'?'Reading saved records…':state.error??`${coverage?.read??0} sessions · ${coverage?.bodies??0} newest contexts · ${coverage?.failed??0} failed · ${coverage?.partial??0} partial reads · ${coverage?.usageGaps??0} usage gaps.`} Figures cover retained records. Dates filter sessions by last update. Measured SDK steps: {timingCoverage.complete}; {timingCoverage.partial} partial; {timingCoverage.incomplete} incomplete/invalid; {timingCoverage.legacy} older/unlinked calls. Tool intervals include validation/approval and may overlap. Timings cover measured steps, excluding idle gaps between SDK steps. <Button disabled={state.phase==='loading'} onClick={()=>void reader.load()}>Refresh Insights</Button></div><Panel useSessions={select=>select(state.snapshot)} useWorkspaces={select=>select(state.workspaces)} reportedTokens={reportedInsightTokens} recordedMetrics={recordedMetrics} recordedTiming={recordedTiming} currentAvailable={id=>state.details.get(id)?.currentAvailable===true} openSettings={onSettings}/></section>;
}
