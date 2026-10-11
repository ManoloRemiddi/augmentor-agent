// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
const node=(tag,text)=>{const element=document.createElement(tag);if(text!==undefined)element.textContent=text;return element;};
/** Search only managed originals, with bounded pages and invalidated reply epochs. */
export function attachOriginalSearch(container,{rpc,sessionId,alive,identity,selected,open,invalidateRead}){
 const controls=node('div'),query=node('input'),scope=node('select'),search=node('button','Search saved history'),more=node('button','Continue saved history search'),status=node('p'),results=node('div');
 controls.className='original-search-controls';status.className='original-search-status';results.className='original-search-results native-entry-page';query.type='search';query.maxLength=256;query.placeholder='Literal words in saved originals';query.setAttribute('aria-label','Search saved conversation originals');scope.setAttribute('aria-label','Saved history search scope');
 for(const [value,label] of [['selected-ancestry','Selected Pi ancestry'],['all-entries','All entries in this saved Pi file'],['display','Original display journal']]){const option=node('option',label);option.value=value;scope.append(option);}
 search.disabled=true;more.hidden=true;controls.append(query,scope,search,more);container.append(node('h4','Search saved originals'),controls,node('p','Search matches literal words in serialized originals. The display journal includes streamed fragments compacted out of Chat. These records do not reconstruct effective model context. Building or rebuilding an index reads the saved file; subsequent search pages verify bounded source blocks.'),status,results);
 let epoch=0,cursor,completed=0;
 const invalidate=()=>{++epoch;cursor=undefined;completed=0;more.hidden=true;search.disabled=!query.value.trim();status.textContent=results.childElementCount?'Search changed; these results belong to the previous search.':'';invalidateRead();};
 query.oninput=invalidate;scope.onchange=invalidate;
 const run=async(reset)=>{
  if(!alive()||!query.value.trim())return;
  if(reset){cursor=undefined;completed=0;invalidateRead();}
  const current=++epoch,source=scope.value==='display'?'display':'pi',searchScope=source==='display'?'all-entries':scope.value,expected=source==='display'?sessionId:identity.nativeSessionId;
  search.disabled=true;more.disabled=true;status.textContent='Searching saved originals…';
  try{
   const result=await rpc('session.originalSearch',{sessionId,source,scope:searchScope,query:query.value,limit:50,...(source==='pi'?identity:{}),...(cursor?{cursor}:{})});
   if(!alive()||current!==epoch)return;
   if(!result.available){status.textContent=result.reason;more.hidden=true;return;}
   if(result.source!==source||(expected&&result.sessionIdentity!==expected))throw Error('Search reply belongs to another source or conversation.');
   completed+=result.coverage.completedRecords;status.textContent=result.entries.length+' matches on this page · '+completed.toLocaleString()+' entries searched in '+(source==='display'?'the original display journal':searchScope==='all-entries'?'all saved Pi branches':'the selected Pi ancestry')+' · '+result.coverage.sourceBytesRead.toLocaleString()+' verified bytes this page'+(result.coverage.indexBuildBytesRead?' · '+result.coverage.indexBuildBytesRead.toLocaleString()+' bytes read to build the index':'')+(result.coverage.partialEntry?' · one original is partly scanned':'')+(result.coverage.incompleteTailBytes?' · incomplete tail preserved':'')+(result.hasMore?' · continue to search more originals.':' · saved range complete.');
   results.replaceChildren(...result.entries.map(entry=>{const row=node('div'),button=node('button',(entry.role||entry.type)+' · '+entry.entryId),preview=node('pre',entry.excerpt?.text||'');button.dataset.entryId=entry.entryId;button.dataset.source=source;const selection=selected();button.classList.toggle('selected',selection.source===source&&selection.id===entry.entryId);button.onclick=()=>{if(alive())open(entry,source,result.sessionIdentity);};row.append(button,preview);return row;}));
   cursor=result.nextCursor;more.hidden=!result.hasMore;more.disabled=false;
  }catch(error){if(alive()&&current===epoch){status.textContent=error.message;more.hidden=true;}}
  finally{if(alive()&&current===epoch)search.disabled=!query.value.trim();}
 };
 query.onkeydown=event=>{if(event.key==='Enter'){event.preventDefault();void run(true);}};search.onclick=()=>void run(true);more.onclick=()=>void run(false);
 return container;
}
