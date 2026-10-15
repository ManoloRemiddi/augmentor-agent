// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Actual isolated image/CMD, API, SDK and authored HA/provider servers; never a live home.
import test from 'node:test';import assert from 'node:assert/strict';
import {spawn,execFile} from 'node:child_process';import {once} from 'node:events';import {promisify} from 'node:util';
const run=promisify(execFile);
import {mkdirSync,writeFileSync,readFileSync,readdirSync} from 'node:fs';import {join} from 'node:path';import {randomBytes,randomUUID} from 'node:crypto';
import {fixture,turnOn,args,tool,answer} from '../test/fixtures/runtime.mjs';
async function selectedImageFixture(t){
 const {fixture:devicesFixture}=await import('../test/fixtures/devices.mjs'),h=await devicesFixture(t),{mkdtempSync,rmSync}=await import('node:fs'),{tmpdir}=await import('node:os'),{createServer}=await import('node:http');
 const stateDir=mkdtempSync(join(tmpdir(),'home-image-selected-')),requests=[];
 const provider=createServer(async(req,res)=>{let raw='';for await(const chunk of req)raw+=chunk;requests.push(JSON.parse(raw));const delta=requests.length===1?tool('home_set',{entity_id:'light.fixture',action:'on'},'selected-image'):answer('Authored selected state observed');res.writeHead(200,{'content-type':'text/event-stream'});res.end('data: '+JSON.stringify({id:'image-selected',object:'chat.completion.chunk',choices:[{index:0,delta,finish_reason:delta.tool_calls?'tool_calls':'stop'}]})+'\n\ndata: [DONE]\n\n');});provider.listen(0,'127.0.0.1');await once(provider,'listening');
 t.after(async()=>{provider.closeAllConnections();await new Promise(done=>provider.close(done));rmSync(stateDir,{recursive:true,force:true});});
 return {config:{stateDir,model:'fixture',modelUrl:'http://127.0.0.1:'+provider.address().port+'/v1',mcpUrl:h.url+'/api/mcp/assist'},requests,writes:()=>h.writes.length};
}
const image=process.argv[2];if(!image)throw Error('Provide an already built, unselected Pi Home image.');
for(const mode of ['assist-preview','selected'])await test('isolated Pi Home '+mode+' image runs actual CMD, auth/API, SDK and shared prompts',{timeout:60000},async t=>{
 const h=mode==='selected'?await selectedImageFixture(t):await fixture(t,n=>n===1?tool(turnOn,args,'image-write'):answer('Authored integration acknowledgement'),{harness:'pi',startRuntime:false});
 const proof=join(h.config.stateDir,'proof');mkdirSync(proof,{mode:0o700});const operator=randomBytes(24).toString('hex');
 for(const [file,value] of Object.entries({model:'fixture',ha:'fixture',operator}))writeFileSync(join(proof,file),value,{mode:0o600});
 const ports=[new URL(h.config.modelUrl).port,new URL(h.config.mcpUrl).port].map(Number);
 writeFileSync(join(proof,'network.mjs'),`import net from 'node:net';import {appendFileSync} from 'node:fs';import {registerHooks} from 'node:module';
registerHooks({resolve(s,c,next){if(s.startsWith('@deepseek-ai/'))throw Error('Pi Home loaded a DSH package');return next(s,c);}});
const allowed=${JSON.stringify(ports)},connect=net.Socket.prototype.connect;net.Socket.prototype.connect=function(...args){const a=Array.isArray(args[0])?args[0][0]:args[0];let host,port;if(a&&typeof a==='object'&&!a.path){host=a.host||'localhost';port=a.port;}else if(typeof a==='number'){host=typeof args[1]==='string'?args[1]:'localhost';port=a;}if(port!==undefined){const ok=['127.0.0.1','localhost','::1'].includes(host)&&(allowed.includes(Number(port))||Number(process.env.PORT)>0&&Number(port)===Number(process.env.PORT));appendFileSync('/state/network.jsonl',JSON.stringify({host,port:Number(port),allowed:ok})+'\\n');if(!ok)throw Error('Unexpected Home destination');}return connect.apply(this,args);};`,{mode:0o600});
 const name='augmentor-home-pi-proof-'+randomUUID(),env={...process.env};let stdout='',stderr='';
 const command=['run','--rm','--init','--user',String(process.getuid())+':'+String(process.getgid()),'--name',name,'--network=host','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--memory=1g','--memory-swap=1g','--cpus=1','--pids-limit=128','--no-healthcheck','--mount','type=bind,src='+h.config.stateDir+',dst=/state','--tmpfs','/tmp:rw,nosuid,nodev,size=134217728'];
 const settings={MODEL_ID:'fixture',MODEL_BASE_URL:h.config.modelUrl,HA_MCP_URL:h.config.mcpUrl,MODEL_API_KEY_FILE:'/state/proof/model',HA_TOKEN_FILE:'/state/proof/ha',HOME_AGENT_TOKEN_FILE:'/state/proof/operator',...(mode==='assist-preview'?{HOME_DEVICE_MODE:mode}:{}),PORT:'0',PI_TELEMETRY:'true',PI_CODING_AGENT_DIR:'/unrelated-cli',NODE_OPTIONS:'--import=/state/proof/network.mjs',AUGMENTOR_SHARED_STATE:'/state/shared-run',AUGMENTOR_SHARED_DATA:'/state/shared-data'};
 for(const [key,value] of Object.entries(settings))command.push('--env',key+'='+value);command.push(image);
 const child=spawn('docker',command,{env,stdio:['ignore','pipe','pipe']}),exited=once(child,'exit');child.stdout.on('data',data=>stdout+=data);child.stderr.on('data',data=>stderr+=data);
 const stop=async()=>{if(child.exitCode===null){await run('docker',['stop','--time=10',name]);const [code]=await exited;assert.equal(code,0,'Home graceful shutdown');}};t.after(stop);
 try{
 let address;const end=Date.now()+20000;while(Date.now()<end){assert.equal(child.exitCode,null,stderr);address=stdout.split('\n').filter(line=>line.startsWith('{')).map(line=>{try{return JSON.parse(line);}catch{return null;}}).find(row=>row?.event==='home.listening');if(address)break;await new Promise(done=>setTimeout(done,30));}assert(address,'Home actual listener: '+stderr);
 const request=async(path,body,auth=true)=>{const response=await fetch('http://127.0.0.1:'+address.port+path,{method:body===undefined?'GET':'POST',headers:{'content-type':'application/json',...(auth?{authorization:'Bearer '+operator}:{})},...(body===undefined?{}:{body:JSON.stringify(body)})});return {status:response.status,body:await response.json()};};
 assert.equal((await request('/health',undefined,false)).status,401);assert.equal((await request('/health')).body.runtime,'pi');assert.equal(h.requests.length,0);
 if(mode==='selected'){const selected=await request('/devices/select',{entity_id:'light.fixture',enabled:true,control:true,effects_reviewed:true});assert.equal(selected.status,200);}
 const input={request_id:'image-one',session_id:'household',prompt:'Turn on the authored fixture'};const result=await request('/ask',input);assert.equal(result.body.status,'completed',JSON.stringify(result));assert.equal(h.writes(),1);assert.equal(h.requests.length,2);
 assert.equal((await request('/ask',input)).body.replayed_response,true);assert.equal(h.requests.length,2);assert.equal(h.writes(),1);
 for(const sent of h.requests){const system=JSON.stringify(sent.messages.filter(m=>m.role==='system'));assert.match(system,/Augmentor Agent Home/);assert(!system.includes('<cwd>')&&!system.includes('/state/pi'));}
 await run('docker',['exec','--env','PORT='+address.port,name,'node','healthcheck.mjs']);
 const prompts=await request('/prompts');assert.equal(prompts.status,200);assert(Array.isArray(prompts.body.prompts));
 const audit=readFileSync(join(h.config.stateDir,'network.jsonl'),'utf8').trim().split('\n').map(JSON.parse);assert(audit.length>0&&audit.every(row=>row.allowed),'only selected authored endpoints and self-health are contacted');
 const data=JSON.parse((await run('docker',['exec',name,'node','--input-type=module','-e',`import {readFileSync} from 'node:fs';const lock=JSON.parse(readFileSync('/app/package-lock.json'));console.log(JSON.stringify({packages:Object.keys(lock.packages).length-1,dsh:Object.keys(lock.packages).filter(k=>k.includes('@deepseek-ai/')),node:process.version,gui:Object.keys(lock.packages).filter(k=>/Qt|xvfb/i.test(k))}));`])).stdout);
 assert.equal(data.node,'v24.19.0');assert.deepEqual(data.dsh,[]);assert.deepEqual(data.gui,[]);
 assert(readdirSync(join(h.config.stateDir,'pi/sessions')).some(p=>p.endsWith('.jsonl')));console.log(JSON.stringify({piHomeImageProof:{mode,node:data.node,lockedNpmPackages:data.packages,modelRequests:2,deviceMutations:1,cachedResponseNoReplay:true,unexpectedTcpDestinations:0,sharedPrompts:true,actualCmd:true,loopbackPort:address.port}}));
 }finally{await stop();}
});
