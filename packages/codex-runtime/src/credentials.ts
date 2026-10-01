// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {pythonExecutable} from '../../platform/src/index.js';

export interface CredentialStore {
  get(reference: string): Promise<string | undefined>;
  put(reference: string, value: string): Promise<void>;
  delete(reference: string): Promise<void>;
}
export class OsCredentialStore implements CredentialStore {
  private call(operation: string, reference: string, value?: string): Promise<any> {
    if (!/^codex-[a-zA-Z0-9_-]{1,100}$/.test(reference)) return Promise.reject(new Error('Invalid Codex credential reference.'));
    return new Promise((resolve, reject) => {
      const env: NodeJS.ProcessEnv = {PYTHONDONTWRITEBYTECODE: '1'};
      for (const key of ['PATH', 'HOME', 'USER', 'LANG', 'DBUS_SESSION_BUS_ADDRESS', 'XDG_RUNTIME_DIR']) if (process.env[key]) env[key] = process.env[key];
      const child = spawn(pythonExecutable(), [fileURLToPath(new URL('../../../services/codex/credentials.py', import.meta.url))], {env, stdio: ['pipe', 'pipe', 'ignore']});
      let output = ''; let settled = false;
      const finish = (error?: Error, result?: unknown) => {
        if (settled) return; settled = true; clearTimeout(timer);
        if (error) {child.kill('SIGKILL'); reject(error);} else resolve(result);
      };
      const timer = setTimeout(() => finish(new Error('OS credential storage did not respond. Unlock it and retry.')), 30000);
      child.on('error', () => finish(new Error('The Codex OS credential helper could not start.')));
      child.stdin.on('error', () => finish(new Error('The Codex OS credential helper disconnected.')));
      child.stdout.on('data', chunk => {output += chunk; if (Buffer.byteLength(output) > 262144) finish(new Error('Invalid credential helper response.'));});
      child.on('close', code => {
        if (settled) return;
        try {
          const frame = JSON.parse(output);
          if (code !== 0 || frame.error || !frame.result) throw new Error();
          finish(undefined, frame.result);
        } catch {finish(new Error('OS credential storage is unavailable or locked. Unlock it and retry; no plaintext fallback was used.'));}
      });
      // Credentials are transmitted only on the private child pipe, never argv/env.
      child.stdin.end(JSON.stringify({operation, reference, ...(value !== undefined ? {value} : {})}));
    });
  }
  async get(reference: string): Promise<string | undefined> {
    const result = await this.call('get', reference);
    if (result.value === null || result.value === undefined) return;
    if (typeof result.value !== 'string') throw new Error('Invalid OS credential record.');
    return result.value;
  }
  async put(reference: string, value: string): Promise<void> {await this.call('put', reference, value);}
  async delete(reference: string): Promise<void> {await this.call('delete', reference);}
}
