// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Actual Host, SDK, private IPC/config and queue. Independent synthetic speech
// and provider peers only; no private companion, ASR/TTS, devices or owner data.
import test from 'node:test';
import assert from 'node:assert/strict';
import {once} from 'node:events';
import {mkdtemp, writeFile, rm, readFile} from 'node:fs/promises';
import {join, resolve} from 'node:path';
import {tmpdir} from 'node:os';
import {pathToFileURL} from 'node:url';
import {WebSocket} from 'ws';
import {setTimeout as delay} from 'node:timers/promises';
import {planFixture, until} from './fixtures/plans.mjs';
import {createSyntheticVoicePeer} from './fixtures/codex/synthetic-voice-peer.mjs';
const artifact = resolve(process.env.AUGMENTOR_PI_TEST_ROOT ?? '.');
const {privateDir, atomicJson} = await import(pathToFileURL(join(artifact, 'dist/runtime/src/storage.js')));
const {PiConnection} = await import(pathToFileURL(join(artifact, 'dist/client/src/socket.js')));
const {localConnect} = await import(pathToFileURL(join(artifact, 'dist/platform/src/transport.js')));
const {piTranscriptEvent} = await import(pathToFileURL(join(artifact, 'dist/memory/src/pi.js')));
async function fixture(t, {peerOptions, ...options} = {}) {
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
  const connect = async (sid = 'voice-root', surface = 'linux') => {
    const ticket = await f.call('voice.ticket', {sessionId: sid, surface});
    assert.deepEqual(Object.keys(ticket).sort(), ['protocol', 'sessionId', 'ticket', 'url']);
    const socket = new WebSocket(ticket.url), messages = [];
    socket.on('message', (data, binary) => {if (!binary) messages.push(JSON.parse(data));});
    await once(socket, 'open'); socket.send(JSON.stringify({type: 'auth', ticket: ticket.ticket, textSource: 'plugin'}));
    await until(() => messages.some(row => row.type === 'ready'), 'speech authentication'); return {socket, messages};
  };
  return {...f, peer, create, connect, ticketCalls: () => ticketCalls, beforeClose: close => cleanup.push(close)};
}
async function inactive(f) {await until(async () => (await f.call('host.describe')).activeVoiceBridges === 0, 'voice terminal');}
const input = (sid, requestId, op = {kind: 'worker-reply', reply: 'Owned public reply.'}) => ({sessionId: sid, requestId, content: [{type: 'text', text: JSON.stringify(op)}]});
const speechInput = (sid, op) => ({...input(sid, 'resonant-voice:' + crypto.randomUUID(), op), inputMode: 'voice'});
const systemText = body => JSON.stringify(body.messages.filter(message => message.role === 'system'));
const historyEvents = async (f, sid = 'voice-root') => (await f.call('session.history', {sessionId: sid})).events.map(row => row.event);

