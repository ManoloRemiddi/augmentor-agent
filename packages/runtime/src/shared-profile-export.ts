// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {lstatSync,realpathSync,cpSync,chmodSync} from 'node:fs';
import {join,dirname,resolve,isAbsolute,relative} from 'node:path';
import {createHash} from 'node:crypto';
import type {SharedProfile} from './shared-profile-import.js';
import {validateSharedDatabases} from './shared-profile-import.js';
import {acquireProfileLease,acquireFileLease,profileFence,isTransactionTree,isNativeArchive,isSharedArchive} from './profile-lease.js';
import {present,stateInventory,stateTransaction} from './profile-transaction.js';

const databases=['prompts.sqlite3','dual-memory.sqlite3','memory.sqlite3'];
const files=[...databases,'hindsight.json','hindsight-installation.json'];
function folder(path:string){
 if(!isAbsolute(path)||resolve(path)!==path||realpathSync(path)!==path)throw Error('Choose canonical real absolute shared-profile paths.');
 const stat=lstatSync(path);if(!stat.isDirectory()||stat.uid!==process.getuid?.()||(stat.mode&0o077))throw Error('Legacy export needs private owned directories.');
}
function overlap(a:string,b:string){const r=relative(a,b);return !r||!r.startsWith('..')&&!isAbsolute(r);}
function profile(value:SharedProfile){
 if(process.platform!=='linux')throw Error('Legacy shared-profile export is currently qualified only on Linux.');
 folder(value.state);folder(value.data);
 if(overlap(value.state,value.data)||overlap(value.data,value.state))throw Error('Use separate companion state and data roots.');
 if(isTransactionTree(value.data)||isNativeArchive(value.data)||isSharedArchive(value.data)||present(profileFence(value.data)))throw Error('Evidence or unfinished migration data cannot be exported for adoption.');
 const parent=lstatSync(dirname(value.data));if(parent.uid!==process.getuid?.()||(parent.mode&0o022))throw Error('Legacy data parent must be owned and protected from other writers.');
}
function companionLocks(state:string){
 const held:ReturnType<typeof acquireFileLease>[]=[];
 try{for(const name of ['prompts','dual-memory'])held.push(acquireFileLease(join(state,name+'.lock')));return {close(){while(held.length)held.pop()!.close();}};}
 catch(error){while(held.length)held.pop()!.close();throw error;}
}
function selected(data:string){
 if(present(join(data,'shared-imports')))throw Error('Existing shared import archives need an explicit export adapter.');
 for(const name of databases){
  if(!present(join(data,name)))throw Error('Initialize and cleanly stop all three legacy databases before export.');
  for(const suffix of ['-wal','-shm','-journal'])if(present(join(data,name+suffix)))throw Error('Recover and cleanly stop SQLite journals before export.');
 }
 let bytes=0;const components=[];
 for(const name of files){
  const path=join(data,name),stat=present(path);if(!stat)continue;
  if(!stat.isFile()||stat.isSymbolicLink()||stat.uid!==process.getuid?.()||stat.nlink!==1||(stat.mode&0o077))throw Error('Export requires private owned regular unlinked component files.');
  if(stat.size>(name.endsWith('.json')?1024*1024:2*1024**3))throw Error('Legacy shared component exceeds its size bound.');
  const inventory=stateInventory(path),row=inventory.rows[0];bytes+=inventory.bytes;
  if(bytes>4*1024**3)throw Error('Legacy shared components exceed four GiB.');
  components.push({name,mode:row.mode,bytes:row.bytes!,sha256:row.sha256!});
 }
 return {sha256:createHash('sha256').update(JSON.stringify(components)).digest('hex'),bytes,components};
}
/** Inspect only the explicit shared components of a cold mixed application root.
 * Application files are neither traversed nor placed in a store transaction. */
export async function inspectLegacySharedProfile(source:SharedProfile){
 profile(source);const old=companionLocks(source.state);let lease:ReturnType<typeof acquireProfileLease>|undefined;
 try{lease=acquireProfileLease(source.data,{maintenance:true});const before=selected(source.data);await validateSharedDatabases(source.data);if(selected(source.data).sha256!==before.sha256)throw Error('Legacy components changed during inspection.');return {schema:'augmentor-legacy-shared-inspection/1',...before};}
 finally{lease?.close();old.close();}
}
/** Exact copy into a previously absent dedicated root. Does not merge identities,
 * change source files, switch launchers, or construct an engine/service/model. */
export async function exportLegacySharedProfile(source:SharedProfile,target:SharedProfile,expectedSha256:string){
 profile(source);folder(target.state);
 if(!isAbsolute(target.data)||resolve(target.data)!==target.data||present(target.data))throw Error('Choose a new absent dedicated shared-data path.');
 for(const a of [source.state,source.data,target.state])if(overlap(a,target.data)||overlap(target.data,a))throw Error('Legacy source, target state and dedicated data must not overlap.');
 for(const a of [source.state,source.data])if(overlap(a,target.state)||overlap(target.state,a))throw Error('Legacy source and target state must not overlap.');
 if(!/^[a-f0-9]{64}$/.test(expectedSha256))throw Error('Inspect the cold legacy components before export.');
 const old=companionLocks(source.state);let targetLocks:ReturnType<typeof companionLocks>|undefined,lease:ReturnType<typeof acquireProfileLease>|undefined;
 try{
  targetLocks=companionLocks(target.state);lease=acquireProfileLease(source.data,{maintenance:true});const before=selected(source.data);
  if(before.sha256!==expectedSha256)throw Error('Legacy components changed since inspection.');
  await validateSharedDatabases(source.data);
  return await stateTransaction(target.data,async stage=>{
   for(const row of before.components){const path=join(stage,row.name);cpSync(join(source.data,row.name),path,{errorOnExist:true,force:false,preserveTimestamps:true});chmodSync(path,row.mode);}
   if(selected(stage).sha256!==before.sha256)throw Error('Legacy component copy differs from the inspected source.');
   await validateSharedDatabases(stage);
   if(selected(source.data).sha256!==before.sha256)throw Error('Legacy components changed before export publication.');
   return {schema:'augmentor-legacy-shared-export/1',sourceSha256:before.sha256,components:before.components,sourceRetained:true,applicationFilesCopied:false,engineConfigurationPreserved:true,externalEngineCopiedOrCalled:false,modelWorkSubmitted:false};
  },{requireAbsent:true});
 }finally{lease?.close();targetLocks?.close();old.close();}
}
