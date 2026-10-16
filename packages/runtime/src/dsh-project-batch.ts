// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {readFileSync,lstatSync,readdirSync} from 'node:fs';
import {join,isAbsolute,resolve,dirname} from 'node:path';
import {createHash,randomUUID} from 'node:crypto';
import {SessionManager} from '@earendil-works/pi-coding-agent';
import {prepareDshProject,type ImportOptions} from './dsh-project-import.js';
import {stateTransaction,present} from './profile-transaction.js';
import {WorkspaceRegistry} from './workspace-registry.js';
import {SessionOrganization} from './session-organization.js';
import {atomicJson} from './storage.js';
import {identifier,type Data} from '../../protocol/src/index.js';
export type DshProjectInput={sourceFile:string;options:ImportOptions};
const digest=(value:Buffer|string)=>createHash('sha256').update(value).digest('hex');
const targetId=(sourceId:string)=>'dsh-import-'+digest(sourceId).slice(0,24);
function json(path:string,max=32*1024*1024):Data{const stat=lstatSync(path);if(!stat.isFile()||stat.isSymbolicLink()||stat.size>max)throw Error('Expected a bounded regular private import record.');return JSON.parse(readFileSync(path,'utf8'));}
/** Consolidate explicitly chosen projects into one new or cold existing state.
 * Existing native conversations are never relocated, regenerated or replayed.
 * An earlier import is retained only when its original source cut still matches;
 * divergence is a conflict, never an automatic overwrite or stale-source skip. */