test('explicit spoken admission binds style and memory mode without changing original native input or typed defaults', {timeout: 25000}, async t => {
  const f = await fixture(t, {jobMode: {}}), sid = 'voice-root'; await f.create(); const spoken = speechInput(sid);
  await assert.rejects(f.call('session.prompt', spoken), /scoped voice bridge/);
  await assert.rejects(f.call('session.prompt', {...spoken, inputMode: 'other'}), /input mode/);
  await assert.rejects(f.call('session.prompt', {...spoken, requestId: 'typed-id'}), /stable speech request identity/);
  assert.equal(f.requests.length, 0);
  // A speech-looking identity alone must remain ordinary typed input.
  await f.call('session.prompt', {...speechInput(sid), inputMode: undefined}); await f.settled(sid);
  assert(!systemText(f.requests[0]).includes('Augmentor input mode v1'));
  await f.connect(); await f.call('session.prompt', spoken); await f.settled(sid);
  assert(systemText(f.requests[1]).includes('The user spoke this request.'), JSON.stringify({system: systemText(f.requests[1]), users: (await historyEvents(f)).filter(row => row.type === 'user/message'), observations: (await f.call('observation.list', {sessionId: sid})).records.filter(row => row.kind === 'context/provenance').map(row => row.data.inputMode)}));
  assert.deepEqual(f.requests[1].messages.findLast(row => row.role === 'user').content, spoken.content);
  await f.call('voice.close', {sessionId: sid});
  assert.equal((await f.call('session.prompt', spoken)).duplicate, true);
  await assert.rejects(f.call('session.prompt', {...spoken, inputMode: 'text'}), /different input/);
  await f.call('session.prompt', input(sid, 'typed-next')); await f.settled(sid);
  assert(systemText(f.requests[2]).includes('Earlier spoken-response brevity instructions no longer apply'));
  assert(!systemText(f.requests[2]).includes('The user spoke this request.'));
  const events = await historyEvents(f), users = events.filter(row => row.type === 'user/message'), answers = events.filter(row => row.type === 'assistant/message');
  assert.deepEqual(users.map(row => row.data.inputMode), ['text', 'voice', 'text']); assert.deepEqual(answers.map(row => row.data.inputMode), ['text', 'voice', 'text']);
  assert.deepEqual(events.flatMap(row => piTranscriptEvent(row)).map(row => row.mode), ['text', 'text', 'voice', 'voice', 'text', 'text']);
  const native = JSON.parse('[' + (await f.native(sid)).bytes.toString().trim().split('\n').join(',') + ']');
  assert(!native.some(row => JSON.stringify(row.message ?? null).includes('Augmentor input mode v1')));
  assert.deepEqual(native.filter(row => row.customType === 'augmentor.memory-context.v1').map(row => row.data.mode), ['text', 'voice', 'text']);
  const observations = (await f.call('observation.list', {sessionId: sid})).records.filter(row => row.kind === 'context/provenance');
  assert.equal(observations[0].data.inputMode, undefined); assert.equal(observations[1].data.inputMode.mode, 'voice'); assert.equal(observations[1].data.inputMode.providerSystemPresence, 'present');
  assert.equal(observations[1].data.memory.mode, 'voice'); assert.equal(observations[2].data.memory.mode, 'text');
  const before = f.requests.length; await f.stop(); await f.start(); await f.call('session.history', {sessionId: sid});
  assert.equal(f.requests.length, before); assert.deepEqual((await historyEvents(f)).flatMap(row => piTranscriptEvent(row)).map(row => row.mode), ['text', 'text', 'voice', 'voice', 'text', 'text']);
});

test('admitted waiting speech keeps its mode through disconnect and cold resume without reopening speech or replaying history', {timeout: 25000}, async t => {
  const f = await fixture(t, {jobMode: {}}), sid = 'voice-root'; await f.create(); await f.call('session.cancel', {sessionId: sid}); await f.connect(); const spoken = speechInput(sid);
  await f.call('session.prompt', {...spoken, mode: 'queue', resumeQueue: false});
  assert.equal(f.requests.length, 0); assert.equal((await f.call('session.queue', {sessionId: sid})).items[0].inputMode, 'voice');
  await f.call('voice.close', {sessionId: sid}); await f.stop(); await f.start(); await f.call('events.subscribe', {sessionId: sid});
  assert.equal(f.requests.length, 0); assert.equal((await f.call('session.queue', {sessionId: sid})).paused, true);
  assert.equal((await f.call('session.prompt', spoken)).duplicate, true);
  await f.call('session.continueQueue', {sessionId: sid}); await until(() => f.requests.length === 1, 'resumed voice request'); await f.settled(sid);
  assert(systemText(f.requests[0]).includes('The user spoke this request.'));
  assert.equal((await f.call('host.describe')).activeVoiceBridges, 0); assert.equal(f.ticketCalls(), 1); assert.deepEqual(f.peer.spoken, []);
  assert.deepEqual((await historyEvents(f)).filter(row => ['user/message', 'assistant/message'].includes(row.type)).map(row => row.data.inputMode), ['voice', 'voice']);
});

