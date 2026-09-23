// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {MAX_FRAME,type DisplayEvent} from './index.js';

/** Page display history without retransmitting deltas already in a final reply.
 * Native engine history and the on-disk journal are never modified.
 */
export function historyPage(source:DisplayEvent[],maxMessages=12,beforeSeq?:number){
 const compact:DisplayEvent[]=[];let pending:DisplayEvent[]=[];
 for(const event of source){
  if(event.type==='assistant/chunk'){
   if(event.data.chunk?.type==='reasoning-delta'&&!event.data.chunk.text)continue;
   pending.push(event);continue;
  }
  const finalText=event.type==='assistant/message'&&event.data.message?.content?.some((p:any)=>p.type==='text'&&p.text);
  if(!finalText)compact.push(...pending);
  pending=[];compact.push(event);
 }
 compact.push(...pending);
 // Compact before applying the cursor, so paging cannot reintroduce deltas
 // belonging to a final answer on a newer page.
 const all=compact.filter(e=>beforeSeq===undefined||e.seq<beforeSeq);
 const starts=all.map((e,i)=>e.type==='user/message'?i:-1).filter(i=>i>=0);
 const count=Math.max(1,Math.min(100,Number(maxMessages)||12));
 const first=starts.length>count?starts[starts.length-count]:0;
 let index=all.length,bytes=0;
 // Reserve space for the RPC id, result envelope, separators and newline.
 const budget=MAX_FRAME-4096;
 while(index>first){
  const size=Buffer.byteLength(JSON.stringify({event:all[index-1]}))+1;
  if(bytes+size>budget){
   if(index===all.length)throw new Error('A saved display event exceeds the connection limit. The original history is preserved.');
   break;
  }
  bytes+=size;index--;
 }
 return {events:all.slice(index).map(event=>({event})),hasMore:index>0};
}
