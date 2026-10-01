// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
/** Actual OS-store proof. Uses only fresh synthetic entries and removes them. */
import {randomUUID} from 'node:crypto';
import {mkdtempSync, readFileSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {OsCredentialStore} from '../dist/codex-runtime/src/credentials.js';
import {ChatGptAccounts} from '../dist/codex-runtime/src/chatgpt-accounts.js';

const store = new OsCredentialStore();
const first = 'codex-proof-' + randomUUID(), second = 'codex-proof-' + randomUUID();
const value = 'synthetic-credential-' + randomUUID(), updated = 'synthetic-update-' + randomUUID();
const owned = [];
const accountRoot = mkdtempSync(join(tmpdir(), 'augmentor-codex-account-proof-'));
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
  const protectedStore = {get:reference=>store.get(reference), delete:reference=>store.delete(reference),
    put:async(reference, credential)=>{
      require(await store.get(reference) === undefined, 'Synthetic account reference already exists.');
      owned.push(reference); await store.put(reference,credential);
    }};
  const renewal = {refresh:async grant=>({...grant,accessToken:updated,refreshToken:updated,expiresAt:Date.now()+3600000}),
    revoke:async()=>({confirmed:true})}; // Account storage proof; no remote OAuth/inference.
  const accountPath = join(accountRoot,'accounts.json');
  const accounts = new ChatGptAccounts(accountPath,protectedStore,renewal);
  const account = await accounts.save({issuer:'https://auth.openai.com',subject:'synthetic-native-store-proof',clientId:'oaiapp_synthetic_native_store',
    idToken:value,accessToken:value,refreshToken:value,expiresAt:Date.now()+1000,
    scopes:['openid','chatgpt.tokens.use.direct'],planUsage:true});
  require(!readFileSync(accountPath,'utf8').includes(value),'Synthetic token leaked into the account index.');
  require((await accounts.access(account.id)).refreshToken === updated,'Rotated synthetic account token did not persist.');
  const restored = new ChatGptAccounts(accountPath,protectedStore,renewal);
  require((await restored.access(account.id)).accessToken === updated,'Native account restart lost the replacement token.');
  const logout = await restored.signOut(account.id);
  require(logout.localCleanupConfirmed,'Synthetic account logout failed native cleanup.');
  require((await restored.registration(account.id)).clientId==='oaiapp_synthetic_native_store','Logout removed the synthetic registration.');
  require(await store.get(second)===value,'Synthetic account operations affected another credential.');
} finally {
  let cleanupError;
  for (const reference of owned) {
    try {
      await store.delete(reference);
      require(await store.get(reference) === undefined, 'Synthetic native credential cleanup failed.');
    } catch (error) {cleanupError = error;}
  }
  rmSync(accountRoot,{recursive:true,force:true});
  if (cleanupError) throw cleanupError;
}
console.log(JSON.stringify({proof:'PASS', platform:process.platform,
  backend:process.platform==='darwin'?'macOS Keychain':'Secret Service',
  roundTrip:true, update:true, referenceIsolation:true, idempotentRemoval:true,
  accountRoundTrip:true, rotatingTokenPersistence:true, accountRestart:true, accountLogout:true, cleanup:true}));
