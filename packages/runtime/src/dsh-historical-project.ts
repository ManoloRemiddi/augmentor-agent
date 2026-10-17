// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Explicit v3 archive tier: original compressed sources, derived event segments
// and referenced assets share one named closure. No archive code is executed.
import {createHash} from 'node:crypto';
import {isDeepStrictEqual} from 'node:util';
import {identifier,type Data} from '../../protocol/src/index.js';
type Ref={sha256:string;bytes:number};
const hash=(raw:Buffer)=>createHash('sha256').update(raw).digest('hex');
const fail=():never=>{throw Error('DSH historical archive provenance, family, coordinates or asset binding differs. Originals are preserved.');};
const integer=(v:unknown,min:number,max:number)=>typeof v==='number'&&Number.isSafeInteger(v)&&v>=min&&v<=max;
const exact=(v:Data,keys:string)=>v&&typeof v==='object'&&!Array.isArray(v)&&Object.keys(v).sort().join(',')===keys;
const digest=(v:unknown)=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v);
const same=(a:unknown,b:unknown)=>isDeepStrictEqual(a,b);
export const DSH_DERIVED_COORDINATES='derived-dsh-v4';
/** The trusted operator recomputes the view before producing this envelope.
 * Runtime admission checks the expected envelope hash and its entire data-only
 * closure; processing fingerprints are provenance, never executable authority. */
