// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import React,{useEffect,useMemo,useSyncExternalStore} from 'react';
import {Button} from '@deepseek-ai/dsh-client-ui-primitives';
import {DshMemorySettings} from './dsh-memory-settings.mjs';

const modeLabels={off:'Thinking off for memory requests',default:'Server default for memory requests',unknown:'Request mode not reported',unconfigured:'Memory engine not configured'};
/** Existing native memory controls inside the original Settings shell. */
export function MemorySettings({controller,sharedProfile}){
 const profile=useMemo(()=>sharedProfile??new DshMemorySettings(controller),[controller,sharedProfile]);useEffect(()=>()=>{if(!sharedProfile)profile.close();},[profile,sharedProfile]);
 const state=useSyncExternalStore(profile.subscribe,profile.getSnapshot),value=state.value;
 if(!profile.current())return null;
 return <fieldset data-memory-settings><legend>Automatic memory</legend>
  <p>Relationship and project memory are kept separately. Conversation text is saved locally; updates run only during active tool windows.</p>
  {value?.connected?<>
   <p data-memory-request-mode>{modeLabels[value.requestMode]}. This is the configured engine choice. Chat and voice keep their own settings. Mode changes use local engine setup.</p>
   <p role="status">Capture and recall: {value.enabled?'on':'paused'}. Processing: {value.processing.issue?'unavailable':value.processing.known?(value.processing.paused?(value.processing.active?'pausing':'paused'):'enabled'):'not reported'}. {value.events} transcript records; {value.pending} pending items; {value.stopped} stopped jobs.</p>
   <p>{value.processing.issue==='gateway-in-use'?'Processing is unavailable because its local gateway port is in use. Capture and cached recall remain available. Resolve the conflict and restart the memory companion.':value.configured?(value.available?'Memory engine is available.':'Memory engine availability is not confirmed.'):'Local capture remains available; the memory engine is not configured.'}</p>
   <Button disabled={state.busy||!value.actions.capture} onClick={()=>void profile.change('capture').catch(()=>{})}>{value.enabled?'Pause automatic memory':'Resume automatic memory'}</Button>
   <Button disabled={state.busy||!value.actions.processing} onClick={()=>void profile.change('processing').catch(()=>{})}>{value.processing.paused?'Resume memory processing':'Pause memory processing'}</Button>
  </>:<p role="status">{state.busy?'Checking memory…':value?.message||'Memory status is not confirmed.'}</p>}
  {state.error&&<p role="alert">{state.error}</p>}
  <Button disabled={state.busy} onClick={()=>void profile.load()}>Refresh memory status</Button>
 </fieldset>;
}
