// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {existsSync,chmodSync,lstatSync,realpathSync,mkdirSync,readFileSync,writeFileSync,renameSync,rmSync} from 'node:fs';
import {dirname,isAbsolute,join,resolve} from 'node:path';
import {createHash,randomUUID} from 'node:crypto';
import {dshHistorySurface,type DshSurface} from './dsh-history-surface.js';
import {SessionManager} from '@earendil-works/pi-coding-agent';
import {PiAttachments,promptAttachments,IMAGE_LIMITS} from './attachments.js';
import {DSH_MEDIA_TYPE,DSH_MEDIA_SCHEMA} from './dsh-history-media.js';
import {atomicJson,privateDir} from './storage.js';
import {identifier,type Data,type DisplayEvent} from '../../protocol/src/index.js';

const digest=(bytes:string|Buffer)=>createHash('sha256').update(bytes).digest('hex');
const MAX_EXPORT=32*1024*1024;
const present=(path:string)=>{try{lstatSync(path);return true;}catch(error){if((error as NodeJS.ErrnoException).code==='ENOENT')return false;throw error;}};
const messageTypes=new Set(['assistant/message','tool/result','user/message']);
const omittedSources=new Set(['agent-instructions','runtime-context','skill-catalog','repeat-tool-reminder']);
const supportedParts=new Set(['text','reasoning','image','tool-call']);
function fail(message:string):never{throw Error('DSH pilot import: '+message);}
function checkedContent(content:Data[]):Data[]{
 return content.map(p=>{
  if(['text','reasoning'].includes(p?.type))return {type:p.type,text:p.text};
  if(p?.type==='tool-call')return {type:p.type,id:p.id,name:p.name,arguments:p.arguments};
  if(p?.type!=='image')fail('unsupported historical content.');
  const a=p.attachment;
  promptAttachments([p]);
  if(a.originalAttachmentId!==undefined||Object.keys(a).some(key=>!['attachmentId','bytes','mediaType','width','height','name','originalDimensions'].includes(key)))fail('unsupported image attachment metadata.');
  if(p.offloaded!==undefined&&p.offloaded!==true)fail('invalid image offload marker.');
  if(a.bytes>IMAGE_LIMITS.maxImageBytes||a.width*a.height>IMAGE_LIMITS.maxImagePixels)fail('image attachment exceeds its admission bounds.');
  const dimensions=a.originalDimensions;
  if(dimensions!==undefined&&(!dimensions||![dimensions.width,dimensions.height].every(n=>Number.isSafeInteger(n)&&n>0&&n<=32768)))fail('invalid original image dimensions.');
  return {type:'image',attachment:{attachmentId:a.attachmentId,mediaType:a.mediaType,bytes:a.bytes,width:a.width,height:a.height,...(a.name===undefined?{}:{name:a.name}),...(dimensions?{originalDimensions:{width:dimensions.width,height:dimensions.height}}:{})},...(p.offloaded?{offloaded:true}:{})};
 });
}
function records(session:Data){
 const rows=session.records,opening=session.opening;
 if(!opening?.header?.id||!Array.isArray(rows)||!rows.length||rows.length>30000)fail('missing bounded complete session.');
 identifier(opening.header.id);
 if(opening.header.version!==undefined&&opening.header.version!==4)fail('unsupported source session format version.');
 if(opening.header.isSeeded!==undefined&&typeof opening.header.isSeeded!=='boolean')fail('invalid source lineage marker.');
 let previous=-1;const calls=new Map<string,string>(),pending=new Set<string>(),dispatched=new Set<string>();
 let human=false;const effective:Data[]=[],bySeq=new Map<number,Data>();
 for(const row of rows){
  const e=structuredClone(row?.event);
  if(row?.type!=='event'||!e||!Number.isSafeInteger(e.seq)||e.seq!==previous+1||typeof e.type!=='string'||!e.data||!Number.isSafeInteger(e.time))fail('history has a gap or unsupported record.');
  previous=e.seq;
  if(/compact|context\/edit|message\/edit|branch|fork/.test(e.type)&&!['compaction/start','compaction/summary','compaction/prune','compaction/end'].includes(e.type))fail('edited, compacted or branched history needs a separate converter.');
  if(messageTypes.has(e.type)){
   const m=e.type==='user/message'?e.data:e.data.message;
   if(!m||!Array.isArray(m.content))fail('message content is unavailable.');
   for(const p of m.content){
    if(!supportedParts.has(p?.type))fail('attachment/reasoning content needs a separate converter; originals are preserved.');
    if(['text','reasoning'].includes(p.type)&&typeof p.text!=='string')fail('invalid text/reasoning content.');
    if(p.type==='reasoning'&&e.type!=='assistant/message')fail('reasoning is only supported on historical assistant messages.');
    if(p.type==='tool-call'){
     if(e.type!=='assistant/message'||typeof p.id!=='string'||typeof p.name!=='string'||typeof p.arguments!=='string')fail('unsupported tool proposal.');
     let args;try{args=JSON.parse(p.arguments);}catch{fail('malformed tool arguments.');}
     if(!args||typeof args!=='object'||Array.isArray(args)||calls.has(p.id))fail('ambiguous tool proposal.');
     calls.set(p.id,p.name);
    }
   }
   m.content=checkedContent(m.content);
   if(e.type==='user/message'&&m.source?.kind==='user')human=true;
   if(e.type==='tool/result'){
    if((e.surfaceOp?.op!=='replace'&&!pending.delete(m.toolCallId))||!calls.has(m.toolCallId))fail('tool result has no matching historical call.');
   }
  }
  if(e.type==='image/offload'){
   const targets=e.data.targets;
   if(Object.keys(e.data).length!==1||!Array.isArray(targets)||!targets.length)fail('invalid image offload event.');
   const seen=new Set<number>();
   for(const target of targets){
    if(!target||Object.keys(target).sort().join(',')!=='imageIndexes,seq'||!Number.isSafeInteger(target.seq)||seen.has(target.seq)||!Array.isArray(target.imageIndexes)||!target.imageIndexes.length)fail('invalid image offload target.');
    seen.add(target.seq);const original=bySeq.get(target.seq);
    if(!original||!['user/message','tool/result'].includes(original.type))fail('image offload target is unavailable.');
    const images=(original.type==='user/message'?original.data:original.data.message).content.filter((p:Data)=>p.type==='image');let before=-1;
    for(const index of target.imageIndexes){if(!Number.isSafeInteger(index)||index<=before||!images[index]||images[index].offloaded)fail('image offload index is invalid or repeated.');before=index;images[index].offloaded=true;}
   }
  }
  effective.push(e);bySeq.set(e.seq,e);
  if(e.type==='tool/call'){
   if(calls.get(e.data.callId)!==e.data.name||dispatched.has(e.data.callId))fail('tool dispatch is ambiguous.');
   pending.add(e.data.callId);dispatched.add(e.data.callId);
  }
 }
 if(previous!==opening.cursor||pending.size||calls.size!==dispatched.size||!human)fail('history is incomplete or has unresolved actions.');
 const turn=rows.map((r:Data)=>r.event).filter((e:Data)=>e.type==='turn/start'||e.type==='turn/end').at(-1);
 if(turn?.type!=='turn/end')fail('finish the source conversation before importing it.');
 const surface=dshHistorySurface(effective,opening.header.version===4);
 const parent=opening.header.parentSession;if(parent!==undefined){identifier(parent);if(parent===opening.header.id)fail('source lineage cannot name itself.');}
 if(opening.header.isSeeded===true&&!surface.seedCuts.length)fail('seeded source is missing its inherited boundary.');
 return {events:effective,surface};
}

