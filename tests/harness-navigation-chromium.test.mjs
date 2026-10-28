// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Authored isolated pages demonstrate that navigation acknowledgment precedes document readiness.
import test from 'node:test';import assert from 'node:assert/strict';
import http from 'node:http';import {spawn} from 'node:child_process';import {once} from 'node:events';
import {mkdtemp,rm} from 'node:fs/promises';import {join} from 'node:path';import {tmpdir} from 'node:os';
import {setTimeout as delay} from 'node:timers/promises';
import {chromiumPort} from './fixtures/chromium-ready.mjs';import {harnessCdp} from './fixtures/harness-cdp.mjs';
async function until(fn,label){const end=Date.now()+12000;while(Date.now()<end){if(await fn())return;await delay(30);}throw Error('Navigation fixture timeout: '+label);}
test('navigation acknowledgment does not expose the old or unfinished document as a ready inspector',{skip:process.platform!=='linux',timeout:30000},async t=>{
 const profile=await mkdtemp(join(tmpdir(),'augmentor-navigation-'));let chrome,panel;const held=new Map();
 const server=http.createServer((req,res)=>{
  const route=req.url.split('?')[0];
  if(route.endsWith('.js')){held.set(route,()=>res.writeHead(200,{'content-type':'text/javascript'}).end('globalThis.resourceReady=true;'));return;}
  const initial=route==='/start';res.writeHead(200,{'content-type':'text/html'}).end(initial
   ? '<!doctype html><title>Old document</title><script>globalThis.oldDocument=true</script>'
   : '<!doctype html><title>New inspector</title><div id="inspector">Authored read-only fixture</div><script src="'+route+'.js"></script>');
 });server.listen(0,'127.0.0.1');await once(server,'listening');const origin='http://127.0.0.1:'+server.address().port;
 t.after(async()=>{for(const release of held.values())release();panel?.close();if(chrome?.pid&&chrome.exitCode===null){const end=once(chrome,'exit');chrome.kill('SIGTERM');await end;}server.closeAllConnections();await new Promise(done=>server.close(done));await rm(profile,{recursive:true,force:true,maxRetries:5,retryDelay:100});});
 chrome=spawn(process.env.CHROMIUM_BIN??'chromium',['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run','--remote-debugging-port=0','--user-data-dir='+profile,origin+'/start'],{stdio:'ignore'});
 let port;await until(async()=>{assert.equal(chrome.exitCode,null);try{port=await chromiumPort(profile);return !!port;}catch{return false;}},'Chrome');
 const target=(await fetch('http://127.0.0.1:'+port+'/json').then(r=>r.json())).find(row=>row.type==='page');panel=await harnessCdp(target.webSocketDebuggerUrl);for(const name of ['Runtime','Page'])await panel.call(name+'.enable');
 await until(()=>panel.evaluate('document.readyState==="complete"&&globalThis.oldDocument===true'),'old document');
 await panel.call('Page.navigate',{url:origin+'/raw'});await until(()=>held.has('/raw.js'),'raw navigation reached its script');
 assert.equal(await panel.evaluate('document.readyState==="complete"'),false,'Page.navigate acknowledges before its document finishes');
 held.get('/raw.js')();held.delete('/raw.js');await until(()=>panel.evaluate('document.readyState==="complete"&&globalThis.resourceReady===true'),'raw document finished');
 await panel.evaluate('globalThis.oldDocument=true');let finished=false;
 const navigation=panel.navigate(origin+'/waited').then(()=>{finished=true;});
 await until(()=>held.has('/waited.js'),'awaited navigation reached its script');
 assert.equal(await panel.evaluate('document.readyState==="complete"'),false);assert.equal(finished,false,'the helper must not return while the document is unfinished');
 held.get('/waited.js')();held.delete('/waited.js');await navigation;
 assert.deepEqual(await panel.evaluate('({ready:document.readyState,old:globalThis.oldDocument===true,resource:globalThis.resourceReady,inspector:!!document.querySelector("#inspector")})'),{ready:'complete',old:false,resource:true,inspector:true});assert.deepEqual(panel.errors,[]);
});
