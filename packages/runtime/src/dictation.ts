// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {randomUUID} from 'node:crypto';
import {createRequire} from 'node:module';
import type {EventEmitter} from 'node:events';
import {ScopedVoice, voiceConnection, type VoiceConnection} from '../../voice/src/scoped.js';

type Data = Record<string, any>;
interface SpeechSocket extends EventEmitter {send(data: string | Uint8Array): void; terminate(): void}
const {WebSocket} = createRequire(import.meta.url)('ws') as {WebSocket: new (url: string, options: {handshakeTimeout: number; maxPayload: number; perMessageDeflate: boolean}) => SpeechSocket};
interface Capture {
  id: string; clientId: string; sessionId?: string; speechId: string; abort: AbortController;
  frames: Data[]; wake?: () => void; socket?: SpeechSocket; socketClosed?: Promise<void>;
  opening?: Promise<Data>; transcribing?: Promise<Data>; retiring?: Promise<void>;
  timer: ReturnType<typeof setInterval>; seen: number; maxSeconds?: number; used: boolean;
}
const uuid = /^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/;
const cancelled = () => Error('Dictation closed. Start a new recording; audio was not replayed.');
/** Trusted recognition transport only. It never constructs an AgentSession,
 * submits a prompt, changes a draft, stores audio or exposes companion secrets. */
