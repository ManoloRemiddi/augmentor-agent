// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {cpSync,chmodSync,readdirSync,lstatSync,readFileSync,existsSync} from 'node:fs';
import {join,resolve,isAbsolute,relative} from 'node:path';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {acquireProfileLease,acquireFileLease} from './profile-lease.js';
import {stateTransaction,stateInventory,requireColdState,present} from './profile-transaction.js';
import {privateDir,atomicJson} from './storage.js';
import {pythonExecutable,componentEnvironment} from '../../platform/src/index.js';
export interface SharedProfile {state:string;data:string}
const known=new Set(['prompts.sqlite3','dual-memory.sqlite3','memory.sqlite3','hindsight.json','hindsight-installation.json','shared-imports']);
function folder(path:string){
 if(!isAbsolute(path)||resolve(path)!==path)throw Error('Choose canonical absolute shared-profile paths.');
 const stat=lstatSync(path);if(!stat.isDirectory()||stat.isSymbolicLink()||stat.uid!==process.getuid?.()||(stat.mode&0o077))throw Error('Shared profiles need private owned real directories.');
}
function overlap(a:string,b:string){const r=relative(a,b);return !r||!r.startsWith('..')&&!isAbsolute(r);}
function validate(profile:SharedProfile){
 if(process.platform!=='linux')throw Error('Shared-profile consolidation is currently qualified only on Linux.');
 folder(profile.state);folder(profile.data);if(overlap(profile.state,profile.data)||overlap(profile.data,profile.state))throw Error('Use distinct companion state and data roots.');
 for(const name of readdirSync(profile.data))if(!known.has(name))throw Error('Shared data component needs an explicit adapter: '+name);
 for(const name of ['prompts.sqlite3','dual-memory.sqlite3','memory.sqlite3'])if(!present(join(profile.data,name)))throw Error('Initialize and cleanly stop both companions before shared-profile consolidation.');
}
function legacyLeases(profile:SharedProfile){
 const held:ReturnType<typeof acquireFileLease>[]=[];
 try{for(const name of ['prompts','dual-memory'])held.push(acquireFileLease(join(profile.state,name+'.lock')));return {close(){while(held.length)held.pop()!.close();}};}
 catch(error){while(held.length)held.pop()!.close();throw error;}
}
function databaseHelper(value:Record<string,unknown>):Promise<any>{
 return new Promise((done,reject)=>{
  const helper=fileURLToPath(new URL('../../../services/companion_import.py',import.meta.url)),child=spawn(pythonExecutable(),['-I','-B',helper],{stdio:['pipe','pipe','pipe'],env:componentEnvironment(),windowsHide:true});let output='',error='',finished=false;
  const timer=setTimeout(()=>{child.kill('SIGKILL');},120000);
  child.stdout.on('data',b=>{output+=b;if(Buffer.byteLength(output)>1024*1024)child.kill('SIGKILL');});child.stderr.on('data',b=>{error+=b;if(error.length>65536)child.kill('SIGKILL');});
  child.once('error',failure=>{clearTimeout(timer);finished=true;reject(failure);});child.once('close',code=>{clearTimeout(timer);if(finished)return;if(code!==0){reject(Error((value.action==='validate'?'Shared database validation refused; source remains preserved. ':'Shared database merge refused; both profiles remain preserved. ')+error.slice(-6000)));return;}try{done(JSON.parse(output));}catch(failure){reject(failure);}});
  child.stdin.on('error',()=>{});child.stdin.end(JSON.stringify(value));
 });
}
export function validateSharedDatabases(data:string){return databaseHelper({action:'validate',data});}
function buildDatabases(source:string,target:string,sha256:string,mapDefaultPerson:boolean){return databaseHelper({source,target,sha256,mapDefaultPerson});}
/** Hash and inspect a stopped shared store without changing its databases. */
export function inspectSharedProfile(profile:SharedProfile){
 validate(profile);const old=legacyLeases(profile);let lease:ReturnType<typeof acquireProfileLease>|undefined;
 try{lease=acquireProfileLease(profile.data,{maintenance:true});requireColdState(profile.data);const inventory=stateInventory(profile.data);return {schema:'augmentor-shared-profile-inspection/1',sha256:inventory.sha256,entries:inventory.entries,bytes:inventory.bytes};}
 finally{lease?.close();old.close();}
}
/** Existing target configuration/engine ownership wins. Source data is archived
 * exactly; SQLite changes happen only in the unpublished transaction stage. */
export async function importSharedProfile(source:SharedProfile,target:SharedProfile,expectedSha256:string,{mapDefaultPerson=false}={}){
 validate(source);validate(target);if(typeof mapDefaultPerson!=='boolean'||!/^[a-f0-9]{64}$/.test(expectedSha256))throw Error('Inspect the cold source and choose its person-mapping policy.');
 for(const a of [source.state,source.data])for(const b of [target.state,target.data])if(overlap(a,b)||overlap(b,a))throw Error('Source and target shared profiles must not overlap.');
 const oldSource=legacyLeases(source);let oldTarget:ReturnType<typeof legacyLeases>|undefined,lease:ReturnType<typeof acquireProfileLease>|undefined;
 try{
  oldTarget=legacyLeases(target);lease=acquireProfileLease(source.data,{maintenance:true});requireColdState(source.data);const before=stateInventory(source.data);if(before.sha256!==expectedSha256)throw Error('Shared source changed since inspection.');
  return await stateTransaction(target.data,async stage=>{
   const archive=join(stage,'shared-imports',before.sha256,'data');if(present(archive))throw Error('This shared source snapshot was already imported.');privateDir(archive);cpSync(source.data,archive,{recursive:true,preserveTimestamps:true,errorOnExist:true,force:false});for(const row of before.rows)chmodSync(row.path?join(archive,...row.path.split('/')):archive,row.mode);
   if(stateInventory(archive).sha256!==before.sha256)throw Error('Shared source changed during capture.');
   const merged=await buildDatabases(archive,stage,before.sha256,mapDefaultPerson);
   if(stateInventory(archive).sha256!==before.sha256)throw Error('Shared source archive changed during merge.');
   if(stateInventory(source.data).sha256!==before.sha256)throw Error('Shared source changed before publication.');
   for(const name of ['hindsight.json','hindsight-installation.json'])if(existsSync(join(target.data,name))&&(!existsSync(join(stage,name))||!readFileSync(join(target.data,name)).equals(readFileSync(join(stage,name)))))throw Error('Target engine configuration changed during merge.');
   const {schema:_schema,...changes}=merged;const receipt={schema:'augmentor-shared-profile-import/1',sourceSha256:before.sha256,sourceArchive:'shared-imports/'+before.sha256+'/data',sourceRetained:true,mapDefaultPerson,...changes,targetConfigurationPreserved:true,engineCopiedOrCalled:false,modelWorkSubmitted:false};atomicJson(join(stage,'shared-imports',before.sha256,'receipt.json'),receipt);return receipt;
  });
 }finally{lease?.close();oldTarget?.close();oldSource.close();}
}