test('editing waiting speech produces typed delivery with a fresh identity and no false spoken memory', {timeout: 25000}, async t => {
  const f = await fixture(t, {jobMode: {}}), sid = 'voice-root'; await f.create(); await f.call('session.cancel', {sessionId: sid}); await f.connect(); const spoken = speechInput(sid);
  await f.call('session.prompt', {...spoken, mode: 'queue', resumeQueue: false}); await f.call('voice.close', {sessionId: sid});
  const snapshot = await f.call('session.queue', {sessionId: sid}), edited = input(sid, 'typed-edit');
  await f.call('session.updateQueue', {sessionId: sid, itemId: spoken.requestId, newItemId: edited.requestId, expectedRevision: snapshot.revision, action: {kind: 'edit', content: edited.content}});
  await f.call('session.continueQueue', {sessionId: sid}); await until(() => f.requests.length === 1, 'typed edited request'); await f.settled(sid);
  assert(!systemText(f.requests[0]).includes('The user spoke this request.'));
  const journal = JSON.parse(await readFile(join(f.state, 'sessions', sid + '.queue.json'), 'utf8'));
  assert.equal(journal.items[0].status, 'removed'); assert.equal(journal.items[0].inputMode, 'voice'); assert.equal(journal.items[1].inputMode, undefined);
  const events = await historyEvents(f); assert.equal(events.filter(row => row.type === 'user/message').length, 1);
  assert(events.flatMap(row => piTranscriptEvent(row)).every(row => row.mode === 'text'));
});

test('a typed correction supersedes spoken style in the same actual SDK turn', {timeout: 25000}, async t => {
  const f = await fixture(t, {jobMode: {}}), sid = 'voice-root'; await f.create(); await f.connect();
  const started = await f.call('session.prompt', speechInput(sid, {kind: 'worker-hold'}));
  await until(() => f.requests.length === 1, 'spoken provider active');
  await f.call('session.prompt', {...input(sid, 'typed-steer'), mode: 'steer', expectedTurnId: started.turnId}); await f.settled(sid);
  assert.equal(f.requests.length, 2); assert(systemText(f.requests[1]).includes('The user typed this request.')); assert(!systemText(f.requests[1]).includes('The user spoke this request.'));
  const events = await historyEvents(f), users = events.filter(row => row.type === 'user/message');
  assert.deepEqual(users.map(row => row.data.inputMode), ['voice', 'text']); assert(users.every(row => row.turnId === started.turnId));
  assert.equal(events.filter(row => row.type === 'turn/start').length, 1); assert.equal(events.findLast(row => row.type === 'assistant/message').data.inputMode, 'text');
  assert.equal(events.findLast(row => row.type === 'assistant/message').data.humanRequestId, 'typed-steer');
  // Recall is run once at the spoken turn's start; that provenance is distinct
  // from the later typed correction's response style and transcript mode.
  const observations = (await f.call('observation.list', {sessionId: sid})).records.filter(row => row.kind === 'context/provenance');
  assert.equal(observations[1].data.inputMode.mode, 'text'); assert.equal(observations[1].data.memory.mode, 'voice');
});

test('actual Pi Host speaks only live durably delivered human input through one SDK owner and never history or duplicate admission', {timeout: 25000}, async t => {
  const f = await fixture(t, {jobMode: {}}), sid = 'voice-root'; await f.create(sid);
  const description = await f.call('host.describe'); assert.equal(description.capabilities.voiceBridge, true); assert.notEqual(description.capabilities.voice, true);
  const socket = await f.connect(sid), p = input(sid, 'typed-human');
  const result = await f.call('session.prompt', p); await f.settled(sid);
  await until(() => socket.messages.some(row => row.type === 'turn-complete'), 'speech terminal receipt');
  assert.deepEqual(f.peer.spoken, ['Owned public reply.']); assert.equal(f.requests.length, 1);
  assert.equal((await f.call('session.prompt', p)).duplicate, true);
  const history = await f.call('session.history', {sessionId: sid}); await f.call('session.nativeHistory', {sessionId: sid});
  const users = history.events.map(row => row.event).filter(row => row.type === 'user/message');
  assert.equal(users.length, 1); assert.equal(users[0].data.source.rpcId, 'typed-human'); assert.equal(users[0].turnId, result.turnId);
  const queue = JSON.parse(await readFile(join(f.state, 'sessions', sid + '.queue.json'), 'utf8'));
  assert.equal(queue.items[0].delivered, true); assert.equal(queue.items[0].status, 'completed');
  assert.equal(f.peer.received.filter(row => row.type === 'user-turn').length, 1);
  assert(f.peer.received.every(row => row.harness === 'pi' && row.sessionId === sid));
  assert.equal((await f.call('session.list')).items.length, 1);
  await f.call('voice.close', {sessionId: sid}); await inactive(f);
  await f.stop(); await f.start(); await f.call('events.subscribe', {sessionId: sid});
  await f.call('session.history', {sessionId: sid}); assert.equal(f.requests.length, 1);
  assert.equal((await f.call('host.describe')).activeVoiceBridges, 0); assert.deepEqual(f.peer.spoken, ['Owned public reply.']);
});

