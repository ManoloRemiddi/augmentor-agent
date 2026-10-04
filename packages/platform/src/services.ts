// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
/** A short startup request; the authenticated Windows owner retains the service. */
import {execFile} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {componentEnvironment,pythonExecutable} from './index.js';

export function ensureWindowsCompanion(name:'prompts'|'memory',signal?:AbortSignal):Promise<void>{
  if(process.platform!=='win32'||!['prompts','memory'].includes(name))
    return Promise.reject(new Error('Unsupported Windows companion startup.'));
  return new Promise((resolve,reject)=>{
    execFile(pythonExecutable(),['-I','-Xutf8','-B',
      fileURLToPath(new URL('../../../services/windows_supervisor.py',import.meta.url)),
      '--ensure-companion',name],
      {env:componentEnvironment(),windowsHide:true,signal,timeout:35000,maxBuffer:65536},error=>{
        if(error)reject(new Error('The Augmentor background service could not start; no request was replayed.'));
        else resolve();
      });
  });
}
