// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {closeSync, existsSync, fsyncSync, openSync, readFileSync, writeFileSync, lstatSync} from 'node:fs';
import {dirname} from 'node:path';
import {privateDirectory} from './storage.js';
import type {ChatEvent} from './events.js';
import type {DisplayEvent} from '../../protocol/src/index.js';
import {MAX_FRAME} from '../../protocol/src/index.js';
import {historyPage} from '../../protocol/src/history.js';

/** Product display journal; native Codex storage remains the agent's authoritative history. */
export class DisplayJournal {
  private events: DisplayEvent[] = [];
  private keys = new Set<string>();
  constructor(readonly path: string) {
    privateDirectory(dirname(path));
    if (!existsSync(path)) return;
    const stat = lstatSync(path);
    if (!stat.isFile() || stat.isSymbolicLink() || (process.getuid && stat.uid !== process.getuid()) || (stat.mode & 0o077)) throw new Error('Codex display history must be a private user-owned file.');
    const raw = readFileSync(path, 'utf8');
    if (raw && !raw.endsWith('\n')) throw new Error('Codex display journal has an incomplete write. Preserve it and reconcile native history.');
    for (const line of raw.split('\n').filter(Boolean)) {
      const record = JSON.parse(line);
      if (record.event?.seq !== this.events.length + 1 || typeof record.event.type !== 'string' || !record.event.data ||
        (record.key !== undefined && (typeof record.key !== 'string' || this.keys.has(record.key)))) throw new Error('Codex display history is corrupt.');
      this.events.push(record.event);
      if (record.key) this.keys.add(record.key);
    }
  }
  append(event: ChatEvent, key?: string): DisplayEvent | undefined {
    if (key && this.keys.has(key)) return;
    const saved = {...event, seq: this.events.length + 1};
    const line = JSON.stringify({event: saved, ...(key ? {key} : {})}) + '\n';
    if (Buffer.byteLength(line) > MAX_FRAME - 4096) throw new Error('Codex display event exceeds the client frame limit. Native history is retained.');
    const fd = openSync(this.path, 'a', 0o600);
    try {writeFileSync(fd, line); fsyncSync(fd);} finally {closeSync(fd);}
    this.events.push(saved); if (key) this.keys.add(key);
    return structuredClone(saved);
  }
  event(seq: unknown): DisplayEvent | undefined {
    if (typeof seq !== 'number' || !Number.isSafeInteger(seq) || seq < 1) throw new Error('Invalid Codex display sequence.');
    const event = this.events[seq - 1];
    return event ? structuredClone(event) : undefined;
  }
  *committed(afterSeq = 0): Iterable<DisplayEvent> {
    for (const event of this.events) if (event.seq > afterSeq && ['user/message', 'assistant/message'].includes(event.type)) yield structuredClone(event);
  }
  page(maxMessages = 12, beforeSeq?: number) {return historyPage(this.events, maxMessages, beforeSeq);}
}