test('voice admission refuses disconnected, wrong-surface, archived and already-connected roots before issuing another ticket', {timeout: 25000}, async t => {
  const f = await fixture(t); await f.create(); await f.call('events.subscribe', {sessionId: null});
  await assert.rejects(f.call('voice.ticket', {sessionId: 'voice-root', surface: 'linux'}), /Connect the conversation/);
  await f.call('events.subscribe', {sessionId: 'voice-root'});
  await assert.rejects(f.call('voice.ticket', {sessionId: 'voice-root', surface: 'browser'}), /surface/);
  assert.equal(f.ticketCalls(), 0); await f.connect();
  await assert.rejects(f.call('voice.ticket', {sessionId: 'voice-root', surface: 'linux'}), /existing voice/);
  await assert.rejects(f.call('host.prepareShutdown'), /Close voice/);
  const workspaces = await f.call('workspace.list');
  await assert.rejects(f.call('session.organize', {sessionId: 'voice-root', action: 'archive', expectedRevision: workspaces.organizationRevision}), /Close voice/);
  await assert.rejects(f.call('models.reload'), /Close voice/);
  await f.call('voice.close', {sessionId: 'voice-root'}); await inactive(f);
  const current = await f.call('workspace.list');
  await f.call('session.organize', {sessionId: 'voice-root', action: 'archive', expectedRevision: current.organizationRevision});
  await assert.rejects(f.call('voice.ticket', {sessionId: 'voice-root', surface: 'linux'}), /available human/);
  assert.equal(f.ticketCalls(), 1);
});

test('actual Pi Stop cancels speech immediately while preserving the same connection for a later human turn', {timeout: 25000}, async t => {
  const f = await fixture(t, {jobMode: {}}); await f.create(); await f.connect();
  await f.call('session.prompt', input('voice-root', 'old', {kind: 'worker-hold'}));
  await until(() => f.peer.received.some(row => row.type === 'text'), 'live public text');
  await f.call('session.cancel', {sessionId: 'voice-root'}); await f.settled('voice-root');
  assert(f.peer.received.some(row => row.type === 'cancel')); assert.deepEqual(f.peer.spoken, []);
  assert.equal((await f.call('host.describe')).activeVoiceBridges, 1);
  await f.call('session.prompt', {...input('voice-root', 'fresh'), resumeQueue: true}); await f.settled('voice-root');
  await until(() => f.peer.spoken.length === 1, 'new reply'); assert.deepEqual(f.peer.spoken, ['Owned public reply.']);
});

test('the last IPC subscriber closes speech while another operator preserves it and the Pi turn remains independent', {timeout: 25000}, async t => {
  const f = await fixture(t, {jobMode: {}}); await f.create(); await f.connect();
  const wire = localConnect(join(f.state, 'runtime.sock')); await once(wire, 'connect');
  const observer = new PiConnection(wire, () => {}); f.beforeClose(() => observer.close());
  await observer.call('host.hello', {protocol: 'augmentor-pi/1'}); await observer.call('events.subscribe', {sessionId: 'voice-root'});
  await f.call('session.prompt', input('voice-root', 'held', {kind: 'worker-hold'}));
  await until(() => f.peer.received.some(row => row.type === 'text'), 'live output before disconnect');
  await f.call('events.subscribe', {sessionId: null}); assert.equal((await f.call('host.describe')).activeVoiceBridges, 1);
  observer.close(); await inactive(f);
  assert.equal(f.peer.connections[0].closed, true); assert.equal((await f.call('session.list')).items[0].running, true);
  await f.call('session.cancel', {sessionId: 'voice-root'}); await f.settled('voice-root'); assert.deepEqual(f.peer.spoken, []);
});

