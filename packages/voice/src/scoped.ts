// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {lstatSync, readFileSync} from 'node:fs';
import {join} from 'node:path';
import {homedir} from 'node:os';
import {randomUUID} from 'node:crypto';

type Data = Record<string, any>;
export interface VoiceConnection {base: string; token: string}
export function voiceConnection(): VoiceConnection {
  const home = process.env.RESONANT_VOICE_HOME ?? join(process.env.XDG_CONFIG_HOME ?? join(homedir(), '.config'), 'resonant-voice');
  const read = (name: string, limit: number) => {
    const path = join(home, name), stat = lstatSync(path);
    if (!stat.isFile() || stat.isSymbolicLink() || stat.size > limit || stat.mode & 0o077 || process.getuid && stat.uid !== process.getuid()) throw new Error('Private voice configuration is required.');
    return readFileSync(path, 'utf8');
  };
  const config = JSON.parse(read('config.json', 65536)), token = read('token', 128).trim();
  if (!Number.isInteger(config.port ?? 8877) || (config.port ?? 8877) < 1024 || config.port > 65535 || !/^[a-f0-9]{64}$/.test(token)) throw new Error('Invalid voice connection configuration.');
  return {base: `http://127.0.0.1:${config.port ?? 8877}`, token};
}
interface Item {stream: string; text: string; pending: string; done: boolean; timer?: ReturnType<typeof setTimeout>}
interface Lease {
  session: string; connection: VoiceConnection; bridgeId: string; seq: number; epoch: number; pending: number; bytes: number;
  chain: Promise<void>; timer?: ReturnType<typeof setInterval>; request?: string; turn?: string; items: Map<string, Item>; closed: boolean;
}
/** Only a live, explicitly opened speech lease receives public native events. */
export class ScopedVoice {
  protected leases = new Map<string, Lease>();
  private opening = new Set<string>();
  private closed = false;
  constructor(private harness: 'codex' | 'pi', private connection: () => VoiceConnection = voiceConnection, private warn: (session: string, message: string) => void = () => {}) {}
  get active(): boolean {return this.leases.size > 0 || this.opening.size > 0;}
  owns(session: string): boolean {return this.leases.has(session) || this.opening.has(session);}
  private async http(connection: VoiceConnection, path: string, body?: Data): Promise<Data> {
    // Validate even injected/test configuration before attaching a local service credential.
    const url = new URL(connection.base);
    if (url.protocol !== 'http:' || url.hostname !== '127.0.0.1' || !url.port || url.username || url.password || url.search || url.hash || url.pathname !== '/') throw new Error('Voice requires its explicit loopback endpoint.');
    try {
      const response = await fetch(connection.base + path, {method: body ? 'POST' : 'GET', redirect: 'error', signal: AbortSignal.timeout(2500),
        headers: body ? {'content-type': 'application/json', 'x-resonant-token': connection.token} : {}, ...(body ? {body: JSON.stringify(body)} : {})});
      if (!response.ok) throw new Error('Voice service rejected the operation.');
      let content = ''; for await (const chunk of response.body as any) {content += Buffer.from(chunk).toString(); if (Buffer.byteLength(content) > 65536) throw new Error('Oversized');}
      return JSON.parse(content);
    } catch {throw new Error('Resonant Voice did not confirm the operation. Reconnect voice; speech was not replayed.');}
  }
  async ticket(session: string, surface: 'linux' | 'browser'): Promise<Data> {
    if (this.closed || this.owns(session)) throw new Error('Voice is already opening or connected. Close it before reconnecting.');
    this.opening.add(session);
    try {
      const connection = this.connection();
      const health = await this.http(connection, '/health');
      if (health.protocol !== 'resonant-voice/1' || health.capabilities?.scopedHarnessBridge !== 1) throw new Error('Voice requires Resonant Voice with its scoped harness bridge (Codex: 0.1.17).');
      if (this.harness === 'pi' && (!Array.isArray(health.capabilities?.scopedHarnesses) || !health.capabilities.scopedHarnesses.includes('pi'))) throw new Error('Pi voice requires a companion that explicitly advertises its scoped Pi bridge.');
      const result = await this.http(connection, '/internal/ticket', {sessionId: session, surface, harness: this.harness});
      if (result.protocol !== 'resonant-voice/1' || result.sessionId !== session || result.url !== connection.base.replace('http:', 'ws:') + '/voice' ||
          !/^[a-f0-9]{64}$/.test(result.ticket) || !/^[a-f0-9]{64}$/.test(result.bridgeId) || result.bridgeLeaseMs !== 8000) throw new Error('Incompatible scoped voice ticket.');
      if (this.closed) throw new Error('Voice is closing.');
      const lease: Lease = {session, connection, bridgeId: result.bridgeId, seq: 0, epoch: 0, pending: 0, bytes: 0, chain: Promise.resolve(), items: new Map(), closed: false};
      this.leases.set(session, lease);
      lease.timer = setInterval(() => this.enqueue(lease, {type: 'heartbeat'}), 2000); lease.timer.unref();
      return {protocol: result.protocol, sessionId: session, url: result.url, ticket: result.ticket};
    } finally {this.opening.delete(session);}
  }
  protected clearItems(lease: Lease): void {for (const item of lease.items.values()) clearTimeout(item.timer); lease.items.clear();}
  private forget(lease: Lease): void {
    lease.closed = true; clearInterval(lease.timer); this.clearItems(lease);
    if (this.leases.get(lease.session) === lease) this.leases.delete(lease.session);
  }
  protected fail(lease: Lease): void {
    if (lease.closed) return;
    this.forget(lease);
    this.warn(lease.session, 'Voice delivery is unavailable. Reconnect voice; the conversation remains available.');
    // A higher sequence invalidates earlier in-flight speech. The service lease
    // also expires if this one-shot disconnect cannot be delivered.
    void this.send(lease, {type: 'disconnect'}).catch(() => {});
  }
  private async send(lease: Lease, event: Data, seq = ++lease.seq): Promise<Data> {
    return this.http(lease.connection, '/internal/event', {sessionId: lease.session, harness: this.harness, bridgeId: lease.bridgeId, seq, ...event});
  }
  protected enqueue(lease: Lease, event: Data): void {
    if (lease.closed) return;
    const bytes = Buffer.byteLength(JSON.stringify(event));
    if (lease.pending >= 128 || lease.bytes + bytes > 262144) {this.fail(lease); return;}
    const seq = ++lease.seq, epoch = lease.epoch; lease.pending++; lease.bytes += bytes;
    lease.chain = lease.chain.then(async () => {
      if (lease.closed || lease.epoch !== epoch) return;
      const result = await this.send(lease, event, seq);
      if (lease.closed || lease.epoch !== epoch) return;
      if (result.active === false && result.pending !== true) this.forget(lease);
      else if (result.ok !== true || result.ignored === true) this.fail(lease);
    }).catch(() => {if (lease.epoch === epoch) this.fail(lease);}).finally(() => {lease.pending--; lease.bytes -= bytes;});
  }
  protected flushItem(lease: Lease, item: Item): void {
    clearTimeout(item.timer); item.timer = undefined;
    if (!item.pending) return;
    for (let offset = 0; offset < item.pending.length; offset += 16000) this.enqueue(lease, {type: 'text', requestId: lease.request, stream: item.stream, text: item.pending.slice(offset, offset + 16000)});
    item.pending = '';
  }
  protected accept(session: string, request: string, turn: string): Lease | undefined {
    const lease = this.leases.get(session);
    if (!lease || lease.closed || lease.request === request) return;
    this.clearItems(lease); lease.request = request; lease.turn = turn;
    this.enqueue(lease, {type: 'user-turn', requestId: request});
    return lease;
  }
  protected startItem(lease: Lease, id: string): Item | undefined {
    let item = lease.items.get(id);
    if (!item) {
      if (lease.items.size >= 256) {this.fail(lease); return;}
      item = {stream: randomUUID(), text: '', pending: '', done: false}; lease.items.set(id, item);
      this.enqueue(lease, {type: 'start', requestId: lease.request, stream: item.stream});
    }
    return item;
  }
  protected deltaItem(lease: Lease, id: string, text: string): void {
    const item = lease.items.get(id); if (!item || item.done) return;
    item.text += text; item.pending += text;
    if (item.text.length > 262144) {this.fail(lease); return;}
    if (item.pending.length >= 16000) this.flushItem(lease, item);
    else if (!item.timer) item.timer = setTimeout(() => this.flushItem(lease, item), 25);
  }
  protected endItem(lease: Lease, id: string, text: unknown): void {
    const item = this.startItem(lease, id); if (!item || item.done) return;
    if (typeof text !== 'string' || !text.startsWith(item.text) || text.length > 262144) {this.fail(lease); return;}
    item.pending += text.slice(item.text.length); this.flushItem(lease, item); item.done = true; item.text = '';
    this.enqueue(lease, {type: 'end', requestId: lease.request, stream: item.stream});
  }
  finish(session: string, turn: string, completed: boolean): void {
    const lease = this.leases.get(session); if (!lease || lease.closed || lease.turn !== turn) return;
    if (completed) {
      for (const item of lease.items.values()) this.flushItem(lease, item);
      this.enqueue(lease, {type: 'turn-complete', requestId: lease.request});
    } else void this.stop(session);
    lease.turn = undefined; this.clearItems(lease);
  }
  async stop(session: string): Promise<void> {
    const lease = this.leases.get(session); if (!lease) return;
    lease.turn = undefined; lease.request = undefined; this.clearItems(lease);
    // A newer sequence invalidates older in-flight events without waiting for
    // their HTTP acknowledgment. Locally skip all queued events from that epoch.
    lease.epoch++;
    await this.send(lease, {type: 'cancel'}).catch(() => this.fail(lease));
  }
  async release(session: string): Promise<void> {
    const lease = this.leases.get(session); if (!lease) return;
    this.forget(lease); await this.send(lease, {type: 'disconnect'}).catch(() => {});
  }
  async close(): Promise<void> {this.closed = true; await Promise.all([...this.leases.keys()].map(id => this.release(id)));}
  async flush(): Promise<void> {await Promise.all([...this.leases.values()].map(lease => lease.chain));}
}
