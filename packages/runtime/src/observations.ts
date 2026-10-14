// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import type {AgentSession} from '@earendil-works/pi-coding-agent';
import {ObservationStore,payloadText} from '../../observation/src/store.js';
import type {Data} from '../../protocol/src/index.js';
import type {ContextProvenance} from './context-provenance.js';
import {StepTiming} from './step-timing.js';

/** Observe the supported SDK pipeline after all registered payload transforms. */
export function observeSession(session: AgentSession, store: ObservationStore, sessionId: string,
  current: () => {turnId?: string; selected: Data; permissionPreset?: string; toolBudget?: Data;execution?:Data;reasoning?:Data;compactionId?:string}, notify: (event: unknown) => void,
  warning: (message: string) => void, provenance?:ContextProvenance, finalPayload?:(payload:unknown,api:string)=>void) {
  let requestId: string | undefined;
  let started = 0, firstToken = false;
  let providerCount = 0, providerBytes = 0, providerDropped = 0, captureProvider = false;
  let requestOpen = false;
  const providerRedactions = new Set<string>();
  let providerEvents: {index: number; elapsedMs?: number; data: unknown}[] = [];
  const resetProvider = () => {
    providerCount = 0; providerBytes = 0; providerDropped = 0; providerEvents = []; providerRedactions.clear();
    captureProvider = store.policy().capturePayloads;
  };
  const tools = new Map<string, number>();
  const timing=new StepTiming();
  const record = (kind: string, data: Record<string, unknown>, payload?: unknown) => {
    try {
      const event = store.append(sessionId, kind, data, {turnId: current().turnId, requestId:kind.startsWith('execution/')||kind.startsWith('step/')?undefined:requestId}, payload);
      notify(event); return event;
    } catch (error) {warning('Local inspection could not record an observation: ' + String(error));}
  };
  const previousPayload = session.agent.onPayload;
  const previousStream=session.agent.streamFunction;
  const previousTransform=session.agent.transformContext;
  const inspect=(action:()=>void)=>{try{action();}catch(error){warning('Local context inspection could not capture a boundary: '+String(error));}};
  const transformHook:typeof previousTransform=async(messages,signal)=>{
    inspect(()=>provenance?.beginRequest(messages));
    const transformed=previousTransform?await previousTransform(messages,signal):messages;
    inspect(()=>provenance?.transformed(transformed));return transformed;
  };
  if(provenance)session.agent.transformContext=transformHook;
  let requestedThinking:string|undefined;
  const streamHook:typeof previousStream=async(model,context,options)=>{
    const operationId=current().compactionId;
    if(operationId&&session.isCompacting){
      // Default Pi summaries use stream options directly and bypass Agent's
      // onPayload/message hooks. Observe the public request options/result;
      // never consume, replace or retry the SDK's stream.
      let id:string|undefined,clock=0,count=0,bytes=0,dropped=0;
      const capture=store.policy().capturePayloads,events:unknown[]=[],redactions=new Set<string>();
      const summaryRecord=(kind:string,data:Data,payload?:unknown)=>{
        let event;inspect(()=>{event=store.append(sessionId,kind,{...data,purpose:'manual-compaction',operationId},{requestId:id},payload);notify(event);});return event as ReturnType<ObservationStore['append']>|undefined;
      };
      const stream=await previousStream(model,context,{...options,
        onPayload:async(body,selected)=>{const transformed=await options?.onPayload?.(body,selected),effective=transformed===undefined?body:transformed;clock=performance.now();id=undefined;
          id=summaryRecord('model/request',{selected:current().selected,model:model.id,provider:model.provider,api:model.api,capacity:model.contextWindow,thinkingLevel:options?.reasoning??'off',boundary:'provider-payload-after-summary-hooks',transportAttempts:'not-observed'},effective)?.id;return transformed;},
        onResponse:async(response,selected)=>{await options?.onResponse?.(response,selected);summaryRecord('model/response',{status:response.status});},
        onProviderStreamEvent:async(data,selected)=>{await options?.onProviderStreamEvent?.(data,selected);count++;
          if(!capture||!store.policy().capturePayloads){dropped++;return;}
          try{const snapshot=payloadText(data),size=Buffer.byteLength(snapshot.text)+128;if(bytes+size>8*1024*1024){dropped++;return;}bytes+=size;snapshot.redactions.forEach(key=>redactions.add(key));events.push({index:count,...(clock?{elapsedMs:performance.now()-clock}:{}),data:JSON.parse(snapshot.text)});}catch{dropped++;}
        },
      });
      // result() is a public, repeatable promise. Pi still owns and consumes it.
      void stream.result().then(message=>{
        if(count)summaryRecord('provider/stream',{boundary:'parsed-summary-provider-events-after-hooks',observedEvents:count,capturedEvents:events.length,droppedEvents:dropped,coverage:!capture?'disabled-at-request-start':dropped?'partial':'complete',credentialRedactions:[...redactions],maxCaptureBytes:8*1024*1024},{events});
        summaryRecord('model/complete',{stopReason:message.stopReason,usage:message.usage,usageBoundary:'sdk-normalized; zero fields may be unavailable',requestCoverage:id?'observed-after-summary-hooks':'not-observed',...(clock?{durationMs:performance.now()-clock}:{}),model:message.model,provider:message.provider},message);
      }).catch(()=>summaryRecord('model/complete',{stopReason:'error',requestCoverage:id?'observed-after-summary-hooks':'not-observed'}));
      return stream;
    }
    requestedThinking=options?.reasoning??'off';inspect(()=>provenance?.streaming(context));return previousStream(model,context,options);
  };
  if(typeof previousStream==='function')session.agent.streamFunction=streamHook;
  const payloadHook: typeof previousPayload = async (payload, model) => {
    inspect(()=>provenance?.beforePayload(payload));
    const transformed = await previousPayload?.(payload, model);
    const effective = transformed === undefined ? payload : transformed;
    // Core native request state uses the same final boundary, independently of
    // optional diagnostics. Do not swallow a failed native persistence receipt.
    finalPayload?.(effective,model.api);
    started = performance.now(); firstToken = false; requestId = undefined;
    resetProvider(); requestOpen = true;
    const event = record('model/request', {
      selected: current().selected, model: model.id, provider: model.provider, api: model.api,
      thinkingLevel: requestedThinking??session.thinkingLevel,savedThinkingLevel:session.thinkingLevel,
      thinkingBoundary:requestedThinking===undefined?'session-setting-only':'sdk-stream-options; provider payload may translate or override',capacity: model.contextWindow,
      policies: {permissionPreset: current().permissionPreset, toolBudget: current().toolBudget,execution:current().execution,reasoning:current().reasoning},
      boundary: 'provider-payload-after-hooks', transportAttempts: 'not-observed',
    }, effective);
    requestId = event?.id;
    inspect(()=>timing.modelStart(requestId));
    if(requestId&&provenance)inspect(()=>{const contribution=provenance.finish(effective);record('context/provenance',contribution.data,contribution.payload);});
    return transformed;
  };
  session.agent.onPayload = payloadHook;
  const previousResponse = session.agent.onResponse;
  const responseHook: typeof previousResponse = async (response, model) => {
    await previousResponse?.(response, model);
    record('model/response', {status: response.status});
  };
  session.agent.onResponse = responseHook;
  const previousProvider = session.agent.onProviderStreamEvent;
  const providerHook: typeof previousProvider = async (data, model) => {
    await previousProvider?.(data, model);
    if (!requestOpen) {requestId = undefined; started = 0; firstToken = false; resetProvider(); requestOpen = true;}
    providerCount++;
    if (!captureProvider || !store.policy().capturePayloads) {providerDropped++; return;}
    try {
      // Take an immutable JSON copy. The SDK/provider may reuse mutable data.
      // Bound additional live diagnostic memory independently of model output.
      const snapshot = payloadText(data);
      const bytes = Buffer.byteLength(snapshot.text) + 128;
      if (providerBytes + bytes > 8 * 1024 * 1024) {providerDropped++; return;}
      providerBytes += bytes;
      snapshot.redactions.forEach(key => providerRedactions.add(key));
      providerEvents.push({index: providerCount, ...(started ? {elapsedMs: performance.now() - started} : {}), data: JSON.parse(snapshot.text)});
    } catch {providerDropped++;}
  };
  session.agent.onProviderStreamEvent = providerHook;
  const unsubscribe = session.subscribe(event => {
    if(event.type==='turn_start')inspect(()=>{
      const abandoned=timing.abandon('superseded-by-sdk-turn-start');if(abandoned)record('step/incomplete',abandoned);
      record('step/start',timing.begin());
    });
    if(event.type==='message_update')inspect(()=>timing.stream(event.assistantMessageEvent.type));
    if (event.type === 'message_start' && event.message.role === 'assistant' && !requestOpen) {
      // Unsupported/custom adapters may not invoke request hooks. A new
      // assistant message must not inherit the previous request's identity.
      requestId = undefined; started = 0; firstToken = false; resetProvider(); requestOpen = true;
    }
    if (event.type === 'message_start' && event.message.role === 'user') {
      record('user/message', {role: 'user'}, event.message);
    }
    if (event.type === 'message_update' && requestId && !firstToken &&
      ['text_delta', 'thinking_delta', 'toolcall_delta'].includes(event.assistantMessageEvent.type)) {
      firstToken = true; record('model/firstToken', {elapsedMs: performance.now() - started});
    }
    if (event.type === 'message_end' && event.message.role === 'assistant') {
      inspect(()=>timing.modelEnd());
      const observedProviderCount = providerCount;
      if (providerCount) record('provider/stream', {boundary: 'parsed-provider-events-after-hooks-before-normalization',
        observedEvents: providerCount, capturedEvents: providerEvents.length, droppedEvents: providerDropped,
        coverage: !captureProvider ? 'disabled-at-request-start' : providerDropped ? 'partial' : 'complete',
        credentialRedactions: [...providerRedactions], maxCaptureBytes: 8 * 1024 * 1024,
        timings: started ? 'monotonic milliseconds since managed request hook' : 'not-observed'},
      {events: providerEvents});
      providerEvents = []; providerBytes = 0; providerCount = 0;
      record('model/complete', {stopReason: event.message.stopReason, usage: event.message.usage,thinkingLevel:event.message.thinkingLevel,providerThinkingLevel:event.message.providerThinkingLevel,
        usageBoundary: 'sdk-normalized; zero fields may be unavailable',
        requestCoverage: requestId ? 'observed-after-hooks' : 'not-observed',
        providerEventCoverage: observedProviderCount ? 'observed' : 'not-observed',
        ...(requestId && started > 0 ? {durationMs: performance.now() - started} : {}), model: event.message.model, provider: event.message.provider},
      event.message);
      requestOpen = false;
      requestedThinking=undefined;
      provenance?.endRequest();
    }
    if (event.type === 'tool_execution_start') {
      inspect(()=>timing.toolStart(event.toolCallId,event.toolName,event.parentToolCallId));
      tools.set(event.toolCallId, performance.now());
      record('tool/start', {name: event.toolName, toolCallId: event.toolCallId,...(event.parentToolCallId?{parentToolCallId:event.parentToolCallId}:{}),boundary:'proposed-before-validation'}, event.args);
    }
    if (event.type === 'tool_execution_end') {
      inspect(()=>timing.toolEnd(event.toolCallId));
      const start = tools.get(event.toolCallId); tools.delete(event.toolCallId);
      record('tool/end', {name: event.toolName, toolCallId: event.toolCallId,...(event.parentToolCallId?{parentToolCallId:event.parentToolCallId}:{}), isError: event.isError,
        ...(start === undefined ? {} : {durationMs: performance.now() - start})}, event.result);
    }
    if (event.type === 'entry_appended' && event.entry.type === 'context_edit') {
      record('context/edit', {entryId: event.entry.id, targetId: event.entry.targetId}, event.entry);
    }
    if(event.type==='compaction_start'||event.type==='compaction_end'){
      inspect(()=>{const data:Data={reason:event.reason,...(current().compactionId?{operationId:current().compactionId}:{})};
        if(event.type==='compaction_end')Object.assign(data,{aborted:event.aborted,willRetry:event.willRetry,returnedSummary:!!event.result,...(event.result?{tokensBefore:event.result.tokensBefore,estimatedTokensAfter:event.result.estimatedTokensAfter}:{})});
        notify(store.append(sessionId,event.type.replaceAll('_','/'),data,event.reason==='manual'?{}:{turnId:current().turnId},event));
      });
    }
    if (event.type === 'auto_retry_start' || event.type === 'auto_retry_end') {
      record(event.type.replaceAll('_', '/'), {}, event);
    }
    if(event.type==='turn_end')inspect(()=>{const result=timing.end();if(result)record('step/end',result);});
    if(event.type==='agent_end')inspect(()=>{const incomplete=timing.abandon('agent-ended-without-sdk-turn-end');if(incomplete)record('step/incomplete',incomplete);});
  });
  return {record:(kind:string,data:Record<string,unknown>,payload?:unknown)=>{if(kind==='turn/end')inspect(()=>{const incomplete=timing.abandon('host-turn-ended-without-sdk-turn-end');if(incomplete)record('step/incomplete',incomplete);});return record(kind,data,payload);},waiting:(id:string,kind:string,active:boolean)=>inspect(()=>timing.wait(id,kind,active)),currentRequestId:()=>requestId, beginTurn(data: Record<string, unknown>) {
    inspect(()=>{const incomplete=timing.abandon('superseded-by-host-turn');if(incomplete)record('step/incomplete',incomplete);});
    requestId = undefined; started = 0; firstToken = false;
    requestedThinking=undefined;
    provenance?.beginTurn();
    resetProvider(); requestOpen = false;
    return record('turn/start', data);
  }, dispose() {
    inspect(()=>{const incomplete=timing.abandon('observer-disposed-without-sdk-turn-end');if(incomplete)record('step/incomplete',incomplete);});
    unsubscribe();
    if (session.agent.onPayload === payloadHook) session.agent.onPayload = previousPayload;
    if (session.agent.onResponse === responseHook) session.agent.onResponse = previousResponse;
    if (session.agent.onProviderStreamEvent === providerHook) session.agent.onProviderStreamEvent = previousProvider;
    if (session.agent.streamFunction === streamHook) session.agent.streamFunction=previousStream;
    if (session.agent.transformContext === transformHook) session.agent.transformContext=previousTransform;
    provenance?.dispose();
    providerEvents = [];
  }};
}
