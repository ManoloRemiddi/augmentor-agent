// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {Ledger} from '../ledger.mjs';import {createRuntime} from '../runtime.mjs';import {mkdtempSync,rmSync} from 'node:fs';import {tmpdir} from 'node:os';import {join} from 'node:path';import {createServer} from 'node:http';import {once} from 'node:events';import {WebSocketServer} from 'ws';
import {Devices} from '../devices.mjs';
async function fixture(t){
 let writes=[],state='off',registry={entity_id:'light.fixture',id:'registry-id',unique_id:'hardware-id',platform:'fixture',config_entry_id:'integration-id'};
 const server=createServer(async(req,res)=>{res.setHeader('Content-Type','application/json');if(req.method==='POST'){let raw='';for await(const part of req)raw+=part;writes.push({path:req.url,body:JSON.parse(raw)});state='on';res.end('[]');}else{const item={entity_id:'light.fixture',state,attributes:{friendly_name:'Fixture'}};res.end(JSON.stringify(req.url==='/api/states'?[item]:item));}});
 const ws=new WebSocketServer({server,path:'/api/websocket'});ws.on('connection',socket=>{socket.send(JSON.stringify({type:'auth_required'}));socket.on('message',raw=>{const m=JSON.parse(raw);socket.send(JSON.stringify(m.type==='auth'?{type:'auth_ok'}:{id:m.id,type:'result',success:true,result:m.type.endsWith('/list')?[registry]:registry}));});});
 server.listen(0,'127.0.0.1');await once(server,'listening');const ledger=new Ledger(':memory:'),db=ledger.db;
 const devices=new Devices({mcpUrl:`http://127.0.0.1:${server.address().port}/api/mcp/assist`,haToken:'fixture'},db);
 t.after(()=>{for(const client of ws.clients)client.terminate();ws.close();server.closeAllConnections();server.close();db.close();});
 return {devices,writes,ledger,url:`http://127.0.0.1:${server.address().port}`,replace(){registry={...registry,id:'replacement',unique_id:'new-device'};}};
}
test('selection binds registry identity, excludes unselected devices and restricts exact service targets',async t=>{
 const h=await fixture(t);assert.equal((await h.devices.inventory())[0].selectable,true);
 await assert.rejects(h.devices.validate({entity_id:'light.fixture',action:'on'}),/not enabled/);
 await h.devices.select('light.fixture',true,true);
 await h.devices.validate({entity_id:'light.fixture',action:'on'});
 const result=await h.devices.execute({entity_id:'light.fixture',action:'on'});assert.equal(result.status,'completed');assert.equal(result.physical_verification,false);
 assert.deepEqual(h.writes,[{path:'/api/services/light/turn_on',body:{entity_id:'light.fixture'}}]);
 h.replace();await assert.rejects(h.devices.validate({entity_id:'light.fixture',action:'off'}),/identity changed/);assert.equal(h.writes.length,1);
});
test('read-only selection and forged domains, target lists and arbitrary service fields cannot dispatch',async t=>{
 const h=await fixture(t);await h.devices.select('light.fixture',true,false);
 for(const args of [{entity_id:'light.fixture',action:'on'},{entity_id:'lock.door',action:'on'},{entity_id:['light.fixture'],action:'on'},{entity_id:'light.fixture',action:'on',service:'unlock'},{entity_id:'light.fixture',action:'brightness',brightness_pct:101}])await assert.rejects(h.devices.validate(args));
 assert.equal(h.writes.length,0);assert.equal((await h.devices.list()).devices[0].state,'off');
});

test('selected-device runtime dispatches through DSH policy and cannot use Assist to bypass selection',async t=>{
 const h=await fixture(t),stateDir=mkdtempSync(join(tmpdir(),'home-selected-'));let count=0,requests=[];
 const model=createServer(async(req,res)=>{let raw='';for await(const part of req)raw+=part;requests.push(JSON.parse(raw));count++;
  const toolName=count===1?'home_set':count===3?'mcp__homeassistant__intent__HassTurnOn':null;
  const delta=toolName?{role:'assistant',tool_calls:[{index:0,id:'fixture-'+count,type:'function',function:{name:toolName,arguments:JSON.stringify({entity_id:'light.fixture',action:'on'})}}]}:{role:'assistant',content:'Fixture result.'};
  res.writeHead(200,{'Content-Type':'text/event-stream'});for(const [d,reason] of [[delta,null],[{},toolName?'tool_calls':'stop']])res.write('data: '+JSON.stringify({id:'fixture',object:'chat.completion.chunk',model:'fixture',choices:[{index:0,delta:d,finish_reason:reason}]})+'\n\n');res.end('data: [DONE]\n\n');
 });model.listen(0,'127.0.0.1');await once(model,'listening');process.env.HOME_MODEL_KEY='fixture';
 const runtime=await createRuntime({stateDir,model:'fixture',modelUrl:`http://127.0.0.1:${model.address().port}/v1`,mcpUrl:h.url+'/api/mcp/assist',haToken:'fixture',deviceMode:'selected'},h.ledger);
 t.after(async()=>{await runtime.close();model.closeAllConnections();model.close();rmSync(stateDir,{recursive:true,force:true});});
 await runtime.devices.select('light.fixture',true,true);
 const result=await runtime.ask('one','home','Turn on fixture');assert.equal(h.writes.length,1);assert.equal(result.tool_calls[0].status,'completed');
 assert.deepEqual(requests[0].tools.map(t=>t.function.name).sort(),['home_devices','home_set']);
 await runtime.ask('two','home','Try an Assist intent');assert.equal(h.writes.length,1);
});