type ModelSelection={provider:string;model:string};
export type ImportOptions={selection:ModelSelection;sessionSelections?:Record<string,ModelSelection>;sourceSha256:string};
const MAX_PROJECT_SESSIONS=128;
function checkedSelection(value:unknown):ModelSelection{
 const row=value as ModelSelection;
 if(!row||typeof row!=='object'||Array.isArray(row)||Object.keys(row).some(key=>!['provider','model'].includes(key))||typeof row.provider!=='string'||!row.provider.trim()||typeof row.model!=='string'||!row.model.trim())fail('choose the current continuation model explicitly.');
 return {provider:row.provider,model:row.model};
}
/** One native conversation; historical calls never become executable Pi proposals. */
function writeSession(original:Data,events:Data[],surface:DshSurface,stage:string,targetState:string,source:Data,selection:ModelSelection,sha256:string,now:number){
 const workspace=source.workspace,cwd=workspace.path,sid='dsh-import-'+digest(original.opening.header.id).slice(0,24);
 const sessions=privateDir(join(stage,'sessions')),nativeDir=privateDir(join(sessions,sid));
  const manager=SessionManager.create(cwd,nativeDir),title=original.opening.projections?.values?.title??workspace.title;
  manager.appendSessionInfo(typeof title==='string'?title:workspace.title);
  manager.appendCustomEntry('augmentor.dsh-import.v1',{sha256,sourceSessionId:original.opening.header.id,throughSeq:original.opening.cursor,source:'DSH',context:'labelled historical transcript; not reconstructed effective DSH context',rawArchive:'dsh-imports/'+sha256+'.json',historicalUsage:'original archive only; no invented Pi accounting',relatedSessionsArchived:(source.relatedSessions??[]).length,relatedSessionRuntime:'not imported as live Pi jobs'});
  const contextEvents=surface.nodes.map(seq=>events[seq]),activeSeqs=new Set(surface.nodes),replacements=new Map(surface.replacements.map(row=>[row.seq,row]));
  const sourceLineage={parentSession:original.opening.header.parentSession??null,isSeeded:original.opening.header.isSeeded??null,seedCuts:surface.seedCuts};
  manager.appendCustomEntry('augmentor.dsh-surface.v1',{...surface,sourceLineage,contextPolicy:'source message membership/order; current Augmentor instructions; bounded historical tool excerpts; no provider replay'});
  const toolExcerpts=new Map<number,string>();let toolContextLeft=16384,toolPayloadChars=0;
  for(const e of [...contextEvents].reverse())if(e.type==='tool/result'){const m=e.data.message,raw=JSON.stringify({role:m.role,toolCallId:m.toolCallId,isError:m.isError===true,content:m.content});toolPayloadChars+=raw.length;const take=Math.min(toolContextLeft,256,raw.length);toolExcerpts.set(e.seq,take===raw.length?raw:take?raw.slice(0,Math.ceil(take*3/4))+'\n[excerpt cut; full record archived]\n'+raw.slice(-Math.floor(take/4)):'');toolContextLeft-=take;}
  let contextEntries=0,skippedInstructionMessages=0,archivedToolProposalMessages=0;const display:DisplayEvent[]=[],calls=new Map<string,string>();
  const provenance=(e:Data)=>({system:'DSH',sourceSessionId:original.opening.header.id,sourceSeq:e.seq,sourceTime:e.time,archiveSha256:sha256,...(e.surfaceOp===undefined?{}:{sourceSurfaceOp:e.surfaceOp}),...(e.sourceEventSeqs===undefined?{}:{sourceEventSeqs:e.sourceEventSeqs})});
  for(const e of events){
   const d=structuredClone(e.data),seq=e.seq+1,turnId='dsh-import:'+String(d.turn??'seed');let type=e.type,data=d;
   if(e.type==='tool/call'){calls.set(d.callId,d.name);data={toolCallId:d.callId,name:d.name,arguments:d.arguments};}
   if(e.type==='tool/result')data={toolCallId:d.message.toolCallId,name:calls.get(d.message.toolCallId),isError:d.message.isError===true,result:{content:d.message.content}};
   if(e.type==='assistant/message')data={message:{content:d.message.content.map((p:Data)=>p.type==='tool-call'?{type:'toolCall',id:p.id,name:p.name,arguments:JSON.parse(p.arguments)}:p),timestamp:e.time,stopReason:d.message.source?.replayState?.response?.stopReason??'stop'}};
   if(e.type==='user/message'&&d.source?.kind!=='user'){type='dsh/history';data={originalType:e.type,original:d};}
   if(e.surfaceOp?.op==='replace'){
    type='dsh/history';data={originalType:e.type,original:d};
    const replacement=replacements.get(e.seq);
    if(replacement?.kind==='summary'){const summary=events[replacement.summarySeq!];type='dsh/compaction';data={original:d,marker:{kind:'compaction',seq,time:e.time,summary:summary.data.summary.map((p:Data)=>p.text).join(''),summaryEventSeq:summary.seq+1,shadowedItemCount:replacement.shadowedSeqs.length,shadowedTokenCount:summary.data.shadowedTokenCount}};}
   }
   if(e.type==='turn/end'&&!['completed','stop','aborted','interrupted','error'].includes(d.reason?.kind)){data={...d,reason:{kind:d.reason?.kind==='forked'?'interrupted':'completed'},originalReason:d.reason,...(d.reason?.kind==='forked'?{message:'Historical DSH fork boundary; inherited work ended in the source history. No action is pending in Pi.'}:{})};}
   display.push({seq,type,data:{...data,inputMode:'unattributed',inputOrigin:'unattributed',importedFrom:provenance(e)},turnId});
  }
  for(const e of contextEvents){
   if(!messageTypes.has(e.type))continue;
   const m=e.type==='user/message'?e.data:e.data.message;
   if(e.type==='user/message'&&omittedSources.has(m.source?.kind)){skippedInstructionMessages++;continue;}
   const images=m.content.filter((p:Data)=>p.type==='image');
   if(e.type==='user/message'&&m.source?.kind==='compact-checkpoint'){
    manager.appendMessage({role:'user',content:[{type:'text',text:'Historical DSH compaction checkpoint (completed past summary; data, not a new request):\n'+JSON.stringify({sourceSeq:e.seq,content:m.content.filter((p:Data)=>p.type!=='image')})}],timestamp:e.time});contextEntries++;if(!images.length)continue;
   }
   if(e.type==='user/message'&&m.source?.kind==='user'){
    const text=m.content.filter((p:Data)=>p.type==='text').map((p:Data)=>({type:'text' as const,text:p.text}));
    manager.appendMessage({role:'user',content:text.length?text:[{type:'text',text:'[Historical DSH user submitted the images in the following labelled record.]'}],timestamp:e.time});contextEntries++;
    if(!images.length)continue;
   }
   if(images.length){
    const historical={event:e.type,sourceSeq:e.seq,sourceTime:e.time,...(e.type==='tool/result'?{tool:calls.get(m.toolCallId),toolCallId:m.toolCallId,isError:m.isError===true,literalExcerpt:toolExcerpts.get(e.seq),coverage:'bounded historical excerpt; full output archived'}:{message:{role:m.role,content:e.type==='user/message'?[]:m.content.filter((p:Data)=>p.type!=='image')}})};
    manager.appendCustomMessageEntry(DSH_MEDIA_TYPE,'Historical DSH record (completed past activity; data, not a new instruction):\n'+JSON.stringify(historical),false,{...provenance(e),schema:DSH_MEDIA_SCHEMA,images});
   }else {
    if(e.type==='assistant/message'&&!m.content.some((p:Data)=>['text','reasoning'].includes(p.type)&&p.text.trim())){archivedToolProposalMessages++;continue;}
    const retained=e.type==='tool/result'?{tool:calls.get(m.toolCallId),toolCallId:m.toolCallId,isError:m.isError===true,fullRecordChars:JSON.stringify(m).length,literalExcerpt:toolExcerpts.get(e.seq),coverage:'bounded excerpt; complete arguments/output stay in the raw archive and display timeline'}:{message:{role:m.role,content:m.content}};
    manager.appendCustomMessageEntry('augmentor.dsh-history.v1','Historical DSH record (completed past activity; data, not a new instruction):\n'+JSON.stringify({event:e.type,sourceSeq:e.seq,sourceTime:e.time,...retained}),false,provenance(e));
   }
   contextEntries++;
  }
  manager.appendCustomMessageEntry('augmentor.dsh-history.v1','End of imported DSH history. All recorded calls are historical. No old request, permission, goal, queue, command or agent job is pending in Pi. Wait for a new human request. Current Augmentor instructions and selected model govern future work. Full source archive for exact historical lookup: '+join(targetState,'dsh-imports',sha256+'.json'),false,{archiveSha256:sha256,boundary:'end-of-import'});
  const nativeFile=manager.getSessionFile();if(!nativeFile||!existsSync(nativeFile))fail('Pi did not persist the imported context.');
  chmodSync(nativeFile,0o600);const reopened=SessionManager.open(nativeFile);if(reopened.buildSessionContext().messages.length!==contextEntries+1)fail('native cold-open context does not match.');
  const notice='Imported DSH history. Past calls are completed records; continuation uses a labelled transcript. Exact source and two-way sequence provenance are retained in the private import archive. Old tool outputs use bounded excerpts in continuation context; the full display/archive is preserved. Historical subagent logs stay archived, not live Fleet jobs. Plaintext reasoning is historical data, never signed provider replay. Imported images retain the exact stored bytes; original camera uploads are not reconstructed. Source replacements determine continuation context; original append-only records stay inspectable.';
  display.push({seq:display.length+1,type:'runtime/notice',data:{message:notice,importedFrom:{archiveSha256:sha256}}});
  writeFileSync(join(sessions,sid+'.events.jsonl'),display.map(e=>JSON.stringify(e)+'\n').join(''),{mode:0o600,flag:'wx'});
  const finalNative=join(targetState,'sessions',sid,nativeFile.split(/[\\/]/).at(-1)!);
  atomicJson(join(sessions,sid+'.meta.json'),{id:sid,cwd,file:finalNative,selection,title:typeof title==='string'?title:workspace.title,saved:true,policy:'read-only',surface:'linux',updatedAt:now,requests:[],running:false});
  const receipt={schema:'augmentor-dsh-pilot-import/1',sourceSha256:sha256,sourceSessionId:original.opening.header.id,sessionId:sid,selection,cwd,contextEntries,sourceEvents:events.length,effectiveSourceSeqs:surface.nodes,sourceReplacements:surface.replacements.length,shadowedSourceMessages:events.filter(e=>messageTypes.has(e.type)&&!activeSeqs.has(e.seq)).length,sourceLineage,displayEvents:display.length,skippedInstructionMessages,archivedToolProposalMessages,toolPayloadCoverage:'effective source tool results only; shadowed originals remain archived',toolPayloadContextLimitChars:16384,toolPayloadContextChars:16384-toolContextLeft,toolPayloadCharsNotInContext:toolPayloadChars-(16384-toolContextLeft),relatedSessionsArchived:(source.relatedSessions??[]).length,policy:'read-only',historicalToolCallsExecutable:false,rawArchive:'dsh-imports/'+sha256+'.json'};
 return receipt;
}

