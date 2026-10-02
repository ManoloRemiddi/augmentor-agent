// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {mkdtempSync, readFileSync, rmSync, writeFileSync, chmodSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {generateKeyPair, exportJWK, SignJWT} from 'jose';
import {ChatGptAuthorization, ChatGptRefreshError, chatGptHostId} from '../dist/codex-runtime/src/chatgpt-auth.js';

const issuer = 'https://auth.openai.com';
const clientId = 'oaiapp_synthetic-registration';
const hostId = 'urn:uuid:dc9dcf86-7701-4244-b45c-449043e665cd';
const key = await generateKeyPair('RS256');
const foreignKey = await generateKeyPair('RS256');
const jwk = {...await exportJWK(key.publicKey), kid: 'fixture-key', alg: 'RS256', use: 'sig'};
function fixture(t, config = {}) {
  let opened; const calls = []; const issued = []; let release;
  const barrier = new Promise(yes => {release = yes;});
  const transport = async (url, init) => {
    calls.push({url: String(url), init});
    if (String(url).endsWith('openid-configuration')) return Response.json({
      issuer, authorization_endpoint: `${issuer}/api/accounts/authorize`, token_endpoint: `${issuer}/api/accounts/oauth/token`,
      jwks_uri: `${issuer}/.well-known/jwks.json`, id_token_signing_alg_values_supported: ['RS256'], ...config.metadata,
      revocation_endpoint: config.revocationEndpoint ?? `${issuer}/oauth/revoke`,
    });
    if (String(url).endsWith('jwks.json')) return Response.json({keys: [jwk]});
    if (String(url).endsWith('/oauth/revoke')) {
      const body = new URLSearchParams(init.body);
      assert.equal(body.get('client_id'), clientId); assert.equal(body.get('token_type_hint'), 'refresh_token');
      assert.equal(body.get('token'), 'synthetic-refresh');
      if (config.revokeNetworkError) throw new Error('DO-NOT-ECHO');
      return new Response(null, {status: config.revokeStatuses?.shift() ?? 200});
    }
    if (String(url).endsWith('/oauth/token')) {
      const form = new URLSearchParams(init.body);
      if (form.get('grant_type') === 'refresh_token') {
        assert.equal(form.get('client_id'), clientId); assert.equal(form.get('refresh_token'), 'synthetic-refresh');
        assert.equal(form.get('resource'), 'https://api.openai.com/v1'); assert.equal(form.has('scope'), false);
        assert.equal(form.has('client_secret'), false);
        if (config.refreshNetworkError) throw new Error('DO-NOT-ECHO-SYNTHETIC-SECRET');
        if (config.refreshStatus) return Response.json({error: config.refreshError, error_description: 'DO-NOT-ECHO'}, {status: config.refreshStatus});
        return Response.json({access_token: 'rotated-access', refresh_token: 'rotated-refresh', token_type: 'Bearer', expires_in: 3600, ...config.refresh});
      }
      if (config.pauseExchange) await barrier;
      if (config.tokenStatus) return Response.json({error: config.tokenError, error_description: 'DO-NOT-ECHO-SYNTHETIC-SECRET'}, {status: config.tokenStatus});
      const body = new URLSearchParams(init.body);
      assert.equal(body.get('client_id'), config.registration?.clientId ?? clientId);
      assert.equal(body.get('grant_type'), 'authorization_code');
      assert.equal(body.get('resource'), 'https://api.openai.com/v1');
      assert.equal(body.get('redirect_uri'), opened.searchParams.get('redirect_uri'));
      assert.equal(createHash('sha256').update(body.get('code_verifier')).digest('base64url'), opened.searchParams.get('code_challenge'));
      assert.equal(body.has('client_secret'), false);
      const now = Math.floor(Date.now()/1000);
      const claims = {iss: issuer, aud: config.registration?.clientId ?? clientId, sub: 'fixture-subject',
        nonce: opened.searchParams.get('nonce'), iat: now, exp: now + 3600, email: 'synthetic@example.invalid', ...config.claims};
      const idToken = await new SignJWT(claims).setProtectedHeader({alg: 'RS256', kid: 'fixture-key'}).sign((config.foreignSignature ? foreignKey : key).privateKey);
      return Response.json({id_token: idToken, access_token: 'synthetic-access', refresh_token: 'synthetic-refresh', token_type: 'Bearer',
        expires_in: 3600, scope: 'openid profile email resource.invoke chatgpt.tokens.use.direct', ...config.token});
    }
    throw new Error('Unexpected auth request');
  };
  const auth = new ChatGptAuthorization({hostId, enabled: true, fetch: transport}); t.after(() => {release(); auth.cancel();});
  const start = async () => auth.start({registration: config.registration, signal: config.signal,
    issuedClientId: config.issuedClientId, requestPlanUsage: config.requestPlanUsage,
    openBrowser: async value => {opened = new URL(value); if (config.browserError) throw new Error('synthetic-private-url');},
    onRegistration: async id => {issued.push(id); if (config.registrationError) throw new Error('storage locked');},
  });
  const callback = async (overrides = {}, fields = {}) => {
    const url = new URL(opened.searchParams.get('redirect_uri'));
    const params = {state: opened.searchParams.get('state'), code: 'synthetic-code', client_id: clientId, ...overrides};
    for (const [name, value] of Object.entries(params)) if (value !== undefined) url.searchParams.set(name, value);
    for (const [name, value] of Object.entries(fields)) url.searchParams.append(name, value);
    return fetch(url);
  };
  return {auth, start, callback, calls, issued, release, get opened() {return opened;}, get exchanges() {return calls.filter(call => call.url.endsWith('/oauth/token'));}};
}

