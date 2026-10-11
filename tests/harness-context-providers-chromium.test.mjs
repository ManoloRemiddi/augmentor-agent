// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Actual Pi owner/provider adapters/browser; all responses and data are authored.
import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {mkdtemp,readFile,rm} from 'node:fs/promises';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {fileURLToPath} from 'node:url';
import {setTimeout as delay} from 'node:timers/promises';
import {chromiumPort} from './fixtures/chromium-ready.mjs';
import {harnessCdp} from './fixtures/harness-cdp.mjs';
import {harnessPointerClick} from './fixtures/harness-pointer.mjs';
const source=fileURLToPath(new URL('../',import.meta.url));
async function until(fn,label){const end=Date.now()+12000;let last;while(Date.now()<end){try{if(await fn())return;}catch(error){last=error;}await delay(30);}throw Error('Context provider timeout: '+label+(last?' ('+last.message+')':''));}
for(const api of ['anthropic-messages','openai-responses','google-generative-ai'])test('original Context projects actual '+api+' SDK requests without replay',{skip:process.platform!=='linux',timeout:60000},async t=>{
 const profile=await mkdtemp(join(tmpdir(),'augmentor-context-provider-'));let fixture,chrome,panel,link,output='',stderr='';
 t.after(async()=>{panel?.close();for(const child of [chrome,fixture])if(child?.pid&&child.exitCode===null){const ended=once(child,'exit');child.kill('SIGTERM');await ended;}await rm(profile,{recursive:true,force:true,maxRetries:5,retryDelay:100});});
 const env=Object.fromEntries(Object.entries(process.env).filter(([key])=>!/^(AUGMENTOR_|DSH_|PI_)/.test(key)));for(const key of ['AUGMENTOR_PI_TEST_ROOT','AUGMENTOR_PYTHON'])if(process.env[key])env[key]=process.env[key];
 fixture=spawn(process.execPath,[join(source,'scripts/harness-ui-proof.mjs')],{cwd:source,env:{...env,AUGMENTOR_HARNESS_PROOF_RECORD_REQUESTS:'1',AUGMENTOR_HARNESS_PROOF_PROVIDER_API:api},stdio:['ignore','pipe','pipe']});fixture.stdout.on('data',data=>output+=data);fixture.stderr.on('data',data=>stderr+=data);
 await until(()=>{assert.equal(fixture.exitCode,null,stderr);try{link=JSON.parse(output.trim().split('\n').find(line=>line.startsWith('{"fixture"')));return !!link;}catch{return false;}},'actual owner ready');
 const url=new URL(link.url),token=new URLSearchParams(url.hash.slice(1)).get('token'),rpc=async(method,params={})=>{const response=await fetch(url.origin+'/api/rpc',{method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:JSON.stringify({id:crypto.randomUUID(),method,params})}),frame=await response.json();if(frame.error)throw Error(frame.error.message);return frame.result;};
 chrome=spawn(process.env.CHROMIUM_BIN??'chromium',['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run','--remote-debugging-port=0','--user-data-dir='+profile,link.url],{env,stdio:'ignore'});let port;await until(async()=>{try{port=await chromiumPort(profile);return !!port;}catch{return false;}},'Chromium ready');
 const target=(await fetch('http://127.0.0.1:'+port+'/json').then(r=>r.json())).find(row=>row.type==='page');panel=await harnessCdp(target.webSocketDebuggerUrl);for(const domain of ['Runtime','Log','Network','Page'])await panel.call(domain+'.enable');await panel.call('Emulation.setDeviceMetricsOverride',{width:513,height:715,deviceScaleFactor:1,mobile:false});await panel.reload();
 const visible=expression=>until(()=>panel.evaluate('Boolean('+expression+')'),expression).catch(async error=>{error.message+=' '+JSON.stringify({body:await panel.evaluate('document.body.innerText'),errors:panel.errors,fixture:stderr});throw error;}),click=expression=>harnessPointerClick(panel,expression,until);
 await visible('document.querySelector("button[aria-label=\\"New session\\"]")');await click('document.querySelector("button[aria-label=\\"New session\\"]")');await visible('document.querySelector("[contenteditable=true]")&&!document.querySelector("[contenteditable=true]").hasAttribute("aria-disabled")');
 await click('document.querySelector("[contenteditable=true]")');await panel.call('Input.insertText',{text:'Read the authored fixture note once.'});await click('document.querySelector("button[aria-label=\\"Send message\\"]")');await visible('document.body.innerText.includes("The note says:")&&!document.querySelector("button[aria-label=\\"Stop generating\\"]")');
 const sid=(await rpc('session.list')).items[0].sessionId,history=await rpc('session.history',{sessionId:sid}),wire=await readFile(link.requestLog,'utf8'),requests=(await rpc('observation.list',{sessionId:sid,limit:500})).records.filter(r=>r.kind==='model/request');assert.equal(wire.trim().split('\n').length,2);assert.equal(history.events.filter(r=>r.event.type==='tool/result').length,1);assert.equal(requests.length,2);assert(requests.every(r=>r.data.api===api));
 const show=async()=>{
  await click('Array.from(document.querySelectorAll("[role=tab]")).find(x=>x.textContent==="Context")');await visible('document.querySelectorAll("[data-seq]").length===2');await click('Array.from(document.querySelectorAll(".lc-br-cat-row")).find(x=>x.textContent.includes("Tool Results"))');
  await visible('document.querySelector(".lc-br-body")?.innerText.includes("Harness fixture ready.")');
  if(api==='google-generative-ai')assert(await panel.evaluate('document.querySelector(".lc-br-body").innerText.includes("Call arguments unavailable in this recorded request")'),'id-less wire results do not borrow a name-matched call');else await visible('document.querySelector(".lc-ts-arg-val")?.textContent==='+JSON.stringify(join(link.workspace,'note.txt')));
 };
 await show();await panel.reload();await visible('document.querySelector("[role=tab]")');await show();assert.deepEqual(await rpc('session.history',{sessionId:sid}),history);assert.equal(await readFile(link.requestLog,'utf8'),wire,'reading and reload never replay a provider request');assert.equal(panel.errors.length,0,JSON.stringify(panel.errors));assert(panel.urls.every(value=>value.startsWith(url.origin)||value.startsWith('data:')));
});
