// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.
// Real plugin bundle and WebSocket round trips; fake DSH services and browser.
// Run after building plugin/dist; AUGMENTOR_TEST_MODULES points to installed
// plugin dependencies when plugin/node_modules is not installed locally.
import assert from 'node:assert/strict'
import {mkdtemp,copyFile,symlink,rm} from 'node:fs/promises'
import {createServer} from 'node:http'
import {tmpdir} from 'node:os'
import {join,resolve} from 'node:path'
import {fileURLToPath,pathToFileURL} from 'node:url'
const root=fileURLToPath(new URL('..',import.meta.url)),dir=await mkdtemp(join(tmpdir(),'augmentor-plugin-proof-'))
const cleanups=[],registered=new Map(),routes=new Map();let upgrade,pipe,server,response
try {
 await copyFile(join(root,'plugin/dist/index.js'),join(dir,'index.mjs'))
 await symlink(resolve(process.env.AUGMENTOR_TEST_MODULES??join(root,'plugin/node_modules')),join(dir,'node_modules'),'dir')
 const {assertObjectJsonSchema,assertSupportedJsonSchema}=await import(pathToFileURL(join(dir,'node_modules/@deepseek-ai/dsh-tools/lib/index.js')))
 const {apply}=await import(pathToFileURL(join(dir,'index.mjs')))
 const webServer={register:route=>{routes.set(route.path,route.handler);return()=>routes.delete(route.path)},registerUpgrade:route=>{upgrade=route;return()=>{}}}
 let supportsImages=true,attachments=0
 const ctx={tools:{register:tool=>{assertObjectJsonSchema(tool.parameters);assertSupportedJsonSchema(tool.output.schema);registered.set(tool.name,tool)}},get:name=>name==='webServer'?webServer:{},effect:fn=>{const result=fn();cleanups.push(result);return result},on:()=>{},
  llm:{resolveModelInfo:async()=>({inputModalities:supportsImages?['text','image']:['text']})},attachments:{saveImage:async value=>{assert.ok(Buffer.isBuffer(value.data));assert.equal(value.mediaType,'image/jpeg');attachments++;return {id:'test-image'}}}}
 apply(ctx,{chatDir:join(dir,'chats'),apiPath:'/api/augmentor',wsPath:'/api/augmentor/ws',wsToken:'test-only-token',commandTimeoutMs:1000,sweepFirstDelayMs:600000,sweepEveryMs:600000})
 server=createServer((req,res)=>{const handler=routes.get(req.url);if(handler)handler(req,res);else{res.writeHead(404);res.end()}})
 server.on('upgrade',(req,socket,head)=>upgrade.handler(req,socket,head))
 await new Promise(r=>server.listen(0,'127.0.0.1',r))
 pipe=new WebSocket(`ws://127.0.0.1:${server.address().port}/api/augmentor/ws?token=test-only-token`)
 await new Promise((r,j)=>{pipe.onopen=r;pipe.onerror=j})
 let requests=0
 pipe.onmessage=e=>{const frame=JSON.parse(e.data);if(frame.type==='request'){requests++;pipe.send(JSON.stringify({type:'reply',id:frame.id,result:response}))}}
 const exec={signal:new AbortController().signal,agent:{session:{requestHeader:()=>({config:{}})},options:{provider:'fixture',model:'vision'}}}
 response=undefined
 const blank=await registered.get('browser_snapshot').execute({},exec)
 assert.equal(blank.ok,false);assert.match(blank.error,/No document observation/)
 response={ok:false,error:'protected page'}
 assert.equal((await registered.get('browser_snapshot').execute({},exec)).error,'protected page')
 response=undefined
 assert.equal((await registered.get('browser_click').execute({selector:'span:has-text("Control Panel")'},exec)).ok,false)
 response={ok:true,url:'https://fixture.test/',tabId:7,image:{mimeType:'image/jpeg',data:'aGVsbG8='}}
 const image=await registered.get('browser_screenshot').execute({},exec)
 assert.equal(image.content[1].type,'image');assert.equal(attachments,1);assert.match(image.content[0].text,/fixture.test/)
 supportsImages=false;const before=requests
 await assert.rejects(registered.get('browser_screenshot').execute({},exec),/does not declare image input/)
 assert.equal(requests,before)
 console.log('PASS: real DSH plugin/WS handles missing snapshots, nested failures, missing action acknowledgements, image delivery, and text-only gating.')
} finally {
 pipe?.close()
 for(const cleanup of cleanups.reverse())for(const fn of Array.isArray(cleanup)?cleanup:[cleanup])if(typeof fn==='function')await fn()
 if(server)await new Promise(r=>server.close(r))
 await rm(dir,{recursive:true,force:true})
}
