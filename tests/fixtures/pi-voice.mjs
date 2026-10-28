// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Real private Host/SDK with independent speech/provider fixtures, never owner state.
import assert from 'node:assert/strict';
import {once} from 'node:events';
import {mkdtemp,writeFile,rm} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {tmpdir} from 'node:os';
import {pathToFileURL} from 'node:url';
import {WebSocket} from 'ws';
import {planFixture,until} from './plans.mjs';
import {createSyntheticVoicePeer} from './codex/synthetic-voice-peer.mjs';
const artifact=resolve(process.env.AUGMENTOR_PI_TEST_ROOT??'.');
const {privateDir,atomicJson}=await import(pathToFileURL(join(artifact,'dist/runtime/src/storage.js')));
export async function piVoiceFixture(t, {peerOptions, ...options} = {}) {
  const peer = createSyntheticVoicePeer({harnesses: ['pi'], ...peerOptions}), home = process.platform === 'win32' ? privateDir(join(tmpdir(), 'augmentor-speech-profile-' + crypto.randomUUID())) : privateDir(await mkdtemp(join(tmpdir(), 'augmentor-speech-profile-')));
  let f, ticketCalls = 0; const cleanup = [];
  t.after(async () => {for (const close of cleanup.reverse()) await close(); await f?.stop(); await peer.close(); await rm(home, {recursive: true, force: true, maxRetries: 5, retryDelay: 100});});
  await peer.listen(); peer.server.on('request', req => {if (req.url === '/internal/ticket') ticketCalls++;});
  atomicJson(join(home, 'config.json'), {port: Number(new URL(peer.connection.base).port)});
  // The Windows private-record writer creates a protected file atomically;
  // replacing its bytes preserves that ACL and the peer's raw-token protocol.
  if (process.platform === 'win32') atomicJson(join(home, 'token'), null);
  await writeFile(join(home, 'token'), peer.connection.token + '\n', {mode: 0o600});
  f = await planFixture(t, {...options, voiceMode: {home}});
  const create = async (sid = 'voice-root', surface = 'linux') => {await f.call('session.create', {sessionId: sid, surface, selection: f.selection, cwd: f.workspace}); await f.call('events.subscribe', {sessionId: sid});};
  const connect = async (sid = 'voice-root', surface = 'linux', openId) => {
    const ticket = await f.call('voice.ticket', {sessionId: sid, surface,...(openId===undefined?{}:{openId})});
    assert.deepEqual(Object.keys(ticket).sort(), ['protocol', 'sessionId', 'ticket', 'url']);
    const socket = new WebSocket(ticket.url), messages = [];
    socket.on('message', (data, binary) => {if (!binary) messages.push(JSON.parse(data));});
    await once(socket, 'open'); socket.send(JSON.stringify({type: 'auth', ticket: ticket.ticket, textSource: 'plugin'}));
    await until(() => messages.some(row => row.type === 'ready'), 'speech authentication'); return {socket, messages};
  };
  return {...f, peer, create, connect, ticketCalls: () => ticketCalls, beforeClose: close => cleanup.push(close)};
}
