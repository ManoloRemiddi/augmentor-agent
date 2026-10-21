// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Original GUI + actual Pi Host; authored sessions, no inference during controls.
import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {mkdtemp,rm,readFile} from 'node:fs/promises';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {fileURLToPath} from 'node:url';
import {setTimeout as delay} from 'node:timers/promises';
import {chromiumPort} from './fixtures/chromium-ready.mjs';
import {harnessCdp} from './fixtures/harness-cdp.mjs';
import {harnessPointerClick,harnessHoverPointerClick} from './fixtures/harness-pointer.mjs';

const source=fileURLToPath(new URL('../',import.meta.url));
async function until(fn,label){const end=Date.now()+12000;while(Date.now()<end){if(await fn())return;await delay(30);}throw Error('Workspace ordering timeout: '+label);}
test('original restored row survives an actual older catalog reply and opens without inference or replay',{skip:process.platform!=='linux',timeout:45000},async t=>{
 const profile=await mkdtemp(join(tmpdir(),'augmentor-workspace-order-'));let fixture,chrome,panel,link,output='',stderr='';
 t.after(async()=>{panel?.close();for(const child of [chrome,fixture])if(child?.pid&&child.exitCode===null){const ended=once(child,'exit');child.kill('SIGTERM');await ended;}await rm(profile,{recursive:true,force:true,maxRetries:5,retryDelay:100});});
 const env=Object.fromEntries(Object.entries(process.env).filter(([key])=>!/^(AUGMENTOR_|DSH_|PI_)/.test(key)));for(const key of ['AUGMENTOR_PI_TEST_ROOT','AUGMENTOR_PYTHON'])if(process.env[key])env[key]=process.env[key];
 fixture=spawn(process.execPath,[join(source,'scripts/harness-ui-proof.mjs')],{cwd:source,env:{...env,AUGMENTOR_HARNESS_PROOF_RECORD_REQUESTS:'1'},stdio:['ignore','pipe','pipe']});fixture.stdout.on('data',data=>output+=data);fixture.stderr.on('data',data=>stderr+=data);
 await until(()=>{assert.equal(fixture.exitCode,null,stderr);try{link=JSON.parse(output.trim().split('\n').find(line=>line.startsWith('{"fixture"')));return !!link;}catch{return false;}},'private owner ready');
 const url=new URL(link.url),token=new URLSearchParams(url.hash.slice(1)).get('token');
 const rpc=async(method,params={})=>{const response=await fetch(url.origin+'/api/rpc',{method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:JSON.stringify({id:crypto.randomUUID(),method,params})}),frame=await response.json();if(frame.error)throw Error(frame.error.message);return frame.result;};
 const selected='authored-selected-catalog',restored='authored-restored-catalog',selection=(await rpc('models.list')).default;
 const directories=await rpc('workspace.list');await rpc('workspace.adopt',{path:link.workspace,expectedRevision:directories.revision});
 for(const sessionId of [selected,restored])await rpc('session.create',{sessionId,cwd:link.workspace,selection});
 // Original sidebar rows exclude nonselected blank sessions. Seed a genuine
 // retained SDK turn, then prove the catalog controls never continue it.
 await rpc('session.prompt',{sessionId:restored,requestId:crypto.randomUUID(),content:[{type:'text',text:'Read the isolated fixture note for catalog ordering.'}]});
 await until(async()=>(await rpc('session.history',{sessionId:restored})).events.some(row=>row.event.type==='turn/end'),'authored seed turn settled');
 const history=await rpc('session.history',{sessionId:restored}),providerBefore=await readFile(link.requestLog,'utf8');assert(providerBefore.trim());
 const original=await rpc('workspace.list');await rpc('session.organize',{sessionId:restored,action:'archive',expectedRevision:original.organizationRevision});
 chrome=spawn(process.env.CHROMIUM_BIN??'chromium',['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run','--remote-debugging-port=0','--user-data-dir='+profile,link.url+'&session='+selected],{env,stdio:'ignore'});
 let port;await until(async()=>{try{port=await chromiumPort(profile);return !!port;}catch{return false;}},'Chromium ready');
 const target=(await fetch('http://127.0.0.1:'+port+'/json').then(r=>r.json())).find(row=>row.type==='page');panel=await harnessCdp(target.webSocketDebuggerUrl);for(const domain of ['Runtime','Log','Network','Page'])await panel.call(domain+'.enable');await panel.call('Emulation.setDeviceMetricsOverride',{width:513,height:715,deviceScaleFactor:1,mobile:false});await panel.reload();
 const visible=expression=>until(()=>panel.evaluate('Boolean('+expression+')'),expression),click=expression=>harnessPointerClick(panel,expression,until),row=id=>'document.querySelector('+JSON.stringify('[data-row-key="session:'+id+'"]')+')';
 await visible('sessionStorage.getItem("augmentor-harness-session")==='+JSON.stringify(selected)+'&&document.querySelector("[contenteditable=true]")');
 if(await panel.evaluate('Boolean(document.querySelector("button[aria-label=\\"Open sidebar\\"]"))'))await click('document.querySelector("button[aria-label=\\"Open sidebar\\"]")');
 await click('document.querySelector("button[aria-label=\\"View options\\"]")');await click('Array.from(document.querySelectorAll("[role=menuitem]")).find(x=>x.textContent.includes("All conversations (show archived)"))');await visible(row(restored));
 panel.pauseRpcMethods=new Set(['workspace.list']);await panel.call('Fetch.enable',{patterns:[{urlPattern:'*/api/rpc',requestStage:'Response'}]});
 await until(()=>panel.pausedRequests.some(value=>value.rpcMethod==='workspace.list'),'actual old catalog response held');
 const held=panel.pausedRequests.find(value=>value.rpcMethod==='workspace.list'),body=await panel.call('Fetch.getResponseBody',{requestId:held.id}),snapshot=JSON.parse(body.base64Encoded?Buffer.from(body.body,'base64').toString('utf8'):body.body).result;
 assert(snapshot.archivedSessionIds.includes(restored),'The actual held response predates restore');panel.pauseRpcMethods.delete('workspace.list');
 await harnessHoverPointerClick(panel,row(restored),row(restored)+'.querySelector("button[aria-label=\\"Unarchive session\\"]")',until);
 const archive=row(restored)+'.querySelector("button[aria-label=\\"Archive session\\"]")';await visible(archive);
 const confirmed=await rpc('workspace.list');assert(!confirmed.archivedSessionIds.includes(restored));assert(confirmed.organizationRevision>snapshot.organizationRevision);
 await panel.call('Fetch.continueRequest',{requestId:held.id});await until(()=>panel.finishedRequests.has(held.networkId),'old catalog response consumed');
 await panel.evaluate('new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))');
 assert.equal(await panel.evaluate('Boolean('+archive+')'),true,'A late old refresh cannot re-archive the original restored row');
 assert.equal(await panel.evaluate('sessionStorage.getItem("augmentor-harness-session")'),selected,'The existing selected conversation is preserved');
 await panel.call('Fetch.disable');await click(row(restored));await visible('sessionStorage.getItem("augmentor-harness-session")==='+JSON.stringify(restored)+'&&document.querySelector("[contenteditable=true]")');
 assert.equal([...panel.requests.values()].filter(value=>value.method==='session.organize'&&value.params.action==='restore').length,1,'One explicit restore is never replayed');
 assert.equal(await readFile(link.requestLog,'utf8'),providerBefore,'Catalog controls start no additional provider request');assert.deepEqual(await rpc('session.history',{sessionId:restored}),history,'Retained SDK history stays unchanged');assert.equal(panel.errors.length,0,JSON.stringify(panel.errors));assert(panel.urls.every(value=>value.startsWith(url.origin)||value.startsWith('data:')));
});
