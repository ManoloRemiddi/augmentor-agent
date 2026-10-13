// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {chromiumPort} from './fixtures/chromium-ready.mjs';
// Original plugin modal against the real owner and an authored loopback model.
import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {mkdtemp,readFile,writeFile,mkdir,rm} from 'node:fs/promises';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {fileURLToPath} from 'node:url';
import {setTimeout as delay} from 'node:timers/promises';
import {harnessCdp} from './fixtures/harness-cdp.mjs';
import {harnessPointerClick} from './fixtures/harness-pointer.mjs';
import {PiConnection} from '../dist/client/src/socket.js';
import {localConnect} from '../dist/platform/src/transport.js';
const source=fileURLToPath(new URL('../',import.meta.url));
async function until(fn,label){const end=Date.now()+12000;let last;while(Date.now()<end){try{if(await fn())return;}catch(error){last=error;}await delay(30);}throw Error('Harness composition timeout: '+label+(last?' ('+last.message+')':''));}
test('original Context Insights uses retained records, filters, refresh and exact session navigation',{skip:process.platform!=='linux',timeout:60000},async t=>{
 const profile=await mkdtemp(join(tmpdir(),'augmentor-context-chrome-'));let fixture,chrome,panel,owner,link,output='',stderr='';
 t.after(async()=>{owner?.close();panel?.close();for(const child of [chrome,fixture])if(child?.pid&&child.exitCode===null){const ended=once(child,'exit');child.kill('SIGTERM');await ended;}await rm(profile,{recursive:true,force:true,maxRetries:5,retryDelay:100});});
 const env=Object.fromEntries(Object.entries(process.env).filter(([key])=>!/^(AUGMENTOR_|DSH_|PI_)/.test(key)));for(const key of ['AUGMENTOR_PI_TEST_ROOT','AUGMENTOR_PYTHON'])if(process.env[key])env[key]=process.env[key];
 fixture=spawn(process.execPath,[join(source,'scripts/harness-ui-proof.mjs')],{cwd:source,env:{...env,AUGMENTOR_HARNESS_PROOF_RECORD_REQUESTS:'1'},stdio:['ignore','pipe','pipe']});fixture.stdout.on('data',data=>output+=data);fixture.stderr.on('data',data=>stderr+=data);
 await until(()=>{assert.equal(fixture.exitCode,null,stderr);try{link=JSON.parse(output.trim().split('\n').find(line=>line.startsWith('{"fixture"')));return !!link;}catch{return false;}},'owner ready');
 const url=new URL(link.url),token=new URLSearchParams(url.hash.slice(1)).get('token');
 const rpc=async(method,params={},bearer=token)=>{const response=await fetch(url.origin+'/api/rpc',{method:'POST',headers:{Authorization:'Bearer '+bearer,'Content-Type':'application/json'},body:JSON.stringify({id:crypto.randomUUID(),method,params})}),frame=await response.json();if(frame.error)throw Error(frame.error.message);return frame.result;};
 const socket=localConnect(join(link.state,'runtime.sock'));await once(socket,'connect');owner=new PiConnection(socket);await owner.call('host.hello',{protocol:'augmentor-pi/1'});
 chrome=spawn(process.env.CHROMIUM_BIN??'chromium',['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run','--remote-debugging-port=0','--user-data-dir='+profile,link.url],{env,stdio:'ignore'});
 let port;await until(async()=>{try{port=await chromiumPort(profile);return !!port;}catch{return false;}},'Chrome ready');
 const target=(await fetch('http://127.0.0.1:'+port+'/json').then(r=>r.json())).find(row=>row.type==='page');panel=await harnessCdp(target.webSocketDebuggerUrl);await panel.call('Emulation.setDeviceMetricsOverride',{width:513,height:715,deviceScaleFactor:1,mobile:false});await panel.reload();for(const domain of ['Runtime','Log','Network','Page'])await panel.call(domain+'.enable');
 const visible=expression=>until(()=>panel.evaluate('Boolean('+expression+')'),expression).catch(async error=>{error.message+=' '+JSON.stringify({body:await panel.evaluate('document.body.innerText'),composer:await panel.evaluate('Array.from(document.querySelectorAll("[contenteditable]")).map(x=>x.outerHTML)'),focus:await panel.evaluate('document.activeElement.outerHTML.slice(0,200)'),errors:panel.errors,fixture:stderr});throw error;});
 const click=expression=>harnessPointerClick(panel,expression,until);
 const button=(label,within='document')=>'Array.from('+within+'.querySelectorAll("button")).find(x=>x.textContent.trim()==='+JSON.stringify(label)+')';

 const composer='document.querySelector("[contenteditable=true]")';
 await visible('document.querySelector("button[aria-label=\\"New session\\"]")');
 const histories=new Map();
 for(let i=0;i<2;i++){
  await click('document.querySelector("button[aria-label=\\"New session\\"]")');await visible(composer+'&&!'+composer+'.hasAttribute("aria-disabled")');
  await click(composer);await panel.call('Input.insertText',{text:'Read the authored fixture note '+i+'.'});await click('document.querySelector("button[aria-label=\\"Send message\\"]")');await visible('document.body.innerText.includes("The note says:")&&!document.querySelector("button[aria-label=\\"Stop generating\\"]")');
  const row=(await rpc('session.list')).items.find(x=>!histories.has(x.sessionId));histories.set(row.sessionId,await rpc('session.history',{sessionId:row.sessionId}));
 }
 const wire=await readFile(link.requestLog,'utf8');assert.equal(wire.trim().split('\n').length,4);
 const openInsights=async()=>{await click('document.querySelector("button[aria-label=\\"Context Insights\\"]")');await visible('document.querySelector(".lc-ov-search")&&document.querySelector("[role=status]")?.innerText.includes("2 sessions")');};
 await openInsights();
 const timingCard='Array.from(document.querySelectorAll(".lc-ov-stats .lc-card")).find(row=>row.querySelector(".lc-card-title-text")?.textContent==="Timing Stats")';await visible(timingCard+'?.innerText.includes("Measured SDK step time")');assert(await panel.evaluate(timingCard+'.innerText.includes("Text stream")&&'+timingCard+'.innerText.includes("Tool intervals")'));assert(await panel.evaluate('document.querySelector("[role=status]").innerText.includes("Measured SDK steps: 4")'),'cross-session timing coverage matches four actual SDK steps');
 assert.equal(await panel.evaluate('document.querySelectorAll(".lc-ov-session").length'),2);
 assert(await panel.evaluate('document.querySelector(".lc-ov-kpis").innerText.includes("Recorded turns")'));
 assert(await panel.evaluate('document.body.innerText.includes("Reported token buckets")&&document.body.innerText.includes("Skill-load attribution is not captured by Pi.")'));
 assert.equal(await panel.evaluate('document.querySelectorAll(".lc-ov-session .lc-donut").length'),2);
 assert.equal(await panel.evaluate('document.querySelectorAll(".lc-ov-kpi .lc-stat-value")[1].textContent'),'1.4k');assert.equal(await panel.evaluate('document.querySelectorAll(".lc-ov-kpi .lc-stat-value")[4].textContent'),'2');
 const requests=Array.from(panel.requests.values()).filter(frame=>frame.method);assert(!requests.some(frame=>frame.method==='session.open'&&frame.params.sessionId!==[...histories.keys()].at(-1)),'corpus reads never open other agent sessions');
 // Original range, calendar, sort and search controls, including refresh without remount/reset.
 await click(button('All retained','document.querySelector(".lc-ov-range")'));await click('document.querySelector(".lc-dp-trigger")');await visible('document.querySelector(".lc-dp-panel")');
 await panel.call('Input.dispatchKeyEvent',{type:'keyDown',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});await panel.call('Input.dispatchKeyEvent',{type:'keyUp',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});await visible('!document.querySelector(".lc-dp-panel")');
 await click(button('Total Tokens','document.querySelector(".lc-ov-list-head")'));await click('document.querySelector(".lc-ov-search")');await panel.call('Input.insertText',{text:'impossible-missing-fixture'});await visible('document.querySelectorAll(".lc-ov-session").length===0');
 await click(button('Refresh Insights'));await visible('!'+button('Refresh Insights')+'.disabled&&document.querySelector(".lc-ov-search").value==="impossible-missing-fixture"');assert.equal(await panel.evaluate('document.querySelectorAll(".lc-ov-session").length'),0);
 await click('document.querySelector(".lc-ov-search")');await panel.call('Input.dispatchKeyEvent',{type:'keyDown',key:'a',code:'KeyA',modifiers:2,windowsVirtualKeyCode:65,commands:['selectAll']});await panel.call('Input.dispatchKeyEvent',{type:'keyUp',key:'a',code:'KeyA',modifiers:0,windowsVirtualKeyCode:65});await panel.call('Input.dispatchKeyEvent',{type:'keyDown',key:'Backspace',code:'Backspace',windowsVirtualKeyCode:8});await panel.call('Input.dispatchKeyEvent',{type:'keyUp',key:'Backspace',code:'Backspace',windowsVirtualKeyCode:8});await visible('document.querySelectorAll(".lc-ov-session").length===2');
 await click('document.querySelector("button.lc-heat-cell")');await visible('document.querySelector(".lc-ov-day-chip")');await click('document.querySelector(".lc-ov-day-chip")');await visible('document.querySelectorAll(".lc-ov-session").length===2');
 for(const width of [513,1440]){await panel.call('Emulation.setDeviceMetricsOverride',{width,height:715,deviceScaleFactor:1,mobile:false});await visible('document.documentElement.scrollWidth<=innerWidth');assert(await panel.evaluate('(()=>{const e=document.querySelector(".lc-ov-pagescroll"),r=e.getBoundingClientRect();return r.height>150&&r.bottom<=innerHeight+1&&getComputedStyle(e).overflowY==="auto"})()'),'original scroll region remains usable');}
 const nav=await panel.evaluate('Array.from(document.querySelectorAll(".lc-ov-session")).map(e=>({text:e.innerText,title:e.querySelector(".lc-ov-session-name")?.textContent}))');assert.equal(nav.length,2);
 await click('document.querySelector(".lc-ov-session")');await visible('!document.querySelector(".lc-ov-search")&&'+composer);assert.equal(await panel.evaluate(composer+'.textContent'),'');
 for(const [sid,before] of histories)assert.deepEqual(await rpc('session.history',{sessionId:sid}),before);assert.equal(await readFile(link.requestLog,'utf8'),wire);
 const inspection=await owner.call('inspection.open',{sessionId:[...histories.keys()][0]});await panel.call('Page.navigate',{url:inspection.url});await visible('document.querySelector("[data-composer-input][aria-disabled=true][contenteditable=false]")');assert(!await panel.evaluate('document.querySelector("button[aria-label=\\"Context Insights\\"]")'),'restricted inspection exposes no corpus dashboard');
 assert.deepEqual(panel.errors,[]);assert(!panel.urls.some(value=>/^https?:/.test(value)&&!value.startsWith(url.origin+'/')),'no supplier registry, analytics, skill or price requests');
});
