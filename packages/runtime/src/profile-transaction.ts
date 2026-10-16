// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {constants,chmodSync,openSync,closeSync,readSync,fstatSync,lstatSync,readdirSync,cpSync,rmSync,renameSync,readFileSync,fsyncSync,realpathSync} from 'node:fs';
import {join,dirname,basename,isAbsolute,resolve} from 'node:path';
import {createHash,randomUUID} from 'node:crypto';
import {acquireProfileLease,profileFence,isTransactionTree} from './profile-lease.js';
import {atomicJson,privateDir} from './storage.js';
export const present=(path:string)=>{try{return lstatSync(path);}catch(error){if((error as NodeJS.ErrnoException).code==='ENOENT')return undefined;throw error;}};
const hash=(value:string)=>createHash('sha256').update(value).digest('hex');
export function stateInventory(root:string){
 const rows:{path:string;kind:'directory'|'file';mode:number;bytes?:number;sha256?:string}[]=[];let total=0;
 const walk=(path:string,key:string)=>{
  const stat=lstatSync(path);if(stat.isSymbolicLink()||stat.uid!==process.getuid?.())throw Error('State snapshots require owned regular files/directories without links.');
  if(rows.length>=100000)throw Error('State snapshot exceeds 100,000 entries.');
  if(stat.isDirectory()){
   rows.push({path:key,kind:'directory',mode:stat.mode&0o777});for(const name of readdirSync(path).sort())walk(join(path,name),key?key+'/'+name:name);
  }else if(stat.isFile()){
   total+=stat.size;if(total>4*1024*1024*1024)throw Error('State snapshot exceeds four GiB.');
   const fd=openSync(path,constants.O_RDONLY|(constants.O_NOFOLLOW??0));try{
    const before=fstatSync(fd);if(before.dev!==stat.dev||before.ino!==stat.ino||before.size!==stat.size)throw Error('State changed while reading.');
    const digest=createHash('sha256'),buffer=Buffer.alloc(1024*1024);let bytes=0,n;while((n=readSync(fd,buffer,0,buffer.length,null))){bytes+=n;if(bytes>stat.size)throw Error('State changed while reading.');digest.update(buffer.subarray(0,n));}
    const after=fstatSync(fd);if(bytes!==stat.size||before.mtimeMs!==after.mtimeMs||before.ctimeMs!==after.ctimeMs||before.size!==after.size)throw Error('State changed while reading.');
    rows.push({path:key,kind:'file',mode:stat.mode&0o777,bytes,sha256:digest.digest('hex')});
   }finally{closeSync(fd);}
  }else throw Error('Stop the profile and remove no live IPC: state contains a socket or unsupported object.');
 };
 walk(root,'');return {sha256:hash(JSON.stringify(rows)),entries:rows.length,bytes:total,rows};
}
function flush(path:string){const fd=openSync(path,constants.O_RDONLY|(constants.O_NOFOLLOW??0));try{fsyncSync(fd);}finally{closeSync(fd);}}
function flushTree(root:string){for(const name of readdirSync(root)){const path=join(root,name);if(lstatSync(path).isDirectory())flushTree(path);else flush(path);}flush(root);}
function targetPath(state:string){
 if(process.platform!=='linux')throw Error('Transactional profile consolidation is currently qualified only on Linux.');
 if(isTransactionTree(state))throw Error('Choose the original state path, not a migration backup or stage.');
 if(!isAbsolute(state)||resolve(state)!==state)throw Error('Choose a canonical absolute state path.');const parent=dirname(state),stat=lstatSync(parent);
 if(realpathSync(parent)!==parent||!stat.isDirectory()||stat.isSymbolicLink()||stat.uid!==process.getuid?.()||(stat.mode&0o077))throw Error('State migration needs a private owned parent.');
 const old=present(state);if(old&&(!old.isDirectory()||old.isSymbolicLink()||(old.mode&0o077)))throw Error('State migration requires a private real directory.');return state;
}
function cold(state:string){
 const descriptor=join(state,'harness.json');if(!present(descriptor))return;
 const info=lstatSync(descriptor);if(!info.isFile()||info.isSymbolicLink()||info.size>65536)throw Error('Harness owner descriptor is invalid.');
 const pid=JSON.parse(readFileSync(descriptor,'utf8')).pid;
 if(!Number.isSafeInteger(pid)||pid<1)throw Error('Harness owner is unverified. Stop and inspect the profile.');
 try{process.kill(pid,0);}catch(error){if((error as NodeJS.ErrnoException).code==='ESRCH')return;throw Error('Harness owner liveness is unknown.');}
 throw Error('Stop the existing Harness owner before migration.');
}
type Journal={schema:'augmentor-profile-migration/1';transactionId:string;state:string;stage:string;backup:string;before:string|null;after:string;status?:string};
function locations(state:string,id:string){const prefix=join(dirname(state),'.'+basename(state)+'.import-'+id);return {stage:prefix+'.stage',backup:prefix+'.backup',receipt:prefix+'.json'};}
function journal(state:string):Journal{
 const path=profileFence(state),stat=lstatSync(path);if(!stat.isFile()||stat.isSymbolicLink()||stat.uid!==process.getuid?.()||(stat.mode&0o077)||stat.size>65536)throw Error('Migration journal is not a private owned record.');
 const value=JSON.parse(readFileSync(path,'utf8')) as Journal;
 if(value.schema!=='augmentor-profile-migration/1'||value.state!==state||!/^[-a-f0-9]{36}$/.test(value.transactionId)||value.before!==null&&!/^[a-f0-9]{64}$/.test(value.before)||!/^[a-f0-9]{64}$/.test(value.after))throw Error('Invalid migration journal. Preserve all state copies.');
 const paths=locations(state,value.transactionId);if(value.stage!==paths.stage||value.backup!==paths.backup)throw Error('Migration journal paths differ.');return value;
}
function complete(value:Journal,status:string){atomicJson(profileFence(value.state),{...value,status});const path=locations(value.state,value.transactionId).receipt;if(present(path))throw Error('Migration completion record already exists.');renameSync(profileFence(value.state),path);flush(dirname(value.state));return {transactionId:value.transactionId,state:value.state,backup:value.before===null?null:value.backup,receipt:path,status};}
/** Copy-on-write, same-location adoption. A durable external journal fences
 * startup across both renames; a crash preserves every tree for explicit recovery.
 * Old native messages/absolute attachment paths remain byte-for-byte valid. */
