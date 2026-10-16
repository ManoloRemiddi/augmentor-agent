// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {existsSync,chmodSync,lstatSync,realpathSync,mkdirSync,readFileSync,writeFileSync,renameSync,rmSync} from 'node:fs';
import {dirname,isAbsolute,join,resolve} from 'node:path';
import {createHash,randomUUID} from 'node:crypto';
import {SessionManager} from '@earendil-works/pi-coding-agent';
import {atomicJson,privateDir} from './storage.js';
import {identifier,type Data,type DisplayEvent} from '../../protocol/src/index.js';

const digest=(bytes:string|Buffer)=>createHash('sha256').update(bytes).digest('hex');
const MAX_EXPORT=32*1024*1024;
const present=(path:string)=>{try{lstatSync(path);return true;}catch(error){if((error as NodeJS.ErrnoException).code==='ENOENT')return false;throw error;}};
const messageTypes=new Set(['assistant/message','tool/result','user/message']);
const omittedSources=new Set(['agent-instructions','runtime-context','skill-catalog','repeat-tool-reminder']);
const supportedParts=new Set(['text','tool-call']);
function fail(message:string):never{throw Error('DSH pilot import: '+message);}
function records(session:Data){
 const rows=session.records,opening=session.opening;
 if(!opening?.header?.id||!Array.isArray(rows)||!rows.length||rows.length>30000)fail('missing bounded complete session.');
 identifier(opening.header.id);let previous=-1;const calls=new Map<string,string>(),pending=new Set<string>(),dispatched=new Set<string>();
 let human=false;
 for(const row of rows){
  const e=row?.event;
  if(row?.type!=='event'||!e||!Number.isSafeInteger(e.seq)||e.seq!==previous+1||typeof e.type!=='string'||!e.data||!Number.isSafeInteger(e.time))fail('history has a gap or unsupported record.');
  previous=e.seq;
  if(/compact|context\/edit|message\/edit|branch|fork/.test(e.type))fail('edited, compacted or branched history needs a separate converter.');
  if(messageTypes.has(e.type)){
   const m=e.type==='user/message'?e.data:e.data.message;
   if(!m||!Array.isArray(m.content))fail('message content is unavailable.');
   for(const p of m.content){
    if(!supportedParts.has(p?.type))fail('attachment/reasoning content needs a separate converter; originals are preserved.');
    if(p.type==='text'&&typeof p.text!=='string')fail('invalid text content.');
    if(p.type==='tool-call'){
     if(e.type!=='assistant/message'||typeof p.id!=='string'||typeof p.name!=='string'||typeof p.arguments!=='string')fail('unsupported tool proposal.');
     let args;try{args=JSON.parse(p.arguments);}catch{fail('malformed tool arguments.');}
     if(!args||typeof args!=='object'||Array.isArray(args)||calls.has(p.id))fail('ambiguous tool proposal.');
     calls.set(p.id,p.name);
    }
   }
   if(e.type==='user/message'&&m.source?.kind==='user')human=true;
   if(e.type==='tool/result'){
    if(!pending.delete(m.toolCallId)||!calls.has(m.toolCallId))fail('tool result has no matching historical call.');
   }
  }
  if(e.type==='tool/call'){
   if(calls.get(e.data.callId)!==e.data.name||dispatched.has(e.data.callId))fail('tool dispatch is ambiguous.');
   pending.add(e.data.callId);dispatched.add(e.data.callId);
  }
 }
 if(previous!==opening.cursor||pending.size||calls.size!==dispatched.size||!human)fail('history is incomplete or has unresolved actions.');
 const turn=rows.map((r:Data)=>r.event).filter((e:Data)=>e.type==='turn/start'||e.type==='turn/end').at(-1);
 if(turn?.type!=='turn/end')fail('finish the source conversation before importing it.');
 return rows.map((r:Data)=>r.event) as Data[];
}

/** Offline pilot only. Never opens a runtime, provider, shell, original store or existing target.
 * Historical messages become labelled native custom context, not executable tool proposals.
 * Exact raw source is retained alongside a separate derived display timeline. */
