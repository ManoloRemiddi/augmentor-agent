// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {appendFileSync, closeSync, existsSync, openSync, readSync, readFileSync, readdirSync, renameSync, rmSync, statSync, truncateSync, writeFileSync} from 'node:fs';
import {join} from 'node:path';
import {createHash, randomUUID} from 'node:crypto';
import {identifier} from '../../protocol/src/index.js';
import {atomicJson, privateDir, readJson} from '../../runtime/src/storage.js';

export const OBSERVATION_PROTOCOL = 'augmentor-observation/1';
export const DEFAULT_RETENTION = {days: 14, maxBytes: 512 * 1024 * 1024};
export interface ObservationPolicy {capturePayloads: boolean; days: number; maxBytes: number}
export interface Observation {
  protocol: typeof OBSERVATION_PROTOCOL;
  id: string;
  seq: number;
  sessionId: string;
  time: number;
  kind: string;
  turnId?: string;
  requestId?: string;
  data: Record<string, unknown>;
  payload?: {state: 'retained' | 'disabled' | 'too-large' | 'invalid'; bytes?: number; sha256?: string; redactions?: string[]};
}
export interface PageOptions {beforeSeq?: number; afterSeq?: number; limit?: number}
const credential = /^(authorization|proxy-authorization|cookie|set-cookie|api[-_]?key|access[-_]?token|refresh[-_]?token|password|client[-_]?secret)$/i;

// Request bodies and tool content can contain user-supplied secrets. Redact known
// credential fields as an additional measure; never claim content is secret-free.
export function payloadText(value: unknown) {
  const redactions = new Set<string>();
  const text = JSON.stringify(value, (key, item) => {
    if (credential.test(key)) {redactions.add(key); return '[Redacted credential field]';}
    return item;
  });
  if (text === undefined) throw new Error('Payload is not JSON serializable');
  return {text, redactions: [...redactions]};
}
function integer(value: unknown, fallback: number, min: number, max: number) {
  if (value === undefined) return fallback;
  if (!Number.isSafeInteger(value) || Number(value) < min || Number(value) > max) throw new Error('Invalid observation page boundary');
  return Number(value);
}

