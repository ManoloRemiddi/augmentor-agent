// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {isDeepStrictEqual} from 'node:util';
import {SessionManager,CURRENT_SESSION_VERSION} from '@earendil-works/pi-coding-agent';
import {openSync,closeSync,readSync,fstatSync,constants} from 'node:fs';
import type {Data,DisplayEvent} from '../../protocol/src/index.js';
import {readDshArchive} from './dsh-archived-family.js';
import {dshHistoryCut} from './dsh-project-import.js';
export interface BranchSourceScope {state:string;sessionId:string}
const failure=()=>Error('The imported DSH branch cannot verify its exact source cut. Originals were preserved.');
const bindingOf=(manager:SessionManager)=>manager.getBranch().findLast(e=>e.type==='custom'&&e.customType==='augmentor.dsh-import.v1');
const clean=(content:unknown)=>Array.isArray(content)?content.map(p=>{const {offloaded,...part}=p;return part;}):content;
/** A source sequence + archive hash is the identity; repeated answer text and
 * ordinal position are never evidence for an imported historical reply. */
export function importedBranchContext(manager:SessionManager,events:DisplayEvent[],target:DisplayEvent,cutoff:number,mode:'reply'|'edit',scope?:BranchSourceScope){
 const stamp=target.data.importedFrom;if(stamp?.system!=='DSH')return null;
 const native=bindingOf(manager);if(!scope||!native||native.type!=='custom')throw failure();
 const binding=native.data as Data;
 if(stamp.archiveSha256!==binding.sha256||stamp.sourceSessionId!==binding.sourceSessionId||!Number.isSafeInteger(stamp.sourceSeq)||stamp.sourceSeq<0)throw failure();
 const {source,root}=readDshArchive(scope.state,binding);if(source.workspace?.path!==manager.getCwd())throw failure();
 const row=root.records[stamp.sourceSeq]?.event;if(row?.time!==stamp.sourceTime||row.type!==target.type)throw failure();
 const selected=dshHistoryCut(root,source,binding.sha256,scope.state,stamp.sourceSeq);
 const original=selected.display.find(e=>e.data.importedFrom.sourceSeq===stamp.sourceSeq);
 const content=target.type==='user/message'?target.data.content:target.data.message?.content,expected=original?.type==='user/message'?original.data.content:original?.data.message?.content;
 if(!original||original.type!==target.type||!isDeepStrictEqual(clean(content),clean(expected)))throw failure();
 if(mode==='reply'&&(!Array.isArray(content)||content.some(p=>p.type==='toolCall')))throw Error('Choose the historical reply after its tools have finished.');
 const inherited=events.filter(e=>mode==='edit'?e.seq<cutoff:e.seq<=cutoff);
 const sourceEvents=inherited.filter(e=>e.data.importedFrom?.system==='DSH');let through=-1;
 for(const event of sourceEvents){const p=event.data.importedFrom;if(p.archiveSha256!==binding.sha256||p.sourceSessionId!==binding.sourceSessionId||p.sourceSeq!==through+1||p.sourceSeq>stamp.sourceSeq)throw failure();through=p.sourceSeq;}
 if(mode==='reply'&&through!==stamp.sourceSeq)throw failure();
 const projected=mode==='reply'?selected:dshHistoryCut(root,source,binding.sha256,scope.state,through);
 return {manager:projected.manager,leaf:projected.manager.getLeafId(),events:inherited,rebuilt:true as const};
}
/** Ordinary Pi messages after an import keep their own ordinals. Historical
 * display messages are not native Pi assistant entries, and source summaries
 * may have removed earlier human entries from the imported native transcript. */
export function ordinaryBranchEntries(manager:SessionManager,events:DisplayEvent[],type:string,seq:number,role:'user'|'assistant'){
 const branch=manager.getBranch(),binding=bindingOf(manager);
 if(!binding)return {entries:branch.filter(e=>e.type==='message'&&e.message.role===role),ordinal:events.filter(e=>e.type===type&&e.seq<=seq).length-1};
 const bindingData=(binding as {data:Data}).data,cut=branch.findLast(e=>e.type==='custom'&&e.customType==='augmentor.dsh-cut.v1');
 const cutData=cut?.type==='custom'?cut.data as Data:undefined;
 if(cutData&&(cutData.archiveSha256!==bindingData.sha256||cutData.sourceSessionId!==bindingData.sourceSessionId||!Number.isSafeInteger(cutData.throughSeq)||cutData.throughSeq< -1||cutData.throughSeq>bindingData.throughSeq))throw failure();
 const displayCut=(cutData?.throughSeq??bindingData.throughSeq)+1;if(!Number.isSafeInteger(displayCut)||seq<=displayCut)throw failure();
 const end=branch.findLastIndex(e=>e.type==='custom_message'&&e.customType==='augmentor.dsh-history.v1'&&(e.details as Data)?.boundary==='end-of-import');
 if(end<0)throw failure();
 return {entries:branch.slice(end+1).filter(e=>e.type==='message'&&e.message.role===role),ordinal:events.filter(e=>e.type===type&&e.seq<=seq&&e.seq>displayCut&&e.data.importedFrom?.system!=='DSH').length-1};
}
/** Historical assistant/tool attachments have no invented user-upload receipt. A
 * branch may resolve only references actually retained in its selected native
 * DSH media entries and in the checksum-verified source parent's record. */
export function inheritedDshAttachment(manager:SessionManager,state:string,part:Data){
 if(part.type!=='image'&&part.type!=='file')return false;const native=bindingOf(manager);if(!native||native.type!=='custom')return false;const binding=native.data as Data;
 const entries=manager.getBranch().filter(e=>e.type==='custom_message'&&e.customType==='augmentor.dsh-media.v1'&&[...((e.details as Data)?.images??[]),...((e.details as Data)?.files??[])].some((p:Data)=>p.type===part.type&&isDeepStrictEqual(p.attachment,part.attachment)));
 if(!entries.length)return false;const {root}=readDshArchive(state,binding);
 return entries.some(entry=>{if(entry.type!=='custom_message')return false;const d=entry.details as Data;if(d.archiveSha256!==binding.sha256||d.sourceSessionId!==binding.sourceSessionId)return false;const e=root.records[d.sourceSeq]?.event;if(!e||!['user/message','assistant/message','tool/result'].includes(e.type))return false;const content=(e.type==='user/message'?e.data:e.data.message)?.content;return Array.isArray(content)&&content.some((p:Data)=>p.type===part.type&&isDeepStrictEqual(p.attachment,part.attachment));});
}

/** Attachment inspection must not let SDK.open migrate an older native file. */
export function coldDshAttachment(file:string,state:string,part:Data){
 const fd=openSync(file,constants.O_RDONLY|(constants.O_NOFOLLOW??0)|(constants.O_NONBLOCK??0));
 try{const info=fstatSync(fd);if(!info.isFile()||info.nlink!==1||process.platform!=='win32'&&(info.uid!==process.getuid?.()||(info.mode&0o077)!==0))throw failure();
  const buffer=Buffer.alloc(65536),bytes=readSync(fd,buffer,0,buffer.length,0),end=buffer.subarray(0,bytes).indexOf(10);if(end<0)throw failure();const header=JSON.parse(buffer.subarray(0,end).toString('utf8'));if(header.type!=='session'||header.version!==CURRENT_SESSION_VERSION)throw failure();
 }finally{closeSync(fd);}
 return inheritedDshAttachment(SessionManager.open(file),state,part);
}

// Retain internal image-helper imports used by existing integration checks.
export {inheritedDshAttachment as inheritedDshImage,coldDshAttachment as coldDshImage};
