// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {execFileSync} from 'node:child_process';
import {existsSync, mkdtempSync, readFileSync, realpathSync, rmSync, statSync} from 'node:fs';
import {homedir, tmpdir} from 'node:os';
import {isAbsolute, join} from 'node:path';
import {fileURLToPath} from 'node:url';

export const CODEX_VERSION = '0.159.2';
export interface RuntimeSelection {cliPath?: string; bundledPackage?: string | null; userPackage?: string;}
export interface RuntimeCommand {command: string; args: string[];}
const missing = `Install Codex ${CODEX_VERSION} separately; see docs/CODEX-PACKAGING.md. Set AUGMENTOR_CODEX_CLI to its absolute executable path if installed elsewhere.`;

export function resolveCodexRuntime(selection: RuntimeSelection = {}): RuntimeCommand {
  const explicit = selection.cliPath ?? process.env.AUGMENTOR_CODEX_CLI;
  if (explicit !== undefined) {
    if (!isAbsolute(explicit) || /[\r\n\0]/.test(explicit)) throw new Error('AUGMENTOR_CODEX_CLI must be an absolute executable path.');
    // An explicit selection never falls back to another installation.
    if (!existsSync(explicit) || !statSync(explicit).isFile()) throw new Error(missing);
    const path = realpathSync(explicit);
    return path.endsWith('.js') ? {command: process.execPath, args: [path]} : {command: path, args: []};
  }
  const bundled = selection.bundledPackage === undefined
    ? fileURLToPath(new URL('../../../node_modules/@openai/codex', import.meta.url)) : selection.bundledPackage;
  const dataHome = process.env.XDG_DATA_HOME || (process.platform === 'darwin'
    ? join(homedir(), 'Library', 'Application Support', 'Augmentor', 'data') : join(homedir(), '.local', 'share'));
  const user = selection.userPackage ?? join(dataHome,
    'augmentor', 'codex-cli', CODEX_VERSION, 'node_modules', '@openai', 'codex');
  const root = bundled && existsSync(join(bundled, 'package.json')) ? bundled : user;
  if (!existsSync(join(root, 'package.json'))) throw new Error(missing);
  const metadata = JSON.parse(readFileSync(join(root, 'package.json'), 'utf8'));
  if (metadata.name !== '@openai/codex' || metadata.version !== CODEX_VERSION || metadata.bin?.codex !== 'bin/codex.js') {
    throw new Error(`Unsupported Codex package; this release requires ${CODEX_VERSION}.`);
  }
  const entry = join(root, 'bin', 'codex.js');
  if (!existsSync(entry) || !statSync(entry).isFile()) throw new Error(missing);
  return {command: process.execPath, args: [realpathSync(entry)]};
}

export function installedRuntimeVersion(selection: RuntimeSelection = {}): string {
  const runtime = resolveCodexRuntime(selection);
  const state = mkdtempSync(join(tmpdir(), 'augmentor-codex-version-'));
  try {
    // A version probe must not inherit keys or use the user's global auth home.
    const env: NodeJS.ProcessEnv = {CODEX_HOME: state};
    for (const key of ['PATH', 'HOME', 'USER', 'LOGNAME', 'LANG', 'LC_ALL', 'TMPDIR', 'SYSTEMROOT']) {
      if (process.env[key] !== undefined) env[key] = process.env[key];
    }
    let version: string;
    try {
      version = execFileSync(runtime.command, [...runtime.args, '--version'], {
        env, encoding: 'utf8', timeout: 10_000, maxBuffer: 8192, stdio: ['ignore', 'pipe', 'ignore'],
      }).trim();
    } catch {throw new Error(`Could not verify Codex ${CODEX_VERSION}. ${missing}`);}
    if (version !== `codex-cli ${CODEX_VERSION}`) throw new Error(`Unsupported Codex executable; this release requires ${CODEX_VERSION}.`);
    return CODEX_VERSION;
  } finally {rmSync(state, {recursive: true, force: true});}
}
