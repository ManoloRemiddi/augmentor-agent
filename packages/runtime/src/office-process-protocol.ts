// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {isAbsolute} from 'node:path';
import type {ConverterOptions} from '../vendor/office-entry/index.js';

export const OFFICE_PROCESS_SCHEMA='augmentor-office-process/1';
export const OFFICE_PROCESS_REQUEST_BYTES=65_536;
export const OFFICE_PROCESS_REPLY_BYTES=262_144;
export const OFFICE_PROCESS_LIMITS=Object.freeze({timeoutMs:60_000,maxInputBytes:20*1024**2,maxOutputBytes:20*1024**2,maxImageResolution:192,maxArchiveEntries:10_000,maxUncompressedBytes:250*1024**2,maxFontFiles:20_000,maxFontFileBytes:256*1024**2,maxLoadedFontBytes:512*1024**2,maxFontMetadataCacheBytes:32*1024**2,maxFontResolutionEntries:4096});
export const OFFICE_PROCESS_ERRORS=new Set(['input-too-large','output-too-large','invalid-document','unsupported-format','invalid-output','timeout','unavailable','failed','source-changed']);
export function processObject(value:unknown):value is Record<string,unknown>{return !!value&&typeof value==='object'&&!Array.isArray(value)&&Object.getPrototypeOf(value)===Object.prototype;}
function text(value:unknown,limit:number){return typeof value==='string'&&value.length>0&&Buffer.byteLength(value)<=limit&&!/[\x00-\x1f\x7f-\x9f]/.test(value);}
function keys(value:Record<string,unknown>,allowed:readonly string[]){if(Object.keys(value).some(key=>!allowed.includes(key)))throw new TypeError('Unexpected Office process field.');}
export function processOptions(value:unknown={}):ConverterOptions{
 if(!processObject(value))throw new TypeError('Invalid Office process options.');
 keys(value,[...Object.keys(OFFICE_PROCESS_LIMITS),'fontMetadataCacheDirectory','fontDirectories','fontFallbacks','initialFontFamilies']);
 if(value.fontMetadataCacheDirectory!==undefined&&value.fontMetadataCacheDirectory!==false)throw new TypeError('Office preview metadata must remain transient.');
 const result:Record<string,unknown>={fontMetadataCacheDirectory:false};
 for(const [key,max] of Object.entries(OFFICE_PROCESS_LIMITS)){
  const n=value[key]??max;if(typeof n!=='number'||!Number.isSafeInteger(n)||n<1||n>max)throw new RangeError('Invalid Office process limit: '+key);result[key]=n;
 }
 for(const key of ['fontDirectories','initialFontFamilies'])if(value[key]!==undefined){
  const items=value[key];if(!Array.isArray(items)||items.length>128||items.some(item=>!text(item,key==='fontDirectories'?4096:512)||(key==='fontDirectories'&&!isAbsolute(item))))throw new TypeError('Invalid Office process '+key);result[key]=[...items];
 }
 if(value.fontFallbacks!==undefined){
  const groups=value.fontFallbacks;if(!Array.isArray(groups)||groups.length>128||groups.some(group=>!Array.isArray(group)||group.length<2||group.length>64||group.some(item=>!text(item,512))))throw new TypeError('Invalid Office process font fallbacks.');result.fontFallbacks=groups.map(group=>[...group]);
 }
 if(Buffer.byteLength(JSON.stringify(result))>OFFICE_PROCESS_REQUEST_BYTES/2)throw new RangeError('Office process options exceed the metadata bound.');
 return result as ConverterOptions;
}
export interface ProcessFileReceipt {dev:string;ino:string;bytes:number;mtimeNs:string;ctimeNs:string;sha256:string;}
export function processReceipt(value:unknown):ProcessFileReceipt{
 if(!processObject(value))throw new TypeError('Invalid Office process file receipt.');keys(value,['dev','ino','bytes','mtimeNs','ctimeNs','sha256']);
 for(const key of ['dev','ino','mtimeNs','ctimeNs'])if(typeof value[key]!=='string'||!/^\d{1,30}$/.test(value[key] as string))throw new TypeError('Invalid Office process file identity.');
 if(typeof value.bytes!=='number'||!Number.isSafeInteger(value.bytes)||value.bytes<1||value.bytes>20*1024**2||typeof value.sha256!=='string'||!/^[a-f0-9]{64}$/.test(value.sha256))throw new TypeError('Invalid Office process file size/hash.');
 return {dev:value.dev as string,ino:value.ino as string,bytes:value.bytes,mtimeNs:value.mtimeNs as string,ctimeNs:value.ctimeNs as string,sha256:value.sha256};
}
export interface ProcessRequest {schema:typeof OFFICE_PROCESS_SCHEMA;request:{extension:string;input:ProcessFileReceipt;publication:{dev:string;ino:string}};options:ConverterOptions;}
export function processRequest(value:unknown):ProcessRequest{
 if(!processObject(value))throw new TypeError('Invalid Office process request.');keys(value,['schema','request','options']);
 if(value.schema!==OFFICE_PROCESS_SCHEMA||!processObject(value.request))throw new TypeError('Invalid Office process request version.');keys(value.request,['extension','input','publication']);
 if(typeof value.request.extension!=='string'||!['doc','docx','xls','xlsx','ppt','pptx'].includes(value.request.extension))throw new TypeError('Invalid Office process extension.');
 const publication=value.request.publication;if(!processObject(publication)||Object.keys(publication).length!==2||typeof publication.dev!=='string'||typeof publication.ino!=='string'||!/^\d{1,30}$/.test(publication.dev)||!/^\d{1,30}$/.test(publication.ino))throw new TypeError('Invalid Office publication identity.');
 const result={schema:OFFICE_PROCESS_SCHEMA,request:{extension:value.request.extension,input:processReceipt(value.request.input),publication:{dev:publication.dev,ino:publication.ino}},options:processOptions(value.options)} as ProcessRequest;
 if(Buffer.byteLength(JSON.stringify(result))>OFFICE_PROCESS_REQUEST_BYTES)throw new RangeError('Office process request exceeds its bound.');return result;
}
export type ProcessReply={schema:typeof OFFICE_PROCESS_SCHEMA;type:'result';error:{code:string}}|{schema:typeof OFFICE_PROCESS_SCHEMA;type:'result';missingFonts:string[];output:ProcessFileReceipt};
export function processReply(value:unknown):ProcessReply{
 if(!processObject(value)||value.schema!==OFFICE_PROCESS_SCHEMA||value.type!=='result')throw new TypeError('Invalid Office process reply.');
 if(value.error!==undefined){keys(value,['schema','type','error']);if(!processObject(value.error)||Object.keys(value.error).length!==1||typeof value.error.code!=='string'||!OFFICE_PROCESS_ERRORS.has(value.error.code))throw new TypeError('Invalid Office process error.');}
 else{keys(value,['schema','type','missingFonts','output']);if(!Array.isArray(value.missingFonts)||value.missingFonts.length>4096||value.missingFonts.some(item=>!text(item,512)))throw new TypeError('Invalid Office process font reply.');processReceipt(value.output);}
 if(Buffer.byteLength(JSON.stringify(value))>OFFICE_PROCESS_REPLY_BYTES)throw new RangeError('Office process reply exceeds its bound.');
 return value.error!==undefined?{schema:OFFICE_PROCESS_SCHEMA,type:'result',error:{code:(value.error as {code:string}).code}}:{schema:OFFICE_PROCESS_SCHEMA,type:'result',missingFonts:[...(value.missingFonts as string[])],output:processReceipt(value.output)};
}
