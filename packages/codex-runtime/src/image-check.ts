// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {randomInt} from 'node:crypto';
import {deflateSync} from 'node:zlib';

export const checkColors = [
  {name: 'red', rgb: [220, 0, 0]}, {name: 'green', rgb: [0, 160, 0]},
  {name: 'blue', rgb: [0, 0, 255]}, {name: 'yellow', rgb: [255, 220, 0]},
  {name: 'black', rgb: [0, 0, 0]}, {name: 'white', rgb: [255, 255, 255]},
];
function chunk(type: string, data: Buffer): Buffer {
  const bytes = Buffer.concat([Buffer.from(type), data]); let crc = 0xffffffff;
  for (const byte of bytes) {crc ^= byte; for (let bit = 0; bit < 8; bit++) crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0);}
  const length = Buffer.alloc(4); length.writeUInt32BE(data.length);
  const checksum = Buffer.alloc(4); checksum.writeUInt32BE((crc ^ 0xffffffff) >>> 0);
  return Buffer.concat([length, bytes, checksum]);
}
/** Synthetic pixels only. The answer is never included in the provider's text input. */
export function imageChallenge(): {url: string; answer: string} {
  const colors = Array.from({length: 4}, () => checkColors[randomInt(checkColors.length)]);
  const width = 144, height = 36; const rows = Buffer.alloc(height * (1 + width * 3), 128);
  for (let y = 0; y < height; y++) {
    const offset = y * (1 + width * 3); rows[offset] = 0; // PNG filter: none.
    for (let x = 0; x < width; x++) if (x % 36 >= 2 && x % 36 < 34 && y >= 2 && y < 34) {
      const rgb = colors[Math.floor(x / 36)].rgb;
      for (let c = 0; c < 3; c++) rows[offset + 1 + x * 3 + c] = rgb[c];
    }
  }
  const header = Buffer.alloc(13); header.writeUInt32BE(width); header.writeUInt32BE(height, 4); header[8] = 8; header[9] = 2;
  const png = Buffer.concat([Buffer.from([137,80,78,71,13,10,26,10]), chunk('IHDR', header), chunk('IDAT', deflateSync(rows)), chunk('IEND', Buffer.alloc(0))]);
  return {url: 'data:image/png;base64,' + png.toString('base64'), answer: colors.map(color => color.name).join(',')};
}
