// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {openSync, closeSync, fsyncSync, writeFileSync, renameSync, unlinkSync, mkdirSync, lstatSync, readFileSync} from 'node:fs';
import {dirname} from 'node:path';
import {randomUUID} from 'node:crypto';

/** Reject symlinks and other-user state; never silently repair someone else's files. */
export function privateDirectory(path: string): void {
  mkdirSync(path, {recursive: true, mode: 0o700});
  const stat = lstatSync(path);
  if (!stat.isDirectory() || stat.isSymbolicLink() || (process.getuid && stat.uid !== process.getuid()) || (stat.mode & 0o077)) {
    throw new Error('Codex state requires a private, user-owned directory.');
  }
}

export function readPrivateJson(path: string): unknown {
  const stat = lstatSync(path);
  if (!stat.isFile() || stat.isSymbolicLink() || (process.getuid && stat.uid !== process.getuid()) || (stat.mode & 0o077)) {
    throw new Error('Codex state requires a private, user-owned file.');
  }
  return JSON.parse(readFileSync(path, 'utf8'));
}

/** Durable replace: a completed call survives process death without a partial JSON file. */
export function durableJson(path: string, value: unknown): void {
  privateDirectory(dirname(path));
  const temporary = `${path}.${randomUUID()}.tmp`;
  const fd = openSync(temporary, 'wx', 0o600);
  try {writeFileSync(fd, JSON.stringify(value) + '\n'); fsyncSync(fd);}
  catch (error) {try {unlinkSync(temporary);} catch {} throw error;}
  finally {closeSync(fd);}
  try {
    renameSync(temporary, path);
    const directory = openSync(dirname(path), 'r');
    try {fsyncSync(directory);} finally {closeSync(directory);}
  } catch (error) {try {unlinkSync(temporary);} catch {} throw error;}
}
