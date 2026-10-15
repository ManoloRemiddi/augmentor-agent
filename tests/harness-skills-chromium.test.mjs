// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {chromiumPort} from './fixtures/chromium-ready.mjs';
// Original skill source and file viewer over the actual SDK/HTTP owner.
import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {mkdtemp,readFile,writeFile,mkdir,rm} from 'node:fs/promises';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {fileURLToPath} from 'node:url';
import {setTimeout as delay} from 'node:timers/promises';
import {harnessCdp} from './fixtures/harness-cdp.mjs';
import {harnessPointerClick} from './fixtures/harness-pointer.mjs';
import {createHash} from 'node:crypto';
import {PiConnection} from '../dist/client/src/socket.js';
import {localConnect} from '../dist/platform/src/transport.js';
const source=fileURLToPath(new URL('../',import.meta.url));
async function until(fn,label){const end=Date.now()+12000;let last;while(Date.now()<end){try{if(await fn())return;}catch(error){last=error;}await delay(30);}throw Error('Harness composition timeout: '+label+(last?' ('+last.message+')':''));}
test('original skill slash source previews current bytes, loads one approved body and preserves its recorded source across reload',{skip:process.platform!=='linux',timeout:60000},async t=>{
 const profile=await mkdtemp(join(tmpdir(),'augmentor-context-chrome-'));let fixture,chrome,panel,owner,link,output='',stderr='';
 t.after(async()=>{owner?.close();panel?.close();for(const child of [chrome,fixture])if(child?.pid&&child.exitCode===null){const ended=once(child,'exit');child.kill('SIGTERM');await ended;}await rm(profile,{recursive:true,force:true,maxRetries:5,retryDelay:100});});
 const env=Object.fromEntries(Object.entries(process.env).filter(([key])=>!/^(AUGMENTOR_|DSH_|PI_)/.test(key)));for(const key of ['AUGMENTOR_PI_TEST_ROOT','AUGMENTOR_PYTHON'])if(process.env[key])env[key]=process.env[key];
 fixture=spawn(process.execPath,[join(source,'scripts/harness-ui-proof.mjs')],{cwd:source,env:{...env,AUGMENTOR_HARNESS_PROOF_RECORD_REQUESTS:'1',AUGMENTOR_HARNESS_PROOF_PROMPTS:'1',AUGMENTOR_HARNESS_PROOF_SKILLS:'1'},stdio:['ignore','pipe','pipe']});fixture.stdout.on('data',data=>output+=data);fixture.stderr.on('data',data=>stderr+=data);
 await until(()=>{assert.equal(fixture.exitCode,null,stderr);try{link=JSON.parse(output.trim().split('\n').find(line=>line.startsWith('{"fixture"')));return !!link;}catch{return false;}},'owner ready');
 const url=new URL(link.url),token=new URLSearchParams(url.hash.slice(1)).get('token');
 const rpc=async(method,params={},bearer=token)=>{const response=await fetch(url.origin+'/api/rpc',{method:'POST',headers:{Authorization:'Bearer '+bearer,'Content-Type':'application/json'},body:JSON.stringify({id:crypto.randomUUID(),method,params})}),frame=await response.json();if(frame.error)throw Error(frame.error.message);return frame.result;};
 const socket=localConnect(join(link.state,'runtime.sock'));await once(socket,'connect');owner=new PiConnection(socket);await owner.call('host.hello',{protocol:'augmentor-pi/1'});
 chrome=spawn(process.env.CHROMIUM_BIN??'chromium',['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run','--remote-debugging-port=0','--user-data-dir='+profile,link.url],{env,stdio:'ignore'});
 let port;await until(async()=>{try{port=await chromiumPort(profile);return !!port;}catch{return false;}},'Chrome ready');
 const target=(await fetch('http://127.0.0.1:'+port+'/json').then(r=>r.json())).find(row=>row.type==='page');panel=await harnessCdp(target.webSocketDebuggerUrl);await panel.call('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});await panel.reload();for(const domain of ['Runtime','Log','Network','Page'])await panel.call(domain+'.enable');
 const visible=expression=>until(()=>panel.evaluate('Boolean('+expression+')'),expression).catch(async error=>{error.message+=' '+JSON.stringify({body:await panel.evaluate('document.body.innerText'),composer:await panel.evaluate('Array.from(document.querySelectorAll("[contenteditable]")).map(x=>x.outerHTML)'),focus:await panel.evaluate('document.activeElement.outerHTML'),errors:panel.errors,fixture:stderr});throw error;});
 const click=expression=>harnessPointerClick(panel,expression,until);
 const button=(label,within='document')=>'Array.from('+within+'.querySelectorAll("button")).find(x=>x.textContent.trim()==='+JSON.stringify(label)+')';
 const shell='document.querySelector("[data-shortcut-modal=settings]")';
 const settings='document.querySelector("button[aria-label=\\"Settings\\"]")';



 const query=css=>'document.querySelector('+JSON.stringify(css)+')',editor=query('[contenteditable=true]');
 const key=async(key,code=key,modifiers=0)=>{const windowsVirtualKeyCode={a:65,Enter:13,Escape:27,Tab:9,ArrowDown:40,ArrowUp:38,Backspace:8}[key];await panel.call('Input.dispatchKeyEvent',{type:'keyDown',key,code,modifiers,windowsVirtualKeyCode,...(key==='a'&&modifiers===2?{commands:['selectAll']}:{})});await panel.call('Input.dispatchKeyEvent',{type:'keyUp',key,code,modifiers:0,windowsVirtualKeyCode});};
 const replaceDraft=async text=>{await click(editor);if(await panel.evaluate(editor+'.textContent'))await key('a','KeyA',2);await key(text[0],text[0]==='/'?'Slash':'Key'+text[0].toUpperCase());await panel.call('Input.insertText',{text});};
 const requests=async()=>{const body=await readFile(link.requestLog,'utf8').catch(e=>{if(e.code==='ENOENT')return '';throw e;});return body.trim()?body.trim().split('\n').map(JSON.parse):[];};
 await visible(query('button[aria-label="New session"]'));await click(query('button[aria-label="New session"]'));await visible(editor);const sid=(await rpc('session.list')).items[0].sessionId;
 await replaceDraft('/authored-');const option=name=>'Array.from(document.querySelectorAll("[data-trigger-menu] [role=option]")).find(x=>x.querySelector("[class*=itemName]")?.textContent==='+JSON.stringify(name)+')';await visible(option('authored-review'));await visible(option('authored-manual'));assert(await panel.evaluate(option('authored-manual')+'.textContent.includes("user-only")'));assert.equal((await requests()).length,0);
 await click(option('authored-review'));await visible(query('[data-composer-text-ref]'));let draft;await until(async()=>{draft=await rpc('draft.describe',{sessionId:sid});return draft.text==='/authored-review ';},'original literal skill draft saved');await click(query('[data-composer-text-ref]'));await visible(query('[data-document-markdown]')+'&&document.body.innerText.includes("AUTHORED_SKILL_authored-review_V1")');assert.equal((await requests()).length,0);assert.deepEqual(await rpc('draft.describe',{sessionId:sid}),draft);
 await click(query('button[aria-label="Collapse right sidebar"]'));await replaceDraft('/authored-review Please use the authored skill.');await click(query('button[aria-label="Send message"]'));await visible('document.body.innerText.includes("The note says:")&&!'+query('button[aria-label="Stop generating"]'));const chip=query('button[data-ref-chip=skill]');await visible(chip);assert.equal(await panel.evaluate(chip+'.textContent'),'/authored-review');const history=await rpc('session.history',{sessionId:sid}),user=history.events.find(row=>row.event.type==='user/message').event;assert.equal(user.data.submittedContent[0].text,'/authored-review Please use the authored skill.');const record=user.data.skillInvocation;assert.equal(record.name,'authored-review');assert(record.path.includes('skills café'));const sourceV1=await readFile(record.path);assert.equal(record.sourceSha256,createHash('sha256').update(sourceV1).digest('hex'));const sent=await requests();assert.equal(sent.length,2);assert(sent[0].messages.some(m=>m.role==='user'&&JSON.stringify(m.content).includes('AUTHORED_SKILL_authored-review_V1')));
 await click(chip);await visible(query('[data-document-markdown]')+'&&document.body.innerText.includes("AUTHORED_SKILL_authored-review_V1")');await writeFile(record.path,sourceV1.toString().replace('_V1','_V2'));await click(query('[data-textpreview-tool=reload]'));await visible(query('[data-document-markdown]')+'&&document.body.innerText.includes("AUTHORED_SKILL_authored-review_V2")');assert.deepEqual(await rpc('session.history',{sessionId:sid}),history);assert.equal((await requests()).length,2);
 for(const name of ['Dark','Light']){await click(settings);await visible(shell);await click(button(name,shell));await visible('document.body.hasAttribute("data-ds-dark-theme")==='+String(name==='Dark'));await key('Escape');await visible('!'+shell);await visible(query('[data-document-markdown]')+'&&document.body.innerText.includes("AUTHORED_SKILL_authored-review_V2")');if(process.env.AUGMENTOR_SKILL_PROOF_OUTPUT)await writeFile(join(process.env.AUGMENTOR_SKILL_PROOF_OUTPUT,name.toLowerCase()+'.png'),Buffer.from((await panel.call('Page.captureScreenshot',{format:'png'})).data,'base64'),{mode:0o600});}
 await panel.reload();await visible(chip);await visible(query('[data-document-markdown]')+'&&document.body.innerText.includes("AUTHORED_SKILL_authored-review_V2")');assert.deepEqual(await rpc('session.history',{sessionId:sid}),history);assert.equal((await requests()).length,2);
 const inspection=await owner.call('inspection.open',{sessionId:sid}),bearer=new URLSearchParams(new URL(inspection.url).hash.slice(1)).get('token');await assert.rejects(rpc('session.skills',{sessionId:sid},bearer),/read-only/);assert.deepEqual(panel.errors,[]);assert(!panel.urls.some(value=>/^https?:/.test(value)&&!value.startsWith(url.origin+'/')));
});
