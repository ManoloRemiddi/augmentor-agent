// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
/** Explicit private HTML execution preference; no agent or model settings. */
export function developerTools(raw:unknown):{enabled:boolean}{
  if(raw===undefined)return {enabled:true};
  if(!raw||typeof raw!=='object'||Array.isArray(raw))return {enabled:false};
  return {enabled:!Object.hasOwn(raw,'enabled')||(raw as {enabled?:unknown}).enabled===true};
}
export function developerToolsChange(ops:unknown):boolean{
  if(!Array.isArray(ops)||ops.length!==1)throw Error('Choose one HTML preview preference.');
  const op=ops[0];
  if(!op||op.op!=='set'||!Array.isArray(op.path)||op.path.length!==1||op.path[0]!=='enabled'||typeof op.value!=='boolean')throw Error('Unsupported HTML preview preference.');
  return op.value;
}
