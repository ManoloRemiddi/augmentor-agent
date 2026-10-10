// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import type {AgentSession} from '@earendil-works/pi-coding-agent';
import {ObservationStore,payloadText} from '../../observation/src/store.js';
import type {Data} from '../../protocol/src/index.js';

/** Observe the supported SDK pipeline after all registered payload transforms. */
export function observeSession(session: AgentSession, store: ObservationStore, sessionId: string,
  current: () => {turnId?: string; selected: Data; permissionPreset?: string; toolBudget?: Data;execution?:Data}, notify: (event: unknown) => void,
  warning: (message: string) => void) {
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
  const record = (kind: string, data: Record<string, unknown>, payload?: unknown) => {
    try {
      const event = store.append(sessionId, kind, data, {turnId: current().turnId, requestId:kind.startsWith('execution/')?undefined:requestId}, payload);
      notify(event); return event;
    } catch (error) {warning('Local inspection could not record an observation: ' + String(error));}
  };
  const previousPayload = session.agent.onPayload;
  const payloadHook: typeof previousPayload = async (payload, model) => {
    const transformed = await previousPayload?.(payload, model);
    const effective = transformed === undefined ? payload : transformed;
    started = performance.now(); firstToken = false; requestId = undefined;
    resetProvider(); requestOpen = true;
    const event = record('model/request', {
      selected: current().selected, model: model.id, provider: model.provider, api: model.api,
      thinkingLevel: session.thinkingLevel, capacity: model.contextWindow,
      policies: {permissionPreset: current().permissionPreset, toolBudget: current().toolBudget,execution:current().execution},
      boundary: 'provider-payload-after-hooks', transportAttempts: 'not-observed',
    }, effective);
    requestId = event?.id;
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
      const observedProviderCount = providerCount;
      if (providerCount) record('provider/stream', {boundary: 'parsed-provider-events-after-hooks-before-normalization',
        observedEvents: providerCount, capturedEvents: providerEvents.length, droppedEvents: providerDropped,
        coverage: !captureProvider ? 'disabled-at-request-start' : providerDropped ? 'partial' : 'complete',
        credentialRedactions: [...providerRedactions], maxCaptureBytes: 8 * 1024 * 1024,
        timings: started ? 'monotonic milliseconds since managed request hook' : 'not-observed'},
      {events: providerEvents});
      providerEvents = []; providerBytes = 0; providerCount = 0;
      record('model/complete', {stopReason: event.message.stopReason, usage: event.message.usage,
        usageBoundary: 'sdk-normalized; zero fields may be unavailable',
        requestCoverage: requestId ? 'observed-after-hooks' : 'not-observed',
        providerEventCoverage: observedProviderCount ? 'observed' : 'not-observed',
        ...(requestId && started > 0 ? {durationMs: performance.now() - started} : {}), model: event.message.model, provider: event.message.provider},
      event.message);
      requestOpen = false;
    }
    if (event.type === 'tool_execution_start') {
      tools.set(event.toolCallId, performance.now());
      record('tool/start', {name: event.toolName, toolCallId: event.toolCallId,boundary:'proposed-before-validation'}, event.args);
    }
    if (event.type === 'tool_execution_end') {
      const start = tools.get(event.toolCallId); tools.delete(event.toolCallId);
      record('tool/end', {name: event.toolName, toolCallId: event.toolCallId, isError: event.isError,
        ...(start === undefined ? {} : {durationMs: performance.now() - start})}, event.result);
    }
    if (event.type === 'entry_appended' && event.entry.type === 'context_edit') {
      record('context/edit', {entryId: event.entry.id, targetId: event.entry.targetId}, event.entry);
    }
    if (event.type === 'compaction_start' || event.type === 'compaction_end' ||
      event.type === 'auto_retry_start' || event.type === 'auto_retry_end') {
      record(event.type.replaceAll('_', '/'), {}, event);
    }
  });
  return {record, beginTurn(data: Record<string, unknown>) {
    requestId = undefined; started = 0; firstToken = false;
    resetProvider(); requestOpen = false;
    return record('turn/start', data);
  }, dispose() {
    unsubscribe();
    if (session.agent.onPayload === payloadHook) session.agent.onPayload = previousPayload;
    if (session.agent.onResponse === responseHook) session.agent.onResponse = previousResponse;
    if (session.agent.onProviderStreamEvent === providerHook) session.agent.onProviderStreamEvent = previousProvider;
    providerEvents = [];
  }};
}
