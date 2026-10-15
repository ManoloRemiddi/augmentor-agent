// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
export const PERMISSION_PRESETS=['read-only','workspace-write','danger-full-access'] as const;
export type PermissionPreset=typeof PERMISSION_PRESETS[number];
export interface PermissionRecord {version:1;revision:string;preset:PermissionPreset;afterSeq:number;changedAt:number|null}
export interface PermissionHolder {policy:string;permissionHistory?:PermissionRecord[]}
const uuid=/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/;
export function permissionPreset(value:unknown):PermissionPreset {if(!PERMISSION_PRESETS.includes(value as PermissionPreset))throw Error('Choose Read Only, Ask before actions or Full access.');return value as PermissionPreset;}
/** Only a complete leading human command is a permission control. */
export function permissionCommand(input:string){
 const value=input.trim();if(!/^\/permission(?:\s|$)/.test(value))return;
 const match=/^\/permission(?:\s+([^\s]+))?$/.exec(value);if(!match)throw Error('Use /permission by itself or with one supported preset.');
 return {preset:match[1]===undefined?null:permissionPreset(match[1])};
}
export function permissionHistory(holder:PermissionHolder):PermissionRecord[]{
 permissionPreset(holder.policy);
 if(holder.permissionHistory===undefined)return [{version:1,revision:'initial',preset:holder.policy as PermissionPreset,afterSeq:0,changedAt:null}];
 const history=holder.permissionHistory,ids=new Set<string>();let last=-1;
 if(!Array.isArray(history)||!history.length)throw Error('Invalid saved permission history; inspect its original metadata.');
 for(let n=0;n<history.length;n++){
  const r=history[n]!;
  if(!r||typeof r!=='object'||Array.isArray(r)||Object.keys(r).some(k=>!['version','revision','preset','afterSeq','changedAt'].includes(k))||r.version!==1||typeof r.revision!=='string'||(n===0?r.revision!=='initial':!uuid.test(r.revision))||ids.has(r.revision)||!Number.isSafeInteger(r.afterSeq)||r.afterSeq<last||(n===0&&(r.afterSeq!==0||r.changedAt!==null))||(n>0&&(!Number.isSafeInteger(r.changedAt)||r.changedAt!<0)))throw Error('Invalid saved permission history; inspect its original metadata.');
  permissionPreset(r.preset);ids.add(r.revision);last=r.afterSeq;
 }
 if(history.at(-1)!.preset!==holder.policy)throw Error('Saved permission policy and history disagree; inspect the original metadata.');
 return structuredClone(history);
}
export function permissionSelection(holder:PermissionHolder){const latest=permissionHistory(holder).at(-1)!;return {currentValue:latest.preset,revision:latest.revision};}
export function permissionChange(holder:PermissionHolder,value:unknown,expectedRevision:unknown,afterSeq:number,changedAt:number,revision:string){
 const preset=permissionPreset(value),history=permissionHistory(holder),before=history.at(-1)!;
 if(expectedRevision!==before.revision)throw Error('Permission mode changed. Refresh before choosing it again.');
 if(preset===before.preset)return {policy:preset,permissionHistory:history,outcome:'noop' as const};
 const next={version:1 as const,revision,preset,afterSeq,changedAt};const permissionHistoryNext=[...history,next];permissionHistory({policy:preset,permissionHistory:permissionHistoryNext});
 return {policy:preset,permissionHistory:permissionHistoryNext,outcome:'committed' as const};
}
/** A policy selected after a message cannot leak into a branch at that message. */
export function permissionAtBoundary(holder:PermissionHolder,messageSeq:number):PermissionHolder {
 if(!Number.isSafeInteger(messageSeq)||messageSeq<1)throw Error('Choose a recorded permission boundary.');
 const history=permissionHistory(holder).filter(r=>r.afterSeq<messageSeq),latest=history.at(-1)!;
 // The new conversation owns fresh revisions/sequence anchors. Its existing
 // fork metadata retains the parent boundary; parent policy history is untouched.
 return {policy:latest.preset};
}
export const permissionOptions=()=>[
 {value:'read-only',name:'Read Only',description:'Block new changing actions. Already running work and existing job grants are not cancelled.'},
 {value:'workspace-write',name:'Ask before actions',description:'Ask before new changing actions. Existing job grants stay unchanged.'},
 {value:'danger-full-access',name:'Full access',description:'New actions do not require per-action approval. Target scopes, existing job grants and limits still apply.'},
];