test('ChatGPT installation identity persists across restart and rejects exposed/corrupt files', t => {
  const root = mkdtempSync(join(tmpdir(), 'codex-chatgpt-auth-')); t.after(() => rmSync(root, {recursive: true, force: true}));
  const path = join(root, 'host.json'); const id = chatGptHostId(path);
  assert.match(id, /^urn:uuid:/); assert.equal(chatGptHostId(path), id);
  assert.deepEqual(Object.keys(JSON.parse(readFileSync(path))), ['schema', 'hostId']);
  chmodSync(path, 0o644); assert.throws(() => chatGptHostId(path), /private/);
  chmodSync(path, 0o600); writeFileSync(path, JSON.stringify({schema: 1, hostId: 'bad'}));
  assert.throws(() => chatGptHostId(path), /identity/);
});
test('public ChatGPT login remains disabled without confirmed eligibility', async () => {
  let requested = false;
  const auth = new ChatGptAuthorization({hostId, fetch: async () => {requested = true; throw new Error();}});
  await assert.rejects(auth.start({openBrowser: async () => {requested = true;}}), /eligibility/);
  assert.equal(requested, false);
});
test('new registration binds actual loopback callback, fresh PKCE and signed identity', async t => {
  const f = fixture(t); const attempt = await f.start();
  assert.equal(f.opened.origin, issuer); assert.equal(f.opened.searchParams.get('client_id'), 'dynamic_agent_client');
  assert.equal(f.opened.searchParams.get('agent_name_hint'), 'augmentor_agent');
  assert.equal(f.opened.searchParams.get('ext_agent_host_id'), hostId);
  assert.equal(f.opened.searchParams.get('code_challenge_method'), 'S256');
  assert.equal(new URL(f.opened.searchParams.get('redirect_uri')).hostname, '127.0.0.1');
  const response = await f.callback(); assert.equal(response.status, 200); assert.equal(response.headers.get('cache-control'), 'no-store');
  assert.doesNotMatch(await response.text(), /synthetic-(access|refresh|code)|fixture-subject/);
  const grant = await attempt.result;
  assert.deepEqual(f.issued, [clientId]); assert.equal(f.exchanges.length, 1);
  assert.equal(grant.subject, 'fixture-subject'); assert.equal(grant.clientId, clientId); assert.equal(grant.planUsage, true);
  assert.equal(grant.accessToken, 'synthetic-access'); assert.ok(grant.expiresAt > Date.now());
});
test('invalid state, duplicate callback parameters and wrong method never exchange or consume a valid attempt', async t => {
  const f = fixture(t); const attempt = await f.start();
  assert.equal((await f.callback({state: 'wrong'})).status, 400);
  assert.equal((await f.callback({}, {code: 'ambiguous'})).status, 400);
  assert.equal((await fetch(f.opened.searchParams.get('redirect_uri'), {method: 'POST'})).status, 400);
  assert.equal(f.exchanges.length, 0); await f.callback(); assert.equal((await attempt.result).planUsage, true);
});
test('single-use callback prevents racing duplicate exchanges', async t => {
  const f = fixture(t, {pauseExchange: true}); const attempt = await f.start();
  await f.callback(); assert.equal((await f.callback()).status, 409); assert.equal(f.exchanges.length, 1);
  f.release(); await attempt.result; assert.equal(f.exchanges.length, 1);
});
test('declined authorization validates state first and does not exchange a code', async t => {
  const f = fixture(t); const attempt = await f.start();
  assert.equal((await f.callback({state: 'wrong', error: 'access_denied'})).status, 400);
  await f.callback({error: 'access_denied'}); await assert.rejects(attempt.result, /declined/); assert.equal(f.exchanges.length, 0);
});
test('returning registration retains issued client and host, sends hint only to auth, omits new-agent naming', async t => {
  const registration = {issuer, subject: 'fixture-subject', clientId, idTokenHint: 'synthetic-old-id-token', email: 'synthetic@example.invalid'};
  const f = fixture(t, {registration}); const attempt = await f.start();
  assert.equal(f.opened.searchParams.get('client_id'), clientId); assert.equal(f.opened.searchParams.get('agent_name_hint'), null);
  assert.equal(f.opened.searchParams.get('id_token_hint'), registration.idTokenHint);
  await f.callback({client_id: undefined}); await attempt.result;
  assert.deepEqual(f.issued, []); assert.deepEqual(registration, {issuer, subject: 'fixture-subject', clientId, idTokenHint: 'synthetic-old-id-token', email: 'synthetic@example.invalid'});
  assert.doesNotMatch(String(f.exchanges[0].init.body), /synthetic-old-id-token/);
});
for (const returnedId of [undefined, 'dynamic_agent_client', 'other-client']) test(`new registration rejects unusable issued ID ${returnedId}`, async t => {
  const f = fixture(t); const attempt = await f.start(); await f.callback({client_id: returnedId});
  await assert.rejects(attempt.result, /verified/); assert.equal(f.exchanges.length, 0); assert.deepEqual(f.issued, []);
});
test('returning client mismatch rejects before exchange; subject mismatch never replaces selected account', async t => {
  const registration = {issuer, subject: 'original-subject', clientId};
  const f = fixture(t, {registration}); let attempt = await f.start(); await f.callback({client_id: 'oaiapp_another-registration'});
  await assert.rejects(attempt.result, /verified/); assert.equal(f.exchanges.length, 0);
  attempt = await f.start(); await f.callback(); await assert.rejects(attempt.result, /different account/);
  assert.equal(registration.subject, 'original-subject'); assert.deepEqual(f.issued, []);
});
for (const [name, config] of [
  ['foreign signature', {foreignSignature: true}], ['issuer', {claims: {iss: 'https://foreign.invalid'}}],
  ['audience', {claims: {aud: 'oaiapp_foreign'}}], ['nonce', {claims: {nonce: 'wrong'}}],
  ['expiration', {claims: {exp: 1}}], ['missing subject', {claims: {sub: ''}}],
  ['additional audience without authorized party', {claims: {aud: [clientId, 'oaiapp_other']}}],
]) test(`signed ChatGPT identity rejects ${name}`, async t => {
  const f = fixture(t, config); const attempt = await f.start(); await f.callback();
  await assert.rejects(attempt.result, /verified/); assert.equal(f.exchanges.length, 1);
});
test('identity-only consent uses token response scopes rather than claimed callback permission', async t => {
  const f = fixture(t, {token: {scope: 'openid email', access_token: undefined, refresh_token: undefined}});
  const attempt = await f.start(); await f.callback({scope: 'chatgpt.tokens.use.direct'}); const grant = await attempt.result;
  assert.equal(grant.planUsage, false); assert.equal(grant.accessToken, undefined); assert.deepEqual(grant.scopes, ['openid', 'email']);
});
test('plan permission without an access token is rejected', async t => {
  const f = fixture(t, {token: {access_token: undefined}}); const attempt = await f.start(); await f.callback();
  await assert.rejects(attempt.result, /verified/);
});
test('expired authorization retains provisional client ID, never retries code or echoes provider details', async t => {
  const f = fixture(t, {tokenStatus: 400, tokenError: 'invalid_grant'}); const attempt = await f.start(); await f.callback();
  await assert.rejects(attempt.result, error => /expired/.test(error.message) && !error.message.includes('DO-NOT-ECHO'));
  assert.deepEqual(f.issued, [clientId]); assert.equal(f.exchanges.length, 1);
});
test('provisional-registration storage failure prevents exchange', async t => {
  const f = fixture(t, {registrationError: true}); const attempt = await f.start(); await f.callback();
  await assert.rejects(attempt.result, /verified/); assert.equal(f.exchanges.length, 0);
});
test('an incomplete first exchange can restart authorization with its retained issued client ID', async t => {
  const f = fixture(t, {issuedClientId:clientId}); const attempt = await f.start();
  assert.equal(f.opened.searchParams.get('client_id'),clientId);
  assert.equal(f.opened.searchParams.has('agent_name_hint'),false);
  await f.callback({client_id:undefined}); assert.equal((await attempt.result).clientId,clientId);
});
test('ordinary login does not force consent; explicit plan-permission request uses supported OAuth consent', async t => {
  const normal=fixture(t); const a=await normal.start();assert.equal(normal.opened.searchParams.has('prompt'),false);a.cancel();await assert.rejects(a.result,/cancelled/);
  const consent=fixture(t,{requestPlanUsage:true});const b=await consent.start();
  assert.equal(consent.opened.searchParams.get('prompt'),'consent');assert.equal(consent.opened.searchParams.has('force_reconsent'),false);
  assert.ok(consent.opened.searchParams.get('scope').includes('chatgpt.tokens.use.direct'));
  await consent.callback();await b.result;
});
test('cancelled sign-in cannot deliver late credentials; next attempt gets fresh state and nonce', async t => {
  const f = fixture(t, {pauseExchange: true}); const attempt = await f.start(); const old = new URL(f.opened);
  await f.callback(); attempt.cancel(); await assert.rejects(attempt.result, /cancelled/); f.release();
  const next = await f.start(); assert.notEqual(f.opened.searchParams.get('state'), old.searchParams.get('state'));
  assert.notEqual(f.opened.searchParams.get('nonce'), old.searchParams.get('nonce'));
  await f.callback(); assert.equal((await next.result).planUsage, true);
});
test('abort signal and browser launch failure close listener without leaking URL/hint', async t => {
  const controller = new AbortController(); const f = fixture(t, {signal: controller.signal}); const attempt = await f.start();
  const uri = f.opened.searchParams.get('redirect_uri'); controller.abort(); await assert.rejects(attempt.result, /cancelled/);
  await assert.rejects(fetch(uri));
  const fail = fixture(t, {browserError: true}); const failed = await fail.start();
  await assert.rejects(failed.result, error => /verified/.test(error.message) && !error.message.includes('synthetic-private'));
});
test('concurrent login is rejected and malicious discovery cannot send codes/tokens to another origin', async t => {
  const f = fixture(t); const attempt = await f.start(); await assert.rejects(f.start(), /already pending/); attempt.cancel();
  await assert.rejects(attempt.result, /cancelled/);
  const bad = fixture(t, {metadata: {token_endpoint: 'https://foreign.invalid/token'}}); const failed = await bad.start();
  await assert.rejects(failed.result, /verified/); assert.equal(bad.opened, undefined); assert.equal(bad.calls.length, 1);
});