export async function importDshProjects(inputs:DshProjectInput[],targetState:string){
 if(!Array.isArray(inputs)||!inputs.length||inputs.length>128)throw Error('Choose one to 128 project exports.');
 let exportBytes=0;for(const input of inputs){if(!input||typeof input.sourceFile!=='string'||!isAbsolute(input.sourceFile))throw Error('Choose an absolute project export file.');const info=lstatSync(input.sourceFile);exportBytes+=info.size;if(!info.isFile()||info.isSymbolicLink()||info.size>32*1024*1024||exportBytes>256*1024*1024)throw Error('Combined regular exports exceed their 32 MiB/project or 256 MiB batch bound.');}
 const projects=inputs.map(input=>{if(!input||!isAbsolute(input.sourceFile))throw Error('Choose an absolute project export file.');return prepareDshProject(input.sourceFile,input.options);});
 if(projects.reduce((n,p)=>n+p.bytes.length,0)>256*1024*1024)throw Error('Combined exports exceed 256 MiB.');
 const workspaces=new Set<string>(),sourceIds=new Set<string>();
 for(const project of projects){if(workspaces.has(project.cwd))throw Error('The same workspace appears in more than one export.');workspaces.add(project.cwd);for(const id of project.ids){if(sourceIds.has(id))throw Error('A source conversation belongs to more than one chosen project.');sourceIds.add(id);}}
 const batchId=randomUUID();
 return stateTransaction(targetState,async stage=>{
  const metas=new Map<string,Data>(),sessions=join(stage,'sessions');
  if(present(sessions))for(const name of readdirSync(sessions).filter(name=>name.endsWith('.meta.json'))){
   const meta=json(join(sessions,name),1024*1024),sid=identifier(meta.id);if(name!==sid+'.meta.json'||metas.has(sid)||meta.running===true)throw Error('Existing session identity/running state requires inspection.');if(meta.file!==undefined&&(typeof meta.file!=='string'||!isAbsolute(meta.file)||resolve(meta.file)!==meta.file||dirname(meta.file)!==join(targetState,'sessions',sid)))throw Error('Existing native conversation points outside this profile. Relocate it explicitly before consolidation.');metas.set(sid,meta);
  }
  if(new Set([...metas.keys(),...[...sourceIds].map(targetId)]).size>5000)throw Error('Combined conversation catalogue exceeds its bound.');
  const registry=new WorkspaceRegistry(join(stage,'workspaces.json'),()=>[...metas.values()].filter(m=>m.saved).map(m=>m.cwd)),organization=new SessionOrganization(join(stage,'session-organization.json')),next=registry.snapshot(),members=organization.snapshot();
  const created:Data[]=[],retained:Data[]=[],projectReceipts:Data[]=[];
  for(const project of projects){
   if(next.removed.includes(project.cwd))throw Error('A chosen workspace was explicitly removed in Harness. Restore it before migration.');
   const include=new Set<string>();
   for(const id of project.ids){
    const sid=targetId(id),meta=metas.get(sid);if(!meta){if(present(join(sessions,sid))||present(join(sessions,sid+'.events.jsonl')))throw Error('Import identity collides with existing session files.');include.add(id);continue;}
    if(meta.cwd!==project.cwd||typeof meta.file!=='string'||resolve(meta.file)!==meta.file||dirname(meta.file)!==join(targetState,'sessions',sid))throw Error('Existing import identity has different native ownership.');
    const native=join(stage,'sessions',sid,meta.file.split(/[\\/]/).at(-1)!);if(lstatSync(native).size>128*1024*1024)throw Error('Existing native conversation exceeds its offline inspection bound.');
    const manager=SessionManager.open(native),audit=manager.getEntries().find(entry=>entry.type==='custom'&&entry.customType==='augmentor.dsh-import.v1');
    const origin=audit?.type==='custom'?audit.data as Data:undefined;
    if(!origin||origin.sourceSessionId!==id||!/^[a-f0-9]{64}$/.test(origin.sha256))throw Error('Existing conversation is not a verified copy of this source.');
    const archivePath=join(stage,'dsh-imports',origin.sha256+'.json'),raw=readFileSync(archivePath);if(digest(raw)!==origin.sha256)throw Error('Existing source archive checksum differs.');
    const archive=json(archivePath),old=archive.sessions?.find((row:Data)=>row.opening?.header?.id===id),current=project.sourceCut(id);
    if(!old||!current||old.opening.header.cwd!==project.cwd||old.opening.cursor!==current.opening.cursor||digest(JSON.stringify(old.records))!==digest(JSON.stringify(current.records)))throw Error('DSH and the earlier Harness import diverged. Preserve both; choose a conflict policy before migration.');
    retained.push({sourceSessionId:id,sessionId:sid,cwd:meta.cwd,selection:meta.selection,reason:'Original source cut matches; entire existing Harness continuation retained unchanged'});
   }
   const written=await project.write(stage,targetState,include);created.push(...written.receipts);projectReceipts.push({sourceSha256:project.sha256,cwd:project.cwd,createdSessionIds:written.receipts.map(row=>row.sessionId),retainedSessionIds:project.ids.filter(id=>!include.has(id)).map(targetId)});
   if(!next.items.some(row=>row.cwd===project.cwd))next.items.push({workspaceId:project.cwd,cwd:project.cwd,title:project.source.workspace.title});
   for(const id of project.archived)if(include.has(id))members.archivedSessionIds.push(targetId(id));
   for(const id of project.pinned)if(include.has(id)&&!project.archived.has(id))members.pinnedSessionIds.push(targetId(id));
  }
  if(next.items.length>1000)throw Error('Combined workspace catalogue exceeds its bound.');
  next.revision++;members.revision++;atomicJson(join(stage,'workspaces.json'),next);atomicJson(join(stage,'session-organization.json'),members);
  // Reuse the runtime's actual schema validators before any publication.
  new WorkspaceRegistry(join(stage,'workspaces.json'),()=>[]).snapshot();new SessionOrganization(join(stage,'session-organization.json')).snapshot();
  const receipt={schema:'augmentor-dsh-project-batch/1',batchId,projects:projectReceipts,createdSessions:created,retainedSessions:retained,existingConversationsPreserved:metas.size,existingNativeBytesRewritten:false,historicalCallsExecuted:false,continuationModelsChanged:false,configAndCompanionRootsChanged:false};
  atomicJson(join(stage,'dsh-imports','batches',batchId+'.json'),receipt);return receipt;
 });
}
