// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {createServer} from 'node:http';
import {timingSafeEqual} from 'node:crypto';
import {readFileSync,mkdirSync,writeFileSync} from 'node:fs';
import {join} from 'node:path';
import {pathToFileURL} from 'node:url';
import {Ledger,Conflict} from './ledger.mjs';
import {createRuntime} from './runtime.mjs';
import {loadModelSettings,saveModelSettings,modelSettings,publicModelSettings,discoverModels} from './settings.mjs';
import {readDiscovery} from './discovery.mjs';
import {Identity,digest,safeEqual} from './identity.mjs';

const identity=x=>typeof x==='string'&&/^[a-zA-Z0-9_-]{1,100}$/.test(x);
export function readConfig(env=process.env) {
  const secret=name=>{if(!env[name+'_FILE'])throw Error('Missing '+name+'_FILE');return readFileSync(env[name+'_FILE'],'utf8').trim();};
  const config={model:env.MODEL_ID,modelUrl:env.MODEL_BASE_URL,mcpUrl:env.HA_MCP_URL,stateDir:env.HOME_STATE_DIR??'/state',haToken:secret('HA_TOKEN'),token:secret('HOME_AGENT_TOKEN'),publicOrigin:env.HOME_PUBLIC_ORIGIN,deviceMode:env.HOME_DEVICE_MODE??'selected'};
  if(!['selected','assist-preview'].includes(config.deviceMode))throw Error('Invalid Home device mode');
  if(config.token.length<24)throw Error('Service token too short');
  for(const key of ['modelUrl','mcpUrl']) {
    const u=new URL(config[key]);
    if(!['http:','https:'].includes(u.protocol)||u.username||u.password||u.search||u.hash)throw Error('Invalid '+key);
    if(u.protocol==='http:'&&!['127.0.0.1','localhost','[::1]'].includes(u.hostname)&&env.HOME_ALLOW_LAN_HTTP!=='1')throw Error('Non-loopback HTTP requires explicit HOME_ALLOW_LAN_HTTP=1 or HTTPS');
  }
  if(config.publicOrigin){const u=new URL(config.publicOrigin);if(u.origin!==config.publicOrigin||u.protocol!=='https:')throw Error('HOME_PUBLIC_ORIGIN must be an HTTPS origin');}
  if(!config.model)throw Error('MODEL_ID is required');
  if(!new URL(config.mcpUrl).pathname.endsWith('/api/mcp/assist'))throw Error('Use the restricted /api/mcp/assist endpoint');
  process.env.HOME_MODEL_KEY=secret('MODEL_API_KEY');
  const saved=loadModelSettings(config);if(saved){const {key,...settings}=saved;Object.assign(config,settings);process.env.HOME_MODEL_KEY=key||'local-no-key';}
  return config;
}

