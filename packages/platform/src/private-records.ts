// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {pythonExecutable,componentEnvironment} from './index.js';
const helper=fileURLToPath(new URL('../../../services/platform_adapters/node_records.py',import.meta.url));
/** Existing kernel ACL/reparse/single-link checks; never silently repair foreign state. */
export function windowsRecord(operation:'directory'|'write'|'read'|'verify',path:string,value?:unknown):string{
 if(process.platform!=='win32')throw Error('Windows record adapter requires Windows.');
 const result=spawnSync(pythonExecutable(),['-I','-Xutf8','-B',helper,operation,path],{input:operation==='write'?JSON.stringify(value):undefined,encoding:'utf8',env:componentEnvironment(),windowsHide:true,timeout:10000,maxBuffer:20*1024*1024});
 if(result.error||result.status!==0)throw Error('Private Windows record operation was refused.');
 return result.stdout;
}
