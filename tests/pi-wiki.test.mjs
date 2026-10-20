// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Actual supported Pi owner, original public wiki operation bodies, independent temporary vault.
import test from 'node:test';import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';import {once} from 'node:events';
import {readFile,readdir,stat} from 'node:fs/promises';import {join} from 'node:path';
import {fileURLToPath} from 'node:url';import {setTimeout as delay} from 'node:timers/promises';
const source=fileURLToPath(new URL('../',import.meta.url));
async function until(fn,label){const end=Date.now()+15000;while(Date.now()<end){if(await fn())return;await delay(30);}throw Error('Wiki fixture timeout: '+label);}
test('original six Wiki tools and bundled skill execute through one Pi owner, preserve archive bytes and refuse read-only writes',{skip:!['linux','darwin'].includes(process.platform),timeout:60000},async t=>{
 let fixture,output='',stderr='',link;
 t.after(async()=>{if(fixture?.pid&&fixture.exitCode===null){const end=once(fixture,'exit');fixture.kill('SIGTERM');await end;}});
 const env=Object.fromEntries(Object.entries(process.env).filter(([key])=>!/^(AUGMENTOR_|DSH_|PI_)/.test(key)));
 fixture=spawn(process.execPath,[join(source,'scripts/harness-ui-proof.mjs')],{cwd:source,env:{...env,AUGMENTOR_HARNESS_PROOF_WIKI:'1',AUGMENTOR_HARNESS_PROOF_RECORD_REQUESTS:'1'},stdio:['ignore','pipe','pipe']});fixture.stdout.on('data',d=>output+=d);fixture.stderr.on('data',d=>stderr+=d);
 await until(()=>{assert.equal(fixture.exitCode,null,stderr);try{link=JSON.parse(output.trim().split('\n').find(line=>line.startsWith('{"fixture"')));return !!link;}catch{return false;}},'Host');
 const url=new URL(link.url),token=new URLSearchParams(url.hash.slice(1)).get('token');
 const rpc=async(method,params={})=>{const response=await fetch(url.origin+'/api/rpc',{method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:JSON.stringify({id:crypto.randomUUID(),method,params})}),frame=await response.json();if(frame.error)throw Error(frame.error.message);return frame.result;};
 const wikiProfile=await rpc('wiki.describe');await rpc('wiki.set',{expectedRevision:wikiProfile.revision,value:{...wikiProfile.value,typeFolders:{concept:'wiki/areas'}}});
 const selection={provider:'fixture',model:'harness-fixture'},sid='wiki-core';
 await rpc('session.create',{sessionId:sid,selection,cwd:link.workspace});
 await rpc('session.prompt',{sessionId:sid,requestId:crypto.randomUUID(),content:[{type:'text',text:'/skill:wiki-query WIKI_CORE_FLOW'}]});
 await until(async()=>!(await rpc('session.list')).items.find(row=>row.sessionId===sid).running,'Wiki flow completed');
 const history=await rpc('session.history',{sessionId:sid,maxMessages:100}),events=history.events.map(row=>row.event);
 const results=events.filter(event=>event.type==='tool/result');assert.equal(results.length,8,JSON.stringify({results:results.map(e=>({name:e.data.name,isError:e.data.isError,text:JSON.stringify(e.data.result).slice(0,160)})),notices:events.filter(e=>e.type==='runtime/notice').map(e=>e.data)}));assert(results.every(result=>!result.data.isError),JSON.stringify(results));
 assert((await stat(join(link.wikiVault,'wiki/areas/Renamed Authored Page.md'))).isFile(),'configured routing reaches the original Vault');
 const wiki=join(link.wikiVault,'wiki');
 const paths=[];async function walk(path){for(const entry of await readdir(path,{withFileTypes:true})){const p=join(path,entry.name);if(entry.isDirectory())await walk(p);else if(entry.name.endsWith('.md'))paths.push(p);}}await walk(wiki);
 const pages=await Promise.all(paths.map(p=>readFile(p,'utf8')));assert(pages.some(body=>body.includes('title: Renamed Authored Page')&&body.includes('AUTHORED WIKI CONTENT')));assert(pages.some(body=>body.includes('[[Renamed Authored Page]]')));assert(!pages.some(body=>body.includes('[[Authored Page]]')&&!body.includes('Wiki Log')));
 assert.equal(await readFile(join(link.wikiVault,'.archive/source.txt'),'utf8'),'AUTHORED WIKI RAW SOURCE\n');await assert.rejects(stat(join(link.wikiVault,'.raw/source.txt')),error=>error.code==='ENOENT');assert.deepEqual(JSON.parse(await readFile(join(link.wikiVault,'.raw/.manifest.json'),'utf8')).sources,{});
 const requests=(await readFile(link.requestLog,'utf8')).trim().split('\n').map(JSON.parse);assert.equal(requests.length,9);const names=requests[0].tools.map(tool=>tool.function.name);for(const name of ['wiki_query','wiki_write','wiki_rename','wiki_scaffold','wiki_archive','wiki_lint'])assert(names.includes(name),name);
 const skill=(await readFile(join(source,'packages/runtime/vendor/dsh-plugin-wiki-skills/skills/wiki-query/SKILL.md'),'utf8')).split('---',3)[2].trim();assert(requests[0].messages.map(message=>typeof message.content==='string'?message.content:message.content?.map(part=>part.text??'').join('\n')??'').join('\n').includes(skill.slice(0,100)),'the actual approved bundled skill reaches the model');
 const before=await Promise.all(paths.map(async p=>[p,await readFile(p)]));

 await rpc('session.create',{sessionId:'wiki-readonly',selection,cwd:link.workspace});await rpc('session.prompt',{sessionId:'wiki-readonly',requestId:crypto.randomUUID(),content:[{type:'text',text:'WIKI_READONLY'}]});
 await until(async()=>!(await rpc('session.list')).items.find(row=>row.sessionId==='wiki-readonly').running,'read-only settled');
 const readonly=(await rpc('session.history',{sessionId:'wiki-readonly',maxMessages:100})).events.map(row=>row.event);assert(readonly.some(e=>e.type==='tool/result'&&JSON.stringify(e).includes('Read-only chat')));assert(readonly.some(e=>e.type==='tool/result'&&JSON.stringify(e).includes('wiki vault:')));
 for(const [p,bytes] of before)assert.deepEqual(await readFile(p),bytes);assert.equal((await readFile(link.requestLog,'utf8')).trim().split('\n').length,12);assert.equal(stderr,'');
 await rpc('session.create',{sessionId:'wiki-browser',surface:'browser',selection,cwd:link.workspace});await rpc('session.prompt',{sessionId:'wiki-browser',requestId:crypto.randomUUID(),content:[{type:'text',text:'WIKI_BROWSER_CATALOG'}]});await until(async()=>!(await rpc('session.list')).items.find(row=>row.sessionId==='wiki-browser').running,'browser settled');
 const browserRequests=(await readFile(link.requestLog,'utf8')).trim().split('\n').map(JSON.parse).slice(12);assert.equal(browserRequests.length,1);assert(!browserRequests[0].tools.some(tool=>tool.function.name.startsWith('wiki_')),'the native vault is not granted to a browser session');
});

