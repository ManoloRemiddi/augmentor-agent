// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Actual Harness DOM/HTTP/Pi/history, synthetic local provider and private temporary profile.
import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {mkdtemp,readFile,writeFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {setTimeout as delay} from 'node:timers/promises';
const source=fileURLToPath(new URL('../',import.meta.url));
async function until(fn,label,ms=12000){const end=Date.now()+ms;let last;while(Date.now()<end){try{if(await fn())return;}catch(error){last=error;}await delay(30);}throw Error('Harness timeout: '+label+(last?' ('+last.message+')':''));}
async function cdp(url){
 const ws=new WebSocket(url);await once(ws,'open');let id=0;const pending=new Map(),errors=[];
 ws.addEventListener('message',event=>{const frame=JSON.parse(event.data),row=pending.get(frame.id);if(frame.method==='Runtime.exceptionThrown')errors.push(frame.params.exceptionDetails);if(row){pending.delete(frame.id);clearTimeout(row.timer);frame.error?row.reject(Error(frame.error.message)):row.resolve(frame.result);}});
 const call=(method,params={})=>new Promise((resolve,reject)=>{const key=++id,timer=setTimeout(()=>{pending.delete(key);reject(Error('CDP timeout: '+method));},10000);pending.set(key,{resolve,reject,timer});ws.send(JSON.stringify({id:key,method,params}));});
 return {call,errors,close(){for(const row of pending.values())clearTimeout(row.timer);ws.close();},async evaluate(expression){const result=await call('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(result.exceptionDetails)throw Error(JSON.stringify(result.exceptionDetails));return result.result.value;}};
}
test('Harness Branch/Edit controls preserve exact tool history, original drafts and selected child on reload',{skip:process.platform!=='linux',timeout:60000},async t=>{
 const profile=await mkdtemp(join(tmpdir(),'augmentor-harness-branch-chrome-'));let fixture,chrome,panel,output='',stderr='',link;
 t.after(async()=>{panel?.close();for(const child of [chrome,fixture])if(child?.pid&&child.exitCode===null){const ended=once(child,'exit');child.kill('SIGTERM');await ended;}await rm(profile,{recursive:true,force:true,maxRetries:5,retryDelay:100});});
 const env=Object.fromEntries(Object.entries(process.env).filter(([key])=>!/^(AUGMENTOR_|DSH_|PI_)/.test(key)));if(process.env.AUGMENTOR_PI_TEST_ROOT)env.AUGMENTOR_PI_TEST_ROOT=process.env.AUGMENTOR_PI_TEST_ROOT;
 fixture=spawn(process.execPath,[join(source,'scripts/harness-ui-proof.mjs')],{cwd:source,env:{...env,AUGMENTOR_HARNESS_PROOF_RECORD_REQUESTS:'1'},stdio:['ignore','pipe','pipe']});fixture.stdout.on('data',data=>output+=data);fixture.stderr.on('data',data=>stderr+=data);
 await until(()=>{assert.equal(fixture.exitCode,null,stderr);try{link=JSON.parse(output.trim().split('\n').find(line=>line.startsWith('{"fixture"')));return !!link;}catch{return false;}},'fixture readiness',20000);
 const url=new URL(link.url),token=new URLSearchParams(url.hash.slice(1)).get('token');
 const rpc=async(method,params={})=>{const response=await fetch(url.origin+'/api/rpc',{method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:JSON.stringify({id:crypto.randomUUID(),method,params})}),frame=await response.json();if(frame.error)throw Error(frame.error.message);return frame.result;};
 const requests=async()=>{try{return (await readFile(link.requestLog,'utf8')).trim().split('\n').filter(Boolean).map(line=>JSON.parse(line));}catch{return [];}};
 chrome=spawn(process.env.CHROMIUM_BIN??'chromium',['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run','--remote-debugging-port=0','--user-data-dir='+profile,link.url],{env,stdio:'ignore'});
 let port;await until(async()=>{try{port=(await readFile(join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0];return true;}catch{return false;}},'Chromium startup');
 const targets=await fetch('http://127.0.0.1:'+port+'/json').then(response=>response.json()),page=targets.find(row=>row.type==='page');assert(page);panel=await cdp(page.webSocketDebuggerUrl);await panel.call('Runtime.enable');
 const visible=expression=>until(()=>panel.evaluate(expression),expression).catch(async error=>{error.message+=' '+JSON.stringify({body:await panel.evaluate('document.body.innerText'),runtimeErrors:panel.errors,requests:(await requests()).length,fixtureErrors:stderr});throw error;});
 await visible('document.querySelector("#runtime")?.textContent.includes("Pi 1.1.0")&&!document.querySelector("#new-chat").disabled');
 // Hold one real subscription request: typing before selection completes stays a draft.
 await panel.evaluate('(()=>{const original=fetch;globalThis.releaseHarnessSelection=null;globalThis.fetch=async(...args)=>{if(args[1]?.body&&JSON.parse(args[1].body).method==="events.subscribe"&&!globalThis.releaseHarnessSelection)await new Promise(resolve=>globalThis.releaseHarnessSelection=resolve);return original(...args);};document.querySelector("#new-chat").click();})()');
 await visible('typeof globalThis.releaseHarnessSelection==="function"&&document.querySelector("#send").disabled');
 await panel.evaluate('(()=>{const input=document.querySelector("#input");input.value="Loading draft";input.dispatchEvent(new KeyboardEvent("keydown",{key:"Enter",bubbles:true}));})()');assert.equal(await panel.evaluate('document.querySelector("#input").value'),'Loading draft');assert.equal((await requests()).length,0);await panel.evaluate('globalThis.releaseHarnessSelection()');await visible('!document.querySelector("#send").disabled');
 async function send(text){await panel.evaluate('(()=>{const input=document.querySelector("#input");input.value='+JSON.stringify(text)+';input.dispatchEvent(new KeyboardEvent("keydown",{key:"Enter",bubbles:true}));})()');}
 async function settled(sid){await until(async()=>!(await rpc('session.list')).items.find(row=>row.sessionId===sid)?.running,'native idle');await visible('document.querySelector("#stop").disabled');}
 const selected=()=>panel.evaluate('sessionStorage.getItem("augmentor-harness-session")');
 await send('HARNESS_PARENT_ONE');const parentId=await selected();await visible('document.body.innerText.includes("The note says: Harness fixture ready.")');await settled(parentId);assert.equal((await requests()).length,2);
 await send('HARNESS_PARENT_TWO');await until(async()=>(await requests()).length===4,'second actual tool round');await settled(parentId);await visible('document.querySelectorAll("[data-message-action=branch]").length===2');const parent=await rpc('session.history',{sessionId:parentId,maxMessages:100});
 await panel.evaluate('document.querySelector("[data-message-action=branch]").click()');let childId;await until(async()=>{childId=await selected();return childId&&childId!==parentId;},'reply branch selected');await visible('document.body.innerText.includes("HARNESS_PARENT_ONE")&&!document.body.innerText.includes("HARNESS_PARENT_TWO")');
 assert.equal((await requests()).length,4,'Branch performs no inference or tool replay');assert.deepEqual(await rpc('session.history',{sessionId:parentId,maxMessages:100}),parent);
 await send('HARNESS_CHILD');await until(async()=>(await requests()).length===6,'child tool round');await settled(childId);const childInput=(await requests()).at(-1).messages;assert.doesNotMatch(JSON.stringify(childInput),/HARNESS_PARENT_TWO/);assert.match(JSON.stringify(childInput),/HARNESS_PARENT_ONE/);assert.equal(childInput.filter(row=>row.role==='tool').length,2,'native prior read plus actual child read');const child=await rpc('session.history',{sessionId:childId,maxMessages:100});
 await panel.evaluate('(()=>{document.querySelector("#input").value="Harness saved draft";document.querySelector("[data-message-action=edit]").click();})()');await visible('document.querySelector("#input").value==="HARNESS_CHILD"&&!document.querySelector("#edit-message").hidden');assert.equal((await rpc('session.list')).items.length,2,'Edit preparation does not fork');
 await panel.evaluate('document.querySelector("#cancel-edit").click()');assert.equal(await panel.evaluate('document.querySelector("#input").value'),'Harness saved draft');assert.equal((await requests()).length,6);
 await panel.evaluate('document.querySelector("[data-message-action=edit]").click()');await send('HARNESS_REVISED');let editedId;await until(async()=>{editedId=await selected();return editedId&&editedId!==childId;},'edit child selected');await until(async()=>(await requests()).length===8,'edited tool round');await settled(editedId);await visible('document.querySelector("#input").value==="Harness saved draft"&&document.querySelector("#edit-message").hidden');
 const revisedInput=(await requests()).at(-1).messages;assert.match(JSON.stringify(revisedInput),/HARNESS_PARENT_ONE/);assert.match(JSON.stringify(revisedInput),/HARNESS_REVISED/);assert.doesNotMatch(JSON.stringify(revisedInput),/HARNESS_PARENT_TWO|HARNESS_CHILD/);assert.equal(revisedInput.filter(row=>row.role==='tool').length,2);assert.deepEqual(await rpc('session.history',{sessionId:parentId,maxMessages:100}),parent);assert.deepEqual(await rpc('session.history',{sessionId:childId,maxMessages:100}),child);
 await panel.call('Page.reload');await visible('document.body.innerText.includes("HARNESS_REVISED")&&!document.body.innerText.includes("HARNESS_PARENT_TWO")');assert.equal(await selected(),editedId);assert.equal((await requests()).length,8,'reload performs no inference');
 // Shared web controls remain usable at the narrow layout, independent of OS adapters.
 await panel.call('Emulation.setDeviceMetricsOverride',{width:640,height:900,deviceScaleFactor:1,mobile:false});await visible('document.querySelector("#show-conversations").getBoundingClientRect().width>0');
 if(process.env.AUGMENTOR_HARNESS_BRANCH_SCREENSHOT)await writeFile(process.env.AUGMENTOR_HARNESS_BRANCH_SCREENSHOT,Buffer.from((await panel.call('Page.captureScreenshot',{format:'png'})).data,'base64'));
 await send('SLOW Harness branch fixture');await until(async()=>(await requests()).length===9,'slow provider');await visible('!document.querySelector("#stop").disabled&&Array.from(document.querySelectorAll("[data-message-action]")).every(button=>button.disabled)');await panel.evaluate('document.querySelector("#stop").click()');await settled(editedId);assert.equal((await requests()).length,9);assert.deepEqual(panel.errors,[]);assert.equal(stderr,'');
});
