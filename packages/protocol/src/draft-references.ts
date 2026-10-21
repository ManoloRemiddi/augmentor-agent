// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
export interface DraftReference {source:'reference';ref:string;label:string;appearance:'file'|'folder';clipboardText:string;offset:number;length:number;invalid?:boolean}
/** Original DSH clipboard-plane file chips; no path lookup, content read or
 * execution grant. Runtime node keys and occurrence IDs are never persisted. */
export function draftReferences(text:string,value:unknown):DraftReference[]{
 if(value===undefined)return [];
 if(!Array.isArray(value)||value.length>256)throw Error('Invalid saved draft references.');
 let end=0;
 for(const r of value){
  if(!r||typeof r!=='object'||Object.keys(r).some(k=>!['source','ref','label','appearance','clipboardText','offset','length','invalid'].includes(k))||r.source!=='reference'||!['file','folder'].includes(r.appearance)||typeof r.ref!=='string'||r.ref.length>4096||r.clipboardText!==r.ref||typeof r.label!=='string'||r.invalid!==undefined&&typeof r.invalid!=='boolean'||!Number.isSafeInteger(r.offset)||!Number.isSafeInteger(r.length)||r.offset<end||r.length!==r.ref.length||text.slice(r.offset,r.offset+r.length)!==r.ref)throw Error('Invalid saved draft reference span.');
  const match=/^@(?:"([^"\u0000-\u001f\u007f-\u009f]+)"|([^\s"\u0000-\u001f\u007f-\u009f]+))$/u.exec(r.ref),path=match?.[1]??match?.[2];
  if(!path||path.endsWith('/')!==(r.appearance==='folder'))throw Error('Invalid saved draft file mention.');
  const base=(r.appearance==='folder'?path.slice(0,-1):path).split('/').at(-1);
  if(!base||r.label!==base+(r.appearance==='folder'?'/':''))throw Error('Invalid saved draft reference label.');
  end=r.offset+r.length;
 }
 return structuredClone(value);
}
