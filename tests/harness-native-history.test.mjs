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
