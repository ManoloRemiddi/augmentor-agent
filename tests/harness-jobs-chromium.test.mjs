// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {mkdtemp,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {planFixture,until} from './fixtures/plans.mjs';
import {chromiumPort} from './fixtures/chromium-ready.mjs';
import {harnessCdp} from './fixtures/harness-cdp.mjs';
test('actual Harness job controls show output safely, stop a child and enforce scoped cold read-only evidence',{skip:process.platform!=='linux',timeout:60000},async t=>{
 const f=await planFixture(t,{jobMode:{}}),sid='jobs-ui',profile=await mkdtemp(join(tmpdir(),'augmentor-jobs-chrome-'));let chrome,panel;
 t.after(async()=>{panel?.close();if(chrome?.exitCode===null){const ended=once(chrome,'exit');chrome.kill('SIGTERM');await ended;}await rm(profile,{recursive:true,force:true,maxRetries:5,retryDelay:100});});
 await f.call('session.create',{sessionId:sid,selection:f.selection,cwd:f.workspace});await f.prompt(sid,{kind:'read'});await f.call('session.rename',{sessionId:sid,title:'Jobs UI fixture'});
 chrome=spawn(process.env.CHROMIUM_BIN??'chromium',['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run','--remote-debugging-port=0','--user-data-dir='+profile,(await f.link()).url],{env:f.env,stdio:'ignore'});
 let port;await until(async()=>{assert.equal(chrome.exitCode,null);try{port=await chromiumPort(profile);return !!port;}catch{return false;}},'jobs Chromium ready');const targets=await fetch('http://127.0.0.1:'+port+'/json').then(r=>r.json());panel=await harnessCdp(targets.find(row=>row.type==='page').webSocketDebuggerUrl);await panel.call('Runtime.enable');await panel.call('Page.enable');
 const visible=expression=>until(()=>panel.evaluate(expression),expression).catch(async error=>{error.message+=' '+JSON.stringify({body:await panel.evaluate('document.body.innerText'),errors:panel.errors,owner:f.errors()});throw error;});
 await visible('document.querySelector("#runtime")?.textContent.includes("Pi 1.1.0")&&!document.querySelector("#send").disabled');await panel.evaluate('Array.from(document.querySelectorAll("#sessions button")).find(b=>b.textContent==="Jobs UI fixture").click()');await visible('sessionStorage.getItem("augmentor-harness-session")==="jobs-ui"&&!document.querySelector("#send").disabled');await panel.evaluate('document.querySelector("[data-view=jobs]").click()');await visible('document.querySelector("#jobs-content").textContent.includes("No background jobs")');
 const literal='<img src=x onerror="globalThis.jobsInjected=true"> café 日本語';
 const launch=async task=>{await panel.evaluate('(()=>{const el=document.querySelector("[aria-label=\\"Background job task\\"]");el.value='+JSON.stringify(JSON.stringify(task))+';el.dispatchEvent(new Event("input"));Array.from(document.querySelectorAll("#jobs-content button")).find(b=>b.textContent==="Start job").click();})()');};
 await panel.evaluate('document.querySelector("#jobs-content details summary").click()');await launch({kind:'worker-reply',reply:literal});await visible('document.querySelector("#jobs-content").textContent.includes("recorded once")&&document.querySelector("#jobs-content").textContent.includes('+JSON.stringify(literal)+')');assert.equal(await panel.evaluate('document.querySelectorAll("#jobs-content img").length'),0);assert.equal(await panel.evaluate('globalThis.jobsInjected===true'),false);
 const job=(await f.call('session.jobs',{sessionId:sid})).items[0];assert.equal(job.state,'completed');
 await panel.evaluate('document.querySelector("#jobs-content details summary").click()');await launch({kind:'worker-hold'});await visible('document.querySelector("#jobs-content").textContent.includes("worker holding")');await panel.evaluate('Array.from(document.querySelectorAll("#jobs-content button")).find(b=>b.textContent==="Stop job").click()');await visible('document.querySelector("#jobs-content h3")?.textContent.startsWith("cancelled")');
 await panel.call('Emulation.setDeviceMetricsOverride',{width:640,height:900,deviceScaleFactor:1,mobile:false});assert.equal(await panel.evaluate('document.documentElement.scrollWidth<=innerWidth'),true);
 const count=f.requests.length;await f.stop();await f.start();const inspection=await f.call('inspection.open',{sessionId:sid}),link=new URL(inspection.url),token=new URLSearchParams(link.hash.slice(1)).get('token');
 await panel.call('Page.navigate',{url:inspection.url});await panel.reload();await visible('document.querySelector("#runtime")?.textContent.includes("Read-only")');await panel.evaluate('document.querySelector("[data-view=jobs]").click()');await visible('document.querySelector("#jobs-content").textContent.includes("completed")');assert.equal(await panel.evaluate('document.querySelectorAll("#jobs-content textarea").length'),0);
 for(const [method,params,reason] of [['session.job',{sessionId:'other',jobId:job.id},/selected conversation/],['session.startJob',{sessionId:sid,spec:{}},/read-only/]]){const response=await fetch(link.origin+'/api/rpc',{method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:JSON.stringify({id:crypto.randomUUID(),method,params})});assert.match((await response.json()).error.message,reason);}
 assert.equal(f.requests.length,count);assert.deepEqual(panel.errors,[]);assert.equal(f.errors(),'');
});