/** Offline project import. Never opens a runtime/provider or modifies an existing target.
 * All parents validate before staging; the whole project is published by one rename.
 * The single-conversation receipt stays compatible with the earlier pilot. */
/** Prepare a bounded export without touching a destination or model. */
export function prepareDshProject(sourceFile:string,options:ImportOptions){
 const info=lstatSync(sourceFile);if(!info.isFile()||info.isSymbolicLink()||info.size>MAX_EXPORT)fail('source must be a bounded regular export.');
 const bytes=readFileSync(sourceFile),sha256=digest(bytes);if(sha256!==options.sourceSha256)fail('source checksum changed.');
 const source=JSON.parse(bytes.toString('utf8')) as Data;
 if(source.schema!=='augmentor-dsh-project-export/1'||!source.workspace||!Array.isArray(source.sessions)||source.sessions.length>MAX_PROJECT_SESSIONS)fail('choose a project with at most 128 conversations.');
 const workspace=source.workspace,cwd=workspace.path;
 if(typeof cwd!=='string'||!isAbsolute(cwd)||resolve(cwd)!==cwd||!lstatSync(cwd).isDirectory()||typeof workspace.title!=='string'||!workspace.title.trim())fail('workspace folder/name is unavailable.');
 const ids=workspace.sessionIds;
 if(!Array.isArray(ids)||ids.length!==source.sessions.length||new Set(ids).size!==ids.length||ids.some(id=>typeof id!=='string'))fail('workspace membership differs from the export.');
 const byId=new Map<string,Data>();
 for(const session of source.sessions){const id=session?.opening?.header?.id;if(typeof id!=='string'||!ids.includes(id)||byId.has(id))fail('workspace membership differs from the export.');byId.set(id,session);}
 const fallback=checkedSelection(options.selection),selected=new Map<string,ModelSelection>();
 if(options.sessionSelections!==undefined){
  if(!options.sessionSelections||typeof options.sessionSelections!=='object'||Array.isArray(options.sessionSelections))fail('session model choices must be keyed by source conversation.');
  for(const [id,value] of Object.entries(options.sessionSelections)){if(!byId.has(id))fail('session model choice belongs to another project.');selected.set(id,checkedSelection(value));}
 }
 const prepared=ids.map(id=>{const original=byId.get(id)!;if(original.opening.header.cwd!==cwd)fail('source conversation belongs to another workspace.');return {original,...records(original)};});
 const organization=(key:string)=>{const value=source[key]??[];if(!Array.isArray(value)||new Set(value).size!==value.length||value.some(id=>typeof id!=='string'||!byId.has(id)))fail('session organization differs from project membership.');return new Set<string>(value);};
 const archived=organization('archivedSessionIds'),pinned=organization('pinnedSessionIds');
 if(source.relatedSessions!==undefined&&(!Array.isArray(source.relatedSessions)||source.relatedSessions.length>32))fail('related-session archive exceeds its project bound.');
 const attachmentRows=source.attachments??[];
 if(!Array.isArray(attachmentRows)||attachmentRows.length>10000)fail('invalid image attachment bundle.');
 const blobs=new Map<string,Buffer>();
 for(const row of attachmentRows){
  if(!row||Object.keys(row).sort().join(',')!=='attachmentId,bytes,data'||!/^sha256:[a-f0-9]{64}$/.test(row.attachmentId)||blobs.has(row.attachmentId)||!Number.isSafeInteger(row.bytes)||row.bytes<1||row.bytes>IMAGE_LIMITS.maxImageBytes||typeof row.data!=='string'||row.data.length>Math.ceil(IMAGE_LIMITS.maxImageBytes/3)*4)fail('invalid image attachment bundle entry.');
  const data=Buffer.from(row.data,'base64');
  if(data.toString('base64')!==row.data||data.length!==row.bytes||'sha256:'+digest(data)!==row.attachmentId)fail('image attachment checksum or encoding differs.');
  blobs.set(row.attachmentId,data);
 }
 const used=new Set<string>();
 for(const {events} of prepared)for(const e of events)if(messageTypes.has(e.type))for(const p of (e.type==='user/message'?e.data:e.data.message).content)if(p.type==='image'){
  const bytes=blobs.get(p.attachment.attachmentId);if(!bytes||bytes.length!==p.attachment.bytes)fail('image attachment bytes are unavailable.');used.add(p.attachment.attachmentId);
 }
 // Child-only objects remain in the exact archive, never a parent's receipts.
 for(const child of source.relatedSessions??[])for(const row of child?.records??[]){const e=row?.event,m=e?.type==='user/message'?e.data:['assistant/message','tool/result'].includes(e?.type)?e.data?.message:undefined;for(const p of m?.content??[])if(p?.type==='image'){const [part]=checkedContent([p]);const b=blobs.get(part.attachment.attachmentId);if(!b||b.length!==part.attachment.bytes)fail('archived child image bytes are unavailable.');used.add(part.attachment.attachmentId);}}
 if([...blobs.keys()].some(id=>!used.has(id)))fail('image attachment bundle contains an unreferenced object.');
 return {cwd,source,sha256,bytes,ids,pinned,archived,
  sourceCut:(id:string)=>prepared.find(row=>row.original.opening.header.id===id)?.original,
  async write(stage:string,targetState:string,includeIds:Set<string>=new Set(ids)){
  privateDir(join(stage,'sessions'));const archiveDir=privateDir(join(stage,'dsh-imports'));const rawPath=join(archiveDir,sha256+'.json');if(present(rawPath)){if(!lstatSync(rawPath).isFile()||digest(readFileSync(rawPath))!==sha256)fail('existing source archive differs.');}else writeFileSync(rawPath,bytes,{mode:0o600,flag:'wx'});
  const attachments=new PiAttachments(stage);
  for(const {original,events} of prepared.filter(row=>includeIds.has(row.original.opening.header.id))){const sid='dsh-import-'+digest(original.opening.header.id).slice(0,24),seen=new Set<string>();
   for(const e of events)if(messageTypes.has(e.type))for(const p of (e.type==='user/message'?e.data:e.data.message).content)if(p.type==='image'){const key=JSON.stringify(p.attachment);if(!seen.has(key)){seen.add(key);await attachments.importStoredImage(sid,p.attachment,blobs.get(p.attachment.attachmentId)!);}}
  }
  const receipts=prepared.filter(row=>includeIds.has(row.original.opening.header.id)).map(({original,events,surface})=>writeSession(original,events,surface,stage,targetState,source,selected.get(original.opening.header.id)??fallback,sha256,Date.now()));
  const receipt=receipts.length===1?receipts[0]:{schema:'augmentor-dsh-project-import/2',sourceSha256:sha256,cwd,sessions:receipts,sourceEvents:receipts.reduce((sum,row)=>sum+row.sourceEvents,0),displayEvents:receipts.reduce((sum,row)=>sum+row.displayEvents,0),contextEntries:receipts.reduce((sum,row)=>sum+row.contextEntries,0),relatedSessionsArchived:(source.relatedSessions??[]).length,policy:'read-only',historicalToolCallsExecutable:false,rawArchive:'dsh-imports/'+sha256+'.json'};
   return {receipt,receipts};
  }};
}

