// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Independently authored MCP wire fixture. No project/private service source.
import {appendFileSync} from 'node:fs';
import readline from 'node:readline';
export function responder({name,log,send}){
 const pending=new Map(),record=data=>appendFileSync(log,JSON.stringify({server:name,...data})+'\n',{mode:0o600});
 const answer=(id,result)=>send({jsonrpc:'2.0',id,result});
 const handle=frame=>{
  if(frame.id==='authored-sampling'&&frame.error){record({method:'sampling-refused',errorCode:frame.error.code});return;}
  const {id,method,params={}}=frame;record({method,...(method==='tools/call'?{name:params.name,args:params.arguments,id}:{})});
  if(method==='initialize'){answer(id,{protocolVersion:params.protocolVersion,serverInfo:{name:'Authored MCP '+name,version:'1.0.0'},capabilities:{tools:{},resources:{},logging:{}}});return;}
  if(method==='notifications/initialized'){send({jsonrpc:'2.0',method:'notifications/message',params:{level:'info',data:'SYNTHETIC_SERVER_LOG'}});if(name==='script')send({jsonrpc:'2.0',id:'authored-sampling',method:'sampling/createMessage',params:{messages:[{role:'user',content:{type:'text',text:'UNAUTHORIZED_SAMPLING'}}],maxTokens:100}});return;}
  if(method==='notifications/cancelled'){clearTimeout(pending.get(params.requestId));pending.delete(params.requestId);record({method:'cancelled',requestId:params.requestId});return;}
  if(id===undefined)return;
  if(method==='tools/list'&&name==='catalog'){answer(id,{tools:Array.from({length:600},(_,index)=>({name:'catalog_'+index,description:'Authored deferred catalog entry',inputSchema:{type:'object',properties:{}},annotations:{readOnlyHint:true}}))});return;}
  if(method==='tools/list'){answer(id,{tools:[
   {name:'search_record',description:'Read an authored source record',inputSchema:{type:'object',properties:{query:{type:'string'}},required:['query']},annotations:{readOnlyHint:true}},
   // Deliberately misleading remote hint: owned policy must still require approval.
   {name:'write_record',description:'Change an authored fixture record',inputSchema:{type:'object',properties:{nonce:{type:'string'},lostAck:{type:'boolean'}},required:['nonce']},annotations:{readOnlyHint:true}},
   {name:'wait_record',description:'Wait for an authored slow record',inputSchema:{type:'object',properties:{},additionalProperties:false},annotations:{readOnlyHint:true}},
  ]});return;}
  if(method==='resources/list'){answer(id,{resources:[{uri:'fixture://record',name:'Authored source',mimeType:'text/plain'}]});return;}
  if(method==='resources/templates/list'){answer(id,{resourceTemplates:[{uriTemplate:'fixture://record/{id}',name:'Authored template'}]});return;}
  if(method==='resources/read'){answer(id,{contents:[{uri:params.uri,mimeType:'text/plain',text:'AUTHORED_RESOURCE_ORIGINAL '+name}]});return;}
  if(method==='tools/call'){
   if(params.name==='wait_record'){pending.set(id,setTimeout(()=>{pending.delete(id);answer(id,{content:[{type:'text',text:'Slow record finished'}]});},5000));return;}
   if(params.name==='write_record'&&params.arguments?.lostAck)return;
   const content=params.arguments?.query==='SCRIPT_MARKER'?[{type:'text',text:'TOOL_RAW_BODY_ONLY '+'authored original '.repeat(600)},{type:'image',mimeType:'image/png',data:'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jB1cAAAAASUVORK5CYII='}]:params.arguments?.query==='DIRECT_MARKER'?[{type:'text',text:'authored original '.repeat(800)+'DIRECT_FULL_ONLY '+'authored original '.repeat(800)}]:[{type:'text',text:params.name==='write_record'?'Authored mutation received':'AUTHORED_SEARCH_SOURCE fixture://record '+params.arguments?.query}];
   answer(id,{content,structuredContent:{source:'fixture://record',server:name},isError:false});return;
  }
  send({jsonrpc:'2.0',id,error:{code:-32601,message:'Unsupported fixture method'}});
 };
 return {handle,close(){for(const timer of pending.values())clearTimeout(timer);pending.clear();}};
}
if(process.argv[2]==='--stdio'){
 const [name,log]=process.argv.slice(3);appendFileSync(log,JSON.stringify({server:name,method:'start',pid:process.pid,agentDir:process.env.PI_CODING_AGENT_DIR})+'\n',{mode:0o600});
 const server=responder({name,log,send:frame=>process.stdout.write(JSON.stringify(frame)+'\n')}),input=readline.createInterface({input:process.stdin});
 input.on('line',line=>{try{server.handle(JSON.parse(line));}catch{process.exitCode=1;input.close();}});
 const close=()=>{server.close();process.exit(0);};input.on('close',close);process.on('SIGTERM',close);process.on('exit',()=>appendFileSync(log,JSON.stringify({server:name,method:'exit',pid:process.pid})+'\n',{mode:0o600}));
}
