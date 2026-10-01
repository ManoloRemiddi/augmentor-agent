// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {createHash} from 'node:crypto';
import {existsSync} from 'node:fs';
import {join} from 'node:path';
import {definitions, homeTool, homeRequestOwned} from '../../home-client/src/index.js';
import {durableJson, privateDirectory, readPrivateJson} from './storage.js';
import {toolFailure, type ToolReply} from './tool-content.js';

export const homeTools = definitions.map(d => ({type: 'function', name: d.name,
  description: d.name === 'home_cancel' ? 'Request cancellation of a Home request submitted by this conversation, using its returned request_id. Cancellation cannot undo an action; inspect home_result. Requires a server with request-specific cancellation.' : d.description,
  inputSchema: d.name === 'home_cancel' ? {type: 'object', properties: {request_id: {type: 'string', pattern: '^[a-zA-Z0-9_-]{1,100}$'}}, required: ['request_id'], additionalProperties: false} : d.parameters,
}));
const hash = (s: string) => createHash('sha256').update(s).digest('hex');
const plain = (v: any) => v && typeof v === 'object' && !Array.isArray(v);

/** Existing NAS client owns execution/receipts; Codex only translates dynamic calls. */
export class CodexHome {
  private busy = new Set<string>();
  async call(session: string, root: string, request: Record<string, any>, signal: AbortSignal): Promise<ToolReply> {
    const tool = homeTools.find(d => d.name === request.tool), args = request.arguments;
    if (!tool || request.namespace || !plain(args) || Buffer.byteLength(JSON.stringify(args)) > 20000) return toolFailure('Invalid Home tool or arguments.');
    const keys = Object.keys(tool.inputSchema.properties);
    if (Object.keys(args).some(key => !keys.includes(key)) ||
        ((tool.inputSchema as {required?: string[]}).required ?? []).some(key => args[key] === undefined) ||
        (args.prompt !== undefined && (typeof args.prompt !== 'string' || !args.prompt.trim() || args.prompt.length > 4000)) ||
        (args.request_id !== undefined && (typeof args.request_id !== 'string' || !/^[a-zA-Z0-9_-]{1,100}$/.test(args.request_id))) ||
        (args.entity_id !== undefined && (typeof args.entity_id !== 'string' || !/^[a-z_]+\.[a-z0-9_]+$/.test(args.entity_id))) ||
        (args.action !== undefined && !['on', 'off', 'brightness'].includes(args.action)) ||
        (args.brightness_pct !== undefined && (!Number.isInteger(args.brightness_pct) || args.brightness_pct < 1 || args.brightness_pct > 100)) ||
        (args.action === 'brightness' && args.brightness_pct === undefined)) return toolFailure('Invalid Home tool arguments.');
    if (![request.turnId, request.callId].every(v => typeof v === 'string' && v.length > 0 && v.length <= 512)) return toolFailure('Invalid Home call identity.');
    const owner = 'codex:' + session;
    if (args.request_id && !homeRequestOwned(owner, args.request_id)) return toolFailure('That Home request is not owned by this conversation. No request was dispatched.');
    privateDirectory(root);
    const call = hash(JSON.stringify([request.turnId, request.callId]));
    const path = join(root, call + '.json');
    const fingerprint = hash(JSON.stringify([request.tool, Object.keys(args).sort().map(key => [key, args[key]])]));
    if (existsSync(path)) {
      const saved = readPrivateJson(path) as any;
      if (saved?.schema !== 1 || saved.fingerprint !== fingerprint) return toolFailure('Home call identity changed; no action was dispatched.');
      if (saved.status === 'completed' && typeof saved.reply?.success === 'boolean' && Array.isArray(saved.reply.contentItems) && saved.reply.contentItems.every((item: any) => item.type === 'inputText' && typeof item.text === 'string') && Buffer.byteLength(JSON.stringify(saved.reply)) <= 1048576) return saved.reply;
      return toolFailure('A prior Home call has an unknown outcome and was not retried. Inspect the NAS request history before another action.');
    }
    if (signal.aborted) return toolFailure('Home call cancelled before dispatch.');
    if (this.busy.has(session)) return toolFailure('Another Home call is pending in this conversation. Wait for its result.');
    this.busy.add(session);
    try {
      durableJson(path, {schema: 1, fingerprint, status: 'dispatched'});
      const value = await homeTool(request.tool, args, owner, call, signal);
      const text = JSON.stringify(value);
      if (Buffer.byteLength(text) > 1000000) throw new Error('Oversized Home result');
      const reply: ToolReply = {success: true, contentItems: [{type: 'inputText', text}]};
      durableJson(path, {schema: 1, fingerprint, status: 'completed', reply});
      return reply;
    } catch {
      return toolFailure('Home call could not be confirmed. An admitted NAS request may still be running. Inspect its outcome; do not repeat the action.');
    } finally {this.busy.delete(session);}
  }
}
