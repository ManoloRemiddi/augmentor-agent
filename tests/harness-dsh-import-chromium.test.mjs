// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Authored historical data only; actual offline importer, Pi Host and original DSH GUI.
import test from 'node:test';import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';import {once} from 'node:events';
import {mkdtemp,writeFile,rename,rm} from 'node:fs/promises';import {join} from 'node:path';import {tmpdir} from 'node:os';import {createHash} from 'node:crypto';import {setTimeout as delay} from 'node:timers/promises';
import {planFixture} from './fixtures/plans.mjs';import {chromiumPort} from './fixtures/chromium-ready.mjs';import {harnessCdp} from './fixtures/harness-cdp.mjs';import {harnessPointerClick} from './fixtures/harness-pointer.mjs';
import {importDshProject} from '../dist/runtime/src/dsh-project-import.js';
async function until(fn,label){const end=Date.now()+12000;while(Date.now()<end){if(await fn())return;await delay(30);}throw Error('Imported trajectory timeout: '+label);}
test('large imported history renders virtualized Trajectory and inspection without replay or page errors',{skip:process.platform!=='linux',timeout:60000},async t=>{
 const f=await planFixture(t,{policy:'read-only'});await f.stop();await rename(f.state,f.state+'-before-import');
 const rows=[],add=(type,data)=>rows.push({type:'event',event:{seq:rows.length,time:1700000000000+rows.length,type,data}});
 add('turn/start',{turn:1});add('user/message',{role:'user',source:{kind:'user'},content:[{type:'text',text:'Authored historical project inspection.'}]});
 for(let i=0;i<140;i++){
  const id='authored-call-'+i;add('assistant/message',{turn:1,step:i+1,message:{role:'assistant',content:[{type:'tool-call',id,name:'read',arguments:JSON.stringify({path:'authored-'+i+'.txt'})}]}});
  add('tool/call',{turn:1,step:i+1,callId:id,name:'read',arguments:JSON.stringify({path:'authored-'+i+'.txt'})});add('tool/result',{turn:1,step:i+1,message:{role:'tool',toolCallId:id,content:[{type:'text',text:'Authored historical result '+i}],isError:false}});
 }
 add('assistant/message',{turn:1,step:141,message:{role:'assistant',content:[{type:'text',text:'Authored historical inspection completed.'}]}});add('turn/end',{turn:1,reason:{kind:'completed'}});
 const value={schema:'augmentor-dsh-project-export/1',workspace:{path:f.workspace,title:'Authored migrated project',sessionIds:['authored-long']},sessions:[{opening:{header:{id:'authored-long',cwd:f.workspace},cursor:rows.length-1,projections:{values:{title:'Authored migrated history'}}},records:rows}]},bytes=JSON.stringify(value),source=join(f.root,'authored-export.json');await writeFile(source,bytes,{mode:0o600});
 const receipt=importDshProject(source,f.state,{sourceSha256:createHash('sha256').update(bytes).digest('hex'),selection:f.selection});await f.start();const link=await f.link();assert.equal(f.requests.length,0);
 const profile=await mkdtemp(join(tmpdir(),'augmentor-import-chrome-'));let chrome,panel;t.after(async()=>{panel?.close();if(chrome?.exitCode===null){const ended=once(chrome,'exit');chrome.kill('SIGTERM');await ended;}await rm(profile,{recursive:true,force:true,maxRetries:5,retryDelay:100});});
 chrome=spawn(process.env.CHROMIUM_BIN??'chromium',['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run','--remote-debugging-port=0','--user-data-dir='+profile,link.url],{env:f.env,stdio:'ignore'});let port;await until(async()=>{try{port=await chromiumPort(profile);return !!port;}catch{return false;}},'Chrome ready');
 const target=(await fetch('http://127.0.0.1:'+port+'/json').then(r=>r.json())).find(x=>x.type==='page');panel=await harnessCdp(target.webSocketDebuggerUrl);for(const domain of ['Runtime','Log','Page','Network'])await panel.call(domain+'.enable');await panel.call('Emulation.setDeviceMetricsOverride',{width:1440,height:900,deviceScaleFactor:1,mobile:false});
 const visible=expr=>until(async()=>{assert.deepEqual(panel.errors,[]);return panel.evaluate('Boolean('+expr+')');},expr),click=expr=>harnessPointerClick(panel,expr,until);
 await visible('document.body?.innerText.includes("Authored migrated project") && document.querySelector("[contenteditable=true]")');
 await click('Array.from(document.querySelectorAll("[role=tab]")).find(x=>x.textContent==="Trajectory")');await visible('document.querySelector("tr[data-virtual-position]")');
 const rendered=await panel.evaluate('document.querySelectorAll("tr[data-virtual-position]").length');assert(rendered>0&&rendered<140,'long timeline is virtualized');await visible('document.body?.innerText.includes("Authored historical inspection completed")');
 assert.equal(f.requests.length,0);assert.equal((await f.call('session.queue',{sessionId:receipt.sessionId})).items.length,0);assert.deepEqual(panel.failedResponses,[]);assert.deepEqual(panel.errors,[]);
 await f.call('events.subscribe',{sessionId:receipt.sessionId});await f.prompt(receipt.sessionId,{kind:'read'});await visible('document.body?.innerText.includes(\"Synthetic planning reply\")');assert.equal(f.requests.length,2,'only the new explicit turn generates provider requests');assert.deepEqual(f.frames.filter(x=>x.method==='session/event'&&x.payload.event.type==='tool/call').map(x=>x.payload.event.data.name),['plan_read']);
 await click('Array.from(document.querySelectorAll(\"tr[data-record-index]\")).at(-1)');await visible('document.querySelector(\"[role=tabpanel]\")?.innerText.includes(\"Synthetic planning reply\")');
 await click('Array.from(document.querySelectorAll("[role=tab]")).find(x=>x.textContent==="Chat")');await visible('document.querySelector("[contenteditable=true]") && document.body?.innerText.includes("Authored historical inspection completed")');assert.equal(f.requests.length,2);assert.deepEqual(panel.errors,[]);
});
