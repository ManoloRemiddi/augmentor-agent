// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Original GUI, independent real Host and a disposable Chromium profile only.
import test from 'node:test';import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';import {once} from 'node:events';
import {mkdtemp,rm} from 'node:fs/promises';import {join} from 'node:path';import {tmpdir} from 'node:os';
import {setTimeout as delay} from 'node:timers/promises';
import {planFixture} from './fixtures/plans.mjs';import {chromiumPort} from './fixtures/chromium-ready.mjs';import {harnessCdp} from './fixtures/harness-cdp.mjs';
async function until(fn,label){const end=Date.now()+15000;while(Date.now()<end){if(await fn())return;await delay(30);}throw Error('Browser reopen timeout: '+label);}
test('original GUI reopens a bare bookmark in a new tab and after browser/Host restart without upgrading inspectors',{skip:process.platform!=='linux',timeout:90000},async t=>{
 const f=await planFixture(t);await f.call('session.create',{sessionId:'authored-bookmark',cwd:f.workspace,selection:f.selection});const link=await f.call('harness.open'),token=new URLSearchParams(new URL(link.url).hash.slice(1)).get('token');
 const profile=await mkdtemp(join(tmpdir(),'augmentor-reopen-chrome-'));let chrome,port;const panels=[];
 const env=Object.fromEntries(Object.entries(process.env).filter(([k])=>!/^(AUGMENTOR_|DSH_|PI_)/.test(k)));
 async function stopChrome(){for(const p of panels.splice(0)){try{await p.navigate('about:blank');}catch{}p.close();}if(chrome?.exitCode===null&&chrome.signalCode===null){const ended=once(chrome,'exit');chrome.kill('SIGTERM');await ended;}}
 t.after(async()=>{await stopChrome();await rm(profile,{recursive:true,force:true,maxRetries:5,retryDelay:100});});
 async function attach(target){const p=await harnessCdp(target.webSocketDebuggerUrl);panels.push(p);await p.call('Runtime.enable');await p.call('Page.enable');return p;}
 async function boot(url){await rm(join(profile,'DevToolsActivePort'),{force:true});chrome=spawn(process.env.CHROMIUM_BIN??'chromium',['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run','--remote-debugging-port=0','--user-data-dir='+profile,url],{env,stdio:'ignore'});await until(async()=>{assert.equal(chrome.exitCode,null);try{port=await chromiumPort(profile);return !!port;}catch{return false;}},'Chromium');const rows=await fetch('http://127.0.0.1:'+port+'/json').then(r=>r.json());return attach(rows.find(v=>v.type==='page'));}
 async function newTab(owner,url){const {targetId}=await owner.call('Target.createTarget',{url});let row;await until(async()=>{row=(await fetch('http://127.0.0.1:'+port+'/json').then(r=>r.json())).find(v=>v.id===targetId);return !!row;},'new tab');return attach(row);}
 const ready=p=>until(()=>p.evaluate('Boolean(document.querySelector("button[aria-label=\\"New session\\"]"))&&!document.body.innerText.includes("Open Augmentor Harness from")'),'original authenticated GUI');
 let first=await boot(link.url);await ready(first);await until(()=>first.evaluate('localStorage.getItem("augmentor-harness-operator-token")===sessionStorage.getItem("augmentor-harness-token")'),'confirmed login remembered');
 const bare=await newTab(first,link.origin+'/');await ready(bare);assert.equal(await bare.evaluate('sessionStorage.getItem("augmentor-harness-token")'),token);
 const inspector=await f.call('inspection.open',{sessionId:'authored-bookmark'}),readOnly=await newTab(first,inspector.url);await until(()=>readOnly.evaluate('Boolean(document.querySelector("[data-augmentor-access=\\"read-only\\"]"))'),'read-only scope');assert.equal(await readOnly.evaluate('localStorage.getItem("augmentor-harness-operator-token")'),token);assert.notEqual(await readOnly.evaluate('sessionStorage.getItem("augmentor-harness-token")'),token);
 await stopChrome();await f.stop();await f.start();const reopened=await f.call('harness.open');assert.equal(reopened.url,link.url);
 first=await boot(link.origin+'/');await ready(first);assert.equal(await first.evaluate('sessionStorage.getItem("augmentor-harness-token")'),token);assert.equal((await fetch(link.origin+'/api/access')).status,401);assert.equal(f.requests.length,0);assert.equal(f.errors(),'');
});
