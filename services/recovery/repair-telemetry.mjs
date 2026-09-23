// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Preserve records and physical frame boundaries, including the header frame.
import { readFileSync, statSync } from 'node:fs';
import { zstdDecompressSync, zstdCompressSync, constants } from 'node:zlib';
import { once } from 'node:events';
import { scanZstdFrames } from './zstd-frames.mjs';
const allowed = new Set(['adaptive-reasoning/decision', 'adaptive-reasoning/measurement']);
const limit = 512 * 1024 * 1024;
let bytes = 0, records = 0, changed = 0;
try {
  if (statSync(process.argv[2]).size > limit) throw Error('History too large');
  const source = readFileSync(process.argv[2]);
  const { frames, tornStart } = scanZstdFrames(source);
  if (tornStart !== undefined || !frames.length) throw Error('Incomplete history');
  for (const { start, end } of frames) {
    const original = source.subarray(start, end);
    const raw = zstdDecompressSync(original, { maxOutputLength: limit - bytes });
    bytes += raw.length;
    if (!raw.length || raw.at(-1) !== 10) throw Error('Incomplete record');
    let frameChanged = false;
    const lines = raw.toString('utf8').slice(0, -1).split('\n').map(line => {
      const event = JSON.parse(line);
      if (records === 0) {
        if (event.type !== 'session' || event.version !== 3) throw Error('Unsupported header');
      } else if (event.seq !== records - 1) throw Error('Noncontiguous history');
      records++;
      if (allowed.has(event.type) && event.ignorable !== true) {
        if (!event.data || !Number.isInteger(event.data.version) || !Number.isInteger(event.data.turn) || !Number.isInteger(event.data.step)) throw Error('Unrecognized diagnostic');
        frameChanged = true; changed++;
        return JSON.stringify({ ...event, ignorable: true });
      }
      return line;
    });
    const output = frameChanged ? zstdCompressSync(Buffer.from(lines.join('\n') + '\n'), { params: { [constants.ZSTD_c_checksumFlag]: 1 } }) : original;
    if (!process.stdout.write(output)) await once(process.stdout, 'drain');
  }
  process.stderr.write(JSON.stringify({ changed, records }) + '\n');
} catch { process.exitCode = 1; }
