// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Independently authored HTTP and credential callbacks; no live account/service.
import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import {once} from 'node:events';
import {resolve,join} from 'node:path';
import {pathToFileURL} from 'node:url';
import {McpClient} from '@earendil-works/pi-mcp';
import {createHash} from 'node:crypto';
const {managedMcpTransport,createManagedMcpTransport}=await import(pathToFileURL(join(resolve(process.env.AUGMENTOR_PI_TEST_ROOT||'.'),'dist/runtime/src/mcp-transport.js')));

async function fixture(t,handle,save){
 const calls=[],clients=[],timers=new Set();
 const server=http.createServer(async(req,res)=>{
  if(req.method!=='POST'){res.writeHead(req.method==='DELETE'?200:405).end();return;}
  let raw='';for await(const chunk of req)raw+=chunk;const frame=JSON.parse(raw);calls.push({frame,path:req.url,authorization:req.headers.authorization});
  const answer=result=>res.writeHead(200,{'content-type':'application/json','mcp-session-id':'authored-session'}).end(JSON.stringify({jsonrpc:'2.0',id:frame.id,result}));
  const later=(fn,ms)=>{const timer=setTimeout(()=>{timers.delete(timer);fn();},ms);timers.add(timer);};
  if(frame.method==='initialize'){answer({protocolVersion:frame.params.protocolVersion,capabilities:{tools:{}},serverInfo:{name:'Authored HTTP',version:'1'}});return;}
  if(frame.id===undefined){res.writeHead(202).end();return;}
  await handle({frame,req,res,answer,later});
 });server.listen(0,'127.0.0.1');await once(server,'listening');
 t.after(async()=>{for(const client of clients)await client.close();for(const timer of timers)clearTimeout(timer);server.closeAllConnections();await new Promise(done=>server.close(done));});
 const connect=async auth=>{const client=new McpClient({name:'Authored transport caller',version:'1',requestTimeoutMs:1500});clients.push(client);await client.connect((save?createManagedMcpTransport(save):managedMcpTransport)({name:'web',config:{url:'http://127.0.0.1:'+server.address().port+'/mcp'}},process.cwd(),auth));return client;};
 return {calls,connect};
}
const tools=calls=>calls.filter(row=>row.frame.method==='tools/call');

for(const status of [401,403,404,500])test('dispatched HTTP '+status+' never becomes an unobserved second tool POST',async t=>{
 let mutations=0;const f=await fixture(t,({res})=>{mutations++;res.writeHead(status).end('SYNTHETIC_PRIVATE_ERROR_BODY');});
 const client=await f.connect();await assert.rejects(client.callTool('write_record',{nonce:'one'}),error=>error.status===status&&error.message.includes('outcome unknown')&&!error.message.includes('SYNTHETIC_PRIVATE_ERROR_BODY'));
 assert.equal(mutations,1);assert.equal(tools(f.calls).length,1);
});

test('OAuth refresh callback can rotate credentials without replaying the dispatched tool',async t=>{
 let token='AUTHORED_OLD',refreshes=0,mutations=0;
 const f=await fixture(t,({frame,req,res,answer})=>{
  if(frame.method==='tools/list'){answer({tools:[]});return;}
  mutations++;if(req.headers.authorization==='Bearer AUTHORED_OLD')res.writeHead(401,{'www-authenticate':'Bearer resource_metadata="http://authored.invalid/metadata"'}).end();else answer({content:[{type:'text',text:'Authored new explicit operation'}]});
 });
 const auth={token:async()=>token,onUnauthorized:async context=>{refreshes++;assert.equal(context.token,'AUTHORED_OLD');assert.equal(context.response.status,401);token='AUTHORED_NEW';}};
 const client=await f.connect(auth);await assert.rejects(client.callTool('write_record',{nonce:'first'}),/outcome unknown/);assert.equal(refreshes,1);assert.equal(mutations,1);
 const next=await f.connect(auth);assert.equal((await next.callTool('write_record',{nonce:'explicit-next'})).content[0].text,'Authored new explicit operation');assert.equal(mutations,2);assert.equal(refreshes,1);
});

