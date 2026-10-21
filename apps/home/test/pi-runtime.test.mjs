// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,readdirSync,writeFileSync} from 'node:fs';
import {join} from 'node:path';
import {registerHooks} from 'node:module';
const moduleGuard=registerHooks({resolve(specifier,context,next){if(specifier.startsWith('@deepseek-ai/'))throw Error('Pi Home attempted to load a DSH package: '+specifier);return next(specifier,context);}});
import {fixture,turnOn,args,tool,answer} from './fixtures/runtime.mjs';
import {READ_TOOL} from '../../../adapters/dsh-home/index.mjs';

test('actual Pi Home uses the approved MCP tools once and cold-resumes its native household context',{timeout:20000},async t=>{
 const h=await fixture(t,n=>[tool(READ_TOOL,{},'read'),tool(turnOn,args,'write'),tool(READ_TOOL,{},'verify'),answer('Fixture integration state is on; physical verification remains unavailable.'),answer('You asked to turn on the fixture.')][n-1],{harness:'pi'});
 assert.equal(h.runtime.harness,'pi');assert.equal(h.requests.length,0);
 const result=await h.runtime.ask('one','household','Turn on the test lamp');
 assert.equal(result.status,'completed',JSON.stringify(result));assert.equal(h.writes(),1);
 assert.deepEqual(result.tool_calls.map(x=>x.status),['completed','completed','completed']);
 assert.deepEqual(h.requests[0].tools.map(x=>x.function.name).sort(),[READ_TOOL,turnOn,'mcp__homeassistant__intent__HassTurnOff','mcp__homeassistant__intent__HassLightSet'].sort());
 const files=readdirSync(join(h.config.stateDir,'pi/sessions'));assert.equal(files.length,1);const file=join(h.config.stateDir,'pi/sessions',files[0]),original=readFileSync(file);
 await h.restart();assert.equal(h.requests.length,4);assert.equal(h.writes(),1);
 assert.equal((await h.runtime.ask('two','household','What did I ask?')).status,'completed');
 assert.match(JSON.stringify(h.requests.at(-1).messages),/Turn on the test lamp/);assert.equal(h.writes(),1);
 assert.deepEqual(readFileSync(file).subarray(0,original.length),original);
 for(const request of h.requests){const system=request.messages.filter(m=>m.role==='system');assert.match(JSON.stringify(system),/Augmentor Agent Home/);assert(!JSON.stringify(system).includes(h.config.stateDir));assert(!JSON.stringify(system).includes('<cwd>'));}
});

test('Pi Home refuses unconverted DSH household history without model or device work',{timeout:20000},async t=>{
 const h=await fixture(t,()=>answer('Must not run'),{harness:'pi'});
 const {createHash}=await import('node:crypto');const marker=join(h.config.stateDir,'home-'+createHash('sha256').update('legacy').digest('hex')+'.json');writeFileSync(marker,'{"session":"authored-legacy"}',{mode:0o600});
 const result=await h.runtime.ask('legacy-request','legacy','Continue');assert.equal(result.status,'incomplete');assert.match(result.reason,/DSH history/);assert.equal(h.requests.length,0);assert.equal(h.writes(),0);assert.equal(readFileSync(marker,'utf8'),'{"session":"authored-legacy"}');
});

