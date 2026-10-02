// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {existsSync} from 'node:fs';
import {durableJson, readPrivateJson} from './storage.js';
export type Access = 'read-only' | 'workspace-write' | 'danger-full-access';
export const accessValues: Access[] = ['read-only', 'workspace-write', 'danger-full-access'];
export function nativePolicy(access: Access) {
  // Ask mode requires an explicit native escalation before filesystem writes.
  return {approvalPolicy: access === 'workspace-write' ? 'on-request' : 'never', sandbox: access === 'danger-full-access' ? 'danger-full-access' : 'read-only'};
}
const observation = new Set(['browser_tabs_list','browser_snapshot','browser_screenshot','linux_desktop_connect','linux_desktop_snapshot','linux_desktop_observe','linux_desktop_stop','memory_recall','memory_source','home_devices','home_read','home_status','home_result','home_cancel']);
export function actionNeedsApproval(name: string): boolean {return !observation.has(name);}
export class AccessSettings {
  constructor(readonly path: string) {}
  read(): {revision: number; defaultPreset: Access} {
    const value = existsSync(this.path) ? readPrivateJson(this.path) as any : {revision: 0, defaultPreset: 'danger-full-access'};
    if (!Number.isSafeInteger(value.revision) || value.revision < 0 || !accessValues.includes(value.defaultPreset)) throw new Error('Invalid Codex access settings.');
    return value;
  }
  describe() {const {revision, defaultPreset} = this.read(); return {ns: 'permission', revision, value: {defaultPreset}};}
  mutate(params: any) {
    const value = this.read(), op = params.ops?.[0];
    if (params.ns !== 'permission' || params.expectedRevision !== value.revision || params.ops?.length !== 1 || op.op !== 'set' || JSON.stringify(op.path) !== '["defaultPreset"]' || !accessValues.includes(op.value)) throw new Error('Access changed elsewhere or the requested policy is invalid. Reload settings.');
    durableJson(this.path, {revision: value.revision+1, defaultPreset: op.value}); return this.describe();
  }
}
