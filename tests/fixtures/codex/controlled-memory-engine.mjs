// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {createServer} from 'node:net';
import {mkdirSync, readFileSync} from 'node:fs';
import {join} from 'node:path';
import {randomUUID} from 'node:crypto';

const run = promisify(execFile);
async function port() {
  const server = createServer(); await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const value = server.address().port; await new Promise(resolve => server.close(resolve)); return value;
}
/** Opt-in real pinned engine. Owns only a fresh named container/volume and empty configuration. */
export async function controlledMemoryEngine(root, modelUrl) {
  const id = randomUUID().replaceAll('-', ''), name = 'augmentor-codex-proof-' + id, volume = name + '-data';
  const setup = join(root, 'setup'); mkdirSync(setup, {mode:0o700});
  const env = {PATH:process.env.PATH, LANG:process.env.LANG ?? 'C.UTF-8', HOME:root,
    AUGMENTOR_SHARED_DATA:setup, XDG_CONFIG_HOME:join(root, 'config'), XDG_STATE_HOME:join(root, 'state'), XDG_DATA_HOME:join(root, 'data')};
  const options = {env, timeout:180000, maxBuffer:2*1024*1024};
  const close = async () => {
    const containers = await run('docker', ['ps', '-a', '--format', '{{.Names}}'], options);
    if (containers.stdout.split('\n').includes(name)) await run('docker', ['rm', '-f', name], options);
    const volumes = await run('docker', ['volume', 'ls', '--format', '{{.Name}}'], options);
    if (volumes.stdout.split('\n').includes(volume)) await run('docker', ['volume', 'rm', volume], options);
  };
  try {
    const apiPort = await port(); let gatewayPort = await port(); while (gatewayPort === apiPort) gatewayPort = await port();
    await run(process.env.AUGMENTOR_PYTHON ?? 'python3', ['scripts/setup-hindsight.py', '--name', name, '--volume', volume,
      '--port', String(apiPort), '--gateway-port', String(gatewayPort), '--model-url', modelUrl, '--model', 'fixture'], options);
    await run('docker', ['update', '--restart=no', name], options);
    return {configuration:JSON.parse(readFileSync(join(setup, 'hindsight.json'), 'utf8')), close};
  } catch (error) {await close(); throw error;}
}
