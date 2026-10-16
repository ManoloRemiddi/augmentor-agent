// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {mkdirSync, readFileSync, writeFileSync, renameSync, existsSync, chmodSync} from 'node:fs';
import {dirname, join} from 'node:path';
import {homedir} from 'node:os';
import {randomUUID} from 'node:crypto';
import {windowsRecord} from '../../platform/src/private-records.js';
export function privateDir(path: string) {if(process.platform==='win32')windowsRecord('directory',path);else{mkdirSync(path,{recursive:true,mode:0o700});chmodSync(path,0o700);}return path;}
export function readJson<T>(path: string, fallback:T):T {
  if (!existsSync(path)) return fallback;
  if(process.platform==='win32')return JSON.parse(windowsRecord('read',path)) as T;
  return JSON.parse(readFileSync(path,'utf8'));
}
export function atomicJson(path: string, data: unknown) {
  if(process.platform==='win32'){windowsRecord('write',path,data);return;}
  privateDir(dirname(path));const tmp=path+'.'+randomUUID()+'.tmp';
  writeFileSync(tmp,JSON.stringify(data,null,2)+'\n',{mode:0o600});renameSync(tmp,path);
}
export function statePath(){return process.env.AUGMENTOR_PI_STATE || join(process.env.XDG_STATE_HOME || join(homedir(),'.local/state'),'augmentor-pi');}
export function paths() {
  const config=process.env.AUGMENTOR_PI_CONFIG || join(process.env.XDG_CONFIG_HOME || join(homedir(),'.config'),'augmentor-pi');
  const state=statePath();
  return {config:privateDir(config),state:privateDir(state),agent:privateDir(join(config,'agent')),sessions:privateDir(join(state,'sessions')),socket:process.env.AUGMENTOR_PI_SOCKET || join(state,'runtime.sock')};
}
