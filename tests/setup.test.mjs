// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {crc32} from 'node:zlib';
import {createServer} from 'node:http';
import {mkdtempSync,readFileSync,writeFileSync,existsSync,statSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {connectionConfig,SetupConnections} from '../dist/runtime/src/setup.js';
import {Host} from '../dist/runtime/src/host.js';

test('guided setup verifies a literal credential without tools, saves privately and rejects stale checks',async()=>{
  const root=mkdtempSync(join(tmpdir(),'augmentor-setup-'));
  const previous={...process.env};let host;
  const calls=[];let fail=false;
  const server=createServer(async(req,res)=>{
    let raw='';for await(const part of req)raw+=part;
    calls.push({body:JSON.parse(raw),auth:req.headers.authorization,url:req.url});
    if(fail){res.writeHead(401,{'Content-Type':'application/json'});res.end(JSON.stringify({error:{message:'private-response-body '+secret}}));return;}
    res.writeHead(200,{'Content-Type':'text/event-stream'});
    res.end('data: '+JSON.stringify({id:'setup',object:'chat.completion.chunk',model:'fixture',choices:[{index:0,delta:{role:'assistant',content:'READY'},finish_reason:'stop'}]})+'\n\ndata: [DONE]\n\n');
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const secret='!literal-$AUGMENTOR_DO_NOT_EXPAND';
  const input={name:'My model',model:'fixture',api:'openai-completions',baseUrl:`http://127.0.0.1:${server.address().port}/v1`,apiKey:secret,contextWindow:32768,maxTokens:4096};
  try{
    process.env.AUGMENTOR_PI_CONFIG=join(root,'config');process.env.AUGMENTOR_PI_STATE=join(root,'state');process.env.PI_OFFLINE='1';
    host=new Host(()=>{},()=>false);await host.init();
    const file=join(host.dirs.agent,'models.json');
    const checked=await host.dispatch('setup.test',input,'check');
    assert.equal(existsSync(file),false,'Testing must not save credentials/configuration');
    assert.equal(calls.length,1);assert.equal(calls[0].auth,'Bearer '+secret);
    assert.equal(calls[0].url,'/v1/chat/completions');
    assert.equal(calls[0].body.messages.length,1);assert.equal(calls[0].body.messages[0].content,'Reply with READY to verify this connection.');
    assert.equal((calls[0].body.tools??[]).length,0);assert.equal(host.metadata.size,0);
    assert.equal(JSON.stringify(checked).includes(secret),false);
    const saved=await host.dispatch('setup.save',{token:checked.token,approvalMode:'workspace-write'},'save');
    assert.deepEqual(saved.selection,{provider:'augmentor-my-model',model:'fixture'});
    assert.equal(statSync(file).mode&0o777,0o600);assert.deepEqual(host.settings.defaultModel,saved.selection);
    const auth=await host.modelRuntime.getAuth('augmentor-my-model');assert.equal(auth.auth.apiKey,secret);
    await assert.rejects(host.dispatch('setup.save',{token:checked.token,approvalMode:'workspace-write'},'again'),/check again/);
    const another=await host.setup.test({...input,name:'Second model',images:true});
    assert.deepEqual(another.verified,['text','image-input']);
    const image=calls[1].body.messages[0].content.find(p=>p.type==='image_url');
    assert.match(image.image_url.url,/^data:image\/png;base64,/);
    const png=Buffer.from(image.image_url.url.split(',')[1],'base64');
    for(let offset=8;offset<png.length;){const length=png.readUInt32BE(offset);assert.equal(crc32(png.subarray(offset+4,offset+8+length)),png.readUInt32BE(offset+8+length));offset+=12+length}
    assert.deepEqual(host.setup.checked(another.token).config.providers['augmentor-second-model'].models[0].input,['text','image']);
    writeFileSync(file,readFileSync(file,'utf8')+'\n');
    await assert.rejects(host.dispatch('setup.save',{token:another.token,approvalMode:'workspace-write'},'stale'),/settings changed/);
    const snapshot=readFileSync(file,'utf8');fail=true;
    await assert.rejects(host.setup.test({...input,name:'Rejected model'}),error=>{
      assert.match(error.message,/rejected the credentials/);assert.equal(error.message.includes(secret),false);assert.equal(error.message.includes('private-response-body'),false);return true;
    });
    assert.equal(readFileSync(file,'utf8'),snapshot);assert.equal(calls.length,3,'No automatic model request retries');
  }finally{await host?.close();server.closeAllConnections();await new Promise(resolve=>server.close(resolve));process.env=previous;rmSync(root,{recursive:true,force:true});}
});

test('setup rejects invalid endpoints and limits before contacting a provider',()=>{
  const input={name:'test',model:'test',api:'openai-completions',baseUrl:'http://localhost:8080/v1',apiKey:'',contextWindow:32768,maxTokens:4096};
  for(const patch of [{baseUrl:'http://example.com/v1'},{baseUrl:'https://user:secret@example.com'},{baseUrl:'file:///etc/passwd'},
    {baseUrl:'https://example.com/v1?api_key=secret'},{contextWindow:2},{maxTokens:100000},{images:'yes'},{api:'made-up'},{name:'!!!'}]){
    assert.throws(()=>connectionConfig({...input,...patch}));
  }
});

test('cancelling a connection check prevents saving and does not replay the request',async()=>{
  const root=mkdtempSync(join(tmpdir(),'augmentor-setup-stop-'));let resolveSeen;
  const seen=new Promise(resolve=>{resolveSeen=resolve;});let requests=0;
  const server=createServer((_req,res)=>{requests++;res.writeHead(200,{'Content-Type':'text/event-stream'});res.write(': waiting\n\n');resolveSeen();});
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  try{
    const setup=new SetupConnections(join(root,'models.json'));
    const checking=setup.test({name:'cancel',model:'fixture',api:'openai-completions',baseUrl:`http://127.0.0.1:${server.address().port}/v1`,contextWindow:32768,maxTokens:4096});
    const assertion=assert.rejects(checking,/cancelled or timed out/);
    await seen;setup.cancel();await assertion;
    assert.throws(()=>setup.checked('anything'),/check again/);assert.equal(requests,1);assert.equal(existsSync(join(root,'models.json')),false);
  }finally{server.closeAllConnections();await new Promise(resolve=>server.close(resolve));rmSync(root,{recursive:true,force:true});}
});
