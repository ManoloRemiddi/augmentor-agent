// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
/** Pi lookup binding for original DSH file rows, breadcrumbs and reference chips.
 * Values are paths, never uploaded contents or execution authority. */
export function fileReferenceSource({controller,valid,fileCandidate,crumbsFor,parseCandidate,t},scope){
 return {name:'reference',trigger:'@',showGroupTitle:false,
  async candidates(_,query){if(!valid(scope)||query.signal.aborted)return [];const rows=await controller.rpc('session.fileReferences',{sessionId:scope.sessionId,query:query.query},query.signal);if(!valid(scope)||query.signal.aborted)return [];if(!Array.isArray(rows)||rows.length>20||rows.some(r=>!r||!['file','directory'].includes(r.kind)||typeof r.path!=='string'||!r.path.length||r.path.length>4096))throw Error('Invalid file-reference candidates.');const located=crumbsFor(query.query,query.quoted===true,query.drilled,t)===undefined;return rows.flatMap(r=>fileCandidate(r,query.quoted===true,located,t));},
  header(_,q){return crumbsFor(q.query,q.quoted===true,q.drilled,t);},
  onPick({candidate,action}){if(!valid(scope))return 'handled';const v=parseCandidate(candidate.value);if(v?.kind!=='file')return undefined;if(v.fileKind==='directory'&&action==='drill')return {text:v.mention,continue:true};const mention=v.fileKind==='directory'&&v.mention.startsWith('@"')&&!v.mention.endsWith('"')?v.mention+'"':v.mention;return {insert:{source:'reference',ref:mention,label:v.label+(v.fileKind==='directory'?'/':''),appearance:v.fileKind==='directory'?'folder':'file',clipboardText:mention}};},
  codec:{clipboardText:ref=>ref,serialize:ref=>Promise.resolve(ref)},
 };
}
