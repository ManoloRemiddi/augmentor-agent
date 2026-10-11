// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Component-contract fixture only; the separate DSH browser cohort uses the real Pi SDK.
import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {mkdtemp,rm} from 'node:fs/promises';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {setTimeout as delay} from 'node:timers/promises';
import {HarnessServer} from '../dist/runtime/src/harness-server.js';
import {chromiumPort} from './fixtures/chromium-ready.mjs';
import {harnessCdp} from './fixtures/harness-cdp.mjs';
import {harnessPointerClick} from './fixtures/harness-pointer.mjs';
async function until(fn,label){const end=Date.now()+10000;while(Date.now()<end){if(await fn())return;await delay(25);}throw Error(label);}
test('original DSH approval/question components answer the selected Host interaction',{skip:process.platform!=='linux',timeout:30000},async t=>{
 const profile=await mkdtemp(join(tmpdir(),'augmentor-dsh-controls-'));let chrome,panel,server;
 t.after(async()=>{panel?.close();if(chrome?.exitCode===null){const end=once(chrome,'exit');chrome.kill('SIGTERM');await end;}await server?.close();await rm(profile,{recursive:true,force:true,maxRetries:5,retryDelay:100});});
 const selection={provider:'fixture',model:'chosen'},queue={revision:0,paused:false,activeTurnId:null,items:[]},answers=[];
 let pending={method:'approval/requested',rpcId:'approve',payload:{toolName:'fixture_write',reason:'Synthetic approval; no tool is executed.'}};
 const host={getMeta:()=>({id:'fixture',cwd:profile,selection}),queueSnapshot:()=>queue,interactions:{frames:()=>pending?[pending]:[]},dispatch:async(method,p)=>{
  if(method==='host.describe')return {workspace:profile};
  if(method==='models.list')return {groups:[{provider:'fixture',name:'Fixture',models:[{...selection,name:'Chosen'}]}],default:selection,failures:[]};
  if(method==='session.list')return {items:[{sessionId:'fixture',cwd:profile,title:'Synthetic interaction',running:false}]};
  if(method==='session.history')return {events:[],hasMore:false};
  if(method==='observation.list')return {records:[]};
  if(method==='session.models')return {current:selection};
  if(method==='session.reasoning')return {availableLevels:['off'],thinkingLevel:'off'};
  if(method==='session.goal')return {goal:null};
  if(method==='session.queue')return queue;
  if(method==='interaction.respond'){answers.push(p);const id=pending.rpcId;pending=null;server.publish('fixture',{method:'interaction/resolved',rpcId:id,payload:{sessionId:'fixture'}});return {accepted:true};}
  throw Error('Unexpected fixture RPC: '+method);
 }};
 server=new HarnessServer(host);const link=await server.start();
 chrome=spawn(process.env.CHROMIUM_BIN??'chromium',['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run','--remote-debugging-port=0','--user-data-dir='+profile,link.url],{stdio:'ignore'});
 let port;await until(async()=>{port=await chromiumPort(profile).catch(()=>null);return !!port;},'Chrome ready');
 const target=(await fetch('http://127.0.0.1:'+port+'/json').then(r=>r.json())).find(x=>x.type==='page');panel=await harnessCdp(target.webSocketDebuggerUrl);await panel.call('Runtime.enable');await panel.call('Log.enable');
 const visible=expression=>until(()=>panel.evaluate('Boolean('+expression+')'),expression);
 const click=expression=>harnessPointerClick(panel,expression,until);
 await visible('document.body.innerText.includes("Waiting for approval")');await click('Array.from(document.querySelectorAll("button")).find(x=>x.textContent==="Reject")');
 await until(()=>answers.length===1,'approval answered');assert.equal(answers[0].sessionId,'fixture');assert.deepEqual(answers[0].value,{outcome:'denied'});
 pending={method:'question/requested',rpcId:'question',payload:{questions:[{id:'answer',header:'Choose',question:'Which fixture option?',options:[{label:'First'},{label:'Second'}]}]}};server.publish('fixture',pending);
 await visible('document.body.innerText.includes("Which fixture option?")');await click('Array.from(document.querySelectorAll("button")).find(x=>x.textContent.includes("First"))');
 await click('Array.from(document.querySelectorAll("button")).find(x=>x.textContent==="Submit")');
 await until(()=>answers.length===2,'question answered');assert.equal(answers[1].rpcId,'question');assert.deepEqual(answers[1].value.answer.answers[0].selected,['First']);assert.equal(answers[1].sessionId,'fixture');assert.deepEqual(panel.errors,[]);
});
