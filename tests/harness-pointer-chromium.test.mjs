// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {mkdtemp,rm} from 'node:fs/promises';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {setTimeout as delay} from 'node:timers/promises';
import {chromiumPort} from './fixtures/chromium-ready.mjs';
import {harnessCdp} from './fixtures/harness-cdp.mjs';
import {harnessPointerClick} from './fixtures/harness-pointer.mjs';
async function until(fn,label){const end=Date.now()+12000;while(Date.now()<end){if(await fn())return;await delay(30);}throw Error('Pointer fixture timeout: '+label);}
test('real Chromium reobserves a replaced offscreen target before one pointer click',{skip:process.platform!=='linux',timeout:30000},async t=>{
 const profile=await mkdtemp(join(tmpdir(),'augmentor-pointer-chrome-'));let chrome,panel;
 const server=http.createServer((_,res)=>res.writeHead(200,{'content-type':'text/html'}).end(`<!doctype html><title>Authored pointer fixture</title><button id="target">Authored control</button><script>
 globalThis.receipts={old:0,replacement:0,pressed:0};const old=document.querySelector('#target');old.addEventListener('click',()=>receipts.old++);
 old.scrollIntoView=function(options){Element.prototype.scrollIntoView.call(this,options);requestAnimationFrame(()=>{const next=document.createElement('button');next.id='target';next.textContent='Authored control';next.style.marginTop='1800px';next.addEventListener('mousedown',()=>receipts.pressed++);next.addEventListener('click',()=>receipts.replacement++);this.replaceWith(next);globalThis.replaced=true;});};
 </script>`));server.listen(0,'127.0.0.1');await once(server,'listening');
 t.after(async()=>{panel?.close();if(chrome?.pid&&chrome.exitCode===null){const ended=once(chrome,'exit');chrome.kill('SIGTERM');await ended;}server.closeAllConnections();await new Promise(done=>server.close(done));await rm(profile,{recursive:true,force:true,maxRetries:5,retryDelay:100});});
 chrome=spawn(process.env.CHROMIUM_BIN??'chromium',['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run','--remote-debugging-port=0','--user-data-dir='+profile,'http://127.0.0.1:'+server.address().port],{stdio:'ignore'});
 let port;await until(async()=>{assert.equal(chrome.exitCode,null);try{port=await chromiumPort(profile);return !!port;}catch{return false;}},'Chrome ready');
 const target=(await fetch('http://127.0.0.1:'+port+'/json').then(response=>response.json())).find(row=>row.type==='page');panel=await harnessCdp(target.webSocketDebuggerUrl);await panel.call('Runtime.enable');
 await until(()=>panel.evaluate('document.readyState==="complete"&&!!document.querySelector("#target")'),'document');
 await harnessPointerClick(panel,'document.querySelector("#target")',until);
 assert.equal(await panel.evaluate('globalThis.replaced'),true);assert.deepEqual(await panel.evaluate('globalThis.receipts'),{old:0,replacement:1,pressed:1});assert.deepEqual(panel.errors,[]);
});
