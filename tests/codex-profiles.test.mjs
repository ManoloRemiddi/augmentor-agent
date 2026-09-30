// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync, rmSync, readFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {ProfileStore} from '../dist/codex-runtime/src/profiles.js';
function fixture(t) {
  const root = mkdtempSync(join(tmpdir(), 'codex-profile-')); t.after(() => rmSync(root, {recursive: true, force: true}));
  const secrets = new Map(); const credentials = {get: async id => secrets.get(id), put: async (id, value) => {secrets.set(id, value);}, delete: async id => {secrets.delete(id);}};
  const store = new ProfileStore(join(root, 'profiles.json'), credentials);
  return {store, secrets, credentials};
}
const profile = {id: 'api-one', name: 'Test provider', kind: 'api', model: 'test-model', endpoint: 'https://provider.example/v1'};
test('Codex profiles persist only credential references and retrieve the selected secret privately', async t => {
  const {store, secrets, credentials} = fixture(t);
  const publicProfile = await store.upsert({...profile, credential: 'synthetic-key-one'});
  assert.equal(publicProfile.credentialConfigured, true);
  assert.equal(publicProfile.credentialRef, undefined);
  assert.ok(!readFileSync(store.path, 'utf8').includes('synthetic-key-one'));
  assert.equal((await store.resolve(profile.id)).connection.credential, 'synthetic-key-one');
  const restored = new ProfileStore(store.path, credentials);
  await restored.upsert({...profile, credential: 'synthetic-key-two'});
  assert.equal(secrets.size, 1);
  assert.equal((await restored.resolve(profile.id)).connection.credential, 'synthetic-key-two');
  assert.equal(restored.list()[0].revision, 2);
});
test('Codex profile setup never silently redirects credentials or bypasses login', async t => {
  const {store} = fixture(t); await store.upsert({...profile, credential: 'synthetic-key'});
  await assert.rejects(store.upsert({...profile, endpoint: 'https://another.example/v1'}), /destination/);
  await assert.rejects(store.upsert({...profile, kind: 'chatgpt-plan'}), /supported login/);
  await assert.rejects(store.upsert({...profile, endpoint: 'https://user:secret@provider.example/v1'}), /URLs/);
  await store.upsert({...profile, endpoint: 'https://another.example/v1', credential: null});
  assert.equal((await store.resolve(profile.id)).connection.credential, undefined);
});
test('failed keychain writes leave the previous connection intact with no plaintext fallback', async t => {
  const {store, credentials} = fixture(t); await store.upsert({...profile, credential: 'original'});
  const before = readFileSync(store.path, 'utf8');
  credentials.put = async () => {throw new Error('keychain locked');};
  await assert.rejects(store.upsert({...profile, credential: 'replacement'}), /locked/);
  assert.equal(readFileSync(store.path, 'utf8'), before);
  assert.equal((await store.resolve(profile.id)).connection.credential, 'original');
});
test('concurrent profile replacements have ordered revisions and retired secrets are removed', async t => {
  const {store, secrets} = fixture(t);
  await Promise.all([store.upsert({...profile, credential: 'first'}), store.upsert({...profile, credential: 'second'})]);
  assert.equal(store.list()[0].revision, 2); assert.equal(secrets.size, 1);
  assert.equal((await store.resolve(profile.id)).connection.credential, 'second');
});
test('local profiles need no keychain and stored credential loss is explicit', async t => {
  const {store, credentials, secrets} = fixture(t);
  credentials.put = async () => {throw new Error('unavailable');};
  await store.upsert({...profile, kind: 'local', endpoint: 'http://127.0.0.1:8080/v1'});
  assert.equal((await store.resolve(profile.id)).connection.kind, 'local');
  credentials.put = async (id, value) => {secrets.set(id, value);};
  await store.upsert({...profile, credential: 'temporary'}); secrets.clear();
  await assert.rejects(store.resolve(profile.id), /credential is missing/);
});
test('renaming a profile preserves its connection identity and stale checks cannot validate a new model', async t => {
  const {store} = fixture(t); await store.upsert(profile); await store.validated(profile.id, 1);
  await store.upsert({...profile, name: 'Renamed'});
  assert.equal(store.list()[0].revision, 1); assert.equal(store.list()[0].validation, 'responses-text');
  await store.upsert({...profile, model: 'changed-model'});
  await assert.rejects(store.validated(profile.id, 1), /changed/);
  assert.equal(store.list()[0].validation, 'unverified');
});

test('image qualification is host-owned, retained on rename and invalidated by connection changes', async t => {
  const {store, credentials} = fixture(t);
  await store.upsert({...profile, imageValidatedAt: Date.now(), imageInput: true});
  assert.equal((await store.resolve(profile.id)).connection.imageInput, false);
  await store.validated(profile.id, 1, 'image');
  await store.upsert({...profile, name: 'Renamed'});
  const restored = new ProfileStore(store.path, credentials);
  assert.equal((await restored.resolve(profile.id)).connection.imageInput, true);
  assert.ok(restored.list()[0].imageValidatedAt > 0);
  await restored.upsert({...profile, model: 'other'});
  assert.equal((await restored.resolve(profile.id)).connection.imageInput, false);
  await assert.rejects(restored.validated(profile.id, 1, 'image'), /changed/);
  await restored.validated(profile.id, 2, 'text');
  assert.equal((await restored.resolve(profile.id)).connection.imageInput, false);
  await restored.validated(profile.id, 2, 'image');
  await restored.upsert({...profile, model: 'other', credential: 'replacement'});
  assert.equal((await restored.resolve(profile.id)).connection.imageInput, false);
});
