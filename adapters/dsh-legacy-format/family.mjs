// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {isAbsolute,resolve} from 'node:path';
import {isDeepStrictEqual} from 'node:util';
const fail=message=>{throw Error('Offline DSH family: '+message);};
/** Bind complete physical membership independently of catalog/model metadata. */
export function bindFamily(snapshot,decodeHeader){
 if(snapshot?.schema!=='augmentor-dsh-source-family/1'||!Array.isArray(snapshot.roots)||!snapshot.roots.length||snapshot.roots.length>128||new Set(snapshot.roots).size!==snapshot.roots.length||!Array.isArray(snapshot.nodes)||snapshot.nodes.length>snapshot.roots.length+32||!isDeepStrictEqual(snapshot.roots,snapshot.workspace?.sessionIds)||snapshot.sourceWitness?.membershipStable!==true||!(/^[a-f0-9]{64}$/).test(snapshot.sourceWitness.headerIndexSha256)||!Number.isSafeInteger(snapshot.sourceWitness.headerCount)||snapshot.sourceWitness.headerCount<snapshot.nodes.length||snapshot.sourceWitness.headerCount>10000||typeof snapshot.workspace.path!=='string'||!isAbsolute(snapshot.workspace.path)||resolve(snapshot.workspace.path)!==snapshot.workspace.path||typeof snapshot.workspace.title!=='string'||!snapshot.workspace.title.trim())fail('invalid bounded source-family receipt');
 const roots=new Set(snapshot.roots),nodes=new Map(),headers=new Map();
 for(const key of ['archivedSessionIds','pinnedSessionIds']){const ids=snapshot.organization?.[key];if(!Array.isArray(ids)||new Set(ids).size!==ids.length||ids.some(id=>!roots.has(id)))fail('source organization differs');}
 for(const node of snapshot.nodes){
  const header=decodeHeader(node.header),id=header.id;
  if(typeof id!=='string'||!id||nodes.has(id)||header.version!==node.version||!Number.isSafeInteger(node.compressedBytes)||node.compressedBytes<1||node.compressedBytes>64*1024*1024||!(/^[a-f0-9]{64}$/).test(node.sourceSha256)||!(/^[a-f0-9]{64}$/).test(node.headerSha256))fail('source identity/version is ambiguous');
  if(roots.has(id)?node.relation!=='root'||header.origin==='subagent':node.relation!=='subagent'||header.origin!=='subagent'||typeof header.parentSession!=='string')fail('source parent relation is invalid');
  nodes.set(id,node);headers.set(id,header);
 }
 for(const id of roots)if(!nodes.has(id))fail('a declared root is absent');
 for(const [id,h] of headers){let at=id;const seen=new Set();while(!roots.has(at)){if(seen.has(at)||!headers.has(at))fail('source family is cyclic or orphaned');seen.add(at);at=headers.get(at).parentSession;}if(roots.has(id)&&h.cwd!==snapshot.workspace.path)fail('a source root belongs to another working directory');}
 const direct=new Map([...nodes.keys()].map(id=>[id,[]]));for(const [id,h] of headers)if(!roots.has(id))direct.get(h.parentSession).push(id);
 return {roots,nodes,headers,direct};
}
/** Read each child historically before the v4 edge, then supply only its actual
 * direct parent with own-descriptor facts. No recursive Session/Host is created. */
export async function normalizeFamily(snapshot,api,loadRows,saveView){
 const bound=bindFamily(snapshot,api.decodeHeaderValue),facts=new Map();
 const read=async id=>{const rows=await loadRows(bound.nodes.get(id));if(!Array.isArray(rows)||!rows.length||!isDeepStrictEqual(api.decodeHeaderValue(rows[0]),bound.headers.get(id)))fail('raw source header differs from its receipt');return rows;};
 for(const [id,h] of bound.headers)if(!bound.roots.has(id)){
  const historical=api.restoreHistoricalRows(await read(id)),fact=api.childCatalogEvidence(historical);
  if(historical.header.id!==id||historical.header.parentSession!==h.parentSession||fact.childId!==id||fact.childCreatedAt!==h.createdAt)fail('historical child evidence changed identity');facts.set(id,fact);
 }
 const result=[];
 for(const [id,node] of bound.nodes){
  const evidence=bound.direct.get(id).map(child=>facts.get(child)),artifact=api.restoreRows(await read(id),evidence);
  if(artifact.header.id!==id||artifact.header.version!==4||artifact.events.length>30000||artifact.events.some((event,index)=>event.seq!==index))fail('derived view exceeds its complete current-coordinate bound');
  const declared=artifact.events.filter(e=>e.type==='subagent/catalog').map(e=>e.data.childId),direct=bound.direct.get(id);
  // Report incomplete modern catalog coverage explicitly. The caller must not
  // publish this as a complete project view or borrow other projects' logs.
  const missing=declared.filter(child=>!bound.nodes.has(child)||bound.headers.get(child).parentSession!==id),uncatalogued=direct.filter(child=>!declared.includes(child));
  if(missing.length||uncatalogued.length)fail('recorded catalog and complete physical membership differ');
  result.push(await saveView(node,artifact,{directChildFacts:evidence,descriptorCount:artifact.events.filter(e=>e.type==='subagent/descriptor'&&e.seq>=artifact.inheritedEventCount).length}));
 }
 return {roots:snapshot.roots,nodes:result,completePhysicalFamily:true,completeCatalogCoverage:true,originalSourceRequired:true,historicalOnly:true,agentOrHostCreated:false,modelRequests:0};
}
