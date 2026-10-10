// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import type {AgentSession} from '@earendil-works/pi-coding-agent';
import {ObservationStore} from '../../observation/src/store.js';
import type {Data} from '../../protocol/src/index.js';

/** Observe the supported SDK pipeline after all registered payload transforms. */
export function observeSession(session: AgentSession, store: ObservationStore, sessionId: string,
  current: () => {turnId?: string; selected: Data}, notify: (event: unknown) => void,
  warning: (message: string) => void) {
  let requestId: string | undefined;
  let started = 0, firstToken = false;
  const tools = new Map<string, number>();
  const record = (kind: string, data: Record<string, unknown>, payload?: unknown) => {
    try {
      const event = store.append(sessionId, kind, data, {turnId: current().turnId, requestId}, payload);
      notify(event); return event;
    } catch (error) {warning('Local inspection could not record an observation: ' + String(error));}
  };
  const previousPayload = session.agent.onPayload;
  const payloadHook: typeof previousPayload = async (payload, model) => {
    const transformed = await previousPayload?.(payload, model);
    const effective = transformed === undefined ? payload : transformed;
    started = performance.now(); firstToken = false; requestId = undefined;
    const event = record('model/request', {
      selected: current().selected, model: model.id, provider: model.provider, api: model.api,
      thinkingLevel: session.thinkingLevel, capacity: model.contextWindow,
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
  const unsubscribe = session.subscribe(event => {
    if (event.type === 'message_start' && event.message.role === 'user') {
      record('user/message', {role: 'user'}, event.message);
    }
    if (event.type === 'message_update' && requestId && !firstToken &&
      ['text_delta', 'thinking_delta', 'toolcall_delta'].includes(event.assistantMessageEvent.type)) {
      firstToken = true; record('model/firstToken', {elapsedMs: performance.now() - started});
    }
    if (event.type === 'message_end' && event.message.role === 'assistant') {
      record('model/complete', {stopReason: event.message.stopReason, usage: event.message.usage,
        usageBoundary: 'sdk-normalized; zero fields may be unavailable',
        ...(requestId && started > 0 ? {durationMs: performance.now() - started} : {}), model: event.message.model, provider: event.message.provider},
      event.message);
    }
    if (event.type === 'tool_execution_start') {
      tools.set(event.toolCallId, performance.now());
      record('tool/start', {name: event.toolName, toolCallId: event.toolCallId}, event.args);
    }
    if (event.type === 'tool_execution_end') {
      const start = tools.get(event.toolCallId); tools.delete(event.toolCallId);
      record('tool/end', {name: event.toolName, toolCallId: event.toolCallId, isError: event.isError,
        ...(start === undefined ? {} : {durationMs: performance.now() - start})}, event.result);
    }
    if (event.type === 'compaction_start' || event.type === 'compaction_end' ||
      event.type === 'auto_retry_start' || event.type === 'auto_retry_end') {
      record(event.type.replaceAll('_', '/'), {}, event);
    }
  });
  return {record, beginTurn(data: Record<string, unknown>) {
    requestId = undefined; started = 0; firstToken = false;
    return record('turn/start', data);
  }, dispose() {
    unsubscribe();
    if (session.agent.onPayload === payloadHook) session.agent.onPayload = previousPayload;
    if (session.agent.onResponse === responseHook) session.agent.onResponse = previousResponse;
  }};
}
