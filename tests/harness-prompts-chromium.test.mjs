// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Actual Harness/Chromium/HTTP/Pi/shared SQLite and Native client, synthetic private inputs.
import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {harnessCdp as cdp} from './fixtures/harness-cdp.mjs';
import {mkdtemp,readFile,writeFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {setTimeout as delay} from 'node:timers/promises';
const source=fileURLToPath(new URL('../',import.meta.url));
async function until(fn,label,ms=12000){const end=Date.now()+ms;let last;while(Date.now()<end){try{if(await fn())return;}catch(error){last=error;}await delay(30);}throw Error('Harness prompts timeout: '+label+(last?' ('+last.message+')':''));}
test('Harness shared prompt editor, Native conflicts and two-step clipboard insertion use one service without automatic inference',{skip:process.platform!=='linux',timeout:90000},async t=>{
  const profile=await mkdtemp(join(tmpdir(),'augmentor-harness-prompts-chrome-'));let fixture,chrome,panel,output='',stderr='',link;
  t.after(async()=>{panel?.close();for(const child of [chrome,fixture])if(child?.pid&&child.exitCode===null){const ended=once(child,'exit');child.kill('SIGTERM');await ended;}await rm(profile,{recursive:true,force:true,maxRetries:5,retryDelay:100});});
  const env=Object.fromEntries(Object.entries(process.env).filter(([key])=>!/^(AUGMENTOR_|DSH_|PI_)/.test(key)));
  for(const key of ['AUGMENTOR_PI_TEST_ROOT','AUGMENTOR_PYTHON'])if(process.env[key])env[key]=process.env[key];
  fixture=spawn(process.execPath,[join(source,'scripts/harness-ui-proof.mjs')],{cwd:source,env:{...env,AUGMENTOR_HARNESS_PROOF_RECORD_REQUESTS:'1',AUGMENTOR_HARNESS_PROOF_PROMPTS:'1'},stdio:['ignore','pipe','pipe']});
  fixture.stdout.on('data',data=>output+=data);fixture.stderr.on('data',data=>stderr+=data);
  await until(()=>{assert.equal(fixture.exitCode,null,stderr);try{link=JSON.parse(output.trim().split('\n').find(line=>line.startsWith('{"fixture"')));return !!link;}catch{return false;}},'fixture readiness',20000);
  const url=new URL(link.url),token=new URLSearchParams(url.hash.slice(1)).get('token');
  const rpc=async(method,params={})=>{const response=await fetch(url.origin+'/api/rpc',{method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:JSON.stringify({id:crypto.randomUUID(),method,params})}),frame=await response.json();if(frame.error)throw Error(frame.error.message);return frame.result;};
  const requests=async()=>{try{return (await readFile(link.requestLog,'utf8')).trim().split('\n').filter(Boolean).map(line=>JSON.parse(line));}catch{return [];}};
  const native=async(method,params={})=>{
    const root=env.AUGMENTOR_PI_TEST_ROOT??source;
    const child=spawn(env.AUGMENTOR_PYTHON??'python3',['-Xutf8','-B','-c','import json,sys; from augmentor_linux.prompt_client import PromptClient; print(json.dumps(PromptClient().call(sys.argv[1],json.loads(sys.argv[2]))))',method,JSON.stringify(params)],{env:{...env,PYTHONPATH:join(root,'apps/native'),AUGMENTOR_SHARED_STATE:link.sharedState,AUGMENTOR_SHARED_DATA:link.sharedData},stdio:['ignore','pipe','pipe']});
    let result='',error='';child.stdout.on('data',data=>result+=data);child.stderr.on('data',data=>error+=data);const [code]=await once(child,'exit');assert.equal(code,0,error);return JSON.parse(result);
  };
  chrome=spawn(process.env.CHROMIUM_BIN??'chromium',['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run','--remote-debugging-port=0','--user-data-dir='+profile,link.url],{env,stdio:'ignore'});
  let port;await until(async()=>{try{port=(await readFile(join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0];return true;}catch{return false;}},'Chromium startup');
  const targets=await fetch('http://127.0.0.1:'+port+'/json').then(response=>response.json()),page=targets.find(row=>row.type==='page');assert(page);panel=await cdp(page.webSocketDebuggerUrl);await panel.call('Runtime.enable');await panel.call('Log.enable');await panel.call('Network.enable');await panel.call('Page.enable');await panel.call('Page.bringToFront');
  const visible=expression=>until(()=>panel.evaluate(expression),expression).catch(async error=>{error.message+=' '+JSON.stringify({body:await panel.evaluate('document.body.innerText'),runtimeErrors:panel.errors,requests:(await requests()).length,fixtureErrors:stderr});throw error;});
  const value=selector=>panel.evaluate('document.querySelector('+JSON.stringify(selector)+').value');
  const clickExpression=async expression=>{
    const point=await panel.evaluate('(()=>{const e='+expression+';if(!e||e.disabled)throw Error("Control unavailable");e.scrollIntoView({block:"nearest"});const r=e.getBoundingClientRect();if(!r.width||!r.height)throw Error("Control hidden");return {x:r.x+r.width/2,y:r.y+r.height/2};})()');
    await panel.call('Input.dispatchMouseEvent',{type:'mousePressed',...point,button:'left',clickCount:1});await panel.call('Input.dispatchMouseEvent',{type:'mouseReleased',...point,button:'left',clickCount:1});
  };
  const click=selector=>clickExpression('document.querySelector('+JSON.stringify(selector)+')');
  const button=label=>clickExpression('Array.from(document.querySelectorAll(".shared-prompt-editor button")).find(b=>b.textContent==='+JSON.stringify(label)+'&&!b.hidden&&b.getBoundingClientRect().width)');
  const key=async(key,extra={})=>{const code={Enter:13,Tab:9,Backspace:8}[key]??0;await panel.call('Input.dispatchKeyEvent',{type:'keyDown',key,code:key,windowsVirtualKeyCode:code,...extra});await panel.call('Input.dispatchKeyEvent',{type:'keyUp',key,code:key,windowsVirtualKeyCode:code});};
  const fill=async(selector,text)=>{await panel.evaluate('(()=>{const input=document.querySelector('+JSON.stringify(selector)+');input.focus();input.select();})()');if(text)await panel.call('Input.insertText',{text});else await key('Backspace');};
  const select=async id=>panel.evaluate('(()=>{const list=document.querySelector(".shared-prompt-editor select");list.value='+JSON.stringify(id)+';list.dispatchEvent(new Event("change",{bubbles:true}));})()');
  const recordConflict=async method=>{
    const response=panel.failedResponses.at(-1);assert(response);assert.equal(panel.requests.get(response.id)?.method,method);
    response.frame=JSON.parse((await panel.call('Network.getResponseBody',{requestId:response.id})).body);assert.match(response.frame.error.message,/changed elsewhere/);
  };
  const name='.shared-prompt-editor [aria-label="Prompt name"]',body='.shared-prompt-editor [aria-label="Prompt text"]',instructions='.shared-prompt-editor [aria-label="Prompt improvement instructions"]';
  await visible('document.querySelector("#runtime")?.textContent.includes("Pi 1.1.0")&&!document.querySelector("#prompt-library").disabled');
  assert.equal((await requests()).length,0);await fill('#input','Original Harness draft');await click('#prompt-library');await visible('document.querySelector(".shared-prompt-editor[open]")&&document.querySelector(".shared-prompt-editor select")');
  const template='Rewrite "[clipboard]". Again: [clipboard]';
  await fill(name,'rewrite');await fill(body,template);await button('Save');await visible('document.querySelector(".shared-prompt-editor").textContent.includes("Prompt saved.")');
  let library=await native('prompts.list'),row=library.prompts[0];assert.equal(row.content,template);assert.equal(library.prompts.length,1);const stableId=row.id;
  await select(row.id);await fill(body,'Unsaved Harness revision Café 😀');
  const changed=await native('prompts.save',{id:row.id,name:'revise',content:'Concurrent Native revision',expectedRevision:row.revision});row=changed.prompts[0];
  await visible('Array.from(document.querySelector(".shared-prompt-editor select").options).some(o=>o.textContent==="/revise")');assert.equal(await value(body),'Unsaved Harness revision Café 😀');
  await button('Save');await visible('document.querySelector(".shared-prompt-editor").textContent.includes("changed elsewhere")');await recordConflict('prompts.save');assert.equal(await value(body),'Unsaved Harness revision Café 😀');assert.deepEqual((await native('prompts.list')).prompts,[row]);
  await button('Reload selected');await visible('document.querySelector('+JSON.stringify(body)+').value==="Concurrent Native revision"');assert.equal(await value(name),'revise');
  await fill(name,'rewrite');await fill(body,template);await button('Save');await visible('document.querySelector(".shared-prompt-editor").textContent.includes("Prompt saved.")');row=(await native('prompts.list')).prompts[0];assert.equal(row.id,stableId);assert.equal(row.name,'rewrite');
  await button('New');await fill(name,'temporary');await fill(body,'Literal token: ');await button('Insert clipboard');assert.equal(await value(body),'Literal token: [clipboard]');await button('Save');await visible('document.querySelector(".shared-prompt-editor").textContent.includes("Prompt saved.")');
  const temporary=(await native('prompts.list')).prompts.find(item=>item.name==='temporary');assert(temporary);await select(temporary.id);
  panel.acceptDialog=false;await button('Delete');await until(()=>panel.dialogs.length===1,'cancel delete confirmation');assert.equal((await native('prompts.list')).prompts.length,2);
  panel.acceptDialog=true;await button('Delete');await visible('document.querySelector(".shared-prompt-editor").textContent.includes("Prompt deleted.")');assert.equal(panel.dialogs.length,2);assert.deepEqual((await native('prompts.list')).prompts,[row]);
  await button('Improvement instructions');await visible('document.querySelector(".shared-prompt-editor").textContent.includes("Prompt improvement in Pi is not yet available")');
  await fill(instructions,'Preserve the language. Keep the requested scope.');await button('Save instructions');await visible('document.querySelector(".shared-prompt-editor").textContent.includes("Instructions saved.")');let improvement=(await native('prompts.list')).improvement;assert.equal(improvement.content,'Preserve the language. Keep the requested scope.');
  await native('prompts.improvement.save',{content:'Concurrent Native instructions',expectedRevision:improvement.revision});await fill(instructions,'Unsaved Harness instructions');await button('Save instructions');await visible('document.querySelector(".shared-prompt-editor").textContent.includes("instructions changed elsewhere")');await recordConflict('prompts.improvementSave');assert.equal(await value(instructions),'Unsaved Harness instructions');
  await button('Reload');await visible('document.querySelector('+JSON.stringify(instructions)+').value==="Concurrent Native instructions"');improvement=(await native('prompts.list')).improvement;
  await button('Use default');assert.equal(await value(instructions),improvement.defaultContent);assert.equal((await native('prompts.list')).improvement.content,'Concurrent Native instructions');await button('Save instructions');await visible('document.querySelector(".shared-prompt-editor").textContent.includes("Instructions saved.")');assert.equal((await native('prompts.list')).improvement.content,improvement.defaultContent);
  await button('Saved prompts');await select(stableId);assert.equal(await value(body),template);
  await panel.call('Emulation.setDeviceMetricsOverride',{width:640,height:900,deviceScaleFactor:1,mobile:false});
  assert(await panel.evaluate('(()=>{const r=document.querySelector(".shared-prompt-editor").getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&r.bottom<=innerHeight;})()'));
  if(process.env.AUGMENTOR_HARNESS_PROMPTS_SCREENSHOT)await writeFile(process.env.AUGMENTOR_HARNESS_PROMPTS_SCREENSHOT,Buffer.from((await panel.call('Page.captureScreenshot',{format:'png'})).data,'base64'));
  await button('Done');assert.equal(await value('#input'),'Original Harness draft');assert.equal((await requests()).length,0,'CRUD and instructions do not perform inference');
  await panel.call('Emulation.clearDeviceMetricsOverride');await visible('document.querySelector("#new-chat").getBoundingClientRect().width>0');await click('#new-chat');await visible('!document.querySelector("#send").disabled');await panel.call('Page.reload');await visible('!document.querySelector("#send").disabled');
  assert.deepEqual((await rpc('prompts.list')).prompts,[row]);
  await panel.call('Browser.grantPermissions',{origin:url.origin,permissions:['clipboardReadWrite','clipboardSanitizedWrite']});await panel.call('Page.bringToFront');
  const snapshot='Café 😀\n[clipboard]';await panel.evaluate('navigator.clipboard.writeText('+JSON.stringify(snapshot)+')');
  await panel.evaluate('(()=>{const originalFetch=fetch,read=navigator.clipboard.readText.bind(navigator.clipboard);globalThis.promptReads=0;globalThis.holdPromptRead=null;globalThis.releasePromptCatalog=null;globalThis.promptCatalogOffline=false;globalThis.fetch=async(...args)=>{if(args[1]?.body&&JSON.parse(args[1].body).method==="prompts.list"){if(globalThis.promptCatalogOffline)throw Error("Synthetic prompt transport outage");if(!globalThis.releasePromptCatalog)await new Promise(resolve=>globalThis.releasePromptCatalog=resolve);}return originalFetch(...args);};navigator.clipboard.readText=async()=>{globalThis.promptReads++;await new Promise(resolve=>globalThis.holdPromptRead=resolve);return read();};})()');
  await fill('#input','/rewrite');await visible('typeof globalThis.releasePromptCatalog==="function"');await key('Enter');await key('Enter');assert.equal(await value('#input'),'/rewrite');assert.equal((await requests()).length,0);
  await panel.evaluate('globalThis.releasePromptCatalog()');await visible('document.querySelector("#prompt-completions button")?.textContent.startsWith("/rewrite")');await key('Enter');await visible('typeof globalThis.holdPromptRead==="function"&&document.querySelector("#send").disabled');
  await key('Enter');await panel.evaluate('document.querySelector("#composer").requestSubmit()');assert.equal((await requests()).length,0);assert.equal(await value('#input'),'/rewrite');
  await panel.evaluate('globalThis.holdPromptRead()');const expanded='Rewrite "'+snapshot+'". Again: '+snapshot;await visible('document.querySelector("#input").value==='+JSON.stringify(expanded));assert.equal(await panel.evaluate('globalThis.promptReads'),1);assert.equal((await requests()).length,0);
  await key('Enter',{autoRepeat:true});assert.equal((await requests()).length,0);await key('Enter');await until(async()=>(await requests()).length===2,'explicit second Enter model and real read tool');await visible('document.querySelector("#stop").disabled&&document.body.innerText.includes("The note says: Harness fixture ready.")');
  const selected=await panel.evaluate('sessionStorage.getItem("augmentor-harness-session")'),history=await rpc('session.history',{sessionId:selected,maxMessages:100});assert.equal(history.events.filter(event=>event.event.type==='user/message').length,1);assert.match(JSON.stringify((await requests())[0].messages),/Café/);assert.deepEqual((await native('prompts.list')).prompts,[row]);
  await panel.evaluate('globalThis.holdPromptRead=null');await fill('#input','/rewrite');await visible('document.querySelector("#prompt-completions button")');await key('Enter');await visible('typeof globalThis.holdPromptRead==="function"');await click('#new-chat');await visible('!document.querySelector("#new-chat").disabled&&sessionStorage.getItem("augmentor-harness-session")!=='+JSON.stringify(selected));await fill('#input','/rewrite');await panel.evaluate('globalThis.holdPromptRead()');await visible('!document.querySelector("#send").disabled');assert.equal(await value('#input'),'/rewrite');assert.equal((await requests()).length,2,'old clipboard work cannot submit or rewrite a new conversation');
  await panel.evaluate('globalThis.promptCatalogOffline=true');await visible('document.querySelector("#prompt-completions")?.textContent.includes("Synthetic prompt transport outage")');await key('Enter');assert.equal(await value('#input'),'/rewrite');assert.equal((await requests()).length,2);await panel.evaluate('globalThis.promptCatalogOffline=false');await visible('document.querySelector("#prompt-completions button")');
  assert.equal(panel.failedResponses.length,2,'only the two deliberately stale revision writes fail');
  const expected=new Set();
  for(const response of panel.failedResponses){
    assert.equal(response.status,400);assert.equal(response.url,url.origin+'/api/rpc');
    const method=panel.requests.get(response.id)?.method;assert(['prompts.save','prompts.improvementSave'].includes(method));expected.add(method);
    assert.match(response.frame.error.message,/changed elsewhere/);
  }
  assert.deepEqual([...expected].sort(),['prompts.improvementSave','prompts.save']);
  const conflicts=new Set(panel.failedResponses.map(response=>response.id));
  assert.deepEqual(panel.errors.filter(error=>!(error.source==='network'&&conflicts.has(error.networkRequestId))),[]);assert.equal(stderr,'');
});
