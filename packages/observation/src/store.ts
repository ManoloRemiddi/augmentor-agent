// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {appendFileSync, closeSync, existsSync, openSync, readSync, readdirSync, renameSync, rmSync, statSync, writeFileSync} from 'node:fs';
import {join} from 'node:path';
import {createHash, randomUUID} from 'node:crypto';
import {identifier} from '../../protocol/src/index.js';
import {atomicJson, privateDir, readJson} from '../../runtime/src/storage.js';
import {ObservationIndex} from './journal-index.js';
import {PayloadIndex,PayloadUnavailable,PAYLOAD_BLOCK} from './payload-index.js';
import {PayloadSearch,type SearchOptions} from './payload-search.js';

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
export interface PageOptions {beforeSeq?: number; afterSeq?: number; limit?: number; query?:string}
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
  private indexes=new Map<string,ObservationIndex>();
  private payloadIndexes=new Map<string,PayloadIndex>();
  private pendingPayloadPrune=false;
  private searcher=new PayloadSearch(this,id=>this.index(id),(sid,id)=>this.payloadIndex(sid,id));
  constructor(readonly root: string, readonly policy: () => ObservationPolicy, readonly now = Date.now) {
    privateDir(root);
    this.prune(true);
  }
  private directory(sessionId: string) {return privateDir(join(this.root, identifier(sessionId)));}
  private journal(sessionId: string) {return join(this.directory(sessionId), 'events.jsonl');}
  private index(sessionId:string){let index=this.indexes.get(sessionId);if(!index){index=new ObservationIndex(this.journal(sessionId),sessionId);if(this.indexes.size>=32)this.indexes.delete(this.indexes.keys().next().value!);this.indexes.set(sessionId,index);}return index;}
  private payloadIndex(sessionId:string,eventId:string){const file=join(this.directory(sessionId),identifier(eventId)+'.payload.json');let index=this.payloadIndexes.get(file);if(!index){index=new PayloadIndex(file,()=>{this.pendingPayloadPrune=true;});if(this.payloadIndexes.size>=32)this.payloadIndexes.delete(this.payloadIndexes.keys().next().value!);this.payloadIndexes.set(file,index);}return index;}
  private flushPayloadIndexes(){if(this.pendingPayloadPrune){this.pendingPayloadPrune=false;this.prune(true);}}
  search(sessionId:string,options:SearchOptions={}){this.prune();try{return this.searcher.page(identifier(sessionId),options);}finally{this.flushPayloadIndexes();}}
  append(sessionId: string, kind: string, data: Record<string, unknown>,
    correlations: {turnId?: string; requestId?: string} = {}, payload?: unknown): Observation {
    const directory = this.directory(sessionId);
    const counter = join(directory, 'counter.json');
    const previous = this.counters.get(sessionId) ?? Math.max(
      integer(readJson<{seq: number}>(counter, {seq: 0}).seq, 0, 0, Number.MAX_SAFE_INTEGER - 1),
      this.index(sessionId).snapshot().lastSeq ?? 0);
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
    this.index(sessionId).append(event,line);
    this.size += Buffer.byteLength(line)+40;
    this.prune(this.size > this.policy().maxBytes);
    return event;
  }
  page(sessionId: string, options: PageOptions = {}) {
    this.prune();
    const limit = integer(options.limit, 100, 1, 500);
    if (options.beforeSeq !== undefined && options.afterSeq !== undefined) throw new Error('Choose one observation cursor');
    const before = integer(options.beforeSeq, Number.MAX_SAFE_INTEGER, 1, Number.MAX_SAFE_INTEGER);
    const after = integer(options.afterSeq, 0, 0, Number.MAX_SAFE_INTEGER);
    if(options.query!==undefined&&(typeof options.query!=='string'||options.query.length>256))throw Error('Search up to 256 characters of retained metadata.');
    const terms=(options.query??'').trim().toLowerCase().split(/\s+/).filter(Boolean);if(terms.length>16)throw Error('Search up to 16 literal metadata terms.');
    return {protocol:OBSERVATION_PROTOCOL,...this.index(sessionId).page({before,after,forward:options.afterSeq!==undefined,limit,terms}),capturePayloads:this.policy().capturePayloads,
      coverage:{scope:terms.length?'retained-metadata-search':'retained-metadata',payloadBodies:false,index:'byte-offset-v1',query:options.query??''}};
  }
  payload(sessionId: string, eventId: string, offset?: number, limit?: number, sha256?:unknown) {
    this.prune();
    const file = join(this.directory(sessionId), identifier(eventId) + '.payload.json');
    if (!existsSync(file)) return {available: false, reason: 'Payload was not captured or has expired.'};
    if(sha256!==undefined){if(typeof sha256!=='string')throw Error('Invalid captured payload hash');try{return this.payloadIndex(sessionId,eventId).withReader(sha256,reader=>{const start=integer(offset,0,0,reader.size),length=integer(limit,65536,1,65536),pieces:Buffer[]=[];let at=start,remaining=Math.min(length+3,reader.size-start);while(remaining){const block=reader.block(Math.floor(at/PAYLOAD_BLOCK)),inside=at%PAYLOAD_BLOCK,n=Math.min(remaining,block.length-inside);pieces.push(block.subarray(inside,inside+n));at+=n;remaining-=n;}const bytes=Buffer.concat(pieces);if(bytes.length&&(bytes[0]!&0xc0)===0x80)throw Error('Payload cursor splits a UTF-8 character');let end=Math.min(length,bytes.length);while(end>0&&end<bytes.length&&(bytes[end]!&0xc0)===0x80)end--;if(!end&&bytes.length){end=1;while(end<bytes.length&&(bytes[end]!&0xc0)===0x80)end++;}return {available:true,offset:start,nextOffset:start+end,length:reader.size,units:'utf8-bytes',text:bytes.subarray(0,end).toString('utf8'),hasMore:start+end<reader.size,sha256,verification:'captured snapshot source blocks'};});}catch(error){if(error instanceof PayloadUnavailable)return {available:false,reason:error.message};throw error;}finally{this.flushPayloadIndexes();}}
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
    this.index(sessionId).invalidate();
    for (const file of readdirSync(directory)) {
      if (file === 'events.jsonl' || file.endsWith('.payload.json')) {rmSync(join(directory,file));if(file.endsWith('.payload.json'))this.payloadIndex(sessionId,file.slice(0,-13)).invalidate();}
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
        const index=this.index(entry.name),snapshot=index.snapshot();
        if(snapshot.minTime!==null&&snapshot.minTime<oldest){
          // Atomic replacement prevents readers from seeing a partial retention rewrite.
          const temporary = join(directory, randomUUID() + '.retention.tmp');
          writeFileSync(temporary,'',{mode:0o600});
          for(const {record} of index.lines())if(record.time>=oldest)appendFileSync(temporary,JSON.stringify(record)+'\n');
          renameSync(temporary,journal);index.invalidate();index.snapshot();
        }
      }
      for (const name of readdirSync(directory)) {
        // Only our atomic-write leftovers are owned here. A second runtime is
        // excluded by the host socket before this store is constructed.
        if (/^(?:counter\.json\.|[a-f0-9-]{36}\.payload\.json\.)[a-f0-9-]{36}\.tmp$/.test(name) ||
          /^[a-f0-9-]{36}\.retention\.tmp$/.test(name)||/^events\.jsonl\.idx(?:\.json)?\.[a-f0-9-]{36}\.tmp$/.test(name)||/^[a-f0-9-]{36}\.payload\.json\.idx(?:\.json)?\.[a-f0-9-]{36}\.tmp$/.test(name)) {rmSync(join(directory, name)); continue;}
        if(/^[a-f0-9-]{36}\.payload\.json\.idx(?:\.json)?$/.test(name)&&!existsSync(join(directory,name.replace(/\.idx(?:\.json)?$/,'')))){rmSync(join(directory,name),{force:true});continue;}
        if (name !== 'events.jsonl' && !name.endsWith('.payload.json')) continue;
        const path = join(directory, name), info = statSync(path);
        if (name.endsWith('.payload.json') && info.mtimeMs < oldest) {rmSync(path);this.payloadIndex(entry.name,name.slice(0,-13)).invalidate(); continue;}
        const indexBytes=['.idx','.idx.json'].reduce((n,suffix)=>n+(existsSync(path+suffix)?statSync(path+suffix).size:0),0);
        files.push({path, time: info.mtimeMs, size: info.size+indexBytes, payload: name.endsWith('.payload.json')});
      }
    }
    this.size = files.reduce((total, file) => total + file.size, 0);
    // Expire payload copies before metadata. Sequence counters survive both.
    files.sort((a, b) => Number(b.payload) - Number(a.payload) || a.time - b.time);
    for (const file of files) {
      if (this.size <= maxBytes) break;
      rmSync(file.path);if(!file.payload)this.index(file.path.split(/[\\/]/).at(-2)!).invalidate();else this.payloadIndex(file.path.split(/[\\/]/).at(-2)!,file.path.split(/[\\/]/).at(-1)!.slice(0,-13)).invalidate();this.size -= file.size;
    }
  }
}
