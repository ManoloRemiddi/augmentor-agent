// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {readFileSync,writeFileSync,lstatSync,readdirSync,mkdirSync,cpSync,chmodSync} from 'node:fs';
import {join,dirname,relative,isAbsolute,resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {loadDshProjectArchive,copyDshProjectArchive} from './dsh-project-archive.js';
import {CURRENT_SESSION_VERSION} from '@earendil-works/pi-coding-agent';
import {acquireProfileLease} from './profile-lease.js';
import {stateTransaction,stateInventory,requireColdState,present} from './profile-transaction.js';
import {WorkspaceRegistry} from './workspace-registry.js';
import {SessionOrganization} from './session-organization.js';
import {PiAttachments,promptAttachments,type PromptAttachment} from './attachments.js';
import {contentDigest,readRelocationBindings,relocationBindings,type RelocationRule} from './native-relocation-context.js';
import {identifier,type Data,type DisplayEvent} from '../../protocol/src/index.js';
import {atomicJson,privateDir} from './storage.js';
const hash=(bytes:Buffer|string)=>createHash('sha256').update(bytes).digest('hex');
function json(path:string,max=1024*1024):Data{const s=lstatSync(path);if(!s.isFile()||s.isSymbolicLink()||s.size>max)throw Error('Native profile record exceeds its regular-file bound.');return JSON.parse(readFileSync(path,'utf8'));}
function lines(path:string):Data[]{
 if(!present(path))return [];const s=lstatSync(path);if(!s.isFile()||s.isSymbolicLink()||s.size>128*1024*1024)throw Error('Native/display file exceeds 128 MiB.');
 const raw=readFileSync(path,'utf8');if(raw&&!raw.endsWith('\n'))throw Error('Finish or recover the incomplete source history before relocating it.');const values=raw.split('\n').filter(Boolean);if(values.length>100000)throw Error('Native/display history exceeds 100,000 records.');return values.map(line=>JSON.parse(line));
}
function nativeTree(rows:Data[]){
 const header=rows[0];if(header?.type!=='session'||header.version!==CURRENT_SESSION_VERSION||typeof header.id!=='string'||!header.id||typeof header.cwd!=='string')throw Error('Native source format needs an explicit migration first.');
 const types=new Set(['message','thinking_level_change','model_change','usage','compaction','branch_summary','custom','custom_message','label','session_info','context_edit']),seen=new Set<string>();
 for(const row of rows.slice(1)){
  if(!types.has(row.type)||typeof row.id!=='string'||!row.id||seen.has(row.id)||row.parentId!==null&&!seen.has(row.parentId))throw Error('Native source tree contains an unsupported entry, duplicate identity or missing parent.');
  if(['label','context_edit'].includes(row.type)&&!seen.has(row.targetId)||row.type==='compaction'&&!seen.has(row.firstKeptEntryId))throw Error('Native source history references a missing entry.');seen.add(row.id);
 }
}
function metas(state:string,referenceState=state){const rows=new Map<string,Data>(),directory=join(state,'sessions');if(!present(directory))return rows;
 for(const name of readdirSync(directory).filter(name=>name.endsWith('.meta.json'))){const row=json(join(directory,name)),sid=identifier(row.id);if(name!==sid+'.meta.json'||rows.has(sid)||row.running===true)throw Error('Native source session identity/running state is not settled.');
  if(row.file!==undefined&&(typeof row.file!=='string'||resolve(row.file)!==row.file||dirname(row.file)!==join(referenceState,'sessions',sid)))throw Error('Native source file points outside its own profile.');rows.set(sid,row);
 }if(rows.size>5000)throw Error('Native source catalogue exceeds 5,000 conversations.');return rows;
}
function within(parent:string,child:string){const path=relative(parent,child);return path===''||!path.startsWith('..')&&!isAbsolute(path);}
function copyTree(source:string,target:string,allow:(key:string)=>boolean=()=>true,key=''){
 if(!allow(key))return;
 const s=lstatSync(source);if(s.isDirectory()){if(!present(target))mkdirSync(target,{recursive:true,mode:s.mode&0o777});else if(!lstatSync(target).isDirectory())throw Error('Native transfer path collides with a file.');for(const name of readdirSync(source))copyTree(join(source,name),join(target,name),allow,key?key+'/'+name:name);}
 else if(s.isFile()){if(present(target)){if(!lstatSync(target).isFile()||hash(readFileSync(target))!==hash(readFileSync(source)))throw Error('Native transfer file identity collides with the destination.');}else{mkdirSync(dirname(target),{recursive:true,mode:0o700});cpSync(source,target,{errorOnExist:true,force:false,preserveTimestamps:true});chmodSync(target,s.mode&0o777);}}
 else throw Error('Native transfer refuses linked or unsupported objects.');
}
function validateSource(state:string){
 const known=new Set(['sessions','attachments','observations','harness-drafts','jobs','desktop-runs','dsh-imports','native-relocations','native-imports','native-index','session-exports','harness.json','workspaces.json','session-organization.json','branch-intents.json','branch-publications','compactions.json','prompt-improvements.json','model-account-logins.json','mcp-management.json']);
 for(const name of readdirSync(state))if(!known.has(name))throw Error('Source state component needs an explicit relocation adapter: '+name);
 const desktop=join(state,'desktop-runs');if(present(desktop)&&readdirSync(desktop).length)throw Error('Desktop artifact references need an explicit relocation adapter.');
 const rows=metas(state);if(!rows.size)throw Error('Choose a source with saved Harness conversations.');
 for(const row of rows.values())for(const parent of [row.fork?.sessionId,row.delegation?.parentId].filter(Boolean))if(!rows.has(identifier(parent)))throw Error('Native transfer requires the complete saved parent/child family.');
 const pending=join(state,'branch-intents.json');if(present(pending)){const data=json(pending);if(data.schema!=='augmentor-branch-intents/1'||!Array.isArray(data.pending)||data.pending.length)throw Error('Resolve pending branch creation in the source profile before relocating it.');}
 const publications=join(state,'branch-publications');if(present(publications)&&readdirSync(publications).length)throw Error('Resolve source branch publication before relocating the profile.');
 const jobs=join(state,'jobs');if(present(jobs))for(const name of readdirSync(jobs).filter(name=>name.endsWith('.json'))){const job=json(join(jobs,name));if(!rows.has(job.owner)||job.childId&&!rows.has(job.childId)||!['completed','failed','cancelled','unknown'].includes(job.state))throw Error('Settle source jobs and retain their complete family before relocation.');}
 return rows;
}
export function inspectNativeProfile(state:string){const lease=acquireProfileLease(state,{maintenance:true});try{requireColdState(state);const inventory=stateInventory(state),sessions=validateSource(state);return {schema:'augmentor-native-profile-inspection/1',stateSha256:inventory.sha256,entries:inventory.entries,bytes:inventory.bytes,sessions:[...sessions.values()].map(m=>({sessionId:m.id,title:m.title,cwd:m.cwd,selection:m.selection}))};}finally{lease.close();}}
/** Copy one complete cold native profile into another, with a full verified
 * source archive and a recoverable destination backup. Canonical native bodies,
 * opaque provider state, display/queue/draft bytes and identities remain intact.
 * Only native parent-header paths, metadata and managed request bindings relocate. */
export async function importNativeProfile(sourceState:string,targetState:string,expectedSourceSha256:string){
 if(!isAbsolute(sourceState)||resolve(sourceState)!==sourceState||!isAbsolute(targetState)||resolve(targetState)!==targetState||within(sourceState,targetState)||within(targetState,sourceState))throw Error('Choose distinct canonical, non-nested native profiles.');
 if(!/^[a-f0-9]{64}$/.test(expectedSourceSha256))throw Error('Inspect and choose the exact cold source checksum first.');
 const sourceLease=acquireProfileLease(sourceState,{maintenance:true});
 try{
  requireColdState(sourceState);const before=stateInventory(sourceState);if(before.sha256!==expectedSourceSha256)throw Error('Native source changed since inspection.');const originalMetas=validateSource(sourceState);
  return await stateTransaction(targetState,async stage=>{
   const targetMetas=metas(stage,targetState);if(!present(join(stage,'sessions')))privateDir(join(stage,'sessions'));for(const id of originalMetas.keys())if(targetMetas.has(id)||readdirSync(join(stage,'sessions')).some(name=>name===id||name.startsWith(id+'.')))throw Error('A native conversation ID already exists in the destination; both versions are preserved.');
   if(targetMetas.size+originalMetas.size>5000)throw Error('Combined native catalogue exceeds its bound.');
   const archive=join(stage,'native-imports',before.sha256,'state');if(present(archive))throw Error('This source snapshot is already archived here.');privateDir(archive);cpSync(sourceState,archive,{recursive:true,preserveTimestamps:true,force:false});for(const row of before.rows)chmodSync(row.path?join(archive,...row.path.split('/')):archive,row.mode);
   if(stateInventory(archive).sha256!==before.sha256)throw Error('Native source snapshot changed during capture.');
   const sourceMetas=new Map([...originalMetas].map(([id,m])=>[id,structuredClone(m)])),events=new Map<string,DisplayEvent[]>(),nativeFiles=new Map<string,{sid:string;rows:Data[];bytes:Buffer;end:number}>();
   for(const [sid,m] of sourceMetas){
    const display=lines(join(archive,'sessions',sid+'.events.jsonl')) as DisplayEvent[];let last=0;for(const e of display){if(!Number.isSafeInteger(e.seq)||e.seq<=last||typeof e.type!=='string'||!e.data)throw Error('Native source display sequence is invalid.');last=e.seq;}events.set(sid,display);
    const directory=join(archive,'sessions',sid);if(present(directory))for(const name of readdirSync(directory).filter(name=>name.endsWith('.jsonl'))){const path=join(directory,name),bytes=readFileSync(path),rows=lines(path);nativeTree(rows);nativeFiles.set(join(sourceState,'sessions',sid,name),{sid,rows,bytes,end:bytes.indexOf(10)});}
    if(m.file&&!nativeFiles.has(m.file))throw Error('Native source file is missing.');
   }
   const copied:string[]=[];
   for(const prefix of ['sessions','attachments','observations','harness-drafts','jobs','desktop-runs']){const path=join(archive,prefix);if(present(path)){copyTree(path,join(stage,prefix),key=>{if(!key)return true;const receipt=prefix==='attachments'?/^v1\/([^/]+)\.json$/.exec(key):prefix==='harness-drafts'?/^v1\/(?:records|edit-origins)\/([^/]+)\.json$/.exec(key):null;if(receipt)return sourceMetas.has(receipt[1]);if(prefix==='observations')return sourceMetas.has(key.split('/')[0]);if(prefix==='sessions')return [...sourceMetas.keys()].some(id=>key===id||key.startsWith(id+'/')||key.startsWith(id+'.'));return true;});copied.push(prefix);}}
   const imports=join(archive,'dsh-imports');if(present(imports))for(const name of readdirSync(imports)){if(/^[a-f0-9]{64}\.json$/.test(name)){const source=loadDshProjectArchive(join(imports,name),name.slice(0,-5),undefined,true);copyDshProjectArchive(source,join(stage,'dsh-imports'));}else if(name==='batches')copyTree(join(imports,name),join(stage,'dsh-imports','batches'));}
   const attachments=present(join(archive,'attachments','v1'))?new PiAttachments(archive,(sid,part)=>(events.get(sid)??[]).some(e=>e.type==='user/message'&&e.data.source?.sessionId!==sid&&(e.data.submittedContent??e.data.content??[]).some((p:Data)=>JSON.stringify(p)===JSON.stringify(part))),true):undefined;
   const relocated=[];
   for(const [sid,m] of sourceMetas){
    const rules=new Map<string,RelocationRule>();for(const rule of readRelocationBindings(archive,sid)?.rules??[])rules.set(rule.contentSha256,rule);
    const footers=new Map<string,PromptAttachment[]>();
    for(const e of events.get(sid)??[])if(e.type==='user/message'){
     const refs=promptAttachments((e.data.submittedContent??e.data.content??[]).filter((p:Data)=>p.type==='file'||p.type==='image'&&p.attachment).map((p:Data)=>({type:p.type,attachment:p.attachment})));const files=refs.filter(p=>p.type==='file');
     if(refs.length){if(!attachments)throw Error('Source attachment receipts are missing.');const resolved=await attachments.resolve(sid,'',refs);if(files.length){const oldFooter=resolved.text.replaceAll(join(archive,'attachments','v1'),join(sourceState,'attachments','v1'));footers.set(oldFooter,files);}}
    }
    for(const [oldPath,native] of nativeFiles)if(native.sid===sid){
     for(const row of native.rows.slice(1)){
      const target=row.type==='context_edit'?native.rows.find(r=>r.id===row.targetId):undefined;
      const content=row.type==='message'&&row.message?.role==='user'?row.message.content:row.type==='context_edit'&&target?.type==='message'&&target.message?.role==='user'?row.replacement?.content:undefined;
      if(content!==undefined)for(const [footer,files] of footers){const texts=typeof content==='string'?[content]:Array.isArray(content)?content.filter((p:Data)=>p.type==='text').map((p:Data)=>p.text):[];if(texts.some((text:string)=>text.endsWith(footer)))rules.set(contentDigest(content),{kind:'files',contentSha256:contentDigest(content),footer,files});}
      if(row.type==='custom_message'&&row.customType==='augmentor.dsh-history.v1'&&row.details?.boundary==='end-of-import'){
       const sha=row.details.archiveSha256,known=rules.get(contentDigest(row.content));if(known?.kind==='dsh-archive'&&known.archiveSha256===sha&&typeof row.content==='string'&&row.content.endsWith(known.oldPath))continue;const oldArchive=join(sourceState,'dsh-imports',String(sha)+'.json');if(!/^[a-f0-9]{64}$/.test(sha)||typeof row.content!=='string'||!row.content.endsWith(oldArchive))throw Error('Source DSH archive boundary is not exact.');rules.set(contentDigest(row.content),{kind:'dsh-archive',contentSha256:contentDigest(row.content),oldPath:oldArchive,archiveSha256:sha});
      }
     }
     const header=native.rows[0];if(header.parentSession!==undefined){if(!nativeFiles.has(header.parentSession))throw Error('Native parent header points outside the complete source family.');const rebound={...header,parentSession:join(targetState,relative(sourceState,header.parentSession))},path=join(stage,relative(sourceState,oldPath));writeFileSync(path,Buffer.concat([Buffer.from(JSON.stringify(rebound)+'\n'),native.bytes.subarray(native.end+1)]),{mode:0o600});}
    }
    const bindings=relocationBindings({schema:'augmentor-native-relocation-bindings/1',sourceStateSha256:before.sha256,rules:[...rules.values()]});if(Buffer.byteLength(JSON.stringify(bindings))>1024*1024)throw Error('Relocation bindings exceed their bound.');atomicJson(join(stage,'native-relocations',sid+'.json'),bindings);
    const through=events.get(sid)?.at(-1)?.seq??0;m.importedHistoryThroughSeq=through;if(m.file)m.file=join(targetState,relative(sourceState,m.file));atomicJson(join(stage,'sessions',sid+'.meta.json'),m);relocated.push({sessionId:sid,nativeFiles:[...nativeFiles.values()].filter(r=>r.sid===sid).length,bindings:rules.size,sourceDisplayThroughSeq:through});
   }
   // Configuration/login/MCP controls belong to the destination configuration;
   // conversation-bound compaction and prompt receipts keep their duplicate guards.
   for(const [name,key,version] of [['compactions.json','receipts','augmentor-compactions/1'],['prompt-improvements.json',null,null]] as const){const source=join(archive,name);if(!present(source))continue;const incoming=json(source),existing:any=present(join(stage,name))?json(join(stage,name)):key?{version,receipts:[]}:[];if(key&&(incoming.version!==version||existing.version!==version)||!Array.isArray(key?incoming[key]:incoming)||!Array.isArray(key?existing[key]:existing))throw Error('Source operation receipt format is unsupported.');const a=key?incoming[key]:incoming,b=key?existing[key]:existing,ids=new Set(b.map((r:Data)=>r.requestId));for(const row of a){if(ids.has(row.requestId)||row.sessionId&&!sourceMetas.has(row.sessionId))throw Error('Source operation receipt identity collides or is foreign.');ids.add(row.requestId);}if(key&&a.length+b.length>256)throw Error('Combined compaction receipt catalogue is full.');atomicJson(join(stage,name),key?{version,receipts:[...b,...a]}:[...b,...a]);}
   const targetRegistry=new WorkspaceRegistry(join(stage,'workspaces.json'),()=>[...targetMetas.values()].map(m=>m.cwd)).snapshot(),sourceRegistry=new WorkspaceRegistry(join(archive,'workspaces.json'),()=>[...sourceMetas.values()].map(m=>m.cwd)).snapshot();
   for(const row of sourceRegistry.items)if(!targetRegistry.items.some(x=>x.cwd===row.cwd)){if(targetRegistry.removed.includes(row.cwd))throw Error('The destination explicitly removed a source workspace.');targetRegistry.items.push(row);}targetRegistry.revision++;atomicJson(join(stage,'workspaces.json'),targetRegistry);new WorkspaceRegistry(join(stage,'workspaces.json'),()=>[]).snapshot();
   const membership=new SessionOrganization(join(stage,'session-organization.json')).snapshot(),sourceMembership=new SessionOrganization(join(archive,'session-organization.json')).snapshot();for(const key of ['pinnedSessionIds','archivedSessionIds'] as const){if(sourceMembership[key].some(id=>!sourceMetas.has(id)))throw Error('Source organization references an absent conversation.');membership[key].push(...sourceMembership[key]);}membership.revision++;atomicJson(join(stage,'session-organization.json'),membership);new SessionOrganization(join(stage,'session-organization.json')).snapshot();
   if(stateInventory(sourceState).sha256!==before.sha256)throw Error('Native source changed before adoption.');
   const receipt={schema:'augmentor-native-profile-import/1',sourceStateSha256:before.sha256,sourceArchive:'native-imports/'+before.sha256+'/state',relocated,copiedOperationalTrees:copied,existingDestinationConversationsPreserved:targetMetas.size,configurationCopied:false,memoryBanksMerged:false,oldHistoryCapturedAsNewMemory:false,modelWorkSubmitted:false};atomicJson(join(stage,'native-imports',before.sha256,'receipt.json'),receipt);return receipt;
  });
 }finally{sourceLease.close();}
}