export function historicalProject(document:Data,reference:(v:Data)=>Ref,read:(v:Ref)=>Buffer){
 if(!exact(document,'assets,coordinates,notices,profile,schema,sourceFamily,view')||document.profile!=='augmentor-dsh-historical-family/1'||document.coordinates!==DSH_DERIVED_COORDINATES)fail();
 const viewRef=reference(document.view),familyRef=reference(document.sourceFamily),assetRef=reference(document.assets);
 const decode=(ref:Ref):any=>JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(read(ref)));
 const view=decode(viewRef),family=decode(familyRef),assets=decode(assetRef);
 if(view.schema!=='augmentor-dsh-offline-project-view/1'||view.profile!=='augmentor-dsh-historical-family/1'||view.historicalOnly!==true||view.currentHarnessImportCompatible!==false||view.completePhysicalFamily!==true||view.completeCatalogCoverage!==true||view.originalCompressedSourcesRetained!==true||view.attachmentsCaptured!==false||view.workingFilesCaptured!==false||view.sourceFamilySha256!==familyRef.sha256||view.sourceFamilyFile!=='source-family.json'||!same(view.workspace,family.workspace)||!same(view.organization,family.organization)||!same(view.sourceWitness,family.sourceWitness)||!same(view.roots,family.roots))fail();
 if(family.schema!=='augmentor-dsh-source-family/1'||family.attachmentsCaptured!==false||family.sourceWitness?.membershipStable!==true||!integer(family.sourceWitness.headerCount,1,10000)||!digest(family.sourceWitness.headerIndexSha256)||!Array.isArray(family.roots)||!family.roots.length||family.roots.length>128||new Set(family.roots).size!==family.roots.length||!same(family.roots,family.workspace?.sessionIds)||!Array.isArray(family.nodes)||family.nodes.length>family.roots.length+32||!Array.isArray(view.nodes)||family.nodes.length!==view.nodes.length)fail();
 if(assets.schema!=='augmentor-dsh-historical-assets/1'||assets.currentHarnessImportCompatible!==false||assets.workingFilesCaptured!==false||assets.inventory?.viewSha256!==viewRef.sha256||assets.inventory?.sourceFamilySha256!==familyRef.sha256||!Array.isArray(assets.assets)||assets.assets.length>20000)fail();
 const owned=['adapters/dsh-legacy-format/restore.ts','adapters/dsh-legacy-format/descriptor-v2.mjs','adapters/dsh-legacy-format/build.mjs','adapters/dsh-legacy-format/family.mjs','adapters/dsh-legacy-format/source.mjs','scripts/export-dsh-legacy-view.mjs'];
 if(view.normalization?.supplierRevision!=='d743267388641bc76f17c45ce8b4c231aed1d32c'||!digest(view.normalization.compatibilityBundleSha256)||!digest(view.normalization.supplierSourceLedgerSha256)||!view.normalization.ownedSources||!same(Object.keys(view.normalization.ownedSources).sort(),owned.sort())||Object.values(view.normalization.ownedSources).some(v=>!digest(v)))fail();
 const noticeNames=['FORMAT-LICENSE','SCHEMA-REFERENCE-LICENSE','SOURCES.json'];
 if(!Array.isArray(document.notices)||document.notices.length!==noticeNames.length)fail();
 const noticeRefs=document.notices.map((row:Data,i:number)=>{if(!exact(row,'name,object')||row.name!==noticeNames[i])fail();return reference(row.object);});
 if(noticeRefs[2]!.sha256!==view.normalization.supplierSourceLedgerSha256)fail();
 const ledger=decode(noticeRefs[2]!);if(ledger.revision!==view.normalization.supplierRevision||ledger.license!=='MIT'||!Array.isArray(ledger.files)||ledger.files.length!==52||ledger.legacyDescriptorSchema?.license!=='BSD-3-Clause'||noticeRefs[0]!.sha256!==ledger.files.find((f:Data)=>f.path==='LICENSE')?.sha256||noticeRefs[1]!.sha256!==ledger.legacyDescriptorSchema.licenseSha256)fail();
 const roots=new Set<string>(family.roots),originals=new Map<string,Data>(),nodes=new Map<string,Data>(),headers=new Map<string,Data>(),segments=new Map<string,(Ref&{firstSeq:number;count:number})[]>(),titles=new Map<string,string>();
 // Count each original logical reference even when its disk object is shared.
 for(const original of family.nodes){
  const id=original?.header?.id;identifier(id);
  if(originals.has(id)||!integer(original.version,0,4)||original.version!==original.header.version||!digest(original.sourceSha256)||!digest(original.headerSha256)||!integer(original.compressedBytes,1,64*1024*1024)||!Array.isArray(original.chunks)||original.chunks.length<1||original.chunks.length>8)fail();
  if(roots.has(id)?original.relation!=='root'||original.header.origin==='subagent'||original.header.cwd!==family.workspace.path:original.relation!=='subagent'||original.header.origin!=='subagent'||typeof original.header.parentSession!=='string')fail();
  const h=createHash('sha256');let length=0;for(const value of original.chunks){const ref=reference(value),raw=read(ref);length+=raw.length;h.update(raw);}if(length!==original.compressedBytes||h.digest('hex')!==original.sourceSha256)fail();originals.set(id,original);
 }
 for(const id of roots)if(!originals.has(id))fail();
 for(const [id,original] of originals){let at=id;const seen=new Set<string>();while(!roots.has(at)){if(seen.has(at)||!originals.has(at))fail();seen.add(at);at=originals.get(at)!.header.parentSession;}if(!integer(original.header.createdAt,0,Number.MAX_SAFE_INTEGER))fail();}
 for(const node of view.nodes){
  const id=node.sourceId,original=originals.get(id)!;if(!original||nodes.has(id)||node.sourceSha256!==original.sourceSha256||node.sourceFormat!==original.version||node.viewFormat!==4||node.viewCoordinates!=='derived current-format coordinates; original physical log retained separately'||!integer(node.eventCount,0,30000)||!integer(node.inheritedEventCount,0,node.eventCount)||!Array.isArray(node.segments))fail();
  const header=decode(reference(node.header));if(header.id!==id||header.version!==4||header.parentSession!==original.header.parentSession||header.origin!==original.header.origin||header.cwd!==original.header.cwd||header.createdAt!==original.header.createdAt)fail();
  let next=0;const refs=node.segments.map((value:Data)=>{if(!exact(value,'bytes,count,firstSeq,sha256')||value.firstSeq!==next||!integer(value.count,1,512))fail();next+=value.count;const ref=reference({bytes:value.bytes,sha256:value.sha256});return {...ref,firstSeq:value.firstSeq,count:value.count};});if(next!==node.eventCount)fail();
  nodes.set(id,node);headers.set(id,header);segments.set(id,refs);
 }
 let cachedId:string|undefined,cachedRows:Data[]=[];
 const rows=(id:string)=>{
  if(cachedId!==id){const result:Data[]=[];for(const segment of segments.get(id)!){const part=decode(segment);if(!Array.isArray(part)||part.length!==segment.count)fail();for(let i=0;i<part.length;i++){const event=part[i];if(event?.seq!==segment.firstSeq+i||!integer(event.time,0,Number.MAX_SAFE_INTEGER)||typeof event.type!=='string'||!event.data||typeof event.data!=='object'||Array.isArray(event.data))fail();result.push({type:'event',event});}}cachedId=id;cachedRows=result;}return cachedRows;
 };
 const children=new Map<string,{parent:string;mode:string}>(),imageRequests=new Map<string,number>(),fileRequests=new Map<string,number>(),occurrences:Data[]=[];let occurrenceBytes=0;
 for(const [id,node] of nodes){
  const direct:string[]=[];
  for(const {event:e} of rows(id)){
   if(e.type==='session/title'&&typeof e.data.title==='string')titles.set(id,e.data.title);
   if(e.type==='subagent/catalog'){
    const child=e.data.childId,mode=e.data.mode,original=originals.get(child);if(!original||roots.has(child)||original.header.parentSession!==id||typeof mode!=='string'||!mode||mode.length>128)fail();const previous=children.get(child);if(previous&&(previous.parent!==id||previous.mode!==mode))fail();children.set(child,{parent:id,mode});direct.push(child);
   }
   const message=e.type==='user/message'?e.data:['assistant/message','tool/result'].includes(e.type)?e.data.message:undefined;if(!message)continue;if(!Array.isArray(message.content))fail();
   for(const [partIndex,part] of message.content.entries())if(['image','file'].includes(part?.type)){
    const a=part.attachment,kind=part.type,map=kind==='image'?imageRequests:fileRequests;
    if(!a||typeof a.attachmentId!=='string'||!/^sha256:[a-f0-9]{64}$/.test(a.attachmentId)||!integer(a.bytes,kind==='image'?1:0,(kind==='image'?10:20)*1024*1024)||map.has(a.attachmentId)&&map.get(a.attachmentId)!==a.bytes)fail();map.set(a.attachmentId,a.bytes);if(map.size>10000)fail();
    const occurrence={sourceId:id,seq:e.seq,partIndex,kind,attachment:a};occurrenceBytes+=Buffer.byteLength(JSON.stringify(occurrence))+1;if(occurrenceBytes>32*1024*1024)fail();occurrences.push(occurrence);
   }
  }
  const facts=node.directChildFacts;if(!Array.isArray(facts)||facts.length>32||new Set(facts.map((f:Data)=>f.childId)).size!==facts.length||!same([...new Set(direct)].sort(),facts.map((f:Data)=>f.childId).sort())||facts.some((f:Data)=>f.childCreatedAt!==originals.get(f.childId)?.header.createdAt))fail();
 }
 if(children.size!==originals.size-roots.size||family.sourceWitness.headerCount<originals.size)fail();
 const requests=[...imageRequests].map(([attachmentId,bytes])=>({kind:'image',attachmentId,bytes})).concat([...fileRequests].map(([attachmentId,bytes])=>({kind:'file',attachmentId,bytes})));
 if(!same(assets.inventory.requests,requests)||!same(assets.inventory.references,occurrences)||assets.assets.length!==requests.length)fail();
 const attachments:Data[]=[],files:Data[]=[];
 for(let i=0;i<requests.length;i++){
  const row=assets.assets[i],want=requests[i]!;if(!exact(row,'attachmentId,bytes,chunks,kind')||row.kind!==want.kind||row.attachmentId!==want.attachmentId||row.bytes!==want.bytes||!Array.isArray(row.chunks)||row.chunks.length>3)fail();
  const h=createHash('sha256');let length=0;for(const value of row.chunks){const ref=reference(value),raw=read(ref);length+=raw.length;h.update(raw);}if(length!==row.bytes||'sha256:'+h.digest('hex')!==row.attachmentId)fail();
  (want.kind==='image'?attachments:files).push({attachmentId:row.attachmentId,bytes:row.bytes,chunks:row.chunks});
 }
 for(const key of ['archivedSessionIds','pinnedSessionIds']){const value=family.organization?.[key];if(!Array.isArray(value)||new Set(value).size!==value.length||value.some((id:unknown)=>typeof id!=='string'||!roots.has(id)))fail();}
 const derivation={coordinates:DSH_DERIVED_COORDINATES,viewSha256:viewRef.sha256,sourceFamilySha256:familyRef.sha256,supplierRevision:view.normalization.supplierRevision,originalCompressedSourcesRetained:true,physicalRowMapping:'No one-to-one physical-row mapping; derived event coordinates use the retained v4 view'};
 const session=(id:string)=>{
  const original=originals.get(id)!,child=children.get(id),node=nodes.get(id)!;
  const row:Data={address:child?{kind:'subagent',parentSessionId:child.parent,childSessionId:id,mode:child.mode}:{kind:'session',sessionId:id},historicalOriginal:{sourceFormat:original.version,sourceSha256:original.sourceSha256,compressedBytes:original.compressedBytes,chunks:original.chunks},historicalDerivation:derivation};
  Object.defineProperties(row,{
   opening:{enumerable:true,get(){const title=titles.get(id);return {header:headers.get(id),cursor:node.eventCount-1,projections:{values:typeof title==='string'?{title}:{}}};}},
   records:{enumerable:true,get(){return rows(id);}},
  });return row;
 };
 // Avoid retaining the last validation pass's large history until first read.
 cachedId=undefined;cachedRows=[];
 return {schema:document.schema,workspace:family.workspace,sessions:family.roots.map(session),relatedSessions:[...nodes.keys()].filter(id=>!roots.has(id)).map(session),archivedSessionIds:family.organization.archivedSessionIds,pinnedSessionIds:family.organization.pinnedSessionIds,attachments,files,historicalDerivation:derivation};
}
