// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {mkdtemp,mkdir,writeFile,readFile,rm} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {tmpdir} from 'node:os';
import {fileURLToPath} from 'node:url';
import http from 'node:http';
import {setTimeout as delay} from 'node:timers/promises';
import assert from 'node:assert/strict';
import {PiConnection} from '../../dist/client/src/socket.js';
import {localConnect} from '../../dist/platform/src/transport.js';
import {oauthWire} from './mcp-oauth-wire.mjs';
export async function until(fn,label){const end=Date.now()+15000;while(Date.now()<end){if(await fn())return;await delay(25);}throw Error('MCP management fixture timeout: '+label);}
export async function managementOwner(t){
 const root=await mkdtemp(join(tmpdir(),'augmentor-mcp-manager-owner-')),config=join(root,'config'),agent=join(config,'agent'),state=join(root,'state'),cwd=join(root,'workspace'),home=join(root,'home'),network=join(root,'network.jsonl'),events=[],requests=[],wire=await oauthWire();
 for(const folder of [agent,cwd,home,state])await mkdir(folder,{recursive:true,mode:0o700});
 let providerGate,providerRelease,pendingProvider=0;
 const provider=http.createServer(async(req,res)=>{let raw='';for await(const chunk of req)raw+=chunk;const body=JSON.parse(raw);requests.push(body);if(providerGate){pendingProvider++;try{await providerGate;}finally{pendingProvider--;}}res.writeHead(200,{'content-type':'text/event-stream'});const chunk=(delta,finish)=>res.write('data: '+JSON.stringify({id:'authored-manager',object:'chat.completion.chunk',choices:[{index:0,delta,finish_reason:finish??null}]})+'\n\n');if(!body.messages.some(row=>row.role==='tool')){chunk({role:'assistant',tool_calls:[{index:0,id:'explicit-read',type:'function',function:{name:'mcp__web__read_record',arguments:'{}'}}]},'tool_calls');}else chunk({role:'assistant',content:'Authored manager explicit read settled.'},'stop');res.end('data: [DONE]\n\n');});provider.listen(0,'127.0.0.1');await once(provider,'listening');
 const selection={provider:'fixture',model:'manager-model'};
 await writeFile(join(agent,'models.json'),JSON.stringify({providers:{fixture:{api:'openai-completions',baseUrl:'http://127.0.0.1:'+provider.address().port+'/v1',apiKey:'authored-synthetic-only',models:[{id:selection.model,name:'Authored manager provider',reasoning:false,input:['text'],contextWindow:32768,maxTokens:1024}]}}}),{mode:0o600});
 await writeFile(join(agent,'mcp.json'),JSON.stringify({mcpServers:{web:wire.config,disabled:{...wire.config,enabled:false},header:{...wire.config,headers:{Authorization:'Bearer authored-static'},enabled:false}},augmentor:{readOnlyTools:['mcp__web__read_record']}}),{mode:0o600});
 await writeFile(join(config,'settings.json'),JSON.stringify({revision:0,defaultPreset:'read-only',defaultModel:selection,pinned:[],hidden:[],observation:{capturePayloads:true}}),{mode:0o600});
 const env=Object.fromEntries(Object.entries(process.env).filter(([key])=>!/^(AUGMENTOR_|DSH_|PI_)/.test(key)));Object.assign(env,{HOME:home,XDG_CONFIG_HOME:join(root,'xdg-config'),XDG_STATE_HOME:join(root,'xdg-state'),XDG_DATA_HOME:join(root,'xdg-data'),XDG_CACHE_HOME:join(root,'xdg-cache'),AUGMENTOR_PI_CONFIG:config,AUGMENTOR_PI_STATE:state,AUGMENTOR_SHARED_DATA:join(root,'shared-data'),AUGMENTOR_SHARED_STATE:join(root,'shared-state'),AUGMENTOR_PI_LINUX_TOOLS:'0',AUGMENTOR_HARNESS:'1',AUGMENTOR_PI_TEST_NETWORK_LOG:network,PI_OFFLINE:'1'});
 let owner,client,output='',errors='';
 const api={root,config,agent,state,cwd,home,network,events,requests,wire,selection,env,holdProvider(){if(providerGate)throw Error("Authored provider is already held");providerGate=new Promise(done=>providerRelease=done);},releaseProvider(){providerRelease?.();providerRelease=undefined;providerGate=undefined;},get pendingProvider(){return pendingProvider;},get client(){return client;},get owner(){return owner;},get errors(){return errors;},get link(){return this._link;},async start(){
  output='';errors='';owner=spawn(process.execPath,['--import',fileURLToPath(new URL('./pi-network-audit.mjs',import.meta.url)),join(resolve(process.env.AUGMENTOR_PI_TEST_ROOT||'.'),'dist/runtime/src/main.js')],{env,stdio:['ignore','pipe','pipe']});owner.stdout.on('data',data=>output+=data);owner.stderr.on('data',data=>errors+=data);
  await until(()=>{if(owner.exitCode!==null)throw Error(errors);return output.split('\n').some(line=>{try{return JSON.parse(line).ready;}catch{return false;}});},'owner ready');const socket=localConnect(join(state,'runtime.sock'));await once(socket,'connect');client=new PiConnection(socket,event=>events.push(event));await client.call('host.hello',{protocol:'augmentor-pi/1'});this._link=JSON.parse(await readFile(join(state,'harness.json'),'utf8'));
 },async stop(signal='SIGTERM'){client?.close();if(owner?.exitCode===null&&owner.signalCode===null){const exit=once(owner,'exit');owner.kill(signal);await exit;if(signal==='SIGTERM')assert.equal(owner.exitCode,0,errors);}},async create(sid='manager'){await client.call('session.create',{sessionId:sid,cwd,selection});await client.call('events.subscribe',{sessionId:sid});return sid;},async settle(sid,requestId){let row;await until(async()=>{row=await client.call('session.mcpActionStatus',{sessionId:sid,requestId});return !['running','cancel-requested'].includes(row.state);},'SDK command settlement');return row;},async authorize(sid,requestId){let row;await until(async()=>{row=await client.call('session.mcpActionStatus',{sessionId:sid,requestId});return !!row.authorizationUrl;},'authorization URL');const response=await fetch(row.authorizationUrl,{redirect:'manual'});assert.equal(response.status,302);const callback=await fetch(response.headers.get('location'));assert.equal(callback.status,200);return this.settle(sid,requestId);}};
 t.after(async()=>{api.releaseProvider();await api.stop();await wire.close();provider.closeAllConnections();await new Promise(resolve=>provider.close(resolve));await rm(root,{recursive:true,force:true,maxRetries:5,retryDelay:100});});
 await api.start();return api;
}