async function signedGrant(f) {const attempt = await f.start(); await f.callback(); return attempt.result;}
test('refresh exchanges the selected issued client and rotates both tokens without changing account or scope', async t => {
  const f = fixture(t); const grant = await signedGrant(f); const renewed = await f.auth.refresh(grant);
  assert.equal(renewed.clientId, clientId); assert.equal(renewed.subject, grant.subject);
  assert.equal(renewed.accessToken, 'rotated-access'); assert.equal(renewed.refreshToken, 'rotated-refresh');
  assert.equal(renewed.idToken, grant.idToken); assert.deepEqual(renewed.scopes, grant.scopes);
  assert.equal(grant.refreshToken, 'synthetic-refresh');
});
for (const [error, recovery, status] of [
  ['invalid_grant', 'sign-in', 400], ['refresh_token_reused', 'sign-in', 400],
  ['invalid_client', 'configuration', 400], ['server_error', 'retry-later', 503],
]) test(`refresh handles ${error} without echoing diagnostics or retrying`, async t => {
  const f = fixture(t, {refreshStatus: status, refreshError: error}); const grant = await signedGrant(f);
  await assert.rejects(f.auth.refresh(grant), value => value instanceof ChatGptRefreshError && value.recovery === recovery && !value.message.includes('DO-NOT-ECHO'));
  assert.equal(f.exchanges.length, 2); assert.equal(grant.refreshToken, 'synthetic-refresh');
});
test('lost refresh response and missing replacement token remain unconfirmed, never replayed', async t => {
  for (const config of [{refreshNetworkError: true}, {refresh: {refresh_token: undefined}}]) {
    const f = fixture(t, config); const grant = await signedGrant(f);
    await assert.rejects(f.auth.refresh(grant), error => error.recovery === 'unconfirmed');
    assert.equal(f.exchanges.length, 2);
  }
});
test('refresh respects earliest time and a removed plan grant', async t => {
  const f = fixture(t, {refresh: {scope: 'openid profile'}}); const grant = await signedGrant(f);
  await assert.rejects(f.auth.refresh({...grant, earliestRefreshAt: Date.now()+60000}), error => error.recovery === 'retry-later');
  assert.equal(f.exchanges.length, 1);
  const renewed = await f.auth.refresh(grant); assert.equal(renewed.planUsage, false);
});
test('refresh rejects a newly signed ID token bound to another identity', async t => {
  const now = Math.floor(Date.now()/1000);
  const wrong = await new SignJWT({iss:issuer,aud:clientId,sub:'another-subject',iat:now,exp:now+3600})
    .setProtectedHeader({alg:'RS256',kid:'fixture-key'}).sign(key.privateKey);
  const f = fixture(t, {refresh:{id_token:wrong}}); const grant = await signedGrant(f);
  await assert.rejects(f.auth.refresh(grant), error => error.recovery === 'unconfirmed');
});
test('revocation accepts empty success, uses discovery and retries at most once after infrastructure failure', async t => {
  const f = fixture(t, {revokeStatuses:[503,200]}); const grant = await signedGrant(f);
  assert.deepEqual(await f.auth.revoke(grant), {confirmed:true});
  assert.equal(f.calls.filter(call => call.url.endsWith('/oauth/revoke')).length,2);
  assert.equal(f.exchanges.length,1);
});
test('failed or foreign revocation reports lack of confirmation without exposing tokens', async t => {
  const f = fixture(t, {revokeNetworkError:true}); const grant = await signedGrant(f);
  assert.deepEqual(await f.auth.revoke(grant), {confirmed:false});
  assert.equal(f.calls.filter(call => call.url.endsWith('/oauth/revoke')).length,2);
  const foreign = fixture(t, {revocationEndpoint:'https://foreign.invalid/revoke'});
  const attempt = await foreign.start(); await assert.rejects(attempt.result,/verified/);
  assert.equal(foreign.opened,undefined); assert.equal(foreign.calls.length,1);
});
