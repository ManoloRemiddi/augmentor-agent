// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Packaged runtime proof with an external supplier prerequisite and synthetic inference.
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {existsSync,mkdtempSync,mkdirSync,symlinkSync,rmSync,readFileSync} from 'node:fs';
import {join,resolve} from 'node:path';
import {tmpdir} from 'node:os';
import {pathToFileURL} from 'node:url';
if(process.argv.length!==4)throw Error('Usage: proof-codex-prerequisite.mjs <packaged-app-root> <supplier-npm-package>');
const app=resolve(process.argv[2]),supplier=resolve(process.argv[3]);
assert.equal(JSON.parse(readFileSync(join(supplier,'package.json'))).name,'@openai/codex');
assert.equal(JSON.parse(readFileSync(join(supplier,'package.json'))).version,'0.159.2');
const release=JSON.parse(readFileSync(join(app,'release.json')));
assert.ok(!existsSync(join(app,'node_modules/@openai/codex')),'Supplier CLI must not be bundled');
const proof=mkdtempSync(join(tmpdir(),'augmentor-packaged-codex-')),state=join(proof,'state'),cwd=join(proof,'workspace');
mkdirSync(state,{mode:0o700});mkdirSync(cwd);
process.env.XDG_DATA_HOME=join(proof,'data');delete process.env.AUGMENTOR_CODEX_CLI;
const prerequisite=join(process.env.XDG_DATA_HOME,'augmentor/codex-cli/0.159.2/node_modules/@openai');
mkdirSync(prerequisite,{recursive:true});symlinkSync(supplier,join(prerequisite,'codex'));
assert.equal(JSON.parse(readFileSync(join(app,'distribution-prerequisites.json')))[0].bundled,false);
const {runtimeOptions,installedRuntimeVersion}=await import(pathToFileURL(join(app,'dist/codex-runtime/src/config.js')));
const {CodexRpc}=await import(pathToFileURL(join(app,'dist/codex-runtime/src/rpc.js')));
let requests=0;const responseText='Packaged Codex prerequisite proof passed.';
const server=createServer(async(req,res)=>{
 if(req.method!=='POST'||req.url!=='/v1/responses'){res.writeHead(404);res.end();return;}
 let body='';for await(const chunk of req)body+=chunk;
 const request=JSON.parse(body);assert.equal(request.model,'packaged-synthetic');assert.equal(request.stream,true);assert.equal(request.store,false);requests++;
 res.writeHead(200,{'content-type':'text/event-stream'});
 const send=event=>res.write(`data: ${JSON.stringify(event)}\n\n`);
 const item={id:'packaged_msg',type:'message',role:'assistant',status:'completed',content:[{type:'output_text',text:responseText,annotations:[]}]};
 send({type:'response.created',response:{id:'packaged_resp',status:'in_progress',output:[]}});
 send({type:'response.output_item.added',output_index:0,item:{...item,status:'in_progress',content:[]}});
 send({type:'response.output_text.delta',item_id:item.id,output_index:0,content_index:0,delta:responseText});
 send({type:'response.output_item.done',output_index:0,item});
 send({type:'response.completed',response:{id:'packaged_resp',status:'completed',output:[item],usage:{input_tokens:1,output_tokens:1,total_tokens:2}}});res.end();
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const options={...runtimeOptions({kind:'local',model:'packaged-synthetic',endpoint:`http://127.0.0.1:${server.address().port}/v1`},state,cwd),experimentalApi:true};
const clients=[];
try{
 assert.equal(installedRuntimeVersion(),'0.159.2');
 const rpc=new CodexRpc(options);clients.push(rpc);await rpc.initialize();
 const {thread}=await rpc.call('thread/start',{cwd,approvalPolicy:'never',sandbox:'read-only',baseInstructions:'Synthetic proof; do not use tools.'});
 const done=new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Synthetic turn timeout')),15000);rpc.on('notification',event=>{if(event.method==='turn/completed'){clearTimeout(timer);resolve(event.params);}});});
 await rpc.call('turn/start',{threadId:thread.id,input:[{type:'text',text:'Return the synthetic proof response.'}]});
 assert.equal((await done).turn.status,'completed');assert.equal(requests,1);await rpc.close();
 const reopened=new CodexRpc(options);clients.push(reopened);await reopened.initialize();
 const resumed=await reopened.call('thread/resume',{threadId:thread.id,approvalPolicy:'never',sandbox:'read-only'});assert.equal(resumed.thread.id,thread.id);
 const history=await reopened.call('thread/read',{threadId:thread.id,includeTurns:true});
 assert.ok(history.thread.turns.some(turn=>turn.items.some(item=>item.type==='agentMessage'&&item.text===responseText)));assert.equal(requests,1);
 console.log(JSON.stringify({source:release.source,artifact:'packaged runtime',bundledCodex:false,defaultExternalPrerequisite:true,version:'0.159.2',syntheticInference:true,nativeReopen:true,requests:1}));
}finally{for(const rpc of clients)await rpc.close();server.closeAllConnections();await new Promise(resolve=>server.close(resolve));rmSync(proof,{recursive:true,force:true});}