export function httpService(config,ledger,runtime,{readiness=async()=>{
  if(runtime.devices){await runtime.devices.rest('/api/');return true;}
  const res=await fetch(config.mcpUrl,{method:'POST',headers:{Authorization:'Bearer '+config.haToken,'Content-Type':'application/json',Accept:'application/json, text/event-stream'},body:JSON.stringify({jsonrpc:'2.0',id:1,method:'initialize',params:{protocolVersion:'2025-03-26',capabilities:{},clientInfo:{name:'augmentor-readiness',version:'0.1.0'}}}),signal:AbortSignal.timeout(3000)});
  await res.body?.cancel();return res.ok;
}}={}) {
  const identities=new Identity(ledger.db),attempts=new Map();
  const scoped=(client,id)=>client.id==='operator'?id:digest(client.id+':'+id);
  let draining=false,admitted=false,activeClient=null,directAbort=null;
  async function json(req){
    if(!req.headers['content-type']?.startsWith('application/json'))throw Error('Use application/json');
    const size=Number(req.headers['content-length']);
    if(req.headers['transfer-encoding']||!Number.isSafeInteger(size)||size<=0||size>16384)throw Error('Invalid body size');
    let bytes=0,chunks=[];for await(const chunk of req){bytes+=chunk.length;if(bytes>16384)throw Error('Body too large');chunks.push(chunk);}
    const body=JSON.parse(Buffer.concat(chunks));if(!body||Array.isArray(body)||typeof body!=='object')throw Error('Expected JSON object');return body;
  }
  function browserOrigin(req){
    if(config.publicOrigin)return config.publicOrigin;
    const u=new URL('http://'+req.headers.host);
    if(!['127.0.0.1','localhost','[::1]'].includes(u.hostname)||u.username||u.password||u.pathname!=='/')throw Error('Host not allowed');
    return u.origin;
  }
  const server=createServer(async(req,res)=>{
    const reply=(status,data,headers={})=>{if(!res.destroyed&&!res.writableEnded){res.writeHead(status,{'Content-Type':'application/json','Cache-Control':'no-store','Connection':'close','X-Content-Type-Options':'nosniff',...headers});res.end(JSON.stringify(data));}};
    try {
      if(req.method==='GET'&&['/','/home.js','/home.css'].includes(req.url)){
        browserOrigin(req);
        const file=req.url==='/'?'index.html':req.url.slice(1);
        res.writeHead(200,{'Content-Type':file.endsWith('.html')?'text/html; charset=utf-8':file.endsWith('.js')?'text/javascript':'text/css','Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"});
        res.end(readFileSync(new URL('./web/'+file,import.meta.url)));return;
      }
      if(req.method==='POST'&&req.url==='/pair'){
        const origin=browserOrigin(req);
        if(req.headers.origin&&req.headers.origin!==origin){reply(403,{error:'Origin not allowed'});return;}
        const peer=req.socket.remoteAddress??'local',now=Date.now();
        let limit=attempts.get(peer);if(!limit||limit.until<now){limit={count:0,until:now+60000};if(attempts.size>256)attempts.clear();attempts.set(peer,limit);}
        if(++limit.count>5){reply(429,{error:'Wait a minute before trying another pairing code'});return;}
        const body=await json(req),paired=identities.pair(body.code,body.name,body.kind);
        if(body.kind==='browser'){
          reply(200,{id:paired.id,role:paired.role},{'Set-Cookie':`augmentor_home=${paired.token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=604800${origin.startsWith('https:')?'; Secure':''}`});
        }else reply(200,paired);
        return;
      }
      const client=identities.authenticate(req,config.token);
      if(!client){reply(401,{error:'Authentication required'});return;}
      if(client.kind==='browser'){
        const origin=browserOrigin(req);
        if(req.headers.origin&&req.headers.origin!==origin||req.method!=='GET'&&(req.headers.origin!==origin||!safeEqual(String(req.headers['x-home-csrf']??''),client.csrf))){reply(403,{error:'Origin or session verification failed'});return;}
      }else if(req.headers.origin){reply(403,{error:'Browser-origin bearer requests are not enabled'});return;}
      if(req.method==='GET'&&req.url==='/identity'){reply(200,client);return;}
      if(req.method==='GET'&&req.url==='/capabilities'){reply(200,{protocol:'augmentor-home/1',role:client.role,requests:{persistent:true,async:true,scoped:true},model:config.model,capabilities:client.role==='viewer'?['home.read','home.result']:['home.read','home.request','home.result','home.cancel'],devices:runtime.devices?'Owner-selected registered entities':'Assist preview: exposed named lights, switches and helpers'});return;}
      if(req.method==='GET'&&req.url==='/clients'){if(client.role!=='owner'){reply(403,{error:'Owner access required'});return;}reply(200,{clients:identities.list()});return;}
      if(req.method==='POST'&&['/clients/invite','/clients/revoke','/logout'].includes(req.url)){
        const body=await json(req);
        if(req.url==='/logout'){identities.revoke(client.id);if(activeClient===client.id){directAbort?.abort();runtime.cancel();}reply(200,{status:'disconnected'},{'Set-Cookie':'augmentor_home=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'});return;}
        if(client.role!=='owner'){reply(403,{error:'Owner access required'});return;}
        if(req.url==='/clients/invite')reply(200,identities.invite(body.role));
        else{if(typeof body.id!=='string')throw Error('Invalid client');identities.revoke(body.id);if(activeClient===body.id){directAbort?.abort();runtime.cancel();}reply(200,{status:'revoked'});}return;
      }
      if(req.method==='GET'&&req.url==='/devices/discovered'){if(client.role!=='owner'){reply(403,{error:'Owner access required'});return;}reply(200,readDiscovery(config.stateDir));return;}
      if(req.method==='GET'&&['/devices','/devices/selected'].includes(req.url)){
        if(!runtime.devices){reply(409,{error:'Selected-device mode is not enabled'});return;}
        reply(200,client.role==='owner'&&req.url==='/devices'?{devices:await runtime.devices.inventory()}:await runtime.devices.list());return;
      }
      if(req.method==='POST'&&req.url==='/devices/select'){
        if(client.role!=='owner'){reply(403,{error:'Owner access required'});return;}
        if(admitted||!runtime.devices){reply(409,{error:'Wait until Home is idle in selected-device mode'});return;}
        const body=await json(req);if(body.control===true&&body.effects_reviewed!==true)throw Error('Review what this device and its existing automations can do');
        admitted=true;try{await runtime.devices.select(body.entity_id,body.enabled,body.control);reply(200,{status:'saved'});}finally{admitted=false;}return;
      }
      if(req.method==='GET'&&req.url==='/model'){
        if(client.role!=='owner'){reply(403,{error:'Owner access required'});return;}
        reply(200,publicModelSettings(config));return;
      }
      if(req.method==='POST'&&['/model/discover','/model/save'].includes(req.url)){
        if(client.role!=='owner'){reply(403,{error:'Owner access required'});return;}
        if(admitted||ledger.pending().length){reply(409,{error:'Wait until Home is idle and uncertain actions have been reviewed'});return;}
        const body=await json(req),previous={...config,key:process.env.HOME_MODEL_KEY??''},selected=modelSettings(body,previous);
        admitted=true;
        try{
          if(req.url==='/model/discover'){reply(200,await discoverModels(selected));return;}
          const {key,...settings}=selected,nextConfig={...config,...settings};let nextRuntime;
          process.env.HOME_MODEL_KEY=key||'local-no-key';
          try{nextRuntime=await createRuntime(nextConfig,ledger);saveModelSettings(config,selected);}
          catch(error){await nextRuntime?.close();process.env.HOME_MODEL_KEY=previous.key;throw error;}
          await runtime.close();runtime=nextRuntime;Object.assign(config,settings);reply(200,publicModelSettings(config));
        }finally{admitted=false;}
        return;
      }
      if(req.method==='GET'&&req.url==='/health'){reply(200,{status:draining?'draining':'ok',runtime:'dsh',model:config.model,busy:admitted,memory:'household session history; long-term memory disabled'});return;}
      if(req.method==='GET'&&req.url==='/ready'){
        let ready=false;try{ready=!draining&&await readiness();}catch{}
        reply(ready?200:503,{ready,model:config.model,providerProbe:'not performed; no billable health calls'});return;
      }
      if(req.method==='GET'&&req.url==='/actions'){reply(200,{pending:ledger.pending().filter(a=>client.role==='owner'||ledger.request(a.request)?.owner===client.id)});return;}
      if(req.method==='GET'&&req.url?.startsWith('/requests/')){
        const id=req.url.slice('/requests/'.length);
        if(!identity(id)){reply(400,{error:'Invalid request ID'});return;}
        const result=ledger.request(scoped(client,id));reply(result?200:404,result?{...result,recovery_blocked:ledger.pending().length>0}:{error:'Unknown request'});return;
      }
      if(req.method==='GET'&&req.url==='/prompts'){
        const {promptCall}=await import('../../dist/prompt-library/src/client.js');
        reply(200,await promptCall('prompts.list'));return;
      }
      if(req.method!=='POST'||!['/ask','/device-actions','/cancel','/actions/acknowledge'].includes(req.url)){reply(404,{error:'Unknown endpoint'});return;}
      if(!req.headers['content-type']?.startsWith('application/json')){reply(415,{error:'Use application/json'});return;}
      if(req.headers['transfer-encoding']){reply(400,{error:'Content-Length required'});return;}
      const size=Number(req.headers['content-length']);
      if(!Number.isSafeInteger(size)||size<=0||size>16384){reply(413,{error:'Invalid body size'});return;}
      let bytes=0,chunks=[];for await(const chunk of req){bytes+=chunk.length;if(bytes>16384)throw Error('Body too large');chunks.push(chunk);}
      let body;try{body=JSON.parse(Buffer.concat(chunks));}catch{reply(400,{error:'Invalid JSON'});return;}
      if(!body||Array.isArray(body)||typeof body!=='object'){reply(400,{error:'Expected a JSON object'});return;}
      if(req.url==='/cancel'){if(activeClient&&activeClient!==client.id&&client.role!=='owner'){reply(403,{error:'This request belongs to another client'});return;}directAbort?.abort();runtime.cancel();reply(200,{status:'cancellation requested; inspect action outcomes'});return;}
      if(req.url==='/actions/acknowledge'){
        if(client.role!=='owner'){reply(403,{error:'Owner access required'});return;}
        if(admitted){reply(409,{error:'Wait until the active request stops'});return;}
        if(!Number.isSafeInteger(body.action_id)||body.outcome_reviewed!==true){reply(400,{error:'An action_id and explicit outcome_reviewed=true are required'});return;}
        ledger.acknowledge(body.action_id);reply(200,{status:'acknowledged; no action replayed'});return;
      }
      const direct=req.url==='/device-actions';
      if(direct){
        if(client.role==='viewer'){reply(403,{error:'Read-only Home access'});return;}
        if(!runtime.devices){reply(409,{error:'Selected-device mode is required'});return;}
        if(!body.action||typeof body.action!=='object'||Array.isArray(body.action)){reply(400,{error:'Invalid device action'});return;}
        body.prompt=JSON.stringify(body.action);
      }
      if(!identity(body.request_id)||!identity(body.session_id)||typeof body.prompt!=='string'||!body.prompt.trim()||body.prompt.length>4000){reply(400,{error:'Supply request_id, session_id and a non-empty prompt up to 4000 characters'});return;}
      if(draining||admitted){reply(409,{error:'Home is busy; do not submit a new ID to repeat an uncertain request'});return;}
      admitted=true;activeClient=client.id;directAbort=new AbortController();
      try {
        let prompt=body.prompt;
        if(body.prompt_id!==undefined){
          if(typeof body.prompt_id!=='string')throw Error('Invalid prompt ID');
          const {promptCall}=await import('../../dist/prompt-library/src/client.js');
          const library=await promptCall('prompts.list');
          const selected=library.prompts.find(p=>p.id===body.prompt_id);
          if(!selected)throw Error('Unknown saved prompt');
          prompt=selected.content+'\n\n'+prompt;
        }
        if(directAbort.signal.aborted)throw Error('Request cancelled before admission');
        const requestId=scoped(client,body.request_id),sessionId=scoped(client,body.session_id);
        const cached=ledger.begin(requestId,sessionId,prompt,client.id);
        if(cached){reply(200,{...cached,replayed_response:true});return;}
        const asynchronous=body.async===true;
        if(asynchronous)reply(202,{status:'accepted',request_id:body.request_id});
        let result;
        try{
          if(direct){
            await runtime.devices.validate(body.action,directAbort.signal);
            const actionId=ledger.reserve(requestId,'home_set',body.action);
            try{const outcome=await runtime.devices.execute(body.action,directAbort.signal);ledger.outcome(actionId,outcome.status);result={...outcome,reply:outcome.evidence,action_id:actionId};}
            catch{ledger.outcome(actionId,'unknown');result={status:'unknown',reply:'Device action outcome is unknown. Inspect it before another change.',action_id:actionId};}
          }else result=await runtime.ask(requestId,sessionId,prompt,{readOnly:client.role==='viewer'||body.read_only===true,signal:directAbort.signal});
        }catch{result={request_id:body.request_id,session_id:body.session_id,status:'incomplete',reply:'Request interrupted. Inspect saved session and action outcomes before another action.'};}
        result={...result,request_id:body.request_id,session_id:body.session_id};
        ledger.finish(requestId,result);if(!asynchronous)reply(200,result);
      } finally {admitted=false;activeClient=null;directAbort=null;}
    } catch(error){reply(error instanceof Conflict?409:400,{error:error instanceof Conflict?error.message:'Invalid request'});}
  });
  server.requestTimeout=10000;server.headersTimeout=10000;server.timeout=10000;server.maxConnections=16;
  // Once the complete body is read, the bounded harness owns the response wait.
  server.on('request',(req)=>req.on('end',()=>req.socket.setTimeout(120000)));
  return {server,identities,async close(){draining=true;server.close();directAbort?.abort();runtime.cancel();await runtime.close();server.closeAllConnections();}};
}

export async function main(){
  process.umask(0o077);
  const config=readConfig();mkdirSync(config.stateDir,{recursive:true,mode:0o700});
  const ledger=new Ledger(join(config.stateDir,'actions.sqlite3'));
  const runtime=await createRuntime(config,ledger),app=httpService(config,ledger,runtime);
  if(!app.identities.hasOwner()){const invite=app.identities.invite('owner');writeFileSync(join(config.stateDir,'pairing-code'),invite.code+'\n',{mode:0o600});}
  app.server.listen(Number(process.env.PORT??8181),'127.0.0.1',()=>console.log('Augmentor Home ready on loopback; shared DSH runtime, HA Assist MCP'));
  let closing=false;
  const stop=async()=>{if(closing)return;closing=true;await app.close();ledger.close();process.exit(0);};
  process.on('SIGTERM',()=>void stop());process.on('SIGINT',()=>void stop());
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href)main().catch(()=>{console.error('Home startup failed; check configured endpoints, credentials and dependencies.');process.exitCode=1;});
