// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {openSync,closeSync,fstatSync,readSync,lstatSync,realpathSync,writeFileSync,fsyncSync,constants} from 'node:fs';
import {dirname,join,resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {historicalProject} from './dsh-historical-project.js';
import {privateDir} from './storage.js';
import {type Data} from '../../protocol/src/index.js';
export const DSH_MANIFEST_BYTES=32*1024*1024,DSH_OBJECT_BYTES=16*1024*1024,DSH_BUNDLE_BYTES=256*1024*1024,DSH_BUNDLE_OBJECTS=16384;
const hash=(b:Buffer|string)=>createHash('sha256').update(b).digest('hex');
const fail=():never=>{throw Error('DSH bundle object, manifest, checksum or bound differs. Originals are preserved.');};
const integer=(v:unknown,min:number,max:number)=>typeof v==='number'&&Number.isSafeInteger(v)&&v>=min&&v<=max;
const keys=(v:Data,want:string)=>v&&typeof v==='object'&&!Array.isArray(v)&&Object.keys(v).sort().join(',')===want;
type Ref={sha256:string;bytes:number};
function folder(path:string){const s=lstatSync(path);if(!s.isDirectory()||s.isSymbolicLink()||realpathSync(path)!==resolve(path)||process.platform!=='win32'&&(s.uid!==process.getuid?.()||(s.mode&0o077)!==0))fail();}
/** A fixed-size descriptor read cannot grow with a concurrently replaced file. */
function boundedFile(path:string,max:number,expected?:Ref,objectDir?:string,privateFile=true){
 let directory:number|undefined,fd:number|undefined;
 try{
  if(objectDir){folder(objectDir);directory=openSync(objectDir,constants.O_RDONLY|(constants.O_DIRECTORY??0)|(constants.O_NOFOLLOW??0));}
  const anchored=directory!==undefined&&process.platform==='linux'?'/proc/self/fd/'+directory+'/'+expected!.sha256:path,visible=lstatSync(anchored);if(!visible.isFile()||visible.isSymbolicLink())fail();
  fd=openSync(anchored,constants.O_RDONLY|(constants.O_NOFOLLOW??0)|(constants.O_NONBLOCK??0));
  const before=fstatSync(fd);if(before.ino!==visible.ino||before.dev!==visible.dev||!before.isFile()||privateFile&&before.nlink!==1||before.size>max||expected&&before.size!==expected.bytes||privateFile&&process.platform!=='win32'&&(before.uid!==process.getuid?.()||(before.mode&0o077)!==0))fail();
  const out=Buffer.alloc(before.size+1);let length=0;
  while(length<out.length){const n=readSync(fd,out,length,out.length-length,null);if(!n)break;length+=n;}
  const after=fstatSync(fd),raw=out.subarray(0,length);
  if(length!==before.size||after.size!==before.size||after.mtimeMs!==before.mtimeMs||after.ctimeMs!==before.ctimeMs||expected&&hash(raw)!==expected.sha256)fail();
  if(directory!==undefined){const d=fstatSync(directory),now=lstatSync(objectDir!);if(now.isSymbolicLink()||now.ino!==d.ino||now.dev!==d.dev)fail();}
  return raw;
 }finally{if(fd!==undefined)closeSync(fd);if(directory!==undefined)closeSync(directory);}
}
export type DshProjectArchive={source:Data;bytes:Buffer;sha256:string;expandedBytes:number;objects:Map<string,Ref>;readObject:(ref:Ref)=>Buffer};
const bundled=new WeakMap<Data,DshProjectArchive>();
/** v1 retains its immutable JSON. v2 resolves only checksum-named bounded objects,
 * caching at most one session's records and one opening snapshot per archive. */
export function loadDshProjectArchive(sourceFile:string,sha256:string,objectDir=join(dirname(sourceFile),'objects'),privateManifest=false):DshProjectArchive{
 const bytes=boundedFile(sourceFile,DSH_MANIFEST_BYTES,undefined,undefined,privateManifest);if(hash(bytes)!==sha256)throw Error('DSH pilot import: source checksum changed.');
 const document=JSON.parse(bytes.toString('utf8')) as Data,objects=new Map<string,Ref>();let expandedBytes=bytes.length;
 const readObject=(ref:Ref)=>{const known=objects.get(ref.sha256);if(!known||known.bytes!==ref.bytes)fail();return boundedFile(join(objectDir,ref.sha256),DSH_OBJECT_BYTES,ref,objectDir);};
 if(document.schema==='augmentor-dsh-project-export/1')return {source:document,bytes,sha256,expandedBytes,objects,readObject};
 if(!['augmentor-dsh-project-export/2','augmentor-dsh-project-export/3'].includes(document.schema))fail();
 /* v3 registers its original/derived closure once, without storing wrappers. */
 if(document.schema==='augmentor-dsh-project-export/2'&&(!Array.isArray(document.sessions)||document.sessions.length>128||!Array.isArray(document.relatedSessions)||document.relatedSessions.length>32))fail();
 const reference=(value:Data):Ref=>{
  if(!keys(value,'bytes,sha256')||typeof value.sha256!=='string'||!/^[a-f0-9]{64}$/.test(value.sha256)||!integer(value.bytes,1,DSH_OBJECT_BYTES))fail();
  const ref={sha256:value.sha256,bytes:value.bytes},previous=objects.get(ref.sha256);if(previous&&previous.bytes!==ref.bytes)fail();
  objects.set(ref.sha256,ref);expandedBytes+=ref.bytes;if(objects.size>DSH_BUNDLE_OBJECTS||expandedBytes>DSH_BUNDLE_BYTES)fail();return ref;
 };
 if(document.schema==='augmentor-dsh-project-export/3'){const source=historicalProject(document,reference,readObject),result={source,bytes,sha256,expandedBytes,objects,readObject};bundled.set(source,result);return result;}
 let cachedRecords:Data|undefined,cachedRows:Data[]=[],cachedOpening:Data|undefined,cachedSnapshot:Data;
 const session=(descriptor:Data)=>{
  if(!keys(descriptor,'address,opening,segments')||!Array.isArray(descriptor.segments))fail();
  const opening=reference(descriptor.opening);let count=0;
  const segments=descriptor.segments.map((segment:Data)=>{
   if(!keys(segment,'bytes,count,firstSeq,sha256')||segment.firstSeq!==count||!integer(segment.count,1,512))fail();
   count+=segment.count;if(count>30000)fail();return {...reference({sha256:segment.sha256,bytes:segment.bytes}),firstSeq:segment.firstSeq,count:segment.count};
  });
  const row:Data={address:descriptor.address};
  Object.defineProperties(row,{
   opening:{enumerable:true,get(){if(cachedOpening!==descriptor){cachedSnapshot=JSON.parse(readObject(opening).toString('utf8'));cachedOpening=descriptor;}return cachedSnapshot;}},
   records:{enumerable:true,get(){
    if(cachedRecords!==descriptor){const rows:Data[]=[];
     for(const segment of segments){const part=JSON.parse(readObject(segment).toString('utf8'));if(!Array.isArray(part)||part.length!==segment.count)fail();for(let i=0;i<part.length;i++){const r=part[i];if(r?.type!=='event'||r.event?.seq!==segment.firstSeq+i)fail();rows.push(r);}}
     cachedRows=rows;cachedRecords=descriptor;
    }return cachedRows;
   }}
  });return row;
 };
 const source:Data={...document,sessions:document.sessions.map(session),relatedSessions:document.relatedSessions.map(session)};
 const attachments=document.attachments??[];if(!Array.isArray(attachments)||attachments.length>10000)fail();
 const ids=new Set<string>();for(const row of attachments){if(!keys(row,'attachmentId,bytes,sha256')||row.attachmentId!=='sha256:'+row.sha256||ids.has(row.attachmentId)||!integer(row.bytes,1,10*1024*1024))fail();ids.add(row.attachmentId);reference({sha256:row.sha256,bytes:row.bytes});}
 const files=document.files??[];if(!Array.isArray(files)||files.length>10000)fail();
 const fileIds=new Set<string>();for(const row of files){
  if(!keys(row,'attachmentId,bytes,chunks')||typeof row.attachmentId!=='string'||!/^sha256:[a-f0-9]{64}$/.test(row.attachmentId)||fileIds.has(row.attachmentId)||!integer(row.bytes,0,20*1024*1024)||!Array.isArray(row.chunks)||row.chunks.length>3)fail();
  fileIds.add(row.attachmentId);let size=0;for(const chunk of row.chunks)size+=reference(chunk).bytes;if(size!==row.bytes)fail();
 }
 const result={source,bytes,sha256,expandedBytes,objects,readObject};bundled.set(source,result);return result;
}
export function dshAttachmentBytes(source:Data,row:Data):Buffer{
 const bundle=bundled.get(source);if(bundle){if(source.schema==='augmentor-dsh-project-export/3'){const raw=dshFileBytes(source,row);if(raw.length<1||raw.length>10*1024*1024)fail();return raw;}if(!bundle.objects.has(row.sha256)||row.attachmentId!=='sha256:'+row.sha256)fail();return bundle.readObject({sha256:row.sha256,bytes:row.bytes});}
 return Buffer.from(row.data,'base64');
}
/** Files retain their complete verbatim digest across bounded object chunks. */
export function dshFileBytes(source:Data,row:Data):Buffer{
 const bundle=bundled.get(source);let raw:Buffer;
 if(!integer(row.bytes,0,20*1024*1024)||typeof row.attachmentId!=='string'||!/^sha256:[a-f0-9]{64}$/.test(row.attachmentId))fail();
 if(bundle){if(!Array.isArray(row.chunks)||row.chunks.length>3||row.chunks.some((r:Ref)=>!integer(r.bytes,1,DSH_OBJECT_BYTES))||row.chunks.reduce((n:number,r:Ref)=>n+r.bytes,0)!==row.bytes)fail();raw=Buffer.concat(row.chunks.map((ref:Ref)=>bundle.readObject(ref)));}
 else {if(typeof row.data!=='string'||row.data.length>Math.ceil(20*1024*1024/3)*4)fail();raw=Buffer.from(row.data,'base64');if(raw.toString('base64')!==row.data)fail();}
 if(raw.length!==row.bytes||raw.length>20*1024*1024||'sha256:'+hash(raw)!==row.attachmentId)fail();return raw;
}

function writeObject(dir:string,name:string,raw:Buffer){
 folder(dir);const path=join(dir,name);let fd:number|undefined;
 try{fd=openSync(path,constants.O_WRONLY|constants.O_CREAT|constants.O_EXCL|(constants.O_NOFOLLOW??0),0o600);writeFileSync(fd,raw);fsyncSync(fd);}
 catch(error){if((error as NodeJS.ErrnoException).code!=='EEXIST')throw error;if(!boundedFile(path,Math.max(raw.length,1)).equals(raw))fail();}
 finally{if(fd!==undefined)closeSync(fd);}
}
/** Copy precisely the manifest closure into an unpublished private transaction.
 * Re-open the frozen target before native projection; never trust later source edits. */
export function copyDshProjectArchive(archive:DshProjectArchive,archiveDir:string){
 try{folder(archiveDir);}catch(error){if((error as NodeJS.ErrnoException).code!=='ENOENT')throw error;privateDir(archiveDir);folder(archiveDir);}
 if(archive.objects.size){const objects=join(archiveDir,'objects');try{folder(objects);}catch(error){if((error as NodeJS.ErrnoException).code!=='ENOENT')throw error;privateDir(objects);folder(objects);}
  for(const ref of archive.objects.values())writeObject(objects,ref.sha256,archive.readObject(ref));
 }
 writeObject(archiveDir,archive.sha256+'.json',archive.bytes);
 return loadDshProjectArchive(join(archiveDir,archive.sha256+'.json'),archive.sha256,undefined,true);
}
/** Equivalent to the old JSON-array digest without building a whole-history string. */
export function dshRecordsDigest(rows:readonly Data[]){const h=createHash('sha256');h.update('[');for(let i=0;i<rows.length;i++){if(i)h.update(',');h.update(JSON.stringify(rows[i]));}return h.update(']').digest('hex');}

/** Operator/archive consumers can recover exact compressed originals. No row
 * mapping is invented and no executable parser is loaded from the archive. */
export function dshCompressedSource(source:Data,sourceId:string){
 const bundle=bundled.get(source),row=[...(source.sessions??[]),...(source.relatedSessions??[])].find((r:Data)=>r.opening.header.id===sourceId),original=row?.historicalOriginal;
 if(!bundle||source.schema!=='augmentor-dsh-project-export/3'||!original||!Array.isArray(original.chunks)||original.chunks.length>8)fail();
 const bytes=Buffer.concat(original.chunks.map((ref:Ref)=>bundle!.readObject(ref)));if(bytes.length!==original.compressedBytes||bytes.length>64*1024*1024||hash(bytes)!==original.sourceSha256)fail();return {sourceId,format:original.sourceFormat,sha256:original.sourceSha256,bytes};
}