export async function stateTransaction<T>(state:string,build:(stage:string)=>Promise<T>){
 targetPath(state);const lease=acquireProfileLease(state,{maintenance:true});let stage:string|undefined,armed=false;
 try{
  if(present(profileFence(state)))throw Error('Inspect the unfinished migration before starting another.');cold(state);
  const original=present(state),before=original?stateInventory(state):null,id=randomUUID(),paths=locations(state,id);stage=paths.stage;
  if(present(stage)||present(paths.backup))throw Error('Migration staging path exists.');
  privateDir(stage);if(original){cpSync(state,stage,{recursive:true,preserveTimestamps:true,errorOnExist:true,force:false});for(const row of before!.rows)chmodSync(row.path?join(stage,...row.path.split('/')):stage,row.mode);}
  if(before&&stateInventory(stage).sha256!==before.sha256)throw Error('State copy differs from its source.');
  const result=await build(stage);flushTree(stage);const after=stateInventory(stage);
  const now=present(state);if(original?(!now||now.dev!==original.dev||now.ino!==original.ino||stateInventory(state).sha256!==before!.sha256):!!now)throw Error('Source state changed; no migration was published.');
  const value:Journal={schema:'augmentor-profile-migration/1',transactionId:id,state,stage,backup:paths.backup,before:before?.sha256??null,after:after.sha256};
  atomicJson(profileFence(state),value);flush(dirname(state));armed=true;
  if(original)renameSync(state,paths.backup);renameSync(stage,state);flush(dirname(state));
  const transaction=complete(value,'completed');armed=false;return {result,transaction,before:before?{sha256:before.sha256,entries:before.entries,bytes:before.bytes}:null,after:{sha256:after.sha256,entries:after.entries,bytes:after.bytes}};
 }finally{if(stage&&!armed&&present(stage))rmSync(stage,{recursive:true,force:true});lease.close();}
}
/** Recovery never re-runs build, import, model work or tools. It only adopts
 * verified already-built bytes or restores the unchanged original directory. */
export function recoverStateTransaction(state:string,action:'inspect'|'finish'|'rollback'){
 targetPath(state);const lease=acquireProfileLease(state,{maintenance:true});try{
  const value=journal(state),current=present(state)?stateInventory(state).sha256:null,staged=present(value.stage)?stateInventory(value.stage).sha256:null,backup=present(value.backup)?stateInventory(value.backup).sha256:null;
  const prepared=current===value.before&&staged===value.after&&backup===null,between=current===null&&staged===value.after&&backup===value.before,published=current===value.after&&staged===null&&backup===value.before;
  if(!prepared&&!between&&!published)throw Error('Migration copies differ from the journal; preserve all trees for inspection.');
  if(action==='inspect')return {transactionId:value.transactionId,state,current,staged,backup,phase:published?'published':prepared?'prepared':'between-renames'};
  if(action==='finish'){
   if(prepared&&value.before!==null)renameSync(state,value.backup);if(!published)renameSync(value.stage,state);
  }else if(action==='rollback'){
   if(published)renameSync(state,value.stage);if(value.before!==null&&!prepared)renameSync(value.backup,state);
  }else throw Error('Choose inspect, finish or rollback.');
  flush(dirname(state));return complete(value,action==='finish'?'completed':'rolled-back');
 }finally{lease.close();}
}
