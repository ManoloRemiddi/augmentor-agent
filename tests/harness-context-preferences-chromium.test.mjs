// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {chromiumPort} from './fixtures/chromium-ready.mjs';
// Original settings navigation against the real owner; no model requests.
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
test('original Context preferences persist across Host restart, drive dashboard defaults and enforce stale/read-only guards',{skip:process.platform!=='linux',timeout:60000},async t=>{
 const profile=await mkdtemp(join(tmpdir(),'augmentor-context-chrome-'));let fixture,chrome,panel,owner,link,output='',stderr='';
 t.after(async()=>{owner?.close();panel?.close();for(const child of [chrome,fixture])if(child?.pid&&child.exitCode===null){const ended=once(child,'exit');child.kill('SIGTERM');await ended;}await rm(profile,{recursive:true,force:true,maxRetries:5,retryDelay:100});});
 const env=Object.fromEntries(Object.entries(process.env).filter(([key])=>!/^(AUGMENTOR_|DSH_|PI_)/.test(key)));for(const key of ['AUGMENTOR_PI_TEST_ROOT','AUGMENTOR_PYTHON'])if(process.env[key])env[key]=process.env[key];
 fixture=spawn(process.execPath,[join(source,'scripts/harness-ui-proof.mjs')],{cwd:source,env:{...env,AUGMENTOR_HARNESS_PROOF_RECORD_REQUESTS:'1',AUGMENTOR_HARNESS_PROOF_PROMPTS:'1',AUGMENTOR_HARNESS_PROOF_REOPEN:'1'},stdio:['ignore','pipe','pipe','ipc']});fixture.stdout.on('data',data=>output+=data);fixture.stderr.on('data',data=>stderr+=data);
 await until(()=>{assert.equal(fixture.exitCode,null,stderr);try{link=JSON.parse(output.trim().split('\n').find(line=>line.startsWith('{"fixture"')));return !!link;}catch{return false;}},'owner ready');
 let url=new URL(link.url),token=new URLSearchParams(url.hash.slice(1)).get('token');
 const rpc=async(method,params={},bearer=token)=>{const response=await fetch(url.origin+'/api/rpc',{method:'POST',headers:{Authorization:'Bearer '+bearer,'Content-Type':'application/json'},body:JSON.stringify({id:crypto.randomUUID(),method,params})}),frame=await response.json();if(frame.error)throw Error(frame.error.message);return frame.result;};
 const socket=localConnect(join(link.state,'runtime.sock'));await once(socket,'connect');owner=new PiConnection(socket);await owner.call('host.hello',{protocol:'augmentor-pi/1'});
 chrome=spawn(process.env.CHROMIUM_BIN??'chromium',['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run','--remote-debugging-port=0','--user-data-dir='+profile,link.url],{env,stdio:'ignore'});
 let port;await until(async()=>{try{port=await chromiumPort(profile);return !!port;}catch{return false;}},'Chrome ready');
 const target=(await fetch('http://127.0.0.1:'+port+'/json').then(r=>r.json())).find(row=>row.type==='page');panel=await harnessCdp(target.webSocketDebuggerUrl);await panel.call('Emulation.setDeviceMetricsOverride',{width:513,height:715,deviceScaleFactor:1,mobile:false});await panel.reload();for(const domain of ['Runtime','Log','Network','Page'])await panel.call(domain+'.enable');
 const visible=expression=>until(()=>panel.evaluate('Boolean('+expression+')'),expression).catch(async error=>{error.message+=' '+JSON.stringify({body:await panel.evaluate('document.body.innerText'),composer:await panel.evaluate('Array.from(document.querySelectorAll("[contenteditable]")).map(x=>x.outerHTML)'),focus:await panel.evaluate('document.activeElement.outerHTML'),errors:panel.errors,fixture:stderr});throw error;});
 const click=expression=>harnessPointerClick(panel,expression,until);
 const button=(label,within='document')=>'Array.from('+within+'.querySelectorAll("button")).find(x=>x.textContent.trim()==='+JSON.stringify(label)+')';
 const shell='document.querySelector("[data-shortcut-modal=settings]")';
 const originalOrigin=url.origin;
 const settings='document.querySelector("button[aria-label=\\"Settings\\"]")';
 const prefs=async()=>{await click(settings);await click(button('Plugins',shell));await visible('document.querySelector(".lc-settings-prefs")');};
 const row=label=>'Array.from(document.querySelectorAll(".lc-settings-row")).find(x=>x.querySelector(".lc-settings-label")?.textContent==='+JSON.stringify(label)+')';
 const choice=label=>row(label)+'.querySelector("button")';
 const namespace=async()=>((await rpc('settings.describe')).namespaces.find(x=>x.ns==='dsh-context'));
 const select=async(label,value)=>{await visible(choice(label)+'&&!'+choice(label)+'.disabled');await click(choice(label));const item='Array.from(document.querySelectorAll("[role=menuitem]")).find(x=>x.textContent.trim()==='+JSON.stringify(value)+')';await visible(item);await click(item);};
 const pick=async(label,value)=>{await select(label,value);await visible(choice(label)+'.textContent.trim()==='+JSON.stringify(value)+'&&!'+choice(label)+'.disabled');};
 await visible('document.querySelector("button[aria-label=\\"New session\\"]")');await click('document.querySelector("button[aria-label=\\"New session\\"]")');await visible('document.querySelector("[contenteditable=true]")');
 const sid=(await rpc('session.list')).items[0].sessionId,history=await rpc('session.history',{sessionId:sid});
 await prefs();assert(!await panel.evaluate(choice('Placement')+'.disabled'));assert(await panel.evaluate(choice('Fleet tab')+'.disabled'));assert(await panel.evaluate('Array.from(document.querySelectorAll(".lc-settings-textarea")).every(x=>x.disabled)'));
 for(const width of [513,1440]){await panel.call('Emulation.setDeviceMetricsOverride',{width,height:715,deviceScaleFactor:1,mobile:false});assert(await panel.evaluate('document.documentElement.scrollWidth<=innerWidth&&Array.from(document.querySelectorAll(".lc-settings-textarea")).every(x=>x.getBoundingClientRect().height<120)'),'original card stays within the viewport and retains supplier textarea sizing');}await panel.call('Emulation.setDeviceMetricsOverride',{width:513,height:715,deviceScaleFactor:1,mobile:false});
 await pick('Context Insights entry','Hide');assert(!await panel.evaluate('document.querySelector("button[aria-label=\\"Context Insights\\"]")'));await panel.reload();await visible(settings);await prefs();assert.equal((await namespace()).value.insightsEntry,'hide');await pick('Context Insights entry','Show');await visible('document.querySelector("button[aria-label=\\"Context Insights\\"]")');
 await pick('Trend Chart · Granularity','Turn');await pick('Trend Chart · Display','Delta');await pick('Trend Chart · Duration curve','Hide');await pick('Context Browser · Diff baseline','prev turn');await pick('Tool Schemas · Sort','By name');await pick('File Activity · Sort','By path');
 const saved=await namespace();for(const [field,value] of Object.entries({defaultGranularity:'turn',defaultTrendMode:'delta',defaultDurationCurve:'hide',defaultDeltaBase:'turn',defaultToolSort:'name',defaultFileSort:'path'}))assert.equal(saved.value[field],value);
 const mutate=(field,value,revision)=>rpc('settings.mutate',{ns:'dsh-context',expectedRevision:revision,ops:[{op:'set',path:[field],value}]});
 await assert.rejects(()=>mutate('fleetTab','show',saved.revision),/not supported/);assert.deepEqual(await namespace(),saved);
 // A second operator changes the profile. The stale card refuses once, restores
 // the served default and freezes until an explicit read; no replay.
 await mutate('defaultFileSort','latest',saved.revision);await select('Tool Schemas · Sort','By calls');await visible('document.body.innerText.includes("Nothing was retried")');assert.equal((await namespace()).value.defaultToolSort,'name');
 const attempts=[...panel.requests.values()].filter(x=>x.method==='settings.mutate').length;await click(button('Refresh Context preferences',shell));await visible(choice('Tool Schemas · Sort')+'.textContent.trim()==="By name"&&!'+choice('Tool Schemas · Sort')+'.disabled');assert.equal([...panel.requests.values()].filter(x=>x.method==='settings.mutate').length,attempts);
 await click(button('Open Context',shell));await visible('document.querySelector(".augmentor-context-dashboard")');
 assert(await panel.evaluate('Array.from(document.querySelectorAll(".lc-root button")).some(x=>x.textContent==="Turn"&&x.classList.contains("lc-gran-on"))'),'saved granularity is the original mount default');assert(await panel.evaluate('Array.from(document.querySelectorAll(".lc-root button")).some(x=>x.textContent==="Delta"&&x.classList.contains("lc-gran-on"))'),'saved display is the original mount default');assert(!await panel.evaluate('Array.from(document.querySelectorAll(".lc-root button")).find(x=>x.textContent==="Duration")?.classList.contains("lc-gran-on")'));
 // Cold owner restart retains the independently authored private profile.
 await panel.call('Page.navigate',{url:'about:blank'});owner.close();fixture.send({type:'reopen'});await until(()=>{try{link=output.trim().split('\n').filter(x=>x.startsWith('{"fixture"')).map(JSON.parse).find(x=>x.reopened);return !!link;}catch{return false;}},'cold Host reopened');url=new URL(link.url);token=new URLSearchParams(url.hash.slice(1)).get('token');const socket2=localConnect(join(link.state,'runtime.sock'));await once(socket2,'connect');owner=new PiConnection(socket2);await owner.call('host.hello',{protocol:'augmentor-pi/1'});await panel.call('Page.navigate',{url:link.url});await visible(settings);await prefs();assert.equal((await namespace()).value.defaultGranularity,'turn');assert.equal((await namespace()).value.defaultFileSort,'latest');
 const access=await owner.call('inspection.open',{sessionId:sid});await panel.call('Page.navigate',{url:access.url});await visible('document.querySelector("[data-composer-input][aria-disabled=true]")');await prefs();assert(await panel.evaluate('Array.from(document.querySelectorAll(".lc-settings-select,.lc-settings-textarea")).every(x=>x.disabled)'));const bearer=new URLSearchParams(new URL(access.url).hash.slice(1)).get('token');await assert.rejects(()=>rpc('settings.describe',{},bearer),/read-only/);await assert.rejects(()=>rpc('settings.mutate',{ns:'dsh-context',expectedRevision:saved.revision,ops:[{op:'set',path:['insightsEntry'],value:'hide'}]},bearer),/read-only/);
 assert.deepEqual(await rpc('session.history',{sessionId:sid}),history);assert.equal(await readFile(link.requestLog,'utf8').catch(e=>{if(e.code==='ENOENT')return '';throw e;}),'');assert.deepEqual(panel.errors.filter(x=>!String(x.text??'').includes('400')),[]);assert(!panel.urls.some(value=>/^https?:/.test(value)&&!value.startsWith(url.origin+'/')&&!value.startsWith(originalOrigin+'/')),'no supplier external requests');
});
