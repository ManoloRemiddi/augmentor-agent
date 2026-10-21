// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
export interface MetafolderDocument {v:2;groups:{id:string;name:string;color?:string}[];assignment:Record<string,string>;sessionAssignment:Record<string,string>;metaCollapsed:Record<string,boolean>;expanded:Record<string,boolean>;groupBy:'workspace'|'flat';orderBy:'manual'|'updated'}
export interface MetafolderValue {enabled:boolean;document:MetafolderDocument}
export const blankMetafolders=():MetafolderValue=>({enabled:false,document:{v:2,groups:[],assignment:{},sessionAssignment:{},metaCollapsed:{},expanded:{},groupBy:'workspace',orderBy:'manual'}});
const object=(x:unknown):x is Record<string,unknown>=>!!x&&typeof x==='object'&&!Array.isArray(x)&&[Object.prototype,null].includes(Object.getPrototypeOf(x));
const keys=(x:Record<string,unknown>,allowed:string[])=>Object.keys(x).every(k=>allowed.includes(k));
const id=(x:unknown):x is string=>typeof x==='string'&&x.length>0&&x.length<=4096&&!/[\u0000-\u001f]/.test(x)&&!['__proto__','prototype','constructor'].includes(x);
/** Display metadata only; workspace IDs can contain paths. No move, model or tool authority. */
export function checkedMetafolders(value:unknown):MetafolderValue {
 const bad=()=>{throw Error('Metafolder display metadata is invalid or exceeds its bound.');};
 if(!object(value)||!keys(value,['enabled','document'])||typeof value.enabled!=='boolean'||!object(value.document))return bad();
 const d=value.document;
 if(!keys(d,['v','groups','assignment','sessionAssignment','metaCollapsed','expanded','groupBy','orderBy'])||d.v!==2||!Array.isArray(d.groups)||d.groups.length>128||!['workspace','flat'].includes(d.groupBy as string)||!['manual','updated'].includes(d.orderBy as string))return bad();
 const seen=new Set<string>();
 for(const g of d.groups){if(!object(g)||!keys(g,['id','name','color'])||!id(g.id)||seen.has(g.id)||typeof g.name!=='string'||!g.name.trim()||g.name.length>200||/[\u0000-\u001f]/.test(g.name)||g.color!==undefined&&(typeof g.color!=='string'||!/^#(?:[a-f\d]{3}|[a-f\d]{4}|[a-f\d]{6}|[a-f\d]{8})$/i.test(g.color)))return bad();seen.add(g.id);}
 for(const field of ['assignment','sessionAssignment','metaCollapsed','expanded']){const map=d[field];if(!object(map)||Object.keys(map).length>4096)return bad();for(const [k,v] of Object.entries(map))if(!(id(k)||field==='expanded'&&k==='')||(field==='assignment'||field==='sessionAssignment'?!id(v):typeof v!=='boolean'))return bad();}
 const raw=JSON.stringify(value);if(new TextEncoder().encode(raw).length>64*1024)return bad();
 return JSON.parse(raw) as MetafolderValue;
}