for (const phase of ['/health', '/internal/ticket']) test('closing Host voice during ' + phase + ' joins setup without exposing a cancelled ticket', {timeout: 25000}, async t => {
  const entered = Promise.withResolvers(), gate = Promise.withResolvers();
  const f = await fixture(t, {peerOptions: {beforeRequest: async ({path}) => {if (path === phase) {entered.resolve(); await gate.promise;}}}});
  f.beforeClose(() => gate.resolve()); await f.create();
  const pending = f.call('voice.ticket', {sessionId: 'voice-root', surface: 'linux'}); const refused = assert.rejects(pending, /closing/);
  await entered.promise; let closed = false; const closing = f.call('voice.close', {sessionId: 'voice-root'}).then(value => {closed = true; return value;});
  await delay(30); assert.equal(closed, false); gate.resolve(); await refused; assert.deepEqual(await closing, {closed: true});
  await inactive(f); assert.equal(f.peer.connections.length, 0);
  if (phase === '/internal/ticket') assert.equal(f.peer.received.at(-1).type, 'disconnect');
  else {assert.equal(f.ticketCalls(), 0); assert.deepEqual(f.peer.received, []);}
});

test('Host close remains busy until an older delayed speech request is joined', {timeout: 25000}, async t => {
  const entered = Promise.withResolvers(), gate = Promise.withResolvers();
  const f = await fixture(t, {jobMode: {}, peerOptions: {beforeRequest: async ({body}) => {if (body?.type === 'text') {entered.resolve(); await gate.promise;}}}});
  f.beforeClose(() => gate.resolve()); await f.create(); await f.connect();
  await f.call('session.prompt', input('voice-root', 'delayed')); await entered.promise;
  let closed = false; const closing = f.call('voice.close', {sessionId: 'voice-root'}).then(() => {closed = true;});
  await until(() => f.peer.connections[0].closed, 'scoped socket closed');
  assert.equal((await f.call('host.describe')).activeVoiceBridges, 1); assert.equal(closed, false);
  await assert.rejects(f.call('host.prepareShutdown'), /Close voice/);
  gate.resolve(); await closing; await inactive(f); await f.settled('voice-root'); assert.deepEqual(f.peer.spoken, []);
});

test('Host rejects companion incompatibility without a ticket and forbids speech RPC through the Harness HTTP gateway', {timeout: 25000}, async t => {
  const f = await fixture(t, {peerOptions: {harnesses: ['codex']}}); await f.create();
  await assert.rejects(f.call('voice.ticket', {sessionId: 'voice-root', surface: 'linux'}), /explicitly advertises/); await inactive(f);
  const link = await f.link(), token = new URL(link.url).hash.slice('#token='.length);
  const response = await fetch(link.origin + '/api/rpc', {method: 'POST', headers: {'content-type': 'application/json', origin: link.origin, authorization: 'Bearer ' + token}, body: JSON.stringify({id: 'unavailable-http-voice', method: 'voice.ticket', params: {sessionId: 'voice-root', surface: 'linux'}})});
  const result = await response.json(); assert(response.status !== 200 || result.error); assert.equal(f.ticketCalls(), 0);
});

test('goal and delegated work stay outside the root human speech lease', {timeout: 30000}, async t => {
  const goals = await fixture(t, {goalMode: {completeAfter: 1}}); await goals.create(); await goals.connect();
  await goals.prompt('voice-root', {kind: 'read'}); await until(() => goals.peer.spoken.length === 1, 'human goal inspection reply');
  await goals.call('session.updateGoal', {sessionId: 'voice-root', change: {operation: 'create', expectedRef: null, objective: 'Synthetic bounded goal', maxGoalRounds: 1, continueAutomatically: true}});
  await until(async () => (await goals.call('session.goal', {sessionId: 'voice-root'})).goal?.phase === 'complete', 'automatic goal completed'); await goals.settled('voice-root');
  assert.equal(goals.peer.spoken.length, 1); assert.equal(goals.peer.received.filter(row => row.type === 'user-turn').length, 1);
  const jobs = await fixture(t, {jobMode: {}}); await jobs.create(); await jobs.connect();
  await jobs.call('session.prompt', input('voice-root', 'root')); await jobs.settled('voice-root'); await until(() => jobs.peer.spoken.length === 1, 'root reply');
  const started = await jobs.call('session.startJob', {sessionId: 'voice-root', spec: {requestId: crypto.randomUUID(), kind: 'delegate', task: JSON.stringify({kind: 'worker-reply', reply: 'CHILD_MUST_NOT_SPEAK'}), allowedTools: []}});
  let job; await until(async () => {job = (await jobs.call('session.job', {sessionId: 'voice-root', jobId: started.job.id})).job; return job.state === 'completed';}, 'child complete');
  await assert.rejects(jobs.call('voice.ticket', {sessionId: job.childId, surface: 'linux'}), /available human/);
  assert.equal(jobs.peer.spoken.length, 1); assert(!JSON.stringify(jobs.peer.received).includes('CHILD_MUST_NOT_SPEAK'));
});

