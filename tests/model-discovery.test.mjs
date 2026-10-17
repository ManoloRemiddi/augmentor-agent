// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';import http from 'node:http';import {once} from 'node:events';
import {mkdtempSync,readFileSync,writeFileSync,rmSync,existsSync} from 'node:fs';import {join} from 'node:path';import {tmpdir} from 'node:os';
import {ModelRuntime} from '@earendil-works/pi-coding-agent';import {InMemoryCredentialStore} from '@earendil-works/pi-ai';
import {ModelSettings} from '../dist/runtime/src/model-settings.js';import {DshModelScope} from '../apps/harness/dsh-model-scope.mjs';
async function fixture(t,handler,overrides={}){
 const calls=[],server=http.createServer((req,res)=>{calls.push({method:req.method,url:req.url,headers:req.headers});handler(req,res,calls.length);});server.listen(0,'127.0.0.1');await once(server,'listening');t.after(async()=>{server.closeAllConnections();await new Promise(resolve=>server.close(resolve));});
 const root=mkdtempSync(join(tmpdir(),'augmentor-discovery-')),file=join(root,'models.json'),url='http://127.0.0.1:'+server.address().port;
 const config={providers:{'authored-relay':{api:'openai-completions',baseUrl:url+'/v1',apiKey:'private-$$literal',headers:{'x-authored-private':'deployment-header'},models:[{id:'existing',contextWindow:32000,maxTokens:1024}],...overrides}}};writeFileSync(file,JSON.stringify(config));t.after(()=>rmSync(root,{recursive:true,force:true}));
 const credentials=new InMemoryCredentialStore(),runtime=await ModelRuntime.create({modelsPath:file,credentials,allowModelNetwork:false,refreshOnCreate:false});assert(!runtime.getError());
 const settings=new ModelSettings(file,()=>runtime,()=>{},async()=>{throw Error('Discovery must never persist');});
 return {settings,runtime,credentials,file,url,calls,root,raw:()=>readFileSync(file,'utf8'),request:{provider:'authored-relay',baseURL:url+'/v1',api:'openai-completions'}};
}
const reply=(res,body)=>{res.writeHead(200,{'content-type':'application/json'});res.end(JSON.stringify(body));};
const until=async(predicate)=>{const deadline=Date.now()+2000;while(Date.now()<deadline){if(predicate())return;await new Promise(resolve=>setTimeout(resolve,10));}throw Error('Discovery readiness timed out');};
test('original listing parser uses exact native paths and safe public auth without persistence or DSH attribution',async t=>{
 const f=await fixture(t,(_req,res)=>reply(res,{data:[{id:'listed',display_name:'Listed model',context_length:64000,max_output_tokens:2048},{id:'listed',name:'Duplicate'},{id:'bad whitespace '},{id:'nested',limit:{context:8192,output:512}}],has_more:true})),before=f.raw();
 const out=await f.settings.discover(f.request);assert.equal(out.kind,'found');assert.deepEqual(out.models,[{id:'listed',name:'Listed model',contextWindow:64000,maxTokens:2048},{id:'nested',name:'nested',contextWindow:8192,maxTokens:512}]);assert.deepEqual(out.coverage,{source:'endpoint',pages:1,providerHasMore:true,droppedRows:2});
 assert.equal(f.calls.length,1);assert.equal(f.calls[0].method,'GET');assert.equal(f.calls[0].url,'/v1/models');assert.equal(f.calls[0].headers.authorization,'Bearer private-$literal');assert.equal(f.calls[0].headers['x-authored-private'],'deployment-header');assert(!JSON.stringify(out).includes('private-$literal'));assert(!f.calls[0].headers['user-agent']?.includes('deepseek'));assert(!f.calls[0].headers['http-referer']);assert.equal(f.raw(),before);assert.equal(f.runtime.getModels('authored-relay').length,1);assert.equal(f.settings.activeDiscoveries,0);
});
test('original Anthropic paths, API-version header and enriched alias map preserve only advertised metadata',async t=>{
 const f=await fixture(t,(_req,res)=>reply(res,{models:{alias:{id:'canonical',displayName:'Alias model',limit:{context:16384,output:256}},ignore:'directory metadata'}}));
 for(const baseURL of [f.url,f.url+'/v1',f.url+'/v1/']){
  const out=await f.settings.discover({...f.request,baseURL,api:'anthropic-messages',apiKey:'one-shot'});assert.equal(out.kind,'found');assert.deepEqual(out.models,[{id:'alias',name:'Alias model',contextWindow:16384,maxTokens:256}]);
  const call=f.calls.at(-1);assert.equal(call.url,'/v1/models?limit=1000');assert.equal(call.headers['x-api-key'],'one-shot');assert.equal(call.headers['anthropic-version'],'2023-06-01');
 }
 assert.equal(JSON.parse(f.raw()).providers['authored-relay'].apiKey,'private-$$literal');
});
test('one-shot literal credentials override a command key without resolving it; changed origins never receive stored auth',async t=>{
 const marker=join(tmpdir(),crypto.randomUUID());t.after(()=>rmSync(marker,{force:true}));const f=await fixture(t,(_req,res)=>reply(res,{data:[{id:'one'}]}),{apiKey:'!touch '+marker});
 assert.equal((await f.settings.discover(f.request)).kind,'refused');assert.equal(f.calls.length,0);
 assert.equal((await f.settings.discover({...f.request,apiKey:'!literal-$NOT_AN_ENV'})).kind,'found');assert.equal(f.calls[0].headers.authorization,'Bearer !literal-$NOT_AN_ENV');assert(!existsSync(marker));
 const other=await fixture(t,(_req,res)=>reply(res,{data:[]}));const blocked=await f.settings.discover({...f.request,baseURL:other.url+'/v1'});assert.equal(blocked.kind,'refused');assert.equal(other.calls.length,0);
 assert.equal((await f.settings.discover({...f.request,baseURL:other.url+'/v1',apiKey:'explicit-new-origin'})).kind,'found');assert.equal(other.calls[0].headers.authorization,'Bearer explicit-new-origin');assert.equal(other.calls[0].headers['x-authored-private'],undefined);
});
test('cold provider-only and native installed catalogs never contact endpoints, resolve keys or change configuration',async t=>{
 const f=await fixture(t,(_req,res)=>res.writeHead(500).end());const before=f.raw();assert.equal((await f.settings.discover({provider:'authored-relay'})).models[0].id,'existing');
 assert((await f.settings.discover({provider:'openai',baseURL:f.url+'/v1',apiKey:'ignored-private-key'})).models.length>0);assert.equal(f.calls.length,0);assert.equal(f.raw(),before);
});
test('unsupported API, unsafe URLs, invalid key, redirects, non-JSON/auth failures and oversized bodies refuse without leaking response secrets',async t=>{
 const f=await fixture(t,(req,res)=>{if(req.url.startsWith('/redirect/')){res.writeHead(302,{location:'/should-not-follow'}).end();}else if(req.url.startsWith('/oversize/')){res.writeHead(200,{'content-length':String(4*1024*1024+1)}).end();}else if(req.url.startsWith('/stream/')){res.writeHead(200);res.end('x'.repeat(4*1024*1024+1));}else if(req.url.startsWith('/auth/')){res.writeHead(401).end('SECRET_REFLECTED_TOKEN');}else res.end('SECRET_NON_JSON');});
 for(const request of [{...f.request,api:'google-generative-ai'},{...f.request,baseURL:'https://user:secret@example.invalid'},{...f.request,baseURL:f.url+'/v1?secret=x'},{...f.request,apiKey:'bad\nkey'}]){const count=f.calls.length;assert.equal((await f.settings.discover(request)).kind,'refused');assert.equal(f.calls.length,count);}
 for(const path of ['redirect','oversize','stream','auth','not-json']){const out=await f.settings.discover({...f.request,baseURL:f.url+'/'+path,apiKey:'one-shot'});assert.equal(out.kind,'refused');assert(!JSON.stringify(out).includes('SECRET_'));}
 assert(!f.calls.some(call=>call.url==='/should-not-follow'));assert.equal(f.settings.activeDiscoveries,0);
});
test('caller cancellation and two-listing capacity settle exact requests; late profile changes never publish candidates',async t=>{
 let release;const f=await fixture(t,(_req,res)=>{release=()=>reply(res,{data:[{id:'late'}]});});const a=new AbortController(),b=new AbortController();
 const first=f.settings.discover(f.request,a.signal);await until(()=>f.calls.length===1);const second=f.settings.discover(f.request,b.signal);await until(()=>f.calls.length===2);assert.equal(f.settings.activeDiscoveries,2);
 assert.equal((await f.settings.discover(f.request)).kind,'refused');assert.equal(f.calls.length,2);a.abort();b.abort();assert.equal((await first).kind,'refused');assert.equal((await second).kind,'refused');assert.equal(f.settings.activeDiscoveries,0);
 const late=f.settings.discover(f.request);await until(()=>f.calls.length===3);const config=JSON.parse(f.raw());config.extra='changed externally';writeFileSync(f.file,JSON.stringify(config));release();assert.equal((await late).kind,'refused');assert.equal(f.settings.activeDiscoveries,0);
});
test('header-only relays retain literal deployment headers while stale snapshots and command header expressions refuse auth resolution',async t=>{
 const f=await fixture(t,(_req,res)=>reply(res,{data:[]}),{apiKey:undefined,headers:{'x-authored-private':'$$literal-$!'}});assert.equal((await f.settings.discover(f.request)).kind,'found');assert.equal(f.calls[0].headers['x-authored-private'],'$literal-!');
 const stored=JSON.parse(f.raw());stored.providers['authored-relay'].headers.secret='!must-not-run';writeFileSync(f.file,JSON.stringify(stored));assert.equal((await f.settings.discover(f.request)).kind,'refused');assert.equal(f.calls.length,1);await f.runtime.refresh({allowNetwork:false,providers:['authored-relay']});f.settings.markApplied();let authReads=0;f.runtime.getAuth=async()=>{authReads++;throw Error('Header expressions must be refused before auth');};assert.equal((await f.settings.discover(f.request)).kind,'refused');assert.equal(authReads,0);assert.equal(f.calls.length,1);
});
test('original form scope aborts an in-flight discovery on operator revocation and never adopts late candidates',async()=>{
 const listeners=new Set();let signal,release;const controller={epoch:1,state:{phase:'ready',readOnly:false,capabilities:{modelSettings:true}},subscribe:fn=>{listeners.add(fn);return()=>listeners.delete(fn);},rpc:async(method,_params,requestSignal)=>method==='models.settingsDescribe'?{writable:true,revision:1,rows:[],namespaces:[{ns:'llm-pi-ai',revision:1,user:{providers:{}},base:{},value:{},schema:{apis:[]}}]}:new Promise(resolve=>{signal=requestSignal;release=resolve;})};const scope=new DshModelScope(controller);await scope.load();const pending=scope.operations.discoverModels('llm-pi-ai',{baseURL:'http://127.0.0.1:1'});await until(()=>!!release);controller.state.readOnly=true;for(const listener of listeners)listener();assert(signal.aborted);release({kind:'found',models:[{id:'late'}],coverage:{source:'endpoint',providerHasMore:true}});assert.equal((await pending).kind,'refused');assert(!scope.accepted);assert.equal(scope.pendingDiscoveries.size,0);assert.equal(scope.snapshot.rows.length,0);scope.close();
});
test('expired stored OAuth metadata keeps keys read-only and refuses discovery without refreshing an account; a typed key bypasses the stored credential',async t=>{
 const f=await fixture(t,(_req,res)=>reply(res,{data:[]})),before=f.raw();await f.credentials.modify('authored-relay',async()=>({type:'oauth',access:'expired-authored-access',refresh:'authored-refresh',expires:1}));
 const descriptor=await f.settings.describe();assert.equal(descriptor.rows.find(row=>row.entry.provider==='authored-relay').credential.writable,false);assert.equal((await f.settings.credential('AUTHORED_RELAY_API_KEY')).writable,false);await assert.rejects(f.settings.setCredential('AUTHORED_RELAY_API_KEY','replacement',descriptor.revision),/OAuth/);assert.equal((await f.settings.discover(f.request)).kind,'refused');assert.equal(f.calls.length,0);
 let reads=0;f.credentials.read=async()=>{reads++;throw Error('Stored credentials must not be read for a one-shot key');};assert.equal((await f.settings.discover({...f.request,apiKey:'one-shot'})).kind,'found');assert.equal(reads,0);assert.equal(f.calls[0].headers.authorization,'Bearer one-shot');assert.equal(f.raw(),before);
});
test('a stalled listing reaches the fixed twelve-second deadline and releases its exact active slot without saving or replay',{timeout:20000},async t=>{
 const f=await fixture(t,()=>{}),before=f.raw(),started=Date.now();const out=await f.settings.discover(f.request);assert.equal(out.kind,'refused');assert(out.message.includes('time limit'));assert(Date.now()-started>=11000);assert.equal(f.calls.length,1);assert.equal(f.settings.activeDiscoveries,0);assert.equal(f.raw(),before);
});
test('environment-backed provider keys and headers resolve only for explicit same-origin listing through public Pi auth and stay read-only in the form',async t=>{
 const keyName='AUGMENTOR_DISCOVERY_FIXTURE_KEY_'+process.pid,headerName='AUGMENTOR_DISCOVERY_FIXTURE_HEADER_'+process.pid;
 const previous=[process.env[keyName],process.env[headerName]];process.env[keyName]='authored-env-key';process.env[headerName]='authored-env-header';t.after(()=>{for(const [index,name] of [keyName,headerName].entries()){if(previous[index]===undefined)delete process.env[name];else process.env[name]=previous[index];}});
 const f=await fixture(t,(_req,res)=>reply(res,{data:[{id:'env-listed'}]}),{apiKey:'$'+keyName,headers:{'x-authored-env':'$'+headerName}}),before=f.raw();
 assert.equal((await f.settings.describe()).rows.find(row=>row.entry.provider==='authored-relay').credential.writable,false);assert.equal(f.calls.length,0);assert.equal((await f.settings.discover({provider:'authored-relay'})).kind,'found');assert.equal(f.calls.length,0);assert.equal((await f.settings.discover(f.request)).kind,'found');assert.equal(f.calls[0].headers.authorization,'Bearer authored-env-key');assert.equal(f.calls[0].headers['x-authored-env'],'authored-env-header');assert.equal(f.raw(),before);
});