/** Private observations are read models; they can never resume an operation. */
export class ObservationStore {
  private counters = new Map<string, number>();
  private lastPrune = 0;
  private size = 0;
  constructor(readonly root: string, readonly policy: () => ObservationPolicy, readonly now = Date.now) {
    privateDir(root);
    this.prune(true);
  }
  private directory(sessionId: string) {return privateDir(join(this.root, identifier(sessionId)));}
  private journal(sessionId: string) {return join(this.directory(sessionId), 'events.jsonl');}
  private records(sessionId: string): Observation[] {
    const file = this.journal(sessionId);
    if (!existsSync(file)) return [];
    let raw = readFileSync(file);
    // A killed writer can leave an incomplete final frame; preserve complete frames.
    if (raw.length && raw.at(-1) !== 10) {
      const end = raw.lastIndexOf(10) + 1;
      truncateSync(file, end); raw = raw.subarray(0, end);
    }
    return raw.toString('utf8').split('\n').filter(Boolean).map(line => JSON.parse(line));
  }
  append(sessionId: string, kind: string, data: Record<string, unknown>,
    correlations: {turnId?: string; requestId?: string} = {}, payload?: unknown): Observation {
    const directory = this.directory(sessionId);
    const counter = join(directory, 'counter.json');
    const previous = this.counters.get(sessionId) ?? Math.max(
      integer(readJson<{seq: number}>(counter, {seq: 0}).seq, 0, 0, Number.MAX_SAFE_INTEGER - 1),
      this.records(sessionId).at(-1)?.seq ?? 0);
    if (!Number.isSafeInteger(previous) || previous < 0 || previous >= Number.MAX_SAFE_INTEGER)
      throw new Error('Observation sequence is exhausted or corrupt');
    const event: Observation = {protocol: OBSERVATION_PROTOCOL, id: randomUUID(), seq: previous + 1,
      sessionId, time: this.now(), kind, ...correlations, data};
    // Persist the sequence reservation first. A crash may leave a gap, never a reuse.
    atomicJson(counter, {seq: event.seq});
    this.counters.set(sessionId, event.seq);
    if (payload !== undefined) {
      event.payload = {state: 'disabled'};
      if (this.policy().capturePayloads) {
        try {
          const serialized = payloadText(payload);
          const bytes = Buffer.byteLength(serialized.text);
          if (bytes > Math.min(this.policy().maxBytes / 2, 32 * 1024 * 1024)) event.payload = {state: 'too-large', bytes};
          else {
            const file = join(directory, event.id + '.payload.json'), temporary = file + '.' + randomUUID() + '.tmp';
            writeFileSync(temporary, serialized.text, {mode: 0o600}); renameSync(temporary, file);
            event.payload = {state: 'retained', bytes,
              sha256: createHash('sha256').update(serialized.text).digest('hex'), redactions: serialized.redactions};
            this.size += statSync(join(directory, event.id + '.payload.json')).size;
          }
        } catch {event.payload = {state: 'invalid'};}
      }
    }
    const line = JSON.stringify(event) + '\n';
    appendFileSync(this.journal(sessionId), line, {mode: 0o600});
    this.size += Buffer.byteLength(line);
    this.prune(this.size > this.policy().maxBytes);
    return event;
  }
  page(sessionId: string, options: PageOptions = {}) {
    this.prune();
    const limit = integer(options.limit, 100, 1, 500);
    if (options.beforeSeq !== undefined && options.afterSeq !== undefined) throw new Error('Choose one observation cursor');
    const before = integer(options.beforeSeq, Number.MAX_SAFE_INTEGER, 1, Number.MAX_SAFE_INTEGER);
    const after = integer(options.afterSeq, 0, 0, Number.MAX_SAFE_INTEGER);
    const all = this.records(sessionId);
    const eligible = all.filter(record => record.seq < before && record.seq > after);
    const records = options.afterSeq === undefined ? eligible.slice(-limit) : eligible.slice(0, limit);
    return {protocol: OBSERVATION_PROTOCOL, records, hasMore: eligible.length > records.length,
      earliestSeq: all.at(0)?.seq ?? null, latestSeq: all.at(-1)?.seq ?? null,
      capturePayloads: this.policy().capturePayloads};
  }
  payload(sessionId: string, eventId: string, offset?: number, limit?: number) {
    this.prune();
    const file = join(this.directory(sessionId), identifier(eventId) + '.payload.json');
    if (!existsSync(file)) return {available: false, reason: 'Payload was not captured or has expired.'};
    const size = statSync(file).size;
    const start = integer(offset, 0, 0, size);
    const length = integer(limit, 65536, 1, 65536);
    const buffer = Buffer.alloc(Math.min(length + 3, size - start)), descriptor = openSync(file, 'r');
    let count: number;
    try {count = readSync(descriptor, buffer, 0, buffer.length, start);} finally {closeSync(descriptor);}
    if (count && (buffer[0]! & 0xc0) === 0x80) throw new Error('Payload cursor splits a UTF-8 character');
    let end = Math.min(length, count);
    while (end > 0 && end < count && (buffer[end]! & 0xc0) === 0x80) end--;
    // A tiny requested page still makes progress through a complete code point.
    if (!end && count) {end = 1; while (end < count && (buffer[end]! & 0xc0) === 0x80) end++;}
    return {available: true, offset: start, nextOffset: start + end, length: size, units: 'utf8-bytes',
      text: buffer.subarray(0, end).toString('utf8'), hasMore: start + end < size};
  }
  clear(sessionId: string) {
    const directory = this.directory(sessionId);
    for (const file of readdirSync(directory)) {
      if (file === 'events.jsonl' || file.endsWith('.payload.json')) rmSync(join(directory, file));
    }
    this.prune(true);
    return this.append(sessionId, 'observation/cleared', {scope: 'diagnostic records only'});
  }
  prune(force = false) {
    const now = this.now();
    if (!force && now - this.lastPrune < 60000) return;
    this.lastPrune = now;
    const {days, maxBytes} = this.policy();
    if (!Number.isFinite(days) || days <= 0 || !Number.isSafeInteger(maxBytes) || maxBytes < 4096)
      throw new Error('Invalid observation retention policy');
    const oldest = now - days * 86400000;
    const files: {path: string; time: number; size: number; payload: boolean}[] = [];
    for (const entry of readdirSync(this.root, {withFileTypes: true})) {
      if (!entry.isDirectory() || !/^[a-zA-Z0-9_-]{1,128}$/.test(entry.name)) continue;
      const directory = join(this.root, entry.name);
      const journal = join(directory, 'events.jsonl');
      if (existsSync(journal)) {
        const all = this.records(entry.name);
        const retained = all.filter(record => record.time >= oldest);
        if (retained.length !== all.length) {
          // Atomic replacement prevents readers from seeing a partial retention rewrite.
          const raw = retained.map(record => JSON.stringify(record) + '\n').join('');
          const temporary = join(directory, randomUUID() + '.retention.tmp');
          writeFileSync(temporary, raw, {mode: 0o600}); renameSync(temporary, journal);
        }
      }
      for (const name of readdirSync(directory)) {
        // Only our atomic-write leftovers are owned here. A second runtime is
        // excluded by the host socket before this store is constructed.
        if (/^(?:counter\.json\.|[a-f0-9-]{36}\.payload\.json\.)[a-f0-9-]{36}\.tmp$/.test(name) ||
          /^[a-f0-9-]{36}\.retention\.tmp$/.test(name)) {rmSync(join(directory, name)); continue;}
        if (name !== 'events.jsonl' && !name.endsWith('.payload.json')) continue;
        const path = join(directory, name), info = statSync(path);
        if (name.endsWith('.payload.json') && info.mtimeMs < oldest) {rmSync(path); continue;}
        files.push({path, time: info.mtimeMs, size: info.size, payload: name.endsWith('.payload.json')});
      }
    }
    this.size = files.reduce((total, file) => total + file.size, 0);
    // Expire payload copies before metadata. Sequence counters survive both.
    files.sort((a, b) => Number(b.payload) - Number(a.payload) || a.time - b.time);
    for (const file of files) {
      if (this.size <= maxBytes) break;
      rmSync(file.path); this.size -= file.size;
    }
  }
}
