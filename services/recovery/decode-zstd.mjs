// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Node's zstd decoder stops after one frame; DSH appends concatenated frames.
import { readFileSync, statSync } from 'node:fs';
import { zstdDecompressSync } from 'node:zlib';
import { once } from 'node:events';
import { scanZstdFrames } from './zstd-frames.mjs';
const limit = 512 * 1024 * 1024;
let bytes = 0;
try {
  if (statSync(process.argv[2]).size > limit) throw Error('History too large');
  const source = readFileSync(process.argv[2]);
  const { frames, tornStart } = scanZstdFrames(source);
  if (tornStart !== undefined || !frames.length) throw Error('Incomplete history');
  for (const { start, end } of frames) {
    const decoded = zstdDecompressSync(source.subarray(start, end), { maxOutputLength: limit - bytes });
    bytes += decoded.length;
    if (!process.stdout.write(decoded)) await once(process.stdout, 'drain');
  }
} catch { process.exitCode = 1; }