test('tool redirects cannot forward a mutation to a second endpoint',async t=>{
 let mutations=0;const f=await fixture(t,({req,res,answer})=>{mutations++;if(req.url==='/mcp')res.writeHead(307,{location:'/redirect-target'}).end();else answer({content:[]});});
 const client=await f.connect();await assert.rejects(client.callTool('write_record',{}),error=>error.status===307);assert.equal(mutations,1);assert.equal(tools(f.calls).length,1);assert.equal(f.calls.some(row=>row.path==='/redirect-target'),false);
});

test('a dropped acknowledgment retains one dispatch',async t=>{
 let mutations=0;const f=await fixture(t,({req})=>{mutations++;req.socket.destroy();});const client=await f.connect();await assert.rejects(client.callTool('write_record',{}));assert.equal(mutations,1);assert.equal(tools(f.calls).length,1);
});

test('an expired sibling preserves a concurrent SSE receipt before connection reset',async t=>{
 let releaseFailure;const ready=new Promise(done=>releaseFailure=done),f=await fixture(t,async({frame,res,answer,later})=>{
  if(frame.params.name==='expires'){await ready;res.writeHead(404).end();return;}
  res.writeHead(200,{'content-type':'text/event-stream'});res.write('event: message\ndata: '+JSON.stringify({jsonrpc:'2.0',method:'notifications/progress',params:{progressToken:'authored',progress:1}})+'\n\n');releaseFailure();
  later(()=>res.end('event: message\ndata: '+JSON.stringify({jsonrpc:'2.0',id:frame.id,result:{content:[{type:'text',text:'AUTHORED_CONCURRENT_RECEIPT'}]}})+'\n\n'),50);
 });
 const client=await f.connect(),first=client.callTool('expires',{}),second=client.callTool('succeeds',{});
 const [failed,succeeded]=await Promise.allSettled([first,second]);assert.equal(failed.status,'rejected');assert.equal(failed.reason.status,404);assert.equal(succeeded.status,'fulfilled');assert.equal(succeeded.value.content[0].text,'AUTHORED_CONCURRENT_RECEIPT');assert.equal(tools(f.calls).length,2);
});

test('configured env, escaping, command values and missing-secret errors preserve the public contract',()=>{
 const name='AUGMENTOR_MCP_AUTHORED_ENV',prior=process.env[name];process.env[name]='AUTHORED_VALUE';
 try{
  const transport=managedMcpTransport({name:'stdio',config:{command:'authored-not-started',env:{VALUE:'$'+name,ESCAPED:'$$VALUE $!literal',COMMAND:'!echo AUTHORED_COMMAND'}}},process.cwd());
  assert.equal(transport.options.env.VALUE,'AUTHORED_VALUE');assert.equal(transport.options.env.ESCAPED,'$VALUE !literal');assert.equal(transport.options.env.COMMAND,'AUTHORED_COMMAND');
  assert.throws(()=>managedMcpTransport({name:'stdio',config:{command:'not-started',env:{VALUE:'${AUGMENTOR_AUTHORED_MISSING_SECRET}'}}},process.cwd()),error=>error.message==='A managed MCP configuration value could not be resolved.');
 }finally{if(prior===undefined)delete process.env[name];else process.env[name]=prior;}
});

test('private originals retain bounded exact error bytes with explicit truncation and no request headers',async t=>{
 const originals=[],body=Buffer.concat([Buffer.from('AUTHORED_PRIVATE_ERROR '),Buffer.alloc(1024*1024,0xff)]);
 const f=await fixture(t,({res})=>res.writeHead(404,{'content-type':'application/octet-stream'}).end(body),original=>{originals.push(original);return true;});
 const client=await f.connect({token:async()=> 'SYNTHETIC_HEADER_SECRET'});await assert.rejects(client.callTool('write_record',{nonce:'authored'}),error=>error.status===404&&!error.message.includes('AUTHORED_PRIVATE_ERROR'));
 assert.equal(originals.length,1);const original=originals[0];assert.equal(original.body.coverage,'partial');assert.equal(original.body.retainedBytes,1024*1024);assert.deepEqual(Buffer.from(original.body.base64,'base64'),body.subarray(0,1024*1024));assert.equal(original.body.prefixSha256,createHash('sha256').update(body.subarray(0,1024*1024)).digest('hex'));assert.equal(JSON.stringify(original).includes('SYNTHETIC_HEADER_SECRET'),false);
});
