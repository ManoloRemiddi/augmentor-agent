// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Synthetic histories, actual offline converter/Host and unchanged supplier GUI.
import test from 'node:test';import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';import {once} from 'node:events';import {mkdtemp,readFile,writeFile,rename,rm,mkdir} from 'node:fs/promises';import {tmpdir} from 'node:os';import {resolve,join} from 'node:path';import {pathToFileURL} from 'node:url';import {createHash} from 'node:crypto';
import {batchRuntimeFixture} from './fixtures/dsh-batch-runtime.mjs';
import {planFixture,until} from './fixtures/plans.mjs';import {authoredDshProject} from './fixtures/dsh-project.mjs';import {chromiumPort} from './fixtures/chromium-ready.mjs';import {harnessCdp} from './fixtures/harness-cdp.mjs';import {harnessPointerClick} from './fixtures/harness-pointer.mjs';
const {importDshProject}=await import(pathToFileURL(resolve(process.env.AUGMENTOR_PI_TEST_ROOT??'.','dist/runtime/src/dsh-project-import.js')));

test('original sidebar presents two consolidated projects alongside existing Harness work and keeps their contexts separate',{skip:process.platform!=='linux',timeout:60000},async t=>{
 const f=await batchRuntimeFixture(t),calls=f.requests.length;await f.stop();const receipt=(await f.importBatch()).result;await f.start();
 const alpha=receipt.createdSessions.find(r=>r.sourceSessionId==='A-authored-alpha').sessionId,beta=receipt.createdSessions.find(r=>r.sourceSessionId==='B-authored-alpha').sessionId,importedAlpha=await f.native(alpha),link=await f.link();
 const profile=await mkdtemp(join(tmpdir(),'augmentor-project-chromium-'));let chrome,panel;
 t.after(async()=>{panel?.close();if(chrome?.exitCode===null){const ended=once(chrome,'exit');chrome.kill('SIGTERM');await ended;}await rm(profile,{recursive:true,force:true,maxRetries:5,retryDelay:100});});
 chrome=spawn(process.env.CHROMIUM_BIN??'chromium',['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],{stdio:'ignore'});
 let port;await until(async()=>{try{port=await chromiumPort(profile);return !!port;}catch{return false;}},'multi-chat Chromium');
 const target=(await fetch('http://127.0.0.1:'+port+'/json').then(r=>r.json())).find(r=>r.type==='page');panel=await harnessCdp(target.webSocketDebuggerUrl);
 for(const domain of ['Runtime','Log','Page','Network'])await panel.call(domain+'.enable');await panel.call('Emulation.setDeviceMetricsOverride',{width:1440,height:900,deviceScaleFactor:1,mobile:false});await panel.navigate(link.url+'&session='+beta);
 const q=s=>'document.querySelector('+JSON.stringify(s)+')';
 const visible=expr=>until(async()=>{assert.deepEqual(panel.errors,[]);return panel.evaluate('Boolean('+expr+')');},expr),click=expr=>harnessPointerClick(panel,expr,until);
 await visible('document.body.innerText.includes("PROJECT-B NATIVE-HISTORY-ALPHA") && '+q('[contenteditable=true]'));
 const opener=q('button[aria-label="Open sidebar"]');if(await panel.evaluate('Boolean('+opener+')'))await click(opener);
 const chat=label=>'Array.from(document.querySelectorAll("button,[role=button],span,a,div")).find(e=>e.innerText?.trim()==='+JSON.stringify(label)+')';
 const expand=async index=>{const key='workspace:'+receipt.projects[index].cwd,row='Array.from(document.querySelectorAll("[role=treeitem][data-row-key]")).find(e=>e.dataset.rowKey==='+JSON.stringify(key)+')';await visible(row);if(await panel.evaluate(row+'.getAttribute("aria-expanded")!=="true"'))await click(row);};
 await expand(0);
 await visible(chat('A Authored ALPHA chat'));assert.equal(await panel.evaluate('document.body.innerText.includes("PROJECT-A NATIVE-HISTORY-ALPHA")'),false);assert.equal(await panel.evaluate('document.body.innerText.includes("A Authored GAMMA chat")'),false,'archived chat remains outside ordinary sidebar');
 await expand(0);await click(chat('A Authored ALPHA chat'));await visible('document.body.innerText.includes("PROJECT-A NATIVE-HISTORY-ALPHA") && !document.body.innerText.includes("PROJECT-B NATIVE-HISTORY-ALPHA")');
 // First opening may append the current SDK model/thinking settings. Preserve
 // the complete imported prefix, then isolate changes caused by Beta's turn.
 await f.call('session.reasoning',{sessionId:alpha});const beforeAlpha=await f.native(alpha);assert(beforeAlpha.bytes.subarray(0,importedAlpha.bytes.length).equals(importedAlpha.bytes));
 await expand(1);await click(chat('B Authored ALPHA chat'));await visible('document.body.innerText.includes("PROJECT-B NATIVE-HISTORY-ALPHA") && !document.body.innerText.includes("PROJECT-A NATIVE-HISTORY-ALPHA")');assert.equal(f.requests.length,calls);
 const editor=q('[contenteditable=true]');await click(editor);await panel.call('Input.insertText',{text:JSON.stringify({kind:'read'})});await visible(q('button[aria-label="Send message"]')+' && !'+q('button[aria-label="Send message"]')+'.disabled');await click(q('button[aria-label="Send message"]'));
 await visible('document.body.innerText.includes("Synthetic planning reply")');assert.equal(f.requests.length,calls+2);
 const sent=JSON.stringify(f.requests[calls].messages);assert(sent.includes('PROJECT-B NATIVE-HISTORY-ALPHA'));assert(!sent.includes('PROJECT-A NATIVE-HISTORY-ALPHA'));assert(!sent.includes('NATIVE-HISTORY-GAMMA'));
 assert.deepEqual((await f.native(alpha)).bytes,beforeAlpha.bytes);assert.equal((await f.call('session.list')).items.length,7);
 await expand(0);await click(chat('A Authored ALPHA chat'));await visible('document.body.innerText.includes("PROJECT-A NATIVE-HISTORY-ALPHA") && !document.body.innerText.includes("Synthetic planning reply")');
 await expand(1);await click(chat('B Authored ALPHA chat'));await visible('document.body.innerText.includes("Synthetic planning reply")');assert.equal(f.requests.length,calls+2);
 assert.deepEqual(panel.errors,[]);assert.deepEqual(panel.failedResponses,[]);
 if(process.env.AUGMENTOR_GUI_PROOF_DIR){await mkdir(process.env.AUGMENTOR_GUI_PROOF_DIR,{recursive:true});await writeFile(join(process.env.AUGMENTOR_GUI_PROOF_DIR,'consolidated-projects.png'),Buffer.from((await panel.call('Page.captureScreenshot',{format:'png'})).data,'base64'));}
});
