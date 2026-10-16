// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {openSync,closeSync,lstatSync,fstatSync,constants,mkdirSync,existsSync,realpathSync} from 'node:fs';
import {dirname,basename,join,resolve} from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {pythonExecutable,componentEnvironment} from '../../platform/src/index.js';
export class ProfileBusy extends Error{}
export const isTransactionTree=(state:string)=>/^\..+\.import-[-a-f0-9]{36}\.(?:stage|backup)$/.test(basename(state));
export function profileFence(state:string){const absolute=resolve(state);return join(dirname(absolute),'.'+basename(absolute)+'.augmentor-migration.json');}
/** POSIX flock belongs to Node's retained open file description, not a helper
 * process or PID file. It survives a helper's exit, and releases on owner death.
 * The lease/fence live outside the replaceable state directory. */
export function acquireProfileLease(state:string,{maintenance=false}={}){
 if(!maintenance&&isTransactionTree(resolve(state)))throw Error('Migration backups/staging trees must be restored to the original state path before opening Harness.');
 if(process.platform==='win32'){if(maintenance)throw Error('Profile consolidation is not qualified on Windows.');if(existsSync(profileFence(state)))throw Error('An unfinished profile migration requires inspection before starting Harness.');return {close(){}};}
 const requested=resolve(state);mkdirSync(dirname(requested),{recursive:true,mode:0o700});
 const absolute=existsSync(requested)?realpathSync(requested):join(realpathSync(dirname(requested)),basename(requested)),parent=dirname(absolute);
 if(!maintenance&&isTransactionTree(absolute))throw Error('Migration backups/staging trees must be restored to the original state path before opening Harness.');
 const path=join(parent,'.'+basename(absolute)+'.augmentor-owner.lock'),fd=openSync(path,constants.O_RDWR|constants.O_CREAT|(constants.O_NOFOLLOW??0),0o600);let held=true;
 const close=()=>{if(held){held=false;closeSync(fd);}};
 try{
  const a=fstatSync(fd),b=lstatSync(path);if(!a.isFile()||a.uid!==process.getuid?.()||a.nlink!==1||(a.mode&0o077)||a.dev!==b.dev||a.ino!==b.ino)throw Error('Profile lease needs a private owned regular file.');
  const helper=fileURLToPath(new URL('../../../services/platform_adapters/profile_lease.py',import.meta.url));
  const result=spawnSync(pythonExecutable(),['-I','-B',helper],{stdio:['ignore','pipe','pipe',fd],encoding:'utf8',env:componentEnvironment(),timeout:10000,maxBuffer:65536});
  if(result.status===3)throw new ProfileBusy('This profile is already owned by a runtime or migration.');
  if(result.error||result.status!==0||result.stdout.trim()!=='locked')throw Error('The profile kernel lease could not be acquired.');
  if(!maintenance&&existsSync(profileFence(absolute)))throw Error('An unfinished profile migration requires inspection before starting Harness.');
  return {close};
 }catch(error){close();throw error;}
}
