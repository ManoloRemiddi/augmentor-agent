// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Data-only companion to a verified historical view. No original-store paths
// from a data archive are ever dereferenced here.
import {join} from 'node:path';
import {lstat,readdir} from 'node:fs/promises';
import {hash,readRegular} from './source.mjs';
const MAX_TOTAL=256*1024*1024,MAX_MANIFEST=32*1024*1024,MAX_OBJECT=16*1024*1024;
const fail=message=>{throw Error('Historical assets: '+message);};
const isObject=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const refCheck=ref=>{
 if(!isObject(ref)||Object.keys(ref).sort().join(',')!=='bytes,sha256'||!(/^[a-f0-9]{64}$/).test(ref.sha256)||!Number.isSafeInteger(ref.bytes)||ref.bytes<1||ref.bytes>MAX_OBJECT)fail('invalid bounded object reference');
 return ref;
};
/** Call the full retained-source verifier before using this data reader. It also
 * checks each read object and binds exact segment coordinates locally. */
export async function assetInventory(viewRoot){
 const raw=await readRegular(join(viewRoot,'view.json'),MAX_MANIFEST),view=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(raw));
 if(view.schema!=='augmentor-dsh-offline-project-view/1'||view.historicalOnly!==true||!Array.isArray(view.nodes)||view.nodes.length>160)fail('unsupported view');
 const originals=await readRegular(join(viewRoot,'source-family.json'),MAX_MANIFEST);if(hash(originals)!==view.sourceFamilySha256)fail('source-family binding differs');
 const family=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(originals));if(!Array.isArray(family.nodes)||family.nodes.length>160)fail('invalid family');
 let expandedBytes=raw.length+originals.length,referenceBytes=0;const images=new Map(),files=new Map(),references=[];
 const object=async ref=>{refCheck(ref);expandedBytes+=ref.bytes;if(expandedBytes>MAX_TOTAL)fail('view expanded budget exceeded');const data=await readRegular(join(viewRoot,'objects',ref.sha256),MAX_OBJECT);if(data.length!==ref.bytes||hash(data)!==ref.sha256)fail('view object checksum differs');return data;};
 for(const node of family.nodes){if(!Array.isArray(node.chunks)||node.chunks.length>8)fail('invalid source chunks');for(const ref of node.chunks)await object(ref);}
 for(const node of view.nodes){
  await object(node.header);let next=0;
  if(typeof node.sourceId!=='string'||!Array.isArray(node.segments)||node.eventCount>30000)fail('invalid view node');
  for(const segment of node.segments){
   const {firstSeq,count,...ref}=segment;if(firstSeq!==next||!Number.isSafeInteger(count)||count<1||count>512)fail('invalid segment coverage');
   const events=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(await object(ref)));if(!Array.isArray(events)||events.length!==count)fail('segment count differs');
   for(const event of events){
    if(event.seq!==next++)fail('derived coordinate gap');
    const message=event.type==='user/message'?event.data:['assistant/message','tool/result'].includes(event.type)?event.data?.message:undefined;
    if(!message)continue;if(!Array.isArray(message.content))fail('invalid message content');
    for(const [partIndex,part] of message.content.entries()){
     if(!['image','file'].includes(part?.type))continue;const attachment=part.attachment,id=attachment?.attachmentId,bytes=attachment?.bytes,kind=part.type;
     if(!isObject(attachment)||typeof id!=='string'||!/^sha256:[a-f0-9]{64}$/.test(id)||!Number.isSafeInteger(bytes)||bytes<(kind==='image'?1:0)||bytes>(kind==='image'?10:20)*1024*1024)fail('invalid asset identity or size');
     const map=kind==='image'?images:files;if(map.has(id)&&map.get(id)!==bytes)fail('conflicting asset sizes');map.set(id,bytes);if(map.size>10000)fail('asset count exceeded');
     const reference={sourceId:node.sourceId,seq:event.seq,partIndex,kind,attachment};referenceBytes+=Buffer.byteLength(JSON.stringify(reference))+1;if(referenceBytes>MAX_MANIFEST)fail('asset reference manifest exceeded');references.push(reference);
    }
   }
  }
  if(next!==node.eventCount)fail('event coverage differs');
 }
 for(const name of ['FORMAT-LICENSE','SCHEMA-REFERENCE-LICENSE','SOURCES.json'])expandedBytes+=(await readRegular(join(viewRoot,name),1024*1024)).length;
 const requests=[...images].map(([attachmentId,bytes])=>({kind:'image',attachmentId,bytes})).concat([...files].map(([attachmentId,bytes])=>({kind:'file',attachmentId,bytes})));
 const inventory={viewSha256:hash(raw),sourceFamilySha256:view.sourceFamilySha256,requests,references,viewExpandedBytes:expandedBytes};if(Buffer.byteLength(JSON.stringify(inventory))>MAX_MANIFEST)fail('asset reference manifest exceeded');
 return {view,raw,inventory};
}
/** The source view remains mandatory and immutable. Assets alone cannot grant a
 * parent a child-only attachment or make an intermediate view importable. */
export async function verifyAssets(viewRoot,assetRoot){
 for(const path of [assetRoot,join(assetRoot,'objects')]){const st=await lstat(path);if(!st.isDirectory()||st.isSymbolicLink())fail('real private directories required');}
 if(!same((await readdir(assetRoot)).sort(),['assets.json','objects']))fail('unexpected companion files');
 const {inventory}=await assetInventory(viewRoot),raw=await readRegular(join(assetRoot,'assets.json'),MAX_MANIFEST),manifest=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(raw));
 if(manifest.schema!=='augmentor-dsh-historical-assets/1'||manifest.currentHarnessImportCompatible!==false||manifest.workingFilesCaptured!==false||!same(manifest.inventory,inventory)||!Array.isArray(manifest.assets)||manifest.assets.length!==inventory.requests.length)fail('companion/view binding differs');
 const refs=new Map();let total=inventory.viewExpandedBytes+raw.length;
 for(let i=0;i<manifest.assets.length;i++){
  const row=manifest.assets[i],want=inventory.requests[i];if(!isObject(row)||Object.keys(row).sort().join(',')!=='attachmentId,bytes,chunks,kind'||row.kind!==want.kind||row.attachmentId!==want.attachmentId||row.bytes!==want.bytes||!Array.isArray(row.chunks)||row.chunks.length>3)fail('asset metadata differs');
  let size=0;const chunks=[];
  for(const ref of row.chunks){refCheck(ref);if(refs.has(ref.sha256)&&refs.get(ref.sha256)!==ref.bytes)fail('conflicting object sizes');refs.set(ref.sha256,ref.bytes);total+=ref.bytes;if(total>MAX_TOTAL||refs.size>16384)fail('combined expanded budget exceeded');const data=await readRegular(join(assetRoot,'objects',ref.sha256),MAX_OBJECT);if(data.length!==ref.bytes||hash(data)!==ref.sha256)fail('asset chunk checksum differs');size+=data.length;chunks.push(data);}
  if(size!==want.bytes||'sha256:'+hash(Buffer.concat(chunks))!==want.attachmentId)fail('complete asset checksum differs');
 }
 if(!same((await readdir(join(assetRoot,'objects'))).sort(),[...refs.keys()].sort()))fail('unreferenced asset object');
 if(!(await readRegular(join(assetRoot,'assets.json'),MAX_MANIFEST)).equals(raw))fail('companion changed during verification');
 return {manifest,raw,objects:refs,combinedExpandedBytes:total};
}
