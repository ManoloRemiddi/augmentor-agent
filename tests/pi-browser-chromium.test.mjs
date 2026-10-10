// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Loaded Chromium + native messaging + actual Pi; synthetic provider/page and isolated state only.
import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash,randomUUID} from 'node:crypto';
import {createServer} from 'node:http';
import net from 'node:net';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {mkdtemp,mkdir,readFile,writeFile,symlink,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {setTimeout as delay} from 'node:timers/promises';
import {PiConnection} from '../dist/client/src/socket.js';

const repo=process.env.AUGMENTOR_PI_TEST_ROOT??fileURLToPath(new URL('../',import.meta.url));
async function until(fn,label,ms=10000){
 const end=Date.now()+ms;let last;
 while(Date.now()<end){try{if(await fn())return;}catch(error){last=error;}await delay(30);}
 throw Error('Pi Browser timeout: '+label+(last?' ('+last.message+')':''));
}
async function cdp(url){
 const ws=new WebSocket(url);await once(ws,'open');let id=0;const pending=new Map(),errors=[];
 ws.addEventListener('message',event=>{const frame=JSON.parse(event.data),row=pending.get(frame.id);if(frame.method==='Runtime.exceptionThrown')errors.push(frame.params.exceptionDetails);if(frame.method==='Log.entryAdded'&&['warning','error'].includes(frame.params.entry.level))errors.push(frame.params.entry);if(row){pending.delete(frame.id);clearTimeout(row.timer);frame.error?row.reject(Error(frame.error.message)):row.resolve(frame.result);}});
 const call=(method,params={})=>new Promise((resolve,reject)=>{const key=++id,timer=setTimeout(()=>{pending.delete(key);reject(Error('CDP timeout: '+method));},10000);pending.set(key,{resolve,reject,timer});ws.send(JSON.stringify({id:key,method,params}));});
 return {call,errors,async reload(){const key='__augmentor_test_reload_'+randomUUID().replaceAll('-','');await this.evaluate('globalThis['+JSON.stringify(key)+']=true');await call('Page.reload');await until(()=>this.evaluate('globalThis['+JSON.stringify(key)+']===undefined&&document.readyState==="complete"'),'document replacement');},close(){for(const row of pending.values())clearTimeout(row.timer);ws.close();},async evaluate(expression){const result=await call('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(result.exceptionDetails)throw Error(JSON.stringify(result.exceptionDetails));return result.result.value;}};
}

test('loaded Pi Browser executes tools and identified steering, restores paused queues and branches exact context', {skip:process.platform!=='linux',timeout:60000},async t=>{
 const root=await mkdtemp(join(tmpdir(),'augmentor-pi-chromium-')),config=join(root,'config'),state=join(root,'state'),workspace=join(root,'work'),sockets=[];
 let chrome,runtime,client,stderr='',rounds=0,queueRounds=0,releaseCorrection;
 const inputs=[],queueInputs=[],closed=new Set(),selection={provider:'fixture',model:'pi-browser-fixture'};
 const server=createServer(async(req,res)=>{
  if(req.url==='/page'){res.setHeader('content-type','text/html');res.end('<!doctype html><title>Pi browser fixture</title><input id="fixture-input"><button id="fixture-button" onclick="document.body.dataset.clicks=String(Number(document.body.dataset.clicks||0)+1)">Fixture action</button>');return;}
  if(req.url!=='/v1/chat/completions'){res.writeHead(404).end();return;}
  let raw='';for await(const part of req)raw+=part;const body=JSON.parse(raw),number=inputs.push(body);res.once('close',()=>closed.add(number));
  const latest=JSON.stringify([...body.messages].reverse().find(row=>row.role==='user')?.content);
  res.writeHead(200,{'content-type':'text/event-stream'});
  const chunk=(delta,finish=null)=>res.write('data: '+JSON.stringify({id:'fixture-'+number,object:'chat.completion.chunk',model:selection.model,choices:[{index:0,delta,finish_reason:finish}]})+'\n\n');
  const finish=text=>{chunk({role:'assistant',content:text},'stop');res.end('data: [DONE]\n\n');};
  if(latest.includes('PI_BROWSER_')){
   queueInputs.push(body);queueRounds++;
   if(latest.includes('PI_BROWSER_SLOW')){chunk({role:'assistant',content:'Interrupted Pi Browser fixture. '});const timer=setInterval(()=>chunk({content:'partial '}),50);res.once('close',()=>clearInterval(timer));return;}
   if(latest.includes('Prepared PI_BROWSER_CORRECTION')){releaseCorrection=()=>finish('Pi Browser correction finished.');chunk({role:'assistant',content:'Prepared correction received. '});return;}
   finish('Pi Browser answer '+latest.match(/PI_BROWSER_[A-Z_]+/)?.[0]);return;
  }
  const action=[['browser_snapshot',{}],['browser_type',{selector:'#fixture-input',text:'Pi typed once'}],['browser_snapshot',{}],['browser_click',{selector:'#fixture-button'}],['browser_screenshot',{}]][rounds++];
  if(action){chunk({role:'assistant',tool_calls:[{index:0,id:'pi_fixture_'+rounds,type:'function',function:{name:action[0],arguments:JSON.stringify(action[1])}}]},'tool_calls');res.end('data: [DONE]\n\n');}
  else finish('Pi Browser tool fixture finished.');
 });
 t.after(async()=>{
  for(const socket of sockets)socket.close();client?.close();
  for(const child of [chrome,runtime])if(child?.pid&&child.exitCode===null){const exited=once(child,'exit');child.kill('SIGTERM');await exited;}
  server.closeAllConnections();await new Promise(resolve=>server.close(resolve));await rm(root,{recursive:true,force:true,maxRetries:5,retryDelay:100});
 });
 await Promise.all([mkdir(join(config,'agent','prompts'),{recursive:true}),mkdir(workspace)]);
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const base='http://127.0.0.1:'+server.address().port;
 await writeFile(join(config,'agent','models.json'),JSON.stringify({providers:{fixture:{api:'openai-completions',baseUrl:base+'/v1',apiKey:'synthetic-not-a-real-key',models:[{id:selection.model,name:'Isolated Pi Browser fixture',reasoning:true,compat:{supportsReasoningEffort:true},input:['text','image'],contextWindow:32000,maxTokens:2048}]}}}));
 await writeFile(join(config,'settings.json'),JSON.stringify({revision:0,defaultPreset:'danger-full-access',defaultModel:selection,pinned:[],hidden:[]}));
 await writeFile(join(config,'agent','prompts','correction.md'),'Prepared PI_BROWSER_CORRECTION $1');
 const cleanEnv=Object.fromEntries(Object.entries(process.env).filter(([key])=>!/^(AUGMENTOR_|DSH_|PI_)/.test(key)));
 const env={...cleanEnv,AUGMENTOR_PI_CONFIG:config,AUGMENTOR_PI_STATE:state,AUGMENTOR_PI_SOCKET:join(state,'runtime.sock'),AUGMENTOR_SHARED_STATE:join(root,'shared-state'),AUGMENTOR_SHARED_DATA:join(root,'shared-data'),AUGMENTOR_PI_BROWSER_WORKSPACE:workspace,AUGMENTOR_WORKSPACE_PROFILE:'',AUGMENTOR_PI_LINUX_TOOLS:'0',PI_OFFLINE:'1',XDG_CONFIG_HOME:join(root,'xdg-config'),XDG_STATE_HOME:join(root,'xdg-state'),XDG_DATA_HOME:join(root,'xdg-data')};
 runtime=spawn(process.execPath,[join(repo,'dist/runtime/src/main.js')],{cwd:workspace,env,stdio:['ignore','ignore','pipe']});runtime.stderr.on('data',data=>stderr+=data);
 await until(async()=>{assert.equal(runtime.exitCode,null,stderr);try{const socket=net.createConnection(env.AUGMENTOR_PI_SOCKET);socket.on('error',()=>{});await once(socket,'connect');client=new PiConnection(socket);await client.call('host.hello',{protocol:'augmentor-pi/1'});return true;}catch{return false;}},'runtime startup',20000);
 const extension=join(repo,'apps/browser/extension'),manifest=JSON.parse(await readFile(join(extension,'manifest.json'))),extensionId=createHash('sha256').update(Buffer.from(manifest.key,'base64')).digest('hex').slice(0,32).replace(/[0-9a-f]/g,char=>String.fromCharCode(97+parseInt(char,16)));
 const profile=join(root,'chromium'),launcher=join(root,'native-host');await mkdir(join(profile,'NativeMessagingHosts'),{recursive:true});
 // Explicit trusted workspace/config paths isolate the bridge without changing the account home.
 // A spaces-free interpreter alias keeps the fixture shebang valid for staged paths with spaces.
 const fixtureNode=join(root,'node');await symlink(process.execPath,fixtureNode);
 await writeFile(launcher,'#!'+fixtureNode+'\nObject.assign(process.env,'+JSON.stringify(env)+');import('+JSON.stringify(pathToFileURL(join(repo,'apps/browser/native-host.mjs')).href)+');\n',{mode:0o700});
 await writeFile(join(profile,'NativeMessagingHosts/com.augmentor.agent.json'),JSON.stringify({name:'com.augmentor.agent',description:'Isolated Pi Browser proof',path:launcher,type:'stdio',allowed_origins:['chrome-extension://'+extensionId+'/']}));
 chrome=spawn(process.env.CHROMIUM_BIN??'chromium',['--headless=new','--enable-unsafe-extension-debugging','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run','--no-default-browser-check','--remote-debugging-port=0','--user-data-dir='+profile,'--load-extension='+extension,'--disable-extensions-except='+extension,base+'/page'],{env,stdio:'ignore'});
 let port;await until(async()=>{try{port=(await readFile(join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0];return true;}catch{return false;}},'Chromium startup');
 const targets=()=>fetch('http://127.0.0.1:'+port+'/json').then(response=>response.json());
 let pageInfo;await until(async()=>{pageInfo=(await targets()).find(target=>target.url===base+'/page');return pageInfo;},'fixture page');const page=await cdp(pageInfo.webSocketDebuggerUrl);sockets.push(page);
 const created=await page.call('Target.createTarget',{url:'chrome-extension://'+extensionId+'/sidepanel.html'});let panelInfo;await until(async()=>{panelInfo=(await targets()).find(target=>target.id===created.targetId);return panelInfo;},'extension panel');const panel=await cdp(panelInfo.webSocketDebuggerUrl);sockets.push(panel);
 await until(()=>panel.evaluate('document.readyState==="complete"&&Boolean(document.querySelector("#input"))&&typeof chrome?.runtime?.sendMessage==="function"'),'panel readiness');
 const message=value=>panel.evaluate('chrome.runtime.sendMessage('+JSON.stringify(value)+')');assert.equal((await message({type:'harness/select',harness:'pi'})).ok,true);
 let status;await until(async()=>{status=await message({type:'connect'});if(status.phase==='ready')return true;throw Error(JSON.stringify(status));},'Pi connection');assert.equal((await message({type:'log'})).capabilities.queue,true);assert.equal((await message({type:'log'})).capabilities.steering,true);
 // Open the production settings entry point before any model request.
 const settingsTarget=await page.call('Target.createTarget',{url:'chrome-extension://'+extensionId+'/settings.html#models'});let settingsInfo;
 await until(async()=>{settingsInfo=(await targets()).find(row=>row.id===settingsTarget.targetId);return settingsInfo;},'reasoning settings target');
 const settings=await cdp(settingsInfo.webSocketDebuggerUrl);sockets.push(settings);for(const domain of ['Runtime','Log','Network'])await settings.call(domain+'.enable');
 const settingsUntil=expression=>until(()=>settings.evaluate(expression),'reasoning settings '+expression).catch(async error=>{error.message+=' '+JSON.stringify({body:await settings.evaluate('document.body.innerText')});throw error});
 const clickSetting=async expression=>{const point=await settings.evaluate('(()=>{const e='+expression+';if(!e||e.disabled)throw Error("Setting unavailable");e.scrollIntoView({block:"center"});const r=e.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};})()');await settings.call('Input.dispatchMouseEvent',{type:'mousePressed',...point,button:'left',clickCount:1});await settings.call('Input.dispatchMouseEvent',{type:'mouseReleased',...point,button:'left',clickCount:1});};
 const settingButton=label=>clickSetting('Array.from(document.querySelectorAll(".reasoning-dialog button")).find(e=>e.textContent==='+JSON.stringify(label)+')');
 const chooseSetting=(label,value)=>settings.evaluate('(()=>{const e=document.querySelector('+JSON.stringify('.reasoning-dialog [aria-label='+JSON.stringify(label)+']')+');e.value='+JSON.stringify(value)+';e.dispatchEvent(new Event("change",{bubbles:true}));})()');
 await settingsUntil('document.querySelector("#pi-reasoning-settings")&&!document.querySelector("#pi-reasoning-settings").disabled');
 await clickSetting('document.querySelector("#pi-reasoning-settings")');await settingsUntil('document.querySelector(".reasoning-dialog [role=status]")?.textContent.includes("Changes apply")');
 assert.equal(inputs.length,0);assert.equal((await message({type:'connect'})).capabilities.reasoning,true);await settingButton('Done');
 await page.call('Page.bringToFront');assert.match(await panel.evaluate('chrome.tabs.captureVisibleTab(undefined,{format:"jpeg"}).then(()=>"captured",error=>error.message)'),/activeTab|all_urls|permission/i);
 const browserInfo=await fetch('http://127.0.0.1:'+port+'/json/version').then(response=>response.json()),browser=await cdp(browserInfo.webSocketDebuggerUrl);sockets.push(browser);
 const tabInfo=(await browser.call('Target.getTargets',{filter:[{type:'tab',exclude:false}]})).targetInfos.find(target=>target.url===base+'/page');assert(tabInfo);await browser.call('Extensions.triggerAction',{id:extensionId,targetId:tabInfo.targetId});
 assert.equal((await message({type:'prompt',text:'Inspect the fixture page, type once, click once and capture it.'})).accepted,true);
 await until(()=>panel.evaluate('document.body.innerText.includes("Pi Browser tool fixture finished.")&&!document.querySelector("#send").disabled'),'tool completion');assert.equal(rounds,6);
 assert.deepEqual(await page.evaluate('({text:document.querySelector("#fixture-input").value,clicks:document.body.dataset.clicks})'),{text:'Pi typed once',clicks:'1'});
 const image=inputs.at(-1).messages.flatMap(row=>Array.isArray(row.content)?row.content:[]).find(part=>part.type==='image_url');assert(image?.image_url.url.startsWith('data:image/jpeg;base64,'),JSON.stringify(inputs.at(-1).messages.map(m=>({role:m.role,content:Array.isArray(m.content)?m.content.map(p=>({type:p.type,text:p.text?.slice(0,120)})):m.content?.slice(0,200)}))));assert(Buffer.from(image.image_url.url.split(',')[1],'base64').length>100,'actual Chromium JPEG reaches the Pi provider');
 async function panelUntil(expression,label){return until(()=>panel.evaluate(expression),label);}
 async function enter(text,queued=false){await panel.evaluate('(()=>{const input=document.querySelector("#input");input.value='+JSON.stringify(text)+';input.dispatchEvent(new KeyboardEvent("keydown",{key:"Enter",bubbles:true}));})()');if(!queued)return;const rows='Array.from(document.querySelectorAll(".queue-row"))';await panelUntil(rows+'.some(row=>row.textContent.includes('+JSON.stringify(text)+')&&row.querySelector("button")?.textContent==="Steer")','queued '+text);return panel.evaluate(rows+'.find(row=>row.textContent.includes('+JSON.stringify(text)+')).dataset.queueId');}
 async function action(id,label){const row='Array.from(document.querySelectorAll(".queue-row")).find(row=>row.dataset.queueId==='+JSON.stringify(id)+')';await panelUntil('(()=>{const row='+row+';return row&&Array.from(row.querySelectorAll("button")).some(button=>button.textContent==='+JSON.stringify(label)+'&&!button.disabled)})()','queue action '+label);await panel.evaluate('Array.from(('+row+').querySelectorAll("button")).find(button=>button.textContent==='+JSON.stringify(label)+').click()');}
 await enter('PI_BROWSER_SLOW first');await until(()=>queueRounds===1,'first generation');await panelUntil('!document.querySelector("#stop").hidden&&!document.querySelector("#send").disabled','running queue composer');
 const obsolete=inputs.length,sourceId=(await message({type:'connect'})).sessionId,correction=await enter('/correction "quoted words"',true);await action(correction,'Steer');
 await until(()=>closed.has(obsolete)&&queueRounds===2,'responsive same-turn correction');const removed=await enter('PI_BROWSER_REMOVED',true);await action(removed,'×');const next=await enter('PI_BROWSER_NEXT',true);
 await panel.reload();await panelUntil('document.readyState==="complete"&&Array.from(document.querySelectorAll(".queue-row")).some(row=>row.dataset.queueId==='+JSON.stringify(next)+')','reload restores queued input');
 if(process.env.AUGMENTOR_PI_BROWSER_SCREENSHOT)await writeFile(process.env.AUGMENTOR_PI_BROWSER_SCREENSHOT,Buffer.from((await panel.call('Page.captureScreenshot',{format:'png'})).data,'base64'));
 assert.equal(typeof releaseCorrection,'function');releaseCorrection();await panelUntil('document.body.innerText.includes("Pi Browser answer PI_BROWSER_NEXT")&&document.querySelector("#prompt-queue").hidden&&!document.querySelector("#send").disabled','ordered completion');assert.equal(queueRounds,3);
 assert.match(JSON.stringify(queueInputs[1].messages.at(-1)),/Prepared PI_BROWSER_CORRECTION quoted words/);assert.doesNotMatch(JSON.stringify(queueInputs),/PI_BROWSER_REMOVED/);assert.doesNotMatch(JSON.stringify(queueInputs[1]),/PI_BROWSER_NEXT/);
 assert.equal(await panel.evaluate('Array.from(document.querySelectorAll(".msg.user")).filter(row=>row.textContent.includes("/correction")).length'),1);assert.equal(await panel.evaluate('Array.from(document.querySelectorAll(".msg.user")).some(row=>row.textContent.includes("Prepared PI_BROWSER_CORRECTION"))'),false);
 const history=(await client.call('session.history',{sessionId:sourceId,maxMessages:100})).events.map(row=>row.event),users=history.filter(event=>event.type==='user/message');assert.equal(users.length,4);assert.equal(users[2].data.source.rpcId,correction);assert.equal(users[2].data.submittedContent[0].text,'/correction "quoted words"');assert.equal(users[1].turnId,users[2].turnId);assert.notEqual(users[2].turnId,users[3].turnId);

 // Stop and reconnect leave accepted waiting input paused; explicit idle Send resumes FIFO.
 await enter('PI_BROWSER_SLOW second');await until(()=>queueRounds===4,'second generation');const paused=await enter('PI_BROWSER_PAUSED',true);await panel.evaluate('document.querySelector("#stop").click()');await panelUntil('!document.querySelector("#send").disabled&&document.querySelector("#stop").hidden','Stop settles');
 await panel.reload();await panelUntil('document.readyState==="complete"&&Array.from(document.querySelectorAll(".queue-row")).some(row=>row.dataset.queueId==='+JSON.stringify(paused)+')','paused input reload');assert.equal(queueRounds,4);assert.equal((await client.call('session.queue',{sessionId:sourceId})).paused,true);
 await enter('PI_BROWSER_RESUME');await panelUntil('document.body.innerText.includes("Pi Browser answer PI_BROWSER_RESUME")&&document.querySelector("#prompt-queue").hidden&&!document.querySelector("#send").disabled','explicit resume');assert.equal(queueRounds,6);assert.match(JSON.stringify(queueInputs[4].messages.at(-1)),/PI_BROWSER_PAUSED/);assert.match(JSON.stringify(queueInputs[5].messages.at(-1)),/PI_BROWSER_RESUME/);

 // Branch/edit invoke the actual shared transcript controls and preserve the parent.
 await until(async()=>!(await client.call('session.list')).items.find(row=>row.sessionId===sourceId).running,'parent settled');const parent=await client.call('session.history',{sessionId:sourceId,maxMessages:100});await panel.evaluate('document.querySelector(".msg-branch").click()');let childId;await until(async()=>{childId=(await message({type:'connect'})).sessionId;return childId!==sourceId;},'branch selected');
 await panelUntil('document.body.innerText.includes("Pi Browser tool fixture finished.")&&!document.body.innerText.includes("PI_BROWSER_NEXT")&&!document.querySelector("#send").disabled','branch cutoff');assert.equal(queueRounds,6);assert.deepEqual(await client.call('session.history',{sessionId:sourceId,maxMessages:100}),parent);
 await enter('PI_BROWSER_CHILD');await panelUntil('document.body.innerText.includes("Pi Browser answer PI_BROWSER_CHILD")&&document.querySelector(".msg-edit:not(:disabled)")','branch response');assert.doesNotMatch(JSON.stringify(queueInputs[6]),/PI_BROWSER_NEXT|PI_BROWSER_CORRECTION|PI_BROWSER_RESUME/);assert.equal(queueInputs[6].messages.filter(row=>row.role==='tool').length,5);
 await panel.evaluate('(()=>{document.querySelector("#input").value="PI_BROWSER_DRAFT";document.querySelector(".msg-edit").click();})()');await panelUntil('document.querySelector("#input").value==="PI_BROWSER_CHILD"','edit exact submission');await enter('PI_BROWSER_EDITED');await panelUntil('document.body.innerText.includes("Pi Browser answer PI_BROWSER_EDITED")&&document.querySelector("#input").value==="PI_BROWSER_DRAFT"&&document.querySelector(".msg-edit:not(:disabled)")','edit response/draft restoration');
 const editedId=(await message({type:'connect'})).sessionId;assert.notEqual(editedId,childId);assert.doesNotMatch(JSON.stringify(queueInputs[7]),/PI_BROWSER_CHILD|PI_BROWSER_DRAFT|PI_BROWSER_NEXT/);await panel.reload();await panelUntil('document.body.innerText.includes("PI_BROWSER_EDITED")&&document.body.innerText.includes("Pi Browser answer PI_BROWSER_EDITED")','edited cold display');assert.equal(queueRounds,8);assert.deepEqual(await client.call('session.history',{sessionId:sourceId,maxMessages:100}),parent);

 // Save through rendered settings, extension API, native bridge and real Pi.
 const reasoningSession=(await message({type:'connect'})).sessionId,beforeSettings=inputs.length;
 await settingsUntil('!document.querySelector("#pi-reasoning-settings").disabled');
 await clickSetting('document.querySelector("#pi-reasoning-settings")');await settingsUntil('document.querySelector(".reasoning-dialog [role=status]")?.textContent.includes("Changes apply")');
 await chooseSetting('Reasoning mode','manual');await chooseSetting('Saved thinking effort','high');await settingButton('Save conversation');await settingsUntil('document.querySelector(".reasoning-dialog [role=status]").textContent==="Conversation reasoning saved."');
 assert.equal((await client.call('session.reasoning',{sessionId:reasoningSession})).thinkingLevel,'high');
 await settingButton('Add mapping');await chooseSetting('Complex work','medium');await settingButton('Save adaptive policy');await settingsUntil('document.querySelector(".reasoning-dialog [role=status]").textContent==="Adaptive policy saved."');
 assert.equal(inputs.length,beforeSettings,'Browser settings perform no inference');
 assert.equal((await message({type:'reasoning',action:'select',sourceSession:'wrong-conversation',params:{expectedRevision:0,mode:'manual',thinkingLevel:'off'}})).ok,false);
 assert.equal((await message({type:'reasoning',action:'constructor',sourceSession:reasoningSession})).ok,false);
 await settingButton('Done');await enter('PI_BROWSER_REASONING_MANUAL');await panelUntil('document.body.innerText.includes("Pi Browser answer PI_BROWSER_REASONING_MANUAL")&&!document.querySelector("#send").disabled','manual effort response');assert.equal(inputs.at(-1).reasoning_effort,'high');
 await settingsUntil('!document.querySelector("#pi-reasoning-settings").disabled');await clickSetting('document.querySelector("#pi-reasoning-settings")');await settingsUntil('document.querySelector(".reasoning-dialog [role=status]")?.textContent.includes("Changes apply")');await chooseSetting('Reasoning mode','adaptive');await settingButton('Save conversation');await settingsUntil('document.querySelector(".reasoning-dialog [role=status]").textContent==="Conversation reasoning saved."');await settingButton('Done');
 await enter('PI_BROWSER_REASONING_ADAPTIVE');await panelUntil('document.body.innerText.includes("Pi Browser answer PI_BROWSER_REASONING_ADAPTIVE")&&!document.querySelector("#send").disabled','adaptive effort response');assert.equal(inputs.at(-1).reasoning_effort,'medium');
 await settings.reload();await settingsUntil('document.querySelector("#pi-reasoning-settings")&&!document.querySelector("#pi-reasoning-settings").disabled');await clickSetting('document.querySelector("#pi-reasoning-settings")');await settingsUntil('document.querySelector('+JSON.stringify('.reasoning-dialog [aria-label="Reasoning mode"]')+')?.value==="adaptive"');assert.equal(await settings.evaluate('document.querySelector('+JSON.stringify('.reasoning-dialog [aria-label="Saved thinking effort"]')+').value'),'high');
 await settings.call('Emulation.setDeviceMetricsOverride',{width:640,height:900,deviceScaleFactor:1,mobile:false});await settingsUntil('document.querySelector(".reasoning-dialog").getBoundingClientRect().width<=608');await settings.evaluate('document.querySelector(".reasoning-dialog").scrollTop=0');const screenshot=await settings.call('Page.captureScreenshot',{format:'png'});await mkdir(join(repo,'outputs/harness-proof'),{recursive:true});await writeFile(join(repo,'outputs/harness-proof/browser-reasoning.png'),Buffer.from(screenshot.data,'base64'));await settingButton('Done');
 assert.deepEqual(await client.call('session.history',{sessionId:sourceId,maxMessages:100}),parent,'reasoning never changes an unselected parent');assert.deepEqual(settings.errors,[]);
});
