// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Original Settings shell, real private Host/companion; authored configuration,
// no engine or model inference. Actual Hindsight/Qwen qualification is separate.
import test from 'node:test';import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';import {once} from 'node:events';
import {mkdtemp,mkdir,writeFile,rm} from 'node:fs/promises';import {tmpdir} from 'node:os';import {join} from 'node:path';
import {planFixture,until} from './fixtures/plans.mjs';import {chromiumPort} from './fixtures/chromium-ready.mjs';
import {harnessCdp} from './fixtures/harness-cdp.mjs';import {harnessPointerClick} from './fixtures/harness-pointer.mjs';

test('original Plugins exposes configured memory mode and guarded controls in both themes without inference',{skip:process.platform!=='linux',timeout:60000},async t=>{
 const f=await planFixture(t);await mkdir(f.env.AUGMENTOR_SHARED_DATA,{recursive:true});
 // No processingProtocol: this isolated UI fixture cannot authorize inference.
 await writeFile(join(f.env.AUGMENTOR_SHARED_DATA,'hindsight.json'),JSON.stringify({endpoint:'http://127.0.0.1:1',llamaCppThinking:'off',apiKey:'authored-private-memory-key'}),{mode:0o600});
 await f.call('session.create',{sessionId:'memory-settings',cwd:f.workspace,selection:f.selection});
 const profile=await mkdtemp(join(tmpdir(),'augmentor-memory-settings-chromium-'));let chrome,panel;
 t.after(async()=>{panel?.close();if(chrome?.pid&&chrome.exitCode===null){const ended=once(chrome,'exit');chrome.kill('SIGTERM');await ended;}await rm(profile,{recursive:true,force:true,maxRetries:5,retryDelay:100});});
 chrome=spawn(process.env.CHROMIUM_BIN??'chromium',['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],{stdio:'ignore'});
 let port;await until(async()=>{try{port=await chromiumPort(profile);return !!port;}catch{return false;}},'memory settings Chromium');
 const target=(await fetch('http://127.0.0.1:'+port+'/json').then(r=>r.json())).find(row=>row.type==='page');panel=await harnessCdp(target.webSocketDebuggerUrl);
 for(const domain of ['Runtime','Log','Page','Network'])await panel.call(domain+'.enable');
 await panel.call('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
 const link=await f.link();await panel.navigate(link.url+'&session=memory-settings');
 const q=s=>'document.querySelector('+JSON.stringify(s)+')',shell=q('[data-shortcut-modal=settings]'),card=q('[data-memory-settings]');
 const button=(label,within='document')=>'Array.from('+within+'.querySelectorAll("button")).find(b=>b.textContent.trim()==='+JSON.stringify(label)+')';
 const visible=expression=>until(()=>panel.evaluate('Boolean('+expression+')'),expression),click=expression=>harnessPointerClick(panel,expression,until);
 const settings=q('button[aria-label="Settings"]');await visible(settings);await click(settings);await visible(shell);await click(button('Plugins',shell));await click('document.querySelector('+JSON.stringify('button[aria-label="Open Automatic memory settings"]')+')');
 await visible(card+'?.innerText.includes("Thinking off for memory requests")');
 assert((await panel.evaluate(card+'.innerText')).includes('configured engine choice'));
 assert(!(await panel.evaluate(card+'.innerText')).includes('authored-private-memory-key'));
 await click(button('Pause automatic memory',card));await visible(button('Resume automatic memory',card));
 assert.equal((await f.call('memory.status')).processing.paused,true);
 await click(button('Resume automatic memory',card));await visible(button('Pause automatic memory',card));
 assert.equal((await f.call('memory.status')).processing.paused,true,'resuming capture cannot resume processing');
 await click(button('Resume memory processing',card));await visible(button('Pause memory processing',card));
 await f.call('memory.processing',{paused:true,expectedPaused:false});
 await click(button('Pause memory processing',card));await visible(card+'.querySelector("[role=alert]")');
 assert(await panel.evaluate(card+'.querySelector("[role=alert]").innerText.includes("Nothing was retried")'));
 await until(()=>panel.failedResponses.length===1,'one explicitly stale memory choice');
 const conflict=panel.failedResponses[0];assert.equal(conflict.status,400);assert.equal(conflict.url,new URL(link.url).origin+'/api/rpc');
 assert.deepEqual({...panel.requests.get(conflict.id),id:null},{id:null,method:'memory.processing',params:{paused:true,expectedPaused:false}});
 const conflictBody=await panel.call('Network.getResponseBody',{requestId:conflict.id});assert.match(JSON.parse(conflictBody.body).error.message,/Refresh/);
 assert.equal((await f.call('memory.status')).processing.paused,true);
 await click(button('Refresh memory status',card));await visible(button('Resume memory processing',card));
 const output=process.env.AUGMENTOR_MEMORY_SETTINGS_PROOF_OUTPUT;if(output)await mkdir(output,{recursive:true});
 for(const theme of ['Dark','Light']){
  await click(button('General',shell));await click(button(theme,shell));await visible('document.body.hasAttribute("data-ds-dark-theme")==='+String(theme==='Dark'));
  await click(button('Plugins',shell));await click('document.querySelector('+JSON.stringify('button[aria-label="Open Automatic memory settings"]')+')');await visible(card+'?.innerText.includes("Thinking off for memory requests")');
  const contrasts=await panel.evaluate(`(()=>{const luminance=rgb=>{const c=rgb.match(/[\\d.]+/g).slice(0,3).map(Number).map(n=>{n/=255;return n<=.04045?n/12.92:((n+.055)/1.055)**2.4});return c[0]*.2126+c[1]*.7152+c[2]*.0722;};return Array.from(${card}.querySelectorAll('p,legend')).map(el=>{let bg=el;while(bg.parentElement&&['rgba(0, 0, 0, 0)','transparent'].includes(getComputedStyle(bg).backgroundColor))bg=bg.parentElement;const a=luminance(getComputedStyle(el).color),b=luminance(getComputedStyle(bg).backgroundColor);return (Math.max(a,b)+.05)/(Math.min(a,b)+.05);});})()`);
  assert(contrasts.every(ratio=>ratio>=4.5),theme+' text contrast: '+contrasts.join(','));
  if(output)await writeFile(join(output,'memory-settings-'+theme.toLowerCase()+'.png'),Buffer.from((await panel.call('Page.captureScreenshot',{format:'png'})).data,'base64'));
 }
 const inspection=await f.call('inspection.open',{sessionId:'memory-settings'});await panel.navigate(inspection.url);await visible(q('[data-composer-input][aria-disabled=true]'));
 await click(settings);await visible(shell);await click(button('Plugins',shell));await click('document.querySelector('+JSON.stringify('button[aria-label="Open Automatic memory settings"]')+')');await click(button('← All plugins',shell));await click('document.querySelector('+JSON.stringify('button[aria-label="Open Connected tools settings"]')+')');await visible(button('MCP servers',shell));assert.equal(await panel.evaluate('Boolean('+card+')'),false);
 const final=await f.call('memory.status');assert.equal(final.enabled,true);assert.equal(final.processing.paused,true);assert.equal(final.processing.active,false);assert.equal(final.events,0);
 assert.equal(f.requests.length,0);assert.equal(f.errors(),'');assert.equal(panel.failedResponses.length,1);
 assert.equal(panel.errors.length,1);assert.equal(panel.errors[0].source,'network');assert.equal(panel.errors[0].networkRequestId,conflict.id);
 const origin=new URL(link.url).origin;assert(!panel.urls.some(url=>/^https?:/.test(url)&&!url.startsWith(origin+'/')));
});
