// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {mkdtemp,readFile,rm} from 'node:fs/promises';
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

test('original sidebar rail motion settles before one delayed pointer dispatch, while decorative motion continues',{skip:process.platform!=='linux',timeout:30000},async t=>{
 const css=await readFile(new URL('../apps/harness/vendor/dsh/packages/client/ui-sidebar/src/client/SidebarRoot.module.css',import.meta.url),'utf8');
 const rail=css.match(/^\.railIn \.iconButton,[\s\S]*?\n}/m)?.[0],frames=css.match(/@keyframes rail-in \{[\s\S]*?\n}/)?.[0];assert(rail&&frames,'original supplier rail animation is present');
 const profile=await mkdtemp(join(tmpdir(),'augmentor-pointer-motion-'));let chrome,panel;
 const server=http.createServer((_,res)=>res.writeHead(200,{'content-type':'text/html'}).end(`<!doctype html><title>Authored rail timing fixture</title><style>
 :root{--ds-ease-in-out:linear}button{position:fixed;left:60px;top:60px;width:28px;height:28px;padding:0}#target{z-index:3}#neighbor{left:109px;z-index:2}
 ${rail}\n${frames}
 .decoration{display:block;width:8px;height:8px;animation:decorative 1s infinite linear}@keyframes decorative{to{transform:rotate(360deg)}}
 </style><div id="rail"><button id="target" class="iconButton"><span class="decoration"></span></button></div><button id="neighbor">N</button><script>
 globalThis.receipts={target:0,neighbor:0,pressed:0};target.addEventListener('mousedown',()=>receipts.pressed++);target.addEventListener('click',()=>receipts.target++);neighbor.addEventListener('click',()=>receipts.neighbor++);
 </script>`));server.listen(0,'127.0.0.1');await once(server,'listening');
 t.after(async()=>{panel?.close();if(chrome?.pid&&chrome.exitCode===null){const ended=once(chrome,'exit');chrome.kill('SIGTERM');await ended;}server.closeAllConnections();await new Promise(done=>server.close(done));await rm(profile,{recursive:true,force:true,maxRetries:5,retryDelay:100});});
 chrome=spawn(process.env.CHROMIUM_BIN??'chromium',['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run','--remote-debugging-port=0','--user-data-dir='+profile,'http://127.0.0.1:'+server.address().port],{stdio:'ignore'});
 let port;await until(async()=>{assert.equal(chrome.exitCode,null);try{port=await chromiumPort(profile);return !!port;}catch{return false;}},'Chrome ready');
 const target=(await fetch('http://127.0.0.1:'+port+'/json').then(r=>r.json())).find(row=>row.type==='page');panel=await harnessCdp(target.webSocketDebuggerUrl);await panel.call('Runtime.enable');
 await until(()=>panel.evaluate('document.readyState==="complete"&&!!document.querySelector("#target")'),'document');
 const originalCall=panel.call.bind(panel);let dispatched=0;
 const delayed={evaluate:panel.evaluate.bind(panel),call:async(method,params)=>{if(method==='Input.dispatchMouseEvent'&&params.type==='mousePressed'){dispatched++;await delay(170);}return originalCall(method,params);}};
 const moving=await panel.evaluate('(()=>{document.querySelector("#rail").className="railIn";const e=document.querySelector("#target");return {x:e.getBoundingClientRect().x,name:getComputedStyle(e).animationName,duration:getComputedStyle(e).animationDuration}})()');
 assert.equal(moving.name,'rail-in');assert.equal(moving.duration,'0.15s');assert(moving.x>100,'the real rail transform is active before preparation');
 await harnessPointerClick(delayed,'document.querySelector("#target")',until);
 assert.equal(dispatched,1,'a dispatched click is never replayed');assert.deepEqual(await panel.evaluate('receipts'),{target:1,neighbor:0,pressed:1});
 assert.equal(await panel.evaluate('document.querySelector(".decoration").getAnimations()[0].playState'),'running','infinite decorative motion remains enabled');assert.deepEqual(panel.errors,[]);
});

test('an original toast action remains clickable during its delayed fade hold',{skip:process.platform!=='linux',timeout:30000},async t=>{
 const css=await readFile(new URL('../apps/harness/vendor/dsh/packages/client/ui-primitives/src/Toast.module.css',import.meta.url),'utf8');
 const profile=await mkdtemp(join(tmpdir(),'augmentor-pointer-toast-'));let chrome,panel;
 const server=http.createServer((_,res)=>res.writeHead(200,{'content-type':'text/html'}).end(`<!doctype html><title>Authored toast fixture</title><style>${css}</style><div id="notice" class="toast" style="--dsh-toast-hold:6000ms">Authored archive notice<button id="undo" class="action">undo</button></div><script>globalThis.receipts=0;undo.addEventListener('click',()=>receipts++);setTimeout(()=>notice.remove(),7000)</script>`));server.listen(0,'127.0.0.1');await once(server,'listening');
 t.after(async()=>{panel?.close();if(chrome?.pid&&chrome.exitCode===null){const end=once(chrome,'exit');chrome.kill('SIGTERM');await end;}server.closeAllConnections();await new Promise(done=>server.close(done));await rm(profile,{recursive:true,force:true,maxRetries:5,retryDelay:100});});
 chrome=spawn(process.env.CHROMIUM_BIN??'chromium',['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run','--remote-debugging-port=0','--user-data-dir='+profile,'http://127.0.0.1:'+server.address().port],{stdio:'ignore'});
 let port;await until(async()=>{assert.equal(chrome.exitCode,null);try{port=await chromiumPort(profile);return !!port;}catch{return false;}},'Chrome');
 const target=(await fetch('http://127.0.0.1:'+port+'/json').then(r=>r.json())).find(row=>row.type==='page');panel=await harnessCdp(target.webSocketDebuggerUrl);await panel.call('Runtime.enable');
 await until(()=>panel.evaluate('document.readyState==="complete"&&!!document.querySelector("#undo")'),'toast document');
 assert.equal(await panel.evaluate('document.querySelector("#notice").getAnimations().some(a=>a.animationName==="dsh-toast-fade"&&a.effect.getComputedTiming().progress===null)'),true,'the original delayed fade is waiting');
 await harnessPointerClick(panel,'document.querySelector("#undo")',until);
 assert.deepEqual(await panel.evaluate('({count:receipts,present:!!document.querySelector("#undo"),waiting:document.querySelector("#notice").getAnimations().some(a=>a.animationName==="dsh-toast-fade"&&a.effect.getComputedTiming().progress===null)})'),{count:1,present:true,waiting:true});assert.deepEqual(panel.errors,[]);
});
