// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
/** Actual OS-store proof. Uses only two fresh synthetic entries and removes them. */
import {randomUUID} from 'node:crypto';
import {OsCredentialStore} from '../dist/codex-runtime/src/credentials.js';

const store = new OsCredentialStore();
const first = 'codex-proof-' + randomUUID(), second = 'codex-proof-' + randomUUID();
const value = 'synthetic-credential-' + randomUUID(), updated = 'synthetic-update-' + randomUUID();
const owned = [];
const require = (condition, message) => {if (!condition) throw Error(message);};
try {
  for (const reference of [first, second]) {
    require(await store.get(reference) === undefined, 'Synthetic credential reference already exists.');
    owned.push(reference); // A failed acknowledgment may still have written it.
    await store.put(reference, value);
    require(await store.get(reference) === value, 'Native OS credential read differs from the saved value.');
  }
  await store.put(first, updated);
  require(await store.get(first) === updated, 'Native OS credential update did not persist.');
  await store.delete(first); await store.delete(first);
  require(await store.get(first) === undefined, 'Native OS credential removal did not persist.');
  require(await store.get(second) === value, 'Removing one native credential affected another reference.');
} finally {
  let cleanupError;
  for (const reference of owned) {
    try {
      await store.delete(reference);
      require(await store.get(reference) === undefined, 'Synthetic native credential cleanup failed.');
    } catch (error) {cleanupError = error;}
  }
  if (cleanupError) throw cleanupError;
}
console.log(JSON.stringify({proof:'PASS', platform:process.platform,
  backend:process.platform==='darwin'?'macOS Keychain':'Secret Service',
  roundTrip:true, update:true, referenceIsolation:true, idempotentRemoval:true, cleanup:true}));
