// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import type {CodexConnection} from './config.js';
import {runtimeOptions} from './config.js';
import {imageChallenge} from './image-check.js';

/** Explicit user-requested provider check. No tools, private instructions or history are sent. */
export async function checkProvider(connection: CodexConnection, timeoutMs = 45000, capability: 'text' | 'image' = 'text'): Promise<{valid: true; validation: 'responses-text' | 'responses-image'}> {
  runtimeOptions(connection, '/unused-codex-check', '/');
  if (!['api', 'local'].includes(connection.kind) || !connection.endpoint) throw new Error('This connection check currently supports API and local profiles.');
  const challenge = capability === 'image' ? imageChallenge() : undefined;
  const content: Record<string, unknown>[] = challenge ? [
    {type: 'input_text', text: 'Read the four colored squares from left to right. Return only four lower-case color names separated by commas. Allowed names: red, green, blue, yellow, black, white. Ignore the gray borders.'},
    {type: 'input_image', image_url: challenge.url},
  ] : [{type: 'input_text', text: 'Reply briefly with OK. This is a connection check.'}];
  const url = connection.endpoint.replace(/\/$/, '') + '/responses';
  let response: Response;
  try {
    response = await fetch(url, {method: 'POST', redirect: 'error', signal: AbortSignal.timeout(timeoutMs),
      headers: {'content-type': 'application/json', ...(connection.credential ? {Authorization: `Bearer ${connection.credential}`} : {})},
      body: JSON.stringify({model: connection.model, stream: true, store: false, input: [{role: 'user', content}]}),
    });
  } catch {throw new Error('The Responses endpoint did not accept the connection. Check its URL, TLS and availability.');}
  if (!response.ok || !response.body) {await response.body?.cancel(); throw new Error(`The provider rejected the connection check (HTTP ${response.status}). Check the model and credential.`);}
  const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = ''; let characters = 0; let textSeen = false; let answer = '';
  try {
    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, {stream: true});
      if (Buffer.byteLength(buffer) > 1024 * 1024) throw new Error('The provider sent an oversized connection-check frame.');
      let boundary;
      while ((boundary = /\r?\n\r?\n/.exec(buffer))) {
        const end = boundary.index; const width = boundary[0].length;
        const frame = buffer.slice(0, end); buffer = buffer.slice(end + width);
        const data = frame.split(/\r?\n/).filter(line => line.startsWith('data:')).map(line => line.slice(5).trimStart()).join('\n');
        if (!data || data === '[DONE]') continue;
        let event;
        try {event = JSON.parse(data);} catch {throw new Error('The provider returned invalid Responses streaming data.');}
        if (event.type === 'error' || event.type === 'response.failed') throw new Error('The provider could not complete the connection check. Check model compatibility and account limits.');
        if (event.type === 'response.output_text.delta' && typeof event.delta === 'string') {characters += event.delta.length; answer += event.delta; textSeen ||= Boolean(event.delta.trim());}
        if (characters > 65536) throw new Error('The connection check exceeded its output limit.');
        if (event.type === 'response.completed') {
          textSeen ||= event.response?.output?.some((item: any) => item.type === 'message' && item.content?.some((part: any) => part.type === 'output_text' && typeof part.text === 'string' && part.text.trim()));
          if (event.response?.status !== 'completed' || !textSeen) throw new Error('The model did not complete a text response.');
          const completed = event.response?.output?.filter((item: any) => item.type === 'message').flatMap((item: any) => item.content ?? []).filter((part: any) => part.type === 'output_text' && typeof part.text === 'string').map((part: any) => part.text).join('');
          if (challenge && (completed || answer).trim().toLowerCase().split(/\s*,\s*/).join(',') !== challenge.answer) throw new Error('The model did not identify the test image correctly. Image input was not enabled.');
          return {valid: true, validation: challenge ? 'responses-image' : 'responses-text'};
        }
      }
    }
    throw new Error('The provider stream ended without a completed text response.');
  } catch (error) {
    if (error instanceof DOMException) throw new Error('The provider connection check was interrupted or timed out.');
    throw error;
  } finally {await reader.cancel().catch(() => {});}
}
