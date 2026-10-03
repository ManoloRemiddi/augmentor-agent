// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
/** Selection evidence only; shared by the embedded receiver and the DSH pipe. */
export function snapshotWorkspaceContext(value) {
  if(!value||typeof value!=='object'||Array.isArray(value))throw Error('Workspace context must be an object of at most 16 KB');
  let encoded;try{encoded=JSON.stringify(value);}catch{throw Error('Workspace context must be JSON serializable');}
  if(typeof encoded!=='string'||new TextEncoder().encode(encoded).length>16000)throw Error('Workspace context exceeds 16 KB');
  const snapshot=JSON.parse(encoded);
  if(!snapshot||typeof snapshot!=='object'||Array.isArray(snapshot))throw Error('Workspace context must serialize to an object');
  function depth(item,level=0){if(level>64)throw Error('Workspace context exceeds 64 nested levels');if(item&&typeof item==='object')for(const value of Object.values(item))depth(value,level+1);}
  depth(snapshot);return snapshot;
}
