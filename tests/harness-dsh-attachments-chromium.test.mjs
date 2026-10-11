// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Actual Pi SDK/Host and copied supplier components; deterministic provider.
import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {mkdtemp,readFile,writeFile,rm} from 'node:fs/promises';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {fileURLToPath} from 'node:url';
import sharp from 'sharp';
import {chromiumPort} from './fixtures/chromium-ready.mjs';
import {harnessCdp} from './fixtures/harness-cdp.mjs';
import {harnessPointerClick} from './fixtures/harness-pointer.mjs';
const source=fileURLToPath(new URL('../',import.meta.url));
async function until(fn,label){const end=Date.now()+12000;while(Date.now()<end){if(await fn())return;await new Promise(r=>setTimeout(r,30));}throw Error(label);}
test('original attachment cards, picker and viewer feed exact file/image content to one public Pi owner',{skip:process.platform!=='linux',timeout:60000},async t=>{
 const profile=await mkdtemp(join(tmpdir(),'augmentor-dsh-attachments-'));let fixture,chrome,panel,output='',stderr='',link;
 t.after(async()=>{panel?.close();for(const child of [chrome,fixture])if(child?.exitCode===null){const ended=once(child,'exit');child.kill('SIGTERM');await ended;}await rm(profile,{recursive:true,force:true,maxRetries:5,retryDelay:100});});
 const env=Object.fromEntries(Object.entries(process.env).filter(([key])=>!/^(AUGMENTOR_|DSH_|PI_)/.test(key)));for(const key of ['AUGMENTOR_PI_TEST_ROOT','AUGMENTOR_PYTHON'])if(process.env[key])env[key]=process.env[key];
 fixture=spawn(process.execPath,[join(source,'scripts/harness-ui-proof.mjs')],{cwd:source,env:{...env,AUGMENTOR_HARNESS_PROOF_RECORD_REQUESTS:'1',AUGMENTOR_HARNESS_PROOF_ATTACHMENTS:'1'},stdio:['ignore','pipe','pipe']});fixture.stdout.on('data',b=>output+=b);fixture.stderr.on('data',b=>stderr+=b);
 await until(()=>{assert.equal(fixture.exitCode,null,stderr);try{link=JSON.parse(output.split('\n').find(x=>x.startsWith('{"fixture"')));return !!link;}catch{return false;}},'Host ready');
 const url=new URL(link.url),token=new URLSearchParams(url.hash.slice(1)).get('token'),headers={Authorization:'Bearer '+token};
 const rpc=async(method,params={})=>{const response=await fetch(url.origin+'/api/rpc',{method:'POST',headers:{...headers,'Content-Type':'application/json'},body:JSON.stringify({id:crypto.randomUUID(),method,params})}),frame=await response.json();if(frame.error)throw Error(frame.error.message);return frame.result;};
 await rpc('session.create',{sessionId:'attachment-fixture',selection:(await rpc('models.list')).default,cwd:link.workspace});
 chrome=spawn(process.env.CHROMIUM_BIN??'chromium',['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run','--remote-debugging-port=0','--user-data-dir='+profile,link.url],{env,stdio:'ignore'});
 let port;await until(async()=>{try{port=await chromiumPort(profile);return !!port;}catch{return false;}},'Chromium ready');const target=(await fetch('http://127.0.0.1:'+port+'/json').then(r=>r.json())).find(x=>x.type==='page');panel=await harnessCdp(target.webSocketDebuggerUrl);
 await panel.call('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});for(const domain of ['Runtime','Log','Network','Page','DOM'])await panel.call(domain+'.enable');await panel.reload();
 const visible=expression=>until(()=>panel.evaluate('Boolean('+expression+')'),expression).catch(async error=>{error.message+=' '+JSON.stringify({body:await panel.evaluate('document.body.innerText'),errors:panel.errors,stderr});throw error;});
 const click=expression=>harnessPointerClick(panel,expression,until);
 await visible('document.querySelector("[contenteditable=true]")');const sid=await panel.evaluate('sessionStorage.getItem("augmentor-harness-session")');assert(sid);
 await click('document.querySelector("button[aria-label=\\"Add files or run commands\\"]")');await visible('Array.from(document.querySelectorAll("[role=menuitem]")).find(x=>x.textContent==="File")');
 await panel.call('Page.setInterceptFileChooserDialog',{enabled:true});await click('Array.from(document.querySelectorAll("[role=menuitem]")).find(x=>x.textContent==="File")');
 const file=join(profile,'attachment-note.txt'),image=join(profile,'red.png'),pixels=await sharp({create:{width:3,height:2,channels:3,background:'#f00'}}).png().toBuffer();await writeFile(file,'Exact uploaded fixture note.\n');await writeFile(image,pixels);
 const {root}=await panel.call('DOM.getDocument');const {nodeId}=await panel.call('DOM.querySelector',{nodeId:root.nodeId,selector:'input[type=file]'});assert(nodeId);await panel.call('DOM.setFileInputFiles',{nodeId,files:[file,image]});
 await visible('document.body.innerText.includes("attachment-note.txt")&&document.querySelector("img[alt=\\"red.png\\"]")');await click('document.querySelector("img[alt=\\"red.png\\"]").closest("button")');await visible('document.querySelector("[role=dialog]")');await click('document.querySelector("button[aria-label=\\"Close original image preview\\"]")');
 await click('document.querySelector("[contenteditable=true]")');await panel.call('Input.insertText',{text:'Read the uploaded note and inspect the image.'});await visible('!document.querySelector("button[aria-label=\\"Send message\\"]").disabled');await click('document.querySelector("button[aria-label=\\"Send message\\"]")');
 await visible('document.body.innerText.includes("The note says:")&&!document.querySelector("button[aria-label=\\"Stop generating\\"]")');await visible('document.querySelector("button[aria-label=\\"red.png, click to view original\\"]")');
 const history=await rpc('session.history',{sessionId:sid}),users=history.events.filter(x=>x.event.type==='user/message');assert.equal(users.length,1);assert.deepEqual(users[0].event.data.submittedContent.map(p=>p.type),['text','file','image']);
 assert(history.events.some(x=>x.event.type==='tool/result'&&JSON.stringify(x.event.data.result).includes('Exact uploaded fixture note.')),'the real SDK read tool reads the uploaded immutable file');
 const requests=(await readFile(link.requestLog,'utf8')).trim().split('\n').map(JSON.parse),parts=requests[0].messages.find(x=>x.role==='user').content,imagePart=parts.find(p=>p.type==='image_url');assert(imagePart);assert.equal(imagePart.image_url.url,'data:image/png;base64,'+pixels.toString('base64'));
 const imgRef=users[0].event.data.submittedContent.find(p=>p.type==='image').attachment;
 assert.equal((await fetch(url.origin+'/api/attachments/image?'+new URLSearchParams({sessionId:sid,ref:JSON.stringify(imgRef)}))).status,401);
 const last=history.events.filter(x=>x.event.type==='assistant/message'&&x.event.data.message.stopReason==='stop').at(-1);assert(last);const fork=await rpc('session.branch',{sessionId:sid,newSessionId:'attachment-fork',messageSeq:last.event.seq,mode:'reply'});
 const inheritedImage=await fetch(url.origin+'/api/attachments/image?'+new URLSearchParams({sessionId:fork.sessionId,ref:JSON.stringify(imgRef)}),{headers});assert.equal(inheritedImage.status,200);
 await rpc('session.create',{sessionId:'foreign',selection:(await rpc('models.list')).default,cwd:link.workspace});assert.equal((await fetch(url.origin+'/api/attachments/image?'+new URLSearchParams({sessionId:'foreign',ref:JSON.stringify(imgRef)}),{headers})).status,400);
 await panel.reload();await visible('document.querySelector("button[aria-label=\\"red.png, click to view original\\"]")');assert.equal((await rpc('session.history',{sessionId:sid})).events.filter(x=>x.event.type==='user/message').length,1);assert.equal((await readFile(link.requestLog,'utf8')).trim().split('\n').length,requests.length,'reopening does not resend');
 assert.equal(panel.errors.length,0,JSON.stringify(panel.errors));
});
