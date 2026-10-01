// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {lstatSync, readFileSync} from 'node:fs';
import {join} from 'node:path';
import {homedir} from 'node:os';
import {randomUUID} from 'node:crypto';
import type {RpcNotification} from './rpc.js';

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
export class CodexVoice {
  private leases = new Map<string, Lease>();
  private opening = new Set<string>();
  private closed = false;
  constructor(private connection: () => VoiceConnection = voiceConnection, private warn: (session: string, message: string) => void = () => {}) {}
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
      if (health.protocol !== 'resonant-voice/1' || health.capabilities?.scopedHarnessBridge !== 1) throw new Error('Codex voice requires Resonant Voice 0.1.17 with its scoped harness bridge.');
      const result = await this.http(connection, '/internal/ticket', {sessionId: session, surface, harness: 'codex'});
      if (result.protocol !== 'resonant-voice/1' || result.sessionId !== session || result.url !== connection.base.replace('http:', 'ws:') + '/voice' ||
          !/^[a-f0-9]{64}$/.test(result.ticket) || !/^[a-f0-9]{64}$/.test(result.bridgeId) || result.bridgeLeaseMs !== 8000) throw new Error('Incompatible scoped voice ticket.');
      if (this.closed) throw new Error('Codex voice is closing.');
      const lease: Lease = {session, connection, bridgeId: result.bridgeId, seq: 0, epoch: 0, pending: 0, bytes: 0, chain: Promise.resolve(), items: new Map(), closed: false};
      this.leases.set(session, lease);
      lease.timer = setInterval(() => this.enqueue(lease, {type: 'heartbeat'}), 2000); lease.timer.unref();
      return {protocol: result.protocol, sessionId: session, url: result.url, ticket: result.ticket};
    } finally {this.opening.delete(session);}
  }
  private clearItems(lease: Lease): void {for (const item of lease.items.values()) clearTimeout(item.timer); lease.items.clear();}
  private forget(lease: Lease): void {
    lease.closed = true; clearInterval(lease.timer); this.clearItems(lease);
    if (this.leases.get(lease.session) === lease) this.leases.delete(lease.session);
  }
  private fail(lease: Lease): void {
    if (lease.closed) return;
    this.forget(lease);
    this.warn(lease.session, 'Voice delivery is unavailable. Reconnect voice; the conversation remains available.');
    // A higher sequence invalidates earlier in-flight speech. The service lease
    // also expires if this one-shot disconnect cannot be delivered.
    void this.send(lease, {type: 'disconnect'}).catch(() => {});
  }
  private async send(lease: Lease, event: Data, seq = ++lease.seq): Promise<Data> {
    return this.http(lease.connection, '/internal/event', {sessionId: lease.session, harness: 'codex', bridgeId: lease.bridgeId, seq, ...event});
  }
  private enqueue(lease: Lease, event: Data): void {
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
  private flushItem(lease: Lease, item: Item): void {
    clearTimeout(item.timer); item.timer = undefined;
    if (!item.pending) return;
    for (let offset = 0; offset < item.pending.length; offset += 16000) this.enqueue(lease, {type: 'text', requestId: lease.request, stream: item.stream, text: item.pending.slice(offset, offset + 16000)});
    item.pending = '';
  }
  observe(session: string, frame: RpcNotification, knownRequest: (id: string, turn: string) => boolean): void {
    const lease = this.leases.get(session); if (!lease || lease.closed) return;
    const p = frame.params as Data, item = p.item;
    if (frame.method === 'item/completed' && item?.type === 'userMessage' && typeof item.clientId === 'string' && knownRequest(item.clientId, p.turnId)) {
      if (lease.request === item.clientId) return;
      this.clearItems(lease); lease.request = item.clientId; lease.turn = p.turnId;
      this.enqueue(lease, {type: 'user-turn', requestId: lease.request}); return;
    }
    if (!lease.request || !lease.turn) return;
    if (frame.method === 'turn/completed' && p.turn?.id === lease.turn) {
      if (p.turn.status === 'completed') {
        for (const value of lease.items.values()) this.flushItem(lease, value);
        this.enqueue(lease, {type: 'turn-complete', requestId: lease.request});
      } else void this.stop(session);
      lease.turn = undefined; this.clearItems(lease); return;
    }
    if (p.turnId !== lease.turn) return;
    if (['item/started', 'item/completed'].includes(frame.method) && item?.type === 'agentMessage' && typeof item.id === 'string') {
      let value = lease.items.get(item.id);
      if (value?.done) return;
      if (!value) {
        if (lease.items.size >= 256) {this.fail(lease); return;}
        value = {stream: randomUUID(), text: '', pending: '', done: false}; lease.items.set(item.id, value);
        this.enqueue(lease, {type: 'start', requestId: lease.request, stream: value.stream});
      }
      if (frame.method === 'item/completed') {
        if (typeof item.text !== 'string' || !item.text.startsWith(value.text)) {this.fail(lease); return;}
        value.pending += item.text.slice(value.text.length); this.flushItem(lease, value); value.done = true; value.text = '';
        this.enqueue(lease, {type: 'end', requestId: lease.request, stream: value.stream});
      }
    } else if (frame.method === 'item/agentMessage/delta') {
      const value = lease.items.get(p.itemId);
      if (!value || value.done || typeof p.delta !== 'string') return;
      value.text += p.delta; value.pending += p.delta;
      if (value.text.length > 262144) {this.fail(lease); return;}
      if (value.pending.length >= 16000) this.flushItem(lease, value);
      else if (!value.timer) value.timer = setTimeout(() => this.flushItem(lease, value), 25);
    }
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