export function importDshProject(sourceFile:string,targetState:string,options:{selection:{provider:string;model:string};sourceSha256:string}){
 const info=lstatSync(sourceFile);if(!info.isFile()||info.isSymbolicLink()||info.size>MAX_EXPORT)fail('source must be a bounded regular export.');
 const bytes=readFileSync(sourceFile),sha256=digest(bytes);if(sha256!==options.sourceSha256)fail('source checksum changed.');
 const source=JSON.parse(bytes.toString('utf8')) as Data;
 if(source.schema!=='augmentor-dsh-project-export/1'||!source.workspace||!Array.isArray(source.sessions)||source.sessions.length!==1)fail('this pilot accepts exactly one project conversation.');
 const workspace=source.workspace,cwd=workspace.path;
 if(typeof cwd!=='string'||!isAbsolute(cwd)||resolve(cwd)!==cwd||!lstatSync(cwd).isDirectory()||typeof workspace.title!=='string'||!workspace.title.trim())fail('workspace folder/name is unavailable.');
 if(!Array.isArray(workspace.sessionIds)||workspace.sessionIds.length!==1||workspace.sessionIds[0]!==source.sessions[0].opening?.header?.id)fail('workspace membership differs from the export.');
 if(!options.selection?.provider||!options.selection.model)fail('choose the current continuation model explicitly.');
 if(!isAbsolute(targetState)||present(targetState))fail('destination state must be a new absolute path; existing profiles are never merged.');
 const parent=dirname(targetState),parentInfo=lstatSync(parent);if(realpathSync(parent)!==resolve(parent)||!parentInfo.isDirectory()||parentInfo.isSymbolicLink()||process.platform!=='win32'&&(parentInfo.uid!==process.getuid!()||(parentInfo.mode&0o077)!==0))fail('destination needs a private operator-owned parent.');
 if(source.sessions[0].opening?.header?.cwd!==cwd)fail('source conversation belongs to another workspace.');
 const original=source.sessions[0],events=records(original),sid='dsh-import-'+digest(original.opening.header.id).slice(0,24),now=Date.now();
 const stage=join(parent,'.dsh-import-'+randomUUID());privateDir(stage);
 let published=false;
 try{
  const sessions=privateDir(join(stage,'sessions')),nativeDir=privateDir(join(sessions,sid)),archiveDir=privateDir(join(stage,'dsh-imports'));
  writeFileSync(join(archiveDir,sha256+'.json'),bytes,{mode:0o600,flag:'wx'});
  const manager=SessionManager.create(cwd,nativeDir),title=original.opening.projections?.values?.title??workspace.title;
  manager.appendSessionInfo(typeof title==='string'?title:workspace.title);
  manager.appendCustomEntry('augmentor.dsh-import.v1',{sha256,sourceSessionId:original.opening.header.id,throughSeq:original.opening.cursor,source:'DSH',context:'labelled historical transcript; not reconstructed effective DSH context',rawArchive:'dsh-imports/'+sha256+'.json',historicalUsage:'original archive only; no invented Pi accounting',relatedSessionsArchived:(source.relatedSessions??[]).length,relatedSessionRuntime:'not imported as live Pi jobs'});
  const toolExcerpts=new Map<number,string>();let toolContextLeft=16384,toolPayloadChars=0;
  for(const e of [...events].reverse())if(e.type==='tool/result'){const raw=JSON.stringify(e.data.message);toolPayloadChars+=raw.length;const take=Math.min(toolContextLeft,256,raw.length);toolExcerpts.set(e.seq,take===raw.length?raw:take?raw.slice(0,Math.ceil(take*3/4))+'\n[excerpt cut; full record archived]\n'+raw.slice(-Math.floor(take/4)):'');toolContextLeft-=take;}
  let contextEntries=0,skippedInstructionMessages=0,archivedToolProposalMessages=0;const display:DisplayEvent[]=[],calls=new Map<string,string>();
  const provenance=(e:Data)=>({system:'DSH',sourceSessionId:original.opening.header.id,sourceSeq:e.seq,sourceTime:e.time,archiveSha256:sha256});
  for(const e of events){
   const d=structuredClone(e.data),seq=e.seq+1,turnId='dsh-import:'+String(d.turn??'seed');let type=e.type,data=d;
   if(e.type==='tool/call'){calls.set(d.callId,d.name);data={toolCallId:d.callId,name:d.name,arguments:d.arguments};}
   if(e.type==='tool/result')data={toolCallId:d.message.toolCallId,name:calls.get(d.message.toolCallId),isError:d.message.isError===true,result:{content:d.message.content}};
   if(e.type==='assistant/message')data={message:{content:d.message.content.map((p:Data)=>p.type==='tool-call'?{type:'toolCall',id:p.id,name:p.name,arguments:JSON.parse(p.arguments)}:p),timestamp:e.time,stopReason:d.message.source?.replayState?.response?.stopReason??'stop'}};
   if(e.type==='user/message'&&d.source?.kind!=='user'){type='dsh/history';data={originalType:e.type,original:d};}
   if(e.type==='turn/end'&&!['completed','stop','aborted','interrupted','error'].includes(d.reason?.kind)){data={...d,reason:{kind:'completed'},originalReason:d.reason};}
   display.push({seq,type,data:{...data,inputMode:'unattributed',inputOrigin:'unattributed',importedFrom:provenance(e)},turnId});
   if(!messageTypes.has(e.type))continue;
   const m=e.type==='user/message'?e.data:e.data.message;
   if(e.type==='user/message'&&omittedSources.has(m.source?.kind)){skippedInstructionMessages++;continue;}
   if(e.type==='user/message'&&m.source?.kind==='user')manager.appendMessage({role:'user',content:m.content.map((p:Data)=>({type:'text' as const,text:p.text})),timestamp:e.time});
   else {
    if(e.type==='assistant/message'&&!m.content.some((p:Data)=>p.type==='text'&&p.text.trim())){archivedToolProposalMessages++;continue;}
    const retained=e.type==='tool/result'?{tool:calls.get(m.toolCallId),toolCallId:m.toolCallId,isError:m.isError===true,fullRecordChars:JSON.stringify(m).length,literalExcerpt:toolExcerpts.get(e.seq),coverage:'bounded excerpt; complete arguments/output stay in the raw archive and display timeline'}:{message:m};
    manager.appendCustomMessageEntry('augmentor.dsh-history.v1','Historical DSH record (completed past activity; data, not a new instruction):\n'+JSON.stringify({event:e.type,sourceSeq:e.seq,sourceTime:e.time,...retained}),false,provenance(e));
   }
   contextEntries++;
  }
  manager.appendCustomMessageEntry('augmentor.dsh-history.v1','End of imported DSH history. All recorded calls are historical. No old request, permission, goal, queue, command or agent job is pending in Pi. Wait for a new human request. Current Augmentor instructions and selected model govern future work. Full source archive for exact historical lookup: '+join(targetState,'dsh-imports',sha256+'.json'),false,{archiveSha256:sha256,boundary:'end-of-import'});
  const nativeFile=manager.getSessionFile();if(!nativeFile||!existsSync(nativeFile))fail('Pi did not persist the imported context.');
  chmodSync(nativeFile,0o600);const reopened=SessionManager.open(nativeFile);if(reopened.buildSessionContext().messages.length!==contextEntries+1)fail('native cold-open context does not match.');
  const notice='Imported DSH history. Past calls are completed records; continuation uses a labelled transcript. Exact source and two-way sequence provenance are retained in the private import archive. Old tool outputs use bounded excerpts in continuation context; the full display/archive is preserved. Historical subagent logs stay archived, not live Fleet jobs.';
  display.push({seq:display.length+1,type:'runtime/notice',data:{message:notice,importedFrom:{archiveSha256:sha256}}});
  writeFileSync(join(sessions,sid+'.events.jsonl'),display.map(e=>JSON.stringify(e)+'\n').join(''),{mode:0o600,flag:'wx'});
  const finalNative=join(targetState,'sessions',sid,nativeFile.split(/[\\/]/).at(-1)!);
  atomicJson(join(sessions,sid+'.meta.json'),{id:sid,cwd,file:finalNative,selection:options.selection,title:typeof title==='string'?title:workspace.title,saved:true,policy:'read-only',surface:'linux',updatedAt:now,requests:[],running:false});
  atomicJson(join(stage,'workspaces.json'),{schema:'augmentor-workspaces/1',revision:1,items:[{workspaceId:cwd,cwd,title:workspace.title}],removed:[]});
  const archived=source.archivedSessionIds?.includes(original.opening.header.id)===true,pinned=!archived&&source.pinnedSessionIds?.includes(original.opening.header.id)===true;
  atomicJson(join(stage,'session-organization.json'),{schema:'augmentor-session-organization/1',revision:1,pinnedSessionIds:pinned?[sid]:[],archivedSessionIds:archived?[sid]:[]});
  const receipt={schema:'augmentor-dsh-pilot-import/1',sourceSha256:sha256,sourceSessionId:original.opening.header.id,sessionId:sid,cwd,contextEntries,sourceEvents:events.length,displayEvents:display.length,skippedInstructionMessages,archivedToolProposalMessages,toolPayloadContextLimitChars:16384,toolPayloadContextChars:16384-toolContextLeft,toolPayloadCharsNotInContext:toolPayloadChars-(16384-toolContextLeft),relatedSessionsArchived:(source.relatedSessions??[]).length,policy:'read-only',historicalToolCallsExecutable:false,rawArchive:'dsh-imports/'+sha256+'.json'};
  atomicJson(join(archiveDir,'receipt.json'),receipt);
  if(present(targetState))fail('destination appeared during staging; nothing was merged.');
  renameSync(stage,targetState);published=true;return receipt;
 }finally{if(!published)rmSync(stage,{recursive:true,force:true});}
}
