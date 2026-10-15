// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {createServer} from 'node:http';
import {once} from 'node:events';
import {mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {Server} from '@modelcontextprotocol/sdk/server/index.js';
import {StreamableHTTPServerTransport} from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import {ListToolsRequestSchema,CallToolRequestSchema} from '@modelcontextprotocol/sdk/types.js';
import {createRuntime} from '../../runtime.mjs';
import {Ledger} from '../../ledger.mjs';
import {READ_TOOL} from '../../../../adapters/dsh-home/index.mjs';

export const turnOn='mcp__homeassistant__intent__HassTurnOn';
export const args={name:'Test Lamp',domain:['input_boolean']};
export const tool=(name,arguments_,id)=>({role:'assistant',tool_calls:[{index:0,id,type:'function',function:{name,arguments:JSON.stringify(arguments_)}}]});
export const answer=text=>({role:'assistant',content:text});
export async function fixture(t,replies,{failWrite=false,writeResult,onWrite,requestTimeoutMs=10000,harness='dsh',haToken='fixture',modelKey='fixture',startRuntime=true,httpWriteStatus}={}) {
  const stateDir=mkdtempSync(join(tmpdir(),'home-runtime-')),ledger=new Ledger(join(stateDir,'actions.sqlite3'));
  let writes=0,requests=[];const peers=new Set();
  const mcp=createServer(async(req,res)=>{
    let parsed;
    if(httpWriteStatus&&req.method==='POST'){
      let raw='';for await(const chunk of req)raw+=chunk;parsed=JSON.parse(raw);
      if(parsed.method==='tools/call'&&parsed.params.name!=='homeassistant__GetLiveContext'){writes++;res.writeHead(httpWriteStatus,{'content-type':'text/plain'}).end('AUTHORED_LOST_HOME_ACK');return;}
    }
    const server=new Server({name:'fixture',version:'1'},{capabilities:{tools:{}}});
    server.setRequestHandler(ListToolsRequestSchema,async()=>({tools:['homeassistant__GetLiveContext','intent__HassTurnOn','intent__HassTurnOff','intent__HassLightSet','intent__HassUnlock'].map(name=>({name,description:name,inputSchema:{type:'object',properties:{name:{type:'string'},domain:{type:'array',items:{type:'string'}}}}}))}));
    server.setRequestHandler(CallToolRequestSchema,async r=>{
      if(r.params.name!=='homeassistant__GetLiveContext'){writes++;if(onWrite)await onWrite();if(failWrite)return {isError:true,content:[{type:'text',text:'Connection lost after dispatch'}]};}
      return {content:[{type:'text',text:JSON.stringify(r.params.name==='homeassistant__GetLiveContext'?{success:true,result:writes?'Test Lamp on':'Test Lamp off'}:writeResult??{response_type:'action_done',data:{success:[{name:'Test Lamp',type:'entity',id:'input_boolean.test_lamp'}],failed:[]}})}]};
    });
    const transport=new StreamableHTTPServerTransport({sessionIdGenerator:undefined});peers.add(server);
    res.on('close',()=>{void server.close();peers.delete(server);});
    await server.connect(transport);await transport.handleRequest(req,res,parsed);
  });
  mcp.listen(0,'127.0.0.1');await once(mcp,'listening');
  const model=createServer(async(req,res)=>{
    let raw='';for await(const c of req)raw+=c;const request=JSON.parse(raw);requests.push(request);
    const delta=await replies(requests.length,request);
    res.writeHead(200,{'content-type':'text/event-stream'});
    for(const [d,finish] of [[delta,null],[{},delta.tool_calls?'tool_calls':'stop']])res.write('data: '+JSON.stringify({id:'fixture',object:'chat.completion.chunk',model:'fixture',choices:[{index:0,delta:d,finish_reason:finish}]})+'\n\n');
    res.end('data: [DONE]\n\n');
  });model.listen(0,'127.0.0.1');await once(model,'listening');
  process.env.HOME_MODEL_KEY=modelKey;
  const config={stateDir,harness,model:'fixture',modelUrl:`http://127.0.0.1:${model.address().port}/v1`,mcpUrl:`http://127.0.0.1:${mcp.address().port}/api/mcp/assist`,haToken,requestTimeoutMs};
  let runtime;
  t.after(async()=>{await runtime?.close();for(const s of peers)await s.close();for(const s of [mcp,model]){s.closeAllConnections();await new Promise(r=>s.close(r));}ledger.close();rmSync(stateDir,{recursive:true,force:true});});
  if(startRuntime)runtime=await createRuntime(config,ledger);
  return {ledger,config,requests,writes:()=>writes,get runtime(){return runtime;},async restart(){await runtime.close();runtime=await createRuntime(config,ledger);}};
}
