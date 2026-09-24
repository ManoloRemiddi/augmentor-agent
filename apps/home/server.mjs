// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {createServer} from 'node:http';
import {timingSafeEqual} from 'node:crypto';
import {readFileSync,mkdirSync} from 'node:fs';
import {join} from 'node:path';
import {pathToFileURL} from 'node:url';
import {Ledger,Conflict} from './ledger.mjs';
import {createRuntime} from './runtime.mjs';

const identity=x=>typeof x==='string'&&/^[a-zA-Z0-9_-]{1,100}$/.test(x);
export function readConfig(env=process.env) {
  const secret=name=>{if(!env[name+'_FILE'])throw Error('Missing '+name+'_FILE');return readFileSync(env[name+'_FILE'],'utf8').trim();};
  const config={model:env.MODEL_ID,modelUrl:env.MODEL_BASE_URL,mcpUrl:env.HA_MCP_URL,stateDir:env.HOME_STATE_DIR??'/state',haToken:secret('HA_TOKEN'),token:secret('HOME_AGENT_TOKEN')};
  if(config.token.length<24)throw Error('Service token too short');
  for(const key of ['modelUrl','mcpUrl']) {
    const u=new URL(config[key]);
    if(!['http:','https:'].includes(u.protocol)||u.username||u.password||u.search||u.hash)throw Error('Invalid '+key);
    if(u.protocol==='http:'&&!['127.0.0.1','localhost','[::1]'].includes(u.hostname)&&env.HOME_ALLOW_LAN_HTTP!=='1')throw Error('Non-loopback HTTP requires explicit HOME_ALLOW_LAN_HTTP=1 or HTTPS');
  }
  if(!config.model)throw Error('MODEL_ID is required');
  if(!new URL(config.mcpUrl).pathname.endsWith('/api/mcp/assist'))throw Error('Use the restricted /api/mcp/assist endpoint');
  process.env.HOME_MODEL_KEY=secret('MODEL_API_KEY');
  return config;
}

