// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import type {RpcOptions} from './rpc.js';
import {resolveCodexRuntime} from './runtime.js';
export {CODEX_VERSION, installedRuntimeVersion} from './runtime.js';

export type ConnectionKind = 'api' | 'local' | 'chatgpt' | 'chatgpt-plan';
export interface CodexConnection {
  kind: ConnectionKind;
  model: string;
  endpoint?: string;
  credential?: string;
  wireApi?: 'responses';
  imageInput?: boolean;
}
const ALLOWED_ENV = ['PATH', 'HOME', 'USER', 'LOGNAME', 'LANG', 'LC_ALL', 'TMPDIR',
  'XDG_RUNTIME_DIR', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME', 'DISPLAY',
  'WAYLAND_DISPLAY', 'DBUS_SESSION_BUS_ADDRESS', 'SSL_CERT_FILE', 'SSL_CERT_DIR', 'CODEX_CA_CERTIFICATE'];

export function runtimeOptions(connection: CodexConnection, stateDirectory: string, cwd: string): RpcOptions {
  if (!connection.model || connection.model.length > 256 || /[\r\n\0]/.test(connection.model)) throw new Error('Choose a valid Codex model.');
  if (!['api', 'local', 'chatgpt', 'chatgpt-plan'].includes(connection.kind)) throw new Error('Unsupported Codex connection.');
  if (connection.wireApi !== undefined && connection.wireApi !== 'responses') throw new Error('This pinned Codex runtime requires the Responses API; Chat Completions is not supported.');
  const env: NodeJS.ProcessEnv = {};
  for (const key of ALLOWED_ENV) if (process.env[key] !== undefined) env[key] = process.env[key];
  env.CODEX_HOME = stateDirectory;
  const runtime = resolveCodexRuntime();
  const args = [...runtime.args, 'app-server', '--listen', 'stdio://'];
  const config = (key: string, value: unknown) => args.push('-c', `${key}=${JSON.stringify(value)}`);
  config('model', connection.model);
  config('analytics.enabled', false);
  config('web_search', 'disabled');
  config('approval_policy', 'on-request');
  config('approvals_reviewer', 'user');
  config('features.default_mode_request_user_input', true);
  config('sandbox_mode', 'workspace-write');
  config('shell_environment_policy.inherit', 'none');
  config('shell_environment_policy.include_only', ALLOWED_ENV);
  // The model's shell process must never inherit provider authentication.
  config('shell_environment_policy.exclude', ['AUGMENTOR_CODEX_CREDENTIAL', '*TOKEN*', '*SECRET*', '*API_KEY*']);
  if (connection.kind !== 'chatgpt') {
    const endpoint = connection.kind === 'chatgpt-plan' ? 'https://api.openai.com/v1' : connection.endpoint;
    if (!endpoint) throw new Error('Configure the provider endpoint.');
    const url = new URL(endpoint);
    if (url.username || url.password || url.search || url.hash) throw new Error('Provider URLs cannot contain credentials, queries or fragments.');
    const local = ['127.0.0.1', '[::1]', 'localhost'].includes(url.hostname);
    if (url.protocol !== 'https:' && !(url.protocol === 'http:' && local)) throw new Error('Use HTTPS for remote providers or HTTP on loopback.');
    if (connection.kind === 'local' && !local) throw new Error('Local profiles require a loopback endpoint.');
    if (connection.kind === 'chatgpt-plan' && !connection.credential) throw new Error('Connect your ChatGPT plan before starting Codex.');
    config('model_provider', 'augmentor');
    config('model_providers.augmentor.name', 'Augmentor selected connection');
    config('model_providers.augmentor.base_url', url.href.replace(/\/$/, ''));
    config('model_providers.augmentor.wire_api', connection.kind === 'chatgpt-plan' ? 'responses' : connection.wireApi ?? 'responses');
    config('model_providers.augmentor.requires_openai_auth', false);
    config('model_providers.augmentor.supports_websockets', false);
    config('model_providers.augmentor.request_max_retries', 0);
    config('model_providers.augmentor.stream_max_retries', 0);
    if (connection.credential) {
      env.AUGMENTOR_CODEX_CREDENTIAL = connection.credential;
      config('model_providers.augmentor.env_key', 'AUGMENTOR_CODEX_CREDENTIAL');
    }
  }
  return {command: runtime.command, args, cwd, env};
}
