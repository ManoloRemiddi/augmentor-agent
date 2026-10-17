// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {createServer} from 'node:http';import {spawn} from 'node:child_process';import {once} from 'node:events';
import {mkdtemp,mkdir,writeFile,rm} from 'node:fs/promises';import {tmpdir} from 'node:os';import {join} from 'node:path';
import {planFixture,until} from './fixtures/plans.mjs';import {chromiumPort} from './fixtures/chromium-ready.mjs';
import {harnessCdp} from './fixtures/harness-cdp.mjs';import {harnessPointerClick} from './fixtures/harness-pointer.mjs';

test('original Plugins shows unavailable processing without disabling saved capture when its gateway is occupied',
 {skip:process.platform!=='linux',timeout:60000},async t=>{
 const f=await planFixture(t);let requests=0;
 const occupied=createServer((_req,res)=>{requests++;res.writeHead(503).end();});occupied.listen(0,'127.0.0.1');await once(occupied,'listening');
 t.after(()=>new Promise(resolve=>occupied.close(resolve)));
 const gatewayPort=occupied.address().port;await mkdir(f.env.AUGMENTOR_SHARED_DATA,{recursive:true});
 await writeFile(join(f.env.AUGMENTOR_SHARED_DATA,'hindsight.json'),JSON.stringify({endpoint:`http://127.0.0.1:${gatewayPort}`,processingProtocol:'augmentor-memory-processing/1',gatewayPort,
  gatewayKey:'independently-authored-gateway-key-32-characters',modelUrl:`http://127.0.0.1:${gatewayPort}/v1`}),{mode:0o600});
 await f.call('session.create',{sessionId:'memory-gateway',cwd:f.workspace,selection:f.selection});
 const profile=await mkdtemp(join(tmpdir(),'augmentor-memory-gateway-chromium-'));let chrome,panel;
 t.after(async()=>{panel?.close();if(chrome?.pid&&chrome.exitCode===null){const ended=once(chrome,'exit');chrome.kill('SIGTERM');await ended;}await rm(profile,{recursive:true,force:true,maxRetries:5,retryDelay:100});});
 chrome=spawn(process.env.CHROMIUM_BIN??'chromium',['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],{stdio:'ignore'});
 let port;await until(async()=>{try{port=await chromiumPort(profile);return !!port;}catch{return false;}},'gateway status Chromium');
 const target=(await fetch('http://127.0.0.1:'+port+'/json').then(r=>r.json())).find(row=>row.type==='page');panel=await harnessCdp(target.webSocketDebuggerUrl);
 for(const domain of ['Runtime','Log','Page','Network'])await panel.call(domain+'.enable');
 await panel.call('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
 const link=await f.link();await panel.navigate(link.url+'&session=memory-gateway');
 const q=s=>'document.querySelector('+JSON.stringify(s)+')',card=q('[data-memory-settings]');
 const button=label=>'Array.from(document.querySelectorAll("button")).find(b=>b.textContent.trim()==='+JSON.stringify(label)+')';
 const visible=expression=>until(()=>panel.evaluate('Boolean('+expression+')'),expression),click=expression=>harnessPointerClick(panel,expression,until);
 await visible(q('button[aria-label="Settings"]'));await click(q('button[aria-label="Settings"]'));await click(button('Plugins'));
 const toggle=q('[data-plugin-card=memory] [role=switch]');await visible(toggle+'?.getAttribute("aria-checked")==="true"');
 assert.equal(await panel.evaluate(toggle+'.disabled'),false);assert.match(await panel.evaluate(q('[data-plugin-card=memory]')+'.innerText'),/Processing gateway in use; local capture still works/);
 await click(q('button[aria-label="Open Automatic memory settings"]'));await visible(card+'?.innerText.includes("Processing: unavailable.")');
 const text=await panel.evaluate(card+'.innerText');assert(!text.includes('Processing: enabled'));assert.match(text,/local gateway port is in use/);
 assert.equal(await panel.evaluate(button('Pause automatic memory')+'.disabled'),false);assert.equal(await panel.evaluate(button('Pause memory processing')+'.disabled'),true);
 await click(button('Pause automatic memory'));await visible(button('Resume automatic memory'));assert.equal((await f.call('memory.status')).processing.paused,true);
 await click(button('Resume automatic memory'));await visible(button('Pause automatic memory'));const saved=await f.call('memory.status');
 assert.equal(saved.enabled,true);assert.equal(saved.processing.paused,true);assert.equal(saved.actions.processing,false);
 assert.equal(requests,0);assert.equal(f.requests.length,0);assert.deepEqual(panel.errors,[]);assert.deepEqual(panel.failedResponses,[]);
});
