// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {randomUUID,createHash} from 'node:crypto';
import {join} from 'node:path';
import {readFileSync,lstatSync,openSync,closeSync,fsyncSync} from 'node:fs';
import type {ImageContent} from '@earendil-works/pi-ai';
import {identifier} from '../../protocol/src/index.js';
import type {ArchiveFileSource} from './archive-snapshot.js';
import {privateDir,atomicJson} from './storage.js';
import {saveFileVerbatim,storedFilePath,readFileStreamVerbatim,fileLeafName} from '../vendor/dsh-attachment/file-store.js';
import {saveImageFile,readImageFile,normalizedImagePath,publishImmutableObject} from '../vendor/dsh-attachment/store.js';
import {detectImage} from '../vendor/dsh-attachment/image.js';
import type {FileAttachmentRef,ImageAttachmentRef,ImageMediaType} from '../vendor/dsh-attachment/types.js';

export type PromptAttachment={type:'file';attachment:FileAttachmentRef}|{type:'image';attachment:ImageAttachmentRef & {originalAttachmentId?:string}};
export const IMAGE_LIMITS={maxImageBytes:10*1024*1024,maxImagesPerMessage:8,maxMessageImageBytes:20*1024*1024,maxImagePixels:40_000_000,maxImageDimension:32768,mediaTypes:['image/png','image/jpeg','image/webp','image/gif'] as ImageMediaType[]};
export const FILE_LIMIT=20*1024*1024;
interface Receipt {receiptId:string;part:PromptAttachment;original?:FileAttachmentRef}
/** Validates queue references without granting access to the underlying objects. */
export function promptAttachments(value:unknown):PromptAttachment[]{
 if(value===undefined)return [];
 if(!Array.isArray(value)||value.length>16)throw Error('Choose at most sixteen attachments.');
 return value.map(part=>{
  const a=part?.attachment;
  if(!['image','file'].includes(part?.type)||!a||!/^sha256:[a-f0-9]{64}$/.test(a.attachmentId)||!Number.isSafeInteger(a.bytes)||a.bytes<0||a.bytes>FILE_LIMIT||a.name!==undefined&&(typeof a.name!=='string'||a.name.length>255||/[\\/\x00-\x1f]/.test(a.name)))throw Error('Invalid attachment reference.');
  if(part.type==='image'&&a.originalAttachmentId!==undefined&&!/^sha256:[a-f0-9]{64}$/.test(a.originalAttachmentId))throw Error('Invalid original image identity.');
  if(part.type==='image'&&(!IMAGE_LIMITS.mediaTypes.includes(a.mediaType)||![a.width,a.height].every(n=>Number.isSafeInteger(n)&&n>0&&n<=32768)))throw Error('Invalid image reference.');
  return structuredClone(part);
 });
}
export function submittedParts(input:string,attachments:PromptAttachment[]=[]){return [...(input?[{type:'text',text:input}]:[]),...attachments];}

/** Private immutable supplier objects plus exact-conversation upload authority.
 * Receipts survive Host restart; reading history never loads an AgentSession.
 */
