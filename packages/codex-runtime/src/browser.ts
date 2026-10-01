// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {createHash} from 'node:crypto';
import {existsSync} from 'node:fs';
import {join} from 'node:path';
import {BrowserBroker, browserDefinitions} from '../../pi-browser/src/index.js';
import {durableJson, privateDirectory, readPrivateJson} from './storage.js';
import {type ToolReply, toolFailure as failure, validImageUrl} from './tool-content.js';

// Screenshot registration is bound to the new conversation after explicit profile qualification.
export const browserToolsFor = (imageInput = false) => browserDefinitions.filter(tool => imageInput || tool.action !== 'screenshot').map(tool => ({
  type: 'function', name: tool.name, description: tool.description,
  inputSchema: {...tool.parameters, additionalProperties: false},
}));
export const browserTools = browserToolsFor();
const digest = (value: string) => createHash('sha256').update(value).digest('hex');
const plain = (value: unknown): value is Record<string, any> => Boolean(value) && typeof value === 'object' && !Array.isArray(value);

/** Browser executor binding plus durable call admission; Codex still owns the agent loop. */
export class CodexBrowser {
  readonly broker = new BrowserBroker();
  private readable = new Map<string, {tabId: number; url: string; documentEpoch: number; selectors: string[]}>();
  private busy = new Set<string>();
  constructor(readonly timeoutMs = 20000) {}
  attach(session: string, owner: object, send: (message: unknown) => void): void {
    this.broker.attach(session, owner, send); this.readable.delete(session);
  }
  detach(owner: object): void {
    for (const [session, row] of this.broker.owners) if (row.owner === owner) this.readable.delete(session);
    this.broker.detach(owner);
  }
  cancel(session: string): void {
    this.readable.delete(session);
    for (const row of this.broker.pending.values()) if (row.sid === session) row.finish(new Error('Browser action interrupted. Outcome may be unknown; observe before any retry.'));
  }
  close(): void {for (const row of [...this.broker.owners.values()]) this.detach(row.owner);}
  respond(owner: object, id: string, result: unknown, error?: string): void {this.broker.respond(owner, id, result, error);}
  async call(session: string, root: string, request: Record<string, any>, signal: AbortSignal, imageInput = false): Promise<ToolReply> {
    const tool = browserDefinitions.find(value => value.name === request.tool && (imageInput || value.action !== 'screenshot'));
    if (!tool || request.namespace) return failure('Unknown or unsupported Augmentor browser tool.');
    const args = request.arguments;
    if (!plain(args) || Buffer.byteLength(JSON.stringify(args)) > 32768) return failure('Invalid or oversized browser arguments.');
    const keys = Object.keys(tool.parameters.properties);
    if (Object.keys(args).some(key => !keys.includes(key)) ||
        ((tool.parameters as {required?: string[]}).required ?? []).some(key => args[key] === undefined) ||
        (args.tabId !== undefined && (!Number.isInteger(args.tabId) || args.tabId < 0)) ||
        (args.selector !== undefined && (typeof args.selector !== 'string' || !args.selector.trim() || args.selector.length > 4096)) ||
        (args.text !== undefined && typeof args.text !== 'string') ||
        (args.url !== undefined && (typeof args.url !== 'string' || !/^https?:\/\//i.test(args.url)))) return failure('Invalid browser tool arguments.');
    if (![request.turnId, request.callId].every(value => typeof value === 'string' && value.length > 0 && value.length <= 512)) return failure('Invalid browser call identity.');
    const fingerprint = digest(JSON.stringify([request.tool, Object.keys(args).sort().map(key => [key, args[key]])]));
    privateDirectory(root);
    const path = join(root, digest(JSON.stringify([request.turnId, request.callId])) + '.json');
    if (existsSync(path)) {
      this.readable.delete(session); // Replayed observations never authorize a fresh action.
      const record = readPrivateJson(path) as any;
      if (record?.schema !== 1 || record.fingerprint !== fingerprint) return failure('Browser call identity changed; no action was dispatched.');
      if (record.status === 'completed' && Buffer.byteLength(JSON.stringify(record.reply ?? null)) <= 1000000 && typeof record.reply?.success === 'boolean' && Array.isArray(record.reply.contentItems) && record.reply.contentItems.every((item: any) => plain(item) && ((item.type === 'inputText' && typeof item.text === 'string') || (tool.action === 'screenshot' && item.type === 'inputImage' && validImageUrl(item.imageUrl))))) return record.reply;
      return failure('A prior browser dispatch has an unknown outcome. It was not retried; observe the page before continuing.');
    }
    if (this.busy.has(session)) return failure('Another browser call is pending. Wait for its result before acting.');
    if (signal.aborted) return failure('Browser call was cancelled before dispatch.');
    if (['click', 'type'].includes(tool.action) && !this.readable.has(session)) return failure('Read a fresh, successful browser snapshot before acting on this page.');
    const observed = this.readable.get(session);
    if (['click', 'type'].includes(tool.action) && !observed?.selectors.includes(args.selector)) return failure('Use an exact selector from the latest browser snapshot.');
    this.busy.add(session);
    const abort = new AbortController();
    const cancel = () => abort.abort(); signal.addEventListener('abort', cancel, {once: true});
    const timer = setTimeout(cancel, this.timeoutMs);
    try {
      durableJson(path, {schema: 1, fingerprint, status: 'dispatched'});
      if (['navigate', 'click', 'type'].includes(tool.action)) this.readable.delete(session);
      let reply: ToolReply;
      try {
        const value = await this.broker.execute(session, {action: tool.action, ...args, ...(['click', 'type'].includes(tool.action) && observed ? {target: {tabId: observed.tabId, url: observed.url, documentEpoch: observed.documentEpoch}} : {})}, abort.signal);
        if (!plain(value) || Buffer.byteLength(JSON.stringify(value)) > (tool.action === 'screenshot' ? 950000 : 262144) || (tool.action !== 'screenshot' && Object.hasOwn(value, 'image'))) throw new Error('Invalid or oversized browser result. Observe the page before continuing.');
        if (value.ok === false) throw new Error(typeof value.error === 'string' ? value.error.slice(0, 4096) : 'Browser observation or action failed.');
        if (['click', 'type'].includes(tool.action) && value.ok !== true) throw new Error('Browser action was not acknowledged. Outcome may be unknown; observe before any retry.');
        if (tool.action === 'tabs_list' && !Array.isArray(value.tabs)) throw new Error('No valid tab list was returned.');
        if (['snapshot', 'navigate', 'screenshot'].includes(tool.action) && (typeof value.url !== 'string' || !/^https?:\/\//i.test(value.url) || !Number.isInteger(value.tabId))) throw new Error('No verified browser target was returned.');
        if (tool.action === 'snapshot' && (value.ok !== true || !['readable', 'empty'].includes(value.observation))) throw new Error('No verified browser observation was returned.');
        if (tool.action === 'snapshot') {
          if (typeof value.url === 'string' && /^https?:\/\//i.test(value.url) && value.observation === 'readable' && Number.isInteger(value.tabId) && Number.isFinite(value.documentEpoch) && Array.isArray(value.controls)) this.readable.set(session, {tabId: value.tabId, url: value.url, documentEpoch: value.documentEpoch, selectors: value.controls.filter((control: any) => plain(control) && typeof control.selector === 'string' && control.disabled !== true).map((control: any) => control.selector)});
          else this.readable.delete(session);
        }
        if (tool.action === 'screenshot') {
          this.readable.delete(session); // Pixels never authorize DOM selectors.
          const imageUrl = value.image?.mimeType === 'image/jpeg' ? 'data:image/jpeg;base64,' + value.image.data : '';
          if (value.ok !== true || !validImageUrl(imageUrl)) throw new Error('Invalid browser screenshot.');
          const {image: _image, ...metadata} = value;
          reply = {success: true, contentItems: [{type: 'inputText', text: JSON.stringify(metadata)}, {type: 'inputImage', imageUrl}]};
        } else reply = {success: true, contentItems: [{type: 'inputText', text: JSON.stringify(value)}]};
      } catch (error) {
        this.readable.delete(session);
        reply = failure(error instanceof Error ? error.message.slice(0, 4096) : 'Browser call failed; its outcome may be unknown.');
      }
      durableJson(path, {schema: 1, fingerprint, status: 'completed', reply});
      return reply;
    } finally {clearTimeout(timer); signal.removeEventListener('abort', cancel); this.busy.delete(session);}
  }
}
