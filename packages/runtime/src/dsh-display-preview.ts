// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {createHash} from 'node:crypto';
import {MAX_FRAME,type Data,type DisplayEvent} from '../../protocol/src/index.js';
/** Transport preview only. Canonical journals, source archives, branch inputs and
 * provider context retain every original byte; scoped originals remain pageable. */
export function dshDisplayPreview(event:DisplayEvent,pointer?:Data):DisplayEvent{
 if(event.data.importedFrom?.system!=='DSH'||Buffer.byteLength(JSON.stringify({event}))<MAX_FRAME-4096)return event;
 const original=JSON.stringify(event),notice='Preview of a large historical record. The complete original is preserved. In Saved conversation originals, search the Original display journal to read this entry in pages.';
 let characters=16384,nodes=2048;
 const clipped=(value:any,depth=0):any=>{
  if(--nodes<0||characters<=0||depth>12)return '[Preview omitted; full original preserved]';
  if(typeof value==='string'){const count=Math.min(value.length,characters,2048);let end=count;if(end<value.length&&end>0&&value.charCodeAt(end-1)>=0xd800&&value.charCodeAt(end-1)<=0xdbff)end--;characters-=end;return value.slice(0,end)+(end<value.length?' [Preview continues in saved original]':'');}
  if(!value||typeof value!=='object')return value;
  if(Array.isArray(value)){const out=[];for(const item of value){if(out.length>=64||nodes<=0||characters<=0)break;out.push(clipped(item,depth+1));}return out;}
  const out:Data=Object.create(null);let count=0;
  for(const key of Object.keys(value)){if(++count>64||nodes<=0||characters<=0)break;characters-=Math.min(key.length,128);out[key.slice(0,128)]=key==='arguments'&&typeof value[key]==='string'&&value[key].length>2048?JSON.stringify({historicalPreview:true,literalPrefix:clipped(value[key],depth+1),notice}):clipped(value[key],depth+1);}
  return out;
 };
 const data=clipped(event.data),marker={source:'display',entryId:String(event.seq),entryHash:createHash('sha256').update(original).digest('hex'),bytes:Buffer.byteLength(original),notice,...pointer};
 const provenance=event.data.importedFrom;data.importedFrom={system:'DSH',archiveSha256:provenance.archiveSha256,sourceSessionId:provenance.sourceSessionId,sourceSeq:provenance.sourceSeq,sourceTime:provenance.sourceTime};data.historicalDisplayPreview=marker;
 for(const key of ['turn','step','toolCallId','callId','name','isError','inputMode','inputOrigin']){const value=event.data[key];if(['string','number','boolean'].includes(typeof value))data[key]=typeof value==='string'?value.slice(0,2048):value;}
 if(event.type==='user/message'&&event.data.source?.kind)data.source={kind:String(event.data.source.kind).slice(0,128)};
 if(event.type==='turn/end'&&event.data.reason?.kind)data.reason={kind:String(event.data.reason.kind).slice(0,128)};
 const content=(original:Data[],preview:Data[])=>{
  const text={type:'text',text:String(marker.notice)},images=(Array.isArray(original)?original:[]).filter(part=>part?.type==='image'&&Buffer.byteLength(JSON.stringify(part))<=4096).slice(0,32);
  return [text,...(Array.isArray(preview)?preview:[]).filter(part=>part?.type!=='image'),...images];
 };
 if(event.type==='tool/result')data.result={...(data.result&&typeof data.result==='object'?data.result:{}),content:content(event.data.result?.content,data.result?.content)};
 if(event.type==='assistant/message')data.message={...(data.message&&typeof data.message==='object'?data.message:{}),timestamp:event.data.message?.timestamp,stopReason:String(event.data.message?.stopReason??'stop').slice(0,128),content:content(event.data.message?.content,data.message?.content)};
 if(event.type==='user/message')data.content=content(event.data.content,data.content);
 return {...event,...(event.turnId?{turnId:event.turnId.slice(0,256)}:{}),data};
}
