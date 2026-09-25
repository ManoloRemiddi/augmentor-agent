// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {once} from 'node:events';
import {mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {Server} from '@modelcontextprotocol/sdk/server/index.js';
import {StreamableHTTPServerTransport} from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import {ListToolsRequestSchema,CallToolRequestSchema} from '@modelcontextprotocol/sdk/types.js';
import {createRuntime} from '../runtime.mjs';
import {Ledger} from '../ledger.mjs';
import {READ_TOOL} from '../../../adapters/dsh-home/index.mjs';

const turnOn='mcp__homeassistant__intent__HassTurnOn';
const args={name:'Test Lamp',domain:['input_boolean']};
const tool=(name,arguments_,id)=>({role:'assistant',tool_calls:[{index:0,id,type:'function',function:{name,arguments:JSON.stringify(arguments_)}}]});
const answer=text=>({role:'assistant',content:text});
async function fixture(t,replies,{failWrite=false,writeResult,writeDelayMs=0,requestTimeoutMs=10000}={}) {
  const stateDir=mkdtempSync(join(tmpdir(),'home-runtime-')),ledger=new Ledger(join(stateDir,'actions.sqlite3'));
  let writes=0,requests=[];const peers=new Set();
  const mcp=createServer(async(req,res)=>{
    const server=new Server({name:'fixture',version:'1'},{capabilities:{tools:{}}});
    server.setRequestHandler(ListToolsRequestSchema,async()=>({tools:['homeassistant__GetLiveContext','intent__HassTurnOn','intent__HassTurnOff','intent__HassLightSet','intent__HassUnlock'].map(name=>({name,description:name,inputSchema:{type:'object',properties:{name:{type:'string'},domain:{type:'array',items:{type:'string'}}}}}))}));
    server.setRequestHandler(CallToolRequestSchema,async r=>{
      if(r.params.name!=='homeassistant__GetLiveContext'){writes++;if(writeDelayMs)await new Promise(r=>setTimeout(r,writeDelayMs));if(failWrite)return {isError:true,content:[{type:'text',text:'Connection lost after dispatch'}]};}
      return {content:[{type:'text',text:JSON.stringify(r.params.name==='homeassistant__GetLiveContext'?{success:true,result:writes?'Test Lamp on':'Test Lamp off'}:writeResult??{response_type:'action_done',data:{success:[{name:'Test Lamp',type:'entity',id:'input_boolean.test_lamp'}],failed:[]}})}]};
    });
    const transport=new StreamableHTTPServerTransport({sessionIdGenerator:undefined});peers.add(server);
    res.on('close',()=>{void server.close();peers.delete(server);});
    await server.connect(transport);await transport.handleRequest(req,res);
  });
  mcp.listen(0,'127.0.0.1');await once(mcp,'listening');
  const model=createServer(async(req,res)=>{
    let raw='';for await(const c of req)raw+=c;const request=JSON.parse(raw);requests.push(request);
    const delta=await replies(requests.length,request);
    res.writeHead(200,{'content-type':'text/event-stream'});
    for(const [d,finish] of [[delta,null],[{},delta.tool_calls?'tool_calls':'stop']])res.write('data: '+JSON.stringify({id:'fixture',object:'chat.completion.chunk',model:'fixture',choices:[{index:0,delta:d,finish_reason:finish}]})+'\n\n');
    res.end('data: [DONE]\n\n');
  });model.listen(0,'127.0.0.1');await once(model,'listening');
  process.env.HOME_MODEL_KEY='fixture';
  const config={stateDir,model:'fixture',modelUrl:`http://127.0.0.1:${model.address().port}/v1`,mcpUrl:`http://127.0.0.1:${mcp.address().port}/api/mcp/assist`,haToken:'fixture',requestTimeoutMs};
  let runtime;
  t.after(async()=>{await runtime?.close();for(const s of peers)await s.close();for(const s of [mcp,model]){s.closeAllConnections();await new Promise(r=>s.close(r));}ledger.close();rmSync(stateDir,{recursive:true,force:true});});
  runtime=await createRuntime(config,ledger);
  return {ledger,config,requests,writes:()=>writes,get runtime(){return runtime;},async restart(){await runtime.close();runtime=await createRuntime(config,ledger);}};
}

test('actual DSH + MCP discovers tools, executes once and resumes persisted context',async t=>{
  const h=await fixture(t,n=>[tool(READ_TOOL,{},'read'),tool(turnOn,args,'write'),answer('Lamp switched on.'),answer('You asked me to turn on the test lamp.')][n-1]);
  const result=await h.runtime.ask('one','household','Turn on the test lamp');
  assert.equal(result.status,'completed');assert.equal(h.writes(),1);
  assert.ok(result.tool_calls.some(x=>x.status==='completed'&&x.action_id));
  assert.ok(h.requests[0].tools.every(x=>!x.function.name.includes('Unlock')));
  await h.restart();
  await h.runtime.ask('two','household','What did I ask you to do?');
  assert.match(JSON.stringify(h.requests.at(-1).messages),/Turn on the test lamp/);
  assert.equal(h.writes(),1);
});

test('uncertain MCP mutation blocks same-request retry and subsequent requests',async t=>{
  const h=await fixture(t,n=>n===1?tool(turnOn,args,'first'):n===2?tool(turnOn,args,'retry'):n===4?tool(turnOn,args,'later'):answer('Action outcome is unknown.'),{failWrite:true});
  assert.equal((await h.runtime.ask('one','household','Turn on test')).status,'incomplete');
  await h.runtime.ask('two','household','Try again');
  assert.equal(h.writes(),1);assert.equal(h.ledger.pending()[0].status,'unknown');
});

test('unadvertised administrative tools and unsafe domains are denied before MCP',async t=>{
  const h=await fixture(t,n=>[tool('mcp__homeassistant__intent__HassUnlock',{name:'Door',domain:['lock']},'bad'),tool(turnOn,{name:'Door',domain:['lock']},'bad-domain'),answer('Not permitted.')][n-1]);
  await h.runtime.ask('one','household','Unlock the door');assert.equal(h.writes(),0);
});

 test('deadline cancellation after dispatch latches uncertainty and does not replay',async t=>{
  const h=await fixture(t,n=>n===1?tool(turnOn,args,'slow'):answer('Stopped.'),{writeDelayMs:250,requestTimeoutMs:100});
  const start=Date.now();
  const result=await h.runtime.ask('deadline','home','Turn on test');
  assert.equal(result.status,'incomplete');assert.ok(Date.now()-start<2000);
  assert.equal(h.writes(),1);assert.equal(h.ledger.pending()[0].status,'unknown');
});

 test('provider failure returns incomplete without a device action',async t=>{
  const h=await fixture(t,()=>({role:'assistant',content:''}));
  const result=await h.runtime.ask('failure','home','Read test lamp');
  assert.equal(result.status,'incomplete');assert.equal(h.writes(),0);
});

 test('partial HA intent failure inside successful MCP envelope blocks further changes',async t=>{
  const h=await fixture(t,n=>n===1?tool(turnOn,args,'partial'):n===2?tool(turnOn,{name:'Another Lamp',domain:['light']},'different'):answer('Partial failure; inspect state.'),{
    writeResult:{response_type:'action_done',data:{success:[{id:'light.one'}],failed:[{id:'light.two'}]}}
  });
  const result=await h.runtime.ask('partial','home','Turn on lights');
  assert.equal(result.status,'incomplete');assert.equal(h.writes(),1);
  assert.equal(h.ledger.pending()[0].status,'unknown');
 });

 test('read-only authority denies a model-requested write before MCP dispatch',async t=>{
  const h=await fixture(t,n=>n===1?tool(turnOn,args,'forbidden'):answer('Read-only access.'));
  await h.runtime.ask('readonly','viewer','Turn on test',{readOnly:true});
  assert.equal(h.writes(),0);assert.equal(h.ledger.pending().length,0);
 });

 test('cancelling while the session is being created prevents the first model and device call',async t=>{
  const h=await fixture(t,n=>n===1?tool(turnOn,args,'must-not-run'):answer('Done'));
  const pending=h.runtime.ask('startup','home','Turn on test');h.runtime.cancel();
  const result=await pending;assert.equal(result.status,'incomplete');assert.equal(h.requests.length,0);assert.equal(h.writes(),0);
 });
