// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {chromiumPort} from './fixtures/chromium-ready.mjs';
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
const runtimeRoot=(process.env.AUGMENTOR_PI_RUNTIME_TEST_ROOT??repo).replace(/\/$/,'');
const harness=process.env.AUGMENTOR_BROWSER_PERMISSION_HARNESS??'ah';
async function until(fn,label,ms=10000){
 const end=Date.now()+ms;let last;
 while(Date.now()<end){try{if(await fn())return;}catch(error){last=error;}await delay(30);}
 throw Error('Pi Browser timeout: '+label+(last?' ('+last.message+')':''));
}
async function cdp(url){
 const ws=new WebSocket(url);await once(ws,'open');let id=0;const pending=new Map(),errors=[],dialogs=[];
 ws.addEventListener('message',event=>{const frame=JSON.parse(event.data),row=pending.get(frame.id);if(frame.method==='Page.javascriptDialogOpening')dialogs.push(frame.params);if(frame.method==='Runtime.exceptionThrown')errors.push(frame.params.exceptionDetails);if(frame.method==='Log.entryAdded'&&['warning','error'].includes(frame.params.entry.level))errors.push(frame.params.entry);if(row){pending.delete(frame.id);clearTimeout(row.timer);frame.error?row.reject(Error(frame.error.message)):row.resolve(frame.result);}});
 const call=(method,params={})=>new Promise((resolve,reject)=>{const key=++id,timer=setTimeout(()=>{pending.delete(key);reject(Error('CDP timeout: '+method));},10000);pending.set(key,{resolve,reject,timer});ws.send(JSON.stringify({id:key,method,params}));});
 return {call,errors,dialogs,async reload(){const key='__augmentor_test_reload_'+randomUUID().replaceAll('-','');await this.evaluate('globalThis['+JSON.stringify(key)+']=true');await call('Page.reload');await until(()=>this.evaluate('globalThis['+JSON.stringify(key)+']===undefined&&document.readyState==="complete"'),'document replacement');},close(){for(const row of pending.values())clearTimeout(row.timer);ws.close();},async evaluate(expression){const result=await call('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true}).catch(e=>{e.message+=' '+expression.slice(0,140);throw e});if(result.exceptionDetails)throw Error(JSON.stringify(result.exceptionDetails));return result.result.value;}};
}

test('Browser current-chat permissions govern real navigation, typing and clicks and persist without changing defaults', {skip:process.platform!=='linux',timeout:60000},async t=>{
 const root=await mkdtemp(join(tmpdir(),'augmentor-pi-chromium-')),config=join(root,'config'),state=join(root,'state'),workspace=join(root,'work'),sockets=[];
 let chrome,runtime,client,stderr='';
 const permissionRounds=new Map();const inputs=[],selection={provider:'fixture',model:'pi-browser-fixture'};
 const server=createServer(async(req,res)=>{
  if(req.url.startsWith('/page')){res.setHeader('content-type','text/html');res.end('<!doctype html><title>Pi browser fixture</title><input id="fixture-input"><button id="fixture-button" onclick="document.body.dataset.clicks=String(Number(document.body.dataset.clicks||0)+1)">Fixture action</button>');return;}
  if(req.url!=='/v1/chat/completions'){res.writeHead(404).end();return;}
  let raw='';for await(const part of req)raw+=part;const body=JSON.parse(raw),number=inputs.push(body);
  res.writeHead(200,{'content-type':'text/event-stream'});
  const chunk=(delta,finish=null)=>res.write('data: '+JSON.stringify({id:'fixture-'+number,object:'chat.completion.chunk',model:selection.model,choices:[{index:0,delta,finish_reason:finish}]})+'\n\n');
  const finish=text=>{chunk({role:'assistant',content:text},'stop');res.end('data: [DONE]\n\n');};
  const marker=JSON.stringify(body.messages.filter(row=>row.role==='user')).match(/PERMISSION_[A-Z]+/g)?.at(-1)??'UNKNOWN';
  const count=permissionRounds.get(marker)??0;permissionRounds.set(marker,count+1);
  const action=[['browser_snapshot',{}],['browser_navigate',{url:base+'/page?'+marker}],['browser_snapshot',{}],['browser_type',{selector:'#fixture-input',text:marker}],['browser_snapshot',{}],['browser_click',{selector:'#fixture-button'}]][count];
  if(action){chunk({role:'assistant',tool_calls:[{index:0,id:'permission_'+marker+'_'+count,type:'function',function:{name:action[0],arguments:JSON.stringify(action[1])}}]},'tool_calls');res.end('data: [DONE]\n\n');}
  else finish(marker+' finished.');
 });
 t.after(async()=>{
  for(const socket of sockets)socket.close();client?.close();
  for(const child of [chrome,runtime])if(child?.pid&&child.exitCode===null){const exited=once(child,'exit');child.kill('SIGTERM');await exited;}
  server.closeAllConnections();await new Promise(resolve=>server.close(resolve));await rm(root,{recursive:true,force:true,maxRetries:5,retryDelay:100});
 });
 await mkdir(config,{mode:0o700});
 await Promise.all([mkdir(join(config,'agent','prompts'),{recursive:true}),mkdir(workspace),mkdir(state,{mode:0o700}),mkdir(join(root,'shared-state'),{mode:0o700}),mkdir(join(root,'shared-data'),{mode:0o700})]);
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const base='http://127.0.0.1:'+server.address().port;
 await writeFile(join(config,'agent','models.json'),JSON.stringify({providers:{fixture:{api:'openai-completions',baseUrl:base+'/v1',apiKey:'synthetic-not-a-real-key',models:[{id:selection.model,name:'Isolated Pi Browser fixture',reasoning:true,compat:{supportsReasoningEffort:true},input:['text','image'],contextWindow:32000,maxTokens:2048}]}}}));
 await writeFile(join(config,'settings.json'),JSON.stringify({revision:0,defaultPreset:'read-only',defaultModel:selection,pinned:[],hidden:[],observation:{capturePayloads:true}}));
 const cleanEnv=Object.fromEntries(Object.entries(process.env).filter(([key])=>!/^(AUGMENTOR_|DSH_|PI_)/.test(key)));
 const env={...cleanEnv,AUGMENTOR_PI_CONFIG:config,AUGMENTOR_PI_STATE:state,AUGMENTOR_PI_SOCKET:join(state,'runtime.sock'),AUGMENTOR_SHARED_STATE:join(root,'shared-state'),AUGMENTOR_SHARED_DATA:join(root,'shared-data'),AUGMENTOR_PI_BROWSER_WORKSPACE:workspace,AUGMENTOR_WORKSPACE_PROFILE:'',AUGMENTOR_PI_LINUX_TOOLS:'0',PI_OFFLINE:'1',XDG_CONFIG_HOME:join(root,'xdg-config'),XDG_STATE_HOME:join(root,'xdg-state'),XDG_DATA_HOME:join(root,'xdg-data')};
 runtime=spawn(process.execPath,[join(runtimeRoot,'dist/runtime/src/main.js')],{cwd:workspace,env,stdio:['ignore','ignore','pipe']});runtime.stderr.on('data',data=>stderr+=data);
 await until(async()=>{assert.equal(runtime.exitCode,null,stderr);try{const socket=net.createConnection(env.AUGMENTOR_PI_SOCKET);socket.on('error',()=>{});await once(socket,'connect');client=new PiConnection(socket);await client.call('host.hello',{protocol:'augmentor-pi/1'});return true;}catch{return false;}},'runtime startup',20000);
 const description=await client.call('host.describe');
 env.AUGMENTOR_AH_CONNECTION=join(root,'connection.json');
 await writeFile(env.AUGMENTOR_AH_CONNECTION,JSON.stringify({schema:'augmentor-ah-connection/1',profile:{config,state,workspace,sharedState:env.AUGMENTOR_SHARED_STATE,sharedData:env.AUGMENTOR_SHARED_DATA,socket:env.AUGMENTOR_PI_SOCKET},root:runtimeRoot,version:description.version}),{mode:0o600});
 const extension=process.env.AUGMENTOR_BROWSER_EXTENSION_ROOT??join(repo,'apps/browser/extension'),manifest=JSON.parse(await readFile(join(extension,'manifest.json'))),extensionId=createHash('sha256').update(Buffer.from(manifest.key,'base64')).digest('hex').slice(0,32).replace(/[0-9a-f]/g,char=>String.fromCharCode(97+parseInt(char,16)));
 const profile=join(root,'chromium'),launcher=join(root,'native-host');await mkdir(join(profile,'NativeMessagingHosts'),{recursive:true});
 // Explicit trusted workspace/config paths isolate the bridge without changing the account home.
 // A spaces-free interpreter alias keeps the fixture shebang valid for staged paths with spaces.
 const fixtureNode=join(root,'node');await symlink(process.execPath,fixtureNode);
 await writeFile(launcher,'#!'+fixtureNode+'\nObject.assign(process.env,'+JSON.stringify(env)+');import('+JSON.stringify(pathToFileURL(join(repo,'apps/browser/native-host.mjs')).href)+');\n',{mode:0o700});
 await writeFile(join(profile,'NativeMessagingHosts/com.augmentor.agent.json'),JSON.stringify({name:'com.augmentor.agent',description:'Isolated Pi Browser proof',path:launcher,type:'stdio',allowed_origins:['chrome-extension://'+extensionId+'/']}));
 chrome=spawn(process.env.CHROMIUM_BIN??'chromium',['--headless=new','--enable-unsafe-extension-debugging','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run','--no-default-browser-check','--remote-debugging-port=0','--user-data-dir='+profile,'--load-extension='+extension,'--disable-extensions-except='+extension,base+'/page'],{env,stdio:'ignore'});
 let port;await until(async()=>{try{port=await chromiumPort(profile);return !!port;}catch{return false;}},'Chromium startup');
 const targets=()=>fetch('http://127.0.0.1:'+port+'/json').then(response=>response.json());
 let pageInfo;await until(async()=>{pageInfo=(await targets()).find(target=>target.url===base+'/page');return pageInfo;},'fixture page');const page=await cdp(pageInfo.webSocketDebuggerUrl);sockets.push(page);
 const created=await page.call('Target.createTarget',{url:'chrome-extension://'+extensionId+'/sidepanel.html'});let panelInfo;await until(async()=>{panelInfo=(await targets()).find(target=>target.id===created.targetId);return panelInfo;},'extension panel');const panel=await cdp(panelInfo.webSocketDebuggerUrl);sockets.push(panel);
 await until(()=>panel.evaluate('document.readyState==="complete"&&Boolean(document.querySelector("#input"))&&typeof chrome?.runtime?.sendMessage==="function"'),'panel readiness');
 const message=value=>panel.evaluate('chrome.runtime.sendMessage('+JSON.stringify(value)+')');if((await message({type:'connect'})).harness!==harness)assert.equal((await message({type:'harness/select',harness})).ok,true);
 let status;await until(async()=>{status=await message({type:'connect'});if(status.phase==='ready')return true;throw Error(JSON.stringify(status));},'Pi connection');assert.equal((await message({type:'log'})).capabilities.sessionPermissions,true);

 await panel.call('Page.enable');await panel.call('Runtime.enable');
 
 const click=async expression=>{const point=await panel.evaluate('(()=>{const e='+expression+';if(!e||e.disabled)throw Error("Control unavailable");e.scrollIntoView({block:"center"});const r=e.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()');await panel.call('Input.dispatchMouseEvent',{type:'mousePressed',...point,button:'left',clickCount:1});await panel.call('Input.dispatchMouseEvent',{type:'mouseReleased',...point,button:'left',clickCount:1})};
 const open=async()=>{await click('document.querySelector("#more")');await click('document.querySelector("#approval-menu-item")');await until(()=>panel.evaluate('Boolean(document.querySelector("#access-menu .access-opt:not(:disabled)"))'),'permission menu loaded')};
 const pick=value=>click('document.querySelector('+JSON.stringify('#access-menu [data-preset="'+value+'"]')+')');
 const current=()=>client.call('session.permission',{sessionId:status.sessionId});
 await until(()=>panel.evaluate('document.querySelector("#approval-menu-item").textContent.includes("Read only")'),'visible current mode');
 assert.equal(inputs.length,0,'reading permissions never calls the model');
 assert.equal((await message({type:'permission',action:'select',sourceSession:'unrelated-chat',preset:'danger-full-access',expectedRevision:'initial'})).ok,false);
 assert.equal((await message({type:'permission',action:'select',sourceSession:status.sessionId,preset:'unsupported',expectedRevision:'initial'})).ok,false);
 assert.equal((await current()).currentValue,'read-only');
 const browserInfo=await fetch('http://127.0.0.1:'+port+'/json/version').then(r=>r.json()),browser=await cdp(browserInfo.webSocketDebuggerUrl);sockets.push(browser);
 const tab=(await browser.call('Target.getTargets',{filter:[{type:'tab',exclude:false}]})).targetInfos.find(row=>row.url===base+'/page');await panel.evaluate('chrome.sidePanel.setOptions({enabled:false})');await browser.call('Extensions.triggerAction',{id:extensionId,targetId:tab.targetId});
 const prompt=async marker=>{assert.equal((await message({type:'prompt',text:marker})).accepted,true)};
 const finished=marker=>until(()=>panel.evaluate('document.body.innerText.includes('+JSON.stringify(marker+' finished.')+')&&!document.querySelector("#send").disabled'),'turn finished '+marker).catch(async e=>{e.message+=' '+JSON.stringify({body:await panel.evaluate('document.body.innerText'),requests:inputs.length,stderr});throw e});
 await prompt('PERMISSION_READONLY');await finished('PERMISSION_READONLY');
 assert.equal(await page.evaluate('document.querySelector("#fixture-input").value'),'');assert.equal(await page.evaluate('document.body.dataset.clicks??"0"'),'0');assert.equal(await page.evaluate('location.search'),'');assert.equal(panel.dialogs.length,0);
 assert.match(JSON.stringify(inputs),/Read-only chat: actions that can change state are disabled/);
 await open();assert.equal(await panel.evaluate('document.querySelector("#access-menu .access-opt.current").dataset.preset'),'read-only');
 await pick('workspace-write');await until(async()=>(await current()).currentValue==='workspace-write','current chat ask mode persisted');
 await until(()=>panel.evaluate('document.querySelector("#access-menu .access-opt.current").dataset.preset==="workspace-write"&&!document.querySelector("#access-menu .access-opt").disabled'),'ask mode displayed');
 assert.equal((await message({type:'permission',action:'select',sourceSession:status.sessionId,preset:'danger-full-access',expectedRevision:'initial'})).ok,false,'stale revision cannot elevate permissions');
 assert.equal((await current()).currentValue,'workspace-write');
 await click('document.querySelector("#input")');
 await prompt('PERMISSION_ASK');
 await until(()=>panel.dialogs.length===1,'navigation approval').catch(async e=>{e.message+=' '+JSON.stringify({dialogs:panel.dialogs,rounds:[...permissionRounds],last:inputs.at(-1)?.messages.slice(-6)});throw e});await panel.call('Page.handleJavaScriptDialog',{accept:true});
 await until(()=>panel.dialogs.length===2,'typing approval').catch(async e=>{e.message+=' '+JSON.stringify({dialogs:panel.dialogs,rounds:[...permissionRounds],last:inputs.at(-1)?.messages.slice(-8)});throw e});await panel.call('Page.handleJavaScriptDialog',{accept:true});
 await until(()=>panel.dialogs.length===3,'click approval');await panel.call('Page.handleJavaScriptDialog',{accept:false});
 await finished('PERMISSION_ASK');assert.equal(await page.evaluate('document.querySelector("#fixture-input").value'),'PERMISSION_ASK');assert.equal(await page.evaluate('document.body.dataset.clicks??"0"'),'0','denied click never ran');
 await open();const pending=pick('danger-full-access');await until(()=>panel.dialogs.length===4,'explicit full-access confirmation');await panel.call('Page.handleJavaScriptDialog',{accept:false});await pending;assert.equal((await current()).currentValue,'workspace-write');
 const accept=pick('danger-full-access');await until(()=>panel.dialogs.length===5,'second full-access confirmation');await panel.call('Page.handleJavaScriptDialog',{accept:true});await accept;
 await until(async()=>(await current()).currentValue==='danger-full-access','full access persisted');
 await panel.reload();await until(()=>panel.evaluate('document.querySelector("#approval-menu-item").textContent.includes("Full access")'),'reload displays saved mode');
 const before=panel.dialogs.length;await prompt('PERMISSION_FULL');await finished('PERMISSION_FULL');assert.equal(panel.dialogs.length,before,'full access executes without action approval');
 assert.equal(await page.evaluate('location.search'),'?PERMISSION_FULL');assert.equal(await page.evaluate('document.querySelector("#fixture-input").value'),'PERMISSION_FULL');assert.equal(await page.evaluate('document.body.dataset.clicks'),'1');
 const defaults=await client.call('settings.describe',{ns:'permission'});assert.equal(defaults.namespaces.find(row=>row.ns==='permission').value.defaultPreset,'read-only','current changes leave future-chat default alone');
 await open();await click('document.querySelector("#access-menu [data-scope=default]")');await until(()=>panel.evaluate('document.querySelector("#access-menu .access-opt.current").dataset.preset==="read-only"&&!document.querySelector("#access-menu .access-opt").disabled'),'separate future default');
 await pick('workspace-write');await until(async()=>(await client.call('settings.describe',{ns:'permission'})).namespaces[0].value.defaultPreset==='workspace-write','future default saved');
 assert.equal((await current()).currentValue,'danger-full-access','future default leaves current mode alone');

 // Two visible copies of the Browser UI must not present the same AH/Pi approval twice.
 await click('document.querySelector("#access-menu [data-scope=session]")');await until(()=>panel.evaluate('Boolean(document.querySelector("#access-menu .access-opt:not(:disabled)"))'),'return to current chat');await pick('workspace-write');await until(async()=>(await current()).currentValue==='workspace-write','dual-panel ask mode');
 const duplicateTarget=await page.call('Target.createTarget',{url:'chrome-extension://'+extensionId+'/sidepanel.html'});let duplicateInfo;await until(async()=>{duplicateInfo=(await targets()).find(row=>row.id===duplicateTarget.targetId);return duplicateInfo;},'second panel');const duplicate=await cdp(duplicateInfo.webSocketDebuggerUrl);sockets.push(duplicate);await duplicate.call('Page.enable');await until(()=>duplicate.evaluate('document.querySelector("#approval-menu-item")?.textContent.includes("Ask before actions")'),'second panel ready');
 const seen=new Map([[panel,panel.dialogs.length],[duplicate,0]]);await prompt('PERMISSION_DUAL');
 for(let n=0;n<3;n++){
   let owner;await until(()=>{owner=[panel,duplicate].find(p=>p.dialogs.length>(seen.get(p)??0));return !!owner;},'one approval owner for action '+n);seen.set(owner,owner.dialogs.length);await owner.call('Page.handleJavaScriptDialog',{accept:true});
 }
 await finished('PERMISSION_DUAL');assert.equal(panel.dialogs.length+duplicate.dialogs.length,before+3,'exactly one approval per action across two panels');assert.equal(await page.evaluate('document.body.dataset.clicks'),'1');await page.call('Target.closeTarget',{targetId:duplicateTarget.targetId});
 assert.deepEqual(panel.errors,[]);
});
