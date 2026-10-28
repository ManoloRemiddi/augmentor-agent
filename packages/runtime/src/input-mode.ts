// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import type {AgentSession} from '@earendil-works/pi-coding-agent';
import {inputModeInstructions, type InputMode} from '../../prompt-library/src/input-mode.js';
export type {InputMode} from '../../prompt-library/src/input-mode.js';
export function promptInputMode(value: unknown): InputMode {
  if (value === undefined || value === 'text') return 'text';
  if (value === 'voice') return 'voice';
  throw Error('Choose typed or spoken input mode.');
}
export const spokenRequestId = (value: string) => /^resonant-voice:[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/.test(value);
export interface DeliveredInput {requestId: string; mode: InputMode; voiceSeen: boolean}
export interface InputModeContribution {boundary: 'managed-Pi-stream-request-copy-after-system-projection'; source: 'delivered-human-input'; requestId: string; mode: InputMode; state: 'applied' | 'unavailable-no-leading-system-message'; section?: string; text: string}
type RequestContext = Parameters<AgentSession['agent']['streamFunction']>[1];
/** A request copy only: it does not alter native messages, tools or permissions. */
export function piInputMode(read: () => DeliveredInput | undefined, observe?: (row: InputModeContribution) => void): (context: RequestContext) => RequestContext {
  return context => {
    const input = read(); if (!input || input.mode === 'text' && !input.voiceSeen) return context;
    const text = inputModeInstructions(input.requestId, input.mode), first = context.messages[0];
    const row: InputModeContribution = {boundary: 'managed-Pi-stream-request-copy-after-system-projection', source: 'delivered-human-input', requestId: input.requestId, mode: input.mode, state: 'unavailable-no-leading-system-message', text};
    let messages;
    if (first?.role === 'system') {
      const used = new Set(context.messages.flatMap(message => message.role === 'system' ? Object.keys(message.sections ?? {}) : []));
      let section = 'augmentor:input-mode', ordinal = 0; while (used.has(section)) section = 'augmentor:input-mode:' + ++ordinal;
      messages = context.messages.slice(); messages[0] = {...first, sections: {...first.sections, [section]: text}};
      row.state = 'applied'; row.section = section;
    }
    try {observe?.(row);} catch {/* Observation cannot change composition. */}
    return messages ? {...context, messages} : context;
  };
}
