// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {attachOriginalSearch} from './original-search.mjs';
const node=(tag,text)=>{const element=document.createElement(tag);if(text!==undefined)element.textContent=text;return element;};
/** Bounded pages/excerpts from original conversation storage. No inference or
 * reconstruction of an uncaptured effective request. Keep selection on paging.
 */
export function attachNativeHistory(container,{rpc,sessionId,alive,native,lineage}){
 const section=node('section'),list=node('div'),status=node('p'),viewer=node('div'),load=node('button','Read saved Pi entries'),recent=node('button','Recent entries'),older=node('button','Earlier entries');
 section.className='native-history';list.className='native-entry-page';viewer.className='native-entry-viewer';
 section.append(node('h3','Saved conversation originals'),node('p','These originals come from saved conversation history, including when context capture was off. Edits and added instructions can change what reaches the model.'),load,recent,older,status,list,viewer);container.append(section);recent.hidden=true;older.hidden=true;
 let pageEpoch=0,readEpoch=0,cursor,selectedId,selectedSource='pi',reading=false,displayed;
 const identity={...(native?.sessionId?{nativeSessionId:native.sessionId}:{}),...(native?.leafId!==undefined?{leafId:native.leafId}:{})};
 const mark=()=>section.querySelectorAll('button[data-entry-id]').forEach(button=>button.classList.toggle('selected',button.dataset.entryId===selectedId&&(button.dataset.source||'pi')===selectedSource));
 const render=record=>{
  const {id,at,result,original,offsets}=record,text=node('pre',result.text),copy=node('button',result.hasMore||at>0?'Copy entry excerpt':'Copy original entry'),next=node('button','Next excerpt'),previous=node('button','Previous excerpt');
  copy.onclick=()=>navigator.clipboard.writeText(result.text).catch(error=>{if(alive())status.textContent=error.message;});
  next.disabled=!result.hasMore;previous.disabled=!offsets.length;
  const current=()=>alive()&&!reading&&displayed===record;
  next.onclick=()=>{if(current())void read(id,result.pathHash,result.entryHash,result.nextOffset,original,[...offsets,at]);};
  previous.onclick=()=>{if(current())void read(id,result.pathHash,result.entryHash,offsets.at(-1),original,offsets.slice(0,-1));};
  viewer.replaceChildren(node('h4',(original?.source==='display'?'Original display event ':'Original entry ')+id),...(original?[node('p',result.boundary)]:[]),node('p','Bytes '+at.toLocaleString()+'–'+result.nextOffset.toLocaleString()+' of '+result.length.toLocaleString()+(result.hasMore?' · excerpt; more bytes remain':'')),text,copy,previous,next);mark();
 };
 const read=async(id,pathHash,entryHash,at=0,original,offsets=[])=>{
  const epoch=++readEpoch;reading=true;selectedId=id;selectedSource=original?.source||'pi';const params={sessionId,entryId:id,offset:at,...(original?original:identity.nativeSessionId?{nativeSessionId:identity.nativeSessionId}:{}),...(pathHash?{pathHash}:{}),...(entryHash?{entryHash}:{})};
  viewer.replaceChildren(node('p','Reading saved entry…'));
  try{
   const result=await rpc(original?'session.originalRead':'session.nativeRead',params);if(!alive()||epoch!==readEpoch)return;
   reading=false;if(!result.available){displayed=undefined;viewer.replaceChildren(node('p',result.reason));return;}
   if(result.entryId!==id||(original&&(result.source!==original.source||result.sessionIdentity!==original.sessionIdentity)))throw Error('Original entry reply belongs to another source or conversation.');
   displayed={id,at,result,original,offsets};render(displayed);
  }catch(error){if(alive()&&epoch===readEpoch){reading=false;displayed=undefined;viewer.replaceChildren(node('p',error.message));}}
 };
 const page=async(reset=false)=>{
  const epoch=++pageEpoch;load.disabled=true;older.disabled=true;
  try{
   const result=await rpc('session.nativeHistory',{sessionId,limit:50,...identity,...(!reset&&cursor?{cursor}:{})});if(!alive()||epoch!==pageEpoch)return;
   if(!result.available){status.textContent=result.reason;return;}
   status.textContent=result.entries.length+' saved entries on the selected ancestry'+(result.coverage.incompleteTailBytes?' · incomplete tail preserved':'')+'.';
   // Only the current metadata page is rendered. The independent selected
   // excerpt stays attached while older pages replace these bounded buttons.
   list.replaceChildren(...result.entries.map(entry=>{const button=node('button',(entry.role||entry.type)+' · '+entry.entryId);button.dataset.entryId=entry.entryId;button.classList.toggle('selected',selectedSource==='pi'&&entry.entryId===selectedId);button.onclick=()=>void read(entry.entryId,entry.pathHash,entry.entryHash);return button;}));
   cursor=result.nextCursor;recent.hidden=false;older.hidden=false;older.disabled=!result.hasMore;
  }catch(error){if(alive()&&epoch===pageEpoch)status.textContent=error.message;}finally{if(alive()&&epoch===pageEpoch)load.disabled=false;}
 };
 load.onclick=()=>void page(true);recent.onclick=()=>void page(true);older.onclick=()=>void page();
 if(lineage?.entries?.length){
  const select=node('select'),open=node('button','Read recorded source entry');select.setAttribute('aria-label','Recorded native source entry');
  select.append(node('option','Choose a recorded source entry'));select.firstChild.value='';
  for(const entry of lineage.entries.slice(0,200)){const option=node('option',entry.type+' · '+entry.entryId);option.value=entry.entryId;select.append(option);}
  open.disabled=true;select.onchange=()=>{open.disabled=!select.value;};open.onclick=()=>void read(select.value,undefined,lineage.entries.find(entry=>entry.entryId===select.value)?.entryHash);section.insertBefore(select,status);section.insertBefore(open,status);
  if(lineage.entries.length>200)section.insertBefore(node('p','The first 200 recorded sources are listed. Use saved-entry pages to browse the full ancestry.'),status);
 }
 const search=node('div');section.insertBefore(search,viewer);
 attachOriginalSearch(search,{rpc,sessionId,alive,identity,selected:()=>({id:selectedId,source:selectedSource}),open:(entry,source,sessionIdentity)=>void read(entry.entryId,entry.pathHash,entry.entryHash,0,{source,sessionIdentity}),invalidateRead:()=>{
  if(!reading)return;++readEpoch;reading=false;if(displayed){selectedId=displayed.id;selectedSource=displayed.original?.source||'pi';render(displayed);}else viewer.replaceChildren();viewer.append(node('p','Pending original read cancelled after the search changed.'));
 }});
 return section;
}
