// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {createHash} from 'node:crypto';
import {join} from 'node:path';
import {constants,openSync,closeSync,fstatSync,readFileSync,writeFileSync,lstatSync,readdirSync,fsyncSync} from 'node:fs';
import {identifier} from '../../protocol/src/index.js';
import {privateDir,atomicJson} from './storage.js';
import {FILE_LIMIT,IMAGE_LIMITS,promptAttachments,type PromptAttachment} from './attachments.js';
import {fileLeafName} from '../vendor/dsh-attachment/file-store.js';
import {draftReferences,type DraftReference} from '../../protocol/src/draft-references.js';

export interface DraftFile {id:string;kind:'file'|'image';name:string;mediaType:string;lastModified:number;bytes:number;sha256:string;part:PromptAttachment & {receiptId:string}}
export interface DraftSubmission {requestId:string;mode:'queue'|'steer';text:string;attachmentIds:string[];attachments:PromptAttachment[];preparedAt:number}
export interface HarnessDraft {version:1;revision:number;textRevision:number;attachmentsRevision:number;text:string;references?:DraftReference[];attachments:DraftFile[];submission:DraftSubmission|null}
export interface EditDraftOrigin {sessionId:string;messageSeq:number;sha256:string}
interface PreparedEdit {version:1;origin:EditDraftOrigin;phase:'prepared'|'applied';draft:HarnessDraft}
const blank=():HarnessDraft=>({version:1,revision:0,textRevision:0,attachmentsRevision:0,text:'',attachments:[],submission:null});
const integer=(v:unknown)=>Number.isSafeInteger(v)&&Number(v)>=0;
const keys=(value:any,names:string[])=>value&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).every(k=>names.includes(k));
const nameValid=(v:unknown)=>typeof v==='string'&&v.length>0&&v.length<=255&&!/[\\/\x00-\x1f]/.test(v);
const mediaValid=(v:unknown)=>typeof v==='string'&&v.length<=128&&!/[\x00-\x1f]/.test(v);
function file(value:any):asserts value is DraftFile {
 if(!keys(value,['id','kind','name','mediaType','lastModified','bytes','sha256','part'])||!['file','image'].includes(value.kind)||!nameValid(value.name)||!mediaValid(value.mediaType)||!integer(value.lastModified)||!integer(value.bytes)||value.bytes>FILE_LIMIT||!/^sha256:[a-f0-9]{64}$/.test(value.sha256))throw Error('Invalid saved draft attachment.');
 identifier(value.id);if(!keys(value.part,['type','attachment','receiptId']))throw Error('Invalid saved draft receipt.');identifier(value.part.receiptId);const part=promptAttachments([value.part])[0],displayName=value.kind==='file'?fileLeafName(value.name):value.name.replace(/[\x00-\x1f\x7f]/g,'').trim().slice(0,255)||undefined;if(part.type!==value.kind||(part.type==='image'?part.attachment.originalAttachmentId:part.attachment.attachmentId)!==value.sha256||part.attachment.name!==displayName||part.type==='file'&&part.attachment.bytes!==value.bytes)throw Error('Saved draft receipt does not match its original bytes.');
 if(value.kind==='image'&&(!IMAGE_LIMITS.mediaTypes.includes(value.mediaType)||value.bytes>IMAGE_LIMITS.maxImageBytes))throw Error('Invalid saved draft image.');
}
function uploadInput(value:any){if(!keys(value,['id','kind','name','mediaType','lastModified'])||!['file','image'].includes(value.kind)||!nameValid(value.name)||!mediaValid(value.mediaType)||!integer(value.lastModified)||value.kind==='image'&&!IMAGE_LIMITS.mediaTypes.includes(value.mediaType))throw Error('Invalid Harness draft upload metadata.');identifier(value.id);}
function validate(value:any):asserts value is HarnessDraft {
 if(!keys(value,['version','revision','textRevision','attachmentsRevision','text','attachments','submission',...(value?.references===undefined?[]:['references'])])||value.version!==1||![value.revision,value.textRevision,value.attachmentsRevision].every(integer)||value.textRevision>value.revision||value.attachmentsRevision>value.revision||typeof value.text!=='string'||value.text.length>65536||!Array.isArray(value.attachments)||value.attachments.length>16)throw Error('Saved Harness draft is invalid; no content was replaced.');
 draftReferences(value.text,value.references);
 value.attachments.forEach(file);if(new Set(value.attachments.map((f:DraftFile)=>f.id)).size!==value.attachments.length)throw Error('Duplicate saved draft attachment.');
 const images=value.attachments.filter((f:DraftFile)=>f.kind==='image');if(images.length>IMAGE_LIMITS.maxImagesPerMessage||images.reduce((n:number,f:DraftFile)=>n+f.bytes,0)>IMAGE_LIMITS.maxMessageImageBytes)throw Error('Saved draft images exceed their bounds.');
 if(value.submission!==null){const s=value.submission;if(!keys(s,['requestId','mode','text','attachmentIds','attachments','preparedAt'])||!['queue','steer'].includes(s.mode)||s.text!==value.text||!integer(s.preparedAt)||!Array.isArray(s.attachmentIds)||JSON.stringify(s.attachmentIds)!==JSON.stringify(value.attachments.map((f:DraftFile)=>f.id)))throw Error('Saved draft submission is invalid; no prompt was retried.');identifier(s.requestId);const parts=promptAttachments(s.attachments);if(parts.length!==value.attachments.length||parts.some((p,i)=>JSON.stringify(p)!==JSON.stringify({type:value.attachments[i].part.type,attachment:value.attachments[i].part.attachment})))throw Error('Saved draft submission attachments do not match their original bytes.');}
}
/** Private profile-owned composer state. Reads do not load an SDK owner or retry
 * uploads/prompts. Each accepted file has real immutable bytes; pending submission
 * identity is deliberately separate from the Pi queue's execution truth.
 */
