// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {mkdirSync, writeFileSync, readFileSync, renameSync, readdirSync, statSync} from 'node:fs';
import {join} from 'node:path';
import {randomUUID} from 'node:crypto';
import type {DesktopBrief, DesktopResult} from './contracts.js';

interface RecordData {
  owner: string;
  brief: DesktopBrief;
  startedAt: string;
  result: DesktopResult;
  events: {tool: string; metadata: unknown; image?: string}[];
}
const validId = (id: string) => /^[a-f0-9-]{36}$/.test(id);
export class DesktopEvidence {
  readonly id = randomUUID();
  readonly directory: string;
  private bytes = 0;
  readonly record: RecordData;
  constructor(root: string, owner: string, brief: DesktopBrief, result: DesktopResult, readonly limit: number) {
    mkdirSync(root, {recursive: true, mode: 0o700});
    // Refuse new runs at capacity. Never delete evidence behind the user's back.
    let used = 0;
    for (const entry of readdirSync(root, {withFileTypes: true})) {
      if (!entry.isDirectory() || !validId(entry.name)) continue;
      for (const file of readdirSync(join(root, entry.name))) used += statSync(join(root, entry.name, file)).size;
    }
    if (used + limit > 256 * 1024 * 1024) throw Error('Desktop evidence storage is full. Review or remove old runs before continuing.');
    this.directory = join(root, this.id);
    mkdirSync(this.directory, {mode: 0o700});
    result.runId = this.id;
    this.record = {owner, brief, startedAt: new Date().toISOString(), result, events: []};
    this.save();
  }
  save() {
    const text = JSON.stringify(this.record);
    if (this.bytes + Buffer.byteLength(text) > this.limit) throw Error('Desktop evidence budget exceeded');
    const temp = join(this.directory, 'record.tmp');
    writeFileSync(temp, text, {mode: 0o600});
    renameSync(temp, join(this.directory, 'record.json'));
  }
  add(tool: string, metadata: unknown, image?: {data: string; mimeType: string}) {
    let name: string | undefined;
    if (image) {
      if (!['image/png', 'image/jpeg'].includes(image.mimeType)) throw Error('Unsupported desktop image format');
      const data = Buffer.from(image.data, 'base64');
      if (data.length > 1_000_000 || data.length + this.bytes + Buffer.byteLength(JSON.stringify(this.record)) + 16384 > this.limit)
        throw Error('Desktop evidence budget exceeded');
      name = `${this.record.events.length}.${image.mimeType === 'image/png' ? 'png' : 'jpg'}`;
      writeFileSync(join(this.directory, name), data, {mode: 0o600});
      this.bytes += data.length;
    }
    this.record.events.push({tool, metadata, ...(name ? {image: name} : {})});
    this.save();
  }
  static read(root: string, owner: string, id: string) {
    if (!validId(id)) throw Error('Invalid desktop run ID');
    const record = JSON.parse(readFileSync(join(root, id, 'record.json'), 'utf8')) as RecordData;
    if (record.owner !== owner) throw Error('This desktop evidence belongs to another conversation');
    return record;
  }
}
