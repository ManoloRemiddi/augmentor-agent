// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Small bounded Ed25519 verification using the already bundled Node runtime.
// The installed caller supplies the trust root; a download never supplies it.
import { createPublicKey, verify } from 'node:crypto';

try {
  const chunks = []; let length = 0;
  for await (const chunk of process.stdin) {
    length += chunk.length;
    if (length > 100000) throw new Error('Oversized verification request');
    chunks.push(chunk);
  }
  const input = JSON.parse(Buffer.concat(chunks).toString('utf8'));
  const decode = (text, size) => {
    if (typeof text !== 'string') throw new Error('Invalid encoding');
    const result = Buffer.from(text, 'base64');
    if (result.toString('base64') !== text || (size && result.length !== size))
      throw new Error('Invalid encoding');
    return result;
  };
  const rawKey = decode(input.key, 32);
  const signature = decode(input.signature, 64);
  const manifest = decode(input.manifest);
  if (!manifest.length || manifest.length > 65536) throw new Error('Invalid manifest length');
  const key = createPublicKey({ key: { kty: 'OKP', crv: 'Ed25519', x: rawKey.toString('base64url') }, format: 'jwk' });
  const message = Buffer.concat([Buffer.from('augmentor-release-manifest/1\0'), manifest]);
  if (!verify(null, message, key, signature)) throw new Error('Invalid signature');
  process.stdout.write('verified\n');
} catch {
  // Do not print supplied documents or environment values on failure.
  process.stderr.write('Release signature verification failed.\n');
  process.exitCode = 2;
}