export class HarnessDrafts {
 readonly root:string;readonly records:string;readonly objects:string;readonly editOrigins:string;
 constructor(state:string){const directory=(p:string)=>{try{this.privatePath(p,true);}catch(error){if((error as NodeJS.ErrnoException).code!=='ENOENT')throw error;}return privateDir(p);};directory(join(state,'harness-drafts'));this.root=directory(join(state,'harness-drafts','v1'));this.records=directory(join(this.root,'records'));this.objects=directory(join(this.root,'objects'));this.editOrigins=directory(join(this.root,'edit-origins'));}
 private privatePath(path:string,directory=false){const stat=lstatSync(path);if(stat.isSymbolicLink()||!(directory?stat.isDirectory():stat.isFile())||process.getuid&&stat.uid!==process.getuid()||process.platform!=='win32'&&stat.mode&0o077)throw Error('Harness drafts require private owned storage.');return stat;}
 private path(sid:string){return join(this.records,identifier(sid)+'.json');}
 private read(path:string,max:number){this.privatePath(path);const fd=openSync(path,constants.O_RDONLY|(constants.O_NOFOLLOW??0));try{const stat=fstatSync(fd);if(!stat.isFile()||stat.size>max)throw Error('Saved Harness draft exceeds its bounds.');return readFileSync(fd);}finally{closeSync(fd);}}
 describe(sid:string):HarnessDraft {try{const value=JSON.parse(this.read(this.path(sid),1024*1024).toString('utf8'));validate(value);return value;}catch(error){if((error as NodeJS.ErrnoException).code==='ENOENT')return blank();throw error;}}
 private commit(sid:string,value:HarnessDraft){validate(value);const entries=readdirSync(this.records);if(entries.length>=1024&&!entries.includes(identifier(sid)+'.json'))throw Error('The Harness draft store is full.');atomicJson(this.path(sid),value);if(process.platform!=='win32'){for(const p of [this.path(sid),this.records]){const fd=openSync(p,'r');try{fsyncSync(fd);}finally{closeSync(fd);}}}return structuredClone(value);}
 private editable(sid:string){const value=this.describe(sid);if(value.submission)throw Error('The previous draft submission is unconfirmed. Inspect it and acknowledge without retrying.');return value;}
 private compare(actual:number,expected:unknown){if(!integer(expected)||actual!==expected)throw Error('The saved draft changed in another window. Reload the saved draft before editing.');}
  checkAttachment(sid:string,expected:unknown,input:any,size?:number){const value=this.editable(sid);this.compare(value.attachmentsRevision,expected);uploadInput(input);if(value.attachments.length>=16||value.attachments.some(f=>f.id===input.id))throw Error('This draft attachment identity is already saved or the draft is full.');if(size!==undefined&&(!integer(size)||size>FILE_LIMIT||input.kind==='image'&&(size>IMAGE_LIMITS.maxImageBytes||value.attachments.filter(f=>f.kind==='image').length>=IMAGE_LIMITS.maxImagesPerMessage||value.attachments.filter(f=>f.kind==='image').reduce((n,f)=>n+f.bytes,0)+size>IMAGE_LIMITS.maxMessageImageBytes)))throw Error('Draft attachment exceeds its bounds.');}
 setText(sid:string,expected:unknown,text:unknown,references?:unknown){if(typeof text!=='string'||text.length>65536)throw Error('Draft text exceeds its limit.');const refs=draftReferences(text,references),value=this.editable(sid);this.compare(value.textRevision,expected);if(value.text===text&&JSON.stringify(value.references??[])===JSON.stringify(refs))return value;const {references:previous,...base}=value;return this.commit(sid,{...base,revision:value.revision+1,textRevision:value.textRevision+1,text,...(refs.length?{references:refs}:{})});}
 attach(sid:string,expected:unknown,input:unknown,data:Uint8Array){
  const value=this.editable(sid);this.compare(value.attachmentsRevision,expected);const hash='sha256:'+createHash('sha256').update(data).digest('hex'),entry={...(input as any),bytes:data.byteLength,sha256:hash};file(entry);if(value.attachments.some(f=>f.id===entry.id))throw Error('This draft attachment identity is already saved; it was not uploaded again.');
  const next={...value,revision:value.revision+1,attachmentsRevision:value.attachmentsRevision+1,attachments:[...value.attachments,entry]};validate(next);
  this.storeObject(hash,data);
  return this.commit(sid,next);
 }
 private storeObject(hash:string,data:Uint8Array){
  if(data.byteLength>FILE_LIMIT||hash!=='sha256:'+createHash('sha256').update(data).digest('hex'))throw Error('The original draft bytes do not match their identity.');
  const path=join(this.objects,hash.slice(7)+'.bin');try{const fd=openSync(path,constants.O_WRONLY|constants.O_CREAT|constants.O_EXCL|(constants.O_NOFOLLOW??0),0o600);try{writeFileSync(fd,data);fsyncSync(fd);}finally{closeSync(fd);}}catch(error){if((error as NodeJS.ErrnoException).code!=='EEXIST')throw error;const saved=this.read(path,FILE_LIMIT);if(saved.byteLength!==data.byteLength||'sha256:'+createHash('sha256').update(saved).digest('hex')!==hash)throw Error('The saved draft attachment is corrupt.');}
  if(process.platform!=='win32'){const fd=openSync(this.objects,'r');try{fsyncSync(fd);}finally{closeSync(fd);}}
 }
 private editPath(sid:string){return join(this.editOrigins,identifier(sid)+'.json');}
 private editOrigin(origin:EditDraftOrigin){identifier(origin.sessionId);if(!integer(origin.messageSeq)||origin.messageSeq<1||!/^sha256:[a-f0-9]{64}$/.test(origin.sha256)||!keys(origin,['sessionId','messageSeq','sha256']))throw Error('Invalid edit draft origin.');}
 private readEdit(sid:string):PreparedEdit|null{
  try{const value=JSON.parse(this.read(this.editPath(sid),1024*1024).toString('utf8'));if(!keys(value,['version','origin','phase','draft'])||value.version!==1||!['prepared','applied'].includes(value.phase))throw Error('Invalid prepared edit draft.');this.editOrigin(value.origin);validate(value.draft);return value;}
  catch(error){if((error as NodeJS.ErrnoException).code==='ENOENT')return null;throw error;}
 }
 private saveEdit(sid:string,value:PreparedEdit){
  const entries=readdirSync(this.editOrigins);if(entries.length>=1024&&!entries.includes(identifier(sid)+'.json'))throw Error('The prepared edit store is full.');
  atomicJson(this.editPath(sid),value);if(process.platform!=='win32')for(const path of [this.editPath(sid),this.editOrigins]){const fd=openSync(path,'r');try{fsyncSync(fd);}finally{closeSync(fd);}}
 }
 preparedEdit(sid:string,origin:EditDraftOrigin){this.editOrigin(origin);const saved=this.readEdit(sid);if(saved&&JSON.stringify(saved.origin)!==JSON.stringify(origin))throw Error('The prepared edit source changed; no draft was replaced.');return saved!==null;}
 prepareEdit(sid:string,origin:EditDraftOrigin,text:string,files:{entry:DraftFile;data:Uint8Array}[]){
  if(this.preparedEdit(sid,origin))return;
  if(JSON.stringify(this.describe(sid))!==JSON.stringify(blank()))throw Error('The child already has a draft; no content was replaced.');
  const draft:HarnessDraft={...blank(),revision:1,textRevision:1,attachmentsRevision:files.length?1:0,text,attachments:files.map(f=>f.entry)};validate(draft);
  for(const f of files)this.storeObject(f.entry.sha256,f.data);
  this.saveEdit(sid,{version:1,origin,phase:'prepared',draft});
 }
 applyEdit(sid:string,origin:EditDraftOrigin){
  if(!this.preparedEdit(sid,origin))throw Error('Prepare the original message and attachments before creating the edit branch.');
  const saved=this.readEdit(sid)!;if(saved.phase==='applied')return;
  const current=this.describe(sid);
  for(const f of saved.draft.attachments){const data=this.read(join(this.objects,f.sha256.slice(7)+'.bin'),FILE_LIMIT);if(data.byteLength!==f.bytes||'sha256:'+createHash('sha256').update(data).digest('hex')!==f.sha256)throw Error('The prepared edit attachment is corrupt.');}
  if(JSON.stringify(current)!==JSON.stringify(saved.draft)){
   if(JSON.stringify(current)!==JSON.stringify(blank()))throw Error('The child draft changed; no content was replaced.');
   this.commit(sid,saved.draft);
  }
  this.saveEdit(sid,{...saved,phase:'applied'});
 }
 editApplied(sid:string){const saved=this.readEdit(sid);return saved?.phase==='applied'||!!saved&&this.describe(sid).revision!==0;}
 remove(sid:string,expected:unknown,id:unknown){const value=this.editable(sid);this.compare(value.attachmentsRevision,expected);identifier(id);if(!value.attachments.some(f=>f.id===id))throw Error('This draft attachment is no longer saved.');return this.commit(sid,{...value,revision:value.revision+1,attachmentsRevision:value.attachmentsRevision+1,attachments:value.attachments.filter(f=>f.id!==id)});}
 bytes(sid:string,id:unknown,sha256:unknown){identifier(id);const entry=this.describe(sid).attachments.find(f=>f.id===id&&f.sha256===sha256);if(!entry)throw Error('This draft attachment does not belong to the conversation.');const data=this.read(join(this.objects,entry.sha256.slice(7)+'.bin'),FILE_LIMIT);if(data.byteLength!==entry.bytes||'sha256:'+createHash('sha256').update(data).digest('hex')!==entry.sha256)throw Error('The saved draft attachment is corrupt.');return {entry,data};}
 prepare(sid:string,expected:unknown,requestId:unknown,mode:unknown,attachments:PromptAttachment[]=[]){const value=this.editable(sid);this.compare(value.revision,expected);if(value.references?.some(r=>r.invalid))throw Error('Remove unavailable draft references before sending.');identifier(requestId);if(!['queue','steer'].includes(String(mode))||!value.text.trim()&&!value.attachments.length)throw Error('Choose a non-empty draft and submission mode.');for(const f of value.attachments)this.bytes(sid,f.id,f.sha256);return this.commit(sid,{...value,revision:value.revision+1,submission:{requestId:requestId as string,mode:mode as 'queue'|'steer',text:value.text,attachmentIds:value.attachments.map(f=>f.id),attachments:promptAttachments(attachments),preparedAt:Date.now()}});}
 settle(sid:string,requestId:unknown,accepted:boolean){const value=this.describe(sid);identifier(requestId);if(!value.submission||value.submission.requestId!==requestId)throw Error('This draft submission identity is no longer current.');const {references,...base}=value;return this.commit(sid,{...(accepted?base:value),revision:value.revision+1,...(accepted?{textRevision:value.textRevision+1,attachmentsRevision:value.attachmentsRevision+1,text:'',attachments:[]}:{}) ,submission:null});}
 dirtyCount(){let count=0;const entries=readdirSync(this.records);if(entries.length>1024)throw Error('The Harness draft store exceeds its bounds.');for(const name of entries){if(!name.endsWith('.json'))continue;const value=this.describe(identifier(name.slice(0,-5)));if(value.text.length||value.attachments.length||value.submission)count++;}return count;}
}