export class PiDictation {
  private owner?: Capture;
  private closed = false;
  private leases: ScopedVoice;
  private catalogRequests = new Set<AbortController>();
  private catalogTasks = new Set<Promise<Data>>();
  constructor(private authority: (sessionId?: string) => void, private connection: () => VoiceConnection = voiceConnection) {
    this.leases = new ScopedVoice('pi', connection);
  }
  get active() {return !!this.owner || this.leases.active || this.catalogTasks.size > 0;}
  private check() {if (this.closed) throw cancelled();}
  private async request(path: string, body: Data | undefined, signal: AbortSignal) {
    const c = this.connection(), url = new URL(c.base);
    if (url.protocol !== 'http:' || url.hostname !== '127.0.0.1' || !url.port || url.pathname !== '/' || url.username || url.password || url.hash || url.search) throw Error('Dictation requires its explicit loopback endpoint.');
    const response = await fetch(c.base + path, {method: body ? 'POST' : 'GET', redirect: 'error', signal,
      headers: body ? {'content-type': 'application/json', 'x-resonant-token': c.token} : {}, ...(body ? {body: JSON.stringify(body)} : {})});
    if (!response.ok) throw Error('Recognition service did not confirm the operation.');
    let size = 0; const chunks: Buffer[] = [];
    for await (const part of response.body as any) {size += part.length; if (size > 16384) throw Error('Oversized recognition response.'); chunks.push(Buffer.from(part));}
    return JSON.parse(Buffer.concat(chunks).toString());
  }
  catalog(signal: AbortSignal, refresh = false): Promise<Data> {
    this.check(); this.authority();
    const abort = new AbortController(); this.catalogRequests.add(abort);
    const task = (async () => {
      const joined = AbortSignal.any([signal, abort.signal, AbortSignal.timeout(20000)]);
      const health = await this.request('/health', undefined, joined);
      if (health.protocol !== 'resonant-voice/1' || health.capabilities?.dictation !== 1 || (!Array.isArray(health.capabilities?.scopedHarnesses)||!health.capabilities.scopedHarnesses.includes('pi'))) throw Error('Recognition-only input requires a compatible Resonant Voice companion.');
      const result = await this.request('/internal/dictation/catalog', refresh ? {refresh: true} : {}, joined);
      if (result.protocol !== 'resonant-voice/1' || typeof result.recognition?.available !== 'boolean' || result.language !== 'en' || result.device !== 'cpu' || !Number.isInteger(result.maxUtteranceSeconds) || result.maxUtteranceSeconds < 1 || result.maxUtteranceSeconds > 600) throw Error('Incompatible recognition catalog.');
      this.check(); this.authority();
      return {available: result.recognition.available, language: 'en', device: 'cpu', maxDurationSeconds: result.maxUtteranceSeconds, maxAudioBytes: result.maxUtteranceSeconds * 32000 + 44};
    })();
    this.catalogTasks.add(task);
    void task.finally(() => {this.catalogRequests.delete(abort); this.catalogTasks.delete(task);}).catch(() => {});
    return task;
  }
  open(clientId: string, captureId: string, sessionId: string | undefined, signal: AbortSignal): Promise<Data> {
    this.check(); signal.throwIfAborted(); this.authority(sessionId);
    if (!uuid.test(clientId) || !uuid.test(captureId)) throw Error('Choose exact recording and client identities.');
    if (this.owner || this.leases.active) throw Error('Close the existing recording before starting another.');
    const abort = new AbortController();
    const op: Capture = {id: captureId, clientId, sessionId, speechId: 'draft-asr-' + randomUUID(), abort, frames: [], used: false, seen: Date.now(),
      timer: setInterval(() => {if (Date.now() - op.seen > 8000) void this.closeCapture(clientId, captureId);}, 1000)};
    op.timer.unref(); this.owner = op;
    const cancel = () => abort.abort(cancelled()); signal.addEventListener('abort', cancel, {once: true});
    const task = this.openOwned(op).catch(async error => {await this.retire(op); throw error;}).finally(() => signal.removeEventListener('abort', cancel));
    op.opening = task; return task;
  }
  private alive(op: Capture) {op.abort.signal.throwIfAborted(); this.check(); this.authority(op.sessionId); if (this.owner !== op) throw cancelled();}
  private async openOwned(op: Capture) {
    const catalog = await this.catalog(op.abort.signal); this.alive(op);
    if (!catalog.available) throw Error('The configured CPU recognition model is not cached. No model was downloaded.');
    op.maxSeconds = catalog.maxDurationSeconds;
    const ticket = await this.leases.ticket(op.speechId, 'linux', undefined, op.id, 'dictation'); this.alive(op);
    const socket = op.socket = new WebSocket(ticket.url, {handshakeTimeout: 10000, maxPayload: 65536, perMessageDeflate: false});
    op.socketClosed = new Promise(resolve => socket.once('close', () => resolve()));
    socket.on('error', () => op.abort.abort(Error('Recognition transport failed. Start a new recording.')));
    socket.on('close', () => op.abort.abort(cancelled()));
    socket.on('message', (bytes: Buffer, binary: boolean) => {
      try {
        if (binary || bytes.length > 65536) throw Error('Unexpected recognition data.');
        const frame = JSON.parse(bytes.toString());
        if (frame.type === 'error') throw Error('Recognition failed. Start a new recording.');
        if (['ready', 'listening', 'audio-accepted', 'transcript', 'empty-transcript'].includes(frame.type)) {
          if (op.frames.length >= 8) throw Error('Recognition queue exceeded its limit.');
          op.frames.push(frame); op.wake?.();
        }
      } catch {op.abort.abort(Error('Recognition did not confirm the recording.'));}
    });
    const terminate = () => {socket.terminate();}; op.abort.signal.addEventListener('abort', terminate, {once: true});
    await new Promise<void>((resolve, reject) => {
      const fail = () => {cleanup(); reject(op.abort.signal.reason);}, opened = () => {cleanup(); resolve();};
      const cleanup = () => {op.abort.signal.removeEventListener('abort', fail); socket.removeListener('open', opened);};
      op.abort.signal.addEventListener('abort', fail, {once: true}); socket.once('open', opened);
      if (op.abort.signal.aborted) fail();
    });
    this.alive(op); socket.send(JSON.stringify({type: 'auth', ticket: ticket.ticket, textSource: 'plugin'}));
    const ready = await this.next(op, 'ready', 45000);
    if (ready.protocol !== 'resonant-voice/1' || ready.mode !== 'dictation' || ready.maxUtteranceSeconds !== op.maxSeconds || ready.inputAcknowledgements !== true || ready.input?.sampleRate !== 16000 || ready.input?.channels !== 1 || ready.input?.format !== 's16le') throw Error('Recognition input is incompatible.');
    this.alive(op); return {captureId: op.id, ...catalog};
  }
  private async next(op: Capture, type: string, timeout: number): Promise<Data> {
    const timer = setTimeout(() => op.abort.abort(Error('Recognition timed out. Start a new recording.')), timeout);
    try {
      while (true) {
        this.alive(op);
        const frame = op.frames.shift();
        if (frame) {if (frame.type !== type && !(type === 'transcript' && frame.type === 'empty-transcript')) throw Error('Recognition events arrived out of order.'); return frame;}
        await new Promise<void>(resolve => {
          const wake = () => {op.wake = undefined; op.abort.signal.removeEventListener('abort', wake); resolve();};
          op.wake = wake; op.abort.signal.addEventListener('abort', wake, {once: true});
          if (op.abort.signal.aborted) wake();
        });
      }
    } finally {clearTimeout(timer);}
  }
  private owned(clientId: string, id: string): Capture {const op = this.owner; if (!op || op.id !== id || op.clientId !== clientId) throw Error('This recording is no longer owned by this client.'); this.alive(op); return op;}
  heartbeat(clientId: string, id: string) {const op = this.owned(clientId, id); op.seen = Date.now(); return {active: true};}
  transcribe(clientId: string, id: string, read: (signal: AbortSignal) => Promise<Uint8Array>, signal: AbortSignal): Promise<Data> {
    const op = this.owned(clientId, id); if (op.used) throw Error('This recording was already submitted. Audio was not replayed.'); op.used = true;
    const cancel = () => op.abort.abort(cancelled()); signal.addEventListener('abort', cancel, {once: true});
    if (signal.aborted) cancel();
    const task = (async () => {
      await op.opening; this.alive(op);
      const data = Buffer.from(await read(op.abort.signal)); this.alive(op);
      const pcm = canonicalPcm(data, op.maxSeconds!);
      op.socket!.send(JSON.stringify({type: 'begin'})); const listening = await this.next(op, 'listening', 10000);
      if (typeof listening.requestId !== 'string' || !listening.requestId) throw Error('Missing recognition identity.');
      for (let offset = 0; offset < pcm.length; offset += 65536) {
        this.alive(op); const chunk = pcm.subarray(offset, offset + 65536); op.socket!.send(chunk);
        const ack = await this.next(op, 'audio-accepted', 20000);
        if (ack.requestId !== listening.requestId || ack.bytes !== offset + chunk.length) throw Error('Recognition did not acknowledge the exact audio.');
      }
      // The companion auto-finishes exact-limit input after its last ack.
      if (pcm.length < op.maxSeconds! * 32000) op.socket!.send(JSON.stringify({type: 'end'}));
      const final = await this.next(op, 'transcript', 120000); this.alive(op);
      if (final.type === 'transcript' && (final.requestId !== listening.requestId || typeof final.text !== 'string' || final.text.length > 262144)) throw Error('Recognition returned an incompatible transcript.');
      return {text: final.type === 'empty-transcript' ? '' : final.text};
    })().finally(async () => {signal.removeEventListener('abort', cancel); await this.retire(op);});
    op.transcribing = task; return task;
  }
  private retire(op: Capture): Promise<void> {
    if (!op.retiring) op.retiring = (async () => {
      op.abort.abort(cancelled()); clearInterval(op.timer); op.socket?.terminate();
      await Promise.all([op.socketClosed, this.leases.release(op.speechId, op.id)]);
      if (this.owner === op) this.owner = undefined;
    })();
    return op.retiring;
  }
  async closeCapture(clientId: string, id: string) {
    const op = this.owner; if (!op || op.id !== id || op.clientId !== clientId) return {closed: true};
    op.abort.abort(cancelled());
    await Promise.allSettled([op.opening, op.transcribing]); await this.retire(op); return {closed: true};
  }
  async close() {this.closed = true; for (const abort of this.catalogRequests) abort.abort(cancelled()); const op = this.owner; await Promise.allSettled([...(op ? [this.closeCapture(op.clientId, op.id)] : []), ...this.catalogTasks]); await this.leases.close();}
}

/** Original DSH recorder's canonical WAV only; no parser, conversion or fallback. */
export function canonicalPcm(bytes: Buffer, maxSeconds: number): Buffer {
  if (bytes.length <= 44 || bytes.length > maxSeconds * 32000 + 44 || (bytes.length - 44) % 2 ||
      bytes.toString('ascii', 0, 4) !== 'RIFF' || bytes.readUInt32LE(4) !== bytes.length - 8 || bytes.toString('ascii', 8, 16) !== 'WAVEfmt ' ||
      bytes.readUInt32LE(16) !== 16 || bytes.readUInt16LE(20) !== 1 || bytes.readUInt16LE(22) !== 1 || bytes.readUInt32LE(24) !== 16000 ||
      bytes.readUInt32LE(28) !== 32000 || bytes.readUInt16LE(32) !== 2 || bytes.readUInt16LE(34) !== 16 || bytes.toString('ascii', 36, 40) !== 'data' || bytes.readUInt32LE(40) !== bytes.length - 44) throw Error('Supply a bounded canonical 16 kHz mono PCM16 WAV recording.');
  return bytes.subarray(44);
}