test('an uncertain real Wiki archive stops its Pi owner before another request and preserves both source versions',{skip:!['linux','darwin'].includes(process.platform),timeout:30000},async t=>{
 let fixture,output='',stderr='',link;t.after(async()=>{if(fixture?.pid&&fixture.exitCode===null){const end=once(fixture,'exit');fixture.kill('SIGTERM');await end;}});
 const env=Object.fromEntries(Object.entries(process.env).filter(([key])=>!/^(AUGMENTOR_|DSH_|PI_)/.test(key)));
 fixture=spawn(process.execPath,[join(source,'scripts/harness-ui-proof.mjs')],{cwd:source,env:{...env,AUGMENTOR_HARNESS_PROOF_WIKI:'1',AUGMENTOR_HARNESS_PROOF_WIKI_FAILURE:'1',AUGMENTOR_HARNESS_PROOF_RECORD_REQUESTS:'1'},stdio:['ignore','pipe','pipe']});fixture.stdout.on('data',d=>output+=d);fixture.stderr.on('data',d=>stderr+=d);
 await until(()=>{assert.equal(fixture.exitCode,null,stderr);try{link=JSON.parse(output.trim().split('\n').find(line=>line.startsWith('{"fixture"')));return !!link;}catch{return false;}},'Host');const url=new URL(link.url),token=new URLSearchParams(url.hash.slice(1)).get('token');
 const rpc=async(method,params={})=>{const r=await fetch(url.origin+'/api/rpc',{method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:JSON.stringify({id:crypto.randomUUID(),method,params})}),v=await r.json();if(v.error)throw Error(v.error.message);return v.result;};
 const sid='wiki-unknown';await rpc('session.create',{sessionId:sid,selection:{provider:'fixture',model:'harness-fixture'},cwd:link.workspace});await rpc('session.prompt',{sessionId:sid,requestId:crypto.randomUUID(),content:[{type:'text',text:'WIKI_UNKNOWN'}]});await until(async()=>!(await rpc('session.list')).items.find(row=>row.sessionId===sid).running,'uncertain owner settled');
 const events=(await rpc('session.history',{sessionId:sid,maxMessages:100})).events.map(row=>row.event);assert.equal(events.filter(e=>e.type==='tool/call').length,1);assert(events.some(e=>e.type==='tool/result'&&e.data.result.details?.outcome==='unknown'));assert.equal((await readFile(link.requestLog,'utf8')).trim().split('\n').length,1,'no second provider request after uncertainty');
 assert.equal(await readFile(join(link.wikiVault,'.raw/conflict.txt'),'utf8'),'AUTHORED NEW RAW');assert.equal(await readFile(join(link.wikiVault,'.archive/conflict.txt'),'utf8'),'AUTHORED OLDER ARCHIVE');await assert.rejects(stat(join(link.wikiVault,'wiki/concepts/Never Reached.md')),e=>e.code==='ENOENT');assert.equal(stderr,'');
});
