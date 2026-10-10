// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {createServer, type IncomingMessage, type ServerResponse} from 'node:http';
import {randomBytes, timingSafeEqual} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {MAX_FRAME, identifier, request, type Data} from '../../protocol/src/index.js';
import type {Host} from './host.js';

const allowed = new Set([
  'host.describe', 'models.list', 'models.validate', 'setup.test', 'setup.cancel', 'setup.save',
  'session.list', 'session.create', 'session.history', 'session.models', 'session.selectModel',
  'session.reasoning', 'session.selectReasoning', 'reasoning.describe', 'reasoning.configure',
  'session.prompt', 'session.cancel', 'session.branch', 'session.rename', 'session.trimTools', 'chats.saved',
  'session.queue', 'session.updateQueue', 'session.continueQueue', 'session.resolveQueue',
  'observation.describe', 'observation.configure', 'observation.list', 'observation.payload', 'observation.clear',
  'settings.describe', 'settings.mutate', 'prompts.list', 'prompts.save', 'prompts.delete', 'prompts.improvementSave', 'interaction.respond',
]);
interface Watch {sessionId: string; seen: number}
interface LiveFrame {seq: number; sessionId: string; frame: Data}
const LIVE_BYTES = 16 * 1024 * 1024;

/** A local client of the existing Host. It never creates a second session owner. */
export class HarnessServer {
  readonly token = randomBytes(32).toString('hex');
  readonly watches = new Map<string, Watch>();
  private frames: (LiveFrame & {bytes: number})[] = [];
  private frameBytes = 0;
  private evicted = new Map<string, number>();
  private sequence = 0;
  private base = '';
  private server = createServer((req, res) => void this.handle(req, res));
  constructor(readonly host: Host, readonly assets = fileURLToPath(new URL('../../../apps/harness/', import.meta.url))) {}
  async start(port = 0) {
    if (!Number.isInteger(port) || port < 0 || port > 65535) throw new Error('Invalid Harness port');
    await new Promise<void>((resolve, reject) => {
      this.server.once('error', reject);
      this.server.listen(port, '127.0.0.1', () => {this.server.off('error', reject); resolve();});
    });
    const address = this.server.address();
    if (!address || typeof address === 'string') throw new Error('Harness has no loopback listener');
    this.base = 'http://127.0.0.1:' + address.port;
    return {url: this.base + '/#token=' + this.token, origin: this.base};
  }
  connected(sessionId: string) {
    const now = Date.now();
    for (const [clientId, watch] of this.watches) {
      if (now - watch.seen > 15000) this.watches.delete(clientId);
    }
    return [...this.watches.values()].some(watch => watch.sessionId === sessionId);
  }
  publish(sessionId: string, frame: Data) {
    const item = {seq: ++this.sequence, sessionId, frame, bytes: Buffer.byteLength(JSON.stringify(frame)) + 256};
    if (item.bytes > MAX_FRAME - 4096) {this.evicted.set(sessionId, item.seq); return;}
    this.frames.push(item); this.frameBytes += item.bytes;
    while (this.frames.length > 4096 || this.frameBytes > LIVE_BYTES) {
      const removed = this.frames.shift()!; this.frameBytes -= removed.bytes;
      this.evicted.set(removed.sessionId, Math.max(this.evicted.get(removed.sessionId) ?? 0, removed.seq));
    }
  }
  private authenticated(req: IncomingMessage) {
    const value = req.headers.authorization;
    if (!value?.startsWith('Bearer ')) return false;
    const supplied = Buffer.from(value.slice(7)), expected = Buffer.from(this.token);
    return supplied.length === expected.length && timingSafeEqual(supplied, expected);
  }
  private send(res: ServerResponse, status: number, value: unknown) {
    const raw = JSON.stringify(value);
    if (Buffer.byteLength(raw) > MAX_FRAME) throw new Error('Response exceeds the connection limit; request a smaller page');
    res.writeHead(status, {'Content-Type': 'application/json; charset=utf-8'});
    res.end(raw);
  }
  private async body(req: IncomingMessage) {
    let size = 0; const chunks: Buffer[] = [];
    for await (const chunk of req) {
      size += chunk.length;
      if (size > MAX_FRAME) throw new Error('Request exceeds the local connection limit');
      chunks.push(Buffer.from(chunk));
    }
    return JSON.parse(Buffer.concat(chunks).toString('utf8'));
  }
  private async handle(req: IncomingMessage, res: ServerResponse) {
    res.setHeader('Cache-Control', 'no-store');
    res.setHeader('X-Content-Type-Options', 'nosniff');
    res.setHeader('Referrer-Policy', 'no-referrer');
    res.setHeader('Cross-Origin-Resource-Policy', 'same-origin');
    res.setHeader('Content-Security-Policy', "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; base-uri 'none'; frame-ancestors 'none'");
    try {
      if (!this.base || req.headers.host !== new URL(this.base).host ||
        (req.headers.origin !== undefined && req.headers.origin !== this.base)) {
        this.send(res, 403, {error: {message: 'This client origin is not authorized'}}); return;
      }
      const url = new URL(req.url ?? '/', this.base);
      if (url.origin !== this.base) {this.send(res, 403, {error: {message: 'Invalid request origin'}}); return;}
      if (url.pathname.startsWith('/api/')) {
        if (!this.authenticated(req)) {this.send(res, 401, {error: {message: 'Open the private Harness link to connect'}}); return;}
        if (req.method === 'GET' && url.pathname === '/api/events') {
          const sessionId = identifier(url.searchParams.get('sessionId'));
          const clientId = identifier(url.searchParams.get('clientId'));
          this.host.getMeta(sessionId);
          const watch = this.watches.get(clientId);
          if (!watch || watch.sessionId !== sessionId) throw new Error('Subscribe to this session before polling');
          watch.seen = Date.now();
          const after = Number(url.searchParams.get('after') ?? 0);
          if (!Number.isSafeInteger(after) || after < 0) throw new Error('Invalid live event cursor');
          const eligible = this.frames.filter(frame => frame.sessionId === sessionId && frame.seq > after);
          const frames: LiveFrame[] = []; let bytes = 0;
          for (const item of eligible) {
            if (frames.length >= 100 || bytes + item.bytes > MAX_FRAME - 4096) break;
            bytes += item.bytes; frames.push({seq: item.seq, sessionId: item.sessionId, frame: item.frame});
          }
          this.send(res, 200, {frames, cursor: frames.at(-1)?.seq ?? this.sequence, hasMore: eligible.length > frames.length,
            gap: after < (this.evicted.get(sessionId) ?? 0)});
          return;
        }
        if (req.method === 'POST' && url.pathname === '/api/rpc') {
          const rpc: unknown = await this.body(req); request(rpc);
          const params = rpc.params ?? {};
          if (rpc.method === 'events.subscribe') {
            const sessionId = identifier(params.sessionId), clientId = identifier(params.clientId);
            this.host.getMeta(sessionId);
            this.watches.set(clientId, {sessionId, seen: Date.now()});
            this.send(res, 200, {id: rpc.id, result: {subscribed: true, cursor: this.sequence,
              queue:{sessionId,...this.host.queueSnapshot(sessionId)},pending: this.host.interactions.frames(sessionId)}});
            return;
          }
          if (!allowed.has(rpc.method)) throw new Error('Method is not exposed by Augmentor Harness');
          if (rpc.method === 'interaction.respond') {
            const watch = this.watches.get(identifier(params.clientId));
            if (!watch || watch.sessionId !== params.sessionId) throw new Error('Interaction belongs to another session');
            watch.seen = Date.now();
          }
          const result = await this.host.dispatch(rpc.method, params, rpc.id);
          this.send(res, 200, {id: rpc.id, result}); return;
        }
        this.send(res, 404, {error: {message: 'Unknown Harness API'}}); return;
      }
      if (req.method !== 'GET') {this.send(res, 405, {error: {message: 'Use GET for interface assets'}}); return;}
      const staticFiles = new Map([
        ['/', {path: join(this.assets, 'index.html'), type: 'text/html'}],
        ['/app.js', {path: join(this.assets, 'app.js'), type: 'text/javascript'}],
        ['/chat-projection.js', {path: join(this.assets, 'chat-projection.js'), type: 'text/javascript'}],
        ['/message-actions.js', {path: join(this.assets, 'message-actions.js'), type: 'text/javascript'}],
        ['/prompt-library.js', {path: join(this.assets, 'prompt-library.js'), type: 'text/javascript'}],
        ['/reasoning.js', {path: join(this.assets, 'reasoning.js'), type: 'text/javascript'}],
        ['/queue-view.js', {path: fileURLToPath(new URL('../../harness-ui/src/queue-view.js', import.meta.url)), type: 'text/javascript'}],
        ['/harness.css', {path: join(this.assets, 'harness.css'), type: 'text/css'}],
        ['/timeline.js', {path: fileURLToPath(new URL('../../harness-ui/src/dsh-timeline.js', import.meta.url)), type: 'text/javascript'}],
        ['/trajectory-contract.js', {path: fileURLToPath(new URL('../../harness-ui/src/trajectory-contract.js', import.meta.url)), type: 'text/javascript'}],
      ]);
      // Fixed, reviewed presentation assets; never expose arbitrary extension files.
      for(const name of ['prompt-library.mjs','prompt-editor.mjs','clipboard.mjs','settings-form.mjs','maintenance-page.mjs','prompt-library.css']){
        staticFiles.set('/shared-prompts/'+name,{path:fileURLToPath(new URL('../../../apps/browser/extension/'+name,import.meta.url)),type:name.endsWith('.css')?'text/css':'text/javascript'});
      }
      const file = staticFiles.get(url.pathname);
      if (!file) {this.send(res, 404, {error: {message: 'Unknown interface asset'}}); return;}
      const bytes = readFileSync(file.path);
      res.writeHead(200, {'Content-Type': file.type + '; charset=utf-8'}); res.end(bytes);
    } catch (error) {
      if (res.headersSent) {res.destroy(); return;}
      this.send(res, 400, {error: {message: error instanceof Error ? error.message : 'Harness request failed'}});
    }
  }
  async close() {
    this.watches.clear(); this.frames = []; this.frameBytes = 0; this.evicted.clear();
    await new Promise<void>(resolve => {this.server.close(() => resolve()); this.server.closeAllConnections();});
  }
}