export class PiAttachments {
 readonly root:string;
 constructor(state:string,private inherited:(sid:string,part:PromptAttachment)=>boolean=()=>false,private readOnly=false){this.root=join(state,'attachments','v1');if(readOnly){const stat=lstatSync(this.root);if(!stat.isDirectory()||stat.isSymbolicLink()||stat.uid!==process.getuid?.()||(stat.mode&0o077))throw Error('Attachment source is not a private owned store.');}else privateDir(this.root);}
 private writable(){if(this.readOnly)throw Error('This attachment store is read only.');}
 private path(sid:string){return join(this.root,sid+'.json');}
 private receipts(sid:string):Receipt[]{
  try{const stat=lstatSync(this.path(sid));if(!stat.isFile()||stat.isSymbolicLink()||process.getuid&&stat.uid!==process.getuid()||process.platform!=='win32'&&stat.mode&0o077)throw Error('Attachment receipts require a private owned file.');const raw=readFileSync(this.path(sid),'utf8');if(raw.length>4*1024*1024)throw Error('Attachment receipts exceed their bounds.');const rows=JSON.parse(raw);if(!Array.isArray(rows)||rows.length>10000)throw Error('Invalid attachment receipts.');for(const row of rows){if(typeof row.receiptId!=='string')throw Error('Invalid attachment receipt.');promptAttachments([row.part]);}return rows;}
  catch(error){if((error as NodeJS.ErrnoException).code==='ENOENT')return [];throw error;}
 }
 private commit(sid:string,part:PromptAttachment,original?:FileAttachmentRef){const rows=this.receipts(sid);if(rows.length>=10000)throw Error('This conversation has too many attachment receipts.');const receipt={receiptId:randomUUID(),part,...(original?{original}:{})};atomicJson(this.path(sid),[...rows,receipt]);if(process.platform!=='win32'){for(const path of [this.path(sid),this.root]){const fd=openSync(path,'r');try{fsyncSync(fd);}finally{closeSync(fd);}}}return receipt;}
 /** Admit exact already-normalized DSH bytes without recompression. No camera
  * original is invented: an imported reference retains its stored image only. */
 async importStoredImage(sid:string,attachment:ImageAttachmentRef,data:Uint8Array){
  this.writable();identifier(sid);promptAttachments([{type:'image',attachment}]);
  if(data.byteLength!==attachment.bytes||data.byteLength>IMAGE_LIMITS.maxImageBytes)throw Error('Imported image exceeds its byte bound.');
  const decoded=await detectImage(data,{maxPixels:IMAGE_LIMITS.maxImagePixels,maxDimension:IMAGE_LIMITS.maxImageDimension});
  if(decoded.mediaType!==attachment.mediaType||decoded.width!==attachment.width||decoded.height!==attachment.height)throw Error('Imported image metadata differs from its bytes.');
  await publishImmutableObject(this.root,normalizedImagePath(this.root,attachment),data,attachment.attachmentId.slice(7));
  const part:PromptAttachment={type:'image',attachment};
  if(!this.receipts(sid).some(row=>JSON.stringify(row.part)===JSON.stringify(part)))this.commit(sid,part);
 }
 /** Preserve exact historical file bytes and their original sanitized name. */
 async importStoredFile(sid:string,attachment:FileAttachmentRef,data:Uint8Array){
  this.writable();identifier(sid);promptAttachments([{type:'file',attachment}]);
  if(typeof attachment.name!=='string'||attachment.name!==fileLeafName(attachment.name)||Object.keys(attachment).sort().join(',')!=='attachmentId,bytes,name'||data.byteLength!==attachment.bytes||data.byteLength>FILE_LIMIT||'sha256:'+createHash('sha256').update(data).digest('hex')!==attachment.attachmentId)throw Error('Imported file metadata differs from its bytes.');
  const stored=await saveFileVerbatim(this.root,{data,name:attachment.name});
  if(stored.attachmentId!==attachment.attachmentId||stored.bytes!==attachment.bytes||stored.name!==attachment.name)throw Error('Imported file storage differs from its source.');
  const part:PromptAttachment={type:'file',attachment};if(!this.receipts(sid).some(row=>JSON.stringify(row.part)===JSON.stringify(part)))this.commit(sid,part);
 }
 historicalImagePath(sid:string,attachment:ImageAttachmentRef){this.authorize(sid,{type:'image',attachment});return normalizedImagePath(this.root,attachment);}
 async uploadImage(sid:string,data:Uint8Array,name:string,mediaType:ImageMediaType){this.writable();
  if(!IMAGE_LIMITS.mediaTypes.includes(mediaType))throw Error('Unsupported image type.');
  const normalized=await saveImageFile(this.root,{data,name,mediaType},IMAGE_LIMITS,{maxPixels:4_000_000,maxDimension:4096,maxBytes:5*1024*1024});
  const original=await saveFileVerbatim(this.root,{data,name}),attachment={...normalized,originalAttachmentId:original.attachmentId};const receipt=this.commit(sid,{type:'image',attachment},original);return {receiptId:receipt.receiptId,attachment};
 }
 async upload(sid:string,data:Uint8Array,name:string){this.writable();if(data.byteLength>FILE_LIMIT)throw Error('File exceeds the twenty MiB limit.');const file=await saveFileVerbatim(this.root,{data,name});const receipt=this.commit(sid,{type:'file',attachment:file});return {receiptId:receipt.receiptId,file};}
 private authorize(sid:string,part:PromptAttachment){
  promptAttachments([part]);
  if(!this.receipts(sid).some(row=>JSON.stringify(row.part)===JSON.stringify(part))&&!this.inherited(sid,part))throw Error('Attachment does not belong to this conversation.');
 }
 async admit(sid:string,content:unknown):Promise<{input:string;attachments:PromptAttachment[]}>{
  this.writable();if(!Array.isArray(content)||content.length>32)throw Error('Invalid prompt content.');
  let bytes=0,count=0;const attachments:PromptAttachment[]=[],texts:string[]=[];
  for(const p of content){
   if(p?.type==='text'&&typeof p.text==='string'){texts.push(p.text);continue;}
   if(p?.type==='file'||p?.type==='image'&&p.attachment){
    const receipt=this.receipts(sid).find(row=>row.receiptId===p.receiptId&&row.part.type===p.type);
    if(!receipt||JSON.stringify(receipt.part.attachment)!==JSON.stringify(p.attachment))throw Error('Upload receipt is missing or belongs to another conversation.');
    if(receipt.part.type==='image'){bytes+=receipt.original?.bytes??receipt.part.attachment.bytes;if(++count>IMAGE_LIMITS.maxImagesPerMessage||bytes>IMAGE_LIMITS.maxMessageImageBytes)throw Error('Images exceed the message limit.');}attachments.push(receipt.part);continue;
   }
   if(p?.type==='image'&&typeof p.data==='string'){
    if(!IMAGE_LIMITS.mediaTypes.includes(p.mediaType)||p.data.length>Math.ceil(IMAGE_LIMITS.maxImageBytes/3)*4||!p.data.length||p.data.length%4||!/^[A-Za-z0-9+/]*={0,2}$/.test(p.data))throw Error('Invalid or oversized image upload.');
    const data=Buffer.from(p.data,'base64');if(data.toString('base64')!==p.data)throw Error('Invalid image encoding.');bytes+=data.length;
    if(++count>IMAGE_LIMITS.maxImagesPerMessage||bytes>IMAGE_LIMITS.maxMessageImageBytes)throw Error('Images exceed the message limit.');
    const normalized=await saveImageFile(this.root,{data,mediaType:p.mediaType,name:p.name},IMAGE_LIMITS,{maxPixels:4_000_000,maxDimension:4096,maxBytes:5*1024*1024});
    const original=await saveFileVerbatim(this.root,{data,name:p.name}),attachment={...normalized,originalAttachmentId:original.attachmentId};const part:PromptAttachment={type:'image',attachment};this.commit(sid,part,original);attachments.push(part);continue;
   }
   throw Error('Unsupported prompt content; no input was submitted.');
  }
  const input=texts.join('\n');if(input.length>65536||!input.trim()&&!attachments.length)throw Error('Invalid prompt text.');return {input,attachments:promptAttachments(attachments)};
 }
 async resolve(sid:string,input:string,attachments:PromptAttachment[]=[]){
  const images:ImageContent[]=[],files:string[]=[];
  for(const part of attachments){this.authorize(sid,part);
   if(part.type==='image'){const stored=await readImageFile(this.root,part.attachment);images.push({type:'image',mimeType:part.attachment.mediaType,data:Buffer.from(stored.data).toString('base64')});}
   else{let bytes=0;for await(const chunk of readFileStreamVerbatim(this.root,part.attachment)){bytes+=chunk.byteLength;if(bytes>part.attachment.bytes||bytes>FILE_LIMIT)throw Error('Stored file exceeds its declared byte bound.');}files.push(JSON.stringify({name:part.attachment.name,path:storedFilePath(this.root,part.attachment),bytes:part.attachment.bytes}));}
  }
  return {text:input+(files.length?'\n\nAttached files (read their exact contents using the file tools):\n'+files.join('\n'):''),images};
 }
 async image(sid:string,attachment:ImageAttachmentRef){this.authorize(sid,{type:'image',attachment});return readImageFile(this.root,attachment);}
 /** Recover only the original bytes named by this submitted message. A child
  * receives its own receipt, referencing the same immutable supplier objects. */
 async editOriginal(sid:string,originSid:string,part:PromptAttachment){
  identifier(sid);identifier(originSid);this.authorize(sid,part);
  const receipt=this.receipts(originSid).find(row=>JSON.stringify(row.part)===JSON.stringify(part));
  if(!receipt)throw Error('The original attachment receipt is unavailable; the message was not edited.');
  const original=part.type==='file'?part.attachment:receipt.original;
  if(!original||part.type==='image'&&original.attachmentId!==part.attachment.originalAttachmentId)throw Error('The original image is unavailable; the message was not edited.');
  if(original.bytes>(part.type==='image'?IMAGE_LIMITS.maxImageBytes:FILE_LIMIT))throw Error('The original attachment exceeds its bounds.');
  const chunks:Buffer[]=[];let bytes=0;
  for await(const chunk of readFileStreamVerbatim(this.root,original)){bytes+=chunk.byteLength;if(bytes>FILE_LIMIT)throw Error('The original attachment exceeds its bounds.');chunks.push(Buffer.from(chunk));}
  const data=Buffer.concat(chunks);let mediaType='application/octet-stream';
  if(part.type==='image'){
   await readImageFile(this.root,part.attachment);
   if(data.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10])))mediaType='image/png';
   else if(data[0]===255&&data[1]===216&&data[2]===255)mediaType='image/jpeg';
   else if(['GIF87a','GIF89a'].includes(data.subarray(0,6).toString('ascii')))mediaType='image/gif';
   else if(data.subarray(0,4).toString('ascii')==='RIFF'&&data.subarray(8,12).toString('ascii')==='WEBP')mediaType='image/webp';
   else throw Error('The original image type is unavailable; the message was not edited.');
  }
  return {part:structuredClone(part),original:receipt.original,data,name:part.attachment.name??original.name,mediaType};
 }
 grantEdit(sid:string,original:{part:PromptAttachment;original?:FileAttachmentRef}){this.writable();
  identifier(sid);const receipt=this.receipts(sid).find(row=>JSON.stringify(row.part)===JSON.stringify(original.part))??this.commit(sid,original.part,original.original);
  return {...structuredClone(receipt.part),receiptId:receipt.receiptId};
 }
 /** Select only the immutable objects named by an already authorized part.
  * Receipt tables and workspace aliases are never exported or scanned. */
 archiveSources(sid:string,part:PromptAttachment):ArchiveFileSource[]{
  identifier(sid);this.authorize(sid,part);const a=part.attachment,digest=a.attachmentId.slice(7),name=fileLeafName(a.name);
  const object=(hash:string)=>join(this.root,'file-objects',hash.slice(0,2),hash);
  if(part.type==='file')return [{root:this.root,file:object(digest),path:'files/'+digest+'/'+name,expectedBytes:a.bytes,expectedSha256:digest}];
  const image=part.attachment,extension=({'image/png':'png','image/jpeg':'jpg','image/webp':'webp','image/gif':'gif'} as const)[image.mediaType];
  const sources:ArchiveFileSource[]=[{root:this.root,file:normalizedImagePath(this.root,image),path:'media/'+digest+'.'+extension,expectedBytes:image.bytes,expectedSha256:digest}];
  if(image.originalAttachmentId){const original=image.originalAttachmentId.slice(7);sources.push({root:this.root,file:object(original),path:'files/'+original+'/'+name,expectedSha256:original});}
  return sources;
 }
}
