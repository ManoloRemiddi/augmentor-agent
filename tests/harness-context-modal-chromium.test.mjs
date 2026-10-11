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
test('original Context modal preserves chat, exact arguments, close guards and running Stop',{skip:process.platform!=='linux',timeout:60000},async t=>{
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
 const visible=expression=>until(()=>panel.evaluate('Boolean('+expression+')'),expression).catch(async error=>{error.message+=' '+JSON.stringify({body:await panel.evaluate('document.body.innerText'),composer:await panel.evaluate('Array.from(document.querySelectorAll("[contenteditable]")).map(x=>x.outerHTML)'),focus:await panel.evaluate('document.activeElement.outerHTML'),errors:panel.errors,fixture:stderr});throw error;});
 const click=expression=>harnessPointerClick(panel,expression,until);
 const button=(label,within='document')=>'Array.from('+within+'.querySelectorAll("button")).find(x=>x.textContent.trim()==='+JSON.stringify(label)+')';

 const modal='document.querySelector(".lc-modal-card")',composer='document.querySelector("[contenteditable=true]")';
 const key=async name=>{const code=name==='Escape'?27:13;await panel.call('Input.dispatchKeyEvent',{type:'keyDown',key:name,code:name,windowsVirtualKeyCode:code});await panel.call('Input.dispatchKeyEvent',{type:'keyUp',key:name,code:name,windowsVirtualKeyCode:code});};
 const draft=()=>panel.evaluate(composer+'.textContent');
 const open=async()=>{await click(composer);await panel.call('Input.insertText',{text:'/context'});await key('Enter');await visible(modal);};
 await visible('document.querySelector("button[aria-label=\\"New session\\"]")');await click('document.querySelector("button[aria-label=\\"New session\\"]")');await visible(composer+'&&!'+composer+'.hasAttribute("aria-disabled")');
 const sid=(await rpc('session.list')).items[0].sessionId,empty=await rpc('session.history',{sessionId:sid});
 await open();assert.equal(await draft(),'/context','supplier token stays until close');assert(await panel.evaluate(modal+'.innerText.includes("Recorded SDK snapshots: 0 of 0")'));
 await key('Escape');await visible('!'+modal);await visible(composer+'.textContent===""');assert(await panel.evaluate('document.activeElement==='+composer),'Escape restores original composer focus');
 assert.deepEqual(await rpc('session.history',{sessionId:sid}),empty);assert.equal(await readFile(link.requestLog,'utf8').catch(e=>{if(e.code==='ENOENT')return '';throw e;}),'','empty modal adds no inference');
 // Create one real SDK/tool record using independently authored responses.
 await panel.call('Input.insertText',{text:'Read the authored fixture note once.'});await click('document.querySelector("button[aria-label=\\"Send message\\"]")');await visible('document.body.innerText.includes("The note says:")&&!document.querySelector("button[aria-label=\\"Stop generating\\"]")');
 const before=await rpc('session.history',{sessionId:sid}),wire=await readFile(link.requestLog,'utf8');assert.equal(wire.trim().split('\n').length,2);
 await open();await visible(modal+'.querySelector("select[aria-label=\\"Context request\\"]")');
 assert(await panel.evaluate('Array.from(document.querySelectorAll("[role=tab]")).find(x=>x.textContent==="Chat").getAttribute("aria-selected")==="true"'),'modal keeps the original Chat view');
 await click('Array.from('+modal+'.querySelectorAll(".lc-br-cat-row")).find(x=>x.textContent.includes("Tool Results"))');await visible(modal+'.querySelector(".lc-ts-arg-val")?.textContent==='+JSON.stringify(join(link.workspace,'note.txt')));
 assert(await panel.evaluate(modal+'.innerText.includes("Harness fixture ready.")'));
 await click(modal+'.querySelector("button[aria-label=\\"Close\\"]")');await visible('!'+modal+'&&'+composer+'.textContent===""');assert.deepEqual(await rpc('session.history',{sessionId:sid}),before);assert.equal(await readFile(link.requestLog,'utf8'),wire);
 // A changed draft cannot be erased by the original dialog close path.
 await open();assert(await panel.evaluate('document.activeElement==='+composer));await panel.call('Input.insertText',{text:' changed'});const changed=await draft();await key('Escape');await visible('!'+modal);assert.equal(await draft(),changed);
 await until(async()=> (await rpc("draft.describe",{sessionId:sid})).text===changed,"changed Context draft saved");await panel.reload();await visible(composer+"&&"+composer+".textContent==="+JSON.stringify(changed));
 // Clear the restored draft through the original composer before the next fixture.
 await click(composer);await panel.call("Input.dispatchKeyEvent",{type:"keyDown",key:"a",code:"KeyA",windowsVirtualKeyCode:65,modifiers:2});await panel.call("Input.dispatchKeyEvent",{type:"keyUp",key:"a",code:"KeyA",windowsVirtualKeyCode:65,modifiers:2});await panel.call("Input.dispatchKeyEvent",{type:"keyDown",key:"Backspace",code:"Backspace",windowsVirtualKeyCode:8});await panel.call("Input.dispatchKeyEvent",{type:"keyUp",key:"Backspace",code:"Backspace",windowsVirtualKeyCode:8});await visible(composer+'.textContent===""');
 // Capture-phase dialog Escape must not bubble into the running owner's Stop.
 await click(composer);await panel.call('Input.insertText',{text:'SLOW fixture'});await click('document.querySelector("button[aria-label=\\"Send message\\"]")');await visible('document.querySelector("button[aria-label=\\"Stop generating\\"]")&&'+composer+'.textContent===""');
 await open();await key('Escape');await visible('!'+modal);assert.equal((await rpc('session.list')).items.find(x=>x.sessionId===sid).running,true,'Escape closes only the inspection dialog');
 await click('document.querySelector("button[aria-label=\\"Stop generating\\"]")');await visible('!document.querySelector("button[aria-label=\\"Stop generating\\"]")');
 // Switching scope closes the dialog without consuming another session's draft.
 await open();await click('document.querySelector("button[aria-label=\\"New session\\"]")');await visible('!'+modal+'&&'+composer+'.textContent===""');
 const newSid=(await rpc('session.list')).items.find(x=>x.sessionId!==sid).sessionId;assert.equal((await rpc('session.history',{sessionId:newSid})).events.filter(x=>x.event.type==='user/message').length,0);
 assert.deepEqual(panel.errors,[]);assert(!panel.urls.some(value=>/^https?:/.test(value)&&!value.startsWith(url.origin+'/')),'no supplier analytics/registry/price network');
});