for(const [label,options] of [['failed acknowledgement',{failWrite:true}],['partial intent',{writeResult:{response_type:'action_done',data:{success:[{id:'one'}],failed:[{id:'two'}]}}}]])test('Pi Home retains uncertainty and blocks another mutation after '+label,{timeout:20000},async t=>{
 const h=await fixture(t,n=>n===1?tool(turnOn,args,'first'):n===2?tool(turnOn,args,'retry'):n===4?tool(turnOn,{...args,name:'Other'},'later'):answer('Inspect the unknown action.'),{harness:'pi',...options});
 assert.equal((await h.runtime.ask('one','household','Turn on fixture')).status,'incomplete');
 await h.runtime.ask('two','household','Try the other device');assert.equal(h.writes(),1);assert.equal(h.ledger.pending()[0].status,'unknown');
});
test('Pi Home refuses read-only writes and unadvertised or unsafe-domain calls before HA',{timeout:20000},async t=>{
 const h=await fixture(t,n=>[tool(turnOn,args,'viewer'),answer('Read only'),tool('mcp__homeassistant__intent__HassUnlock',{name:'Door',domain:['lock']},'unknown'),tool(turnOn,{name:'Door',domain:['lock']},'domain'),answer('Not permitted')][n-1],{harness:'pi'});
 const first=await h.runtime.ask('viewer','viewer','Turn on fixture',{readOnly:true});assert.equal(first.tool_calls[0].status,'denied');
 await h.runtime.ask('owner','owner','Unlock door');assert.equal(h.writes(),0);assert.equal(h.ledger.pending().length,0);
});
test('Pi Home cancellation during session creation sends no model request',{timeout:20000},async t=>{
 const h=await fixture(t,()=>answer('Must not run'),{harness:'pi'}),pending=h.runtime.ask('cancel','household','Act');h.runtime.cancel();
 assert.equal((await pending).status,'incomplete');assert.equal(h.requests.length,0);assert.equal(h.writes(),0);
});
test('Pi Home deadline after real dispatch retains unknown outcome without replay',{timeout:20000},async t=>{
 const dispatched=Promise.withResolvers(),release=Promise.withResolvers();t.after(()=>release.resolve());let deadline;const native=setTimeout;
 t.mock.method(globalThis,'setTimeout',(fn,ms,...args)=>{if(ms===30001)deadline=fn;return native(fn,ms,...args);});
 const h=await fixture(t,n=>n<=2?tool(turnOn,args,'write-'+n):answer('Inspect the action'),{harness:'pi',requestTimeoutMs:30001,onWrite:()=>{dispatched.resolve();return release.promise;}});
 const pending=h.runtime.ask('deadline','household','Turn on fixture');await dispatched.promise;assert.equal(typeof deadline,'function');deadline();
 const result=await pending;assert.equal(result.status,'incomplete');assert.equal(result.reason,'Request deadline exceeded');assert.equal(h.writes(),1);assert.equal(h.ledger.pending()[0].status,'unknown');release.resolve();
 await h.runtime.ask('later','household','Try again');assert.equal(h.writes(),1);
});
test('Pi Home request/tool bounds stop actual production without further provider or device calls',{timeout:20000},async t=>{
 const h=await fixture(t,()=>tool(READ_TOOL,{},crypto.randomUUID()),{harness:'pi'}),result=await h.runtime.ask('bound','household','Read repeatedly');
 assert.equal(result.status,'incomplete');assert.equal(result.reason,'Step budget exhausted');assert.equal(h.requests.length,10);assert.equal(h.writes(),0);
});
test('Pi Home exact native scope rejects a foreign household file and keeps model selection explicit',{timeout:20000},async t=>{
 const h=await fixture(t,()=>answer('Authored answer'),{harness:'pi'});await h.runtime.ask('one','one','First household');await h.runtime.ask('two','two','Second household');
 h.config.model='fixture-new';await h.restart();await h.runtime.ask('model','one','Same context, explicitly changed model');assert.equal(h.requests.at(-1).model,'fixture-new');assert.match(JSON.stringify(h.requests.at(-1).messages),/First household/);
 await h.runtime.close();const {createHash}=await import('node:crypto'),index=s=>join(h.config.stateDir,'pi/index','home-'+createHash('sha256').update(s).digest('hex')+'.json');
 const first=JSON.parse(readFileSync(index('one'))),second=JSON.parse(readFileSync(index('two')));writeFileSync(index('one'),JSON.stringify({...first,file:second.file}),{mode:0o600});await h.restart();const before=h.requests.length;
 assert.equal((await h.runtime.ask('foreign','one','Do not expose another household')).status,'incomplete');assert.equal(h.requests.length,before);assert.equal(h.writes(),0);
});
test('Pi Home core opt-outs defeat inherited reporting without storing model or HA tokens',{timeout:20000},async t=>{
 const before=process.env.PI_TELEMETRY;process.env.PI_TELEMETRY='true';t.after(()=>{if(before===undefined)delete process.env.PI_TELEMETRY;else process.env.PI_TELEMETRY=before;});
 const modelKey='AUTHORED_HOME_MODEL_TOKEN',haToken='AUTHORED_HOME_HA_TOKEN',h=await fixture(t,()=>answer('Private reply'),{harness:'pi',modelKey,haToken});await h.runtime.ask('private','household','Explicit privacy check');assert.equal(process.env.PI_TELEMETRY,'0');assert.equal(h.requests.length,1);
 function files(root){return readdirSync(root,{withFileTypes:true}).flatMap(p=>p.isDirectory()?files(join(root,p.name)):[join(root,p.name)]);}
 for(const p of files(join(h.config.stateDir,'pi'))){const bytes=readFileSync(p).toString();assert(!bytes.includes(modelKey)&&!bytes.includes(haToken),'tokens remain out of SDK native/cache files');}
});

