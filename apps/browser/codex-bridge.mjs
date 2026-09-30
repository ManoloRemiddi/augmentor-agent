// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.

import {PiConnection} from '../../dist/client/src/socket.js';
import {homedir} from 'node:os';
import {join} from 'node:path';
import {mkdir} from 'node:fs/promises';
import {promptLibrary} from './shared/prompts.mjs';
import {surfaceRequest} from './shared/surface.mjs';
import {supportReport} from './shared/support.mjs';
import {randomUUID} from 'node:crypto';

const preset = 'augmentor-browser-codex';
const workspace = process.env.AUGMENTOR_CODEX_BROWSER_WORKSPACE ?? join(homedir(), 'Augmentor Browser Codex');
const MAX_FRAME = 1024 * 1024;
let connection, opening, selection, currentSession;
const send = value => {
  const body = Buffer.from(JSON.stringify(value));
  if (body.length > MAX_FRAME || process.stdout.writableLength > MAX_FRAME * 4) throw new Error('Browser connection is backpressured.');
  const header = Buffer.alloc(4); header.writeUInt32LE(body.length); process.stdout.write(Buffer.concat([header, body]));
};
async function client() {
  if (connection && !connection.closed) return connection;
  opening ??= PiConnection.open(frame => {
    if (frame.method === 'session/event') {
      send({method: 'session.event', params: frame.payload});
      const type = frame.payload.event.type;
      if (type === 'turn/start' || type === 'turn/end') send({method: 'session.status', params: {sessionId: frame.payload.sessionId, status: type === 'turn/start' ? 'running' : 'idle'}});
    } else if (frame.method === 'session/attention') send({method: 'session.attention', params: frame.payload});
  }, () => setImmediate(() => process.exit(1)), 'codex').then(value => {connection = value; return value;}).finally(() => {opening = undefined;});
  return opening;
}
async function attach(sessionId) {
  const c = await client(); await c.call('events.subscribe', {sessionId}); currentSession = sessionId;
}
async function request(method, params = {}, id) {
  if (method === 'augmentor/prompts') return promptLibrary(params);
  if (method === 'augmentor/diagnostics') return supportReport();
  if (method === 'augmentor/surface') {
    if (params.action !== 'appearance') throw new Error('Codex draft improvement is not yet available. Your draft was preserved.');
    return surfaceRequest(params);
  }
  const c = await client();
  if (method === 'augmentor/models') return c.call('models.list');
  if (method === 'augmentor/codex') {
    if (params.action === 'profiles') return c.call('profiles.list');
    if (params.action === 'test') return c.call('profiles.test', {id: params.id});
    if (params.action === 'configure') return c.call('profiles.configure', params.profile);
    throw new Error('Unsupported Codex setup action.');
  }
  if (method === 'initialize') {
    selection = {provider: params.provider, model: params.model}; await c.call('models.validate', selection);
    await mkdir(workspace, {recursive: true, mode: 0o700});
    const saved = await c.call('chats.saved');
    return {serverInfo: {home: homedir(), harness: 'codex', capabilities: {branch: false, edit: false, memory: false, voice: false, browserTools: false}, augmentor: {chatCwd: workspace, agentPreset: preset, saved: saved.saved}}};
  }
  if (method === 'session.create') {
    if (!selection) throw new Error('Select a Codex connection before starting a chat.');
    const result = await c.call(method, {...params, surface: 'browser', selection, cwd: workspace});
    await attach(params.sessionId); return result;
  }
  if (method === 'session.attach') {
    const {items} = await c.call('session.list');
    const row = items.find(value => value.sessionId === params.sessionId);
    if (!row) throw new Error('Codex conversation not found.');
    // Explicit attachment may share an existing native conversation; account binding stays in the host.
    await c.call('session.create', {sessionId: row.sessionId, cwd: row.cwd});
    await attach(params.sessionId); selection = row.selection;
    return {attached: true, running: row.running === true};
  }
  if (method === 'session.prompt') {if (currentSession !== params.sessionId) await attach(params.sessionId); return c.call(method, {...params, requestId: params.requestId ?? randomUUID()});}
  if (method === 'session.selectModel') {const result = await c.call(method, params); selection = result.current; return result;}
  if (method === 'session.list') {
    const {items} = await c.call(method); return {items: items.map(row => ({...row, projections: {values: {title: row.title}}})), total: items.length};
  }
  if (['augmentor/save', 'augmentor/unsave', 'augmentor/state'].includes(method)) return {ok: true, ...await c.call('chats.saved', {action: method.split('/')[1], sessionId: params.sessionId})};
  if (['session.cancel', 'session.rename', 'session.models', 'session.history', 'settings.describe'].includes(method)) return c.call(method, params);
  if (method === 'shutdown') {connection?.close(); setTimeout(() => process.exit(0), 30); return {ok: true};}
  throw new Error('This Codex browser capability is not yet available: ' + method);
}
let buffer = Buffer.alloc(0); const pending = new Set();
process.stdin.on('data', chunk => {
  buffer = Buffer.concat([buffer, chunk]);
  if (buffer.length > MAX_FRAME * 2) process.exit(1);
  while (buffer.length >= 4) {
    const size = buffer.readUInt32LE(0); if (size > MAX_FRAME) process.exit(1); if (buffer.length < size + 4) break;
    let frame;
    try {frame = JSON.parse(buffer.subarray(4, size + 4));} catch {process.exit(1);}
    buffer = buffer.subarray(size + 4);
    if (!frame || typeof frame.method !== 'string' || !['string', 'number'].includes(typeof frame.id) || pending.has(frame.id) || pending.size >= 32) process.exit(1);
    pending.add(frame.id);
    void request(frame.method, frame.params, frame.id).then(result => send({id: frame.id, result}), error => send({id: frame.id, error: {message: error.message}})).finally(() => pending.delete(frame.id));
  }
});
process.stdin.on('end', () => {connection?.close(); process.exit(0);});
process.on('SIGTERM', () => {connection?.close(); process.exit(0);});
