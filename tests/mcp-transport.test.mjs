// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Independently authored HTTP and credential callbacks; no live account/service.
import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import {once} from 'node:events';
import {resolve,join} from 'node:path';
import {pathToFileURL} from 'node:url';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const root=resolve(process.env.AUGMENTOR_PI_TEST_ROOT||'.'),mcpRoot=join(root,'node_modules/@earendil-works/pi-mcp');
// Use the selected artifact's declared public ESM exports, including class identity.
const exports=JSON.parse(await readFile(join(mcpRoot,'package.json'),'utf8')).exports;
const {McpClient,McpAbortError,McpTimeoutError,McpConnectionClosedError}=await import(pathToFileURL(join(mcpRoot,exports['.'].import)));
const {McpOAuthAuthorizationRequiredError}=await import(pathToFileURL(join(mcpRoot,exports['./oauth'].import)));
const {managedMcpTransport,createManagedMcpTransport}=await import(pathToFileURL(join(root,'dist/runtime/src/mcp-transport.js')));

async function fixture(t,handle,save,options={}){
 const calls=[],clients=[],timers=new Set();
 const server=http.createServer(async(req,res)=>{
  if(req.method!=='POST'){res.writeHead(req.method==='DELETE'?200:405).end();return;}
  let raw='';for await(const chunk of req)raw+=chunk;const frame=JSON.parse(raw);calls.push({frame,path:req.url,authorization:req.headers.authorization});
  const answer=result=>res.writeHead(200,{'content-type':'application/json','mcp-session-id':'authored-session'}).end(JSON.stringify({jsonrpc:'2.0',id:frame.id,result}));
  const later=(fn,ms)=>{const timer=setTimeout(()=>{timers.delete(timer);fn();},ms);timers.add(timer);};
  if(frame.method==='initialize'){answer({protocolVersion:frame.params.protocolVersion,capabilities:{tools:{}},serverInfo:{name:'Authored HTTP',version:'1'}});return;}
  if(frame.id===undefined){if(options.control)await options.control({frame,res});else res.writeHead(202).end();return;}
  await handle({frame,req,res,answer,later});
 });server.listen(0,'127.0.0.1');await once(server,'listening');
 t.after(async()=>{for(const client of clients)await client.close();for(const timer of timers)clearTimeout(timer);server.closeAllConnections();await new Promise(done=>server.close(done));});
 const connect=async auth=>{const client=new McpClient({name:'Authored transport caller',version:'1',requestTimeoutMs:1500});clients.push(client);await client.connect(createManagedMcpTransport(save,options.authorizationObserved)({name:'web',config:{url:'http://127.0.0.1:'+server.address().port+'/mcp'}},process.cwd(),auth));return client;};
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

test('refresh exceptions expose an unknown HTTP outcome without leaking the provider error',async t=>{
 let refreshes=0;const originals=[],authorization=[],f=await fixture(t,({res})=>res.writeHead(401).end('AUTHORED_BODY'),original=>{originals.push(original);return true;},{authorizationObserved:event=>{authorization.push(event);return true;},control:({frame,res})=>frame.grant_type?res.writeHead(401).end('AUTHORED_PRIVATE_REFRESH_BODY'):res.writeHead(202).end()});
 const client=await f.connect({token:async()=>undefined,onUnauthorized:async context=>{refreshes++;const response=await context.fetch(context.serverUrl,{method:'POST',body:JSON.stringify({grant_type:'authored-refresh'})});assert.equal(response.status,401);await response.body?.cancel();throw Error('SYNTHETIC_REFRESH_SECRET');}});
 await assert.rejects(client.callTool('write_record',{}),error=>error.status===401&&error.message.includes('outcome unknown')&&error.message.includes('Authorization handling failed')&&!JSON.stringify({message:error.message,body:error.body}).includes('SYNTHETIC_REFRESH_SECRET'));
 assert.equal(refreshes,1);assert.equal(tools(f.calls).length,1);assert.equal(originals[0].body.text,'AUTHORED_BODY');
 assert.deepEqual(authorization.map(row=>row.state),['challenge-observed','refresh-failed'],'a non-RPC refresh response at the same URL is not MCP response evidence');assert(!JSON.stringify(authorization).includes('AUTHORED_PRIVATE_REFRESH_BODY'));
});

for(const mode of ['sibling-cancel','failed-cancel','sibling-timeout','auth-timeout','both-cancel','client-close'])test('typed OAuth failure drains siblings and controls across '+mode,{timeout:5000},async t=>{
 let releaseFailure,bodySaved,mutations=0;const ready=new Promise(done=>releaseFailure=done),saved=new Promise(done=>bodySaved=done),originals=[],authorization=[];
 const f=await fixture(t,async({frame,res,later})=>{
  if(frame.params.name==='needs_auth'){mutations++;await ready;res.writeHead(401).end('AUTHORED_PRIVATE_BODY');return;}
  res.writeHead(200,{'content-type':'text/event-stream'});res.write('event: message\ndata: '+JSON.stringify({jsonrpc:'2.0',method:'notifications/progress',params:{progressToken:'authored',progress:1}})+'\n\n');releaseFailure();
  if(mode==='failed-cancel'||mode==='auth-timeout')later(()=>res.end('event: message\ndata: '+JSON.stringify({jsonrpc:'2.0',id:frame.id,result:{content:[{type:'text',text:'AUTHORED_SURVIVING_RECEIPT'}]}})+'\n\n'),120);
 },original=>{originals.push(original);bodySaved();return true;},{authorizationObserved:event=>{authorization.push(event);return true;}});
 const client=await f.connect({token:async()=>undefined,onUnauthorized:async()=>{throw new McpOAuthAuthorizationRequiredError();}}),firstAbort=new AbortController(),secondAbort=new AbortController();
 let closed;const closeEvent=new Promise(done=>closed=done);client.onClose(closed);
 const result=Promise.allSettled([client.callTool('needs_auth',{}, {signal:firstAbort.signal,timeoutMs:mode==='auth-timeout'?60:1000}),client.callTool('pending_read',{}, {signal:secondAbort.signal,timeoutMs:mode==='sibling-timeout'?60:1000})]);
 await saved;
 if(mode==='client-close')await client.close();
 if(mode==='sibling-cancel'||mode==='both-cancel')secondAbort.abort('Authored sibling cancellation');
 if(mode==='failed-cancel'||mode==='both-cancel')firstAbort.abort('Authored failed-call cancellation');
 const [first,second]=await result;
 if(mode==='client-close'){assert(first.reason instanceof McpConnectionClosedError);assert(second.reason instanceof McpConnectionClosedError);}
 else if(mode==='failed-cancel'||mode==='auth-timeout'){assert(first.reason instanceof (mode==='auth-timeout'?McpTimeoutError:McpAbortError));assert.equal(second.status,'fulfilled');assert.equal(second.value.content[0].text,'AUTHORED_SURVIVING_RECEIPT');}
 else{assert(first.reason instanceof (mode==='both-cancel'?McpAbortError:McpOAuthAuthorizationRequiredError));assert(second.reason instanceof (mode==='sibling-timeout'?McpTimeoutError:McpAbortError));}
 await closeEvent;assert.equal(client.connectionState,'closed');assert.equal(mutations,1);assert.equal(tools(f.calls).length,2);assert.equal(originals.length,1);assert.equal(originals[0].body.coverage,'complete');
 assert.equal(authorization.at(-1).state,'sign-in-required','the observation survives the original caller timeout/cancellation');assert(!JSON.stringify(authorization).includes('AUTHORED_PRIVATE_BODY'));
 if(mode!=='client-close'){
  const cancelled=f.calls.filter(row=>row.frame.method==='notifications/cancelled').map(row=>row.frame.params.requestId);
  if(mode!=='failed-cancel'&&mode!=='auth-timeout')assert(cancelled.includes(tools(f.calls).find(row=>row.frame.params.name==='pending_read').frame.id),'sibling cancellation reaches the wire before reset');
  if(mode==='failed-cancel'||mode==='auth-timeout'||mode==='both-cancel')assert(cancelled.includes(tools(f.calls).find(row=>row.frame.params.name==='needs_auth').frame.id),'failed-call cancellation reaches the wire before reset');
 }
});

test('new MCP tools are refused before dispatch during an auth drain while admitted receipts survive',{timeout:5000},async t=>{
 let releaseRead,required;const ready=new Promise(done=>releaseRead=done),reported=new Promise(done=>required=done),authorization=[];
 const f=await fixture(t,async({frame,res,later})=>{
  if(frame.params.name==='write_record'){await ready;res.writeHead(401).end('AUTHORED_PRIVATE_BODY');return;}
  res.writeHead(200,{'content-type':'text/event-stream'});res.write('event: message\ndata: '+JSON.stringify({jsonrpc:'2.0',method:'notifications/progress',params:{progressToken:'authored',progress:1}})+'\n\n');releaseRead();
  later(()=>res.end('event: message\ndata: '+JSON.stringify({jsonrpc:'2.0',id:frame.id,result:{content:[{type:'text',text:'AUTHORED_ADMITTED_RECEIPT'}]}})+'\n\n'),120);
 },()=>true,{authorizationObserved:event=>{authorization.push(event);if(event.state==='sign-in-required')required();return true;}});
 const client=await f.connect({token:async()=>undefined,onUnauthorized:async()=>{throw new McpOAuthAuthorizationRequiredError();}});
 const settled=Promise.allSettled([client.callTool('write_record',{}),client.callTool('read_record',{})]);await reported;
 await assert.rejects(client.callTool('late_write',{}),error=>error.message.includes('not dispatched'));
 const [failed,read]=await settled;assert(failed.reason instanceof McpOAuthAuthorizationRequiredError);assert.equal(read.value.content[0].text,'AUTHORED_ADMITTED_RECEIPT');assert.equal(tools(f.calls).length,2);assert.equal(authorization.at(-1).state,'sign-in-required');
});

test('an unauthorized cancellation does not wait on its own POST or discard a sibling receipt',{timeout:5000},async t=>{
 let held,release;const ready=new Promise(done=>release=done),authorization=[];
 const f=await fixture(t,({frame,res,later})=>{
  res.writeHead(200,{'content-type':'text/event-stream'});res.write('event: message\ndata: '+JSON.stringify({jsonrpc:'2.0',method:'notifications/progress',params:{progressToken:'authored',progress:1}})+'\n\n');
  if(frame.params.name==='cancel_read'){held=res;release();}else later(()=>res.end('event: message\ndata: '+JSON.stringify({jsonrpc:'2.0',id:frame.id,result:{content:[{type:'text',text:'AUTHORED_CONTROL_SIBLING'}]}})+'\n\n'),120);
 },undefined,{authorizationObserved:event=>{authorization.push(event);return true;},control:({frame,res})=>frame.method==='notifications/cancelled'?res.writeHead(403,{'www-authenticate':'Bearer error="insufficient_scope"'}).end('AUTHORED_PRIVATE_CONTROL'):res.writeHead(202).end()});
 const client=await f.connect({token:async()=>undefined,onUnauthorized:async()=>{throw new McpOAuthAuthorizationRequiredError();}}),abort=new AbortController();let close;const closed=new Promise(done=>close=done);client.onClose(close);
 const settled=Promise.allSettled([client.callTool('cancel_read',{}, {signal:abort.signal}),client.callTool('surviving_read',{})]);await ready;abort.abort();const [cancelled,read]=await settled;assert(cancelled.reason instanceof McpAbortError);assert.equal(read.value.content[0].text,'AUTHORED_CONTROL_SIBLING');await closed;
 assert(held);assert.equal(f.calls.filter(row=>row.frame.method==='notifications/cancelled').length,1);assert.equal(authorization.at(-1).state,'sign-in-required');assert.equal(authorization.at(-1).boundary,'http-control-response');assert(!JSON.stringify(authorization).includes('AUTHORED_PRIVATE_CONTROL'));
});
