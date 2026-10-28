// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Independently authored protocol, queue, memory and public extension contracts.
import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {mkdtempSync, readFileSync, writeFileSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join, resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {SessionManager} from '@earendil-works/pi-coding-agent';
const artifact = resolve(process.env.AUGMENTOR_PI_TEST_ROOT ?? '.');
const load = path => import(pathToFileURL(join(artifact, 'dist', path)));
const {piInputMode, promptInputMode, spokenRequestId} = await load('runtime/src/input-mode.js');
const {inputModeInstructions} = await load('prompt-library/src/input-mode.js');
const {inputContext} = await load('codex-runtime/src/input-context.js');
const {PiPromptQueue} = await load('runtime/src/queue.js');
const {managedPiMemory, piTranscriptEvent} = await load('memory/src/pi.js');
const {piMemorySnapshot, readPiMemorySnapshot, PI_MEMORY_SNAPSHOT_TYPE} = await load('memory/src/pi-snapshot.js');
const {ContextProvenance} = await load('runtime/src/context-provenance.js');
const speechId = 'resonant-voice:00112233-4455-6677-8899-aabbccddeeff';
function queue(t) {
  const root = mkdtempSync(join(tmpdir(), 'augmentor-input-mode-'));
  t.after(() => rmSync(root, {recursive: true, force: true}));
  const file = join(root, 'queue.json'); return {file, value: new PiPromptQueue(file, 'fixture')};
}
test('Pi input mode is explicit while the existing Codex instructions retain their contract', () => {
  assert.equal(promptInputMode(undefined), 'text'); assert.equal(promptInputMode('voice'), 'voice');
  for (const value of [null, true, 'spoken', {}, 1]) assert.throws(() => promptInputMode(value), /input mode/);
  assert(spokenRequestId(speechId));
  for (const id of ['resonant-voice:a', speechId.toUpperCase(), speechId + ':more']) assert(!spokenRequestId(id));
  assert.equal(inputContext(speechId).augmentor_input_mode.value, inputModeInstructions(speechId, 'voice'));
  assert.equal(inputContext('typed').augmentor_input_mode.value, inputModeInstructions('typed', 'text'));
});
test('request-only style copies preserve every native message and existing section, and typed input resets voice style', () => {
  let input, handler; const rows = [];
  handler = piInputMode(() => input, row => rows.push(row));
  const original = [{role: 'system', content: 'BASE', sections: {'augmentor:input-mode': 'FOREIGN'}, timestamp: 1}, {role: 'user', content: 'UNMODIFIED_INPUT', timestamp: 2}];
  const before = structuredClone(original);
  assert.equal(handler({messages: original}).messages, original);
  input = {requestId: 'typed', mode: 'text', voiceSeen: false}; assert.equal(handler({messages: original}).messages, original);
  input = {requestId: speechId, mode: 'voice', voiceSeen: true};
  const voice = handler({messages: original}); assert.notEqual(voice.messages, original); assert.equal(voice.messages[1], original[1]);
  assert.equal(voice.messages[0].sections['augmentor:input-mode'], 'FOREIGN');
  assert.equal(voice.messages[0].sections['augmentor:input-mode:1'], inputModeInstructions(speechId, 'voice'));
  assert.deepEqual(original, before); assert.equal(rows.at(-1).mode, 'voice');
  input = {requestId: 'next-typed', mode: 'text', voiceSeen: true};
  assert(handler({messages: original}).messages[0].sections['augmentor:input-mode:1'].includes('Earlier spoken-response brevity instructions no longer apply'));
  const noSystem = {messages: original.slice(1)}; assert.equal(handler(noSystem), noSystem); assert.equal(rows.at(-1).state, 'unavailable-no-leading-system-message');
  handler = piInputMode(() => input, () => {throw Error('diagnostics unavailable');});
  assert(handler({messages: original}).messages); assert.deepEqual(original, before);
});
test('durable voice receipts survive cold recovery, bind mode to identity and retain legacy text fingerprints', t => {
  const f = queue(t), q = f.value; q.enqueue('legacy', 'Typed original', true);
  const legacy = JSON.parse(readFileSync(f.file)).items[0];
  assert(!Object.hasOwn(legacy, 'inputMode')); assert.equal(legacy.fingerprint, createHash('sha256').update('Typed original').digest('hex'));
  q.enqueue(speechId, 'Spoken original', true, undefined, [], 'voice');
  let cold = new PiPromptQueue(f.file, 'fixture'); cold.recover();
  assert(cold.paused); assert.equal(cold.read(speechId).inputMode, 'voice'); assert.equal(cold.snapshot().items[1].inputMode, 'voice');
  assert.equal(cold.enqueue(speechId, 'Spoken original', true, undefined, [], 'voice'), false);
  assert.throws(() => cold.lookup(speechId, 'Spoken original'), /different input/);
  assert.throws(() => cold.lookup('legacy', 'Typed original', [], 'voice'), /different input/);
  cold.remove('legacy'); cold.resume(); cold.dispatch(speechId, 'turn'); cold.accepted(speechId); cold.delivered(speechId);
  cold = new PiPromptQueue(f.file, 'fixture'); cold.recover(); assert(cold.uncertain); assert.throws(() => cold.resume(), /unknown outcome/);
  assert.equal(cold.read(speechId).inputMode, 'voice'); cold.resolve(speechId);
  assert.equal(cold.lookup(speechId, 'Spoken original', [], 'voice').status, 'cancelled');
});
test('editing waiting speech creates a fresh typed receipt and preserves the original admission', t => {
  const {value: q} = queue(t); q.enqueue(speechId, 'Garbled speech', true, undefined, [], 'voice');
  q.replaceWaiting(speechId, 'typed-edit', 'Corrected by typing', q.snapshot().revision);
  assert.equal(q.read(speechId).inputMode, 'voice'); assert.equal(q.read(speechId).status, 'removed');
  assert.equal(q.read('typed-edit').inputMode, undefined); assert.equal(q.next.id, 'typed-edit');
  assert.equal(q.replaceWaiting(speechId, 'typed-edit', 'Corrected by typing', q.snapshot().revision), false);
});
test('damaged or relabelled mode records refuse recovery instead of weakening the journal contract', t => {
  const f = queue(t); f.value.enqueue(speechId, 'Spoken', true, undefined, [], 'voice'); const original = JSON.parse(readFileSync(f.file));
  for (const mode of ['unknown', 'text', null]) {
    const changed = structuredClone(original); changed.items[0].inputMode = mode; writeFileSync(f.file, JSON.stringify(changed), {mode: 0o600});
    assert.throws(() => new PiPromptQueue(f.file, 'fixture'), /Corrupt prompt queue/);
  }
  assert.throws(() => f.value.enqueue('bad', 'No relabel', true, undefined, [], 'unknown'), /input mode/);
  assert.throws(() => f.value.enqueue('goal', 'No spoken goal', true, {}, [], 'voice'), /input mode/);
});
test('memory capture retains original spoken text, legacy text and truthful source exclusions', () => {
  const user = {seq: 1, type: 'user/message', data: {inputMode: 'voice', source: {kind: 'user'}, content: [{type: 'text', text: 'EXPANDED_SKILL'}], submittedContent: [{type: 'text', text: 'Actual spoken input'}]}};
  assert.deepEqual(piTranscriptEvent(user)[0], {id: '1', role: 'user', mode: 'voice', content: 'Actual spoken input', live: false, status: 'complete'});
  const assistant = {seq: 2, type: 'assistant/message', data: {inputMode: 'voice', message: {content: [{type: 'thinking', thinking: 'NO_REASONING'}, {type: 'text', text: 'Answer'}], stopReason: 'aborted'}}};
  assert.equal(piTranscriptEvent(assistant, true)[0].mode, 'voice'); assert.equal(piTranscriptEvent(assistant)[0].status, 'interrupted');
  delete assistant.data.inputMode; assert.equal(piTranscriptEvent(assistant)[0].mode, 'text');
  assistant.data.inputMode = 'unattributed'; assert.deepEqual(piTranscriptEvent(assistant), []);
  for (const kind of ['goal', 'delegation', 'unattributed']) assert.deepEqual(piTranscriptEvent({...user, data: {...user.data, source: {kind}}}), []);
});
test('memory recall and native branch restoration preserve the actual recall register independently of current input style', async () => {
  const calls = [], rows = [], manager = SessionManager.inMemory(); let mode = 'voice';
  const memory = {session: 'pi:fixture', recall: async (mode, query) => {calls.push({mode, query}); return 'VOICE_MEMORY';}, close() {}, activity: async () => {}};
  const handlers = new Map(), managed = managedPiMemory(memory, true, row => rows.push(structuredClone(row)), () => mode);
  const api = {on: (name, fn) => handlers.set(name, fn), appendEntry: (type, value) => manager.appendCustomEntry(type, value)};
  managed.extension(api); assert.equal((await handlers.get('before_agent_start')({prompt: 'Spoken', systemPrompt: 'BASE'})).systemPrompt, 'BASE\n\nVOICE_MEMORY');
  assert.deepEqual(calls, [{mode: 'voice', query: 'Spoken'}]); managed.finalPayload({messages: [{role: 'system', content: 'VOICE_MEMORY'}]}, 'openai-completions');
  assert.equal(readPiMemorySnapshot(manager.getBranch()).value.mode, 'voice');
  mode = 'text'; const branch = managedPiMemory(memory, false, row => rows.push(structuredClone(row)), () => mode); branch.extension(api);
  await handlers.get('before_agent_start')({prompt: 'Typed branch follow-up', systemPrompt: 'BASE'}, {sessionManager: manager});
  assert.equal(calls.length, 1); assert.equal(rows.at(-1).mode, 'voice'); assert.equal(rows.at(-1).status, 'restored-for-branch');
  branch.finalPayload({messages: [{role: 'system', content: 'VOICE_MEMORY'}]}, 'openai-completions'); assert.equal(readPiMemorySnapshot(manager.getBranch()).value.mode, 'voice');
  manager.appendCustomEntry(PI_MEMORY_SNAPSHOT_TYPE, {...piMemorySnapshot('pi:fixture', 'bad', 'present', 'voice'), mode: 'unknown'});
  assert.deepEqual(readPiMemorySnapshot(manager.getBranch()), {state: 'invalid'});
  assert.throws(() => piMemorySnapshot('pi:fixture', 'bad', 'present', 'unknown'), /snapshot contract/);
});
test('input-mode provenance reports literal provider-system presence and obeys payload capture', () => {
  let capture = true; const p = new ContextProvenance(() => capture), row = {boundary: 'managed-Pi-stream-request-copy-after-system-projection', source: 'delivered-human-input', requestId: speechId, mode: 'voice', state: 'applied', section: 'augmentor:input-mode', text: inputModeInstructions(speechId, 'voice')};
  p.beginRequest([]); p.inputMode(row);
  assert.equal(p.finish({messages: [{role: 'user', content: row.text}]}, 'openai-completions').data.inputMode.providerSystemPresence, 'not-present');
  p.beginRequest([]); p.inputMode(row);
  assert.equal(p.finish({messages: [{role: 'system', content: row.text}]}, 'openai-completions').data.inputMode.providerSystemPresence, 'present');
  p.beginRequest([]); p.inputMode(row); capture = false;
  const disabled = p.finish({messages: []}, 'openai-completions'); assert.equal(disabled.data.inputMode.providerSystemPresence, 'unavailable'); assert(!JSON.stringify(disabled).includes(row.text));
  p.endRequest(); assert.equal(p.finish({}, 'openai-completions').data.inputMode, undefined);
});