/** Backwards-compatible one-project import into a new private destination. */
export async function importDshProject(sourceFile:string,targetState:string,options:ImportOptions){
 const project=prepareDshProject(sourceFile,options),{cwd,ids,pinned,archived,sha256}=project;
 if(!isAbsolute(targetState)||present(targetState))fail('destination state must be a new absolute path; existing profiles are never merged.');
 const parent=dirname(targetState),parentInfo=lstatSync(parent);if(realpathSync(parent)!==resolve(parent)||!parentInfo.isDirectory()||parentInfo.isSymbolicLink()||process.platform!=='win32'&&(parentInfo.uid!==process.getuid!()||(parentInfo.mode&0o077)!==0))fail('destination needs a private operator-owned parent.');
 const stage=join(parent,'.dsh-import-'+randomUUID());privateDir(stage);let published=false;
 try{
  const {receipt,receipts}=await project.write(stage,targetState);
  atomicJson(join(stage,'workspaces.json'),{schema:'augmentor-workspaces/1',revision:1,items:[{workspaceId:cwd,cwd,title:project.source.workspace.title}],removed:[]});
  const mapped=new Map(receipts.map(row=>[row.sourceSessionId,row.sessionId]));
  atomicJson(join(stage,'session-organization.json'),{schema:'augmentor-session-organization/1',revision:1,pinnedSessionIds:[...pinned].filter(id=>!archived.has(id)).map(id=>mapped.get(id)!),archivedSessionIds:[...archived].map(id=>mapped.get(id)!)});
  atomicJson(join(stage,'dsh-imports','receipt.json'),receipt);
  if(present(targetState))fail('destination appeared during staging; nothing was merged.');
  renameSync(stage,targetState);published=true;return receipt;
 }finally{if(!published)rmSync(stage,{recursive:true,force:true});}
}
