// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Real Pi owner and Chromium, authored profiles/provider; curation never sends a request.
import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {mkdtemp,readFile,writeFile,rm} from 'node:fs/promises';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {fileURLToPath} from 'node:url';
import {chromiumPort} from './fixtures/chromium-ready.mjs';
import {harnessCdp} from './fixtures/harness-cdp.mjs';
import {harnessPointerClick} from './fixtures/harness-pointer.mjs';
const source=fileURLToPath(new URL('../',import.meta.url));
async function until(fn,label){const end=Date.now()+12000;let last;while(Date.now()<end){try{if(await fn())return;}catch(e){last=e;}await new Promise(resolve=>setTimeout(resolve,30));}throw Error(label+(last?' '+last.message:''));}

test('MX picker shows and saves effort, opens at the top, saves ordered pins, hides models and contains the context meter',{skip:!['linux','darwin'].includes(process.platform),timeout:60000},async t=>{
 const profile=await mkdtemp(join(tmpdir(),'augmentor-picker-'));let fixture,chrome,panel,link,output='',stderr='';
 t.after(async()=>{panel?.close();for(const child of [chrome,fixture])if(child?.pid&&child.exitCode===null){const ended=once(child,'exit');child.kill('SIGTERM');await ended;}await rm(profile,{recursive:true,force:true,maxRetries:5,retryDelay:100});});
 const env=Object.fromEntries(Object.entries(process.env).filter(([key])=>!/^(AUGMENTOR_|DSH_|PI_)/.test(key)));
 for(const key of ['AUGMENTOR_PI_TEST_ROOT','AUGMENTOR_PYTHON'])if(process.env[key])env[key]=process.env[key];
 fixture=spawn(process.execPath,[join(source,'scripts/harness-ui-proof.mjs')],{cwd:source,env:{...env,AUGMENTOR_HARNESS_PROOF_RECORD_REQUESTS:'1'},stdio:['ignore','pipe','pipe']});
 fixture.stdout.on('data',b=>output+=b);fixture.stderr.on('data',b=>stderr+=b);
 await until(()=>{assert.equal(fixture.exitCode,null,stderr);try{link=JSON.parse(output.split('\n').find(line=>line.startsWith('{"fixture"')));return !!link;}catch{return false;}},'private Host ready');
 const url=new URL(link.url),token=new URLSearchParams(url.hash.slice(1)).get('token');
 const rpc=async(method,params={},credential=token)=>{const response=await fetch(url.origin+'/api/rpc',{method:'POST',headers:{Authorization:'Bearer '+credential,'Content-Type':'application/json'},body:JSON.stringify({id:crypto.randomUUID(),method,params})});const body=await response.json();if(body.error)throw Error(body.error.message);return body.result;};
 const modelFile=join(link.config,'agent/models.json'),models=JSON.parse(await readFile(modelFile,'utf8'));
 const original=models.providers.fixture;
 models.providers={
  openai:{models:[{id:'gpt-4',name:'Authored single OpenAI entry'}]},
  'fixture-many':{...structuredClone(original),name:'Authored catalog',models:Array.from({length:40},(_,i)=>({...structuredClone(original.models[0]),id:'extra-'+i,name:'Authored extra '+i}))},
  'fixture-twin':{...structuredClone(original),name:'Authored twin',models:original.models.map(m=>({...m,name:'Authored twin model'}))},
  'fixture-needs-auth':{...structuredClone(original),apiKey:undefined,name:'Authored missing credential',models:original.models.map(m=>({...m,name:'Authored credentials needed'}))},
  fixture:original,
 };
 await writeFile(modelFile,JSON.stringify(models));await rpc('models.settingsRefresh');
 const initial=await rpc('models.list'),selection=initial.default;
 assert.deepEqual(initial.groups.map(g=>g.provider).sort(),['fixture','fixture-many','fixture-needs-auth','fixture-twin','openai'],'bundled unconfigured providers must not appear');
 assert.equal(initial.groups.reduce((n,g)=>n+g.models.length,0),44);
 assert.equal(initial.groups.find(g=>g.provider==='fixture-many').name,'Authored catalog');
 assert.deepEqual(initial.groups.find(g=>g.provider==='openai').models.map(m=>m.model),['gpt-4'],'explicit built-in profile must not expand into every bundled model');
 assert.deepEqual(initial.groups.map(g=>g.provider),Object.keys(models.providers),'configured provider order must survive');
 await rpc('session.create',{sessionId:'picker-parent',cwd:link.workspace,selection});
 await rpc('session.prompt',{sessionId:'picker-parent',requestId:'picker-seed',content:[{type:'text',text:'Independent seed before model configuration.'}]});
 await until(async()=>(await rpc('session.history',{sessionId:'picker-parent'})).events.some(row=>row.event.type==='turn/end'),'authored seed settled');
 const initialHistory=await rpc('session.history',{sessionId:'picker-parent'}),initialRequests=await readFile(link.requestLog,'utf8');
 chrome=spawn(process.env.CHROMIUM_BIN??'chromium',['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run','--remote-debugging-port=0','--user-data-dir='+profile,url.href],{env,stdio:'ignore'});
 let port;await until(async()=>{port=await chromiumPort(profile).catch(()=>null);return !!port;},'Chromium ready');
 const target=(await fetch('http://127.0.0.1:'+port+'/json').then(r=>r.json())).find(row=>row.type==='page');panel=await harnessCdp(target.webSocketDebuggerUrl);await Promise.all(['Runtime.enable','Network.enable','Log.enable','Page.enable'].map(method=>panel.call(method)));
 const q=selector=>'document.querySelector('+JSON.stringify(selector)+')';
 const button=(label,root='document')=>'Array.from('+root+'.querySelectorAll("button")).find(e=>(e.getAttribute("aria-label")||e.textContent.trim())==='+JSON.stringify(label)+')';
 const click=expression=>harnessPointerClick(panel,expression,until);
 const visible=expression=>until(()=>panel.evaluate('Boolean('+expression+')'),expression);
 const menu=q('[role=menu][aria-label="Model"]'),search=q('[role=searchbox]');
 const openPicker=async()=>{await click(q('[aria-label^="Select model"]'));await click('Array.from(document.querySelectorAll("[role=menuitem]")).find(e=>e.textContent.startsWith("Model"))');await visible(menu);};
 const closePicker=async()=>{await panel.call('Input.dispatchKeyEvent',{type:'keyDown',key:'Escape'});await panel.call('Input.dispatchKeyEvent',{type:'keyUp',key:'Escape'});await panel.call('Input.dispatchKeyEvent',{type:'keyDown',key:'Escape'});await panel.call('Input.dispatchKeyEvent',{type:'keyUp',key:'Escape'});};
 await visible(q('[aria-label^="Select model"]'));await openPicker();
 assert.equal(await panel.evaluate(menu+'.scrollTop'),0,'un-pinned current model near the catalog tail must not move opening scroll');
 assert(await panel.evaluate(menu+'.scrollHeight>'+menu+'.clientHeight*3'));
 await closePicker();
 // The real DSH selector consumes effort.name, not effort.label. Check visible
 // options and actual saved changes so blank-but-clickable rows cannot pass.
 const openEffort=async()=>{await click(q('[aria-label^="Select model"]'));await click('Array.from(document.querySelectorAll("[role=menuitem]")).find(e=>e.textContent.startsWith("Effort"))');await visible(q('[role=menuitemradio]'));};
 const availableLevels=initial.groups.find(g=>g.provider===selection.provider).models.find(m=>m.model===selection.model).thinkingLevels;
 await openEffort();
 assert.deepEqual(await panel.evaluate('Array.from(document.querySelectorAll("[role=menuitemradio]")).map(e=>e.textContent.trim())'),availableLevels,'every supported effort must have a visible label');
 await click('Array.from(document.querySelectorAll("[role=menuitemradio]")).find(e=>e.textContent.trim()==="high")');
 await visible(q('[aria-label^="Select model"]')+'.textContent.includes("high")');
 let reasoning=await rpc('session.reasoning',{sessionId:'picker-parent'});assert.equal(reasoning.thinkingLevel,'high');assert.equal(reasoning.mode,'manual');
 await panel.reload();await visible(q('[aria-label^="Select model"]')+'.textContent.includes("high")');await openEffort();
 assert.equal(await panel.evaluate('document.querySelector("[role=menuitemradio][aria-checked=true]").textContent.trim()'),'high');
 await click('Array.from(document.querySelectorAll("[role=menuitemradio]")).find(e=>e.textContent.trim()==="off")');
 await visible(q('[aria-label^="Select model"]')+'.textContent.includes("off")');
 reasoning=await rpc('session.reasoning',{sessionId:'picker-parent'});assert.equal(reasoning.thinkingLevel,'off');
 assert.equal(await readFile(link.requestLog,'utf8'),initialRequests,'changing/reloading effort must not dispatch a provider request');
 await click(q('[aria-label="Settings"]'));await click(button('Model Picker Augmented'));
 const settings=q('section[aria-label="Model Picker Augmented"]');await visible(settings);
 const setQuery=async value=>{await click(q('[aria-label="Search picker settings"]'));await panel.call('Input.dispatchKeyEvent',{type:'keyDown',key:'a',code:'KeyA',modifiers:2});await panel.call('Input.dispatchKeyEvent',{type:'keyUp',key:'a',code:'KeyA',modifiers:2});await panel.call('Input.insertText',{text:value});};
 await setQuery('fixture');
 await click(button('Pin Harness deterministic fixture (fixture)',settings));await visible(button('Unpin Harness deterministic fixture (fixture)',settings));
 await click(button('Pin Authored twin model (fixture-twin)',settings));await visible(button('Unpin Authored twin model (fixture-twin)',settings));
 await click(button('Move up Authored twin model (fixture-twin)',settings));
 await until(async()=>(await rpc('models.list')).pinned[0]==='fixture-twin/'+selection.model,'pin reorder persisted');
 const saved=await rpc('models.list');assert.deepEqual(saved.pinned,['fixture-twin/'+selection.model,'fixture/'+selection.model]);
 await assert.rejects(rpc('models.curate',{provider:'fixture',model:selection.model,action:'hide',revision:initial.revision}),/settings changed/);
 await click(button('Hide Authored twin model (fixture-twin)',settings));await visible(button('Show Authored twin model (fixture-twin)',settings));
 await click(button('Show Authored twin model (fixture-twin)',settings));await visible(button('Hide Authored twin model (fixture-twin)',settings));
 await panel.reload();await visible(q('[aria-label^="Select model"]'));await openPicker();
 assert.equal(await panel.evaluate(menu+'.scrollTop'),0);
 assert.deepEqual(await panel.evaluate('Array.from('+menu+'.querySelectorAll("button")).slice(0,2).map(e=>e.textContent.trim())'),['Authored twin model','Harness deterministic fixture']);
 assert.equal(await panel.evaluate('Array.from('+menu+'.querySelectorAll("button")).filter(e=>e.textContent.trim()==="Authored twin model").length'),1);
 assert.equal(await panel.evaluate('Array.from('+menu+'.querySelectorAll("button")).filter(e=>e.textContent.trim()==="Harness deterministic fixture").length'),1);
 assert.equal(await panel.evaluate(menu+'.querySelectorAll("[aria-checked=true]").length'),1,'same model ID on two providers must check only the actual selection');
 await click(search);await panel.call('Input.insertText',{text:'Authored twin model'});await visible(menu+'.querySelectorAll("button").length===1');
 await panel.call('Input.dispatchKeyEvent',{type:'keyDown',key:'ArrowDown'});await panel.call('Input.dispatchKeyEvent',{type:'keyUp',key:'ArrowDown'});
 assert.equal(await panel.evaluate(menu+'.querySelector("[data-highlighted]").textContent.trim()'),'Authored twin model');
 await closePicker();await openPicker();assert.equal(await panel.evaluate(menu+'.scrollTop'),0);await closePicker();
 for(const width of [1440,666,420]){
  await panel.call('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:false});
  await visible(q('[data-composer-card] button[aria-label$="of context used"]'));
  const layout=await panel.evaluate('(()=>{const e=document.querySelector("button[aria-label$=\\"of context used\\"]"),c=e.closest("[data-composer-card]"),r=e.getBoundingClientRect(),b=c.getBoundingClientRect();return {inside:!!c,footer:!!e.closest("[data-composer-dock]"),fits:r.left>=b.left&&r.right<=b.right&&r.top>=b.top&&r.bottom<=b.bottom,overflow:document.documentElement.scrollWidth>innerWidth}})()');
  assert.deepEqual(layout,{inside:true,footer:false,fits:true,overflow:false},'context meter at width '+width);
 }
 await panel.call('Emulation.setDeviceMetricsOverride',{width:1440,height:900,deviceScaleFactor:1,mobile:false});
 await openPicker();await click(search);await panel.call('Input.insertText',{text:'Authored twin model'});await visible(menu+'.querySelectorAll("button").length===1');
 await panel.call('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter'});await panel.call('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter'});
 await visible('!'+menu);assert.equal((await rpc('session.models',{sessionId:'picker-parent'})).current.provider,'fixture-twin');
 const unavailable=initial.groups.find(group=>group.provider!=='fixture'&&group.provider!=='fixture-twin'&&group.models.some(model=>!model.available));
 const rejected=unavailable.models.find(model=>!model.available),selectsBefore=[...panel.requests.values()].filter(row=>row.method==='session.selectModel').length;
 await openPicker();await click(search);await panel.call('Input.insertText',{text:rejected.name});
 await visible(menu+'.innerText.includes("Credentials required")');
 await click('Array.from('+menu+'.querySelectorAll("button")).find(e=>e.title==='+JSON.stringify(rejected.name)+')');
 await visible('document.body.innerText.includes("needs credentials")');
 assert.equal((await rpc('session.models',{sessionId:'picker-parent'})).current.provider,'fixture-twin');
 assert.equal([...panel.requests.values()].filter(row=>row.method==='session.selectModel').length,selectsBefore+1,'failed selection never replays');
 await closePicker();
 await assert.rejects(rpc('models.curate',{provider:'fixture',model:selection.model,action:'hide',revision:saved.revision},'missing'),/Open Augmentor Harness from your Applications menu to reconnect this browser/);
 assert.equal((await rpc('session.list')).items.length,1);assert.deepEqual(await rpc('session.history',{sessionId:'picker-parent'}),initialHistory);
 assert.equal(await readFile(link.requestLog,'utf8'),initialRequests);
 assert.equal(panel.failedResponses.length,1);const rejectedResponse=panel.failedResponses[0];
 assert.equal(rejectedResponse.status,400);assert.equal(panel.requests.get(rejectedResponse.id)?.method,'session.selectModel');
 assert.equal(panel.errors.length,1);assert.equal(panel.errors[0].source,'network');assert.equal(panel.errors[0].networkRequestId,rejectedResponse.id);
 assert.equal(panel.errors[0].url,url.origin+'/api/rpc');

});
