// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from '../apps/browser/test/node_modules/jsdom/lib/api.js';
import {attachNativeHistory} from '../apps/harness/native-history.mjs';
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function fixture(t){const dom=new JSDOM('<main></main>'),previous=globalThis.document;globalThis.document=dom.window.document;t.after(()=>{globalThis.document=previous;dom.window.close();});return {dom,container:document.querySelector('main')};}
const button=(root,label)=>[...root.querySelectorAll('button')].find(element=>element.textContent===label);
const page=entries=>({available:true,entries,hasMore:false,coverage:{incompleteTailBytes:0}});
const entry=id=>({entryId:id,type:'message',role:'user',pathHash:'hash-'+id,entryHash:'entry-'+id});
const excerpt=(id,text,offset=0,hasMore=false)=>({available:true,entryId:id,pathHash:'hash-'+id,entryHash:'entry-'+id,text,offset,nextOffset:offset+text.length,length:hasMore?100:text.length+offset,hasMore});
test('native source controls reject older entry replies, retain selected excerpts on paging and label partial copies',async t=>{
 const f=fixture(t),held=[],calls=[];let history=0;
 attachNativeHistory(f.container,{sessionId:'fixture',alive:()=>true,native:{sessionId:'native-fixture',leafId:'leaf'},lineage:{entries:[{entryId:'a',type:'message',entryHash:'entry-a'},{entryId:'b',type:'message',entryHash:'entry-b'}]},rpc:(method,params)=>{
  calls.push({method,params});if(method==='session.nativeHistory')return Promise.resolve(page([entry(history++?'c':'a')]));return new Promise(resolve=>held.push({params,resolve}));
 }});
 const select=f.container.querySelector('select'),choose=id=>{select.value=id;select.dispatchEvent(new f.dom.window.Event('change'));button(f.container,'Read recorded source entry').click();};
 choose('a');choose('b');assert.equal(held[0].params.entryHash,'entry-a');assert.equal(held[1].params.entryHash,'entry-b');held[0].resolve(excerpt('a','OBSOLETE_SOURCE'));await tick();assert(!f.container.textContent.includes('OBSOLETE_SOURCE'));
 held[1].resolve(excerpt('b','FIRST_PART',0,true));await tick();assert(f.container.textContent.includes('Original entry b'));assert(button(f.container,'Copy entry excerpt'));assert.equal(button(f.container,'Copy original entry'),undefined);
 const selected=f.container.querySelector('.native-entry-viewer').textContent;button(f.container,'Read saved Pi entries').click();await tick();button(f.container,'Recent entries').click();await tick();assert.equal(f.container.querySelector('.native-entry-viewer').textContent,selected);assert.equal(f.container.querySelectorAll('[data-entry-id]').length,1);
 button(f.container,'Next excerpt').click();assert.equal(held[2].params.entryId,'b');assert.equal(held[2].params.pathHash,'hash-b');assert.equal(held[2].params.entryHash,'entry-b');assert.equal(held[2].params.offset,10);held[2].resolve(excerpt('b','LAST_PART',10));await tick();assert(button(f.container,'Copy entry excerpt'));assert.equal(button(f.container,'Next excerpt').disabled,true);
 assert(calls.every(call=>['session.nativeHistory','session.nativeRead'].includes(call.method)));assert(calls.filter(call=>call.method==='session.nativeRead').every(call=>call.params.nativeSessionId==='native-fixture'));
});
test('a native page or original excerpt arriving after a conversation change cannot modify the new view',async t=>{
 const f=fixture(t);let alive=true,reply;
 const attach=()=>attachNativeHistory(f.container,{sessionId:'old',alive:()=>alive,rpc:()=>new Promise(resolve=>reply=resolve)});
 attach();button(f.container,'Read saved Pi entries').click();alive=false;f.container.textContent='NEW_CONVERSATION';reply(page([entry('private-old')]));await tick();assert.equal(f.container.textContent,'NEW_CONVERSATION');
 alive=true;f.container.replaceChildren();attachNativeHistory(f.container,{sessionId:'old',alive:()=>alive,lineage:{entries:[{entryId:'a',type:'message'}]},rpc:()=>new Promise(resolve=>reply=resolve)});
 const select=f.container.querySelector('select');select.value='a';select.dispatchEvent(new f.dom.window.Event('change'));button(f.container,'Read recorded source entry').click();alive=false;f.container.textContent='NEW_CONVERSATION';reply(excerpt('a','OLD_PRIVATE_BODY'));await tick();assert.equal(f.container.textContent,'NEW_CONVERSATION');
});
const searchReply=(source,entries=[],hasMore=false)=>({available:true,source,sessionIdentity:source==='pi'?'native-fixture':'fixture',entries,hasMore,nextCursor:hasMore?'SIGNED_PROGRESS':undefined,coverage:{completedRecords:entries.length,sourceBytesRead:65536,indexBuildBytesRead:0,partialEntry:hasMore,incompleteTailBytes:0}});
function searchControls(f){return {query:f.container.querySelector('input[type=search]'),scope:f.container.querySelector('[aria-label="Saved history search scope"]'),set(text){this.query.value=text;this.query.dispatchEvent(new f.dom.window.Event('input'));},change(value){this.scope.value=value;this.scope.dispatchEvent(new f.dom.window.Event('change'));}};}
test('original search continues partial scans, selects distinct sources and preserves hash-guarded excerpt controls after query changes',async t=>{
 const f=fixture(t),calls=[],reads=[];let pages=0;
 attachNativeHistory(f.container,{sessionId:'fixture',alive:()=>true,native:{sessionId:'native-fixture',leafId:'leaf'},rpc:(method,params)=>{
  calls.push({method,params});if(method==='session.originalSearch')return Promise.resolve(params.source==='display'?searchReply('display',[{...entry('3'),type:'assistant/chunk',excerpt:{text:'RAW_FRAGMENT'}}]):searchReply('pi',pages++?[{...entry('a'),excerpt:{text:'SAVED_MATCH'}}]:[],pages===1));
  return new Promise(resolve=>reads.push({params,resolve}));
 }});
 const controls=searchControls(f);controls.set('literal words');button(f.container,'Search saved history').click();await tick();assert.match(f.container.querySelector('.original-search-status').textContent,/partly scanned/);assert.equal(button(f.container,'Continue saved history search').hidden,false);
 button(f.container,'Continue saved history search').click();await tick();assert.equal(calls[1].params.cursor,'SIGNED_PROGRESS');assert.equal(calls[1].params.leafId,'leaf');assert.equal(calls[1].params.nativeSessionId,'native-fixture');assert.equal(calls[1].params.scope,'selected-ancestry');assert(f.container.textContent.includes('SAVED_MATCH'));
 controls.change('all-entries');button(f.container,'Search saved history').click();await tick();assert.equal(calls.at(-1).params.scope,'all-entries');assert.equal(calls.at(-1).params.cursor,undefined);
 controls.change('display');button(f.container,'Search saved history').click();await tick();assert.equal(calls.at(-1).params.source,'display');assert.equal(calls.at(-1).params.nativeSessionId,undefined);assert.equal(calls.at(-1).params.leafId,undefined);
 f.container.querySelector('.original-search-results button').click();assert.equal(reads[0].params.source,'display');assert.equal(reads[0].params.sessionIdentity,'fixture');assert.equal(reads[0].params.entryHash,'entry-3');reads[0].resolve({...excerpt('3','FIRST',0,true),source:'display',sessionIdentity:'fixture',boundary:'Raw display fragments'});await tick();assert(f.container.textContent.includes('Original display event 3'));
 controls.set('changed query');button(f.container,'Next excerpt').click();assert.equal(reads[1].params.offset,5);assert.equal(reads[1].params.pathHash,'hash-3');assert.equal(reads[1].params.entryHash,'entry-3');controls.change('selected-ancestry');assert.match(f.container.querySelector('.native-entry-viewer').textContent,/Pending original read cancelled/);
 reads[1].resolve({...excerpt('3','STALE_RAW_FRAGMENT',5),source:'display',sessionIdentity:'fixture'});await tick();assert(!f.container.textContent.includes('STALE_RAW_FRAGMENT'));
 button(f.container,'Next excerpt').click();assert.equal(reads.length,3,'restored selected excerpt keeps working navigation');reads[2].resolve({...excerpt('3','LAST',5),source:'display',sessionIdentity:'fixture'});await tick();button(f.container,'Previous excerpt').click();assert.equal(reads[3].params.offset,0);reads[3].resolve({...excerpt('3','FIRST',0,true),source:'display',sessionIdentity:'fixture'});await tick();
});
test('changed query and source discard delayed searches and foreign original replies',async t=>{
 const f=fixture(t),held=[];attachNativeHistory(f.container,{sessionId:'fixture',alive:()=>true,native:{sessionId:'native-fixture'},rpc:(method,params)=>new Promise(resolve=>held.push({method,params,resolve}))});const controls=searchControls(f);
 controls.set('old');button(f.container,'Search saved history').click();controls.set('new');button(f.container,'Search saved history').click();held[0].resolve(searchReply('pi',[{...entry('old'),excerpt:{text:'OBSOLETE_QUERY'}}]));await tick();assert(!f.container.textContent.includes('OBSOLETE_QUERY'));
 controls.change('display');button(f.container,'Search saved history').click();held[1].resolve(searchReply('pi',[{...entry('old'),excerpt:{text:'OBSOLETE_SOURCE'}}]));held[2].resolve({...searchReply('display'),sessionIdentity:'foreign'});await tick();assert(!f.container.textContent.includes('OBSOLETE_SOURCE'));assert.match(f.container.querySelector('.original-search-status').textContent,/another source or conversation/);
 button(f.container,'Search saved history').click();held[3].resolve(searchReply('display',[{...entry('1'),excerpt:{text:'CURRENT'}}]));await tick();f.container.querySelector('.original-search-results button').click();held[4].resolve({...excerpt('1','FOREIGN_PRIVATE_BODY'),source:'pi',sessionIdentity:'native-fixture'});await tick();assert(!f.container.textContent.includes('FOREIGN_PRIVATE_BODY'));assert.match(f.container.querySelector('.native-entry-viewer').textContent,/another source or conversation/);
});
test('conversation change discards in-flight original search and original read',async t=>{
 const f=fixture(t);let alive=true,reply;const attach=()=>attachNativeHistory(f.container,{sessionId:'fixture',alive:()=>alive,rpc:()=>new Promise(resolve=>reply=resolve)});
 attach();let controls=searchControls(f);controls.set('old');controls.change('display');button(f.container,'Search saved history').click();alive=false;f.container.textContent='NEW_CONVERSATION';reply(searchReply('display',[entry('1')]));await tick();assert.equal(f.container.textContent,'NEW_CONVERSATION');
 alive=true;f.container.replaceChildren();attach();controls=searchControls(f);controls.set('old');controls.change('display');button(f.container,'Search saved history').click();reply(searchReply('display',[entry('1')]));await tick();f.container.querySelector('.original-search-results button').click();alive=false;f.container.textContent='NEW_CONVERSATION';reply({...excerpt('1','OLD_PRIVATE_BODY'),source:'display',sessionIdentity:'fixture'});await tick();assert.equal(f.container.textContent,'NEW_CONVERSATION');
});