async function selectedFixture(t,replies){
 const {fixture:devicesFixture}=await import('./fixtures/devices.mjs'),h=await devicesFixture(t);
 const {mkdtempSync,rmSync}=await import('node:fs'),{tmpdir}=await import('node:os'),{createServer}=await import('node:http'),{once}=await import('node:events'),{createRuntime}=await import('../runtime.mjs');
 const root=mkdtempSync(join(tmpdir(),'home-pi-selected-')),requests=[];
 const provider=createServer(async(req,res)=>{let text='';for await(const chunk of req)text+=chunk;requests.push(JSON.parse(text));const delta=replies(requests.length);res.writeHead(200,{'content-type':'text/event-stream'});res.end('data: '+JSON.stringify({id:'selected-pi',object:'chat.completion.chunk',choices:[{index:0,delta,finish_reason:delta.tool_calls?'tool_calls':'stop'}]})+'\n\ndata: [DONE]\n\n');});provider.listen(0,'127.0.0.1');await once(provider,'listening');process.env.HOME_MODEL_KEY='fixture';
 const runtime=await createRuntime({harness:'pi',deviceMode:'selected',stateDir:root,model:'fixture',modelUrl:'http://127.0.0.1:'+provider.address().port+'/v1',mcpUrl:h.url+'/api/mcp/assist',haToken:'fixture'},h.ledger);
 t.after(async()=>{await runtime.close();provider.closeAllConnections();await new Promise(done=>provider.close(done));rmSync(root,{recursive:true,force:true});});
 return {...h,runtime,requests};
}
test('Pi Home selected devices use the same registry identity, exact REST target and observed state',{timeout:20000},async t=>{
 const operation={entity_id:'light.fixture',action:'on'},h=await selectedFixture(t,n=>[tool('home_devices',{},'inventory'),tool('home_set',operation,'change'),tool('home_devices',{},'observe'),answer('Integration state observed; no physical verification'),tool('home_set',operation,'viewer'),answer('Read only')][n-1]);
 await h.runtime.devices.select('light.fixture',true,true);const result=await h.runtime.ask('selected','household','Turn on fixture');assert.equal(result.status,'completed',JSON.stringify(result));assert.deepEqual(h.writes,[{path:'/api/services/light/turn_on',body:{entity_id:'light.fixture'}}]);
 assert.deepEqual(h.requests[0].tools.map(x=>x.function.name).sort(),['home_devices','home_set']);assert.equal(result.tool_calls[1].status,'completed');
 const denied=await h.runtime.ask('viewer','viewer','Turn on fixture',{readOnly:true});assert.equal(denied.tool_calls[0].status,'denied');assert.equal(h.writes.length,1);
});
test('Pi Home refuses replaced selected identities before a REST write or action reservation',{timeout:20000},async t=>{
 const h=await selectedFixture(t,n=>n===1?tool('home_set',{entity_id:'light.fixture',action:'on'},'replace'):answer('Owner must review identity'));await h.runtime.devices.select('light.fixture',true,true);h.replace();
 const result=await h.runtime.ask('replace','household','Turn on fixture');assert.equal(result.tool_calls[0].status,'denied');assert.equal(h.writes.length,0);assert.equal(h.ledger.pending().length,0);
});
test('Pi Home does not treat a REST acknowledgement without matching state as completed',{timeout:20000},async t=>{
 const h=await selectedFixture(t,n=>n===1?tool('home_set',{entity_id:'light.fixture',action:'off'},'first'):n===2?tool('home_set',{entity_id:'light.fixture',action:'on'},'retry'):answer('Observed state does not confirm the request'));await h.runtime.devices.select('light.fixture',true,true);
 const result=await h.runtime.ask('mismatch','household','Switch off fixture');assert.equal(result.status,'incomplete');assert.equal(result.tool_calls[0].status,'unknown');assert.equal(h.writes.length,1);assert.equal(h.ledger.pending()[0].status,'unknown');
});
test('Pi Home preserves authenticated HTTP request identity, cached receipts and truthful health',{timeout:20000},async t=>{
 const h=await fixture(t,n=>n===1?tool(turnOn,args,'write'):answer('Fixture action acknowledged'),{harness:'pi'}),{httpService}=await import('../server.mjs'),{once}=await import('node:events');const token='authored-private-home-operator-token';
 const app=httpService({...h.config,token},h.ledger,h.runtime,{readiness:async()=>true});app.server.listen(0,'127.0.0.1');await once(app.server,'listening');t.after(()=>app.close());
 const request=async(path,body,auth=true)=>{const res=await fetch('http://127.0.0.1:'+app.server.address().port+path,{method:body===undefined?'GET':'POST',headers:{'content-type':'application/json',...(auth?{authorization:'Bearer '+token}:{})},...(body===undefined?{}:{body:JSON.stringify(body)})});return {status:res.status,body:await res.json()};};
 assert.equal((await request('/health',undefined,false)).status,401);assert.equal((await request('/health')).body.runtime,'pi');
 const input={request_id:'one',session_id:'household',prompt:'Turn on fixture'};assert.equal((await request('/ask',input)).body.status,'completed');const count=h.requests.length;
 assert.equal((await request('/ask',input)).body.replayed_response,true);assert.equal(h.requests.length,count);assert.equal(h.writes(),1);
 assert.equal((await request('/ask',{...input,prompt:'Different intent'})).status,409);assert.equal(h.writes(),1);
});