export function httpService(config,ledger,runtime,{readiness=async()=>{
  const res=await fetch(config.mcpUrl,{method:'POST',headers:{Authorization:'Bearer '+config.haToken,'Content-Type':'application/json',Accept:'application/json, text/event-stream'},body:JSON.stringify({jsonrpc:'2.0',id:1,method:'initialize',params:{protocolVersion:'2025-03-26',capabilities:{},clientInfo:{name:'augmentor-readiness',version:'0.1.0'}}}),signal:AbortSignal.timeout(3000)});
  await res.body?.cancel();return res.ok;
}}={}) {
  let draining=false,admitted=false;
  const server=createServer(async(req,res)=>{
    const reply=(status,data)=>{if(!res.destroyed){res.writeHead(status,{'Content-Type':'application/json','Cache-Control':'no-store','Connection':'close'});res.end(JSON.stringify(data));}};
    try {
      const actual=Buffer.from(req.headers.authorization??''),expected=Buffer.from('Bearer '+config.token);
      if(actual.length!==expected.length||!timingSafeEqual(actual,expected)){reply(401,{error:'Authentication required'});return;}
      if(req.headers.origin){reply(403,{error:'Browser-origin API requests are not enabled'});return;}
      if(req.method==='GET'&&req.url==='/health'){reply(200,{status:draining?'draining':'ok',runtime:'dsh',model:config.model,busy:admitted,memory:'household session history; long-term memory disabled'});return;}
      if(req.method==='GET'&&req.url==='/ready'){
        let ready=false;try{ready=!draining&&await readiness();}catch{}
        reply(ready?200:503,{ready,model:config.model,providerProbe:'not performed; no billable health calls'});return;
      }
      if(req.method==='GET'&&req.url==='/actions'){reply(200,{pending:ledger.pending()});return;}
      if(req.method==='GET'&&req.url?.startsWith('/requests/')){
        const id=req.url.slice('/requests/'.length);
        if(!identity(id)){reply(400,{error:'Invalid request ID'});return;}
        const result=ledger.request(id);reply(result?200:404,result??{error:'Unknown request'});return;
      }
      if(req.method==='GET'&&req.url==='/prompts'){
        const {promptCall}=await import('../../dist/prompt-library/src/client.js');
        reply(200,await promptCall('prompts.list'));return;
      }
      if(req.method!=='POST'||!['/ask','/cancel','/actions/acknowledge'].includes(req.url)){reply(404,{error:'Unknown endpoint'});return;}
      if(!req.headers['content-type']?.startsWith('application/json')){reply(415,{error:'Use application/json'});return;}
      if(req.headers['transfer-encoding']){reply(400,{error:'Content-Length required'});return;}
      const size=Number(req.headers['content-length']);
      if(!Number.isSafeInteger(size)||size<=0||size>16384){reply(413,{error:'Invalid body size'});return;}
      let bytes=0,chunks=[];for await(const chunk of req){bytes+=chunk.length;if(bytes>16384)throw Error('Body too large');chunks.push(chunk);}
      let body;try{body=JSON.parse(Buffer.concat(chunks));}catch{reply(400,{error:'Invalid JSON'});return;}
      if(!body||Array.isArray(body)||typeof body!=='object'){reply(400,{error:'Expected a JSON object'});return;}
      if(req.url==='/cancel'){runtime.cancel();reply(200,{status:'cancellation requested; inspect action outcomes'});return;}
      if(req.url==='/actions/acknowledge'){
        if(admitted){reply(409,{error:'Wait until the active request stops'});return;}
        if(!Number.isSafeInteger(body.action_id)||body.outcome_reviewed!==true){reply(400,{error:'An action_id and explicit outcome_reviewed=true are required'});return;}
        ledger.acknowledge(body.action_id);reply(200,{status:'acknowledged; no action replayed'});return;
      }
      if(!identity(body.request_id)||!identity(body.session_id)||typeof body.prompt!=='string'||!body.prompt.trim()||body.prompt.length>4000){reply(400,{error:'Supply request_id, session_id and a non-empty prompt up to 4000 characters'});return;}
      if(draining||admitted){reply(409,{error:'Home is busy; do not submit a new ID to repeat an uncertain request'});return;}
      admitted=true;
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
        const cached=ledger.begin(body.request_id,body.session_id,prompt);
        if(cached){reply(200,{...cached,replayed_response:true});return;}
        let result;
        try{result=await runtime.ask(body.request_id,body.session_id,prompt);}catch{result={request_id:body.request_id,session_id:body.session_id,status:'incomplete',reply:'Request interrupted. Inspect saved session and action outcomes before another action.'};}
        ledger.finish(body.request_id,result);reply(200,result);
      } finally {admitted=false;}
    } catch(error){reply(error instanceof Conflict?409:400,{error:error instanceof Conflict?error.message:'Invalid request'});}
  });
  server.requestTimeout=10000;server.headersTimeout=10000;server.timeout=10000;server.maxConnections=16;
  // Once the complete body is read, the bounded harness owns the response wait.
  server.on('request',(req)=>req.on('end',()=>req.socket.setTimeout(120000)));
  return {server,async close(){draining=true;server.close();runtime.cancel();await runtime.close();server.closeAllConnections();}};
}

export async function main(){
  process.umask(0o077);
  const config=readConfig();mkdirSync(config.stateDir,{recursive:true,mode:0o700});
  const ledger=new Ledger(join(config.stateDir,'actions.sqlite3'));
  const runtime=await createRuntime(config,ledger),app=httpService(config,ledger,runtime);
  app.server.listen(Number(process.env.PORT??8181),'127.0.0.1',()=>console.log('Augmentor Home ready on loopback; shared DSH runtime, HA Assist MCP'));
  let closing=false;
  const stop=async()=>{if(closing)return;closing=true;await app.close();ledger.close();};
  process.on('SIGTERM',()=>void stop());process.on('SIGINT',()=>void stop());
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href)main().catch(()=>{console.error('Home startup failed; check configured endpoints, credentials and dependencies.');process.exitCode=1;});
