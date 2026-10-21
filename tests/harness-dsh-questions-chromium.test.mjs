// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Actual Pi SDK and original DSH components with independently authored provider/extension input.
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
async function until(fn,label){const end=Date.now()+12000;while(Date.now()<end){if(await fn())return;await delay(25);}throw Error('Original question fixture: '+label);}
test('original question Take time survives the SDK deadline and page reconnect, submits once and retains real native answers',{skip:process.platform!=='linux',timeout:60000},async t=>{
 const profile=await mkdtemp(join(tmpdir(),'augmentor-question-chrome-'));let fixture,chrome,panel,link,output='',stderr='';
 t.after(async()=>{panel?.close();for(const child of [chrome,fixture])if(child?.pid&&child.exitCode===null){const end=once(child,'exit');child.kill('SIGTERM');await end;}await rm(profile,{recursive:true,force:true,maxRetries:5,retryDelay:100});});
 const env=Object.fromEntries(Object.entries(process.env).filter(([key])=>!/^(AUGMENTOR_|DSH_|PI_)/.test(key)));for(const key of ['AUGMENTOR_PI_TEST_ROOT','AUGMENTOR_PYTHON'])if(process.env[key])env[key]=process.env[key];
 fixture=spawn(process.execPath,[join(source,'scripts/harness-ui-proof.mjs')],{cwd:source,env:{...env,AUGMENTOR_HARNESS_PROOF_RECORD_REQUESTS:'1',AUGMENTOR_HARNESS_PROOF_QUESTIONS:'1'},stdio:['ignore','pipe','pipe']});fixture.stdout.on('data',s=>output+=s);fixture.stderr.on('data',s=>stderr+=s);
 await until(()=>{assert.equal(fixture.exitCode,null,stderr);try{link=JSON.parse(output.trim().split('\n').find(s=>s.startsWith('{"fixture"')));return !!link;}catch{return false;}},'owner ready');
 const url=new URL(link.url),token=new URLSearchParams(url.hash.slice(1)).get('token');
 const rpc=async(method,params)=>{const response=await fetch(url.origin+'/api/rpc',{method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:JSON.stringify({id:crypto.randomUUID(),method,params})}),frame=await response.json();if(frame.error)throw Error(frame.error.message);return frame.result;};
 const requests=async()=>{try{return (await readFile(link.requestLog,'utf8')).trim().split('\n').map(JSON.parse);}catch{return [];}};
 chrome=spawn(process.env.CHROMIUM_BIN??'chromium',['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run','--remote-debugging-port=0','--user-data-dir='+profile,link.url],{env,stdio:'ignore'});
 let port;await until(async()=>{port=await chromiumPort(profile).catch(()=>null);return !!port;},'browser ready');const target=(await fetch('http://127.0.0.1:'+port+'/json').then(r=>r.json())).find(x=>x.type==='page');panel=await harnessCdp(target.webSocketDebuggerUrl);for(const domain of ['Runtime','Log','Network'])await panel.call(domain+'.enable');await panel.call('Emulation.setDeviceMetricsOverride',{width:513,height:715,deviceScaleFactor:1,mobile:false});
 const visible=expression=>until(()=>panel.evaluate('Boolean('+expression+')'),expression).catch(async error=>{error.message+=' '+JSON.stringify({body:await panel.evaluate('document.body.innerText'),errors:panel.errors,fixture:stderr});throw error;}),click=expression=>harnessPointerClick(panel,expression,until);
 await visible('document.querySelector("button[aria-label=\\"New session\\"]")');await click('document.querySelector("button[aria-label=\\"New session\\"]")');await visible('document.querySelector("[contenteditable=true][data-composer-input]")');
 await click('document.querySelector("[contenteditable=true][data-composer-input]")');await panel.call('Input.insertText',{text:'QUESTION_FIXTURE'});await click('document.querySelector("button[aria-label=\\"Send message\\"]")');
 await visible('document.body.innerText.includes("Keep the authored fixture going?")&&document.body.innerText.includes("Continuing in")');await click('Array.from(document.querySelectorAll("button")).find(x=>x.textContent==="Take time")');await visible('document.body.innerText.includes("Waiting until you answer")');
 await delay(3200);assert.equal((await requests()).length,1,'no continuation request while the human holds the question');
 const sessionId=(await rpc('session.list')).items[0].sessionId;await panel.reload();await visible('document.body.innerText.includes("Keep the authored fixture going?")&&document.body.innerText.includes("Waiting until you answer")');assert.equal((await requests()).length,1,'reconnect does not replay the question producer');
 await click('document.querySelector("button[role=radio][aria-label=\\"Keep going\\"]")');await click('Array.from(document.querySelectorAll("button")).find(x=>x.textContent==="Submit")');await visible('document.body.innerText.includes("Original question answer received")');
 assert.equal((await requests()).length,2);assert.equal((await rpc('session.history',{sessionId})).events.filter(x=>x.event.type==='user/message').length,1);
 const native=await rpc('session.nativeHistory',{sessionId,limit:100}),tool=native.entries.find(x=>x.role==='toolResult');assert(tool,'actual native tool result exists');const original=await rpc('session.nativeRead',{sessionId,entryId:tool.entryId,pathHash:tool.pathHash,entryHash:tool.entryHash,nativeSessionId:native.nativeSessionId,limit:4096});assert(original.text.includes('Fixture choice: Keep going'),'actual SDK tool answer is saved in native history');
 await panel.reload();await visible('document.body.innerText.includes("Original question answer received")');assert.equal((await requests()).length,2,'saved reopening does not resend the answer');assert.equal(panel.errors.length,0,JSON.stringify(panel.errors));assert(panel.urls.every(x=>x.startsWith(url.origin)||x.startsWith('data:')),JSON.stringify(panel.urls));
});
