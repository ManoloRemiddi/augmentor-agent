// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {createHash, randomBytes, randomUUID, timingSafeEqual} from 'node:crypto';
import {createServer, type Server} from 'node:http';
import {createRemoteJWKSet, customFetch, jwtVerify, type RemoteJWKSet} from 'jose';
import {durableJson, readPrivateJson} from './storage.js';

const ISSUER = 'https://auth.openai.com';
const RESOURCE = 'https://api.openai.com/v1';
const DIRECT_SCOPE = 'chatgpt.tokens.use.direct';
const SCOPES = `openid profile email offline_access resource.invoke ${DIRECT_SCOPE}`;
const CLIENT = /^oaiapp_[A-Za-z0-9_-]{1,200}$/;
const HOST = /^urn:uuid:[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/;
const MAX_BODY = 262144;
const FAILURE = 'ChatGPT sign-in could not be verified. Start a new sign-in.';

/** Installation identity only. Tokens and login hints never enter this file. */
export function chatGptHostId(path: string): string {
  let value: any;
  try {value = readPrivateJson(path);}
  catch (error: any) {if (error?.code !== 'ENOENT') throw error;}
  if (value === undefined) {
    value = {schema: 1, hostId: `urn:uuid:${randomUUID()}`};
    durableJson(path, value);
  }
  if (value?.schema !== 1 || typeof value.hostId !== 'string' || !HOST.test(value.hostId)) {
    throw new Error('Invalid saved ChatGPT installation identity.');
  }
  return value.hostId;
}

export interface ChatGptRegistration {
  issuer: string;
  subject: string;
  clientId: string;
  /** Read from protected storage; never expose the authorization URL to a UI/log. */
  idTokenHint?: string;
  email?: string;
}
/** Internal host result, not a surface RPC response. Persist only in the OS store. */
export interface VerifiedChatGptGrant {
  issuer: string;
  subject: string;
  clientId: string;
  email?: string;
  idToken: string;
  accessToken?: string;
  refreshToken?: string;
  expiresAt?: number;
  earliestRefreshAt?: number;
  scopes: string[];
  planUsage: boolean;
}
interface Metadata {
  issuer: string;
  authorization_endpoint: string;
  token_endpoint: string;
  jwks_uri: string;
  revocation_endpoint?: string;
  id_token_signing_alg_values_supported: string[];
}
interface AuthOptions {
  hostId: string;
  /** Distribution eligibility must be confirmed by the product owner. Default off. */
  enabled?: boolean;
  /** Internal transport seam for deterministic tests; never accepted over IPC. */
  fetch?: typeof fetch;
}
export interface ChatGptSignInAttempt {
  id: string;
  result: Promise<VerifiedChatGptGrant>;
  cancel(): void;
}
/** Safe recovery classification; never includes token-endpoint diagnostic text. */
export class ChatGptRefreshError extends Error {
  constructor(readonly recovery: 'sign-in' | 'retry-later' | 'configuration' | 'unconfirmed', readonly code?: string) {
    super(recovery === 'retry-later' ? 'ChatGPT renewal is temporarily unavailable. Try again later.' :
      recovery === 'configuration' ? 'ChatGPT client configuration needs correction.' :
      'ChatGPT credentials need a new sign-in.');
  }
}
interface Pending {
  id: string;
  server: Server;
  controller: AbortController;
  settled: boolean;
  consumed: boolean;
  timer?: NodeJS.Timeout;
  cleanupSignal?: () => void;
  finish(error?: Error, grant?: VerifiedChatGptGrant): void;
}
function secret(value: unknown): string | undefined {
  if (value === undefined) return;
  if (typeof value !== 'string' || !value || value.length > 65536 || /[\x00-\x20\x7f]/.test(value)) throw new Error(FAILURE);
  return value;
}
function same(a: string, b: string): boolean {
  const left = Buffer.from(a); const right = Buffer.from(b);
  return left.length === right.length && timingSafeEqual(left, right);
}
function trustedEndpoint(value: unknown): string {
  if (typeof value !== 'string') throw new Error(FAILURE);
  const url = new URL(value);
  if (url.origin !== ISSUER || url.username || url.password || url.search || url.hash) throw new Error(FAILURE);
  return url.href;
}

/** Shared-host OAuth transaction. No API billing fallback, legacy auth-cache access,
 * automatic browser launch, inference or account activation happens here. */
export class ChatGptAuthorization {
  private readonly transport: typeof fetch;
  private metadataPromise?: Promise<Metadata>;
  private keys?: RemoteJWKSet;
  private pending?: Pending;
  constructor(private readonly options: AuthOptions) {
    if (!HOST.test(options.hostId)) throw new Error('Invalid ChatGPT installation identity.');
    this.transport = options.fetch ?? fetch;
  }
  private async json(url: string | URL, init?: RequestInit): Promise<{status: number; body: any}> {
    const response = await this.transport(url, {...init, redirect: 'error', signal: AbortSignal.any([
      AbortSignal.timeout(15000), ...(init?.signal ? [init.signal] : []),
    ])});
    const reader = response.body?.getReader(); let size = 0; const chunks: Uint8Array[] = [];
    try {
      if (!reader) throw new Error(FAILURE);
      for (;;) {
        const next = await reader.read(); if (next.done) break;
        size += next.value.byteLength;
        if (size > MAX_BODY) throw new Error(FAILURE);
        chunks.push(next.value);
      }
      return {status: response.status, body: JSON.parse(Buffer.concat(chunks).toString('utf8'))};
    } finally {await reader?.cancel().catch(() => {});}
  }
  private metadata(): Promise<Metadata> {
    if (!this.metadataPromise) this.metadataPromise = this.json(`${ISSUER}/.well-known/openid-configuration`).then(({status, body}) => {
      if (status !== 200 || body?.issuer !== ISSUER || !Array.isArray(body.id_token_signing_alg_values_supported)) throw new Error(FAILURE);
      const metadata: Metadata = {...body,
        authorization_endpoint: trustedEndpoint(body.authorization_endpoint),
        token_endpoint: trustedEndpoint(body.token_endpoint), jwks_uri: trustedEndpoint(body.jwks_uri)};
      if (body.revocation_endpoint !== undefined) metadata.revocation_endpoint = trustedEndpoint(body.revocation_endpoint);
      if (metadata.authorization_endpoint !== `${ISSUER}/api/accounts/authorize` || metadata.token_endpoint !== `${ISSUER}/api/accounts/oauth/token`) throw new Error(FAILURE);
      this.keys = createRemoteJWKSet(new URL(metadata.jwks_uri), {
        timeoutDuration: 15000,
        [customFetch]: async (url, init) => {
          const result = await this.json(url, init);
          return new Response(JSON.stringify(result.body), {status: result.status, headers: {'content-type': 'application/json'}});
        },
      });
      return metadata;
    }).catch(() => {this.metadataPromise = undefined; throw new Error(FAILURE);});
    return this.metadataPromise;
  }
  async start(options: {
    /** Only an internal OS/browser adapter receives this potentially hinted URL. */
    openBrowser: (url: string) => Promise<void>;
    registration?: ChatGptRegistration;
    /** Provisional issued ID retained after an incomplete first code exchange. */
    issuedClientId?: string;
    /** Set only for the user's explicit request to enable plan usage. */
    requestPlanUsage?: boolean;
    /** Save only a provisional client ID, not a verified/active account. */
    onRegistration?: (clientId: string) => Promise<void>;
    signal?: AbortSignal;
  }): Promise<ChatGptSignInAttempt> {
    if (!this.options.enabled) throw new Error('ChatGPT login is disabled until distribution eligibility is confirmed.');
    if (this.pending) throw new Error('A ChatGPT sign-in is already pending.');
    const selected = options.registration ? {...options.registration} : undefined;
    if (options.issuedClientId !== undefined && (!CLIENT.test(options.issuedClientId) || selected && options.issuedClientId !== selected.clientId)) throw new Error('Invalid provisional ChatGPT registration.');
    const priorClientId = selected?.clientId ?? options.issuedClientId;
    if (selected && (selected.issuer !== ISSUER || !CLIENT.test(selected.clientId) || !secret(selected.subject))) throw new Error('Invalid saved ChatGPT registration.');
    if (selected?.idTokenHint) secret(selected.idTokenHint);
    if (selected?.email && (selected.email.length > 320 || /[\x00-\x1f\x7f]/.test(selected.email))) throw new Error('Invalid saved ChatGPT registration.');
    if (options.signal?.aborted) throw new Error('ChatGPT sign-in cancelled.');
    const state = randomBytes(32).toString('base64url'); const nonce = randomBytes(32).toString('base64url');
    const verifier = randomBytes(32).toString('base64url');
    let resolve!: (grant: VerifiedChatGptGrant) => void; let reject!: (error: Error) => void;
    const result = new Promise<VerifiedChatGptGrant>((yes, no) => {resolve = yes; reject = no;});
    // An early callback/cancellation can settle before the caller receives the handle.
    void result.catch(() => {});
    const server = createServer();
    server.requestTimeout = 10000; server.headersTimeout = 10000;
    const pending: Pending = {id: randomUUID(), server, controller: new AbortController(), settled: false, consumed: false,
      finish: (error, grant) => {
        if (pending.settled) return;
        pending.settled = true; pending.controller.abort(); clearTimeout(pending.timer); pending.cleanupSignal?.();
        server.close(); server.closeAllConnections();
        if (this.pending === pending) this.pending = undefined;
        if (error) reject(error); else resolve(grant!);
      },
    };
    this.pending = pending;
    const cancel = () => pending.finish(new Error('ChatGPT sign-in cancelled.'));
    if (options.signal) {
      options.signal.addEventListener('abort', cancel, {once: true});
      pending.cleanupSignal = () => options.signal?.removeEventListener('abort', cancel);
    }
    pending.timer = setTimeout(() => pending.finish(new Error('ChatGPT sign-in expired. Start a new sign-in.')), 300000);
    pending.timer.unref();
    let redirectUri = '';
    server.on('request', (request, response) => {
      response.setHeader('cache-control', 'no-store'); response.setHeader('referrer-policy', 'no-referrer');
      response.setHeader('content-type', 'text/plain; charset=utf-8'); response.setHeader('x-content-type-options', 'nosniff');
      const respond = (status: number, text: string) => {response.writeHead(status); response.end(text);};
      if (!redirectUri || request.method !== 'GET' || !request.url?.startsWith('/auth/callback?') || request.url.length > 8192 || request.headers.host !== new URL(redirectUri).host) {
        respond(400, 'Invalid sign-in callback.'); return;
      }
      const callback = new URL(request.url, redirectUri);
      for (const key of callback.searchParams.keys()) if (callback.searchParams.getAll(key).length !== 1) {
        respond(400, 'Invalid sign-in callback.'); return;
      }
      if (!same(callback.searchParams.get('state') ?? '', state)) {respond(400, 'Invalid sign-in callback.'); return;}
      if (pending.consumed || pending.settled) {respond(409, 'Sign-in callback already received.'); return;}
      pending.consumed = true;
      // The response contains neither user identity nor upstream error text.
      respond(200, 'Sign-in received. Return to Augmentor Agent.');
      void (async () => {
        if (callback.searchParams.has('error')) throw new Error(callback.searchParams.get('error') === 'access_denied' ? 'ChatGPT sign-in declined.' : FAILURE);
        const code = secret(callback.searchParams.get('code') ?? undefined);
        if (!code) throw new Error(FAILURE);
        const returnedId = callback.searchParams.get('client_id');
        const clientId = returnedId ?? priorClientId;
        if (!clientId || !CLIENT.test(clientId) || (priorClientId && clientId !== priorClientId)) throw new Error(FAILURE);
        if (!selected) await options.onRegistration?.(clientId);
        if (pending.settled) return;
        const metadata = await this.metadata();
        const receivedAt = Date.now();
        const token = await this.json(metadata.token_endpoint, {method: 'POST', signal: pending.controller.signal,
          headers: {'content-type': 'application/x-www-form-urlencoded'}, body: new URLSearchParams({
            grant_type: 'authorization_code', client_id: clientId, code, code_verifier: verifier, redirect_uri: redirectUri, resource: RESOURCE,
          })});
        if (token.status !== 200) throw new Error(token.body?.error === 'invalid_grant' ? 'ChatGPT authorization expired or was already used. Start a new sign-in.' : FAILURE);
        const idToken = secret(token.body?.id_token); if (!idToken || !this.keys) throw new Error(FAILURE);
        const algorithms = metadata.id_token_signing_alg_values_supported.filter(value => ['RS256', 'PS256', 'ES256', 'EdDSA'].includes(value));
        if (!algorithms.length) throw new Error(FAILURE);
        const {payload} = await jwtVerify(idToken, this.keys, {issuer: ISSUER, audience: clientId, algorithms,
          requiredClaims: ['sub', 'exp', 'iat', 'nonce'], clockTolerance: 5});
        const subject = secret(payload.sub); if (!subject || !same(String(payload.nonce), nonce)) throw new Error(FAILURE);
        if ((payload.azp !== undefined && payload.azp !== clientId) || (Array.isArray(payload.aud) && payload.aud.length > 1 && payload.azp !== clientId)) throw new Error(FAILURE);
        if (selected && subject !== selected.subject) throw new Error('ChatGPT returned a different account. The saved account was not changed.');
        const body = token.body;
        if (body.scope !== undefined && (typeof body.scope !== 'string' || body.scope.length > 8192 || /[\x00-\x1f\x7f]/.test(body.scope))) throw new Error(FAILURE);
        const scopes = [...new Set((body.scope ?? '').split(' ').filter(Boolean))] as string[];
        const accessToken = secret(body.access_token); const refreshToken = secret(body.refresh_token);
        const planUsage = scopes.includes(DIRECT_SCOPE);
        if (accessToken && (body.token_type?.toLowerCase() !== 'bearer' || !Number.isInteger(body.expires_in) || body.expires_in < 1 || body.expires_in > 86400)) throw new Error(FAILURE);
        if (planUsage && !accessToken) throw new Error(FAILURE);
        if (body.earliest_refresh_at !== undefined && (!Number.isSafeInteger(body.earliest_refresh_at) || body.earliest_refresh_at < 0)) throw new Error(FAILURE);
        const email = typeof payload.email === 'string' && payload.email.length <= 320 && !/[\x00-\x1f\x7f]/.test(payload.email) ? payload.email : undefined;
        pending.finish(undefined, {issuer: ISSUER, subject, clientId, email, idToken, accessToken, refreshToken,
          expiresAt: accessToken ? receivedAt + body.expires_in * 1000 : undefined,
          earliestRefreshAt: body.earliest_refresh_at === undefined ? undefined : body.earliest_refresh_at * 1000,
          scopes, planUsage});
      })().catch(error => pending.finish(new Error([
        'ChatGPT sign-in declined.', 'ChatGPT returned a different account. The saved account was not changed.',
        'ChatGPT authorization expired or was already used. Start a new sign-in.',
      ].includes(error?.message) ? error.message : FAILURE)));
    });
    server.on('error', () => pending.finish(new Error('ChatGPT callback listener could not start.')));
    try {
      await new Promise<void>((yes, no) => {server.once('error', no); server.listen(0, '127.0.0.1', () => {server.removeListener('error', no); yes();});});
      if (pending.settled) throw new Error('ChatGPT sign-in cancelled.');
      const address = server.address(); if (!address || typeof address === 'string') throw new Error(FAILURE);
      redirectUri = `http://127.0.0.1:${address.port}/auth/callback`;
      const metadata = await this.metadata(); if (pending.settled) throw new Error('ChatGPT sign-in cancelled.');
      const url = new URL(metadata.authorization_endpoint);
      url.search = new URLSearchParams({response_type: 'code', client_id: priorClientId ?? 'dynamic_agent_client',
        redirect_uri: redirectUri, scope: SCOPES, resource: RESOURCE, ext_agent_host_id: this.options.hostId,
        state, nonce, code_challenge_method: 'S256', code_challenge: createHash('sha256').update(verifier).digest('base64url'),
        ...(priorClientId ? {} : {agent_name_hint: 'augmentor_agent'}),
        ...(options.requestPlanUsage ? {prompt: 'consent'} : {}),
        ...(selected?.idTokenHint ? {id_token_hint: selected.idTokenHint} : {}), ...(selected?.email ? {login_hint: selected.email} : {}),
      }).toString();
      await options.openBrowser(url.href);
      return {id: pending.id, result, cancel};
    } catch {pending.finish(new Error(FAILURE)); return {id: pending.id, result, cancel};}
  }
  cancel(): void {this.pending?.finish(new Error('ChatGPT sign-in cancelled.'));}

  /** Caller owns serialization and durable rotating-token replacement. No inference replay. */
  async refresh(grant: VerifiedChatGptGrant, signal?: AbortSignal): Promise<VerifiedChatGptGrant> {
    if (!this.options.enabled) throw new Error('ChatGPT login is disabled until distribution eligibility is confirmed.');
    if (grant.issuer !== ISSUER || !CLIENT.test(grant.clientId) || !secret(grant.subject) || !secret(grant.refreshToken)) throw new ChatGptRefreshError('sign-in');
    if (grant.earliestRefreshAt !== undefined && Date.now() < grant.earliestRefreshAt) throw new ChatGptRefreshError('retry-later');
    // Discovery completes before dispatch; its failure cannot consume a refresh token.
    let metadata: Metadata;
    try {metadata = await this.metadata();} catch {throw new ChatGptRefreshError('retry-later');}
    if (signal?.aborted) throw new ChatGptRefreshError('retry-later');
    try {
      const receivedAt = Date.now();
      const {status, body} = await this.json(metadata.token_endpoint, {method: 'POST', signal,
        headers: {'content-type': 'application/x-www-form-urlencoded'}, body: new URLSearchParams({
          grant_type: 'refresh_token', client_id: grant.clientId, refresh_token: grant.refreshToken!, resource: RESOURCE,
        })});
      if (status !== 200) {
        const unusable = ['invalid_grant', 'invalid_refresh_token', 'token_expired', 'refresh_token_expired', 'refresh_token_invalidated', 'refresh_token_reused'];
        if (unusable.includes(body?.error)) throw new ChatGptRefreshError('sign-in', body.error);
        if (body?.error === 'invalid_client') throw new ChatGptRefreshError('configuration', 'invalid_client');
        if (status === 429 || status >= 500) throw new ChatGptRefreshError('retry-later');
        throw new ChatGptRefreshError('sign-in');
      }
      const accessToken = secret(body.access_token); const refreshToken = secret(body.refresh_token);
      if (!accessToken || !refreshToken || body.token_type?.toLowerCase() !== 'bearer' ||
        !Number.isInteger(body.expires_in) || body.expires_in < 1 || body.expires_in > 86400) throw new Error();
      if (body.earliest_refresh_at !== undefined && (!Number.isSafeInteger(body.earliest_refresh_at) || body.earliest_refresh_at < 0)) throw new Error();
      if (body.scope !== undefined && (typeof body.scope !== 'string' || body.scope.length > 8192 || /[\x00-\x1f\x7f]/.test(body.scope))) throw new Error();
      const scopes: string[] = body.scope === undefined ? [...grant.scopes] : [...new Set<string>(body.scope.split(' ').filter(Boolean))];
      let idToken = grant.idToken;
      if (body.id_token !== undefined) {
        idToken = secret(body.id_token)!;
        if (!idToken || !this.keys) throw new Error();
        const algorithms = metadata.id_token_signing_alg_values_supported.filter(value => ['RS256', 'PS256', 'ES256', 'EdDSA'].includes(value));
        const {payload} = await jwtVerify(idToken, this.keys, {issuer: ISSUER, audience: grant.clientId, algorithms,
          requiredClaims: ['sub', 'exp', 'iat'], clockTolerance: 5});
        if (payload.sub !== grant.subject || (payload.azp !== undefined && payload.azp !== grant.clientId) ||
          (Array.isArray(payload.aud) && payload.aud.length > 1 && payload.azp !== grant.clientId)) throw new Error();
      }
      return {...grant, idToken, accessToken, refreshToken, expiresAt: receivedAt + body.expires_in * 1000,
        earliestRefreshAt: body.earliest_refresh_at === undefined ? undefined : body.earliest_refresh_at * 1000,
        scopes, planUsage: scopes.includes(DIRECT_SCOPE)};
    } catch (error) {
      if (error instanceof ChatGptRefreshError) throw error;
      // A lost or malformed reply may have rotated the token. Never retry it blindly.
      throw new ChatGptRefreshError('unconfirmed');
    }
  }

  /** Idempotent revocation has bounded retries. Local logout must still clear tokens. */
  async revoke(grant: VerifiedChatGptGrant, signal?: AbortSignal): Promise<{confirmed: boolean}> {
    if (!this.options.enabled) throw new Error('ChatGPT login is disabled until distribution eligibility is confirmed.');
    if (grant.issuer !== ISSUER || !CLIENT.test(grant.clientId) || !secret(grant.refreshToken)) return {confirmed: false};
    let endpoint: string | undefined;
    try {endpoint = (await this.metadata()).revocation_endpoint;} catch {return {confirmed: false};}
    if (!endpoint) return {confirmed: false};
    for (let attempt = 0; attempt < 2 && !signal?.aborted; attempt++) {
      try {
        const response = await this.transport(endpoint, {method: 'POST', redirect: 'error',
          signal: AbortSignal.any([AbortSignal.timeout(15000), ...(signal ? [signal] : [])]),
          headers: {'content-type': 'application/x-www-form-urlencoded'}, body: new URLSearchParams({
            token: grant.refreshToken!, token_type_hint: 'refresh_token', client_id: grant.clientId,
          })});
        await response.body?.cancel().catch(() => {});
        if (response.status === 200) return {confirmed: true};
        if (response.status < 500) return {confirmed: false};
      } catch { /* Report lack of confirmation; never echo the response or credentials. */ }
      if (attempt === 0) await new Promise(resolve => setTimeout(resolve, 250));
    }
    return {confirmed: false};
  }
}
