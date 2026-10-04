// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {mkdtemp, mkdir, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {randomBytes} from 'node:crypto';
import {CodexRpc} from './rpc.js';
import {runtimeOptions, CODEX_VERSION, type CodexConnection} from './config.js';

/** A real Codex turn in empty temporary state, with one pure synthetic tool. */
export async function checkAgent(connection: CodexConnection, signal: AbortSignal): Promise<{valid: true; validation: 'codex-tools'; runtime: string; toolsVerified: true}> {
  if (!['api', 'local'].includes(connection.kind)) throw new Error('This check supports API and local profiles.');
  signal.throwIfAborted();
  const root = await mkdtemp(join(tmpdir(), 'augmentor-codex-check-'));
  let rpc: CodexRpc | undefined;
  let removeAbort = () => {};
  try {
    const home = join(root, 'home'), state = join(root, 'state');
    await mkdir(home, {mode: 0o700}); await mkdir(state, {mode: 0o700});
    const options = runtimeOptions(connection, state, root);
    // No owner home, project instructions, auth cache, plugin state or desktop
    // executor enters this check. Empty environments disable shell/file tools.
    options.env = {...options.env, HOME: home, XDG_CONFIG_HOME: join(home, 'config'), XDG_DATA_HOME: join(home, 'data'), XDG_STATE_HOME: join(home, 'state')};
    for (const name of ['DISPLAY', 'WAYLAND_DISPLAY', 'DBUS_SESSION_BUS_ADDRESS']) delete options.env[name];
    options.args.push('-c', 'features.multi_agent=false', '-c', 'project_doc_max_bytes=0');
    rpc = new CodexRpc({...options, experimentalApi: true, maxFrameBytes: 1024 * 1024});
    const nonce = randomBytes(16).toString('hex'), receipt = randomBytes(24).toString('hex');
    let threadId: string | undefined, invoked = false, answer = '', events = 0;
    let resolve!: () => void, reject!: (error: Error) => void;
    const finished = {promise: new Promise<void>((yes, no) => {resolve = yes; reject = no;}), resolve: () => resolve(), reject: (error: Error) => reject(error)};
    // Attach a rejection handler before any startup await can fail.
    void finished.promise.catch(() => {});
    const fail = (message: string) => {finished.reject(new Error(message)); void rpc!.close();};
    const abort = () => fail('Codex connection check was cancelled or timed out. It was not retried.');
    signal.addEventListener('abort', abort, {once: true}); removeAbort = () => signal.removeEventListener('abort', abort);
    if (signal.aborted) {abort(); throw new Error('Codex connection check was cancelled.');}
    rpc.on('failure', () => finished.reject(new Error('Codex connection check lost its runtime. It was not retried.')));
    rpc.on('request', request => {
      const p = request.params, args = p.arguments as Record<string, unknown> | undefined;
      if (request.method !== 'item/tool/call' || p.threadId !== threadId || p.tool !== 'augmentor_connection_probe' || invoked ||
          !args || typeof args !== 'object' || Array.isArray(args) || Object.keys(args).length !== 1 || args.nonce !== nonce) {
        rpc!.reject(request.id, 'Only the one synthetic connection probe is permitted.'); fail('The model did not use the permitted connection-check tool.'); return;
      }
      invoked = true;
      rpc!.respond(request.id, {success: true, contentItems: [{type: 'inputText', text: receipt}]});
    });
    rpc.on('notification', frame => {
      if (++events > 4096) {fail('Codex connection check exceeded its event limit.'); return;}
      const p = frame.params as Record<string, any>;
      if (p.threadId !== threadId) return;
      if (frame.method === 'item/completed' && p.item?.type === 'agentMessage') {
        if (typeof p.item.text !== 'string' || p.item.text.length > 4096) {fail('Codex connection check exceeded its answer limit.'); return;}
        answer = p.item.text.trim();
      }
      if (frame.method === 'turn/completed') {
        if (p.turn?.status === 'completed' && invoked && answer === receipt) finished.resolve();
        else fail('The model did not complete the Codex tool check. It must call the probe and return its receipt.');
      }
    });
    await rpc.initialize(); signal.throwIfAborted();
    const started = await rpc.call('thread/start', {cwd: root, ephemeral: true, environments: [], approvalPolicy: 'never', sandbox: 'read-only',
      baseInstructions: 'You are checking model compatibility. Use only the provided synthetic probe. Read no files and perform no other work.',
      dynamicTools: [{name: 'augmentor_connection_probe', description: 'Pure connection check. Return its receipt to finish the check.',
        inputSchema: {type: 'object', additionalProperties: false, required: ['nonce'], properties: {nonce: {type: 'string'}}}}]});
    if (typeof started.thread?.id !== 'string') throw new Error('Codex did not create its connection-check thread.');
    threadId = started.thread.id; signal.throwIfAborted();
    await rpc.call('turn/start', {threadId, environments: [], input: [{type: 'text', text: 'Call augmentor_connection_probe with nonce ' + nonce + '. Then reply with only the exact receipt returned by that tool.'}]});
    await finished.promise;
    return {valid: true, validation: 'codex-tools', runtime: CODEX_VERSION, toolsVerified: true};
  } catch {
    if (signal.aborted) throw new Error('Codex connection check was cancelled or timed out. It was not retried.');
    throw new Error('Codex could not verify this model’s tool support. Check its Responses compatibility or try another model. No user task was sent or retried.');
  } finally {
    removeAbort(); await rpc?.close(); await rm(root, {recursive: true, force: true});
  }
}