test('Pi Home preserves slash text as user input instead of executing SDK manager commands',{timeout:20000},async t=>{
 const h=await fixture(t,()=>answer('Authored literal response'),{harness:'pi'});await h.runtime.ask('literal','household','/mcp disable homeassistant',{readOnly:true});assert.equal(h.requests.length,1);assert.match(JSON.stringify(h.requests[0].messages),/\/mcp disable homeassistant/);assert.equal(h.writes(),0);assert(!readdirSync(join(h.config.stateDir,'pi/agent')).includes('mcp.json'));
});
test('Pi Home allows at most twelve tool actions from one actual provider batch',{timeout:20000},async t=>{
 const h=await fixture(t,n=>n===1?{role:'assistant',tool_calls:Array.from({length:16},(_,i)=>({index:i,id:'batch-'+i,type:'function',function:{name:turnOn,arguments:JSON.stringify({...args,name:'Authored lamp '+i})}}))}:answer('Inspect the bounded receipts'),{harness:'pi'});
 const result=await h.runtime.ask('batch','household','Authored bounded batch');assert.equal(h.requests.length,2);assert.equal(h.writes(),12);assert.equal(result.tool_calls.filter(x=>x.status==='denied').length,4);assert.equal(result.tool_calls.filter(x=>x.status==='completed').length,12);
});
test('Pi Home actual HTTP 404 after a mutation cannot trigger SDK or model replay',{timeout:20000},async t=>{
 const h=await fixture(t,n=>n<=2?tool(turnOn,args,'lost-'+n):answer('Outcome unknown; inspect first'),{harness:'pi',httpWriteStatus:404});const result=await h.runtime.ask('lost','household','Turn on fixture');assert.equal(result.status,'incomplete');assert.equal(h.writes(),1);assert.equal(h.ledger.pending()[0].status,'unknown');
 const native=readdirSync(join(h.config.stateDir,'pi/sessions')).map(p=>readFileSync(join(h.config.stateDir,'pi/sessions',p),'utf8')).join('');assert(native.includes('AUTHORED_LOST_HOME_ACK'));assert(!JSON.stringify(h.requests).includes('AUTHORED_LOST_HOME_ACK'),'private original HTTP body stays out of model input');
});
