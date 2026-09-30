// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {spawn} from 'node:child_process';
import {createConnection} from 'node:net';
import {mkdirSync, existsSync, writeFileSync} from 'node:fs';
import {join} from 'node:path';
import {randomUUID} from 'node:crypto';

/** Real companions in empty state. Never inherit owner config, credentials or model routes. */
export async function memoryServices(root, configuration) {
  const state = join(root, 's'), data = join(root, 'd');
  mkdirSync(state, {mode: 0o700}); mkdirSync(data, {mode: 0o700});
  if (configuration) writeFileSync(join(data, 'hindsight.json'), JSON.stringify(configuration), {mode:0o600});
  const env = {PATH: process.env.PATH, LANG: process.env.LANG ?? 'C.UTF-8', HOME: root,
    AUGMENTOR_SHARED_STATE: state, AUGMENTOR_SHARED_DATA: data, AUGMENTOR_WORKSPACE_PROFILE: '',
    XDG_RUNTIME_DIR: join(root, 'run'), XDG_CONFIG_HOME: join(root, 'config'), XDG_STATE_HOME: state, XDG_DATA_HOME: data};
  const processes = [], sockets = new Set(), calls = [];
  const stop = async entry => {
    if (entry.child.exitCode !== null || entry.child.signalCode !== null) return;
    entry.child.kill('SIGTERM');
    let timer;
    try {await Promise.race([entry.done, new Promise(resolve => {timer = setTimeout(() => {if (entry.child.exitCode === null && entry.child.signalCode === null) entry.child.kill('SIGKILL'); resolve();}, 2000);})]); await entry.done;}
    finally {clearTimeout(timer);}
  };
  const close = async () => {for (const socket of sockets) socket.destroy(); await Promise.all(processes.map(stop));};
  const start = async (script, endpoint) => {
    const child = spawn(process.env.AUGMENTOR_PYTHON ?? 'python3', [script], {env, stdio: 'ignore'});
    let failed = false;
    const done = new Promise(resolve => {child.once('exit', resolve); child.once('error', () => {failed = true; resolve();});});
    const entry = {child, done}; processes.push(entry);
    for (let n = 0; n < 400; n++) {
      if (failed || child.exitCode !== null || child.signalCode !== null) throw Error('Isolated memory fixture service stopped before readiness.');
      if (existsSync(join(state, endpoint))) return entry;
      await new Promise(resolve => setTimeout(resolve, 20));
    }
    throw Error('Isolated memory fixture service did not become ready.');
  };
  let memoryProcess;
  try {
    memoryProcess = await start('services/memory/service.py', 'dual-memory.sock');
    await start('services/prompt-library/service.py', 'prompts.sock');
  } catch (error) {await close(); throw error;}
  const call = (method, params = {}, id = randomUUID(), signal) => new Promise((resolve, reject) => {
    if (signal?.aborted) {reject(signal.reason); return;}
    calls.push({method, params});
    const socket = createConnection(join(state, method.startsWith('memory.dual.') ? 'dual-memory.sock' : 'prompts.sock'));
    sockets.add(socket); let raw = Buffer.alloc(0);
    const abort = () => socket.destroy(signal.reason instanceof Error ? signal.reason : Error('Fixture request cancelled'));
    signal?.addEventListener('abort', abort, {once: true});
    socket.once('close', () => {sockets.delete(socket); signal?.removeEventListener('abort', abort);});
    socket.setTimeout(5000, () => socket.destroy(Error('Isolated memory RPC timeout')));
    socket.once('error', reject);
    socket.once('connect', () => socket.write(JSON.stringify({protocol: 'augmentor-prompts/1', id, method, params}) + '\n'));
    socket.on('data', chunk => {
      raw = Buffer.concat([raw, chunk]);
      if (raw.length > 1024 * 1024) {socket.destroy(Error('Isolated memory reply exceeds fixture bound')); return;}
      const end = raw.indexOf(10); if (end < 0) return;
      try {
        const frame = JSON.parse(raw.subarray(0, end).toString());
        if (frame.id !== id) throw Error('Isolated memory reply identity mismatch');
        if (frame.error) throw Error(frame.error.message);
        resolve(frame.result);
      } catch (error) {reject(error);} finally {socket.end();}
    });
    socket.once('end', () => reject(Error('Isolated memory service disconnected')));
  });
  return {call, calls, close, state, data, stopMemory: () => stop(memoryProcess),
    restartMemory: async () => {memoryProcess = await start('services/memory/service.py', 'dual-memory.sock');}};
}
