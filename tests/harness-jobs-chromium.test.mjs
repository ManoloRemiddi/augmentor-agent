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
import {harnessPointerClick} from './fixtures/harness-pointer.mjs';
test('original DSH Jobs view retains explicit child evidence through a fresh refresh',{skip:process.platform!=='linux',timeout:60000},async t=>{
 const f=await planFixture(t,{desktopMode:{}}),sid='original-jobs-evidence',profile=await mkdtemp(join(tmpdir(),'augmentor-original-jobs-'));let chrome,panel;
 t.after(async()=>{panel?.close();if(chrome?.exitCode===null){const ended=once(chrome,'exit');chrome.kill('SIGTERM');await ended;}await rm(profile,{recursive:true,force:true,maxRetries:5,retryDelay:100});});
 await f.call('session.create',{sessionId:sid,selection:f.selection,cwd:f.workspace});await f.prompt(sid,{kind:'read'});
 const admission=await f.call('session.startJob',{sessionId:sid,spec:{requestId:crypto.randomUUID(),kind:'desktop',task:JSON.stringify({task:'Click the independent synthetic button',successCriteria:'Synthetic screen displays DONE',constraints:'Stay in the synthetic screen'}),allowedTools:[],limits:{timeoutMs:60000,maxRequests:24,maxTools:40,maxOutputTokens:24576}}});
 await until(async()=>(await f.call('session.jobs',{sessionId:sid})).items.some(row=>row.id===admission.job.id&&row.state==='completed'),'original view child completed');
 const history=await f.call('session.history',{sessionId:sid}),modelCount=f.requests.length;
 chrome=spawn(process.env.CHROMIUM_BIN??'chromium',['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run','--remote-debugging-port=0','--user-data-dir='+profile,(await f.link()).url+'&session='+sid],{env:f.env,stdio:'ignore'});
 let port;await until(async()=>{assert.equal(chrome.exitCode,null);try{port=await chromiumPort(profile);return !!port;}catch{return false;}},'original Jobs Chromium ready');const targets=await fetch('http://127.0.0.1:'+port+'/json').then(r=>r.json());panel=await harnessCdp(targets.find(row=>row.type==='page').webSocketDebuggerUrl);await panel.call('Runtime.enable');await panel.call('Network.enable');
 const visible=expression=>until(()=>panel.evaluate('Boolean('+expression+')'),expression).catch(async error=>{error.message+=' '+JSON.stringify({body:await panel.evaluate('document.body.innerText'),errors:panel.errors,owner:f.errors()});throw error;});
 const control=label=>'Array.from(document.querySelectorAll(".augmentor-extension button")).find(el=>el.textContent==='+JSON.stringify(label)+')',click=label=>harnessPointerClick(panel,control(label),until);
 const jobsTab='Array.from(document.querySelectorAll("[role=tab]")).find(el=>el.textContent==="Jobs")';await visible(jobsTab);await harnessPointerClick(panel,jobsTab,until);
 await visible(control('desktop · completed · '+admission.job.id));await click('desktop · completed · '+admission.job.id);
 const section='Array.from(document.querySelectorAll(".augmentor-extension details")).find(el=>el.querySelector("summary")?.textContent==="Child originals and provider observations")';await visible(section);await harnessPointerClick(panel,section+'.querySelector("summary")',until);
 await click('Inspect child native originals');await visible('document.querySelector(".augmentor-extension").textContent.includes("indexed original selected ancestry")');
 await harnessPointerClick(panel,'Array.from(document.querySelectorAll(".augmentor-extension button")).find(el=>el.textContent.startsWith("message · toolResult"))',until);await visible('document.querySelector(".augmentor-extension").textContent.includes("desktop_finish")');
 await click('Inspect child provider observations');const request='Array.from(document.querySelectorAll(".augmentor-extension details")).find(el=>el.querySelector("summary")?.textContent.includes("model/request"))';await visible(request);await harnessPointerClick(panel,request+'.querySelector("summary")',until);await harnessPointerClick(panel,request+'.querySelector("button")',until);await visible('document.querySelector(".augmentor-extension").textContent.includes("bounded desktop specialist")');
 await panel.evaluate('globalThis.originalJobsHeader=document.querySelector(".augmentor-extension h3");globalThis.originalJobsEvidence='+section);
 panel.pauseRpcMethods=new Set(['session.jobHistory']);await panel.call('Fetch.enable',{patterns:[{urlPattern:'*/api/rpc',requestStage:'Response'}]});await click('Refresh jobs');await until(()=>panel.pausedRequests.length===1,'original fresh history held');
 const retained=()=>panel.evaluate('originalJobsEvidence.isConnected&&originalJobsEvidence.open&&originalJobsEvidence.textContent.includes("indexed original selected ancestry")&&originalJobsEvidence.textContent.includes("desktop_finish")&&originalJobsEvidence.textContent.includes("bounded desktop specialist")');assert.equal(await retained(),true,'original pending refresh preserves open evidence');
 const editor='Array.from(document.querySelectorAll(".augmentor-extension details")).find(el=>el.querySelector("summary")?.textContent==="Start a bounded job")';
 await harnessPointerClick(panel,editor+'.querySelector("summary")',until);
 await panel.evaluate('(()=>{const field=document.querySelector("[aria-label=\\"Background job task\\"]");field.value="Authored draft opened during retained history refresh";field.dispatchEvent(new Event("input"));})()');
 panel.pauseRpcMethods.clear();const held=panel.pausedRequests[0];await panel.call('Fetch.continueRequest',{requestId:held.id});await until(()=>panel.finishedRequests.has(held.networkId),'original history delivered');await visible('document.querySelector(".augmentor-extension h3")!==originalJobsHeader');assert.equal(await retained(),true,'original completed refresh preserves open evidence');
 assert.equal(await panel.evaluate(editor+'.open'),true,'fresh history cannot close a job draft opened during its read');
 assert.equal(await panel.evaluate('document.querySelector("[aria-label=\\"Background job task\\"]").value'),'Authored draft opened during retained history refresh');
 await harnessPointerClick(panel,editor+'.querySelector("summary")',until);
 const reads=[...panel.requests.values()].filter(row=>row.method==='session.jobPayload').length;await harnessPointerClick(panel,request+'.querySelector("button")',until);await until(async()=>[...panel.requests.values()].filter(row=>row.method==='session.jobPayload').length===reads+1&&await panel.evaluate('Array.from(originalJobsEvidence.querySelectorAll("button")).every(el=>!el.disabled)'),'original retained payload callback completes once');
 assert.equal(f.requests.length,modelCount);assert.deepEqual(await f.call('session.history',{sessionId:sid}),history);assert.deepEqual(panel.errors,[]);assert.equal(f.errors(),'');
});
test('actual Harness job controls show output safely, stop a child and enforce scoped cold read-only evidence',{skip:process.platform!=='linux',timeout:60000},async t=>{
 const f=await planFixture(t,{jobMode:{}}),sid='jobs-ui',profile=await mkdtemp(join(tmpdir(),'augmentor-jobs-chrome-'));let chrome,panel;
 t.after(async()=>{panel?.close();if(chrome?.exitCode===null){const ended=once(chrome,'exit');chrome.kill('SIGTERM');await ended;}await rm(profile,{recursive:true,force:true,maxRetries:5,retryDelay:100});});
 await f.call('session.create',{sessionId:sid,selection:f.selection,cwd:f.workspace});await f.prompt(sid,{kind:'read'});await f.call('session.rename',{sessionId:sid,title:'Jobs UI fixture'});
 chrome=spawn(process.env.CHROMIUM_BIN??'chromium',['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run','--remote-debugging-port=0','--user-data-dir='+profile,(await f.link()).url.replace('/#','/inspection#')],{env:f.env,stdio:'ignore'});
 let port;await until(async()=>{assert.equal(chrome.exitCode,null);try{port=await chromiumPort(profile);return !!port;}catch{return false;}},'jobs Chromium ready');const targets=await fetch('http://127.0.0.1:'+port+'/json').then(r=>r.json());panel=await harnessCdp(targets.find(row=>row.type==='page').webSocketDebuggerUrl);await panel.call('Runtime.enable');await panel.call('Page.enable');
 const visible=expression=>until(()=>panel.evaluate(expression),expression).catch(async error=>{error.message+=' '+JSON.stringify({body:await panel.evaluate('document.body.innerText'),errors:panel.errors,owner:f.errors()});throw error;});
 await visible('document.querySelector("#runtime")?.textContent.includes("Pi 1.1.0")&&!document.querySelector("#send").disabled');await panel.evaluate('Array.from(document.querySelectorAll("#sessions button")).find(b=>b.textContent==="Jobs UI fixture").click()');await visible('sessionStorage.getItem("augmentor-harness-session")==="jobs-ui"&&!document.querySelector("#send").disabled');await panel.evaluate('document.querySelector("[data-view=jobs]").click()');await visible('document.querySelector("#jobs-content").textContent.includes("No background jobs")');
 const literal='<img src=x onerror="globalThis.jobsInjected=true"> café 日本語';
 const control=label=>'Array.from(document.querySelectorAll("#jobs-content button")).find(b=>b.textContent==='+JSON.stringify(label)+')',click=label=>harnessPointerClick(panel,control(label),until);
 const stage=async task=>{await panel.evaluate('(()=>{const el=document.querySelector("[aria-label=\\"Background job task\\"]");el.value='+JSON.stringify(JSON.stringify(task))+';el.dispatchEvent(new Event("input"));})()');},launch=async task=>{await stage(task);await click('Start job');};
 await panel.call('Network.enable');panel.pauseRpcMethods=new Set();await panel.call('Fetch.enable',{patterns:[{urlPattern:'*/api/rpc',requestStage:'Response'}]});
 const holdInspection=async()=>{const before=panel.pausedRequests.length;panel.pauseRpcMethods=new Set(['session.jobs']);await panel.evaluate('document.querySelector("[data-view=jobs]").click()');await until(()=>panel.pausedRequests.length>before,'actual older job list held');return {before,release:async()=>{panel.pauseRpcMethods.clear();const reads=panel.pausedRequests.slice(before);for(const read of reads.reverse()){await panel.call('Fetch.continueRequest',{requestId:read.id});await until(()=>panel.finishedRequests.has(read.networkId),'held job response delivered');}}};};
 await panel.evaluate('document.querySelector("#jobs-content details summary").click()');await stage({kind:'worker-reply',reply:literal});const initial=await holdInspection(),body=await panel.call('Fetch.getResponseBody',{requestId:panel.pausedRequests[initial.before].id});assert.equal(JSON.parse(body.base64Encoded?Buffer.from(body.body,'base64').toString():body.body).result.items.length,0);
 await click('Start job');await until(async()=>(await f.call('session.jobs',{sessionId:sid})).items.length===1,'displayed Start admitted during inspection');await until(()=>panel.pausedRequests.length>initial.before+1,'post-start job list held');await initial.release();
 await visible('document.querySelector("#jobs-content").textContent.includes("recorded once")&&document.querySelector("#jobs-content").textContent.includes('+JSON.stringify(literal)+')');assert.equal(await panel.evaluate('document.querySelectorAll("#jobs-content img").length'),0);assert.equal(await panel.evaluate('globalThis.jobsInjected===true'),false);
 assert.equal([...panel.requests.values()].filter(row=>row.method==='session.startJob').length,1,'one Start request, without retry');
 const job=(await f.call('session.jobs',{sessionId:sid})).items[0];assert.equal(job.state,'completed');
 const sourceSummary='Array.from(document.querySelectorAll("#jobs-content summary")).find(e=>e.textContent==="Child originals and provider observations")';await visible(sourceSummary);await harnessPointerClick(panel,sourceSummary,until);
 const heldEvidence=await holdInspection(),requestsBeforeRead=f.requests.length;await click('Inspect child native originals');await visible('document.querySelector("#jobs-content").textContent.includes("indexed original selected ancestry")');await heldEvidence.release();assert.equal(await panel.evaluate('document.querySelector("#jobs-content").textContent.includes("indexed original selected ancestry")'),true,'older list response cannot erase the explicit evidence view');assert.equal(f.requests.length,requestsBeforeRead,'explicit evidence inspection starts no inference');
 await panel.evaluate('document.querySelector("#jobs-content details summary").click()');await launch({kind:'worker-hold'});await visible('document.querySelector("#jobs-content").textContent.includes("worker holding")');const stopping=await holdInspection();await click('Stop job');await until(async()=>(await f.call('session.jobs',{sessionId:sid})).items.some(j=>j.state==='cancelled'),'displayed Stop admitted during inspection');await until(()=>panel.pausedRequests.length>stopping.before+1,'post-stop job list held');await stopping.release();await visible('document.querySelector("#jobs-content h3")?.textContent.startsWith("cancelled")');
 assert.equal([...panel.requests.values()].filter(row=>row.method==='session.startJob').length,2);assert.equal([...panel.requests.values()].filter(row=>row.method==='session.cancelJob').length,1,'one child Stop request, without retry');
 await panel.call('Emulation.setDeviceMetricsOverride',{width:640,height:900,deviceScaleFactor:1,mobile:false});assert.equal(await panel.evaluate('document.documentElement.scrollWidth<=innerWidth'),true);
 // Controlled frontend receipts exercise owner replacement while two different
 // operations are pending. The actual producers/permissions are covered above.
 const modelCount=f.requests.length;
 const ownerProbe=await panel.evaluate('('+String(async()=>{
  const {attachJobs}=await import('/jobs.js'),container=document.createElement('div');document.body.append(container);
  let context={sessionId:'probe-old-owner',epoch:1,readOnly:false},releaseOld,failNew;const writes=[];
  const oldJob={id:'probe-old-job',kind:'delegate',state:'completed',childId:'probe-old-child',owner:'probe-old-owner',spec:{task:'Synthetic old task',allowedTools:[],limits:{}},usageAccounted:true};
  const rpc=async(method,params)=>{
   if(method==='session.jobs')return {items:context.sessionId==='probe-old-owner'?[oldJob]:[]};
   if(method==='session.job')return {job:oldJob,output:{chunks:[],next:0,lossy:false}};
   if(method==='session.jobHistory')return {events:[]};
   if(method==='session.jobNativeHistory')return new Promise(resolve=>{releaseOld=resolve;});
   if(method==='session.startJob'){writes.push(params);return new Promise((_resolve,reject)=>{failNew=reject;});}
   throw Error('Unexpected controlled frontend method');
  };
  const view=attachJobs({container,rpc,current:()=>context}),frames=()=>new Promise(done=>requestAnimationFrame(()=>requestAnimationFrame(done))),button=label=>[...container.querySelectorAll('button')].find(el=>el.textContent===label),input=label=>container.querySelector('[aria-label="'+label+'"]');
  try{
   await view.refresh();button('delegate · completed · probe-old-job').click();await frames();button('Inspect child native originals').click();await frames();
   if(!releaseOld)throw Error('Controlled old-owner evidence request was not dispatched');
   context={sessionId:'probe-new-owner',epoch:2,readOnly:false};view.reset();await view.refresh();
   input('Background job kind').value='desktop';input('Background job kind').dispatchEvent(new Event('input'));
   input('Background job task').value='Preserve this new-owner draft';input('Background job task').dispatchEvent(new Event('input'));button('Start job').click();await frames();
   if(!failNew)throw Error('Controlled new-owner Start was not dispatched');
   const disabledBefore=button('Start job').disabled;
   releaseOld({coverage:{marker:'OLD_OWNER_PRIVATE_EVIDENCE'},entries:[]});await frames();
   const isolated={startDisabled:button('Start job').disabled,grantsDisabled:input('Delegated tool grants').disabled,oldEvidenceAbsent:!container.textContent.includes('OLD_OWNER_PRIVATE_EVIDENCE')};
   button('Start job').click();await frames();const writesWhilePending=writes.length;
   failNew(Error('Synthetic unconfirmed acknowledgement'));await frames();
   return {disabledBefore,isolated,writesWhilePending,writes:writes.map(row=>({sessionId:row.sessionId,requestId:row.spec.requestId})),draftPreserved:input('Background job task').value==='Preserve this new-owner draft',kindPreserved:input('Background job kind').value==='desktop',grantsStillDisabled:input('Delegated tool grants').disabled,recovered:!button('Start job').disabled,status:container.textContent.includes('The draft and request ID are preserved.')};
  }finally{view.reset();container.remove();}
 })+')()');
 assert.equal(ownerProbe.disabledBefore,true);assert.deepEqual(ownerProbe.isolated,{startDisabled:true,grantsDisabled:true,oldEvidenceAbsent:true});assert.equal(ownerProbe.writesWhilePending,1);assert.equal(ownerProbe.writes.length,1);assert.equal(ownerProbe.writes[0].sessionId,'probe-new-owner');assert(ownerProbe.writes[0].requestId);for(const key of ['draftPreserved','kindPreserved','grantsStillDisabled','recovered','status'])assert.equal(ownerProbe[key],true,key);assert.equal(f.requests.length,modelCount);
 const evidenceScope=await panel.evaluate('('+String(async()=>{
  const {attachJobs}=await import('/jobs.js'),container=document.createElement('div');document.body.append(container);
  let context={sessionId:'scope-owner',epoch:1,readOnly:false},child='scope-child',available=true,failRead=false,reads=0;
  const job=()=>({id:'scope-job',kind:'delegate',state:'completed',childId:child,owner:context.sessionId,spec:{task:'Synthetic evidence scope',allowedTools:[],limits:{}},usageAccounted:true});
  const rpc=async method=>{
   if(method==='session.jobs'){if(failRead)throw Error('Synthetic denied refresh');return {available,items:available?[job()]:[],reason:'Synthetic unavailable jobs'};}
   if(method==='session.job')return {job:job(),output:{chunks:[],next:0,lossy:false}};
   if(method==='session.jobHistory')return {events:[]};
   if(method==='session.jobNativeHistory'){reads++;return {coverage:{marker:'SCOPED_NATIVE_EVIDENCE'},entries:[]};}
   throw Error('Unexpected evidence scope method');
  };
  const view=attachJobs({container,rpc,current:()=>context}),frames=()=>new Promise(done=>requestAnimationFrame(()=>requestAnimationFrame(done))),button=label=>[...container.querySelectorAll('button')].find(el=>el.textContent===label);
  const open=async()=>{await view.refresh();button('delegate · completed · scope-job').click();await frames();button('Inspect child native originals').click();await frames();if(!container.textContent.includes('SCOPED_NATIVE_EVIDENCE'))throw Error('Scoped fixture evidence did not open');return [...container.querySelectorAll('details')].find(el=>el.querySelector('summary')?.textContent==='Child originals and provider observations');};
  const gone=el=>!el.isConnected&&!container.textContent.includes('SCOPED_NATIVE_EVIDENCE');
  try{
   const first=await open();await view.refresh();const retained=first.isConnected&&container.textContent.includes('SCOPED_NATIVE_EVIDENCE')&&reads===1;
   child='different-child';await view.refresh();const changedChild=gone(first);
   const second=await open();context={...context,readOnly:true};await view.refresh();const changedAccess=gone(second)&&!container.querySelector('textarea');
   const third=await open();available=false;await view.refresh();const unavailable=gone(third);
   available=true;const fourth=await open();failRead=true;await view.refresh();const denied=gone(fourth);
   failRead=false;const fifth=await open();view.reset();return {retained,changedChild,changedAccess,unavailable,denied,reset:gone(fifth),reads};
  }finally{view.reset();container.remove();}
 })+')()');
 assert.deepEqual(evidenceScope,{retained:true,changedChild:true,changedAccess:true,unavailable:true,denied:true,reset:true,reads:5});assert.equal(f.requests.length,modelCount);
 const count=f.requests.length;await f.stop();await f.start();const inspection=await f.call('inspection.open',{sessionId:sid}),link=new URL(inspection.url.replace('/#','/inspection#')),token=new URLSearchParams(link.hash.slice(1)).get('token');
 await panel.call('Page.navigate',{url:inspection.url.replace('/#','/inspection#')});await panel.reload();await visible('document.querySelector("#runtime")?.textContent.includes("Read-only")');await panel.evaluate('document.querySelector("[data-view=jobs]").click()');await visible('document.querySelector("#jobs-content").textContent.includes("completed")');assert.equal(await panel.evaluate('document.querySelectorAll("#jobs-content textarea").length'),0);
 for(const [method,params,reason] of [['session.job',{sessionId:'other',jobId:job.id},/selected conversation/],['session.startJob',{sessionId:sid,spec:{}},/read-only/]]){const response=await fetch(link.origin+'/api/rpc',{method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:JSON.stringify({id:crypto.randomUUID(),method,params})});assert.match((await response.json()).error.message,reason);}
 assert.equal(f.requests.length,count);assert.deepEqual(panel.errors,[]);assert.equal(f.errors(),'');
});
test('actual Harness desktop jobs preserve briefs, expose child originals and payloads, and allow scoped cold inspection',{skip:process.platform!=='linux',timeout:60000},async t=>{
 const mode={},f=await planFixture(t,{desktopMode:mode}),sid='desktop-jobs-ui',profile=await mkdtemp(join(tmpdir(),'augmentor-desktop-jobs-chrome-'));let chrome,panel;
 t.after(async()=>{panel?.close();if(chrome?.exitCode===null){const ended=once(chrome,'exit');chrome.kill('SIGTERM');await ended;}await rm(profile,{recursive:true,force:true,maxRetries:5,retryDelay:100});});
 await f.call('session.create',{sessionId:sid,selection:f.selection,cwd:f.workspace});await f.prompt(sid,{kind:'read'});await f.call('session.rename',{sessionId:sid,title:'Desktop Jobs UI fixture'});
 chrome=spawn(process.env.CHROMIUM_BIN??'chromium',['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run','--remote-debugging-port=0','--user-data-dir='+profile,(await f.link()).url.replace('/#','/inspection#')],{env:f.env,stdio:'ignore'});
 let port;await until(async()=>{assert.equal(chrome.exitCode,null);try{port=await chromiumPort(profile);return !!port;}catch{return false;}},'desktop jobs Chromium ready');const targets=await fetch('http://127.0.0.1:'+port+'/json').then(r=>r.json());panel=await harnessCdp(targets.find(row=>row.type==='page').webSocketDebuggerUrl);await panel.call('Runtime.enable');await panel.call('Page.enable');
 const visible=expression=>until(()=>panel.evaluate(expression),expression).catch(async error=>{error.message+=' '+JSON.stringify({body:await panel.evaluate('document.body.innerText'),errors:panel.errors,owner:f.errors()});throw error;});
 const click=label=>panel.evaluate('Array.from(document.querySelectorAll("#jobs-content button")).find(b=>b.textContent==='+JSON.stringify(label)+').click()');
 await visible('document.querySelector("#runtime")?.textContent.includes("Pi 1.1.0")&&!document.querySelector("#send").disabled');await panel.evaluate('Array.from(document.querySelectorAll("#sessions button")).find(b=>b.textContent==="Desktop Jobs UI fixture").click()');await visible('sessionStorage.getItem("augmentor-harness-session")==="desktop-jobs-ui"&&!document.querySelector("#send").disabled');await panel.evaluate('document.querySelector("[data-view=jobs]").click()');await visible('document.querySelector("#jobs-content").textContent.includes("No background jobs")');
 const task='<img src=x onerror="globalThis.desktopJobInjected=true"> click only the synthetic button',criteria='Synthetic screen displays DONE',constraints='Do not type or open another application';
 const prepare=async()=>{await panel.evaluate('document.querySelector("#jobs-content details summary").click()');await panel.evaluate('(()=>{const kind=document.querySelector("[aria-label=\\"Background job kind\\"]");kind.value="desktop";kind.dispatchEvent(new Event("input"));})()');assert.equal(await panel.evaluate('document.querySelector("[aria-label=\\"Delegated tool grants\\"]").disabled'),true);assert.equal(await panel.evaluate('document.querySelector("[aria-label=\\"Background job seconds\\"]").value'),'180');await panel.evaluate('(()=>{for(const [label,value] of '+JSON.stringify([['Background job task',task],['Desktop success criteria',criteria],['Desktop constraints',constraints]])+'){const el=document.querySelector("[aria-label=\\""+label+"\\"]");el.value=value;el.dispatchEvent(new Event("input"));}})()');};
 await prepare();await click('Start job');await visible('document.querySelector("#jobs-content h3")?.textContent.startsWith("completed")&&document.querySelector("#jobs-content").textContent.includes("recorded once")');
 const job=(await f.call('session.jobs',{sessionId:sid})).items[0],receipt=await f.call('session.job',{sessionId:sid,jobId:job.id});assert.deepEqual(JSON.parse(receipt.job.spec.task),{task,successCriteria:criteria,constraints});assert.equal(receipt.job.desktop.status,'completed');assert.equal(await panel.evaluate('globalThis.desktopJobInjected===true'),false);assert.equal(await panel.evaluate('document.querySelectorAll("#jobs-content img").length'),0);
 await click('Inspect child native originals');await visible('document.querySelector("#jobs-content").textContent.includes("indexed original selected ancestry")');await panel.evaluate('Array.from(document.querySelectorAll("#jobs-content button")).find(b=>b.textContent.startsWith("message · toolResult")).click()');await visible('Array.from(document.querySelectorAll("#jobs-content pre")).some(el=>el.textContent.includes("\\\"toolName\\\":\\\"desktop_finish\\\""))');
 await click('Inspect child provider observations');await visible('document.querySelector("#jobs-content").textContent.includes("model/request")');await panel.evaluate('(()=>{const row=Array.from(document.querySelectorAll("#jobs-content details")).find(el=>el.querySelector("summary")?.textContent.includes("model/request"));row.querySelector("button").click();})()');await visible('Array.from(document.querySelectorAll("#jobs-content pre")).some(el=>el.textContent.includes("bounded desktop specialist"))');
 // A fresh list is legitimate: it must update the producer summary without
 // discarding the native/provider excerpts the user explicitly opened. Hold
 // the final history read to also observe the panel during that refresh.
 await panel.evaluate('globalThis.jobsEvidenceHeader=document.querySelector("#jobs-content h3");globalThis.jobsEvidenceSection=Array.from(document.querySelectorAll("#jobs-content details")).find(el=>el.querySelector("summary")?.textContent==="Child originals and provider observations");jobsEvidenceSection.open=true');
 const requestsBeforeRefresh=f.requests.length;
 await panel.call('Network.enable');panel.pauseRpcMethods=new Set(['session.jobHistory']);await panel.call('Fetch.enable',{patterns:[{urlPattern:'*/api/rpc',requestStage:'Response'}]});
 await harnessPointerClick(panel,'document.querySelector("[data-view=jobs]")',until);await until(()=>panel.pausedRequests.length===1,'fresh job history held');
 const retained=()=>panel.evaluate('jobsEvidenceSection.isConnected&&jobsEvidenceSection.open&&jobsEvidenceSection.textContent.includes("indexed original selected ancestry")&&jobsEvidenceSection.textContent.includes("desktop_finish")&&jobsEvidenceSection.textContent.includes("bounded desktop specialist")');
 assert.equal(await retained(),true,'fresh pending refresh preserves explicitly opened originals and payloads');
 panel.pauseRpcMethods.clear();const read=panel.pausedRequests[0];await panel.call('Fetch.continueRequest',{requestId:read.id});await until(()=>panel.finishedRequests.has(read.networkId),'fresh job history delivered');await visible('document.querySelector("#jobs-content h3")!==jobsEvidenceHeader');
 assert.equal(await retained(),true,'completed fresh refresh preserves the evidence section and its open state');
 const payloadReads=[...panel.requests.values()].filter(row=>row.method==='session.jobPayload').length;
 await click('Read child captured payload');await until(async()=>[...panel.requests.values()].filter(row=>row.method==='session.jobPayload').length===payloadReads+1&&await panel.evaluate('Array.from(jobsEvidenceSection.querySelectorAll("button")).filter(el=>el.textContent==="Read child captured payload").every(el=>!el.disabled)'),'retained child payload callback completes once');assert.equal(f.requests.length,requestsBeforeRefresh,'refresh and retained evidence callbacks start no inference');
 await panel.call('Emulation.setDeviceMetricsOverride',{width:640,height:900,deviceScaleFactor:1,mobile:false});assert.equal(await panel.evaluate('document.documentElement.scrollWidth<=innerWidth'),true);
 mode.holdAfterAction=true;await prepare();await click('Start job');await visible('document.querySelector("#jobs-content h3")?.textContent.startsWith("running")');assert.equal(await panel.evaluate('jobsEvidenceSection.isConnected'),false,'selecting another child removes the previous inspection');await until(()=>f.desktop.calls.filter(c=>c.method==='action').length===2,'second independent input');await click('Stop job');await visible('document.querySelector("#jobs-content h3")?.textContent.startsWith("cancelled")');
 const count=f.requests.length;await f.stop();const calls=f.desktop.calls.length;await f.start();const inspection=await f.call('inspection.open',{sessionId:sid}),link=new URL(inspection.url.replace('/#','/inspection#')),token=new URLSearchParams(link.hash.slice(1)).get('token');await panel.call('Page.navigate',{url:inspection.url.replace('/#','/inspection#')});await panel.reload();await visible('document.querySelector("#runtime")?.textContent.includes("Read-only")');await panel.evaluate('document.querySelector("[data-view=jobs]").click()');await visible('document.querySelector("#jobs-content").textContent.includes("completed")');await click('desktop · completed · '+job.id);await visible('document.querySelector("#jobs-content h3")?.textContent.startsWith("completed")');await click('Inspect child native originals');await visible('document.querySelector("#jobs-content").textContent.includes("indexed original selected ancestry")');assert.equal(await panel.evaluate('document.querySelectorAll("#jobs-content textarea").length'),0);
 const rpc=async(method,params)=>{const response=await fetch(link.origin+'/api/rpc',{method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:JSON.stringify({id:crypto.randomUUID(),method,params})});return response.json();};
 assert((await rpc('session.jobObservations',{sessionId:sid,jobId:job.id,limit:30})).result.records.length);for(const [method,params] of [['session.jobNativeHistory',{sessionId:'other',jobId:job.id}],['session.nativeHistory',{sessionId:job.childId}],['session.startJob',{sessionId:sid,spec:{}}]])assert.match((await rpc(method,params)).error.message,/selected conversation|read-only/);
 assert.equal(f.requests.length,count);assert.equal(f.desktop.calls.length,calls);assert.deepEqual(panel.errors,[]);assert.equal(f.errors(),'');
});
