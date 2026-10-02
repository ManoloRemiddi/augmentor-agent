// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {openSync, readSync, closeSync, existsSync, mkdirSync, readFileSync, writeFileSync, linkSync, unlinkSync} from 'node:fs';
import {join} from 'node:path';
import {homedir} from 'node:os';
import {createHash, randomUUID} from 'node:crypto';

export function identityDirectory(): string {
  const config = process.env.AUGMENTOR_PI_CONFIG ?? join(process.env.XDG_CONFIG_HOME ?? join(homedir(), '.config'), 'augmentor-pi');
  return process.env.AUGMENTOR_IDENTITY_DIR ?? join(config, 'identity');
}

/** The UI writes by atomic replace. Harnesses snapshot this value when a chat is created. */
export function soulText(): string {
  const path = join(identityDirectory(), 'soul.md');
  let fd: number;
  try {fd = openSync(path, 'r');}
  catch (error: any) {if (error.code !== 'ENOENT') throw error; fd = openSync(new URL('../../../config/agent-persona.md', import.meta.url), 'r');}
  try {
    const raw = Buffer.alloc(32769); let size = 0;
    while (size < raw.length) {const count = readSync(fd, raw, size, raw.length-size, null); if (!count) break; size += count;}
    const text = new TextDecoder('utf-8', {fatal: true}).decode(raw.subarray(0, size));
    if (size > 32768 || !text.trim() || text.includes('\0')) throw new Error('Soul must contain nonempty instructions of at most 32 KiB.');
    return text;
  } finally {closeSync(fd);}
}

/** A preset is shared by DSH agents; save each agent's independent prompt authority. */
export function sessionSoul(id: string, initial?: string): string {
  if (typeof id !== 'string' || !id || id.length > 512) throw new Error('Invalid identity session.');
  const directory = join(identityDirectory(), 'dsh-sessions');
  const path = join(directory, createHash('sha256').update(id).digest('hex')+'.md');
  if (!existsSync(path)) {
    mkdirSync(directory, {recursive: true, mode: 0o700});
    const temporary = join(directory, randomUUID()+'.tmp');
    try {
      writeFileSync(temporary, initial ?? soulText(), {mode: 0o600, flag: 'wx', flush: true});
      // Publish without replacement so two writers never overwrite a chat's snapshot.
      try {linkSync(temporary, path);} catch (error: any) {if (error.code !== 'EEXIST') throw error;}
    } finally {if (existsSync(temporary)) unlinkSync(temporary);}
  }
  const text = readFileSync(path, 'utf8');
  if (!text.trim() || Buffer.byteLength(text)>32768) throw new Error('Invalid saved conversation Soul.');
  return text;
}
