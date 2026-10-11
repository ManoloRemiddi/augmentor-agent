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
import {Interactions} from '../dist/runtime/src/interactions.js';
import {contextPreferences,CONTEXT_PREFERENCE_OPTIONS} from '../dist/runtime/src/context-preferences.js';
import {chromiumPort} from './fixtures/chromium-ready.mjs';
import {harnessCdp} from './fixtures/harness-cdp.mjs';
import {harnessPointerClick} from './fixtures/harness-pointer.mjs';
async function until(fn,label){const end=Date.now()+10000;while(Date.now()<end){if(await fn())return;await delay(25);}throw Error(label);}
test('original DSH approval/question components answer the selected Host interaction',{skip:process.platform!=='linux',timeout:30000},async t=>{
 const profile=await mkdtemp(join(tmpdir(),'augmentor-dsh-controls-'));let chrome,panel,server;
 t.after(async()=>{panel?.close();if(chrome?.exitCode===null){const end=once(chrome,'exit');chrome.kill('SIGTERM');await end;}await server?.close();await rm(profile,{recursive:true,force:true,maxRetries:5,retryDelay:100});});
 const selection={provider:'fixture',model:'chosen'},queue={revision:0,paused:false,activeTurnId:null,items:[]},answers=[];
 let compaction={available:true,busy:false,blocked:false,lastReceipt:null};
 const interactions=new Interactions((sid,frame)=>server?.publish(sid,frame),()=>true,20000);
 t.after(()=>interactions.cancel('fixture'));
 const approval=interactions.ask('fixture','approval/requested',{toolName:'fixture_write',reason:'Synthetic approval; no tool is executed.'});
 const waits=[];
 const host={getMeta:()=>({id:'fixture',cwd:profile,selection}),queueSnapshot:()=>queue,interactions,dispatch:async(method,p)=>{
  if(method==='settings.describe'&&p.ns==='dsh-context')return {namespaces:[{ns:'dsh-context',revision:0,value:contextPreferences({}),writableFields:Object.keys(CONTEXT_PREFERENCE_OPTIONS)}]};
  if(method==='host.describe')return {workspace:profile};
  if(method==='models.list')return {groups:[{provider:'fixture',name:'Fixture',models:[{...selection,name:'Chosen'}]}],default:selection,failures:[]};
  if(method==='session.list')return {items:[{sessionId:'fixture',cwd:profile,title:'Synthetic interaction',running:false}]};
  if(method==='workspace.list')return {revision:0,items:[{workspaceId:profile,cwd:profile,title:'Fixture',sessionIds:['fixture']}],pinnedSessionIds:[],archivedSessionIds:[]};
  if(method==='session.history')return {events:[],hasMore:false};
  if(method==='observation.list')return {records:[]};
  if(method==='session.models')return {current:selection};
  if(method==='session.reasoning')return {availableLevels:['off'],thinkingLevel:'off'};
  if(method==='session.compaction')return compaction;
  if(method==='session.acknowledgeCompaction'){answers.push(p);compaction={...compaction,blocked:false,lastReceipt:{...compaction.lastReceipt,acknowledged:true}};return compaction;}
  if(method==='session.goal')return {goal:null};
  if(method==='session.queue')return queue;
  if(method==='interaction.respond'){answers.push(p);return interactions.answer(p.rpcId,p.value,p.sessionId);}
  if(method==='interaction.wait'){waits.push(p);return interactions.wait(p.rpcId,p.sessionId,p.clientId,p.action);}
  throw Error('Unexpected fixture RPC: '+method);
 }};
 server=new HarnessServer(host);const link=await server.start();
 chrome=spawn(process.env.CHROMIUM_BIN??'chromium',['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run','--remote-debugging-port=0','--user-data-dir='+profile,link.url],{stdio:'ignore'});
 let port;await until(async()=>{port=await chromiumPort(profile).catch(()=>null);return !!port;},'Chrome ready');
 const target=(await fetch('http://127.0.0.1:'+port+'/json').then(r=>r.json())).find(x=>x.type==='page');panel=await harnessCdp(target.webSocketDebuggerUrl);await panel.call('Runtime.enable');await panel.call('Log.enable');
 await panel.call('Emulation.setDeviceMetricsOverride',{width:513,height:715,deviceScaleFactor:1,mobile:false});
 const visible=expression=>until(()=>panel.evaluate('Boolean('+expression+')'),expression);
 const click=expression=>harnessPointerClick(panel,expression,until);
 await visible('document.body?.innerText.includes("Waiting for approval")');await click('Array.from(document.querySelectorAll("button")).find(x=>x.textContent==="Reject")');
 await until(()=>answers.length===1,'approval answered');assert.equal(answers[0].sessionId,'fixture');assert.deepEqual(answers[0].value,{outcome:'denied'});
 assert.deepEqual(await approval,{outcome:'denied'});
 const question=interactions.ask('fixture','question/requested',{questions:[{id:'answer',header:'Choose',question:'Which fixture option?',options:[{label:'First'},{label:'Second'}]}]});const questionId=interactions.frames('fixture')[0].rpcId;
 await visible('document.body?.innerText.includes("Which fixture option?")');await visible('document.body.innerText.includes("Continuing in")');
 await click('Array.from(document.querySelectorAll("button")).find(x=>x.textContent==="Take time")');await visible('document.body.innerText.includes("Waiting until you answer")');
 assert.equal(interactions.frames('fixture')[0].payload.wait.state,'waiting');assert(waits.some(x=>x.action==='take-time'));
 await click('Array.from(document.querySelectorAll("button")).find(x=>x.textContent.includes("First"))');
 await click('document.querySelector("button[aria-label=\\"Collapse the question card\\"]")');await click('document.querySelector("button[aria-label=\\"Expand the question card\\"]")');await visible('document.querySelector("button[role=radio][aria-checked=true]")?.textContent.includes("First")');
 await click('Array.from(document.querySelectorAll("button")).find(x=>x.textContent==="Submit")');
 await until(()=>answers.length===2,'question answered');assert.equal(answers[1].rpcId,questionId);assert.deepEqual(answers[1].value.answer.answers[0].selected,['First']);assert.equal(answers[1].sessionId,'fixture');assert.deepEqual(await question,answers[1].value);
 compaction={available:true,busy:false,blocked:true,lastReceipt:{state:'unknown',requestId:'uncertain-summary',acknowledged:false}};server.publish('fixture',{method:'session/compaction',payload:compaction});
 await visible('document.body.innerText.includes("Compaction outcome unknown; inspect native history")');assert(await panel.evaluate('!!Array.from(document.querySelectorAll("[role=tab]")).find(x=>x.textContent==="Context")'),'empty unknown context still exposes original inspection tabs');
 await click('Array.from(document.querySelectorAll("button")).find(x=>x.textContent==="Acknowledge unknown; do not retry")');await until(()=>answers.length===3,'unknown acknowledgement');assert.equal(answers[2].requestId,'uncertain-summary');assert.equal(answers[2].acknowledgeUnknownOutcome,true);assert.equal(compaction.lastReceipt.state,'unknown');assert(compaction.lastReceipt.acknowledged);assert.deepEqual(panel.errors,[]);
});
