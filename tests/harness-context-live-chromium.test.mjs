// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Original GUI over a real private Pi owner; only delivery of authored frames is delayed.
import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {mkdtemp,readFile,writeFile,rm} from 'node:fs/promises';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {fileURLToPath} from 'node:url';
import {setTimeout as delay} from 'node:timers/promises';
import {chromiumPort} from './fixtures/chromium-ready.mjs';
import {harnessCdp} from './fixtures/harness-cdp.mjs';
import {harnessPointerClick} from './fixtures/harness-pointer.mjs';
const source=fileURLToPath(new URL('../',import.meta.url));
async function until(fn,label){const end=Date.now()+12000;let last;while(Date.now()<end){try{if(await fn())return;}catch(error){last=error;}await delay(30);}throw Error('Live Context timeout: '+label+(last?' ('+last.message+')':''));}

test('open original Raw Context accepts later provenance without rereading its request and retires old reads/errors',{skip:process.platform!=='linux',timeout:60000},async t=>{
 const profile=await mkdtemp(join(tmpdir(),'augmentor-context-live-'));let fixture,chrome,panel,link,output='',stderr='';
 t.after(async()=>{panel?.close();for(const child of [chrome,fixture])if(child?.pid&&child.exitCode===null){const ended=once(child,'exit');child.kill('SIGTERM');await ended;}await rm(profile,{recursive:true,force:true,maxRetries:5,retryDelay:100});});
 const env=Object.fromEntries(Object.entries(process.env).filter(([key])=>!/^(AUGMENTOR_|DSH_|PI_)/.test(key)));for(const key of ['AUGMENTOR_PI_TEST_ROOT','AUGMENTOR_PYTHON'])if(process.env[key])env[key]=process.env[key];
 fixture=spawn(process.execPath,[join(source,'scripts/harness-ui-proof.mjs')],{cwd:source,env:{...env,AUGMENTOR_HARNESS_PROOF_RECORD_REQUESTS:'1'},stdio:['ignore','pipe','pipe']});fixture.stdout.on('data',b=>output+=b);fixture.stderr.on('data',b=>stderr+=b);
 await until(()=>{assert.equal(fixture.exitCode,null,stderr);try{link=JSON.parse(output.split('\n').find(x=>x.startsWith('{"fixture"')));return !!link;}catch{return false;}},'actual owner ready');
 const url=new URL(link.url),token=new URLSearchParams(url.hash.slice(1)).get('token');
 const rpc=async(method,params={})=>{const response=await fetch(url.origin+'/api/rpc',{method:'POST',headers:{authorization:'Bearer '+token,'content-type':'application/json'},body:JSON.stringify({id:crypto.randomUUID(),method,params})}),frame=await response.json();if(frame.error)throw Error(frame.error.message);return frame.result;};
 chrome=spawn(process.env.CHROMIUM_BIN??'chromium',['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],{env,stdio:'ignore'});let port;await until(async()=>{try{port=await chromiumPort(profile);return !!port;}catch{return false;}},'Chromium ready');
 const target=(await fetch('http://127.0.0.1:'+port+'/json').then(r=>r.json())).find(x=>x.type==='page');panel=await harnessCdp(target.webSocketDebuggerUrl);for(const domain of ['Runtime','Log','Network','Page'])await panel.call(domain+'.enable');await panel.call('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
 // Install before the controller captures fetch. Preserve real records, IDs and
 // payloads; split only the delivery of actual observation/event frames.
 await panel.call('Page.addScriptToEvaluateOnNewDocument',{source:`(()=>{
  const fetchOriginal=fetch;const gate=globalThis.__contextDelivery={heldFrames:[],releasedIds:[],releaseFrames:true,holdPayloadFor:null,heldReads:[],completedPayloads:[],retiredReads:0,polls:0};
  globalThis.fetch=async(...args)=>{
   const response=await fetchOriginal(...args);let body;try{body=JSON.parse(args[1]?.body);}catch{}
   if(body?.method==='observation.payload'){
    if(body.params.eventId===gate.holdPayloadFor&&body.params.offset===0)await new Promise((resolve,reject)=>gate.heldReads.push({release:fail=>{gate.retiredReads++;fail?reject(Error('Authored delayed provenance read failure')):resolve();}}));
    const frame=await response.clone().json();if(frame.result?.hasMore===false)gate.completedPayloads.push(body.params.eventId);return response;
   }
   if(String(args[0]).startsWith('/api/events?')){
    gate.polls++;const page=await response.json();const frames=[];
    for(const row of page.frames??[]){if(!gate.releaseFrames&&row.frame.method==='observation/event'&&row.frame.payload.observation.kind==='context/provenance')gate.heldFrames.push(row);else frames.push(row);}
    if(gate.releaseFrames)for(const row of gate.heldFrames.splice(0)){gate.releasedIds.push(row.frame.payload.observation.id);frames.push(row);}
    const headers=new Headers(response.headers);headers.delete('content-length');return new Response(JSON.stringify({...page,frames}),{status:response.status,headers});
   }
   return response;
  };
 })();`});await panel.navigate(link.url);
 const visible=expression=>until(()=>panel.evaluate('Boolean('+expression+')'),expression).catch(async error=>{error.message+=' '+JSON.stringify({body:await panel.evaluate('document.body.innerText'),delivery:await panel.evaluate('({held:__contextDelivery.heldFrames.length,released:__contextDelivery.releasedIds})'),errors:panel.errors,stderr});throw error;}),click=expression=>harnessPointerClick(panel,expression,until);
 const q=css=>'document.querySelector('+JSON.stringify(css)+')',button=label=>'Array.from(document.querySelectorAll("button")).find(x=>x.textContent.trim()==='+JSON.stringify(label)+')',raw='Array.from(document.querySelectorAll("details>summary")).find(x=>x.textContent.trim()==="Raw Pi context and saved entries")';
 await visible(q('button[aria-label="New session"]'));await click(q('button[aria-label="New session"]'));await visible(q('[contenteditable=true]'));const sid=(await rpc('session.list')).items[0].sessionId;
 // The original GUI displays its tab header only after a conversation has work.
 await rpc('session.prompt',{sessionId:sid,requestId:'authored-context-warmup',content:[{type:'text',text:'Read the authored warmup note once.'}]});await visible('document.body.innerText.includes("The note says:")&&!'+q('button[aria-label="Stop generating"]'));
 await click(button('Context'));await visible(raw);await click(raw);await visible(button('▸ Composition coverage'));await panel.evaluate('__contextDelivery.releaseFrames=false');
 await rpc('session.prompt',{sessionId:sid,requestId:'authored-live-context',content:[{type:'text',text:'Read the independently authored fixture note once.'}]});
 const chooser='Array.from(document.querySelectorAll("label")).find(x=>x.textContent.startsWith("Recorded request ")).querySelector("select")';
 await visible(chooser+'.options.length===4&&'+button('▸ Effective provider request'));await visible('__contextDelivery.heldFrames.length===2');
 await visible('document.body.innerText.includes("Recorded provider context: 4 of 4")');
 await until(async()=>(await rpc('session.history',{sessionId:sid})).events.some(x=>x.event.type==='turn/end'),'real turn settled');
 const history=await rpc('session.history',{sessionId:sid}),wire=await readFile(link.requestLog,'utf8'),meta=JSON.parse(await readFile(join(link.state,'sessions',sid+'.meta.json'),'utf8')),native=await readFile(meta.file),display=await readFile(join(link.state,'sessions',sid+'.events.jsonl'));
 assert.equal(wire.trim().split('\n').length,4);const observations=(await rpc('observation.list',{sessionId:sid})).records,requests=observations.filter(x=>x.kind==='model/request'),provenance=observations.filter(x=>x.kind==='context/provenance'),latest=requests.at(-1),latestProvenance=provenance.find(x=>x.requestId===latest.id),firstProvenance=provenance.find(x=>x.requestId===requests[0].id);assert.equal(provenance.length,4);assert.equal(await panel.evaluate(chooser+'.value'),latest.id);assert(!await panel.evaluate('Boolean('+button('▸ Composition coverage')+')'));
 const bodyReads=()=>[...panel.requests.values()].filter(x=>x.method==='observation.payload'&&x.params.eventId===latest.id).length,readsBefore=bodyReads();
 await panel.evaluate('__contextDelivery.releaseFrames=true');await visible('__contextDelivery.releasedIds.length===2');
 await visible(button('▸ Composition coverage'));assert.equal(await panel.evaluate(chooser+'.value'),latest.id,'arrival keeps the selected request');assert.equal(bodyReads(),readsBefore,'later provenance does not reread the unchanged provider request');
 await click(button('▸ Composition coverage'));const coverage='Array.from(document.querySelectorAll("button")).find(x=>x.textContent.trim()==="▾ Composition coverage").parentElement.querySelector("pre")';await visible(coverage);assert.deepEqual(JSON.parse(await panel.evaluate(coverage+'.textContent')),latestProvenance.data);
 const key=async name=>{await panel.call('Input.dispatchKeyEvent',{type:'keyDown',key:name,code:name});await panel.call('Input.dispatchKeyEvent',{type:'keyUp',key:name,code:name});};
 const choose=async id=>{const index=await panel.evaluate('Array.from('+chooser+'.options).findIndex(x=>x.value==='+JSON.stringify(id)+')');assert(index>=0);await click(chooser);await key('Home');for(let n=0;n<index;n++)await key('ArrowDown');await key('Enter');await visible(chooser+'.value==='+JSON.stringify(id));};
 const openCoverage=async()=>{await visible(button('▸ Composition coverage')+'||'+button('▾ Composition coverage'));if(await panel.evaluate('Boolean('+button('▸ Composition coverage')+')'))await click(button('▸ Composition coverage'));await visible(coverage);};
 await panel.evaluate('__contextDelivery.holdPayloadFor='+JSON.stringify(firstProvenance.id));await choose(requests[0].id);await visible('__contextDelivery.heldReads.length===1');await choose(latest.id);await openCoverage();assert.deepEqual(JSON.parse(await panel.evaluate(coverage+'.textContent')),latestProvenance.data);
 await panel.evaluate('__contextDelivery.heldReads.splice(0).forEach(x=>x.release(true));new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))');assert.equal(await panel.evaluate('__contextDelivery.retiredReads'),1);assert(!await panel.evaluate('document.body.innerText.includes("Authored delayed provenance read failure")'));assert.deepEqual(JSON.parse(await panel.evaluate(coverage+'.textContent')),latestProvenance.data,'old failure cannot alter current coverage');
 const pollsBefore=await panel.evaluate('__contextDelivery.polls'),readsBeforePoll=bodyReads();await visible('__contextDelivery.polls>'+pollsBefore);assert.equal(bodyReads(),readsBeforePoll,'unrelated event polling adds no provider-body reads');
 if(process.env.AUGMENTOR_CONTEXT_LIVE_PROOF_OUTPUT)await writeFile(join(process.env.AUGMENTOR_CONTEXT_LIVE_PROOF_OUTPUT,'live-context.png'),Buffer.from((await panel.call('Page.captureScreenshot',{format:'png'})).data,'base64'),{mode:0o600});
 const tailsBefore=await panel.evaluate('__contextDelivery.completedPayloads.filter(x=>x==='+JSON.stringify(firstProvenance.id)+').length');await choose(requests[0].id);await visible('__contextDelivery.heldReads.length===1');
 // Change conversation through the original sidebar while an old body is held.
 await rpc('session.create',{sessionId:'authored-context-sibling',cwd:link.workspace,selection:(await rpc('models.list')).default});await rpc('session.rename',{sessionId:'authored-context-sibling',title:'Authored Context sibling'});
 const sibling='Array.from(document.querySelectorAll("[data-row-key]")).find(x=>x.textContent.includes("Authored Context sibling"))';await visible(sibling);await click(sibling);await visible('sessionStorage.getItem("augmentor-harness-session")==="authored-context-sibling"');
 await panel.evaluate('__contextDelivery.heldReads.splice(0).forEach(x=>x.release(false))');await visible('__contextDelivery.completedPayloads.filter(x=>x==='+JSON.stringify(firstProvenance.id)+').length>'+tailsBefore);await panel.evaluate('new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))');assert.equal(await panel.evaluate('__contextDelivery.retiredReads'),2);assert(!await panel.evaluate('document.body.innerText.includes("Composition coverage")||document.body.innerText.includes("Authored delayed provenance read failure")'));
 assert.deepEqual(await rpc('session.history',{sessionId:sid}),history);assert.equal(await readFile(link.requestLog,'utf8'),wire);assert.deepEqual(await readFile(meta.file),native);assert.deepEqual(await readFile(join(link.state,'sessions',sid+'.events.jsonl')),display);assert.deepEqual(panel.errors,[]);assert.deepEqual(panel.failedResponses,[]);assert(!panel.urls.some(x=>/^https?:/.test(x)&&!x.startsWith(url.origin+'/')));assert.equal(stderr,'');t.diagnostic('Two real provenance frames delivered later; request identity/body-read count preserved, old error/success retired, original history and four provider requests unchanged.');
});