test('actual Host shutdown disconnects its active lease and a cold owner never reopens it automatically', {timeout: 25000}, async t => {
  const f = await fixture(t); await f.create(); await f.connect(); await f.stop();
  await until(() => f.peer.connections[0].closed, 'speech shutdown'); assert.equal(f.peer.received.at(-1).type, 'disconnect');
  await f.start(); assert.equal((await f.call('host.describe')).activeVoiceBridges, 0); assert.equal(f.requests.length, 0);
  assert.equal(f.ticketCalls(), 1); assert.deepEqual(f.peer.spoken, []);
});

test('working and recovered unknown-outcome owners cannot open speech or replay their prompt', {timeout: 25000}, async t => {
  const f = await fixture(t, {jobMode: {}}); await f.create();
  await f.call('session.prompt', input('voice-root', 'uncertain', {kind: 'worker-hold'}));
  await until(() => f.requests.length === 1, 'provider active');
  await assert.rejects(f.call('voice.ticket', {sessionId: 'voice-root', surface: 'linux'}), /idle, confirmed/);
  await f.crash(); await f.start(); await f.call('events.subscribe', {sessionId: 'voice-root'});
  const before = await f.native('voice-root');
  await assert.rejects(f.call('voice.ticket', {sessionId: 'voice-root', surface: 'linux'}), /idle, confirmed/);
  const after = await f.native('voice-root'); assert.deepEqual(after.bytes, before.bytes);
  assert.equal(f.requests.length, 1); assert.equal(f.ticketCalls(), 0); assert.equal((await f.call('host.describe')).activeVoiceBridges, 0);
});

test('an extension-injected follow-up cannot inherit a human speech request identity', {timeout: 25000}, async t => {
  const f = await fixture(t, {jobMode: {}}), extension = join(f.config, 'agent', 'authored-follow-up.mjs');
  await writeFile(extension, `// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
export default pi => {let sent = false; pi.on('turn_end', () => {if (!sent) {sent = true; pi.sendUserMessage(JSON.stringify({kind:'worker-reply',reply:'AUTOMATIC_REPLY_MUST_NOT_SPEAK'}), {deliverAs:'followUp'});}});};\n`);
  atomicJson(join(f.config, 'resources.json'), {sources: [extension], skills: []});
  await f.create(); await f.connect(); const human = speechInput('voice-root'); await f.call('session.prompt', human); await f.settled('voice-root');
  await until(() => f.peer.received.some(row => row.type === 'cancel'), 'unadmitted follow-up speech suppression');
  assert.equal(f.requests.length, 2); assert(!f.peer.spoken.some(text => text.includes('AUTOMATIC_REPLY_MUST_NOT_SPEAK')));
  assert(!JSON.stringify(f.peer.received).includes('AUTOMATIC_REPLY_MUST_NOT_SPEAK'));
  assert.equal(f.peer.received.filter(row => row.type === 'user-turn').length, 1);
  const history = await f.call('session.history', {sessionId: 'voice-root'}), users = history.events.map(row => row.event).filter(row => row.type === 'user/message');
  assert.equal(users.length, 2); assert.equal(users[0].data.source.rpcId, human.requestId); assert.equal(users[1].data.source.rpcId, undefined);
  assert.equal(users[1].data.source.kind, 'unattributed'); assert.equal(users[1].data.inputMode, 'unattributed'); assert.deepEqual(piTranscriptEvent(users[1]), []);
  assert(systemText(f.requests[0]).includes('The user spoke this request.')); assert(!systemText(f.requests[1]).includes('Augmentor input mode v1'));
  const automatic = history.events.map(row => row.event).findLast(row => row.type === 'assistant/message'); assert.equal(automatic.data.inputMode, 'unattributed'); assert.deepEqual(piTranscriptEvent(automatic), []);
});
